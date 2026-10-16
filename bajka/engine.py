"""Silnik bajki: odtwarza sceny, słucha dziecka (albo całej widowni) i wybiera kolejny klip."""

from __future__ import annotations

import logging
import threading
from collections import Counter
from pathlib import Path

from bajka.ports import Audience, IntentResolver, Interpretation, Listener, Player, ShoutMeter, Voice
from bajka.scenario import Choice, Scenario, Scene

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"


class _Stopped(Exception):
    """Okno zostało zamknięte (Esc): bajka kończy się natychmiast, bez dalszych scen i kwestii."""


class StoryEngine:
    """Prowadzi bajkę od sceny startowej do zakończenia.

    Błędy mikrofonu, LLM i TTS są tu logowane i obsłużone, żeby bajka nigdy nie stanęła.
    """

    def __init__(
        self,
        scenario: Scenario,
        player: Player,
        listener: Listener,
        voice: Voice,
        resolver: IntentResolver,
        max_reprompts: int = 2,
        meter: ShoutMeter | None = None,
        audience: Audience | None = None,
    ) -> None:
        self._stopped = threading.Event()
        self._scenario = scenario
        self._player = player
        self._listener = listener
        self._voice = voice
        self._resolver = resolver
        self._max_reprompts = max_reprompts
        self._meter = meter  # bez krzykomierza sceny `vote` rozpoznają wybór z mowy, jak pozostałe
        self._audience = audience  # telefony widzów; gdy żaden nie jest połączony, słuchamy sali

    def stop(self) -> None:
        """Przerywa bajkę przy najbliższej okazji; wywoływane z wątku okna, np. po Esc."""
        self._stopped.set()

    def _check_stopped(self) -> None:
        if self._stopped.is_set():
            raise _Stopped

    def _play(self, clip: Path) -> None:
        self._check_stopped()
        self._player.play(clip)

    def _loop(self, clip: Path) -> None:
        self._check_stopped()
        self._player.loop(clip)

    def run(self) -> list[str]:
        """Odtwarza bajkę i zwraca identyfikatory odwiedzonych scen."""
        visited: list[str] = []
        scene = self._scenario.scene(self._scenario.start)
        try:
            while True:
                self._check_stopped()
                visited.append(scene.id)
                log.info("Scena: %s", scene.id)
                self._play(scene.clip)
                if scene.is_ending:
                    return visited
                if scene.idle is not None:
                    self._loop(scene.idle)
                scene = self._scenario.scene(self._decide(scene).next)
        except _Stopped:
            log.info("Bajka zatrzymana")
            return visited

    def _decide(self, scene: Scene) -> Choice:
        if self._audience is not None and self._phones_connected():
            return self._ask_audience(scene)
        if scene.vote and self._meter is not None:
            return self._vote(scene)
        return self._ask(scene)

    def _phones_connected(self) -> bool:
        try:
            return self._audience.connected() > 0
        except Exception:
            log.exception("Błąd aplikacji mobilnej, słucham sali")
            return False

    def _ask_audience(self, scene: Scene) -> Choice:
        """Runda na telefonach widowni: wygrywa wybór, który wskazało najwięcej osób."""
        for attempt in range(self._max_reprompts + 1):
            answers = self._collect(scene)
            votes = Counter(a.choice_id for a in answers if a.choice_id in scene.choices)
            ranked = votes.most_common(2)
            log.info("Odpowiedzi z telefonów: %d, głosy: %s", len(answers), dict(votes))
            if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
                choice = scene.choices[ranked[0][0]]
                # Jedna odpowiedź = osobista reakcja modelu; przy wielu Lila mówi stałą kwestię ze scenariusza.
                personal = answers[0].reply if len(answers) == 1 else ""
                self._say(personal or choice.reply)
                return choice
            if attempt < self._max_reprompts:
                unclear = answers[0].reply if len(answers) == 1 and not votes else ""
                self._say(unclear or scene.reprompt)
        default = scene.choices[scene.default]
        log.info("Brak decyzji z telefonów, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _collect(self, scene: Scene) -> list[Interpretation]:
        try:
            return self._audience.collect(scene)
        except Exception:
            log.exception("Błąd aplikacji mobilnej, traktuję rundę jak ciszę")
            return []

    def _vote(self, scene: Scene) -> Choice:
        """Runda okrzyków: bohaterka wzywa po kolei do każdej opcji, wygrywa najgłośniejsza."""
        for attempt in range(self._max_reprompts + 1):
            winner = self._shout_round(scene)
            if winner is not None:
                choice = scene.choices[winner]
                self._say(choice.reply)
                return choice
            if attempt < self._max_reprompts:
                self._say(scene.reprompt)
        default = scene.choices[scene.default]
        log.info("Za cicho albo remis, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _shout_round(self, scene: Scene) -> str | None:
        try:
            self._meter.calibrate()
            levels: dict[str, float] = {}
            for choice in scene.choices.values():
                if choice.call_clip is not None:
                    self._play(choice.call_clip)
                    self._loop(scene.idle)
                else:
                    self._say(choice.call)
                levels[choice.id] = self._meter.measure()
            winner = self._meter.winner(levels)
        except _Stopped:
            raise
        except Exception:
            log.exception("Błąd krzykomierza, traktuję jak ciszę")
            return None
        log.info("Okrzyki: %s -> %s", ", ".join(f"{k}={v:.0f}" for k, v in levels.items()), winner)
        return winner if winner in scene.choices else None

    def _ask(self, scene: Scene) -> Choice:
        for attempt in range(self._max_reprompts + 1):
            transcript = self._listen()
            if transcript:
                interpretation = self._interpret(scene, transcript)
                if interpretation.choice_id is not None:
                    choice = scene.choices[interpretation.choice_id]
                    self._say(interpretation.reply or choice.reply)
                    return choice
                retry_line = interpretation.reply or scene.reprompt
            else:
                retry_line = scene.reprompt
            if attempt < self._max_reprompts:
                self._say(retry_line)
        default = scene.choices[scene.default]
        log.info("Brak decyzji, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _listen(self) -> str | None:
        self._check_stopped()
        try:
            transcript = self._listener.listen()
        except Exception:
            log.exception("Błąd rozpoznawania mowy, traktuję jak ciszę")
            return None
        log.info("Dziecko: %r", transcript)
        return transcript or None

    def _interpret(self, scene: Scene, transcript: str) -> Interpretation:
        default = scene.choices[scene.default]
        try:
            interpretation = self._resolver.resolve(scene, transcript)
        except Exception:
            log.exception("Błąd LLM, wybieram domyślnie: %s", default.id)
            return Interpretation(choice_id=default.id, reply=default.reply)
        if interpretation.choice_id is not None and interpretation.choice_id not in scene.choices:
            log.error("LLM zwrócił nieznany wybór %r, wybieram: %s", interpretation.choice_id, default.id)
            return Interpretation(choice_id=default.id, reply=default.reply)
        log.info("Intencja: %s | %s", interpretation.choice_id, interpretation.reply)
        return interpretation

    def _say(self, text: str) -> None:
        self._check_stopped()  # przed try: zatrzymanie nie jest błędem TTS
        try:
            self._voice.say(text)
        except Exception:
            log.exception("Błąd TTS, bajka leci dalej bez kwestii: %s", text)

"""Silnik odcinka: odtwarza sceny, otwiera okna wyboru i prowadzi widza po grafie scen.

Okno wyboru: widz wskazuje opcję (pilot, dotyk, klawiatura) albo mówi ją do mikrofonu. Gdy czas minie bez wyboru,
postać dopytuje, a po ostatniej próbie gra wybór domyślny — odcinek nigdy nie staje. Po wyborze gra nagrany klip
reakcji (`reaction`), a gdy go nie ma, postać mówi swoją kwestię (`reply`).
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from pathlib import Path
from typing import Any

from bajka.ports import (
    Answer,
    Audience,
    AudiencePulse,
    IntentResolver,
    Interpretation,
    Listener,
    Player,
    ShowObserver,
    Viewer,
    Voice,
)
from bajka.pulse import PulseSettings, hall_state, pick_variant
from bajka.scenario import Choice, Scenario, Scene

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"
DEFAULT_CHOICE_SECONDS = 12.0  # dzieci 4–7 lat potrzebują więcej czasu niż dorośli widzowie (ok. 10 s)


class _Stopped(Exception):
    """Widz zamknął odcinek (Esc, przycisk „Zakończ”): koniec natychmiast, bez dalszych scen i kwestii."""


class _ListenerViewer:
    """Okno wyboru bez przycisków: tylko mikrofon (np. odtwarzacz VLC na komputerze)."""

    def __init__(self, listener: Listener) -> None:
        self._listener = listener

    def ask(self, scene: Scene, seconds: float) -> Answer:
        return Answer(transcript=self._listener.listen())


class StoryEngine:
    """Prowadzi odcinek od sceny startowej do zakończenia.

    Błędy mikrofonu, modelu językowego, głosu i panelu są logowane i obsłużone, żeby odcinek nigdy nie stanął.
    """

    def __init__(
        self,
        scenario: Scenario,
        player: Player,
        viewer: Viewer | Listener,
        voice: Voice,
        resolver: IntentResolver,
        max_reprompts: int = 2,
        audience: Audience | None = None,
        pulse: AudiencePulse | None = None,
        pulse_settings: PulseSettings | None = None,
        observer: ShowObserver | None = None,
        choice_seconds: float = DEFAULT_CHOICE_SECONDS,
    ) -> None:
        self._stopped = threading.Event()
        self._observer = observer  # panel podglądu; jego błędy nigdy nie zatrzymują odcinka
        self._pulse = pulse  # tętno widza; bez niego sceny grają zawsze zwykłą wersję
        self._pulse_settings = pulse_settings or PulseSettings()
        self._baseline: float | None = None  # tętno tuż po pierwszej scenie, punkt odniesienia na cały odcinek
        self._scenario = scenario
        self._player = player
        self._viewer: Viewer = viewer if isinstance(viewer, Viewer) else _ListenerViewer(viewer)
        self._voice = voice
        self._resolver = resolver
        self._max_reprompts = max_reprompts
        self._audience = audience  # telefony domowników (drugi ekran); bez nich odpowiada okno wyboru
        self._choice_seconds = choice_seconds

    def stop(self) -> None:
        """Przerywa odcinek przy najbliższej okazji; wywoływane z innego wątku, np. po Esc."""
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

    def _emit(self, kind: str, **data: Any) -> None:
        if self._observer is None:
            return
        try:
            self._observer.event(kind, data)
        except Exception:
            log.exception("Błąd panelu, odcinek leci dalej")

    def _clip_for(self, scene: Scene) -> tuple[Path, str]:
        """Klip i nazwa wersji według tętna widza; zwykła wersja, gdy tętna nie ma albo jest w normie."""
        if not scene.variants or self._pulse is None or self._baseline is None:
            return scene.clip, "zwykla"
        bpm = self._read_bpm()
        if bpm is None:
            return scene.clip, "zwykla"
        state = hall_state(bpm, self._baseline, self._pulse_settings)
        variant = pick_variant(self._scenario.mood, state)
        chosen = variant if variant in scene.variants else "zwykla"
        log.info("Tętno %.0f (odniesienie %.0f), stan: %s: scena %s w wersji %s",
                 bpm, self._baseline, state, scene.id, chosen)  # fmt: skip
        self._emit("wersja", scene=scene.id, bpm=bpm, baseline=self._baseline, state=state, variant=chosen)
        return scene.variants.get(chosen, scene.clip), chosen

    def _read_bpm(self) -> float | None:
        try:
            return self._pulse.read().bpm
        except Exception:
            log.exception("Błąd odczytu tętna, scena w zwykłej wersji")
            return None

    def run(self) -> list[str]:
        """Odtwarza odcinek i zwraca identyfikatory odwiedzonych scen."""
        visited: list[str] = []
        scene = self._scenario.scene(self._scenario.start)
        try:
            while True:
                self._check_stopped()
                visited.append(scene.id)
                log.info("Scena: %s", scene.id)
                clip, variant = self._clip_for(scene)
                self._emit("scena", scene=scene.id, clip=clip.name, variant=variant)
                self._play(clip)
                if scene.is_ending:
                    return visited
                if self._pulse is not None and self._baseline is None:
                    self._baseline = self._read_bpm()  # widz dopiero się usadowił
                    if self._baseline is not None:
                        self._emit("odniesienie", bpm=self._baseline)
                if scene.idle is not None:
                    self._loop(scene.idle)
                scene = self._scenario.scene(self._decide(scene).next)
        except _Stopped:
            log.info("Odcinek zatrzymany")
            return visited

    def _decide(self, scene: Scene) -> Choice:
        if self._audience is not None and self._phones_connected():
            return self._ask_audience(scene)
        return self._ask(scene)

    def _chosen(self, scene: Scene, choice: Choice, how: str, personal: str = "", prefix: str = "") -> Choice:
        """Zapisuje decyzję dla panelu i odtwarza reakcję postaci na wybór."""
        self._emit("decyzja", scene=scene.id, choice=choice.id, label=choice.display_label, how=how)
        if choice.reaction is not None:
            if prefix:
                self._say(prefix)
            self._play(choice.reaction)  # nagrana reakcja: ten sam głos i animacja co w odcinku
        else:
            line = personal or choice.reply
            self._say(f"{prefix} {line}" if prefix else line)
        return choice

    def _default(self, scene: Scene) -> Choice:
        default = scene.choices[scene.default]
        log.info("Brak wyboru, postać wybiera sama: %s", default.id)
        return self._chosen(scene, default, "domyslna", prefix=scene.fallback or DEFAULT_FALLBACK)

    def _ask(self, scene: Scene) -> Choice:
        """Okno wyboru: przycisk rozstrzyga od razu, głos przez rozpoznanie intencji, cisza to dopytanie."""
        seconds = scene.timeout or self._choice_seconds
        for attempt in range(self._max_reprompts + 1):
            answer = self._prompt(scene, seconds)
            if answer.choice_id in scene.choices:
                return self._chosen(scene, scene.choices[answer.choice_id], "przycisk")
            if answer.transcript:
                interpretation = self._interpret(scene, answer.transcript)
                if interpretation.choice_id is not None:
                    choice = scene.choices[interpretation.choice_id]
                    return self._chosen(scene, choice, "glos", personal=interpretation.reply)
                retry_line = interpretation.reply or scene.reprompt
            else:
                retry_line = scene.reprompt
            if attempt < self._max_reprompts:
                self._say(retry_line)
        return self._default(scene)

    def _prompt(self, scene: Scene, seconds: float) -> Answer:
        self._check_stopped()
        try:
            answer = self._viewer.ask(scene, seconds)
        except Exception:
            log.exception("Błąd okna wyboru albo mikrofonu, traktuję jak brak odpowiedzi")
            return Answer()
        self._check_stopped()  # zamknięcie odcinka w trakcie okna wyboru to nie odpowiedź
        log.info("Widz: wybór %s, mowa %r", answer.choice_id, answer.transcript)
        return answer

    def _phones_connected(self) -> bool:
        try:
            return self._audience.connected() > 0
        except Exception:
            log.exception("Błąd drugiego ekranu, odpowiada okno wyboru")
            return False

    def _ask_audience(self, scene: Scene) -> Choice:
        """Runda na telefonach domowników: wygrywa wybór, który wskazało najwięcej osób."""
        for attempt in range(self._max_reprompts + 1):
            answers = self._collect(scene)
            votes = Counter(a.choice_id for a in answers if a.choice_id in scene.choices)
            ranked = votes.most_common(2)
            log.info("Odpowiedzi z telefonów: %d, głosy: %s", len(answers), dict(votes))
            self._emit("glosy", scene=scene.id, source="telefony", counts={cid: votes[cid] for cid in scene.choices})
            if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
                # Jedna odpowiedź = osobista reakcja modelu (gdy nie ma klipu reakcji); przy wielu — kwestia ze scenariusza.
                personal = answers[0].reply if len(answers) == 1 else ""
                return self._chosen(scene, scene.choices[ranked[0][0]], "wiekszosc", personal=personal)
            if attempt < self._max_reprompts:
                unclear = answers[0].reply if len(answers) == 1 and not votes else ""
                self._say(unclear or scene.reprompt)
        return self._default(scene)

    def _collect(self, scene: Scene) -> list[Interpretation]:
        try:
            return self._audience.collect(scene)
        except Exception:
            log.exception("Błąd drugiego ekranu, traktuję rundę jak ciszę")
            return []

    def _interpret(self, scene: Scene, transcript: str) -> Interpretation:
        default = scene.choices[scene.default]
        try:
            interpretation = self._resolver.resolve(scene, transcript)
        except Exception:
            log.exception("Błąd modelu językowego, wybieram domyślnie: %s", default.id)
            return Interpretation(choice_id=default.id, reply="")
        if interpretation.choice_id is not None and interpretation.choice_id not in scene.choices:
            log.error("Model zwrócił nieznany wybór %r, wybieram: %s", interpretation.choice_id, default.id)
            return Interpretation(choice_id=default.id, reply="")
        log.info("Intencja: %s | %s", interpretation.choice_id, interpretation.reply)
        return interpretation

    def _say(self, text: str) -> None:
        self._check_stopped()  # przed try: zatrzymanie nie jest błędem głosu
        try:
            self._voice.say(text)
        except Exception:
            log.exception("Błąd głosu postaci, odcinek leci dalej bez kwestii: %s", text)

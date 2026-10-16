"""Silnik bajki: odtwarza sceny, słucha dziecka i wybiera kolejny klip."""

from __future__ import annotations

import logging

from bajka.ports import IntentResolver, Interpretation, Listener, Player, Voice
from bajka.scenario import Choice, Scenario, Scene

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"


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
    ) -> None:
        self._scenario = scenario
        self._player = player
        self._listener = listener
        self._voice = voice
        self._resolver = resolver
        self._max_reprompts = max_reprompts

    def run(self) -> list[str]:
        """Odtwarza bajkę i zwraca identyfikatory odwiedzonych scen."""
        visited: list[str] = []
        scene = self._scenario.scene(self._scenario.start)
        while True:
            visited.append(scene.id)
            log.info("Scena: %s", scene.id)
            self._player.play(scene.clip)
            if scene.is_ending:
                return visited
            if scene.idle is not None:
                self._player.loop(scene.idle)
            choice = self._ask(scene)
            scene = self._scenario.scene(choice.next)

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
        try:
            self._voice.say(text)
        except Exception:
            log.exception("Błąd TTS, bajka leci dalej bez kwestii: %s", text)

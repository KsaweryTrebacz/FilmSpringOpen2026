"""Interfejsy, od których zależy silnik bajki. Implementacje: Azure, VLC, konsola, atrapy w testach."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bajka.scenario import Scene


@dataclass(frozen=True)
class Interpretation:
    choice_id: str | None  # None = intencja nierozpoznana, bohater dopytuje
    reply: str  # kwestia bohatera do wypowiedzenia przez TTS


class Player(Protocol):
    def play(self, clip: Path) -> None:
        """Odtwarza klip i blokuje do jego końca."""

    def loop(self, clip: Path) -> None:
        """Zapętla klip w tle i wraca od razu."""


class Listener(Protocol):
    def listen(self) -> str | None:
        """Słucha jednej wypowiedzi dziecka. None oznacza ciszę."""


class Voice(Protocol):
    def say(self, text: str) -> None:
        """Wypowiada kwestię bohatera i blokuje do końca wypowiedzi."""


class IntentResolver(Protocol):
    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        """Zamienia wypowiedź dziecka na wybór ze sceny i kwestię bohatera."""

"""Kontrakty między modułami bajki.

Każdy moduł (STT, TTS, odtwarzacz, intencje) implementuje jeden z tych interfejsów i nie importuje
pozostałych modułów, więc można go rozwijać i testować osobno. Silnik bajki zależy tylko od nich.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from bajka.scenario import Scene


@dataclass(frozen=True)
class Interpretation:
    choice_id: str | None  # None = intencja nierozpoznana, bohater dopytuje
    reply: str  # kwestia bohatera do wypowiedzenia przez TTS


@runtime_checkable
class Player(Protocol):
    def play(self, clip: Path) -> None:
        """Odtwarza klip i blokuje do jego końca."""

    def loop(self, clip: Path) -> None:
        """Zapętla klip w tle i wraca od razu."""


@runtime_checkable
class Listener(Protocol):
    def listen(self) -> str | None:
        """Słucha jednej wypowiedzi dziecka. None oznacza ciszę."""


@runtime_checkable
class Voice(Protocol):
    def say(self, text: str) -> None:
        """Wypowiada kwestię bohatera i blokuje do końca wypowiedzi."""


@runtime_checkable
class IntentResolver(Protocol):
    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        """Zamienia wypowiedź dziecka na wybór ze sceny i kwestię bohatera."""


@runtime_checkable
class ShoutMeter(Protocol):
    """Krzykomierz: mierzy okrzyki widowni w scenach `vote` (seans w kinie)."""

    def calibrate(self) -> None:
        """Mierzy gwar sali tuż przed rundą okrzyków."""

    def measure(self) -> float:
        """Mierzy okrzyk zaraz po wezwaniu do jednej opcji i zwraca jego głośność."""

    def winner(self, levels: dict[str, float]) -> str | None:
        """Zwycięska opcja rundy albo None, gdy było za cicho lub wyszedł remis."""

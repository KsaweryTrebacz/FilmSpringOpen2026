"""Kontrakty między modułami bajki.

Każdy moduł (odtwarzacz, okno wyboru, rozpoznawanie mowy, głos postaci, intencje) implementuje jeden z tych
interfejsów i nie importuje pozostałych modułów, więc można go rozwijać i testować osobno. Silnik zależy tylko od nich.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

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


@dataclass(frozen=True)
class Answer:
    """Odpowiedź z okna wyboru: wskazana opcja (pilot, dotyk, klawiatura) albo to, co widz powiedział."""

    choice_id: str | None = None
    transcript: str | None = None


@runtime_checkable
class Viewer(Protocol):
    """Widz przed ekranem: okno wyboru w odtwarzaczu (bajka/web_player.py), konsola przy próbach."""

    def ask(self, scene: Scene, seconds: float) -> Answer:
        """Pokazuje okno wyboru (i słucha mikrofonu, jeśli rodzic go włączył) aż do odpowiedzi albo upływu czasu.

        Pusta odpowiedź oznacza, że czas minął bez wyboru.
        """


@runtime_checkable
class Voice(Protocol):
    def say(self, text: str) -> None:
        """Wypowiada kwestię bohatera i blokuje do końca wypowiedzi."""


@runtime_checkable
class IntentResolver(Protocol):
    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        """Zamienia wypowiedź dziecka na wybór ze sceny i kwestię bohatera."""


@runtime_checkable
class Audience(Protocol):
    """Drugi ekran: telefony domowników jako pilot głosowy, gdy telewizor nie ma mikrofonu (bajka/mobile.py)."""

    def connected(self) -> int:
        """Ile telefonów jest teraz połączonych z odcinkiem."""

    def collect(self, scene: Scene) -> list[Interpretation]:
        """Otwiera rundę na telefonach (pytanie i opcje), czeka na odpowiedzi i zwraca rozpoznane wybory.

        Pusta lista oznacza, że nikt nie odpowiedział.
        """


@dataclass(frozen=True)
class Pulse:
    bpm: float  # tętno widza (przy kilku widzach z zegarkami: średnia)
    viewers: int  # od ilu widzów pochodzi odczyt (w demo: symulowanych)


@runtime_checkable
class AudiencePulse(Protocol):
    """Tętno widza z zegarka, za zgodą rodzica (w przyszłości; dziś z symulatora, bajka/pulse.py)."""

    def read(self) -> Pulse:
        """Bieżące tętno widza."""


@runtime_checkable
class ShowObserver(Protocol):
    """Obserwator odcinka: panel podglądu (bajka/panel.py) dostaje zdarzenia z silnika."""

    def event(self, kind: str, data: Mapping[str, Any]) -> None:
        """Zdarzenie odcinka: `scena`, `odniesienie`, `wersja`, `glosy` albo `decyzja` z danymi do pokazania."""

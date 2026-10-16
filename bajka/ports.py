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


@runtime_checkable
class Audience(Protocol):
    """Widownia z aplikacją mobilną: odpowiedzi przychodzą z mikrofonów telefonów (bajka/mobile.py)."""

    def connected(self) -> int:
        """Ile telefonów jest teraz połączonych z seansem."""

    def collect(self, scene: Scene) -> list[Interpretation]:
        """Otwiera rundę na telefonach (pytanie i opcje), czeka na odpowiedzi i zwraca rozpoznane wybory.

        Pusta lista oznacza, że nikt nie odpowiedział.
        """


@dataclass(frozen=True)
class Vision:
    reply: str  # kwestia postaci po polsku, wypowiadana podczas rysowania
    idea: str  # pomysł dziecka po angielsku, bezpieczny dla dzieci; "" gdy nie da się go użyć


@runtime_checkable
class Imaginer(Protocol):
    def imagine(self, scene: Scene, transcript: str) -> Vision:
        """Zamienia odpowiedź na pytanie otwarte na kwestię postaci i opis ilustracji."""


@runtime_checkable
class Illustrator(Protocol):
    def draw(self, prompt: str) -> Path:
        """Rysuje ilustrację sceny w stylu bajki i zwraca ścieżkę do pliku PNG."""


@runtime_checkable
class Animator(Protocol):
    def animate(self, image: Path) -> Path:
        """Robi z ilustracji klip MP4 z ruchem kamery i zwraca jego ścieżkę."""

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


@dataclass(frozen=True)
class Cut:
    """Decyzja montażowa: jak kolejny klip wchodzi na ekran (rodzaje w `bajka.scenario.TRANSITIONS`)."""

    transition: str = "ciecie"
    seconds: float = 0.0
    reason: str = ""  # jednym zdaniem dla panelu podglądu: dlaczego takie przejście
    source: str = "reguly"  # kto zdecydował: "model" (AI) albo "reguly"


@dataclass(frozen=True)
class Shot:
    """Ujęcie do odtworzenia: klip z nałożonymi warstwami i przejściem, którym wchodzi na ekran."""

    clip: Path
    layers: tuple[Path, ...] = ()  # przezroczyste klipy nakładane na klip, w kolejności od spodu
    cut: Cut = Cut()


@runtime_checkable
class Compositor(Protocol):
    """Odtwarzacz, który nakłada klipy na siebie i płynnie przechodzi między nimi (bajka/web_player.py).

    Silnik używa go zamiast `Player`, gdy odtwarzacz to umie; VLC gra klipy po kolei, bez warstw.
    """

    def play_shot(self, shot: Shot) -> None:
        """Odtwarza ujęcie i blokuje, aż klip będzie się kończył (następne ujęcie może na niego zachodzić)."""

    def loop_shot(self, shot: Shot) -> None:
        """Zapętla ujęcie w tle (pętla oczekiwania z warstwami) i wraca od razu."""


@dataclass(frozen=True)
class CutContext:
    """Co montażysta wie o przejściu: skąd, dokąd, co wybrał widz i jak się czuje."""

    from_scene: str
    to_scene: str
    edge: str  # "wybor" (po oknie wyboru), "dalej" (scena bez pytania), "reakcja" (pętla → klip reakcji)
    from_place: str = ""
    to_place: str = ""
    to_ending: bool = False
    hint: str = ""  # podpowiedź autora scenariusza (`transition` sceny docelowej)
    choice: str = ""  # nazwa wybranej opcji
    meaning: str = ""  # znaczenie wyboru (opis ze scenariusza)
    how: str = ""  # przycisk, glos, wiekszosc, domyslna
    transcript: str = ""  # co widz powiedział (przy odpowiedzi głosem)
    viewer: str = ""  # stan widza według tętna: pobudzenie, norma, znużenie; puste = brak tętna
    mood: str = ""  # nastrój odcinka ze scenariusza


@runtime_checkable
class Editor(Protocol):
    """Montażysta: przetwarza informacje o przejściu i decyduje, jak połączyć klipy (bajka/montage.py)."""

    def cut(self, context: CutContext) -> Cut:
        """Rodzaj i długość przejścia do kolejnego klipu."""


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
        """Zdarzenie odcinka: `scena`, `odniesienie`, `wersja`, `glosy`, `decyzja` albo `montaz` z danymi do pokazania."""

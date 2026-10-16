"""Tryb próbny --text: odpowiedzi z klawiatury, kwestie bohatera w konsoli (bez mikrofonu i głośnika)."""

from __future__ import annotations

from collections.abc import Callable


class ConsoleListener:
    def __init__(self, read: Callable[[str], str] = input) -> None:
        self._read = read

    def listen(self) -> str | None:
        try:
            return self._read("Dziecko> ").strip() or None
        except EOFError:
            return None


class ConsoleVoice:
    def __init__(self, write: Callable[[str], None] = print) -> None:
        self._write = write

    def say(self, text: str) -> None:
        self._write(f"Bohater: {text}")


class ConsoleMeter:
    """Krzykomierz do prób: głośność okrzyku widowni wpisujesz jako liczbę od 0 do 10."""

    def __init__(self, read: Callable[[str], str] = input) -> None:
        self._read = read

    def calibrate(self) -> None:
        pass

    def measure(self) -> float:
        try:
            answer = self._read("Głośność okrzyku 0-10> ").strip().replace(",", ".")
        except EOFError:
            return 0.0
        try:
            return max(0.0, float(answer or 0))
        except ValueError:
            return 0.0

    def winner(self, levels: dict[str, float]) -> str | None:
        ranked = sorted(levels.items(), key=lambda item: item[1], reverse=True)
        if not ranked or ranked[0][1] <= 0 or (len(ranked) > 1 and ranked[1][1] == ranked[0][1]):
            return None  # cisza albo remis
        return ranked[0][0]

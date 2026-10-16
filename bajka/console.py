"""Tryb próbny --text: odpowiedzi z klawiatury, kwestie bohatera w konsoli (bez Azure Speech)."""

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

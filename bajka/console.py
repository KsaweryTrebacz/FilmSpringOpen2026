"""Tryb próbny --text: odcinek w konsoli, bez wideo, mikrofonu i głośnika.

Klipy są tylko wypisywane, okno wyboru to ponumerowana lista: cyfra działa jak przycisk na pilocie,
tekst jak odpowiedź głosem (przechodzi przez rozpoznawanie intencji), pusta linia to cisza.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bajka.ports import Answer
from bajka.scenario import Scene


class ConsolePlayer:
    def __init__(self, write: Callable[[str], None] = print) -> None:
        self._write = write

    def play(self, clip: Path) -> None:
        self._write(f"[klip] {clip.name}")

    def loop(self, clip: Path) -> None:
        self._write(f"[w pętli] {clip.name}")

    def stop(self) -> None:
        pass


class ConsoleViewer:
    def __init__(self, read: Callable[[str], str] = input, write: Callable[[str], None] = print) -> None:
        self._read = read
        self._write = write

    def ask(self, scene: Scene, seconds: float) -> Answer:
        options = list(scene.choices.values())
        self._write(f"[okno wyboru, {seconds:.0f} s] {scene.question}")
        for number, choice in enumerate(options, start=1):
            self._write(f"  {number}. {choice.display_label}")
        try:
            typed = self._read("Widz (numer albo słowa)> ").strip()
        except EOFError:
            return Answer()
        if typed.isdigit() and 1 <= int(typed) <= len(options):
            return Answer(choice_id=options[int(typed) - 1].id)
        return Answer(transcript=typed or None)


class ConsoleVoice:
    def __init__(self, write: Callable[[str], None] = print) -> None:
        self._write = write

    def say(self, text: str) -> None:
        self._write(f"Postać: {text}")

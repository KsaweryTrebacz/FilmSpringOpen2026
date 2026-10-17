"""Tryb próbny --text: odcinek w konsoli, bez wideo, mikrofonu i głośnika.

Klipy są tylko wypisywane (z warstwami i przejściem wybranym przez montaż), okno wyboru to ponumerowana lista:
cyfra działa jak przycisk na pilocie, tekst jak odpowiedź głosem (przechodzi przez rozpoznawanie intencji),
pusta linia to cisza.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bajka.ports import Answer, Shot
from bajka.scenario import CUT, Scene


class ConsolePlayer:
    def __init__(self, write: Callable[[str], None] = print) -> None:
        self._write = write

    def play(self, clip: Path) -> None:
        self.play_shot(Shot(clip))

    def loop(self, clip: Path) -> None:
        self.loop_shot(Shot(clip))

    def play_shot(self, shot: Shot) -> None:
        self._write(f"[klip] {self._describe(shot)}")

    def loop_shot(self, shot: Shot) -> None:
        self._write(f"[w pętli] {self._describe(shot)}")

    @staticmethod
    def _describe(shot: Shot) -> str:
        details = []
        if shot.cut.transition != CUT:
            details.append(f"{shot.cut.transition} {shot.cut.seconds:.1f} s".replace(".", ","))
        if shot.layers:
            details.append("warstwy: " + ", ".join(layer.name for layer in shot.layers))
        return shot.clip.name + (f" ({'; '.join(details)})" if details else "")

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

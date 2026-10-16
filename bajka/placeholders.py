"""Klipy-zaślepki (kolorowe plansze), żeby uruchomić bajkę, zanim powstaną animacje.

Użycie: python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml   (wymaga ffmpeg w PATH)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from bajka.scenario import Scenario, load_scenario

COLORS = ("darkgreen", "midnightblue", "saddlebrown", "darkred", "indigo", "darkslategray")


def planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]:
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen i zapasy scen otwartych mają ton; pętle (oczekiwanie,
    rysowanie) i zapasy scen generowanych są ciche, bo grają w pętli pod narracją postaci."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        tracks = [(scene.clip, True), (scene.idle, False), (scene.drawing, False)]
        tracks += [(path, scene.kind != "generated") for path in scene.fallback_clips]
        for path, with_tone in tracks:
            if path is not None and path not in clips:  # wspólna pętla rysowania tylko raz
                clips[path] = (path, color, with_tone)
    return list(clips.values())


def ffmpeg_command(target: Path, color: str, seconds: float, with_tone: bool) -> list[str]:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=25:d={seconds}"]
    if with_tone:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac"]
    else:
        cmd += ["-an"]
    return cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.placeholders", description=__doc__)
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem")
    parser.add_argument("--seconds", type=float, default=4.0, help="długość każdego klipu")
    parser.add_argument("--force", action="store_true", help="nadpisz istniejące pliki")
    args = parser.parse_args(argv)
    if shutil.which("ffmpeg") is None:
        print("Nie znaleziono ffmpeg w PATH (Windows: winget install Gyan.FFmpeg)", file=sys.stderr)
        return 1
    for path, color, with_tone in planned_clips(load_scenario(args.scenario)):
        if path.exists() and not args.force:
            print(f"pomijam, plik istnieje: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(ffmpeg_command(path, color, args.seconds, with_tone), check=True)
        print(f"utworzono: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

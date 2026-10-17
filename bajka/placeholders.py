"""Klipy-zaślepki (kolorowe plansze z nazwą pliku), żeby uruchomić odcinek, zanim powstaną animacje.

Użycie: python -m bajka.placeholders scenarios/klub_ciekawskich.yaml   (wymaga ffmpeg w PATH)
Pliki .mp4 dostają H.264/AAC z indeksem na początku pliku (szybki start w przeglądarce, jak w serwisach
streamingowych), a pliki .webm — VP9/Opus (dla przeglądarek bez kodeka H.264, np. Chromium do testów).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from bajka.scenario import Scenario, load_scenario

COLORS = ("darkgreen", "midnightblue", "saddlebrown", "darkred", "indigo", "darkslategray")
# ffmpeg pisze na klipie tylko z podaną czcionką; pierwsza istniejąca z listy (Windows, Linux, macOS)
LABEL_FONTS = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
)


def planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]:
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen, ich wersje i reakcje mają ton, a pętle oczekiwania są ciche."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        tracks = [(scene.clip, True), (scene.idle, False)] + [(path, True) for path in scene.variants.values()]
        tracks += [(choice.reaction, True) for choice in scene.choices.values()]
        for path, with_tone in tracks:
            if path is not None and path not in clips:  # ten sam plik w kilku scenach tylko raz
                clips[path] = (path, color, with_tone)
    return list(clips.values())


def ffmpeg_command(
    target: Path, color: str, seconds: float, with_tone: bool, label: str = "", font: Path | None = None
) -> list[str]:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=25:d={seconds}"]
    webm = target.suffix.lower() == ".webm"
    if with_tone:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "libopus" if webm else "aac"]
    else:
        cmd += ["-an"]
    if label and font is not None:  # nazwa pliku na planszy: na próbie widać, która scena i wersja gra
        fontfile = str(font).replace("\\", "/").replace(":", "\\:")
        text = label.replace("'", "").replace(":", "\\:")
        position = "fontsize=56:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
        cmd += ["-vf", f"drawtext=fontfile='{fontfile}':text='{text}':{position}"]
    if webm:
        return cmd + ["-c:v", "libvpx-vp9", "-b:v", "300k", "-deadline", "realtime", "-pix_fmt", "yuv420p", str(target)]
    return cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.placeholders", description=__doc__)
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem")
    parser.add_argument("--seconds", type=float, default=4.0, help="długość każdego klipu")
    parser.add_argument("--force", action="store_true", help="nadpisz istniejące pliki")
    args = parser.parse_args(argv)
    if shutil.which("ffmpeg") is None:
        print("Nie znaleziono ffmpeg w PATH (Windows: winget install Gyan.FFmpeg)", file=sys.stderr)
        return 1
    font = next((path for path in LABEL_FONTS if path.is_file()), None)
    for path, color, with_tone in planned_clips(load_scenario(args.scenario)):
        if path.exists() and not args.force:
            print(f"pomijam, plik istnieje: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(ffmpeg_command(path, color, args.seconds, with_tone, path.stem, font), check=True)
        print(f"utworzono: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

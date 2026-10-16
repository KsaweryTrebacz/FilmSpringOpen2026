"""Ruch kamery dla ilustracji: z obrazu PNG robi krótki, cichy klip MP4 (efekt Kena Burnsa) przez ffmpeg.

Moduł spełnia kontrakt `bajka.ports.Animator`. Wymaga ffmpeg w PATH.
Podgląd: python -m bajka.motion obraz.png [--move zoom_in|pan] [--seconds 6]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bajka.config import ConfigError, get_float, load_env

MOVES = ("zoom_in", "pan")
FPS = 25
WIDTH, HEIGHT = 1280, 720
MAX_ZOOM = 1.15


class MotionError(RuntimeError):
    """ffmpeg nie zrobił klipu: brak programu albo zły plik wejściowy."""


@dataclass(frozen=True)
class MotionSettings:
    seconds: float = 6.0

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> MotionSettings:
        return cls(seconds=get_float(env, "BAJKA_MOTION_SECONDS", cls.seconds))


def ffmpeg_command(image: Path, target: Path, seconds: float, move: str = "zoom_in") -> list[str]:
    frames = max(1, round(seconds * FPS))
    if move == "zoom_in":
        zoom = f"min(zoom+{(MAX_ZOOM - 1) / frames:.6f},{MAX_ZOOM})"
        x = "iw/2-(iw/zoom/2)"
    elif move == "pan":
        zoom = f"{MAX_ZOOM}"
        x = f"(iw-iw/zoom)*on/{frames}"
    else:
        raise ValueError(f"nieznany ruch kamery {move!r}, dostępne: {', '.join(MOVES)}")
    # Kadr 16:9 ze środka ilustracji, powiększony 2x, żeby zoompan nie drgał na zaokrągleniach.
    video_filter = (
        f"crop=iw:min(ih\\,iw*9/16),scale={2 * WIDTH}:{2 * HEIGHT},"
        f"zoompan=z='{zoom}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        "format=yuv420p"
    )
    return [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(image), "-vf", video_filter,
        "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-an", str(target),
    ]  # fmt: skip


class FfmpegAnimator:
    def __init__(
        self,
        out_dir: Path,
        seconds: float = 6.0,
        move: str = "zoom_in",
        run: Callable[..., Any] = subprocess.run,
    ) -> None:
        self._out_dir = Path(out_dir)
        self._seconds = seconds
        self._move = move
        self._run = run

    @classmethod
    def from_settings(cls, settings: MotionSettings, out_dir: Path) -> FfmpegAnimator:
        return cls(out_dir, seconds=settings.seconds)

    def animate(self, image: Path) -> Path:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        target = self._out_dir / f"{Path(image).stem}.mp4"
        try:
            self._run(
                ffmpeg_command(Path(image), target, self._seconds, self._move),
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise MotionError("Nie znaleziono ffmpeg w PATH (Windows: winget install --id Gyan.FFmpeg -e)") from exc
        except subprocess.CalledProcessError as exc:
            raise MotionError(f"ffmpeg: {(exc.stderr or '').strip()}") from exc
        return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.motion", description="Klip z ruchem kamery z ilustracji.")
    parser.add_argument("image", type=Path, help="ilustracja PNG albo JPG")
    parser.add_argument("--move", choices=MOVES, default="zoom_in", help="ruch kamery (domyślnie zoom_in)")
    parser.add_argument("--seconds", type=float, help="długość klipu (domyślnie BAJKA_MOTION_SECONDS albo 6)")
    parser.add_argument("--out", type=Path, help="katalog na klip (domyślnie obok ilustracji)")
    args = parser.parse_args(argv)
    try:
        seconds = args.seconds or MotionSettings.from_env(load_env()).seconds
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    animator = FfmpegAnimator(args.out or args.image.parent, seconds=seconds, move=args.move)
    started = time.perf_counter()
    try:
        clip = animator.animate(args.image)
    except MotionError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Klip: {clip} ({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

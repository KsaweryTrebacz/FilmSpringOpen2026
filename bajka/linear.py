"""Wersja liniowa odcinka: zwykły film z tych samych klipów, dla serwisów i telewizorów bez interakcji.

Ścieżka biegnie od sceny startowej przez wybory domyślne do zakończenia. Po każdym pytaniu pętla oczekiwania
daje chwilę na odpowiedź widza przed ekranem, a potem postać wybiera sama: mówi `fallback` i gra klip reakcji
albo — gdy reakcji nie nagrano — kwestię `reply` widać w napisach na pętli. Kwestie, których nie ma w klipach,
trafiają do pliku napisów .srt obok filmu (w produkcji: nagrać je aktorsko i wmontować).

Użycie: python -m bajka.linear SCENARIUSZ [--out odcinek_liniowy.mp4] [--plan]   (wymaga ffmpeg i ffprobe)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bajka.engine import DEFAULT_FALLBACK
from bajka.scenario import Scenario, ScenarioError, load_scenario, missing_media

PAUSE_SECONDS = 3.0  # cisza po pytaniu: widz przed ekranem zdąży odpowiedzieć na głos
SIZE, FPS, RATE = (1280, 720), 25, 48000  # wspólny format odcinków przed sklejeniem


@dataclass(frozen=True)
class Segment:
    clip: Path
    seconds: float | None = None  # None = cały klip; liczba = pętla przycięta do tylu sekund
    line: str = ""  # kwestia na żywo z interaktywnej wersji, tu w napisach


def reading_seconds(text: str) -> float:
    """Ile sekund napis musi wisieć na ekranie (to samo tempo co w odtwarzaczu w przeglądarce)."""
    return max(3.0, 1.2 + len(text) * 0.065)


def default_path(scenario: Scenario) -> list[Segment]:
    """Kolejne fragmenty filmu liniowego: klipy scen, pauzy na pętlach i reakcje na wybory domyślne."""
    segments: list[Segment] = []
    scene, visited = scenario.scene(scenario.start), set()
    while True:
        if scene.id in visited:
            raise ScenarioError(f"wybory domyślne krążą w kółko (scena '{scene.id}'), wersja liniowa nie ma końca")
        visited.add(scene.id)
        segments.append(Segment(scene.clip))
        if scene.is_ending:
            return segments
        choice = scene.choices[scene.default]
        fallback = scene.fallback or DEFAULT_FALLBACK
        segments.append(Segment(scene.idle, PAUSE_SECONDS))
        if choice.reaction is not None:
            segments += [Segment(scene.idle, reading_seconds(fallback), fallback), Segment(choice.reaction)]
        else:
            line = f"{fallback} {choice.reply}"
            segments.append(Segment(scene.idle, reading_seconds(line), line))
        scene = scenario.scene(choice.next)


def probe(path: Path) -> tuple[float, bool]:
    """Długość klipu w sekundach i czy ma ścieżkę dźwiękową."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    info = json.loads(result.stdout)
    has_audio = any(stream.get("codec_type") == "audio" for stream in info.get("streams", []))
    return float(info["format"]["duration"]), has_audio


def segment_command(segment: Segment, has_audio: bool, target: Path) -> list[str]:
    """Jeden fragment w wspólnym formacie (obraz, klatki, dźwięk), żeby dało się je skleić bez ponownego kodowania."""
    loop = ["-stream_loop", "-1"] if segment.seconds is not None else []
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *loop, "-i", str(segment.clip)]
    if not has_audio:
        cmd += ["-f", "lavfi", "-i", f"anullsrc=r={RATE}:cl=stereo"]
    width, height = SIZE
    video = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
             f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={FPS},format=yuv420p")  # fmt: skip
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0", "-vf", video]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-ar", str(RATE), "-ac", "2"]
    if segment.seconds is not None:
        cmd += ["-t", f"{segment.seconds:.3f}"]
    elif not has_audio:
        cmd += ["-shortest"]
    return cmd + [str(target)]


def subtitles(segments: list[Segment], durations: list[float]) -> str:
    """Plik SRT z kwestiami mówionymi na żywo, zsynchronizowany z fragmentami filmu."""
    entries, start = [], 0.0
    for segment, seconds in zip(segments, durations):
        if segment.line:
            entries.append(f"{len(entries) + 1}\n{_timestamp(start)} --> {_timestamp(start + seconds)}\n{segment.line}\n")
        start += seconds
    return "\n".join(entries)


def _timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build(segments: list[Segment], out: Path) -> Path:
    """Skleja film liniowy i zapisuje obok napisy .srt; zwraca ścieżkę napisów."""
    durations: list[float] = []
    with tempfile.TemporaryDirectory(prefix="bajka-linear-") as work:
        parts = []
        for index, segment in enumerate(segments):
            length, has_audio = probe(segment.clip)
            part = Path(work) / f"{index:03d}.mp4"
            subprocess.run(segment_command(segment, has_audio, part), check=True)
            parts.append(part)
            durations.append(segment.seconds if segment.seconds is not None else length)
        listing = Path(work) / "lista.txt"
        listing.write_text("".join(f"file '{part.as_posix()}'\n" for part in parts), encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-c", "copy", "-movflags", "+faststart", str(out)],
            check=True,
        )  # fmt: skip
    srt = out.with_suffix(".srt")
    srt.write_text(subtitles(segments, durations), encoding="utf-8")
    return srt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.linear", description="Wersja liniowa odcinka (bez okien wyboru).")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem odcinka")
    parser.add_argument("--out", type=Path, help="plik wynikowy (domyślnie: obok scenariusza, *_liniowy.mp4)")
    parser.add_argument("--plan", action="store_true", help="tylko wypisz plan montażu, bez ffmpeg")
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        segments = default_path(scenario)
    except (ScenarioError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.plan:
        for segment in segments:
            length = "cały klip" if segment.seconds is None else f"{segment.seconds:.1f} s"
            print(f"{segment.clip.name:32} {length:10} {segment.line}")
        return 0
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("Nie znaleziono ffmpeg i ffprobe w PATH (Windows: winget install Gyan.FFmpeg)", file=sys.stderr)
        return 1
    missing = [path for path in missing_media(scenario) if path in {s.clip for s in segments}]
    if missing:
        print(f"Brak plików wideo: {', '.join(map(str, missing))} (zastępcze: python -m bajka.placeholders)", file=sys.stderr)
        return 2
    out = args.out or args.scenario.with_name(f"{args.scenario.stem}_liniowy.mp4")
    srt = build(segments, out)
    print(f"Wersja liniowa: {out}\nNapisy z kwestiami na żywo: {srt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

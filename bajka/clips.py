"""Klipy z generatora wideo → klipy odcinka: nazwy scen, wspólny format, płynne pętle.

Klipy z generatora (np. folder `download/`) mają własne nazwy, długość 8–10 s i dźwięk generatora. Plik mapy
(`download/klipy.yaml`) mówi, który klip gra którą scenę. Narzędzie zapisuje je pod ścieżkami ze scenariusza:
H.264/AAC z indeksem na początku pliku (szybki start w przeglądarce), 1280×720, 24 kl./s. Pętle oczekiwania dostają
płynny szew (koniec klipu przenika w jego początek, więc zapętlenie nie skacze) i ściszony dźwięk (wtedy słucha
mikrofon). Warstwy (`.webm` z przezroczystością) są kopiowane bez zmian. Brakujące sceny uzupełnia potem
`python -m bajka.placeholders` (tworzy tylko pliki, których nie ma).

Użycie: python -m bajka.clips download/klipy.yaml [--force] [--plan]   (wymaga ffmpeg i ffprobe)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from bajka.linear import probe
from bajka.scenario import ScenarioError, load_scenario, media_files

SIZE, FPS = (1280, 720), 24
SEAM_SECONDS = 1.0  # tyle końca pętli przenika w jej początek
LOOP_VOLUME = 0.25  # dźwięk pętli oczekiwania ok. 12 dB ciszej


@dataclass(frozen=True)
class Assignment:
    source: Path  # klip z generatora
    target: Path  # ścieżka ze scenariusza
    loop: bool  # pętla oczekiwania (`idle` sceny): płynny szew i cichy dźwięk


def read_map(path: Path) -> list[Assignment]:
    """Mapa klipów: `scenario` (ścieżka względem mapy) i `clips` — nazwa pliku sceny → klip z generatora."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), dict) or not data.get("scenario"):
        raise ScenarioError(f"{path}: mapa potrzebuje pól 'scenario' i 'clips' (nazwa pliku sceny: klip)")
    scenario = load_scenario(path.parent / data["scenario"])
    by_name = {media.name: media for media in media_files(scenario)}
    loops = {scene.idle.name for scene in scenario.scenes.values() if scene.idle is not None}
    assignments = []
    for name, source in data["clips"].items():
        if name not in by_name:
            raise ScenarioError(f"{path}: scenariusz nie ma pliku {name!r} (sprawdź nazwy klipów w YAML odcinka)")
        assignments.append(Assignment(path.parent / str(source), by_name[name], name in loops))
    return assignments


def convert_command(assignment: Assignment, seconds: float, has_audio: bool) -> list[str]:
    width, height = SIZE
    fit = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={FPS}"
    seamed = assignment.loop and seconds > 3 * SEAM_SECONDS
    length = seconds - SEAM_SECONDS if seamed else seconds  # szew zjada sekundę: koniec leży na początku
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(assignment.source)]
    if not has_audio:
        cmd += ["-f", "lavfi", "-t", f"{length:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    elif seamed:  # drugi odczyt klipu: acrossfade nie dostaje dźwięku z dwóch gałęzi asplit jednego wejścia
        cmd += ["-i", str(assignment.source)]
    if seamed:
        seam, offset = SEAM_SECONDS, seconds - 2 * SEAM_SECONDS
        graph = [
            f"[0:v]{fit},format=yuv420p,split[a][b]",
            f"[a]trim=start={seam},setpts=PTS-STARTPTS[tail]",
            f"[b]trim=end={seam},setpts=PTS-STARTPTS[head]",
            f"[tail][head]xfade=transition=fade:duration={seam}:offset={offset:.3f}[v]",
        ]
        if has_audio:
            graph += [
                f"[0:a]aresample=48000,atrim=start={seam},asetpts=PTS-STARTPTS[atail]",
                f"[1:a]aresample=48000,atrim=end={seam},asetpts=PTS-STARTPTS[ahead]",
                f"[atail][ahead]acrossfade=d={seam},volume={LOOP_VOLUME}[s]",
            ]
        else:
            graph.append("[1:a]anull[s]")
    else:
        graph = [f"[0:v]{fit},format=yuv420p[v]", f"[{0 if has_audio else 1}:a]aresample=48000[s]"]
    cmd += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[s]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k"]
    return cmd + ["-movflags", "+faststart", str(assignment.target)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.clips", description="Klipy z generatora → klipy odcinka.")
    parser.add_argument("mapping", type=Path, help="mapa klipów, np. download/klipy.yaml")
    parser.add_argument("--force", action="store_true", help="nadpisz klipy, które już są w odcinku")
    parser.add_argument("--plan", action="store_true", help="tylko wypisz, który klip gra którą scenę")
    args = parser.parse_args(argv)
    try:
        assignments = read_map(args.mapping)
    except (ScenarioError, OSError, yaml.YAMLError) as exc:
        print(exc, file=sys.stderr)
        return 2
    missing = [a.source for a in assignments if not a.source.is_file()]
    if missing:
        print(f"Brak klipów z generatora: {', '.join(map(str, missing))}", file=sys.stderr)
        return 2
    if args.plan:
        for a in assignments:
            print(f"{a.target.name:28} <- {a.source.name}{'  (pętla: płynny szew, cichszy dźwięk)' if a.loop else ''}")
        return 0
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("Nie znaleziono ffmpeg i ffprobe w PATH (Windows: winget install Gyan.FFmpeg)", file=sys.stderr)
        return 1
    for a in assignments:
        if a.target.exists() and not args.force:
            print(f"pomijam, plik istnieje: {a.target} (--force nadpisze)")
            continue
        a.target.parent.mkdir(parents=True, exist_ok=True)
        if a.target.suffix.lower() == ".webm":  # warstwa z przezroczystością: kopia, bo przekodowanie zgubiłoby alfę
            shutil.copyfile(a.source, a.target)
            print(f"{a.target.name} ← {a.source.name} (warstwa)")
            continue
        seconds, has_audio = probe(a.source)
        subprocess.run(convert_command(a, seconds, has_audio), check=True)
        print(f"{a.target.name} ← {a.source.name}")
    print("Brakujące sceny uzupełnisz zaślepkami: python -m bajka.placeholders SCENARIUSZ")
    return 0


if __name__ == "__main__":
    sys.exit(main())

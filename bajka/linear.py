"""Wersja liniowa odcinka: zwykły film z tych samych klipów, dla serwisów i telewizorów bez interakcji.

Ścieżka biegnie od sceny startowej przez wybory domyślne do zakończenia, także przez sceny bez pytania (`next`).
Po każdym pytaniu pętla oczekiwania daje chwilę na odpowiedź widza przed ekranem, a potem postać wybiera sama:
mówi `fallback` i gra klip reakcji albo — gdy reakcji nie nagrano — kwestię `reply` widać w napisach na pętli.
Warstwy wybrane domyślnie są nakładane na klipy tak jak w odtwarzaczu, a klipy łączą przejścia z reguł montażu
(`bajka/montage.py`: przenikanie, przetarcie, zaciemnienie, rozjaśnienie albo cięcie). Kwestie, których nie ma
w klipach, trafiają do pliku napisów .srt obok filmu (w produkcji: nagrać je aktorsko i wmontować).

Użycie: python -m bajka.linear SCENARIUSZ [--out odcinek_liniowy.mp4] [--plan]   (wymaga ffmpeg i ffprobe)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from bajka.engine import DEFAULT_FALLBACK
from bajka.montage import RuleEditor, context_for, describe_cut, loop_cut
from bajka.ports import Cut
from bajka.scenario import (
    CUT,
    DISSOLVE,
    FADE_BLACK,
    FADE_WHITE,
    WIPE,
    Scenario,
    ScenarioError,
    load_scenario,
    missing_media,
)

PAUSE_SECONDS = 3.0  # cisza po pytaniu: widz przed ekranem zdąży odpowiedzieć na głos
SIZE, FPS, RATE = (1280, 720), 25, 48000  # wspólny format fragmentów przed sklejeniem
FRAME = 1 / FPS  # cięcie to przejście o długości jednej klatki
XFADE = {CUT: "fade", DISSOLVE: "fade", FADE_BLACK: "fadeblack", FADE_WHITE: "fadewhite", WIPE: "wiperight"}


@dataclass(frozen=True)
class Segment:
    clip: Path
    seconds: float | None = None  # None = cały klip; liczba = pętla przycięta do tylu sekund
    line: str = ""  # kwestia na żywo z interaktywnej wersji, tu w napisach
    line_at: float = 0.0  # po ilu sekundach fragmentu pojawia się napis
    layers: tuple[Path, ...] = ()  # warstwy wybrane domyślnie, nakładane na klip
    cut: Cut = field(default_factory=Cut)  # jak fragment wchodzi na ekran


def reading_seconds(text: str) -> float:
    """Ile sekund napis musi wisieć na ekranie (to samo tempo co w odtwarzaczu w przeglądarce)."""
    return max(3.0, 1.2 + len(text) * 0.065)


def default_path(scenario: Scenario) -> list[Segment]:
    """Kolejne fragmenty filmu liniowego: klipy scen, pauzy na pętlach, reakcje i przejścia z reguł montażu."""
    rules = RuleEditor()
    into_loop = loop_cut(scenario)
    segments: list[Segment] = []
    layers: dict[str, Path] = {}
    scene, visited, entering = scenario.scene(scenario.start), set(), Cut()

    def shown(here):
        return tuple(layers[slot] for slot in here.layers if slot in layers)

    while True:
        if scene.id in visited:
            raise ScenarioError(f"wybory domyślne krążą w kółko (scena '{scene.id}'), wersja liniowa nie ma końca")
        visited.add(scene.id)
        segments.append(Segment(scene.clip, layers=shown(scene), cut=entering))
        if scene.is_ending:
            return segments
        if not scene.choices:  # scena bez pytania przechodzi dalej sama
            entering = rules.cut(context_for(scenario, scene, scene.next, "dalej"))
            scene = scenario.scene(scene.next)
            continue
        choice = scene.choices[scene.default]
        fallback = scene.fallback or DEFAULT_FALLBACK
        if choice.layer is not None:
            layers[choice.slot] = choice.layer
        if choice.reaction is not None:
            segments.append(Segment(scene.idle, PAUSE_SECONDS + reading_seconds(fallback), fallback, PAUSE_SECONDS,
                                    shown(scene), into_loop))  # fmt: skip
            reaction = rules.cut(context_for(scenario, scene, scene.id, "reakcja"))
            segments.append(Segment(choice.reaction, layers=shown(scene), cut=reaction))
        else:
            line = f"{fallback} {choice.reply}"
            segments.append(Segment(scene.idle, PAUSE_SECONDS + reading_seconds(line), line, PAUSE_SECONDS, shown(scene),
                                    into_loop))  # fmt: skip
        context = context_for(scenario, scene, choice.next, "wybor", choice=choice.display_label,
                              meaning=choice.description, how="domyslna")  # fmt: skip
        entering = rules.cut(context)
        scene = scenario.scene(choice.next)


def probe(path: Path) -> tuple[float, bool]:
    """Długość obrazu klipu w sekundach i czy klip ma ścieżkę dźwiękową.

    Liczy się obraz: przejście musi zacząć się przed ostatnią klatką, a dźwięk bywa o kilka milisekund dłuższy.
    """
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    video = next((s for s in streams if s.get("codec_type") == "video" and s.get("duration")), None)
    return float(video["duration"] if video else info["format"]["duration"]), has_audio


def segment_command(segment: Segment, has_audio: bool, target: Path, clip_seconds: float) -> list[str]:
    """Jeden fragment we wspólnym formacie, z nałożonymi warstwami (przezroczystość WebM VP9 albo MOV).

    Fragment trwa dokładnie tyle, ile obraz klipu (`clip_seconds`) albo pętla (`segment.seconds`); dźwięk
    dopełniamy ciszą do tej samej długości, żeby kolejne przejścia trafiały w obraz i dźwięk naraz.
    """
    width, height = SIZE
    fit = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    loop = ["-stream_loop", "-1"] if segment.seconds is not None else []
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *loop, "-i", str(segment.clip)]
    audio = "0:a:0"
    if not has_audio:
        cmd += ["-f", "lavfi", "-i", f"anullsrc=r={RATE}:cl=stereo"]
        audio = "1:a:0"
    graph = [f"[0:v]{fit},fps={FPS}[b0]"]
    first_layer = 1 if has_audio else 2
    for index, layer in enumerate(segment.layers):
        decoder = ["-c:v", "libvpx-vp9"] if layer.suffix.lower() == ".webm" else []  # bez tego VP9 gubi alfę
        cmd += ["-stream_loop", "-1", *decoder, "-i", str(layer)]
        graph.append(f"[{first_layer + index}:v]format=yuva420p,{fit}:color=black@0,fps={FPS}[l{index}]")
        graph.append(f"[b{index}][l{index}]overlay=shortest=1:format=auto[b{index + 1}]")
    graph.append(f"[b{len(segment.layers)}]format=yuv420p[v]")
    graph.append(f"[{audio}]aresample={RATE},apad[a]")  # dźwięk dokładnie tak długi jak obraz
    cmd += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-ar", str(RATE), "-ac", "2"]
    length = segment.seconds if segment.seconds is not None else clip_seconds
    return cmd + ["-t", f"{length:.3f}", str(target)]


def timeline(segments: list[Segment], durations: list[float]) -> tuple[list[float], list[float]]:
    """Początki fragmentów w filmie i długości przejść: kolejny fragment zachodzi na koniec poprzedniego."""
    starts, overlaps, length = [0.0], [0.0], durations[0] if durations else 0.0
    for segment, seconds in zip(segments[1:], durations[1:]):
        overlap = FRAME if segment.cut.transition == CUT else segment.cut.seconds
        overlap = max(FRAME, min(overlap, seconds - FRAME, length - FRAME))
        starts.append(length - overlap)
        overlaps.append(overlap)
        length += seconds - overlap
    return starts, overlaps


def join_command(parts: list[Path], segments: list[Segment], durations: list[float], target: Path) -> list[str]:
    """Skleja fragmenty przejściami xfade (obraz) i acrossfade (dźwięk) według decyzji montażu."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for part in parts:
        cmd += ["-i", str(part)]
    if len(parts) == 1:
        return cmd + ["-c", "copy", "-movflags", "+faststart", str(target)]
    starts, overlaps = timeline(segments, durations)
    graph, video, sound = [], "[0:v]", "[0:a]"
    for index in range(1, len(parts)):
        kind = XFADE[segments[index].cut.transition]
        graph.append(f"{video}[{index}:v]xfade=transition={kind}:duration={overlaps[index]:.3f}:"
                     f"offset={starts[index]:.3f}[v{index}]")  # fmt: skip
        graph.append(f"{sound}[{index}:a]acrossfade=d={overlaps[index]:.3f}[a{index}]")
        video, sound = f"[v{index}]", f"[a{index}]"
    cmd += ["-filter_complex", ";".join(graph), "-map", video, "-map", sound]
    return cmd + ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-movflags", "+faststart", str(target)]


def subtitles(segments: list[Segment], durations: list[float]) -> str:
    """Plik SRT z kwestiami mówionymi na żywo, zsynchronizowany z fragmentami filmu i przejściami."""
    starts, _ = timeline(segments, durations)
    entries = []
    for segment, start, seconds in zip(segments, starts, durations):
        if segment.line:
            begin, end = start + segment.line_at, start + seconds
            entries.append(f"{len(entries) + 1}\n{_timestamp(begin)} --> {_timestamp(end)}\n{segment.line}\n")
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
            clip_seconds, has_audio = probe(segment.clip)
            part = Path(work) / f"{index:03d}.mp4"
            subprocess.run(segment_command(segment, has_audio, part, clip_seconds), check=True)
            parts.append(part)
            durations.append(probe(part)[0])
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(join_command(parts, segments, durations, out), check=True)
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
            name = segment.clip.name + (" + " + ", ".join(p.name for p in segment.layers) if segment.layers else "")
            print(f"{describe_cut(segment.cut):18} {name:52} {length:10} {segment.line}")
        return 0
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("Nie znaleziono ffmpeg i ffprobe w PATH (Windows: winget install Gyan.FFmpeg)", file=sys.stderr)
        return 1
    needed = {s.clip for s in segments} | {layer for s in segments for layer in s.layers}
    missing = [path for path in missing_media(scenario) if path in needed]
    if missing:
        print(f"Brak plików wideo: {', '.join(map(str, missing))} (zastępcze: python -m bajka.placeholders)", file=sys.stderr)
        return 2
    out = args.out or args.scenario.with_name(f"{args.scenario.stem}_liniowy.mp4")
    srt = build(segments, out)
    print(f"Wersja liniowa: {out}\nNapisy z kwestiami na żywo: {srt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Obraz na żywo — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dziecko odpowiada na pytanie otwarte, a bajka w ciągu kilkunastu sekund pokazuje jego pomysł jako ilustrację z ruchem kamery. W wersji P2 dochodzą sceny rysowane w tle z zapamiętanych pomysłów.

**Architecture:** Trzy nowe moduły za kontraktami w `bajka/ports.py`:
- `imagine.py`: pomysł dziecka → kwestia postaci + opis obrazu (Azure OpenAI),
- `illustrate.py`: opis → PNG (Azure AI Foundry, gpt-image),
- `motion.py`: PNG → MP4 (ffmpeg).

Scenariusz dostaje sceny `open` (P1) i `generated` (P2). Silnik rysuje w puli wątków z limitem czasu i zawsze ma klip zapasowy.

**Tech Stack:** Python 3.11+ (testowane na 3.13), openai 3.31 (`AzureOpenAI`: chat i images), ffmpeg 8 (zoompan), PyYAML, pytest. Nowe zależności pip nie są potrzebne.

## Źródła i odstępstwa od specu

Projekt: [2026-10-16-flow-filmu-design.md](../specs/2026-10-16-flow-filmu-design.md). Odstępstwa wynikają z dokumentacji Microsoftu sprawdzonej przy pisaniu planu:

1. **Domyślny model obrazu to `gpt-image-2`**, a nie gpt-image-1.5.
   - gpt-image-1.5 jest w ograniczonym podglądzie (trzeba złożyć wniosek o dostęp), gpt-image-2 jest ogólnie dostępny.
   - Kod jest ten sam, bo nazwę wdrożenia ustawia się w `.env`.
2. **FLUX.2 nie jest w tym planie.** Korzysta z osobnego API Black Forest Labs (`/providers/blackforestlabs/...`), a nie z API obrazów OpenAI. W dniu 1 porównujemy go w playgroundzie Foundry (Task 3). Moduł `FluxIllustrator` powstanie tylko wtedy, gdy FLUX wygra.
3. **`imagine.py` ma własne `ImagineSettings`** zamiast importować `LlmSettings` z `intent.py` (zasada 4 w [podziale pracy](../../PODZIAL_PRACY.md)). Czyta te same zmienne `AZURE_OPENAI_*`.
4. **Stała kwestia awaryjna** brzmi „Zobacz, co mam w wyobraźni!”. Spec proponował „…wyobraziłam”, ale forma neutralna pasuje do każdej postaci.
5. **Do prób mechaniki** służy przykładowy scenariusz [`scenarios/rysowanie_na_zywo.yaml`](../../../scenarios/rysowanie_na_zywo.yaml). Sceny otwarte w prawdziwej bajce dodaje jej autor.
6. **P3 (napisy jako początek) nie jest w tym planie.**

Do pamiętania z dokumentacji Azure:
- generowanie trwa zwykle 10–30 s,
- domyślny limit to 5 obrazów na minutę na wdrożenie,
- **fotorealistyczne obrazy dzieci są domyślnie blokowane** (dlatego prompt zawsze zawiera „not photorealistic”).

## Global Constraints

- Python `>=3.11`, Windows 11, komendy w PowerShellu, ffmpeg w `PATH` (`winget install --id Gyan.FFmpeg -e`).
- Bez nowych zależności pip.
- Moduły `imagine.py`, `illustrate.py` i `motion.py` importują tylko `bajka.config`, `bajka.ports` i `bajka.scenario`.
- **Pliki wspólne:** `bajka/ports.py`, `bajka/scenario.py`, `bajka/engine.py`, `bajka/app.py`, `bajka/placeholders.py` (B), `.env.example`, `README.md`, `docs/PODZIAL_PRACY.md`.
  - Zmieniamy je **punktowo** (bloki „Zamień → na” poniżej), nie podmieniamy całych plików, bo inne osoby równolegle je rozwijają.
  - Jeśli blok „Zamień” nie pasuje, bo ktoś zmienił ten fragment, nanieś zmianę ręcznie z zachowaniem cudzego kodu.
- **Testy:** bez sieci, mikrofonu i VLC. Dwa testy `motion` są pomijane bez ffmpeg w `PATH`.
- **Język:** kod po angielsku; logi, komunikaty i kwestie po polsku; opisy obrazów (`image_prompt`, `idea`, `style`) po angielsku; do dziecka bez form zależnych od płci.
- **Wartości domyślne:**

  | Ustawienie | Wartość |
  |---|---|
  | `AZURE_IMAGE_API_VERSION` | `2025-04-01-preview` |
  | `BAJKA_IMAGE_SIZE` | `1536x1024` |
  | `BAJKA_IMAGE_QUALITY` | `medium` |
  | `BAJKA_IMAGE_TIMEOUT_S` | `25` |
  | `BAJKA_MOTION_SECONDS` | `6` |
  | Wynik ruchu kamery | 1280×720, 25 kl./s, bez dźwięku |
  | `max_retries` | 0 na żywo, 3 przy produkcji (`--batch`) |

- **Prywatność:** nie zapisujemy nagrań głosu. Ilustracje trafiają do `%TEMP%/bajka/seans_*`, a każdy start aplikacji usuwa poprzednie seanse.
- **Git:** wszystko na `main`. Przed commitem `git pull --rebase origin main` i `python -m pytest`, po każdym zadaniu `git push origin main`.

## Struktura plików

| Plik | Rola | Task |
|---|---|---|
| `bajka/ports.py` (wspólny) | + `Vision`, `Imaginer`, `Illustrator`, `Animator` | 1 |
| `bajka/motion.py` | `FfmpegAnimator`, `MotionSettings`, `MotionError`, `ffmpeg_command`, demo | 1 |
| `bajka/scenario.py` (wspólny) | + `style`, `references`, sceny `open`, `fill_prompt`, walidacja szablonów; w P2 sceny `generated` | 2, 7 |
| `scenarios/rysowanie_na_zywo.yaml` | przykład mechaniki | 2, 7 |
| `bajka/illustrate.py` | `AzureIllustrator`, `ImageSettings`, `build_prompt`, `load_shots`, demo z pomiarem i `--batch` | 3 |
| `scenarios/pomiar_obrazow.yaml`, `scenarios/karta_postaci.yaml` | ujęcia do pomiaru dnia 1 i karty postaci | 3 |
| `bajka/imagine.py` | `AzureImaginer`, `ImagineSettings`, `parse_vision`, demo | 4 |
| `bajka/engine.py` (wspólny) | sceny `open`; w P2 sceny `generated` i rysowanie w tle | 5, 7 |
| `bajka/app.py` (wspólny) | `LiveImages`, `prepare_session_dir`, `build_live_images` | 6 |
| `bajka/placeholders.py` (B) | zaślepki pętli „rysuje” i klipów zapasowych | 6 |
| `tests/live_fakes.py` | atrapy modułów do testów silnika | 5 |

## Kolejność i praca równoległa

- **Taski 1–4 są od siebie niezależne**, z jednym wyjątkiem: Task 3 korzysta z pól `style` i `references` z Taska 2. Dwie osoby mogą więc robić równolegle 1+3 i 2+4. Dopilnujcie tylko, żeby Task 2 wszedł na `main` przed testami Taska 3.
- **Task 5** wymaga Tasków 1 i 2, **Task 6** wymaga 3, 4 i 5, a **Task 7 (P2)** wymaga 6.
- **Pomiar dnia 1** (Task 3, krok 6) robimy, jak tylko mentorzy dadzą dostęp do Azure AI Foundry. Od jego wyniku zależą ustawienia jakości i rozmiaru.

---

### Task 1: Kontrakty i ruch kamery

**Files:**
- Modify: `bajka/ports.py` (dopisanie na końcu)
- Create: `bajka/motion.py`
- Test: `tests/test_motion.py`

**Interfaces:**
- Consumes: `bajka.config.get_float`, `load_env`, `ConfigError`.
- Produces:
  - `Vision(reply: str, idea: str)`,
  - protokoły `Imaginer.imagine(scene, transcript) -> Vision`, `Illustrator.draw(prompt: str) -> Path`, `Animator.animate(image: Path) -> Path` (wszystkie `@runtime_checkable`),
  - `FfmpegAnimator(out_dir: Path, seconds=6.0, move="zoom_in", run=subprocess.run)` z `from_settings(settings, out_dir)` i `animate(image) -> Path` (zwraca `out_dir / f"{image.stem}.mp4"`),
  - `MotionSettings.from_env(env)`, `MotionError`, `ffmpeg_command(image, target, seconds, move) -> list[str]`, `MOVES = ("zoom_in", "pan")`.

- [ ] **Step 1: Napisz testy ruchu kamery**

<!-- file: tests/test_motion.py -->
```python
import shutil
import subprocess
from pathlib import Path

import pytest

from bajka.ports import Animator
from bajka.motion import FfmpegAnimator, MotionError, MotionSettings, ffmpeg_command, main

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="brak ffmpeg w PATH")


class FakeRun:
    """Udaje subprocess.run: zapamiętuje polecenie albo rzuca podanym wyjątkiem."""

    def __init__(self, error=None):
        self.commands = []
        self._error = error

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        if self._error is not None:
            raise self._error


def make_png(path):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=skyblue:s=1536x1024", "-frames:v", "1",
         str(path)],
        check=True,
    )
    return path


def test_zoom_in_crops_to_16_9_and_zooms_slowly_for_whole_clip():
    cmd = ffmpeg_command(Path("ul.png"), Path("ul.mp4"), seconds=6, move="zoom_in")

    video_filter = cmd[cmd.index("-vf") + 1]
    assert cmd[cmd.index("-i") + 1] == "ul.png"
    assert "crop=iw:min(ih\\,iw*9/16)" in video_filter
    assert "zoompan=z='min(zoom+0.001000,1.15)'" in video_filter
    assert "s=1280x720" in video_filter
    assert cmd[cmd.index("-frames:v") + 1] == "150"
    assert "-an" in cmd
    assert cmd[-1] == "ul.mp4"


def test_pan_moves_across_the_picture():
    cmd = ffmpeg_command(Path("ul.png"), Path("ul.mp4"), seconds=6, move="pan")

    video_filter = cmd[cmd.index("-vf") + 1]
    assert "z='1.15'" in video_filter
    assert "x='(iw-iw/zoom)*on/150'" in video_filter


def test_unknown_move_is_rejected():
    with pytest.raises(ValueError, match="obrot"):
        ffmpeg_command(Path("ul.png"), Path("ul.mp4"), seconds=6, move="obrot")


def test_animator_fulfils_contract_and_returns_clip_next_to_session_files(tmp_path):
    run = FakeRun()
    animator = FfmpegAnimator(tmp_path, seconds=6, run=run)

    clip = animator.animate(tmp_path / "obraz_1.png")

    assert isinstance(animator, Animator)
    assert clip == tmp_path / "obraz_1.mp4"
    assert run.commands[0][-1] == str(clip)


def test_missing_ffmpeg_raises_motion_error(tmp_path):
    animator = FfmpegAnimator(tmp_path, run=FakeRun(FileNotFoundError("ffmpeg")))

    with pytest.raises(MotionError, match="ffmpeg"):
        animator.animate(tmp_path / "obraz.png")


def test_ffmpeg_failure_raises_motion_error_with_its_message(tmp_path):
    error = subprocess.CalledProcessError(1, ["ffmpeg"], stderr="Invalid data found\n")
    animator = FfmpegAnimator(tmp_path, run=FakeRun(error))

    with pytest.raises(MotionError, match="Invalid data found"):
        animator.animate(tmp_path / "obraz.png")


def test_settings_default_and_override():
    assert MotionSettings.from_env({}).seconds == 6.0
    assert MotionSettings.from_env({"BAJKA_MOTION_SECONDS": "4,5"}).seconds == 4.5


@needs_ffmpeg
def test_real_ffmpeg_makes_clip_from_illustration(tmp_path):
    image = make_png(tmp_path / "ul.png")

    clip = FfmpegAnimator(tmp_path / "klipy", seconds=1).animate(image)

    assert clip.is_file() and clip.stat().st_size > 0


@needs_ffmpeg
def test_demo_makes_clip_and_prints_time(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    image = make_png(tmp_path / "ul.png")

    assert main([str(image), "--seconds", "1", "--move", "pan"]) == 0

    assert "ul.mp4" in capsys.readouterr().out
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_motion.py -v`
Expected: `ModuleNotFoundError: No module named 'bajka.motion'`

- [ ] **Step 3: Dopisz nowe kontrakty na końcu `bajka/ports.py`**

<!-- append: bajka/ports.py -->
```python


@dataclass(frozen=True)
class Vision:
    reply: str  # kwestia postaci po polsku, wypowiadana podczas rysowania
    idea: str  # pomysł dziecka po angielsku, bezpieczny dla dzieci; "" gdy nie da się go użyć


@runtime_checkable
class Imaginer(Protocol):
    def imagine(self, scene: Scene, transcript: str) -> Vision:
        """Zamienia odpowiedź na pytanie otwarte na kwestię postaci i opis ilustracji."""


@runtime_checkable
class Illustrator(Protocol):
    def draw(self, prompt: str) -> Path:
        """Rysuje ilustrację sceny w stylu bajki i zwraca ścieżkę do pliku PNG."""


@runtime_checkable
class Animator(Protocol):
    def animate(self, image: Path) -> Path:
        """Robi z ilustracji klip MP4 z ruchem kamery i zwraca jego ścieżkę."""
```

- [ ] **Step 4: Napisz `bajka/motion.py`**

<!-- file: bajka/motion.py -->
```python
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
```

Uwaga: `crop=iw:min(ih\,iw*9/16)` wycina środek kadru 16:9 z ilustracji 3:2, a powiększenie 2x przed `zoompan` usuwa drgania obrazu przy powolnym zbliżeniu.

- [ ] **Step 5: Uruchom testy**

Run: `python -m pytest tests/test_motion.py -v`
Expected: `9 passed` (bez ffmpeg w `PATH`: `7 passed, 2 skipped`)

- [ ] **Step 6: Sprawdź klip na oko**

```powershell
ffmpeg -loglevel error -f lavfi -i testsrc2=s=1536x1024 -frames:v 1 kadr.png
python -m bajka.motion kadr.png
```

Expected: `Klip: ...\kadr.mp4 (1.3 s)` (u nas 1,3 s; budżet 3 s). Otwórz `kadr.mp4`: 6 s, 1280×720, powolne zbliżenie środka bez zniekształceń, czyli kwadraty szachownicy zostają kwadratowe. Usuń `kadr.png` i `kadr.mp4`.

- [ ] **Step 7: Commit**

```powershell
git add bajka/ports.py bajka/motion.py tests/test_motion.py
git commit -m "feat: kontrakty rysowania na żywo i ruch kamery z ffmpeg"
git pull --rebase origin main; python -m pytest; git push origin main
```

---

### Task 2: Scenariusz — styl, obrazy referencyjne i sceny `open`

**Files:**
- Modify: `bajka/scenario.py` (6 punktowych zmian)
- Create: `scenarios/rysowanie_na_zywo.yaml`
- Test: `tests/test_scenario_live.py`

**Interfaces:**
- Consumes: istniejący `bajka/scenario.py` (z polami `vote`, `call`, `call_clip`, które dodała osoba A — zostają bez zmian).
- Produces:
  - **`Scene`** dostaje pola: `kind` (`"clip"`/`"open"`), `drawing: Path | None`, `image_prompt`, `remember`, `default_idea`, `fallback_clips: tuple[Path, ...]`, `next`.
    - `is_ending` jest prawdą tylko dla `kind == "clip"` bez wyborów.
    - `successors -> tuple[str, ...]`.
  - **`Scenario`** dostaje pola `style: str` i `references: tuple[Path, ...]` oraz `needs_live_images: bool`.
  - **Funkcje:** `fill_prompt(template, values) -> str` (nieznane klucze zostają jako `{klucz}`), `template_fields(template) -> set[str]`, stałe `KINDS` i `LIVE_KINDS`.
  - **`missing_media`** obejmuje też `drawing`, `fallback_clips` i `references`.

- [ ] **Step 1: Napisz testy**

<!-- file: tests/test_scenario_live.py -->
```python
from pathlib import Path

import pytest

from bajka.scenario import ScenarioError, fill_prompt, load_scenario, missing_media, parse_scenario

OPEN_SCENE = {
    "kind": "open",
    "clip": "ozdoby.mp4",
    "idle": "ozdoby_idle.mp4",
    "drawing": "rysuje.mp4",
    "question": "Jak udekorujemy ul Bzyczki na święto?",
    "reprompt": "Kwiatki, wstążki, a może coś innego?",
    "image_prompt": "the beehive decorated for a party with {idea}",
    "remember": "ozdoby",
    "default_idea": "colorful flowers and ribbons",
    "fallback_clips": ["ozdoby_zapas_1.mp4", "ozdoby_zapas_2.mp4"],
    "next": "las",
}


@pytest.fixture
def live_dict(scenario_dict):
    """Scenariusz z conftest + styl, referencje i scena otwarta między wyborem a lasem."""
    scenario_dict["style"] = "soft watercolor children's book illustration"
    scenario_dict["references"] = ["ref_lila.png", "ref_fiku.png"]
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = dict(OPEN_SCENE)
    return scenario_dict


def test_style_and_references_are_read_relative_to_scenario(live_dict):
    scenario = parse_scenario(live_dict, base_dir=Path("film"))

    assert scenario.style == "soft watercolor children's book illustration"
    assert scenario.references == (Path("film/ref_lila.png"), Path("film/ref_fiku.png"))
    assert scenario.needs_live_images


def test_classic_scenario_has_no_style_and_needs_no_live_images(scenario):
    assert scenario.style == ""
    assert scenario.references == ()
    assert not scenario.needs_live_images


def test_open_scene_is_parsed_with_paths_and_next(live_dict):
    scene = parse_scenario(live_dict, base_dir=Path("film")).scene("ozdoby")

    assert scene.kind == "open"
    assert scene.clip == Path("film/ozdoby.mp4")
    assert scene.drawing == Path("film/rysuje.mp4")
    assert scene.remember == "ozdoby"
    assert scene.default_idea == "colorful flowers and ribbons"
    assert scene.fallback_clips == (Path("film/ozdoby_zapas_1.mp4"), Path("film/ozdoby_zapas_2.mp4"))
    assert scene.successors == ("las",)
    assert not scene.is_ending


def test_successors_of_choice_scene_are_its_choices(scenario):
    assert scenario.scene("intro").successors == ("las", "jaskinia")
    assert scenario.scene("las").successors == ()


@pytest.mark.parametrize("field", ["drawing", "image_prompt", "remember", "default_idea", "fallback_clips", "next"])
def test_open_scene_requires_field(live_dict, field):
    del live_dict["scenes"]["ozdoby"][field]

    with pytest.raises(ScenarioError, match=field):
        parse_scenario(live_dict, base_dir=Path("."))


def test_open_image_prompt_must_use_idea(live_dict):
    live_dict["scenes"]["ozdoby"]["image_prompt"] = "the beehive decorated for a party"

    with pytest.raises(ScenarioError, match="idea"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_open_next_must_exist(live_dict):
    live_dict["scenes"]["ozdoby"]["next"] = "bagno"

    with pytest.raises(ScenarioError, match="bagno"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_template_may_only_use_remembered_ideas(live_dict):
    live_dict["scenes"]["ozdoby"]["image_prompt"] = "the beehive with {idea} and {smok}"

    with pytest.raises(ScenarioError, match="smok"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_unknown_kind_is_rejected(live_dict):
    live_dict["scenes"]["ozdoby"]["kind"] = "film"

    with pytest.raises(ScenarioError, match="film"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_missing_media_includes_drawing_fallbacks_and_references(tmp_path, live_dict):
    scenario = parse_scenario(live_dict, base_dir=tmp_path)

    missing = {path.name for path in missing_media(scenario)}

    assert {"rysuje.mp4", "ozdoby_zapas_1.mp4", "ozdoby_zapas_2.mp4", "ref_lila.png", "ref_fiku.png"} <= missing


def test_fill_prompt_fills_known_values_and_keeps_unknown():
    assert fill_prompt("ul z {idea} i {smok}", {"idea": "wstążkami"}) == "ul z wstążkami i {smok}"


def test_live_drawing_example_is_valid():
    path = Path(__file__).resolve().parents[1] / "scenarios" / "rysowanie_na_zywo.yaml"

    scenario = load_scenario(path)

    assert scenario.needs_live_images
    assert scenario.scene("skarb").kind == "open"
    assert scenario.scene("intro").choices["jaskinia"].next == "skarb"
```

- [ ] **Step 2: Dodaj przykładowy scenariusz (używa go ostatni test)**

<!-- file: scenarios/rysowanie_na_zywo.yaml -->
```yaml
# Przykład scen rysowanych na żywo — do prób mechaniki; prawdziwy scenariusz bajki dostarcza autor.
# Klipy-zaślepki:  python -m bajka.placeholders scenarios/rysowanie_na_zywo.yaml
# Próba:           python -m bajka scenarios/rysowanie_na_zywo.yaml --text --windowed
hero: >
  Lisek Feliks: odważny, ciekawski i trochę gapowaty lis, który przeżywa przygodę
  razem z dzieckiem siedzącym przed ekranem i zwraca się do niego jak do przyjaciela.
style: soft watercolor children's book illustration, warm pastel colors, gentle light, simple shapes
start: intro

scenes:
  intro:
    clip: clips/rysowanie/intro.mp4
    idle: clips/rysowanie/intro_idle.mp4
    question: Idziemy do mrocznego lasu czy do jaskini?
    reprompt: Hmm, nie usłyszałem. Idziemy do lasu czy do jaskini?
    default: jaskinia
    choices:
      las:
        description: pójść do mrocznego lasu
        next: las
        reply: Do lasu! Trzymaj się blisko mnie!
      jaskinia:
        description: wejść do jaskini
        next: skarb
        reply: Do jaskini! Dobrze, że mam latarkę!

  # Pytanie otwarte: pomysł dziecka jest rysowany na żywo.
  skarb:
    kind: open
    clip: clips/rysowanie/skarb.mp4               # Feliks znajduje coś błyszczącego i pyta, co to
    idle: clips/rysowanie/skarb_idle.mp4          # cicha pętla oczekiwania
    drawing: clips/rysowanie/rysuje.mp4           # cicha pętla „Feliks rysuje” na czas generowania
    question: Coś tu błyszczy! Jak wygląda skarb, który znaleźliśmy?
    reprompt: Złoto, kryształy, a może coś zupełnie innego? Jaki to skarb?
    image_prompt: "a little fox in a cozy cave lit by a lantern, discovering a treasure: {idea}"
    remember: skarb
    default_idea: a small chest full of glowing colorful crystals
    fallback_clips: [clips/rysowanie/skarb_zapas.mp4]
    next: jaskinia

  las:
    clip: clips/las.mp4

  jaskinia:
    clip: clips/jaskinia.mp4
```

- [ ] **Step 3: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_scenario_live.py -v`
Expected: `ImportError: cannot import name 'fill_prompt' from 'bajka.scenario'`

- [ ] **Step 4: Nagłówek modułu, importy i stałe — w `bajka/scenario.py` zamień:**

<!-- edit: bajka/scenario.py -->
```python
"""Scenariusz bajki: graf scen wczytywany z pliku YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
```

na:

```python
"""Scenariusz bajki: graf scen wczytywany z pliku YAML.

Rodzaje scen (`kind`):
- `clip` (domyślny): gotowy klip, opcjonalnie pytanie zamknięte z wyborami,
- `open`: gotowy klip z pytaniem otwartym; pomysł dziecka jest rysowany na żywo (bajka/imagine.py,
  bajka/illustrate.py, bajka/motion.py).
"""

from __future__ import annotations

import string
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml

KINDS = ("clip", "open")
LIVE_KINDS = ("open",)  # sceny, które potrzebują generowania obrazów na żywo
```

- [ ] **Step 5: Nowe pola `Scene` i `Scenario` — zamień:**

<!-- edit: bajka/scenario.py -->
```python
    vote: bool = False  # widownia wybiera okrzykiem: wygrywa najgłośniej wykrzyczana opcja (seans w kinie)

    @property
    def is_ending(self) -> bool:
        return not self.choices


@dataclass(frozen=True)
class Scenario:
    hero: str
    start: str
    scenes: dict[str, Scene]

    def scene(self, scene_id: str) -> Scene:
        return self.scenes[scene_id]
```

na:

```python
    vote: bool = False  # widownia wybiera okrzykiem: wygrywa najgłośniej wykrzyczana opcja (seans w kinie)
    kind: str = "clip"
    drawing: Path | None = None  # pętla „postać rysuje” na czas generowania ilustracji
    image_prompt: str = ""  # szablon opisu ilustracji po angielsku: {idea} i zapamiętane pomysły
    remember: str = ""  # klucz, pod którym zapamiętujemy pomysł dziecka na resztę seansu
    default_idea: str = ""  # pomysł, gdy dziecko milczy albo pomysłu nie da się narysować
    fallback_clips: tuple[Path, ...] = ()  # gotowe klipy, gdy generowanie zawiedzie
    next: str = ""  # następna scena dla scen bez wyborów (open)

    @property
    def is_ending(self) -> bool:
        return self.kind == "clip" and not self.choices

    @property
    def successors(self) -> tuple[str, ...]:
        if self.next:
            return (self.next,)
        return tuple(choice.next for choice in self.choices.values())


@dataclass(frozen=True)
class Scenario:
    hero: str
    start: str
    scenes: dict[str, Scene]
    style: str = ""  # opis stylu ilustracji po angielsku, dodawany do każdego obrazu
    references: tuple[Path, ...] = ()  # obrazy referencyjne postaci (karta postaci)

    def scene(self, scene_id: str) -> Scene:
        return self.scenes[scene_id]

    @property
    def needs_live_images(self) -> bool:
        return any(scene.kind in LIVE_KINDS for scene in self.scenes.values())
```

- [ ] **Step 6: Wczytanie stylu i referencji, `missing_media`, `fill_prompt` — zamień:**

<!-- edit: bajka/scenario.py -->
```python
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
    )
    _validate_graph(scenario)
    return scenario


def missing_media(scenario: Scenario) -> list[Path]:
    """Zwraca klipy i pętle oczekiwania, których nie ma na dysku."""
    paths: list[Path] = []
    for scene in scenario.scenes.values():
        paths.append(scene.clip)
        if scene.idle is not None:
            paths.append(scene.idle)
        paths.extend(c.call_clip for c in scene.choices.values() if c.call_clip is not None)
    return [path for path in paths if not path.is_file()]
```

na:

```python
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
        style=str(raw.get("style") or "").strip(),
        references=_optional_paths(raw, "references", base_dir, "scenariusz"),
    )
    _validate_graph(scenario)
    return scenario


def missing_media(scenario: Scenario) -> list[Path]:
    """Zwraca klipy, pętle i obrazy referencyjne, których nie ma na dysku."""
    paths: list[Path] = list(scenario.references)
    for scene in scenario.scenes.values():
        paths.append(scene.clip)
        paths.extend(path for path in (scene.idle, scene.drawing) if path is not None)
        paths.extend(c.call_clip for c in scene.choices.values() if c.call_clip is not None)
        paths.extend(scene.fallback_clips)
    return [path for path in dict.fromkeys(paths) if not path.is_file()]


def fill_prompt(template: str, values: Mapping[str, str]) -> str:
    """Wstawia pomysły do szablonu; nieznane klucze zostawia w nawiasach, zamiast się wywrócić."""

    class _Keep(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return string.Formatter().vformat(template, (), _Keep(values))


def template_fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}
```

- [ ] **Step 7: Rozpoznanie rodzaju sceny w `_parse_scene` — zamień:**

<!-- edit: bajka/scenario.py -->
```python
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: oczekiwano słownika")
    raw_choices = data.get("choices") or {}
```

na:

```python
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: oczekiwano słownika")
    kind = data.get("kind", "clip")
    if kind not in KINDS:
        raise ScenarioError(f"{where}: nieznany rodzaj sceny {kind!r}, dostępne: {', '.join(KINDS)}")
    if kind == "open":
        return _parse_open(scene_id, data, base_dir, where)
    raw_choices = data.get("choices") or {}
```

- [ ] **Step 8: Parser sceny otwartej i list ścieżek — zamień:**

<!-- edit: bajka/scenario.py -->
```python
        choices=choices,
        vote=vote,
    )


def _require_str(data: object, key: str, where: str) -> str:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where}: brak pola '{key}' (niepusty tekst)")
    return value.strip()
```

na:

```python
        choices=choices,
        vote=vote,
    )


def _parse_open(scene_id: str, data: dict, base_dir: Path, where: str) -> Scene:
    image_prompt = _require_str(data, "image_prompt", where)
    if "idea" not in template_fields(image_prompt):
        raise ScenarioError(f"{where}: 'image_prompt' musi zawierać {{idea}}, czyli pomysł dziecka")
    return Scene(
        id=scene_id,
        kind="open",
        clip=base_dir / _require_str(data, "clip", where),
        idle=base_dir / _require_str(data, "idle", where),
        drawing=base_dir / _require_str(data, "drawing", where),
        question=_require_str(data, "question", where),
        reprompt=_require_str(data, "reprompt", where),
        image_prompt=image_prompt,
        remember=_require_str(data, "remember", where),
        default_idea=_require_str(data, "default_idea", where),
        fallback_clips=_require_paths(data, "fallback_clips", base_dir, where),
        next=_require_str(data, "next", where),
    )


def _require_str(data: object, key: str, where: str) -> str:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where}: brak pola '{key}' (niepusty tekst)")
    return value.strip()


def _optional_paths(data: dict, key: str, base_dir: Path, where: str) -> tuple[Path, ...]:
    value = data.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ScenarioError(f"{where}: '{key}' musi być listą ścieżek do plików")
    return tuple(base_dir / v.strip() for v in value)


def _require_paths(data: dict, key: str, base_dir: Path, where: str) -> tuple[Path, ...]:
    paths = _optional_paths(data, key, base_dir, where)
    if not paths:
        raise ScenarioError(f"{where}: brak pola '{key}' (lista co najmniej jednego pliku)")
    return paths
```

- [ ] **Step 9: Walidacja grafu z `next` i szablonów — zamień całe `_validate_graph`:**

<!-- edit: bajka/scenario.py -->
```python
def _validate_graph(scenario: Scenario) -> None:
    if scenario.start not in scenario.scenes:
        raise ScenarioError(f"scenariusz: scena startowa '{scenario.start}' nie istnieje")
    for scene in scenario.scenes.values():
        if scene.is_ending:
            continue
        if scene.default not in scene.choices:
            raise ScenarioError(
                f"scena '{scene.id}': 'default' musi być jednym z wyborów: {', '.join(scene.choices)}"
            )
        for choice in scene.choices.values():
            if choice.next not in scenario.scenes:
                raise ScenarioError(
                    f"scena '{scene.id}', wybór '{choice.id}': scena '{choice.next}' nie istnieje"
                )
```

na:

```python
def _validate_graph(scenario: Scenario) -> None:
    if scenario.start not in scenario.scenes:
        raise ScenarioError(f"scenariusz: scena startowa '{scenario.start}' nie istnieje")
    remembered = {scene.remember for scene in scenario.scenes.values() if scene.kind == "open"}
    for scene in scenario.scenes.values():
        if scene.choices and scene.default not in scene.choices:
            raise ScenarioError(
                f"scena '{scene.id}': 'default' musi być jednym z wyborów: {', '.join(scene.choices)}"
            )
        for choice in scene.choices.values():
            if choice.next not in scenario.scenes:
                raise ScenarioError(
                    f"scena '{scene.id}', wybór '{choice.id}': scena '{choice.next}' nie istnieje"
                )
        if scene.next and scene.next not in scenario.scenes:
            raise ScenarioError(f"scena '{scene.id}': następna scena '{scene.next}' (next) nie istnieje")
        allowed = remembered | ({"idea"} if scene.kind == "open" else set())
        unknown = template_fields(scene.image_prompt) - allowed
        if unknown:
            raise ScenarioError(
                f"scena '{scene.id}': 'image_prompt' używa nieznanych pomysłów: {', '.join(sorted(unknown))}"
                " (dozwolone: {idea} i klucze 'remember' scen otwartych)"
            )
```

- [ ] **Step 10: Uruchom testy scenariuszy**

Run: `python -m pytest tests/test_scenario_live.py tests/test_scenario.py tests/test_klub_ciekawskich.py -v`
Expected: `tests/test_scenario_live.py` — `17 passed`; dotychczasowe testy scenariuszy dalej przechodzą.

- [ ] **Step 11: Commit**

```powershell
git add bajka/scenario.py scenarios/rysowanie_na_zywo.yaml tests/test_scenario_live.py
git commit -m "feat: sceny z pytaniem otwartym, styl i obrazy referencyjne w scenariuszu"
git pull --rebase origin main; python -m pytest; git push origin main
```

---

### Task 3: Ilustracje w Azure AI Foundry i pomiar dnia 1

**Files:**
- Create: `bajka/illustrate.py`, `scenarios/pomiar_obrazow.yaml`, `scenarios/karta_postaci.yaml`
- Test: `tests/test_illustrate.py`

**Interfaces:**
- Consumes: `bajka.config` (`require`, `get_int`, `load_env`, `ConfigError`), `bajka.scenario.load_scenario`, `Scenario.style`, `Scenario.references` (Task 2).
- Produces:
  - `ImageSettings.from_env(env)` z polami `endpoint`, `api_key`, `deployment`, `api_version`, `size`, `quality`, `timeout_s`,
  - `AzureIllustrator(client, deployment, out_dir, style="", references=(), size="1536x1024", quality="medium")`:
    - `from_settings(settings, out_dir, style="", references=(), max_retries=0)`,
    - `draw(prompt, name=None) -> Path`: z referencjami woła `images.edit` z listą obrazów, bez nich `images.generate`,
  - `build_prompt(scene_prompt, style, with_references) -> str`,
  - `load_shots(path) -> list[tuple[str, str]]`.

- [ ] **Step 1: Napisz testy**

<!-- file: tests/test_illustrate.py -->
```python
import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from bajka.config import ConfigError
from bajka.illustrate import AzureIllustrator, ImageSettings, build_prompt, load_shots, main
from bajka.ports import Illustrator

IMAGE_ENV = {
    "AZURE_IMAGE_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_IMAGE_API_KEY": "klucz-obrazow",
    "AZURE_IMAGE_DEPLOYMENT": "gpt-image-2",
}


class FakeImages:
    """Udaje client.images z SDK openai: zapamiętuje wywołania i zwraca obraz w base64."""

    def __init__(self, png=b"PNG", error=None):
        self.calls = []
        self._result = SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(png).decode())])
        self._error = error

    def generate(self, **kwargs):
        return self._answer("generate", kwargs)

    def edit(self, **kwargs):
        # pliki są otwarte tylko w trakcie wywołania, więc zapamiętujemy ich nazwy
        return self._answer("edit", {**kwargs, "image": [Path(f.name).name for f in kwargs["image"]]})

    def _answer(self, method, kwargs):
        self.calls.append((method, kwargs))
        if self._error is not None:
            raise self._error
        return self._result


def make_illustrator(tmp_path, images, references=()):
    client = SimpleNamespace(images=images)
    return AzureIllustrator(client, "gpt-image-2", tmp_path / "sesja", style="watercolor", references=references)


def write_references(tmp_path):
    paths = [tmp_path / "ref_lila.png", tmp_path / "ref_fiku.png"]
    for path in paths:
        path.write_bytes(b"REF")
    return tuple(paths)


# Prompt i ustawienia


def test_prompt_adds_style_safety_and_reference_hint():
    prompt = build_prompt("the beehive decorated with ribbons.", "soft watercolor", with_references=True)

    assert prompt.startswith("the beehive decorated with ribbons.")
    assert "Style: soft watercolor." in prompt
    assert "reference images" in prompt
    assert "not photorealistic" in prompt


def test_prompt_without_style_and_references_has_only_safety_hint():
    prompt = build_prompt("a red apple", "", with_references=False)

    assert "Style" not in prompt and "reference" not in prompt
    assert "no text" in prompt


def test_settings_read_keys_and_apply_defaults():
    settings = ImageSettings.from_env(IMAGE_ENV)

    assert settings.deployment == "gpt-image-2"
    assert settings.api_version == "2025-04-01-preview"
    assert (settings.size, settings.quality, settings.timeout_s) == ("1536x1024", "medium", 25)


def test_settings_require_endpoint_key_and_deployment():
    with pytest.raises(ConfigError) as exc:
        ImageSettings.from_env({})

    for name in IMAGE_ENV:
        assert name in str(exc.value)


def test_settings_overrides():
    env = {**IMAGE_ENV, "BAJKA_IMAGE_SIZE": "1024x1024", "BAJKA_IMAGE_QUALITY": "low", "BAJKA_IMAGE_TIMEOUT_S": "15"}

    settings = ImageSettings.from_env(env)

    assert (settings.size, settings.quality, settings.timeout_s) == ("1024x1024", "low", 15)


# Rysowanie


def test_without_references_generates_and_saves_png(tmp_path):
    images = FakeImages(png=b"OBRAZ")
    illustrator = make_illustrator(tmp_path, images)

    path = illustrator.draw("the beehive decorated with ribbons")

    method, kwargs = images.calls[0]
    assert isinstance(illustrator, Illustrator)
    assert method == "generate"
    assert kwargs["model"] == "gpt-image-2"
    assert (kwargs["size"], kwargs["quality"]) == ("1536x1024", "medium")
    assert "Style: watercolor." in kwargs["prompt"]
    assert path.parent == tmp_path / "sesja" and path.suffix == ".png"
    assert path.read_bytes() == b"OBRAZ"


def test_with_references_edits_with_all_reference_images(tmp_path):
    images = FakeImages()
    illustrator = make_illustrator(tmp_path, images, references=write_references(tmp_path))

    illustrator.draw("Lila decorates the beehive")

    method, kwargs = images.calls[0]
    assert method == "edit"
    assert kwargs["image"] == ["ref_lila.png", "ref_fiku.png"]
    assert "reference images" in kwargs["prompt"]


def test_named_drawing_uses_given_file_name(tmp_path):
    path = make_illustrator(tmp_path, FakeImages()).draw("a meadow", name="02_kuferek_01")

    assert path.name == "02_kuferek_01.png"


def test_each_drawing_gets_its_own_file(tmp_path):
    illustrator = make_illustrator(tmp_path, FakeImages())

    assert illustrator.draw("a") != illustrator.draw("b")


def test_service_errors_are_passed_to_the_caller(tmp_path):
    illustrator = make_illustrator(tmp_path, FakeImages(error=RuntimeError("content_policy_violation")))

    with pytest.raises(RuntimeError, match="content_policy_violation"):
        illustrator.draw("a scary monster")


# Plik ujęć do produkcji


def test_load_shots_reads_names_and_prompts(tmp_path):
    shots = tmp_path / "ujecia.yaml"
    shots.write_text(yaml.safe_dump([{"name": "01", "prompt": "Lila waves"}, {"name": "02", "prompt": "Fiku jumps"}]))

    assert load_shots(shots) == [("01", "Lila waves"), ("02", "Fiku jumps")]


def test_load_shots_rejects_shot_without_prompt(tmp_path):
    shots = tmp_path / "ujecia.yaml"
    shots.write_text(yaml.safe_dump([{"name": "01"}]))

    with pytest.raises(ValueError, match="prompt"):
        load_shots(shots)


# Demo: python -m bajka.illustrate


@pytest.fixture
def scenario_file(tmp_path, scenario_dict):
    scenario_dict["style"] = "soft watercolor"
    path = tmp_path / "bajka.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def image_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in IMAGE_ENV.items():
        monkeypatch.setenv(name, value)


def use_fake_images(monkeypatch, images):
    def from_settings(cls, settings, out_dir, style="", references=(), max_retries=0):
        return AzureIllustrator(SimpleNamespace(images=images), settings.deployment, out_dir, style, references)

    monkeypatch.setattr(AzureIllustrator, "from_settings", classmethod(from_settings))


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, scenario_file, capsys):
    monkeypatch.chdir(tmp_path)
    for name in IMAGE_ENV:
        monkeypatch.delenv(name, raising=False)

    assert main([str(scenario_file), "a meadow"]) == 2
    assert "AZURE_IMAGE_ENDPOINT" in capsys.readouterr().err


def test_demo_needs_prompt_or_batch(scenario_file):
    with pytest.raises(SystemExit):
        main([str(scenario_file)])


def test_demo_draws_one_picture_with_scenario_style(image_keys, monkeypatch, scenario_file, tmp_path, capsys):
    images = FakeImages()
    use_fake_images(monkeypatch, images)

    assert main([str(scenario_file), "a meadow", "--out", str(tmp_path / "out")]) == 0

    assert "Style: soft watercolor." in images.calls[0][1]["prompt"]
    assert ".png" in capsys.readouterr().out


def test_demo_batch_reports_median_and_keeps_going_after_error(image_keys, monkeypatch, scenario_file, tmp_path, capsys):
    shots = tmp_path / "ujecia.yaml"
    shots.write_text(yaml.safe_dump([{"name": "01", "prompt": "a"}, {"name": "02", "prompt": "b"}]))
    images = FakeImages()
    use_fake_images(monkeypatch, images)

    assert main([str(scenario_file), "--batch", str(shots), "--out", str(tmp_path / "out")]) == 0

    out = capsys.readouterr().out
    assert "01.png" in out and "02.png" in out
    assert "Mediana" in out


def test_demo_returns_1_when_every_picture_fails(image_keys, monkeypatch, scenario_file, capsys):
    use_fake_images(monkeypatch, FakeImages(error=RuntimeError("401 zły klucz")))

    assert main([str(scenario_file), "a meadow"]) == 1
    assert "401" in capsys.readouterr().err
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_illustrate.py -v`
Expected: `ModuleNotFoundError: No module named 'bajka.illustrate'`

- [ ] **Step 3: Napisz `bajka/illustrate.py`**

<!-- file: bajka/illustrate.py -->
```python
"""Ilustracje scen w stylu bajki przez Azure AI Foundry (wdrożenie modelu gpt-image).

Moduł spełnia kontrakt `bajka.ports.Illustrator`. Styl i obrazy referencyjne postaci bierze ze scenariusza.
Jedna ilustracja z pomiarem czasu:  python -m bajka.illustrate SCENARIUSZ "opis sceny po angielsku"
Produkcja i pomiar wielu ujęć:      python -m bajka.illustrate SCENARIUSZ --batch ujecia.yaml
"""

from __future__ import annotations

import argparse
import base64
import statistics
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bajka.config import ConfigError, get_int, load_env, require
from bajka.scenario import ScenarioError, load_scenario


@dataclass(frozen=True)
class ImageSettings:
    endpoint: str
    api_key: str
    deployment: str  # nazwa wdrożenia w Azure, np. gpt-image-2
    api_version: str = "2025-04-01-preview"
    size: str = "1536x1024"
    quality: str = "medium"
    timeout_s: int = 25

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ImageSettings:
        require(env, "AZURE_IMAGE_ENDPOINT", "AZURE_IMAGE_API_KEY", "AZURE_IMAGE_DEPLOYMENT")
        return cls(
            endpoint=env["AZURE_IMAGE_ENDPOINT"],
            api_key=env["AZURE_IMAGE_API_KEY"],
            deployment=env["AZURE_IMAGE_DEPLOYMENT"],
            api_version=env.get("AZURE_IMAGE_API_VERSION") or cls.api_version,
            size=env.get("BAJKA_IMAGE_SIZE") or cls.size,
            quality=env.get("BAJKA_IMAGE_QUALITY") or cls.quality,
            timeout_s=get_int(env, "BAJKA_IMAGE_TIMEOUT_S", cls.timeout_s),
        )


def build_prompt(scene_prompt: str, style: str, with_references: bool) -> str:
    parts = [scene_prompt.strip().rstrip(".") + "."]
    if style:
        parts.append(f"Style: {style.strip().rstrip('.')}.")
    if with_references:
        parts.append("Draw the characters exactly as they look in the reference images.")
    # Ilustracja, nie zdjęcie: Azure domyślnie blokuje fotorealistyczne obrazy dzieci.
    parts.append("Illustration for young children, not photorealistic, no text or letters.")
    return " ".join(parts)


class AzureIllustrator:
    def __init__(
        self,
        client: Any,
        deployment: str,
        out_dir: Path,
        style: str = "",
        references: Sequence[Path] = (),
        size: str = "1536x1024",
        quality: str = "medium",
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._out_dir = Path(out_dir)
        self._style = style
        self._references = tuple(references)
        self._size = size
        self._quality = quality

    @classmethod
    def from_settings(
        cls,
        settings: ImageSettings,
        out_dir: Path,
        style: str = "",
        references: Sequence[Path] = (),
        max_retries: int = 0,
    ) -> AzureIllustrator:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            timeout=float(settings.timeout_s),
            max_retries=max_retries,  # na żywo 0: lepiej od razu klip zapasowy niż czekanie na ponowienie
        )
        return cls(client, settings.deployment, out_dir, style, references, settings.size, settings.quality)

    def draw(self, prompt: str, name: str | None = None) -> Path:
        full_prompt = build_prompt(prompt, self._style, with_references=bool(self._references))
        options = {"model": self._deployment, "prompt": full_prompt, "size": self._size, "quality": self._quality}
        if self._references:
            with ExitStack() as stack:
                images = [stack.enter_context(open(path, "rb")) for path in self._references]
                result = self._client.images.edit(image=images, **options)
        else:
            result = self._client.images.generate(n=1, **options)
        self._out_dir.mkdir(parents=True, exist_ok=True)
        target = self._out_dir / f"{name or 'obraz_' + uuid.uuid4().hex[:8]}.png"
        target.write_bytes(base64.b64decode(result.data[0].b64_json))
        return target


def load_shots(path: Path) -> list[tuple[str, str]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{path}: oczekiwano listy ujęć [{{name, prompt}}, ...]")
    shots = []
    for number, item in enumerate(raw, start=1):
        name = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
        prompt = str(item.get("prompt") or "").strip() if isinstance(item, dict) else ""
        if not name or not prompt:
            raise ValueError(f"{path}: ujęcie {number} musi mieć 'name' i 'prompt'")
        shots.append((name, prompt))
    return shots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.illustrate", description="Ilustracje scen przez Azure AI Foundry, z pomiarem czasu."
    )
    parser.add_argument("scenario", type=Path, help="scenariusz YAML (styl i obrazy referencyjne postaci)")
    parser.add_argument("prompt", nargs="?", help="opis sceny po angielsku")
    parser.add_argument("--batch", type=Path, help="plik YAML z listą ujęć: [{name, prompt}, ...]")
    parser.add_argument("--out", type=Path, default=Path("ilustracje"), help="katalog na obrazy (domyślnie ilustracje)")
    args = parser.parse_args(argv)
    if (args.prompt is None) == (args.batch is None):
        parser.error("podaj opis sceny albo --batch")
    try:
        scenario = load_scenario(args.scenario)
        settings = ImageSettings.from_env(load_env())
        shots = load_shots(args.batch) if args.batch else [(None, args.prompt)]
    except (ScenarioError, ConfigError, ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2

    # Przy produkcji wolno ponawiać (limit to ok. 5 obrazów na minutę), na żywo nie.
    illustrator = AzureIllustrator.from_settings(
        settings, args.out, scenario.style, scenario.references, max_retries=3
    )
    times = []
    for name, prompt in shots:
        started = time.perf_counter()
        try:
            path = illustrator.draw(prompt, name=name)
        except Exception as exc:  # demo pokazuje każdy błąd Azure (filtr treści, limit, klucz) i idzie dalej
            print(f"Błąd ({name or prompt}): {exc}", file=sys.stderr)
            continue
        times.append(time.perf_counter() - started)
        print(f"{path} ({times[-1]:.1f} s)", flush=True)
    if not times:
        return 1
    if len(shots) > 1:
        median, longest = statistics.median(times), max(times)
        print(f"Mediana: {median:.1f} s, maksimum: {longest:.1f} s, udane: {len(times)}/{len(shots)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_illustrate.py -v`
Expected: `17 passed`

- [ ] **Step 5: Dodaj ujęcia do pomiaru i karty postaci**

<!-- file: scenarios/pomiar_obrazow.yaml -->
```yaml
# Pomiar dnia 1: 10 typowych scen z pomysłami dzieci w świecie „Klubu Ciekawskich”.
# python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml --batch scenarios/pomiar_obrazow.yaml --out pomiar/gpt-image-2
# Sceny 01–03 pokazują Lilę (dziewczynkę): sprawdzają, czy filtr Azure nie blokuje ilustrowanego dziecka.
- name: "01_lila_mostek"
  prompt: "Lila, a 7-year-old explorer girl in yellow rain boots and dungarees with a big magnifying glass, crossing a rainbow bridge over a stream"
- name: "02_lila_fiku_las"
  prompt: "Lila and Fiku, a red squirrel with a question-mark shaped tail and a green scarf, listening to an owl in a friendly forest"
- name: "03_lila_lupa"
  prompt: "Lila looking through her big magnifying glass at a tiny ladybug on a flower"
- name: "04_ul_wstazki"
  prompt: "a beehive on a flower meadow decorated for a party with rainbow ribbons"
- name: "05_ul_balony"
  prompt: "a beehive on a flower meadow decorated with colorful balloons and paper lanterns"
- name: "06_smok_rozowy"
  prompt: "a friendly pink dragon with tiny wings sitting next to a beehive and smiling"
- name: "07_bzyczka_korona"
  prompt: "Bzyczka, a small cheerful bee, wearing a golden crown made of flower petals"
- name: "08_tort_miodowy"
  prompt: "a huge honey cake with candles on a picnic blanket in a sunny meadow"
- name: "09_wiaterek"
  prompt: "Fiufiu, a playful little wind cloud with a face, gently blowing dandelion seeds"
- name: "10_jaskinia_krysztaly"
  prompt: "a cozy cave lit by a lantern, full of glowing colorful crystals"
```

<!-- file: scenarios/karta_postaci.yaml -->
```yaml
# Karta postaci: po dwa warianty każdej postaci na białym tle. Zespół wybiera najlepsze ujęcia,
# kopiuje je do scenarios/ilustracje/ i wpisuje do pola `references` w scenariuszu.
# python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml --batch scenarios/karta_postaci.yaml --out scenarios/ilustracje/kandydaci
- name: "lila_a"
  prompt: "character sheet: Lila, a 7-year-old explorer girl in yellow rain boots, blue dungarees with pockets full of screws, a big magnifying glass on a string, full figure, front view, plain white background"
- name: "lila_b"
  prompt: "character sheet: Lila, a 7-year-old explorer girl in yellow rain boots and blue dungarees, holding a big magnifying glass, full figure, three-quarter view, plain white background"
- name: "fiku_a"
  prompt: "character sheet: Fiku, a fluffy red squirrel with a tail shaped like a question mark, a green scarf and a little baker's apron, full figure, front view, plain white background"
- name: "fiku_b"
  prompt: "character sheet: Fiku, a fluffy red squirrel with a question-mark tail, green scarf and baker's apron, doing a cheerful somersault, plain white background"
- name: "bzyczka_a"
  prompt: "character sheet: Bzyczka, a small round cheerful honey bee with big friendly eyes, full figure, front view, plain white background"
- name: "bzyczka_b"
  prompt: "character sheet: Bzyczka, a small round cheerful honey bee flying with a tiny backpack, side view, plain white background"
```

- [ ] **Step 6: Pomiar dnia 1 (wymaga dostępu do Azure AI Foundry od mentorów Microsoftu)**

1. **Wdrożenie modelu.** W Azure AI Foundry wdróż `gpt-image-2`, albo `gpt-image-1.5`, jeśli zespół ma już na niego zgodę. Do `.env` wpisz:
   - `AZURE_IMAGE_ENDPOINT`,
   - `AZURE_IMAGE_API_KEY`,
   - `AZURE_IMAGE_DEPLOYMENT=gpt-image-2`.
2. **Próba:**
   `python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml "a little fox waving hello in a sunny meadow"`
   Expected: `ilustracje\obraz_xxxxxxxx.png (NN.N s)`. Obejrzyj PNG: akwarela, bez napisów.
3. **Pomiar bez referencji:**
   `python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml --batch scenarios/pomiar_obrazow.yaml --out pomiar/bez-referencji`
   Expected: 10 linii z czasem, na końcu `Mediana: … s, maksimum: … s, udane: N/10`.
   - Jeśli ujęcia 01–03 (Lila) padają z `content_policy_violation`, zespół upraszcza opis Lili w stronę „cartoon character” i powtarza pomiar.
4. **Karta postaci:**
   `python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml --batch scenarios/karta_postaci.yaml --out scenarios/ilustracje/kandydaci`
   - Zespół wybiera 2–4 najlepsze ujęcia i kopiuje je do `scenarios/ilustracje/`, np. `ref_lila.png`, `ref_fiku.png`, `ref_bzyczka.png`.
   - Do scenariusza z bajką dopisuje `references: [ilustracje/ref_lila.png, …]`.
   - Kandydatów nie commitujemy (`Remove-Item -Recurse scenarios/ilustracje/kandydaci`).
5. **Pomiar z referencjami** (ścieżka `images.edit`): powtórz punkt 3 ze scenariuszem, który ma `references`, z `--out pomiar/z-referencjami`. Porównaj czas i to, czy Lila wygląda jak Lila.
6. **FLUX:** w playgroundzie Azure AI Foundry wdróż `FLUX.1-Kontext-pro`. Wygeneruj ujęcia 01, 04 i 06 z `ref_lila.png` jako obrazem wejściowym i oceń spójność postaci na tle gpt-image.
7. **Decyzja** (spec, sekcja 8):
   - wygrywa model z medianą ≤ 20 s i lepszą spójnością postaci, przy remisie gpt-image ze względu na wbudowany filtr,
   - jeśli mediana przekracza 20 s, ustaw `BAJKA_IMAGE_QUALITY=low` albo `BAJKA_IMAGE_SIZE=1024x1024` i zmierz ponownie,
   - jeśli wygrywa FLUX, osobnym zadaniem dopisz `FluxIllustrator`.
8. **Zapis wyników.** Dopisz na końcu specu sekcję `## 11. Wyniki pomiaru dnia 1`, a w niej:
   - model, rozmiar i jakość,
   - medianę i maksimum bez referencji i z referencjami,
   - liczbę odrzuceń przez filtr,
   - ocenę spójności,
   - decyzję.
9. **Prawdziwe klipy zapasowe** (spec, sekcja 4.4), gdy autor doda sceny `open` lub `generated` do bajki:
   - dla każdej takiej sceny przygotuj plik ujęć z 1–3 typowymi odpowiedziami dzieci,
   - wygeneruj je: `python -m bajka.illustrate SCENARIUSZ --batch ujecia_zapas.yaml --out zapas`,
   - zrób z każdej ilustracji klip `python -m bajka.motion zapas\NAZWA.png --out scenarios\clips\...`,
   - wpisz te klipy do `fallback_clips`.

- [ ] **Step 7: Commit**

```powershell
git add bajka/illustrate.py scenarios/pomiar_obrazow.yaml scenarios/karta_postaci.yaml tests/test_illustrate.py
git commit -m "feat: ilustracje scen w Azure AI Foundry z pomiarem czasu i trybem wsadowym"
git pull --rebase origin main; python -m pytest; git push origin main
```

Po pomiarze osobny commit z wybranymi obrazami referencyjnymi (`scenarios/ilustracje/ref_*.png`) i sekcją wyników w specu.

---

### Task 4: Wyobraźnia — pomysł dziecka na kwestię postaci i opis obrazu

**Files:**
- Create: `bajka/imagine.py`
- Test: `tests/test_imagine.py`

**Interfaces:**
- Consumes: `bajka.config`, `bajka.ports.Vision` (Task 1), `bajka.scenario.Scene`, `fill_prompt`, `load_scenario` (Task 2).
- Produces:
  - `ImagineSettings.from_env(env)` (zmienne `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`),
  - `AzureImaginer(client, deployment, hero, temperature=0.5)` z `from_settings(settings, hero)` i `imagine(scene, transcript) -> Vision`,
  - `parse_vision(content) -> Vision` (rzuca `ValueError` przy złym JSON),
  - `IMAGINE_PROMPT`, `RESPONSE_FORMAT` (structured outputs, `strict`).

- [ ] **Step 1: Napisz testy**

<!-- file: tests/test_imagine.py -->
```python
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from bajka.config import ConfigError
from bajka.imagine import AzureImaginer, ImagineSettings, main, parse_vision
from bajka.ports import Imaginer, Vision
from bajka.scenario import Scene

LLM_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
}
OPEN_SCENE = Scene(
    id="ozdoby",
    clip=Path("ozdoby.mp4"),
    kind="open",
    question="Jak udekorujemy ul Bzyczki na święto?",
    image_prompt="the beehive decorated for a party with {idea}",
)


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))])


def make_imaginer(content):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return AzureImaginer(client, deployment="gpt-4o-mini", hero="Lila Lupka, odkrywczyni"), completions


def answer(reply, idea):
    return json.dumps({"reply": reply, "idea": idea})


def test_imagine_returns_reply_and_idea():
    imaginer, _ = make_imaginer(answer("Tęczowe wstążki? Już rysuję!", "rainbow ribbons"))

    vision = imaginer.imagine(OPEN_SCENE, "tęczowymi wstążkami")

    assert isinstance(imaginer, Imaginer)
    assert vision == Vision(reply="Tęczowe wstążki? Już rysuję!", idea="rainbow ribbons")


def test_request_sends_hero_question_and_childs_words_with_strict_schema():
    imaginer, completions = make_imaginer(answer("Super!", "ribbons"))

    imaginer.imagine(OPEN_SCENE, "wstążkami")

    kwargs = completions.kwargs
    system, user = kwargs["messages"]
    assert kwargs["model"] == "gpt-4o-mini"
    assert "Lila Lupka" in system["content"]
    assert "Jak udekorujemy ul Bzyczki na święto?" in system["content"]
    assert "bez form zależnych od płci" in system["content"]
    assert user == {"role": "user", "content": "wstążkami"}
    schema = kwargs["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["required"] == ["reply", "idea"]


def test_unusable_idea_comes_back_empty():
    vision = parse_vision(answer("Hmm, narysuję coś innego!", ""))

    assert vision.idea == ""


def test_malformed_answer_is_an_error():
    with pytest.raises(ValueError):
        parse_vision("to nie jest JSON")
    with pytest.raises(ValueError):
        parse_vision(json.dumps(["reply", "idea"]))


def test_settings_use_the_same_azure_openai_variables_as_intent():
    settings = ImagineSettings.from_env(LLM_ENV)

    assert (settings.deployment, settings.api_version) == ("gpt-4o-mini", "2024-10-21")
    with pytest.raises(ConfigError, match="AZURE_OPENAI_ENDPOINT"):
        ImagineSettings.from_env({})


# Demo: python -m bajka.imagine


@pytest.fixture
def scenario_file(tmp_path, scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul Bzyczki na święto?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "the beehive decorated for a party with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["zapas.mp4"],
        "next": "las",
    }
    path = tmp_path / "bajka.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def llm_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in LLM_ENV.items():
        monkeypatch.setenv(name, value)


def use_fake_llm(monkeypatch, content):
    imaginer, completions = make_imaginer(content)
    monkeypatch.setattr(AzureImaginer, "from_settings", classmethod(lambda cls, settings, hero: imaginer))
    return completions


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, scenario_file, capsys):
    monkeypatch.chdir(tmp_path)
    for name in LLM_ENV:
        monkeypatch.delenv(name, raising=False)

    assert main([str(scenario_file), "wstążkami"]) == 2
    assert "AZURE_OPENAI_ENDPOINT" in capsys.readouterr().err


def test_demo_uses_first_open_scene_and_shows_image_prompt(llm_keys, monkeypatch, scenario_file, capsys):
    use_fake_llm(monkeypatch, answer("Tęczowe wstążki? Już rysuję!", "rainbow ribbons"))

    assert main([str(scenario_file), "tęczowymi wstążkami"]) == 0

    out = capsys.readouterr().out
    assert "Scena: ozdoby" in out
    assert "Postać: Tęczowe wstążki? Już rysuję!" in out
    assert "Obraz: the beehive decorated for a party with rainbow ribbons" in out


def test_demo_reports_unusable_idea(llm_keys, monkeypatch, scenario_file, capsys):
    use_fake_llm(monkeypatch, answer("Narysuję coś innego!", ""))

    assert main([str(scenario_file), "coś strasznego"]) == 0

    assert "nie do użycia" in capsys.readouterr().out


def test_demo_rejects_scene_without_question(llm_keys, monkeypatch, scenario_file, capsys):
    use_fake_llm(monkeypatch, answer("x", "y"))

    assert main([str(scenario_file), "cokolwiek", "--scene", "las"]) == 2
    assert "las" in capsys.readouterr().err
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_imagine.py -v`
Expected: `ModuleNotFoundError: No module named 'bajka.imagine'`

- [ ] **Step 3: Napisz `bajka/imagine.py`**

<!-- file: bajka/imagine.py -->
```python
"""Pomysł dziecka z pytania otwartego → kwestia postaci i opis ilustracji (Azure OpenAI).

Moduł spełnia kontrakt `bajka.ports.Imaginer`. Korzysta z tych samych zmiennych AZURE_OPENAI_* co intent.py.
Test promptu bez reszty aplikacji: python -m bajka.imagine SCENARIUSZ "wypowiedź dziecka" [--scene ID]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bajka.config import ConfigError, load_env, require
from bajka.ports import Vision
from bajka.scenario import Scene, ScenarioError, fill_prompt, load_scenario

IMAGINE_PROMPT = """\
Grasz postać z interaktywnej bajki dla dzieci w wieku 4-8 lat. Twoja postać: {hero}
Przed chwilą w bajce padło pytanie otwarte do dziecka siedzącego przed ekranem: "{question}"
Dziecko odpowiada własnym pomysłem. Zaraz narysujesz ten pomysł i pokażesz go na ekranie.

Zwróć dwa pola:
1. "reply": radosna reakcja twojej postaci na pomysł dziecka, zapowiadająca, że go rysujesz.
   Po polsku, w pierwszej osobie (w rodzaju zgodnym z opisem postaci), najwyżej dwa krótkie zdania,
   prostymi słowami, bez straszenia i bez emotikon. Do dziecka zwracaj się bez form zależnych od płci:
   zamiast "wymyśliłeś" czy "wymyśliłaś" mów "świetny pomysł", "brawo". Nigdy nie wychodź z roli.
2. "idea": pomysł dziecka jako krótki opis tego, co ma się znaleźć na ilustracji, PO ANGIELSKU,
   najwyżej 20 słów. Zachowaj to, co powiedziało dziecko, i nie dodawaj imion ani danych osobowych.
   Jeśli pomysł jest straszny, brutalny, nieodpowiedni dla małych dzieci albo zupełnie nie do
   narysowania, zwróć pusty tekst "" — wtedy bajka pokaże przygotowaną wcześniej ilustrację.
"""

RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "pomysl",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"reply": {"type": "string"}, "idea": {"type": "string"}},
            "required": ["reply", "idea"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class ImagineSettings:
    endpoint: str
    api_key: str
    deployment: str  # nazwa wdrożenia w Azure, nie nazwa modelu
    api_version: str = "2024-10-21"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ImagineSettings:
        require(env, "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
        return cls(
            endpoint=env["AZURE_OPENAI_ENDPOINT"],
            api_key=env["AZURE_OPENAI_API_KEY"],
            deployment=env["AZURE_OPENAI_DEPLOYMENT"],
            api_version=env.get("AZURE_OPENAI_API_VERSION") or cls.api_version,
        )


def parse_vision(content: str) -> Vision:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError(f"LLM zwrócił {type(data).__name__} zamiast obiektu JSON")
    return Vision(reply=str(data.get("reply", "")).strip(), idea=str(data.get("idea", "")).strip())


class AzureImaginer:
    def __init__(self, client: Any, deployment: str, hero: str, temperature: float = 0.5) -> None:
        self._client = client
        self._deployment = deployment
        self._hero = hero
        self._temperature = temperature

    @classmethod
    def from_settings(cls, settings: ImagineSettings, hero: str) -> AzureImaginer:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            timeout=10.0,
            max_retries=1,
        )
        return cls(client, settings.deployment, hero)

    def imagine(self, scene: Scene, transcript: str) -> Vision:
        system = IMAGINE_PROMPT.format(hero=self._hero.strip(), question=scene.question)
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": transcript}],
            response_format=RESPONSE_FORMAT,
            temperature=self._temperature,
            max_tokens=200,
        )
        return parse_vision(response.choices[0].message.content or "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.imagine", description="Test zamiany pomysłu dziecka na kwestię postaci i opis obrazu."
    )
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument("transcript", help="wypowiedź dziecka, np. \"tęczowymi wstążkami\"")
    parser.add_argument("--scene", help="scena z pytaniem (domyślnie pierwsza scena otwarta)")
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        settings = ImagineSettings.from_env(load_env())
    except (ScenarioError, ConfigError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    open_scenes = [scene.id for scene in scenario.scenes.values() if scene.kind == "open"]
    scene_id = args.scene or (open_scenes[0] if open_scenes else scenario.start)
    scene = scenario.scenes.get(scene_id)
    if scene is None or not scene.question:
        print(f"Scena '{scene_id}' nie istnieje albo nie zadaje pytania", file=sys.stderr)
        return 2

    imaginer = AzureImaginer.from_settings(settings, scenario.hero)
    print(f"Scena: {scene.id} — {scene.question}")
    print(f"Dziecko: {args.transcript!r}", flush=True)
    started = time.perf_counter()
    try:
        vision = imaginer.imagine(scene, args.transcript)
    except Exception as exc:  # demo ma pokazać każdy błąd Azure OpenAI, a nie wywrócić się
        print(f"Błąd Azure OpenAI: {exc}", file=sys.stderr)
        return 1
    print(f"Postać: {vision.reply}")
    if vision.idea:
        print(f"Pomysł: {vision.idea}")
        if scene.image_prompt:
            print(f"Obraz: {fill_prompt(scene.image_prompt, {'idea': vision.idea})}")
    else:
        print("Pomysł: nie do użycia (bajka pokaże klip zapasowy)")
    print(f"({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_imagine.py -v`
Expected: `9 passed`

- [ ] **Step 5: Sprawdź prompt na prawdziwym Azure OpenAI** (wymaga `AZURE_OPENAI_*` w `.env`)

1. **Pomysł do narysowania:**
   `python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "złota korona i lizak"`
   Expected: `Scena: skarb — …`, potem:
   - `Postać:` z radosną reakcją bez form zależnych od płci,
   - `Pomysł:` po angielsku, np. `a golden crown and a lollipop`,
   - `Obraz: a little fox in a cozy cave … discovering a treasure: a golden crown and a lollipop`.
2. **Pomysł nie do narysowania:**
   `python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "potwór cały we krwi"`
   Expected: `Pomysł: nie do użycia (bajka pokaże klip zapasowy)`.
3. **Strojenie.** Jeśli odpowiedzi się rozjeżdżają, stroimy `IMAGINE_PROMPT` i powtarzamy oba polecenia.

- [ ] **Step 6: Commit**

```powershell
git add bajka/imagine.py tests/test_imagine.py
git commit -m "feat: pomysł dziecka na kwestię postaci i opis ilustracji przez Azure OpenAI"
git pull --rebase origin main; python -m pytest; git push origin main
```

---

### Task 5: Silnik — sceny z pytaniem otwartym

**Files:**
- Modify: `bajka/engine.py` (4 punktowe zmiany; kod głosowania osoby A zostaje)
- Create: `tests/live_fakes.py`
- Test: `tests/test_engine_open.py`

**Interfaces:**
- Consumes: kontrakty z Taska 1, `Scene.kind`, `drawing`, `image_prompt`, `remember`, `default_idea`, `fallback_clips`, `next`, `Scenario.needs_live_images` i `fill_prompt` z Taska 2.
- Produces:
  - **`StoryEngine(..., meter=None, imaginer=None, illustrator=None, animator=None, image_timeout_s=25.0, rng=None)`.**
    - Rzuca `ValueError`, gdy scenariusz ma sceny rysowane na żywo, a brakuje modułów.
    - Ma właściwość `memory -> Mapping[str, str]`.
  - **`FALLBACK_VISION_LINE = "Zobacz, co mam w wyobraźni!"`.**

**Kontrakt zachowania sceny `open`:**
1. Klip i pętla `idle`, potem nasłuch z dopytaniem (`reprompt`, limit `max_reprompts`).
2. Gdy jest pomysł:
   - zapamiętanie go pod kluczem `remember`,
   - pętla `drawing`,
   - start rysowania w puli wątków,
   - kwestia `reply` przez TTS,
   - odtworzenie klipu, gdy rysowanie zdąży przed terminem `image_timeout_s` liczonym od startu rysowania.
3. Cisza po wszystkich próbach, błąd LLM albo pusty `idea`: `default_idea`, stała kwestia awaryjna i klip zapasowy, bez rysowania.
4. Błąd albo przekroczony czas rysowania: stała kwestia awaryjna i klip zapasowy. Pomysł zostaje w pamięci.
5. Na końcu `run()` pula jest zamykana bez czekania na spóźnione obrazy.

- [ ] **Step 1: Napisz atrapy i testy**

<!-- file: tests/live_fakes.py -->
```python
"""Atrapy modułów do testów silnika ze scenami generowanymi na żywo."""

from pathlib import Path


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, clip):
        self.calls.append(("play", clip.name))

    def loop(self, clip):
        self.calls.append(("loop", clip.name))


class FakeListener:
    """Zwraca kolejne odpowiedzi; wyjątek z listy zostaje rzucony."""

    def __init__(self, *answers):
        self._answers = list(answers)

    def listen(self):
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeVoice:
    def __init__(self):
        self.lines = []

    def say(self, text):
        self.lines.append(text)


class FakeResolver:
    """Mapuje transkrypcję na Interpretation."""

    def __init__(self, answers):
        self._answers = answers

    def resolve(self, scene, transcript):
        return self._answers[transcript]


class FakeImaginer:
    """Mapuje transkrypcję na Vision albo wyjątek."""

    def __init__(self, answers=None):
        self._answers = answers or {}
        self.calls = []

    def imagine(self, scene, transcript):
        self.calls.append((scene.id, transcript))
        answer = self._answers[transcript]
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeIllustrator:
    """Zapamiętuje prompty; może rzucić wyjątkiem albo czekać na sygnał (symulacja wolnego Azure)."""

    def __init__(self, error=None, gate=None):
        self.prompts = []
        self._error = error
        self._gate = gate

    def draw(self, prompt):
        self.prompts.append(prompt)
        if self._gate is not None:
            self._gate.wait(timeout=5)
        if self._error is not None:
            raise self._error
        return Path(f"obraz_{len(self.prompts)}.png")


class FakeAnimator:
    def __init__(self, error=None):
        self._error = error

    def animate(self, image):
        if self._error is not None:
            raise self._error
        return image.with_suffix(".mp4")
```

<!-- file: tests/test_engine_open.py -->
```python
import threading
from pathlib import Path

import pytest
from live_fakes import (
    FakeAnimator,
    FakeIllustrator,
    FakeImaginer,
    FakeListener,
    FakePlayer,
    FakeResolver,
    FakeVoice,
)

from bajka.engine import FALLBACK_VISION_LINE, StoryEngine
from bajka.ports import Interpretation, Vision
from bajka.scenario import parse_scenario

REPROMPT = "Kwiatki, wstążki, a może coś innego?"
REPLY = "Tęczowe wstążki? Już rysuję!"
CHOOSE_FOREST = FakeResolver({"las": Interpretation("las", "Las!")})


@pytest.fixture
def live_scenario(scenario_dict):
    """intro → (las) → ozdoby [pytanie otwarte] → las."""
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul Bzyczki na święto?",
        "reprompt": REPROMPT,
        "image_prompt": "the beehive decorated for a party with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers and ribbons",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "las",
    }
    return parse_scenario(scenario_dict, base_dir=Path("film"))


def make_engine(scenario, listener, imaginer=None, illustrator=None, animator=None, timeout_s=5.0):
    player, voice = FakePlayer(), FakeVoice()
    engine = StoryEngine(
        scenario,
        player,
        listener,
        voice,
        CHOOSE_FOREST,
        imaginer=imaginer or FakeImaginer({"wstążkami": Vision(REPLY, "rainbow ribbons")}),
        illustrator=illustrator or FakeIllustrator(),
        animator=animator or FakeAnimator(),
        image_timeout_s=timeout_s,
    )
    return engine, player, voice


def test_open_scene_draws_childs_idea_while_hero_talks(live_scenario):
    illustrator = FakeIllustrator()
    engine, player, voice = make_engine(live_scenario, FakeListener("las", "wstążkami"), illustrator=illustrator)

    assert engine.run() == ["intro", "ozdoby", "las"]

    assert player.calls == [
        ("play", "intro.mp4"),
        ("loop", "intro_idle.mp4"),
        ("play", "ozdoby.mp4"),
        ("loop", "ozdoby_idle.mp4"),
        ("loop", "rysuje.mp4"),
        ("play", "obraz_1.mp4"),
        ("play", "las.mp4"),
    ]
    assert voice.lines == ["Las!", REPLY]
    assert illustrator.prompts == ["the beehive decorated for a party with rainbow ribbons"]
    assert engine.memory == {"ozdoby": "rainbow ribbons"}


def test_silence_reprompts_then_draws(live_scenario):
    engine, player, voice = make_engine(live_scenario, FakeListener("las", None, "wstążkami"))

    engine.run()

    assert voice.lines == ["Las!", REPROMPT, REPLY]
    assert ("play", "obraz_1.mp4") in player.calls


def test_after_max_reprompts_default_idea_and_fallback_clip(live_scenario):
    illustrator = FakeIllustrator()
    engine, player, voice = make_engine(live_scenario, FakeListener("las", None, None, None), illustrator=illustrator)

    engine.run()

    assert voice.lines == ["Las!", REPROMPT, REPROMPT, FALLBACK_VISION_LINE]
    assert player.calls[-2:] == [("play", "ozdoby_zapas.mp4"), ("play", "las.mp4")]
    assert illustrator.prompts == []
    assert engine.memory == {"ozdoby": "flowers and ribbons"}


def test_unusable_idea_uses_default_and_fallback_clip(live_scenario):
    imaginer = FakeImaginer({"coś strasznego": Vision("Narysuję coś innego!", "")})
    engine, player, voice = make_engine(live_scenario, FakeListener("las", "coś strasznego"), imaginer=imaginer)

    engine.run()

    assert voice.lines == ["Las!", FALLBACK_VISION_LINE]
    assert ("play", "ozdoby_zapas.mp4") in player.calls
    assert engine.memory == {"ozdoby": "flowers and ribbons"}


def test_imaginer_error_uses_fallback_clip(live_scenario):
    imaginer = FakeImaginer({"wstążkami": TimeoutError("Azure OpenAI nie odpowiada")})
    engine, player, voice = make_engine(live_scenario, FakeListener("las", "wstążkami"), imaginer=imaginer)

    assert engine.run() == ["intro", "ozdoby", "las"]

    assert voice.lines == ["Las!", FALLBACK_VISION_LINE]
    assert ("play", "ozdoby_zapas.mp4") in player.calls


@pytest.mark.parametrize(
    "illustrator, animator",
    [
        (FakeIllustrator(error=RuntimeError("content_policy_violation")), FakeAnimator()),
        (FakeIllustrator(), FakeAnimator(error=RuntimeError("ffmpeg"))),
    ],
    ids=["blad_obrazu", "blad_ffmpeg"],
)
def test_render_error_after_hero_reply_shows_fallback(live_scenario, illustrator, animator):
    engine, player, voice = make_engine(
        live_scenario, FakeListener("las", "wstążkami"), illustrator=illustrator, animator=animator
    )

    engine.run()

    assert voice.lines == ["Las!", REPLY, FALLBACK_VISION_LINE]
    assert player.calls[-2:] == [("play", "ozdoby_zapas.mp4"), ("play", "las.mp4")]
    assert engine.memory == {"ozdoby": "rainbow ribbons"}  # pomysł zostaje, nawet gdy obraz zawiódł


def test_slow_drawing_times_out_to_fallback(live_scenario):
    gate = threading.Event()
    illustrator = FakeIllustrator(gate=gate)
    engine, player, voice = make_engine(
        live_scenario, FakeListener("las", "wstążkami"), illustrator=illustrator, timeout_s=0.05
    )
    try:
        engine.run()
    finally:
        gate.set()  # wypuszczamy wątek rysowania

    assert voice.lines[-1] == FALLBACK_VISION_LINE
    assert ("play", "ozdoby_zapas.mp4") in player.calls


def test_open_scenario_without_live_image_modules_is_refused(live_scenario):
    with pytest.raises(ValueError, match="illustrator"):
        StoryEngine(live_scenario, FakePlayer(), FakeListener(), FakeVoice(), CHOOSE_FOREST)


def test_classic_scenario_needs_no_live_image_modules(scenario):
    engine = StoryEngine(scenario, FakePlayer(), FakeListener("las"), FakeVoice(), CHOOSE_FOREST)

    assert engine.run() == ["intro", "las"]
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_engine_open.py -v`
Expected: `ImportError: cannot import name 'FALLBACK_VISION_LINE' from 'bajka.engine'`

- [ ] **Step 3: Nagłówek i importy — w `bajka/engine.py` zamień:**

<!-- edit: bajka/engine.py -->
```python
"""Silnik bajki: odtwarza sceny, słucha dziecka (albo całej widowni) i wybiera kolejny klip."""

from __future__ import annotations

import logging

from bajka.ports import IntentResolver, Interpretation, Listener, Player, ShoutMeter, Voice
from bajka.scenario import Choice, Scenario, Scene

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"
```

na:

```python
"""Silnik bajki: odtwarza sceny, słucha dziecka (albo całej widowni) i wybiera kolejny klip.

Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo: Imaginer → Illustrator → Animator.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from bajka.ports import (
    Animator,
    Illustrator,
    Imaginer,
    IntentResolver,
    Interpretation,
    Listener,
    Player,
    ShoutMeter,
    Vision,
    Voice,
)
from bajka.scenario import Choice, Scenario, Scene, fill_prompt

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"
FALLBACK_VISION_LINE = "Zobacz, co mam w wyobraźni!"
```

- [ ] **Step 4: Nowe parametry konstruktora — zamień:**

<!-- edit: bajka/engine.py -->
```python
        max_reprompts: int = 2,
        meter: ShoutMeter | None = None,
    ) -> None:
        self._scenario = scenario
```

na:

```python
        max_reprompts: int = 2,
        meter: ShoutMeter | None = None,
        imaginer: Imaginer | None = None,
        illustrator: Illustrator | None = None,
        animator: Animator | None = None,
        image_timeout_s: float = 25.0,
        rng: random.Random | None = None,
    ) -> None:
        missing = [name for name, module in (("imaginer", imaginer), ("illustrator", illustrator),
                                             ("animator", animator)) if module is None]  # fmt: skip
        if scenario.needs_live_images and missing:
            raise ValueError("Scenariusz ma sceny rysowane na żywo, a brakuje modułów: " + ", ".join(missing))
        self._imaginer = imaginer
        self._illustrator = illustrator
        self._animator = animator
        self._image_timeout_s = image_timeout_s
        self._rng = rng or random.Random()
        self._memory: dict[str, str] = {}
        self._scenario = scenario
```

- [ ] **Step 5: Pętla bajki z pulą wątków i sceną `open` — zamień:**

<!-- edit: bajka/engine.py -->
```python
    def run(self) -> list[str]:
        """Odtwarza bajkę i zwraca identyfikatory odwiedzonych scen."""
        visited: list[str] = []
        scene = self._scenario.scene(self._scenario.start)
        while True:
            visited.append(scene.id)
            log.info("Scena: %s", scene.id)
            self._player.play(scene.clip)
            if scene.is_ending:
                return visited
            if scene.idle is not None:
                self._player.loop(scene.idle)
            choice = self._vote(scene) if scene.vote and self._meter is not None else self._ask(scene)
            scene = self._scenario.scene(choice.next)
```

na:

```python
    @property
    def memory(self) -> Mapping[str, str]:
        """Pomysły dziecka zapamiętane w tym seansie (klucz `remember` → opis po angielsku)."""
        return dict(self._memory)

    def run(self) -> list[str]:
        """Odtwarza bajkę i zwraca identyfikatory odwiedzonych scen."""
        visited: list[str] = []
        scene = self._scenario.scene(self._scenario.start)
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rysowanie")
        try:
            while True:
                visited.append(scene.id)
                log.info("Scena: %s", scene.id)
                self._player.play(scene.clip)
                if scene.is_ending:
                    return visited
                if scene.idle is not None:
                    self._player.loop(scene.idle)
                if scene.kind == "open":
                    self._ask_open(scene)
                    scene = self._scenario.scene(scene.next)
                    continue
                choice = self._vote(scene) if scene.vote and self._meter is not None else self._ask(scene)
                scene = self._scenario.scene(choice.next)
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)  # nie czekamy na spóźnione obrazy
```

- [ ] **Step 6: Obsługa sceny otwartej — dopisz metody za `_ask`; zamień:**

<!-- edit: bajka/engine.py -->
```python
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _listen(self) -> str | None:
```

na:

```python
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _ask_open(self, scene: Scene) -> None:
        vision = self._hear_idea(scene)
        if vision is None:
            self._memory[scene.remember] = scene.default_idea
            self._say(FALLBACK_VISION_LINE)
            self._player.play(self._fallback_clip(scene))
            return
        self._memory[scene.remember] = vision.idea
        if scene.drawing is not None:
            self._player.loop(scene.drawing)
        prompt = fill_prompt(scene.image_prompt, {**self._memory, "idea": vision.idea})
        deadline = time.monotonic() + self._image_timeout_s
        future = self._pool.submit(self._render, prompt)
        if vision.reply:
            self._say(vision.reply)  # postać mówi, a obraz w tym czasie się rysuje
        self._player.play(self._clip_or_fallback(scene, future, deadline))

    def _hear_idea(self, scene: Scene) -> Vision | None:
        """Pomysł dziecka albo None: cisza po wszystkich dopytaniach, błąd LLM, pomysł nie do narysowania."""
        for attempt in range(self._max_reprompts + 1):
            transcript = self._listen()
            if transcript:
                try:
                    vision = self._imaginer.imagine(scene, transcript)
                except Exception:
                    log.exception("Błąd LLM przy pomyśle dziecka, pokazuję klip zapasowy")
                    return None
                log.info("Pomysł: %r | %s", vision.idea, vision.reply)
                return vision if vision.idea else None
            if attempt < self._max_reprompts:
                self._say(scene.reprompt)
        return None

    def _render(self, prompt: str) -> Path:
        started = time.monotonic()
        clip = self._animator.animate(self._illustrator.draw(prompt))
        log.info("Narysowane w %.1f s: %s", time.monotonic() - started, clip.name)
        return clip

    def _clip_or_fallback(self, scene: Scene, future: Future[Path], deadline: float) -> Path:
        try:
            return future.result(timeout=max(0.0, deadline - time.monotonic()))
        except TimeoutError:
            log.warning("Rysowanie trwa dłużej niż %.0f s, pokazuję klip zapasowy", self._image_timeout_s)
        except Exception:
            log.exception("Błąd rysowania, pokazuję klip zapasowy")
        self._say(FALLBACK_VISION_LINE)
        return self._fallback_clip(scene)

    def _fallback_clip(self, scene: Scene) -> Path:
        return self._rng.choice(scene.fallback_clips)

    def _listen(self) -> str | None:
```

- [ ] **Step 7: Uruchom testy silnika (także głosowania i dotychczasowe)**

Run: `python -m pytest tests/test_engine_open.py tests/test_engine.py tests/test_vote.py -v`
Expected: `tests/test_engine_open.py` — `10 passed` w niecałą sekundę; pozostałe bez zmian.

- [ ] **Step 8: Commit**

```powershell
git add bajka/engine.py tests/live_fakes.py tests/test_engine_open.py
git commit -m "feat: silnik rysuje pomysł dziecka na żywo z limitem czasu i klipem zapasowym"
git pull --rebase origin main; python -m pytest; git push origin main
```

---

### Task 6: Podpięcie w aplikacji, zaślepki i dokumentacja

**Files:**
- Modify: `bajka/app.py` (5 punktowych zmian), `bajka/placeholders.py` (osoba B, 1 zmiana), `.env.example`, `docs/PODZIAL_PRACY.md`, `README.md`
- Test: `tests/test_app_live.py`

**Interfaces:**
- Consumes: `AzureImaginer`, `ImagineSettings` (Task 4), `AzureIllustrator`, `ImageSettings` (Task 3), `FfmpegAnimator`, `MotionSettings` (Task 1), `Scenario.needs_live_images`, `style`, `references` (Task 2), nowe parametry `StoryEngine` (Task 5).
- Produces:
  - `LiveImages(imaginer, illustrator, animator, timeout_s)`,
  - `prepare_session_dir(base=None) -> Path`,
  - `build_live_images(env, scenario, session_dir=prepare_session_dir) -> LiveImages`. Rzuca `ConfigError`, gdy brakuje kluczy albo ffmpeg.
  - `planned_clips` planuje też pętle `drawing` (ciche) i `fallback_clips` (z dźwiękiem), każdy plik raz.

- [ ] **Step 1: Napisz testy**

<!-- file: tests/test_app_live.py -->
```python
from pathlib import Path

import pytest
import yaml

from bajka.app import LiveImages, build_live_images, main, prepare_session_dir
from bajka.config import ConfigError
from bajka.placeholders import planned_clips
from bajka.ports import Animator, Illustrator, Imaginer
from bajka.scenario import parse_scenario

FULL_ENV = {
    "AZURE_IMAGE_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_IMAGE_API_KEY": "klucz-obrazow",
    "AZURE_IMAGE_DEPLOYMENT": "gpt-image-2",
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
}


@pytest.fixture
def live_dict(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul Bzyczki na święto?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "the beehive decorated for a party with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "las",
    }
    return scenario_dict


@pytest.fixture
def live_scenario(live_dict):
    return parse_scenario(live_dict, base_dir=Path("film"))


def test_classic_scenario_builds_no_live_modules(scenario):
    assert build_live_images({}, scenario) == LiveImages()


def test_live_scenario_lists_missing_image_keys(live_scenario, tmp_path):
    with pytest.raises(ConfigError) as exc:
        build_live_images({}, live_scenario, lambda: tmp_path)

    assert "AZURE_IMAGE_ENDPOINT" in str(exc.value)


def test_live_scenario_needs_ffmpeg(live_scenario, monkeypatch, tmp_path):
    monkeypatch.setattr("bajka.app.shutil.which", lambda name: None)

    with pytest.raises(ConfigError, match="ffmpeg"):
        build_live_images(FULL_ENV, live_scenario, lambda: tmp_path)


def test_live_scenario_builds_modules_that_fulfil_contracts(live_scenario, monkeypatch, tmp_path):
    monkeypatch.setattr("bajka.app.shutil.which", lambda name: "ffmpeg")

    live = build_live_images({**FULL_ENV, "BAJKA_IMAGE_TIMEOUT_S": "20"}, live_scenario, lambda: tmp_path)

    assert isinstance(live.imaginer, Imaginer)
    assert isinstance(live.illustrator, Illustrator)
    assert isinstance(live.animator, Animator)
    assert live.timeout_s == 20.0


def test_new_session_dir_removes_pictures_of_previous_sessions(tmp_path):
    old = prepare_session_dir(tmp_path / "bajka")
    (old / "obraz.png").write_bytes(b"PNG")

    new = prepare_session_dir(tmp_path / "bajka")

    assert new.is_dir()
    assert not old.exists()


def test_main_with_open_scene_and_no_image_keys_exits_with_code_2(tmp_path, monkeypatch, live_dict, caplog):
    monkeypatch.chdir(tmp_path)  # w katalogu testu nie ma pliku .env
    for name in FULL_ENV:
        monkeypatch.delenv(name, raising=False)
    for path, _, _ in planned_clips(parse_scenario(live_dict, base_dir=tmp_path)):
        path.touch()
    scenario_file = tmp_path / "bajka.yaml"
    scenario_file.write_text(yaml.safe_dump(live_dict, allow_unicode=True), encoding="utf-8")

    assert main([str(scenario_file), "--text", "--no-llm"]) == 2
    assert "AZURE_IMAGE_ENDPOINT" in caplog.text


# Klipy-zaślepki dla scen otwartych


def test_open_scene_gets_silent_drawing_loop_and_fallback_clips_with_sound(live_scenario):
    tone = {path.name: with_tone for path, _, with_tone in planned_clips(live_scenario)}

    assert tone["ozdoby.mp4"] is True
    assert tone["ozdoby_idle.mp4"] is False
    assert tone["rysuje.mp4"] is False
    assert tone["ozdoby_zapas.mp4"] is True


def test_shared_drawing_loop_is_planned_once(live_dict):
    live_dict["scenes"]["ozdoby2"] = {**live_dict["scenes"]["ozdoby"], "clip": "ozdoby2.mp4", "remember": "druga"}
    live_dict["scenes"]["ozdoby"]["next"] = "ozdoby2"

    names = [path.name for path, _, _ in planned_clips(parse_scenario(live_dict, base_dir=Path("film")))]

    assert names.count("rysuje.mp4") == 1
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_app_live.py -v`
Expected: `ImportError: cannot import name 'LiveImages' from 'bajka.app'`

- [ ] **Step 3: Importy w `bajka/app.py` — zamień:**

<!-- edit: bajka/app.py -->
```python
import argparse
import logging
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING
```

na:

```python
import argparse
import logging
import shutil
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
```

oraz zamień:

<!-- edit: bajka/app.py -->
```python
from bajka.ports import IntentResolver, Listener, ShoutMeter, Voice
from bajka.safety import SafeReplyResolver
from bajka.scenario import ScenarioError, load_scenario, missing_media
```

na:

```python
from bajka.ports import Animator, Illustrator, Imaginer, IntentResolver, Listener, ShoutMeter, Voice
from bajka.safety import SafeReplyResolver
from bajka.scenario import Scenario, ScenarioError, load_scenario, missing_media
```

- [ ] **Step 4: Budowanie modułów rysowania — dopisz za `build_meter`; zamień:**

<!-- edit: bajka/app.py -->
```python
    return MicrophoneMeter(VoteSettings.from_env(env))


def main(
```

na:

```python
    return MicrophoneMeter(VoteSettings.from_env(env))


@dataclass(frozen=True)
class LiveImages:
    """Moduły rysowania na żywo; puste, gdy scenariusz nie ma scen rysowanych na żywo."""

    imaginer: Imaginer | None = None
    illustrator: Illustrator | None = None
    animator: Animator | None = None
    timeout_s: float = 25.0


def prepare_session_dir(base: Path | None = None) -> Path:
    """Nowy katalog na ilustracje seansu. Ilustracje poprzednich seansów usuwamy (prywatność dzieci)."""
    base = base or Path(tempfile.gettempdir()) / "bajka"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="seans_", dir=base))


def build_live_images(
    env: Mapping[str, str],
    scenario: Scenario,
    session_dir: Callable[[], Path] = prepare_session_dir,
) -> LiveImages:
    if not scenario.needs_live_images:
        return LiveImages()
    from bajka.illustrate import AzureIllustrator, ImageSettings
    from bajka.imagine import AzureImaginer, ImagineSettings
    from bajka.motion import FfmpegAnimator, MotionSettings

    images = ImageSettings.from_env(env)
    imagine = ImagineSettings.from_env(env)
    motion = MotionSettings.from_env(env)
    if shutil.which("ffmpeg") is None:
        raise ConfigError("Sceny rysowane na żywo potrzebują ffmpeg w PATH (Windows: winget install --id Gyan.FFmpeg -e)")
    directory = session_dir()
    log.info("Ilustracje seansu: %s", directory)
    return LiveImages(
        imaginer=AzureImaginer.from_settings(imagine, scenario.hero),
        illustrator=AzureIllustrator.from_settings(images, directory, scenario.style, scenario.references),
        animator=FfmpegAnimator.from_settings(motion, directory),
        timeout_s=float(images.timeout_s),
    )


def main(
```

- [ ] **Step 5: Wywołanie w `main` — zamień:**

<!-- edit: bajka/app.py -->
```python
        resolver = build_resolver(env, backend, not args.no_llm, scenario.hero)
    except (ConfigError, FoundryError, VoiceNotFoundError, OSError) as exc:
```

na:

```python
        resolver = build_resolver(env, backend, not args.no_llm, scenario.hero)
        live = build_live_images(env, scenario)
    except (ConfigError, FoundryError, VoiceNotFoundError, OSError) as exc:
```

oraz zamień:

<!-- edit: bajka/app.py -->
```python
    engine = StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=max_reprompts, meter=meter)
```

na:

```python
    engine = StoryEngine(
        scenario,
        player,
        listener,
        voice,
        resolver,
        max_reprompts=max_reprompts,
        meter=meter,
        imaginer=live.imaginer,
        illustrator=live.illustrator,
        animator=live.animator,
        image_timeout_s=live.timeout_s,
    )
```

- [ ] **Step 6: Zaślepki nowych klipów — w `bajka/placeholders.py` zamień:**

<!-- edit: bajka/placeholders.py -->
```python
def planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]:
    """(ścieżka, kolor, czy z dźwiękiem) — klip sceny ma ton, pętla oczekiwania jest cicha."""
    clips = []
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        clips.append((scene.clip, color, True))
        if scene.idle is not None:
            clips.append((scene.idle, color, False))
    return clips
```

na:

```python
def planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]:
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen i zapasowe mają ton, pętle (oczekiwanie, rysowanie) są ciche."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        tracks = [(scene.clip, True), (scene.idle, False), (scene.drawing, False)]
        tracks += [(path, True) for path in scene.fallback_clips]
        for path, with_tone in tracks:
            if path is not None and path not in clips:  # wspólna pętla rysowania tylko raz
                clips[path] = (path, color, with_tone)
    return list(clips.values())
```

- [ ] **Step 7: Uruchom wszystkie testy**

Run: `python -m pytest`
Expected:
- `tests/test_app_live.py` — `8 passed`,
- cały zestaw przechodzi (w dniu pisania planu: `262 passed`).

- [ ] **Step 8: Ustawienia — dopisz na końcu `.env.example`:**

<!-- append: .env.example -->
```ini

# --- bajka/illustrate.py: ilustracje rysowane na żywo (tylko scenariusze ze scenami kind: open/generated) ---
# Azure AI Foundry → wdrożenie modelu obrazu (np. gpt-image-2) → "Klucze i punkt końcowy"
AZURE_IMAGE_ENDPOINT=https://twoj-zasob.openai.azure.com/
AZURE_IMAGE_API_KEY=
AZURE_IMAGE_DEPLOYMENT=gpt-image-2
AZURE_IMAGE_API_VERSION=2025-04-01-preview
BAJKA_IMAGE_SIZE=1536x1024
BAJKA_IMAGE_QUALITY=medium
BAJKA_IMAGE_TIMEOUT_S=25

# --- bajka/imagine.py: pomysł dziecka → kwestia postaci i opis obrazu (zmienne AZURE_OPENAI_* z sekcji intent.py) ---

# --- bajka/motion.py: ruch kamery na ilustracji (wymaga ffmpeg w PATH) ---
BAJKA_MOTION_SECONDS=6
```

- [ ] **Step 9: Podział pracy — w `docs/PODZIAL_PRACY.md` zamień:**

<!-- edit: docs/PODZIAL_PRACY.md -->
```markdown
**Osoba B — „oko i głos”**: wszystko, co dziecko widzi i słyszy.
```

na:

```markdown
**Osoba B — „oko i głos”**: wszystko, co dziecko widzi i słyszy.
**Osoba C — „obraz na żywo”**: ilustracje rysowane z pomysłów dziecka ([projekt](superpowers/specs/2026-10-16-flow-filmu-design.md), [plan](superpowers/plans/2026-10-16-obraz-na-zywo.md)).
```

oraz zamień:

<!-- edit: docs/PODZIAL_PRACY.md -->
```markdown
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |
```

na:

```markdown
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |
| [`bajka/imagine.py`](../bajka/imagine.py) — pomysł dziecka → kwestia postaci + opis obrazu | `Imaginer` | C | `python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "złota korona"` | `tests/test_imagine.py` |
| [`bajka/illustrate.py`](../bajka/illustrate.py) — opis → ilustracja (Azure AI Foundry) | `Illustrator` | C | `python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml "a fox"` | `tests/test_illustrate.py` |
| [`bajka/motion.py`](../bajka/motion.py) — ilustracja → klip z ruchem kamery (ffmpeg) | `Animator` | C | `python -m bajka.motion obraz.png` | `tests/test_motion.py` |
```

- [ ] **Step 10: README — w sekcji „Sprawdzanie modułów osobno” zamień:**

<!-- edit: README.md -->
````markdown
python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4   # klip → pętla (VLC)
```
````

na:

````markdown
python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4   # klip → pętla (VLC)
python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "złota korona"   # pomysł → kwestia + opis obrazu
python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml "a fox"     # opis → ilustracja (Azure AI Foundry)
python -m bajka.motion obraz.png                                         # ilustracja → klip z ruchem kamery
```

Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo; mechanikę pokazuje
[`scenarios/rysowanie_na_zywo.yaml`](scenarios/rysowanie_na_zywo.yaml), a zasady i dobór modeli
[projekt flow filmu](docs/superpowers/specs/2026-10-16-flow-filmu-design.md).
````

- [ ] **Step 11: Próba end-to-end** (wymaga VLC, ffmpeg i kluczy `AZURE_IMAGE_*` oraz `AZURE_OPENAI_*` w `.env`)

1. **Zaślepki:**
   `python -m bajka.placeholders scenarios/rysowanie_na_zywo.yaml`
   Expected: tworzy m.in. `clips\rysowanie\rysuje.mp4` i `clips\rysowanie\skarb_zapas.mp4`.
2. **Uruchomienie:**
   `python -m bajka scenarios/rysowanie_na_zywo.yaml --text --windowed --no-llm`
3. **Przebieg:**
   - wpisz `jaskinia`, potem `złoty smok z kryształów`,
   - Expected w logu: `Ilustracje seansu: …\bajka\seans_…`, `Pomysł: 'a golden dragon made of crystals' | …`, `Narysowane w NN.N s: obraz_….mp4`,
   - w oknie pętla „rysuje”, potem klip z ilustracją.
4. **Zapas:** uruchom ponownie z `$env:BAJKA_IMAGE_TIMEOUT_S = "1"`.
   Expected: `Rysowanie trwa dłużej niż 1 s, pokazuję klip zapasowy`, w konsoli `Bohater: Zobacz, co mam w wyobraźni!` i klip `skarb_zapas.mp4`. Potem `Remove-Item Env:BAJKA_IMAGE_TIMEOUT_S`.

- [ ] **Step 12: Commit**

```powershell
git add bajka/app.py bajka/placeholders.py tests/test_app_live.py .env.example docs/PODZIAL_PRACY.md README.md
git commit -m "feat: rysowanie na żywo w aplikacji, zaślepki pętli rysowania i dokumentacja"
git pull --rebase origin main; python -m pytest; git push origin main
```

<!-- checkpoint -->

---

### Task 7 (P2): Sceny generowane z pamięcią opowieści i rysowaniem w tle

Robimy tylko wtedy, gdy P1 działa stabilnie na próbach.

**Files:**
- Modify: `bajka/scenario.py` (7 punktowych zmian), `bajka/engine.py` (6 punktowych zmian), `scenarios/rysowanie_na_zywo.yaml`
- Test: `tests/test_scenario_generated.py`, `tests/test_engine_generated.py`

**Interfaces:**
- Consumes: wszystko z Tasków 1–6.
- Produces:
  - **Scenariusz:**
    - `KINDS` z `"generated"`,
    - `Scene.clip: Path | None` (`None` tylko w `generated`),
    - `Scene.narration: str`.
  - **Scena `generated`:**
    - wymaga pól `image_prompt` (bez `{idea}`, tylko klucze `remember`), `narration`, `fallback_clips`, `next`,
    - silnik rysuje ją w tle, gdy zaczyna się scena z wyborami, która do niej prowadzi, albo zaraz po zapamiętaniu pomysłu w scenie `open`,
    - pokazuje ją jako pętlę z narracją postaci,
    - przy błędzie użyje klipu zapasowego bez kwestii awaryjnej.
  - **Niewybrane gałęzie** są porzucane.

- [ ] **Step 1: Napisz testy**

<!-- file: tests/test_scenario_generated.py -->
```python
from pathlib import Path

import pytest

from bajka.placeholders import planned_clips
from bajka.scenario import ScenarioError, load_scenario, missing_media, parse_scenario

GENERATED_SCENE = {
    "kind": "generated",
    "image_prompt": "Lila and Fiku celebrating in a meadow",
    "narration": "Zobacz, jak pięknie świętujemy!",
    "fallback_clips": ["final_zapas.mp4"],
    "next": "las",
}


@pytest.fixture
def generated_dict(scenario_dict):
    """intro → (las) → final_ul [scena generowana] → las."""
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "final_ul"
    scenario_dict["scenes"]["final_ul"] = dict(GENERATED_SCENE)
    return scenario_dict


def test_generated_scene_has_no_clip_and_goes_to_next(generated_dict):
    scenario = parse_scenario(generated_dict, base_dir=Path("film"))
    scene = scenario.scene("final_ul")

    assert scene.kind == "generated"
    assert scene.clip is None
    assert scene.narration == "Zobacz, jak pięknie świętujemy!"
    assert scene.fallback_clips == (Path("film/final_zapas.mp4"),)
    assert scene.successors == ("las",)
    assert not scene.is_ending
    assert scenario.needs_live_images


@pytest.mark.parametrize("field", ["image_prompt", "narration", "fallback_clips", "next"])
def test_generated_scene_requires_field(generated_dict, field):
    del generated_dict["scenes"]["final_ul"][field]

    with pytest.raises(ScenarioError, match=field):
        parse_scenario(generated_dict, base_dir=Path("."))


def test_generated_scene_cannot_use_idea_of_the_moment(generated_dict):
    generated_dict["scenes"]["final_ul"]["image_prompt"] = "a meadow with {idea}"

    with pytest.raises(ScenarioError, match="idea"):
        parse_scenario(generated_dict, base_dir=Path("."))


def test_generated_scene_may_use_remembered_idea(generated_dict):
    generated_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    generated_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "the beehive with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "final_ul",
    }
    generated_dict["scenes"]["final_ul"]["image_prompt"] = "a party at the beehive decorated with {ozdoby}"

    scenario = parse_scenario(generated_dict, base_dir=Path("."))

    assert scenario.scene("final_ul").image_prompt.endswith("{ozdoby}")


def test_missing_media_and_placeholders_cover_only_fallbacks_of_generated_scene(tmp_path, generated_dict):
    scenario = parse_scenario(generated_dict, base_dir=tmp_path)

    assert tmp_path / "final_zapas.mp4" in missing_media(scenario)
    assert (tmp_path / "final_zapas.mp4", "darkred", True) in planned_clips(scenario)


def test_live_drawing_example_returns_home_with_remembered_treasure():
    path = Path(__file__).resolve().parents[1] / "scenarios" / "rysowanie_na_zywo.yaml"

    scenario = load_scenario(path)

    assert scenario.scene("skarb").next == "powrot"
    assert "{skarb}" in scenario.scene("powrot").image_prompt
```

<!-- file: tests/test_engine_generated.py -->
```python
import threading
from pathlib import Path

import pytest
from live_fakes import FakeAnimator, FakeImaginer, FakeListener, FakePlayer, FakeResolver, FakeVoice

from bajka.engine import FALLBACK_VISION_LINE, StoryEngine
from bajka.ports import Interpretation, Vision
from bajka.scenario import parse_scenario

NARRATION = "Zobacz, jak pięknie wygląda nasz ul!"


class NamedIllustrator:
    """Nazwa obrazu wynika z pierwszego słowa promptu, więc kolejność rysowania w wątkach nie ma znaczenia."""

    def __init__(self, error=None):
        self.prompts = []
        self.started = threading.Event()
        self._lock = threading.Lock()
        self._error = error

    def draw(self, prompt):
        with self._lock:
            self.prompts.append(prompt)
        self.started.set()
        if self._error is not None:
            raise self._error
        return Path(f"{prompt.split()[0]}.png")


class WaitingListener(FakeListener):
    """Przed pierwszą odpowiedzią czeka, aż ruszy rysowanie w tle, i zapamiętuje, czy ruszyło."""

    def __init__(self, illustrator, *answers):
        super().__init__(*answers)
        self._illustrator = illustrator
        self.drawing_started_before_answer = None

    def listen(self):
        if self.drawing_started_before_answer is None:
            self.drawing_started_before_answer = self._illustrator.started.wait(timeout=2)
        return super().listen()


@pytest.fixture
def story(scenario_dict):
    """intro: las → ozdoby [open] → final_ul [generated] → las; jaskinia → gen_jaskinia [generated] → jaskinia."""
    scenes = scenario_dict["scenes"]
    scenes["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenes["intro"]["choices"]["jaskinia"]["next"] = "gen_jaskinia"
    scenes["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "beehive decorated with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "final_ul",
    }
    scenes["final_ul"] = {
        "kind": "generated",
        "image_prompt": "party at the beehive decorated with {ozdoby}",
        "narration": NARRATION,
        "fallback_clips": ["final_zapas.mp4"],
        "next": "las",
    }
    scenes["gen_jaskinia"] = {
        "kind": "generated",
        "image_prompt": "cave glowing with crystals",
        "narration": "Ale tu pięknie świeci!",
        "fallback_clips": ["jaskinia_zapas.mp4"],
        "next": "jaskinia",
    }
    return parse_scenario(scenario_dict, base_dir=Path("film"))


def make_engine(scenario, listener, illustrator, answer="las"):
    player, voice = FakePlayer(), FakeVoice()
    engine = StoryEngine(
        scenario,
        player,
        listener,
        voice,
        FakeResolver({answer: Interpretation(answer, f"{answer}!")}),
        imaginer=FakeImaginer({"wstążkami": Vision("Wstążki? Już rysuję!", "rainbow ribbons")}),
        illustrator=illustrator,
        animator=FakeAnimator(),
        image_timeout_s=2.0,
    )
    return engine, player, voice


def test_generated_scene_draws_remembered_idea_and_narrates_over_it(story):
    illustrator = NamedIllustrator()
    engine, player, voice = make_engine(story, FakeListener("las", "wstążkami"), illustrator)

    assert engine.run() == ["intro", "ozdoby", "final_ul", "las"]

    assert "party at the beehive decorated with rainbow ribbons" in illustrator.prompts
    assert player.calls[-2:] == [("loop", "party.mp4"), ("play", "las.mp4")]
    assert voice.lines[-1] == NARRATION


def test_choice_scene_draws_generated_branch_while_question_is_asked(story):
    illustrator = NamedIllustrator()
    listener = WaitingListener(illustrator, "jaskinia")
    engine, player, _ = make_engine(story, listener, illustrator, answer="jaskinia")

    assert engine.run() == ["intro", "gen_jaskinia", "jaskinia"]

    assert listener.drawing_started_before_answer
    assert illustrator.prompts.count("cave glowing with crystals") == 1  # nie rysujemy drugi raz
    assert ("loop", "cave.mp4") in player.calls


def test_generated_scene_failure_uses_fallback_clip_without_apology(story):
    engine, player, voice = make_engine(
        story, FakeListener("jaskinia"), NamedIllustrator(error=RuntimeError("429")), answer="jaskinia"
    )

    engine.run()

    assert ("loop", "jaskinia_zapas.mp4") in player.calls
    assert FALLBACK_VISION_LINE not in voice.lines
    assert voice.lines[-1] == "Ale tu pięknie świeci!"
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_scenario_generated.py tests/test_engine_generated.py -v`
Expected: FAIL — `ScenarioError: scena 'final_ul': nieznany rodzaj sceny 'generated'`

- [ ] **Step 3: Scenariusz — opis rodzaju `generated`; w `bajka/scenario.py` zamień:**

<!-- edit: bajka/scenario.py -->
```python
- `open`: gotowy klip z pytaniem otwartym; pomysł dziecka jest rysowany na żywo (bajka/imagine.py,
  bajka/illustrate.py, bajka/motion.py).
"""
```

na:

```python
- `open`: gotowy klip z pytaniem otwartym; pomysł dziecka jest rysowany na żywo (bajka/imagine.py,
  bajka/illustrate.py, bajka/motion.py),
- `generated`: scena bez gotowego klipu, rysowana na żywo z zapamiętanych pomysłów dziecka, z narracją postaci.
"""
```

oraz zamień:

<!-- edit: bajka/scenario.py -->
```python
KINDS = ("clip", "open")
LIVE_KINDS = ("open",)  # sceny, które potrzebują generowania obrazów na żywo
```

na:

```python
KINDS = ("clip", "open", "generated")
LIVE_KINDS = ("open", "generated")  # sceny, które potrzebują generowania obrazów na żywo
```

- [ ] **Step 4: Scenariusz — pola `clip` (opcjonalny) i `narration`; zamień:**

<!-- edit: bajka/scenario.py -->
```python
class Scene:
    id: str
    clip: Path
    idle: Path | None = None
```

na:

```python
class Scene:
    id: str
    clip: Path | None  # None tylko w scenach `generated`
    idle: Path | None = None
```

oraz zamień:

<!-- edit: bajka/scenario.py -->
```python
    next: str = ""  # następna scena dla scen bez wyborów (open)

    @property
```

na:

```python
    next: str = ""  # następna scena dla scen bez wyborów (open, generated)
    narration: str = ""  # kwestia postaci do sceny `generated`

    @property
```

- [ ] **Step 5: Scenariusz — `missing_media` bez klipu sceny generowanej; zamień:**

<!-- edit: bajka/scenario.py -->
```python
    for scene in scenario.scenes.values():
        paths.append(scene.clip)
        paths.extend(path for path in (scene.idle, scene.drawing) if path is not None)
```

na:

```python
    for scene in scenario.scenes.values():
        paths.extend(path for path in (scene.clip, scene.idle, scene.drawing) if path is not None)
```

- [ ] **Step 6: Scenariusz — parser sceny generowanej; zamień:**

<!-- edit: bajka/scenario.py -->
```python
    if kind == "open":
        return _parse_open(scene_id, data, base_dir, where)
    raw_choices
```

na:

```python
    if kind == "open":
        return _parse_open(scene_id, data, base_dir, where)
    if kind == "generated":
        return _parse_generated(scene_id, data, base_dir, where)
    raw_choices
```

oraz zamień:

<!-- edit: bajka/scenario.py -->
```python
        fallback_clips=_require_paths(data, "fallback_clips", base_dir, where),
        next=_require_str(data, "next", where),
    )


def _require_str(
```

na:

```python
        fallback_clips=_require_paths(data, "fallback_clips", base_dir, where),
        next=_require_str(data, "next", where),
    )


def _parse_generated(scene_id: str, data: dict, base_dir: Path, where: str) -> Scene:
    return Scene(
        id=scene_id,
        kind="generated",
        clip=None,
        image_prompt=_require_str(data, "image_prompt", where),
        narration=_require_str(data, "narration", where),
        fallback_clips=_require_paths(data, "fallback_clips", base_dir, where),
        next=_require_str(data, "next", where),
    )


def _require_str(
```

- [ ] **Step 7: Silnik — nagłówek, import i słownik rysowań w tle; w `bajka/engine.py` zamień:**

<!-- edit: bajka/engine.py -->
```python
Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo: Imaginer → Illustrator → Animator.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Mapping
```

na:

```python
Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo: Imaginer → Illustrator → Animator.
Sceny generowane (`kind: generated`) rysujemy w tle zawczasu: gdy pada pytanie, które może do nich prowadzić.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable, Mapping
```

oraz zamień:

<!-- edit: bajka/engine.py -->
```python
        self._memory: dict[str, str] = {}
        self._scenario = scenario
```

na:

```python
        self._memory: dict[str, str] = {}
        self._prefetched: dict[str, tuple[Future[Path], float]] = {}  # scena → (rysowanie, termin)
        self._scenario = scenario
```

- [ ] **Step 8: Silnik — pętla bajki ze scenami generowanymi; zamień:**

<!-- edit: bajka/engine.py -->
```python
            while True:
                visited.append(scene.id)
                log.info("Scena: %s", scene.id)
                self._player.play(scene.clip)
                if scene.is_ending:
                    return visited
                if scene.idle is not None:
                    self._player.loop(scene.idle)
                if scene.kind == "open":
                    self._ask_open(scene)
                    scene = self._scenario.scene(scene.next)
                    continue
                choice = self._vote(scene) if scene.vote and self._meter is not None else self._ask(scene)
                scene = self._scenario.scene(choice.next)
```

na:

```python
            while True:
                visited.append(scene.id)
                log.info("Scena: %s", scene.id)
                if scene.kind == "generated":
                    self._show_generated(scene)
                    scene = self._scenario.scene(scene.next)
                    continue
                self._prefetch(scene.successors if scene.choices else ())
                self._player.play(scene.clip)
                if scene.is_ending:
                    return visited
                if scene.idle is not None:
                    self._player.loop(scene.idle)
                if scene.kind == "open":
                    self._ask_open(scene)
                    scene = self._scenario.scene(scene.next)
                    continue
                choice = self._vote(scene) if scene.vote and self._meter is not None else self._ask(scene)
                self._drop_prefetched(other for other in scene.successors if other != choice.next)
                scene = self._scenario.scene(choice.next)
```

- [ ] **Step 9: Silnik — rysowanie w tle po zapamiętaniu pomysłu; zamień:**

<!-- edit: bajka/engine.py -->
```python
        if vision is None:
            self._memory[scene.remember] = scene.default_idea
            self._say(FALLBACK_VISION_LINE)
            self._player.play(self._fallback_clip(scene))
            return
        self._memory[scene.remember] = vision.idea
        if scene.drawing is not None:
```

na:

```python
        if vision is None:
            self._memory[scene.remember] = scene.default_idea
            self._prefetch((scene.next,))
            self._say(FALLBACK_VISION_LINE)
            self._player.play(self._fallback_clip(scene))
            return
        self._memory[scene.remember] = vision.idea
        self._prefetch((scene.next,))  # następna scena może już korzystać z tego pomysłu
        if scene.drawing is not None:
```

- [ ] **Step 10: Silnik — pokaz sceny generowanej, rysowanie w tle, porzucanie gałęzi; zamień:**

<!-- edit: bajka/engine.py -->
```python
    def _render(self, prompt: str) -> Path:
```

na:

```python
    def _show_generated(self, scene: Scene) -> None:
        self._prefetch((scene.id,))  # nic nie robi, jeśli scena już się rysuje
        future, deadline = self._prefetched.pop(scene.id)
        self._prefetch((scene.next,))
        clip = self._clip_or_fallback(scene, future, deadline, announce=False)
        self._player.loop(clip)
        self._say(scene.narration)  # postać mówi na tle zapętlonej ilustracji

    def _prefetch(self, scene_ids: Iterable[str]) -> None:
        for scene_id in scene_ids:
            target = self._scenario.scene(scene_id)
            if target.kind != "generated" or scene_id in self._prefetched:
                continue
            prompt = fill_prompt(target.image_prompt, self._memory)
            log.info("Rysuję w tle scenę %s", scene_id)
            self._prefetched[scene_id] = (
                self._pool.submit(self._render, prompt),
                time.monotonic() + self._image_timeout_s,
            )

    def _drop_prefetched(self, scene_ids: Iterable[str]) -> None:
        for scene_id in scene_ids:
            self._prefetched.pop(scene_id, None)  # niewybrana gałąź: wynik i tak przepada

    def _render(self, prompt: str) -> Path:
```

- [ ] **Step 11: Silnik — klip zapasowy bez kwestii awaryjnej w scenie generowanej; zamień:**

<!-- edit: bajka/engine.py -->
```python
    def _clip_or_fallback(self, scene: Scene, future: Future[Path], deadline: float) -> Path:
        try:
            return future.result(timeout=max(0.0, deadline - time.monotonic()))
        except TimeoutError:
            log.warning("Rysowanie trwa dłużej niż %.0f s, pokazuję klip zapasowy", self._image_timeout_s)
        except Exception:
            log.exception("Błąd rysowania, pokazuję klip zapasowy")
        self._say(FALLBACK_VISION_LINE)
        return self._fallback_clip(scene)
```

na:

```python
    def _clip_or_fallback(self, scene: Scene, future: Future[Path], deadline: float, announce: bool = True) -> Path:
        try:
            return future.result(timeout=max(0.0, deadline - time.monotonic()))
        except TimeoutError:
            log.warning("Rysowanie trwa dłużej niż %.0f s, pokazuję klip zapasowy", self._image_timeout_s)
        except Exception:
            log.exception("Błąd rysowania, pokazuję klip zapasowy")
        if announce:
            self._say(FALLBACK_VISION_LINE)
        return self._fallback_clip(scene)
```

- [ ] **Step 12: Przykład — scena powrotu ze skarbem; podmień `scenarios/rysowanie_na_zywo.yaml` na:**

<!-- file: scenarios/rysowanie_na_zywo.yaml -->
```yaml
# Przykład scen rysowanych na żywo — do prób mechaniki; prawdziwy scenariusz bajki dostarcza autor.
# Klipy-zaślepki:  python -m bajka.placeholders scenarios/rysowanie_na_zywo.yaml
# Próba:           python -m bajka scenarios/rysowanie_na_zywo.yaml --text --windowed
hero: >
  Lisek Feliks: odważny, ciekawski i trochę gapowaty lis, który przeżywa przygodę
  razem z dzieckiem siedzącym przed ekranem i zwraca się do niego jak do przyjaciela.
style: soft watercolor children's book illustration, warm pastel colors, gentle light, simple shapes
start: intro

scenes:
  intro:
    clip: clips/rysowanie/intro.mp4
    idle: clips/rysowanie/intro_idle.mp4
    question: Idziemy do mrocznego lasu czy do jaskini?
    reprompt: Hmm, nie usłyszałem. Idziemy do lasu czy do jaskini?
    default: jaskinia
    choices:
      las:
        description: pójść do mrocznego lasu
        next: las
        reply: Do lasu! Trzymaj się blisko mnie!
      jaskinia:
        description: wejść do jaskini
        next: skarb
        reply: Do jaskini! Dobrze, że mam latarkę!

  # Pytanie otwarte: pomysł dziecka jest rysowany na żywo.
  skarb:
    kind: open
    clip: clips/rysowanie/skarb.mp4               # Feliks znajduje coś błyszczącego i pyta, co to
    idle: clips/rysowanie/skarb_idle.mp4          # cicha pętla oczekiwania
    drawing: clips/rysowanie/rysuje.mp4           # cicha pętla „Feliks rysuje” na czas generowania
    question: Coś tu błyszczy! Jak wygląda skarb, który znaleźliśmy?
    reprompt: Złoto, kryształy, a może coś zupełnie innego? Jaki to skarb?
    image_prompt: "a little fox in a cozy cave lit by a lantern, discovering a treasure: {idea}"
    remember: skarb
    default_idea: a small chest full of glowing colorful crystals
    fallback_clips: [clips/rysowanie/skarb_zapas.mp4]
    next: powrot

  # Scena generowana: bez gotowego klipu, rysowana w tle z pomysłu zapamiętanego w scenie „skarb”.
  powrot:
    kind: generated
    image_prompt: "the little fox walking home through a meadow at sunset, proudly carrying {skarb}"
    narration: Wracam do domu z naszym skarbem. Dziękuję, że pomagasz mi w wyprawie!
    fallback_clips: [clips/rysowanie/powrot_zapas.mp4]
    next: jaskinia

  las:
    clip: clips/las.mp4

  jaskinia:
    clip: clips/jaskinia.mp4
```

- [ ] **Step 13: Uruchom wszystkie testy kilka razy (testy z wątkami)**

Run: `python -m pytest; python -m pytest; python -m pytest`
Expected:
- za każdym razem wszystkie przechodzą (w dniu pisania planu: `274 passed`),
- `tests/test_scenario_generated.py` — `9 passed`, `tests/test_engine_generated.py` — `3 passed`.

- [ ] **Step 14: Próba end-to-end**

1. **Zaślepki:**
   `python -m bajka.placeholders scenarios/rysowanie_na_zywo.yaml`
   Expected: tworzy `powrot_zapas.mp4`.
2. **Uruchomienie:**
   `python -m bajka scenarios/rysowanie_na_zywo.yaml --text --windowed --no-llm`
3. **Przebieg:** wpisz `jaskinia` i `tęczowy lizak`.
   Expected w logu, zaraz po `Pomysł: …`:
   - `Rysuję w tle scenę powrot`,
   - po klipie skarbu pętla z ilustracją lisa niosącego `a rainbow lollipop`,
   - w konsoli `Bohater: Wracam do domu z naszym skarbem…`.

- [ ] **Step 15: Commit**

```powershell
git add bajka/scenario.py bajka/engine.py scenarios/rysowanie_na_zywo.yaml tests/test_scenario_generated.py tests/test_engine_generated.py
git commit -m "feat: sceny generowane z pamięcią pomysłów dziecka i rysowaniem w tle"
git pull --rebase origin main; python -m pytest; git push origin main
```

<!-- checkpoint -->

---

## Poza tym planem

- **P3: napisy jako początek** (montaż ilustracji seansu z podpisem „Członek Klubu Ciekawskich”). Osobny plan po stabilnym P2.
- **`FluxIllustrator`**: tylko jeśli FLUX wygra pomiar dnia 1.
- **Lokalna wyobraźnia (Phi w Foundry Local)** jako zapas dla `imagine.py`: dopiero gdy Azure OpenAI okaże się zawodny na sali.

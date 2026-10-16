# Interaktywna Bajka Głosowa Zero-UI — plan implementacji szkieletu

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Szkielet aplikacji w Pythonie, który odtwarza klip bajki, po nim słucha dziecka przez mikrofon, wysyła mowę do Azure Speech-to-Text, analizuje intencję przez Azure OpenAI, wypowiada reakcję bohatera przez Azure TTS i odtwarza wybrany kolejny klip.

**Architecture:** Bajka to graf scen w YAML. `StoryEngine` prowadzi pętlę *klip → pętla oczekiwania + nasłuch → intencja → głos bohatera → kolejny klip* i zależy wyłącznie od czterech interfejsów (`Player`, `Listener`, `Voice`, `IntentResolver`), więc da się go w pełni przetestować na atrapach. Implementacje adapterów: VLC osadzony w oknie tkinter (wątek główny), Azure AI Speech (STT/TTS), Azure OpenAI (structured outputs). Silnik działa w wątku roboczym.

**Tech Stack:** Python 3.11+ (testowane na 3.13), python-vlc 3.0.21203 + VLC 3.x 64-bit, azure-cognitiveservices-speech 1.52, openai 3.31 (`AzureOpenAI`), PyYAML, python-dotenv, sounddevice + numpy, pytest.

> **Stan 2026-10-16: plan wykonany, potem zrefaktorowany pod pracę w dwie osoby.** Aktualną strukturę opisuje [podział pracy](../../PODZIAL_PRACY.md). Różnice względem kodu w zadaniach poniżej:
> - **Task 2:** zamiast wspólnej klasy `Settings` i `load_settings` każdy moduł ma własne ustawienia: `SttSettings` (`bajka/stt.py`), `TtsSettings` (`bajka/tts.py`), `LlmSettings` (`bajka/intent.py`); `BAJKA_MAX_REPROMPTS` czyta `app.py`. `bajka/config.py` zawiera tylko `ConfigError`, `load_env()`, `require(env, *names)`, `get_int(env, name, default)`.
> - **Task 5:** `bajka/speech.py` rozdzielono na `bajka/stt.py` (`AzureListener.from_settings(SttSettings)`, `RecognitionError`) i `bajka/tts.py` (`AzureVoice.from_settings(TtsSettings)`, `SynthesisError`).
> - **Nowe dema:** `python -m bajka.stt`, `python -m bajka.tts`, `python -m bajka.intent`. Kontrakty w `bajka/ports.py` są `@runtime_checkable`.

## Kontekst i ustalenia

Ustalenia z sesji projektowej (nie ma osobnego specu — to jest źródło prawdy):

- **Grupa docelowa:** dzieci; interakcja wyłącznie głosem (Zero-UI). Klawiatura tylko dla operatora (`Esc`) i w trybie próbnym `--text`.
- **Odtwarzacz:** python-vlc w jednym pełnoekranowym oknie tkinter, które nie znika między klipami. Pętla oczekiwania przez opcję mediów `input-repeat`.
- **STT:** Azure AI Speech SDK słucha bezpośrednio domyślnego mikrofonu (`recognize_once`), sam wykrywa początek i koniec wypowiedzi (timeouty ciszy z `.env`).
- **LLM:** Azure OpenAI, wdrożenie GPT-4o-mini, prompt systemowy „jesteś bohaterem bajki”, odpowiedź jako JSON wymuszony przez structured outputs: `{"choice": <id wyboru albo "nie_wiem">, "reply": <kwestia bohatera>}`.
- **TTS:** Azure TTS (ten sam klucz co STT), głos `pl-PL-MarekNeural`, SSML z wolniejszym tempem. Synteza do pamięci i odtwarzanie przez sounddevice, żeby `say()` blokowało do końca wypowiedzi.
- **Kolejność:** bohater mówi reakcję (TTS) na pętli oczekiwania, **potem** startuje kolejny klip.
- **Brak intencji:** cisza → kwestia `reprompt` ze scenariusza; niejasna odpowiedź → dopytanie wygenerowane przez LLM. Maksymalnie 2 dopytania, potem „Dobrze, to ja wybiorę!” + reakcja wyboru `default`.
- **Awarie:** błąd STT = cisza; błąd LLM albo nieznany wybór = gałąź `default` ze statyczną kwestią `reply`; błąd TTS = log i bajka leci dalej. Bajka nigdy nie staje.
- **Półdupleks:** mikrofon nie słucha, gdy mówi bohater (sekwencyjny przebieg w silniku).

## Global Constraints

- Python `>=3.11`, 64-bit; VLC 3.x **64-bit** (musi zgadzać się z bitowością Pythona).
- Platforma docelowa: Windows 11 (komendy w planie są dla PowerShella); Linux wspierany, macOS bez osadzania okna.
- Zależności runtime dokładnie: `python-vlc>=3.0.21203`, `azure-cognitiveservices-speech>=1.52`, `openai>=1.55`, `PyYAML>=6.0`, `python-dotenv>=1.0`, `sounddevice>=0.5`, `numpy>=2.0`; dev: `pytest>=8`. Żadnych innych.
- Język: identyfikatory w kodzie po angielsku; komunikaty, logi, prompty, kwestie i README po polsku. Język rozpoznawania `pl-PL`.
- Testy nie łączą się z siecią, nie używają mikrofonu i **nie importują `bajka.player`** (`import vlc` rzuca wyjątek bez zainstalowanego VLC).
- Sekrety tylko w `.env` (w `.gitignore`); w repo jest wyłącznie `.env.example`.
- Wartości domyślne: `AZURE_OPENAI_API_VERSION=2024-10-21`, głos `pl-PL-MarekNeural`, tempo `-10%`, cisza początkowa 6000 ms, cisza końcowa 1200 ms, `max_reprompts=2`.
- Git: wszystkie commity bezpośrednio na `main`, bez gałęzi funkcyjnych; po każdym zadaniu `git push origin main`.

## Struktura plików

| Plik | Odpowiedzialność | Zadanie |
|---|---|---|
| `pyproject.toml` | Pakiet `bajka`, zależności, konfiguracja pytest | 1 |
| `.gitignore` | `.venv`, cache, `.env`, `scenarios/clips/` | 1 |
| `bajka/__init__.py` | Pakiet | 1 |
| `bajka/scenario.py` | `Choice`, `Scene`, `Scenario`, `load_scenario`, `parse_scenario`, `missing_media`, `ScenarioError` | 1 |
| `scenarios/las_czy_jaskinia.yaml` | Przykładowa bajka | 1 |
| `tests/conftest.py` | Fikstury `scenario_dict`, `scenario` | 1 |
| `bajka/config.py` | `Settings`, `load_settings`, `ConfigError` | 2 |
| `.env.example` | Szablon ustawień | 2 |
| `bajka/ports.py` | `Interpretation` + protokoły `Player`, `Listener`, `Voice`, `IntentResolver` | 3 |
| `bajka/engine.py` | `StoryEngine`, `DEFAULT_FALLBACK` | 3 |
| `bajka/intent.py` | `AzureIntentResolver`, prompt, schemat JSON, parsowanie | 4 |
| `bajka/speech.py` | `AzureListener`, `AzureVoice`, `make_speech_config`, `SpeechError` | 5 |
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg) | 6 |
| `bajka/player.py` | `VlcPlayer` + podgląd `python -m bajka.player` | 6 |
| `bajka/console.py` | `ConsoleListener`, `ConsoleVoice` (tryb `--text`) | 7 |
| `bajka/app.py`, `bajka/__main__.py` | CLI, złożenie zależności, okno + wątek silnika | 7 |
| `README.md` | Instrukcja dla zespołu | 7 |

---

### Task 1: Szkielet projektu i model scenariusza

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `bajka/__init__.py`
- Create: `bajka/scenario.py`
- Create: `scenarios/las_czy_jaskinia.yaml`
- Test: `tests/conftest.py`, `tests/test_scenario.py`

**Interfaces:**
- Consumes: nic.
- Produces:
  - `Choice(id: str, description: str, next: str, reply: str)` (frozen dataclass)
  - `Scene(id: str, clip: Path, idle: Path | None, question: str, reprompt: str, fallback: str, default: str | None, choices: dict[str, Choice])` + właściwość `is_ending -> bool`
  - `Scenario(hero: str, start: str, scenes: dict[str, Scene])` + `scene(scene_id: str) -> Scene`
  - `load_scenario(path: str | Path) -> Scenario` (ścieżki względne wobec katalogu pliku YAML)
  - `parse_scenario(raw: object, base_dir: Path) -> Scenario`
  - `missing_media(scenario: Scenario) -> list[Path]`
  - `ScenarioError(ValueError)`
  - Fikstury pytest: `scenario_dict` (głęboka kopia słownika) i `scenario` (sparsowany, `base_dir=Path("film")`): scena `intro` z wyborami `las`/`jaskinia`, `default: las`, sceny końcowe `las` i `jaskinia`.

- [ ] **Step 1: Przygotuj repozytorium, VLC i środowisko**

```powershell
git switch main
git pull
winget install --id VideoLAN.VLC -e
```

VLC musi być 64-bit (domyślny instalator winget jest 64-bit). Utwórz pliki projektu:

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "bajka"
version = "0.1.0"
description = "Interaktywna Bajka Głosowa Zero-UI — prototyp hackathonowy"
requires-python = ">=3.11"
dependencies = [
    "python-vlc>=3.0.21203",
    "azure-cognitiveservices-speech>=1.52",
    "openai>=1.55",
    "PyYAML>=6.0",
    "python-dotenv>=1.0",
    "sounddevice>=0.5",
    "numpy>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.setuptools]
packages = ["bajka"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
.env
scenarios/clips/
```

`bajka/__init__.py`:

```python
"""Interaktywna Bajka Głosowa Zero-UI."""
```

Zainstaluj pakiet w trybie edytowalnym:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Expected: `Successfully installed ... bajka-0.1.0 ...`

- [ ] **Step 2: Napisz fikstury i testy scenariusza**

`tests/conftest.py`:

```python
import copy
from pathlib import Path

import pytest

from bajka.scenario import parse_scenario

SCENARIO = {
    "hero": "Lisek Feliks, odważny i ciekawski lis.",
    "start": "intro",
    "scenes": {
        "intro": {
            "clip": "intro.mp4",
            "idle": "intro_idle.mp4",
            "question": "Idziemy do mrocznego lasu czy do jaskini?",
            "reprompt": "Hmm, nie usłyszałem. Las czy jaskinia?",
            "default": "las",
            "choices": {
                "las": {
                    "description": "pójść do mrocznego lasu",
                    "next": "las",
                    "reply": "Do lasu! Trzymaj się blisko!",
                },
                "jaskinia": {
                    "description": "wejść do jaskini",
                    "next": "jaskinia",
                    "reply": "Do jaskini! Mam latarkę!",
                },
            },
        },
        "las": {"clip": "las.mp4"},
        "jaskinia": {"clip": "jaskinia.mp4"},
    },
}


@pytest.fixture
def scenario_dict():
    return copy.deepcopy(SCENARIO)


@pytest.fixture
def scenario(scenario_dict):
    return parse_scenario(scenario_dict, base_dir=Path("film"))
```

`tests/test_scenario.py`:

```python
from pathlib import Path

import pytest

from bajka.scenario import ScenarioError, load_scenario, missing_media, parse_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_parses_scenes_choices_and_resolves_paths(scenario_dict):
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))

    intro = scenario.scene("intro")
    assert scenario.start == "intro"
    assert intro.clip == Path("film/intro.mp4")
    assert intro.idle == Path("film/intro_idle.mp4")
    assert intro.default == "las"
    assert intro.choices["jaskinia"].next == "jaskinia"
    assert not intro.is_ending
    assert scenario.scene("las").is_ending


def test_missing_start_scene_is_rejected(scenario_dict):
    scenario_dict["start"] = "prolog"
    with pytest.raises(ScenarioError, match="prolog"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_choice_pointing_to_unknown_scene_is_rejected(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "bagno"
    with pytest.raises(ScenarioError, match="bagno"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_default_must_be_one_of_choices(scenario_dict):
    scenario_dict["scenes"]["intro"]["default"] = "rzeka"
    with pytest.raises(ScenarioError, match="default"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_scene_with_choices_requires_idle_loop(scenario_dict):
    del scenario_dict["scenes"]["intro"]["idle"]
    with pytest.raises(ScenarioError, match="idle"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_choice_requires_reply(scenario_dict):
    del scenario_dict["scenes"]["intro"]["choices"]["las"]["reply"]
    with pytest.raises(ScenarioError, match="reply"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_missing_media_lists_files_that_do_not_exist(tmp_path, scenario_dict):
    (tmp_path / "intro.mp4").touch()
    (tmp_path / "las.mp4").touch()
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)

    assert missing_media(scenario) == [tmp_path / "intro_idle.mp4", tmp_path / "jaskinia.mp4"]


def test_invalid_yaml_raises_scenario_error(tmp_path):
    bad = tmp_path / "zly.yaml"
    bad.write_text("scenes: [niezamknięta", encoding="utf-8")
    with pytest.raises(ScenarioError, match="YAML"):
        load_scenario(bad)


def test_bundled_example_scenario_is_valid():
    scenario = load_scenario(ROOT / "scenarios" / "las_czy_jaskinia.yaml")

    assert scenario.start == "intro"
    assert set(scenario.scene("intro").choices) == {"las", "jaskinia"}
    assert scenario.scene("intro").clip == ROOT / "scenarios" / "clips" / "intro.mp4"
```

Przykładowa bajka (używa jej ostatni test) — `scenarios/las_czy_jaskinia.yaml`:

```yaml
# Przykładowa bajka. Ścieżki klipów są względne wobec tego pliku.
# Klipy-zaślepki do prób: python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml
hero: >
  Lisek Feliks: odważny, ciekawski i trochę gapowaty lis, który przeżywa przygodę
  razem z dzieckiem siedzącym przed ekranem i zwraca się do niego jak do przyjaciela.
start: intro

scenes:
  intro:
    clip: clips/intro.mp4          # Feliks odwraca się do kamery i zadaje pytanie
    idle: clips/intro_idle.mp4     # pętla oczekiwania, BEZ dźwięku (mikrofon słucha)
    question: Idziemy do mrocznego lasu czy do jaskini?
    reprompt: Hmm, nie usłyszałem. Idziemy do lasu czy do jaskini?
    fallback: Dobrze, to ja wybiorę!
    default: las
    choices:
      las:
        description: pójść do mrocznego lasu
        next: las
        reply: Do lasu! Trzymaj się blisko mnie!
      jaskinia:
        description: wejść do jaskini
        next: jaskinia
        reply: Do jaskini! Dobrze, że mam latarkę!

  las:
    clip: clips/las.mp4

  jaskinia:
    clip: clips/jaskinia.mp4
```

- [ ] **Step 3: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_scenario.py -v`
Expected: błąd ładowania `conftest.py`: `ModuleNotFoundError: No module named 'bajka.scenario'`

- [ ] **Step 4: Zaimplementuj model scenariusza**

`bajka/scenario.py`:

```python
"""Scenariusz bajki: graf scen wczytywany z pliku YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ScenarioError(ValueError):
    """Scenariusz jest niepoprawny."""


@dataclass(frozen=True)
class Choice:
    id: str
    description: str  # znaczenie wyboru dla LLM, np. "pójść do mrocznego lasu"
    next: str  # identyfikator kolejnej sceny
    reply: str  # statyczna kwestia bohatera, gdy LLM nie odpowie


@dataclass(frozen=True)
class Scene:
    id: str
    clip: Path
    idle: Path | None = None
    question: str = ""
    reprompt: str = ""
    fallback: str = ""
    default: str | None = None
    choices: dict[str, Choice] = field(default_factory=dict)

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


def load_scenario(path: str | Path) -> Scenario:
    """Wczytuje scenariusz; ścieżki klipów są względne wobec katalogu pliku YAML."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"{path}: niepoprawny YAML: {exc}") from exc
    return parse_scenario(raw, base_dir=path.parent)


def parse_scenario(raw: object, base_dir: Path) -> Scenario:
    if not isinstance(raw, dict):
        raise ScenarioError("scenariusz: oczekiwano słownika YAML")
    raw_scenes = raw.get("scenes")
    if not isinstance(raw_scenes, dict) or not raw_scenes:
        raise ScenarioError("scenariusz: brak sekcji 'scenes'")
    scenario = Scenario(
        hero=_require_str(raw, "hero", "scenariusz"),
        start=_require_str(raw, "start", "scenariusz"),
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
    return [path for path in paths if not path.is_file()]


def _parse_scene(scene_id: str, data: object, base_dir: Path) -> Scene:
    where = f"scena '{scene_id}'"
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: oczekiwano słownika")
    raw_choices = data.get("choices") or {}
    if not isinstance(raw_choices, dict):
        raise ScenarioError(f"{where}: 'choices' musi być słownikiem")
    choices = {
        cid: Choice(
            id=cid,
            description=_require_str(c, "description", f"{where}, wybór '{cid}'"),
            next=_require_str(c, "next", f"{where}, wybór '{cid}'"),
            reply=_require_str(c, "reply", f"{where}, wybór '{cid}'"),
        )
        for cid, c in raw_choices.items()
    }
    clip = base_dir / _require_str(data, "clip", where)
    if not choices:
        return Scene(id=scene_id, clip=clip)
    return Scene(
        id=scene_id,
        clip=clip,
        idle=base_dir / _require_str(data, "idle", where),
        question=_require_str(data, "question", where),
        reprompt=_require_str(data, "reprompt", where),
        fallback=str(data.get("fallback") or "").strip(),
        default=_require_str(data, "default", where),
        choices=choices,
    )


def _require_str(data: object, key: str, where: str) -> str:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where}: brak pola '{key}' (niepusty tekst)")
    return value.strip()


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

- [ ] **Step 5: Uruchom testy**

Run: `python -m pytest tests/test_scenario.py -v`
Expected: `9 passed`

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml .gitignore bajka/__init__.py bajka/scenario.py scenarios/las_czy_jaskinia.yaml tests/conftest.py tests/test_scenario.py
git commit -m "feat: model scenariusza bajki z walidacją grafu scen"
```

---

### Task 2: Konfiguracja z `.env`

**Files:**
- Create: `bajka/config.py`, `.env.example`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nic.
- Produces:
  - `Settings` (frozen dataclass) z polami: `openai_endpoint`, `openai_api_key`, `openai_deployment`, `openai_api_version="2024-10-21"`, `speech_key=""`, `speech_region=""`, `language="pl-PL"`, `voice="pl-PL-MarekNeural"`, `voice_rate="-10%"`, `initial_silence_ms=6000`, `end_silence_ms=1200`, `max_reprompts=2`
  - `load_settings(env: Mapping[str, str] | None = None, *, require_speech: bool = True) -> Settings` — bez `env` ładuje `.env` z bieżącego katalogu (`find_dotenv(usecwd=True)`) i czyta `os.environ`
  - `ConfigError(RuntimeError)`, stałe `OPENAI_VARS`, `SPEECH_VARS` (krotki nazw zmiennych)

- [ ] **Step 1: Napisz testy konfiguracji**

`tests/test_config.py`:

```python
import pytest

from bajka.config import ConfigError, load_settings

FULL_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
    "AZURE_SPEECH_KEY": "klucz-mowy",
    "AZURE_SPEECH_REGION": "westeurope",
}


def test_reads_required_values_and_applies_defaults():
    settings = load_settings(FULL_ENV)

    assert settings.openai_deployment == "gpt-4o-mini"
    assert settings.speech_region == "westeurope"
    assert settings.openai_api_version == "2024-10-21"
    assert settings.language == "pl-PL"
    assert settings.voice == "pl-PL-MarekNeural"
    assert settings.max_reprompts == 2


def test_missing_variables_are_listed_in_error():
    env = {k: v for k, v in FULL_ENV.items() if k not in ("AZURE_SPEECH_KEY", "AZURE_OPENAI_API_KEY")}

    with pytest.raises(ConfigError) as exc:
        load_settings(env)

    assert "AZURE_SPEECH_KEY" in str(exc.value)
    assert "AZURE_OPENAI_API_KEY" in str(exc.value)


def test_text_mode_does_not_need_speech_keys():
    env = {k: v for k, v in FULL_ENV.items() if not k.startswith("AZURE_SPEECH")}

    settings = load_settings(env, require_speech=False)

    assert settings.speech_key == ""


def test_numeric_overrides_are_parsed():
    settings = load_settings({**FULL_ENV, "BAJKA_MAX_REPROMPTS": "1", "BAJKA_END_SILENCE_MS": "800"})

    assert settings.max_reprompts == 1
    assert settings.end_silence_ms == 800


def test_non_numeric_override_is_rejected():
    with pytest.raises(ConfigError, match="BAJKA_MAX_REPROMPTS"):
        load_settings({**FULL_ENV, "BAJKA_MAX_REPROMPTS": "dwa"})
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bajka.config'`

- [ ] **Step 3: Zaimplementuj konfigurację i szablon `.env`**

`bajka/config.py`:

```python
"""Ustawienia aplikacji z pliku .env i zmiennych środowiskowych."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

OPENAI_VARS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
SPEECH_VARS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")


class ConfigError(RuntimeError):
    """Brakuje ustawień albo mają zły format."""


@dataclass(frozen=True)
class Settings:
    openai_endpoint: str
    openai_api_key: str
    openai_deployment: str
    openai_api_version: str = "2024-10-21"
    speech_key: str = ""
    speech_region: str = ""
    language: str = "pl-PL"
    voice: str = "pl-PL-MarekNeural"
    voice_rate: str = "-10%"
    initial_silence_ms: int = 6000
    end_silence_ms: int = 1200
    max_reprompts: int = 2


def load_settings(env: Mapping[str, str] | None = None, *, require_speech: bool = True) -> Settings:
    """Czyta ustawienia. Bez `env` najpierw ładuje plik .env z bieżącego katalogu."""
    if env is None:
        load_dotenv(find_dotenv(usecwd=True))
        env = os.environ
    required = OPENAI_VARS + (SPEECH_VARS if require_speech else ())
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise ConfigError("Brak ustawień w .env: " + ", ".join(missing))
    defaults = Settings(openai_endpoint="", openai_api_key="", openai_deployment="")
    return Settings(
        openai_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        openai_api_key=env["AZURE_OPENAI_API_KEY"],
        openai_deployment=env["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=env.get("AZURE_OPENAI_API_VERSION") or defaults.openai_api_version,
        speech_key=env.get("AZURE_SPEECH_KEY", ""),
        speech_region=env.get("AZURE_SPEECH_REGION", ""),
        language=env.get("BAJKA_LANGUAGE") or defaults.language,
        voice=env.get("BAJKA_VOICE") or defaults.voice,
        voice_rate=env.get("BAJKA_VOICE_RATE") or defaults.voice_rate,
        initial_silence_ms=_int(env, "BAJKA_INITIAL_SILENCE_MS", defaults.initial_silence_ms),
        end_silence_ms=_int(env, "BAJKA_END_SILENCE_MS", defaults.end_silence_ms),
        max_reprompts=_int(env, "BAJKA_MAX_REPROMPTS", defaults.max_reprompts),
    )


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} musi być liczbą całkowitą, jest: {value!r}") from exc
```

`.env.example`:

```ini
# Skopiuj do .env i uzupełnij. Plik .env jest w .gitignore — nie commituj kluczy.

# Azure AI Speech (STT + TTS): portal.azure.com → zasób Speech → "Klucze i punkt końcowy"
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=westeurope

# Azure OpenAI: zasób Azure OpenAI → "Klucze i punkt końcowy"; DEPLOYMENT to nazwa wdrożenia modelu
AZURE_OPENAI_ENDPOINT=https://twoj-zasob.openai.azure.com/
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21

# Strojenie (opcjonalne, to są wartości domyślne)
BAJKA_LANGUAGE=pl-PL
BAJKA_VOICE=pl-PL-MarekNeural
BAJKA_VOICE_RATE=-10%
BAJKA_INITIAL_SILENCE_MS=6000
BAJKA_END_SILENCE_MS=1200
BAJKA_MAX_REPROMPTS=2
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_config.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```powershell
git add bajka/config.py .env.example tests/test_config.py
git commit -m "feat: ustawienia Azure i strojenia z pliku .env"
```

---

### Task 3: Interfejsy i silnik bajki

**Files:**
- Create: `bajka/ports.py`, `bajka/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Scenario`, `Scene`, `Choice`, `parse_scenario` (Task 1); fikstury `scenario`, `scenario_dict`.
- Produces:
  - `Interpretation(choice_id: str | None, reply: str)` — `None` = intencja nierozpoznana
  - `Player.play(clip: Path) -> None` (blokuje do końca), `Player.loop(clip: Path) -> None` (wraca od razu)
  - `Listener.listen() -> str | None` (`None` = cisza)
  - `Voice.say(text: str) -> None` (blokuje do końca wypowiedzi)
  - `IntentResolver.resolve(scene: Scene, transcript: str) -> Interpretation`
  - `StoryEngine(scenario, player, listener, voice, resolver, max_reprompts: int = 2)` + `run() -> list[str]` (identyfikatory odwiedzonych scen)
  - `DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"`

Kontrakt błędów: wyjątek z `listen()` = cisza; wyjątek z `resolve()` albo `choice_id` spoza sceny = wybór `default` ze statyczną kwestią `reply`; wyjątek z `say()` jest logowany i ignorowany. Wyjątki z `Player` przerywają bajkę (bez obrazu nie ma pokazu).

- [ ] **Step 1: Napisz testy silnika na atrapach**

`tests/test_engine.py`:

```python
from pathlib import Path

from bajka.engine import DEFAULT_FALLBACK, StoryEngine
from bajka.ports import Interpretation
from bajka.scenario import parse_scenario

REPROMPT = "Hmm, nie usłyszałem. Las czy jaskinia?"
LAS_REPLY = "Do lasu! Trzymaj się blisko!"


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
    def __init__(self, broken=False):
        self.lines = []
        self._broken = broken

    def say(self, text):
        self.lines.append(text)
        if self._broken:
            raise RuntimeError("głośnik nie działa")


class FakeResolver:
    """Mapuje transkrypcję na Interpretation albo wyjątek."""

    def __init__(self, answers):
        self._answers = answers
        self.calls = []

    def resolve(self, scene, transcript):
        self.calls.append((scene.id, transcript))
        answer = self._answers[transcript]
        if isinstance(answer, Exception):
            raise answer
        return answer


def make_engine(scenario, listener, resolver=None, voice=None, max_reprompts=2):
    player = FakePlayer()
    voice = voice or FakeVoice()
    resolver = resolver or FakeResolver({})
    engine = StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=max_reprompts)
    return engine, player, voice


def test_recognized_answer_speaks_reply_and_plays_next_clip(scenario):
    resolver = FakeResolver({"do lasu": Interpretation("las", "Super, idziemy do lasu!")})
    engine, player, voice = make_engine(scenario, FakeListener("do lasu"), resolver)

    assert engine.run() == ["intro", "las"]
    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4"), ("play", "las.mp4")]
    assert voice.lines == ["Super, idziemy do lasu!"]
    assert resolver.calls == [("intro", "do lasu")]


def test_silence_triggers_reprompt_then_accepts_answer(scenario):
    resolver = FakeResolver({"jaskinia": Interpretation("jaskinia", "Do jaskini!")})
    engine, _, voice = make_engine(scenario, FakeListener(None, "jaskinia"), resolver)

    assert engine.run() == ["intro", "jaskinia"]
    assert voice.lines == [REPROMPT, "Do jaskini!"]


def test_unclear_answer_uses_reprompt_generated_by_llm(scenario):
    resolver = FakeResolver({
        "nie wiem": Interpretation(None, "To jak, las czy jaskinia?"),
        "las": Interpretation("las", "Las!"),
    })
    engine, _, voice = make_engine(scenario, FakeListener("nie wiem", "las"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == ["To jak, las czy jaskinia?", "Las!"]


def test_after_max_reprompts_hero_picks_default(scenario):
    engine, _, voice = make_engine(scenario, FakeListener(None, None, None))

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [REPROMPT, REPROMPT, f"{DEFAULT_FALLBACK} {LAS_REPLY}"]


def test_scene_fallback_line_overrides_default_one(scenario_dict):
    scenario_dict["scenes"]["intro"]["fallback"] = "No dobrze, ja decyduję!"
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    engine, _, voice = make_engine(scenario, FakeListener(None), max_reprompts=0)

    engine.run()

    assert voice.lines == [f"No dobrze, ja decyduję! {LAS_REPLY}"]


def test_listener_error_counts_as_silence(scenario):
    resolver = FakeResolver({"las": Interpretation("las", "Las!")})
    engine, _, voice = make_engine(scenario, FakeListener(RuntimeError("brak mikrofonu"), "las"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [REPROMPT, "Las!"]


def test_llm_error_goes_to_default_with_static_reply(scenario):
    resolver = FakeResolver({"jaskinia": TimeoutError("Azure OpenAI nie odpowiada")})
    engine, _, voice = make_engine(scenario, FakeListener("jaskinia"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [LAS_REPLY]


def test_unknown_choice_from_llm_goes_to_default(scenario):
    resolver = FakeResolver({"rzeka": Interpretation("rzeka", "Do rzeki!")})
    engine, _, voice = make_engine(scenario, FakeListener("rzeka"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [LAS_REPLY]


def test_empty_llm_reply_falls_back_to_static_reply(scenario):
    resolver = FakeResolver({"jaskinia": Interpretation("jaskinia", "")})
    engine, _, voice = make_engine(scenario, FakeListener("jaskinia"), resolver)

    engine.run()

    assert voice.lines == ["Do jaskini! Mam latarkę!"]


def test_tts_failure_does_not_stop_the_story(scenario):
    resolver = FakeResolver({"las": Interpretation("las", "Las!")})
    engine, player, _ = make_engine(scenario, FakeListener("las"), resolver, voice=FakeVoice(broken=True))

    assert engine.run() == ["intro", "las"]
    assert player.calls[-1] == ("play", "las.mp4")


def test_story_chains_multiple_decisions(scenario_dict):
    scenario_dict["scenes"]["las"] = {
        "clip": "las.mp4",
        "idle": "las_idle.mp4",
        "question": "Przechodzimy przez most czy po kamieniach?",
        "reprompt": "Most czy kamienie?",
        "default": "most",
        "choices": {
            "most": {"description": "przejść przez most", "next": "jaskinia", "reply": "Most!"},
            "kamienie": {"description": "skakać po kamieniach", "next": "jaskinia", "reply": "Hop!"},
        },
    }
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    resolver = FakeResolver({
        "las": Interpretation("las", "Las!"),
        "kamienie": Interpretation("kamienie", "Hop, hop!"),
    })
    engine, player, voice = make_engine(scenario, FakeListener("las", "kamienie"), resolver)

    assert engine.run() == ["intro", "las", "jaskinia"]
    assert ("loop", "las_idle.mp4") in player.calls
    assert voice.lines == ["Las!", "Hop, hop!"]
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bajka.engine'`

- [ ] **Step 3: Zaimplementuj interfejsy**

`bajka/ports.py`:

```python
"""Interfejsy, od których zależy silnik bajki. Implementacje: Azure, VLC, konsola, atrapy w testach."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bajka.scenario import Scene


@dataclass(frozen=True)
class Interpretation:
    choice_id: str | None  # None = intencja nierozpoznana, bohater dopytuje
    reply: str  # kwestia bohatera do wypowiedzenia przez TTS


class Player(Protocol):
    def play(self, clip: Path) -> None:
        """Odtwarza klip i blokuje do jego końca."""

    def loop(self, clip: Path) -> None:
        """Zapętla klip w tle i wraca od razu."""


class Listener(Protocol):
    def listen(self) -> str | None:
        """Słucha jednej wypowiedzi dziecka. None oznacza ciszę."""


class Voice(Protocol):
    def say(self, text: str) -> None:
        """Wypowiada kwestię bohatera i blokuje do końca wypowiedzi."""


class IntentResolver(Protocol):
    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        """Zamienia wypowiedź dziecka na wybór ze sceny i kwestię bohatera."""
```

- [ ] **Step 4: Zaimplementuj silnik**

`bajka/engine.py`:

```python
"""Silnik bajki: odtwarza sceny, słucha dziecka i wybiera kolejny klip."""

from __future__ import annotations

import logging

from bajka.ports import IntentResolver, Interpretation, Listener, Player, Voice
from bajka.scenario import Choice, Scenario, Scene

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"


class StoryEngine:
    """Prowadzi bajkę od sceny startowej do zakończenia.

    Błędy mikrofonu, LLM i TTS są tu logowane i obsłużone, żeby bajka nigdy nie stanęła.
    """

    def __init__(
        self,
        scenario: Scenario,
        player: Player,
        listener: Listener,
        voice: Voice,
        resolver: IntentResolver,
        max_reprompts: int = 2,
    ) -> None:
        self._scenario = scenario
        self._player = player
        self._listener = listener
        self._voice = voice
        self._resolver = resolver
        self._max_reprompts = max_reprompts

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
            choice = self._ask(scene)
            scene = self._scenario.scene(choice.next)

    def _ask(self, scene: Scene) -> Choice:
        for attempt in range(self._max_reprompts + 1):
            transcript = self._listen()
            if transcript:
                interpretation = self._interpret(scene, transcript)
                if interpretation.choice_id is not None:
                    choice = scene.choices[interpretation.choice_id]
                    self._say(interpretation.reply or choice.reply)
                    return choice
                retry_line = interpretation.reply or scene.reprompt
            else:
                retry_line = scene.reprompt
            if attempt < self._max_reprompts:
                self._say(retry_line)
        default = scene.choices[scene.default]
        log.info("Brak decyzji, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _listen(self) -> str | None:
        try:
            transcript = self._listener.listen()
        except Exception:
            log.exception("Błąd rozpoznawania mowy, traktuję jak ciszę")
            return None
        log.info("Dziecko: %r", transcript)
        return transcript or None

    def _interpret(self, scene: Scene, transcript: str) -> Interpretation:
        default = scene.choices[scene.default]
        try:
            interpretation = self._resolver.resolve(scene, transcript)
        except Exception:
            log.exception("Błąd LLM, wybieram domyślnie: %s", default.id)
            return Interpretation(choice_id=default.id, reply=default.reply)
        if interpretation.choice_id is not None and interpretation.choice_id not in scene.choices:
            log.error("LLM zwrócił nieznany wybór %r, wybieram: %s", interpretation.choice_id, default.id)
            return Interpretation(choice_id=default.id, reply=default.reply)
        log.info("Intencja: %s | %s", interpretation.choice_id, interpretation.reply)
        return interpretation

    def _say(self, text: str) -> None:
        try:
            self._voice.say(text)
        except Exception:
            log.exception("Błąd TTS, bajka leci dalej bez kwestii: %s", text)
```

- [ ] **Step 5: Uruchom testy**

Run: `python -m pytest tests/test_engine.py -v`
Expected: `11 passed`

- [ ] **Step 6: Commit**

```powershell
git add bajka/ports.py bajka/engine.py tests/test_engine.py
git commit -m "feat: silnik bajki z dopytywaniem i ścieżkami awaryjnymi"
```

---

### Task 4: Analiza intencji przez Azure OpenAI

**Files:**
- Create: `bajka/intent.py`
- Test: `tests/test_intent.py`

**Interfaces:**
- Consumes: `Settings` (Task 2), `Interpretation` (Task 3), `Scene` (Task 1); fikstura `scenario`.
- Produces:
  - `AzureIntentResolver(client, deployment: str, hero: str, temperature: float = 0.3)` — implementuje `IntentResolver`
  - `AzureIntentResolver.from_settings(settings: Settings, hero: str) -> AzureIntentResolver` (tworzy `openai.AzureOpenAI`, timeout 10 s, 1 ponowienie)
  - `UNKNOWN = "nie_wiem"`, `build_messages(hero, scene, transcript)`, `build_response_format(scene)`, `parse_interpretation(content: str, scene: Scene) -> Interpretation` (rzuca `ValueError` przy złym JSON albo wyborze spoza sceny)

Uwagi: `model=` w Azure OpenAI to **nazwa wdrożenia**, nie nazwa modelu. Structured outputs (`response_format` typu `json_schema`, `strict: True`) wymagają wdrożenia `gpt-4o-mini` w wersji `2024-07-18` i `api_version` ≥ `2024-08-01-preview` (domyślne `2024-10-21` spełnia warunek).

- [ ] **Step 1: Napisz testy z atrapą klienta**

`tests/test_intent.py`:

```python
import json
from types import SimpleNamespace

import pytest

from bajka.intent import UNKNOWN, AzureIntentResolver, parse_interpretation


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_resolver(content):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return AzureIntentResolver(client, deployment="gpt-4o-mini", hero="Lisek Feliks"), completions


def test_resolve_returns_choice_and_reply(scenario):
    resolver, _ = make_resolver(json.dumps({"choice": "jaskinia", "reply": "Do jaskini, hura!"}))

    result = resolver.resolve(scenario.scene("intro"), "chcę do tej dziury w górze")

    assert result.choice_id == "jaskinia"
    assert result.reply == "Do jaskini, hura!"


def test_request_uses_deployment_schema_and_prompt(scenario):
    resolver, completions = make_resolver(json.dumps({"choice": "las", "reply": "Las!"}))

    resolver.resolve(scenario.scene("intro"), "do lasu")

    kwargs = completions.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["response_format"]["json_schema"]["strict"] is True
    schema = kwargs["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["choice"]["enum"] == ["las", "jaskinia", UNKNOWN]
    system, user = kwargs["messages"]
    assert "Lisek Feliks" in system["content"]
    assert "Idziemy do mrocznego lasu czy do jaskini?" in system["content"]
    assert "- jaskinia: wejść do jaskini" in system["content"]
    assert user == {"role": "user", "content": "do lasu"}


def test_unknown_intent_returns_none_with_clarifying_reply(scenario):
    content = json.dumps({"choice": UNKNOWN, "reply": "Las czy jaskinia?"})

    result = parse_interpretation(content, scenario.scene("intro"))

    assert result.choice_id is None
    assert result.reply == "Las czy jaskinia?"


def test_choice_outside_scene_is_an_error(scenario):
    with pytest.raises(ValueError, match="rzeka"):
        parse_interpretation(json.dumps({"choice": "rzeka", "reply": "?"}), scenario.scene("intro"))


def test_malformed_json_is_an_error(scenario):
    with pytest.raises(ValueError):
        parse_interpretation("to nie jest JSON", scenario.scene("intro"))
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_intent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bajka.intent'`

- [ ] **Step 3: Zaimplementuj resolver**

`bajka/intent.py`:

```python
"""Analiza intencji dziecka przez Azure OpenAI (np. wdrożenie GPT-4o-mini)."""

from __future__ import annotations

import json
from typing import Any

from bajka.config import Settings
from bajka.ports import Interpretation
from bajka.scenario import Scene

UNKNOWN = "nie_wiem"

SYSTEM_PROMPT = """\
Jesteś bohaterem interaktywnej bajki dla dzieci w wieku 4-8 lat. Twoja postać: {hero}
Przed chwilą zapytałeś dziecko siedzące przed ekranem: "{question}"
Możliwe wybory (identyfikator: znaczenie):
{choices}

Twoje zadanie:
1. Ustal, który wybór ma na myśli dziecko. Interpretuj życzliwie i swobodnie: dzieci mówią
   nieprecyzyjnie, opisowo i z błędami (np. "tam gdzie ciemno", "do tej dziury w górze").
2. Jeśli intencja jest jasna, ustaw "choice" na identyfikator wyboru, a w "reply" napisz
   radosną reakcję bohatera na ten wybór.
3. Jeśli odpowiedź jest nie na temat albo nie da się rozstrzygnąć, ustaw "choice" na
   "{unknown}", a w "reply" ciepło dopytaj, przypominając możliwości.

Zasady dla "reply": mów jako bohater, w pierwszej osobie, po polsku, najwyżej dwa krótkie
zdania, prostymi słowami, bez straszenia i bez emotikon. Nigdy nie wychodź z roli.
"""


def build_messages(hero: str, scene: Scene, transcript: str) -> list[dict[str, str]]:
    choices = "\n".join(f"- {c.id}: {c.description}" for c in scene.choices.values())
    system = SYSTEM_PROMPT.format(hero=hero.strip(), question=scene.question, choices=choices, unknown=UNKNOWN)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": transcript},
    ]


def build_response_format(scene: Scene) -> dict[str, Any]:
    """Structured outputs: model może zwrócić tylko wybór z tej sceny albo UNKNOWN."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "interpretacja",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "choice": {"type": "string", "enum": [*scene.choices, UNKNOWN]},
                    "reply": {"type": "string"},
                },
                "required": ["choice", "reply"],
                "additionalProperties": False,
            },
        },
    }


def parse_interpretation(content: str, scene: Scene) -> Interpretation:
    data = json.loads(content)
    choice = data.get("choice")
    reply = str(data.get("reply", "")).strip()
    if choice == UNKNOWN:
        return Interpretation(choice_id=None, reply=reply)
    if choice not in scene.choices:
        raise ValueError(f"LLM zwrócił nieznany wybór: {choice!r}")
    return Interpretation(choice_id=choice, reply=reply)


class AzureIntentResolver:
    def __init__(self, client: Any, deployment: str, hero: str, temperature: float = 0.3) -> None:
        self._client = client
        self._deployment = deployment
        self._hero = hero
        self._temperature = temperature

    @classmethod
    def from_settings(cls, settings: Settings, hero: str) -> AzureIntentResolver:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.openai_endpoint,
            api_key=settings.openai_api_key,
            api_version=settings.openai_api_version,
            timeout=10.0,
            max_retries=1,
        )
        return cls(client, settings.openai_deployment, hero)

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=build_messages(self._hero, scene, transcript),
            response_format=build_response_format(scene),
            temperature=self._temperature,
            max_tokens=200,
        )
        return parse_interpretation(response.choices[0].message.content or "", scene)
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_intent.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```powershell
git add bajka/intent.py tests/test_intent.py
git commit -m "feat: rozpoznawanie intencji dziecka przez Azure OpenAI"
```

---

### Task 5: Mowa przez Azure AI Speech (STT i TTS)

**Files:**
- Create: `bajka/speech.py`
- Test: `tests/test_speech.py`

**Interfaces:**
- Consumes: `Settings` (Task 2).
- Produces:
  - `make_speech_config(settings: Settings) -> speechsdk.SpeechConfig` (język, timeouty ciszy, format `Riff24Khz16BitMonoPcm`)
  - `AzureListener(recognizer)` + `AzureListener.from_config(config) -> AzureListener` — implementuje `Listener` (domyślny mikrofon, `recognize_once_async`)
  - `AzureVoice(synthesizer, voice: str, language: str, rate: str, play_wav=play_wav_bytes)` + `AzureVoice.from_settings(config, settings) -> AzureVoice` — implementuje `Voice`
  - `SpeechError(RuntimeError)`, `text_from_result(result) -> str | None`, `audio_from_result(result) -> bytes`, `build_ssml(text, voice, language, rate) -> str`, `play_wav_bytes(data: bytes) -> None`

Uwagi: `NoMatch` (cisza/niewyraźnie) zwraca `None`; `Canceled` (sieć, klucz, limit) rzuca `SpeechError` — silnik i tak potraktuje to jak ciszę, ale log pokaże przyczynę. TTS syntezuje z `audio_config=None` (do pamięci), a `play_wav_bytes` blokuje do końca odtwarzania — to gwarantuje, że mikrofon nie usłyszy bohatera.

- [ ] **Step 1: Napisz testy z atrapami wyników SDK**

`tests/test_speech.py`:

```python
import io
import sys
import wave
from types import SimpleNamespace

import azure.cognitiveservices.speech as speechsdk
import pytest

from bajka.speech import (
    AzureListener,
    AzureVoice,
    SpeechError,
    audio_from_result,
    build_ssml,
    play_wav_bytes,
    text_from_result,
)

Reason = speechsdk.ResultReason


def canceled_result():
    details = SimpleNamespace(reason="Error", error_details="401 zły klucz")
    return SimpleNamespace(reason=Reason.Canceled, cancellation_details=details)


def test_recognized_speech_is_stripped():
    result = SimpleNamespace(reason=Reason.RecognizedSpeech, text="  do lasu  ")
    assert text_from_result(result) == "do lasu"


def test_no_match_means_silence():
    assert text_from_result(SimpleNamespace(reason=Reason.NoMatch, text="")) is None


def test_canceled_recognition_raises_with_details():
    with pytest.raises(SpeechError, match="401"):
        text_from_result(canceled_result())


def test_listener_returns_text_from_single_recognition():
    result = SimpleNamespace(reason=Reason.RecognizedSpeech, text="jaskinia")
    recognizer = SimpleNamespace(recognize_once_async=lambda: SimpleNamespace(get=lambda: result))

    assert AzureListener(recognizer).listen() == "jaskinia"


def test_ssml_escapes_text_and_sets_voice_and_rate():
    ssml = build_ssml("Las <i> jaskinia & most", "pl-PL-MarekNeural", "pl-PL", "-10%")

    assert '<voice name="pl-PL-MarekNeural">' in ssml
    assert '<prosody rate="-10%">' in ssml
    assert "Las &lt;i&gt; jaskinia &amp; most" in ssml


def test_voice_synthesizes_ssml_and_plays_audio():
    spoken, played = [], []
    done = SimpleNamespace(reason=Reason.SynthesizingAudioCompleted, audio_data=b"WAV")

    def speak_ssml_async(ssml):
        spoken.append(ssml)
        return SimpleNamespace(get=lambda: done)

    synthesizer = SimpleNamespace(speak_ssml_async=speak_ssml_async)
    voice = AzureVoice(synthesizer, "pl-PL-MarekNeural", "pl-PL", "-10%", play_wav=played.append)

    voice.say("Do lasu!")

    assert "Do lasu!" in spoken[0]
    assert played == [b"WAV"]


def test_canceled_synthesis_raises():
    with pytest.raises(SpeechError, match="401"):
        audio_from_result(canceled_result())


def test_play_wav_bytes_plays_samples_and_waits(monkeypatch):
    calls = []
    fake_sd = SimpleNamespace(
        play=lambda samples, rate: calls.append(("play", samples.shape, rate)),
        wait=lambda: calls.append(("wait",)),
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 240)

    play_wav_bytes(buffer.getvalue())

    assert calls == [("play", (240, 1), 24000), ("wait",)]
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_speech.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bajka.speech'`

- [ ] **Step 3: Zaimplementuj adaptery mowy**

`bajka/speech.py`:

```python
"""Azure AI Speech: rozpoznawanie mowy dziecka (STT) i głos bohatera (TTS)."""

from __future__ import annotations

import io
import logging
import wave
from collections.abc import Callable
from typing import Any
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk

from bajka.config import Settings

log = logging.getLogger(__name__)


class SpeechError(RuntimeError):
    """Azure Speech anulował rozpoznawanie lub syntezę (sieć, klucz, limit)."""


def make_speech_config(settings: Settings) -> speechsdk.SpeechConfig:
    config = speechsdk.SpeechConfig(subscription=settings.speech_key, region=settings.speech_region)
    config.speech_recognition_language = settings.language
    # Ile czekamy, aż dziecko zacznie mówić, i ile ciszy kończy wypowiedź.
    config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(settings.initial_silence_ms)
    )
    config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(settings.end_silence_ms))
    config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    return config


def text_from_result(result: Any) -> str | None:
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text.strip() or None
    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise SpeechError(f"STT anulowane: {details.reason}: {details.error_details}")
    return None  # NoMatch: dziecko milczało albo mówiło niewyraźnie


def audio_from_result(result: Any) -> bytes:
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    details = result.cancellation_details
    raise SpeechError(f"TTS anulowane: {details.reason}: {details.error_details}")


def build_ssml(text: str, voice: str, language: str, rate: str) -> str:
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">'
        f'<voice name="{voice}"><prosody rate="{rate}">{escape(text)}</prosody></voice></speak>'
    )


def play_wav_bytes(data: bytes) -> None:
    """Odtwarza WAV (PCM 16-bit) i blokuje do końca, więc mikrofon nie słyszy bohatera."""
    import numpy as np
    import sounddevice as sd

    with wave.open(io.BytesIO(data)) as wav:
        rate, channels = wav.getframerate(), wav.getnchannels()
        frames = wav.readframes(wav.getnframes())
    sd.play(np.frombuffer(frames, dtype=np.int16).reshape(-1, channels), rate)
    sd.wait()


class AzureListener:
    def __init__(self, recognizer: Any) -> None:
        self._recognizer = recognizer

    @classmethod
    def from_config(cls, config: speechsdk.SpeechConfig) -> AzureListener:
        audio = speechsdk.audio.AudioConfig(use_default_microphone=True)
        return cls(speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio))

    def listen(self) -> str | None:
        log.info("Słucham…")
        return text_from_result(self._recognizer.recognize_once_async().get())


class AzureVoice:
    def __init__(
        self,
        synthesizer: Any,
        voice: str,
        language: str,
        rate: str,
        play_wav: Callable[[bytes], None] = play_wav_bytes,
    ) -> None:
        self._synthesizer = synthesizer
        self._voice = voice
        self._language = language
        self._rate = rate
        self._play_wav = play_wav

    @classmethod
    def from_settings(cls, config: speechsdk.SpeechConfig, settings: Settings) -> AzureVoice:
        # audio_config=None: synteza do pamięci, odtwarzamy sami i wiemy, kiedy bohater skończył.
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        return cls(synthesizer, settings.voice, settings.language, settings.voice_rate)

    def say(self, text: str) -> None:
        log.info("Bohater: %s", text)
        ssml = build_ssml(text, self._voice, self._language, self._rate)
        result = self._synthesizer.speak_ssml_async(ssml).get()
        self._play_wav(audio_from_result(result))
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_speech.py -v`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```powershell
git add bajka/speech.py tests/test_speech.py
git commit -m "feat: STT z mikrofonu i głos bohatera przez Azure AI Speech"
```

---

### Task 6: Odtwarzacz VLC i klipy-zaślepki

**Files:**
- Create: `bajka/placeholders.py`, `bajka/player.py`
- Test: `tests/test_placeholders.py` (player sprawdzany ręcznie — patrz Global Constraints)

**Interfaces:**
- Consumes: `Scenario`, `load_scenario` (Task 1); fikstura `scenario`.
- Produces:
  - `planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]` — (ścieżka, kolor, czy z dźwiękiem); pętle oczekiwania są ciche
  - `ffmpeg_command(target: Path, color: str, seconds: float, with_tone: bool) -> list[str]`
  - CLI: `python -m bajka.placeholders SCENARIUSZ [--seconds 4.0] [--force]` (domyślnie pomija istniejące pliki)
  - `VlcPlayer(root: tk.Tk, fullscreen: bool = True)` — implementuje `Player`; dodatkowo `stop() -> None`
  - Podgląd: `python -m bajka.player KLIP [PĘTLA]`

Uwagi do VLC: callback zdarzenia (`MediaPlayerEndReached`, `MediaPlayerEncounteredError`) przychodzi z wątku VLC — wolno w nim tylko ustawić `threading.Event`, wywołanie API libvlc spowoduje zakleszczenie. `video_set_mouse_input(False)` i `video_set_key_input(False)` są konieczne, żeby `Esc` trafiał do tkinter, a nie do VLC.

- [ ] **Step 1: Napisz testy generatora zaślepek**

`tests/test_placeholders.py`:

```python
from pathlib import Path

from bajka.placeholders import ffmpeg_command, planned_clips


def test_scene_clip_has_tone_and_idle_loop_is_silent(scenario):
    clips = planned_clips(scenario)

    assert clips[0] == (Path("film/intro.mp4"), "darkgreen", True)
    assert clips[1] == (Path("film/intro_idle.mp4"), "darkgreen", False)
    assert [path.name for path, _, _ in clips] == ["intro.mp4", "intro_idle.mp4", "las.mp4", "jaskinia.mp4"]


def test_ffmpeg_command_for_silent_loop_has_no_audio():
    cmd = ffmpeg_command(Path("out/idle.mp4"), "indigo", 4.0, with_tone=False)

    assert "-an" in cmd
    assert not any(part.startswith("sine=") for part in cmd)
    assert cmd[-1] == str(Path("out/idle.mp4"))


def test_ffmpeg_command_for_clip_adds_tone():
    cmd = ffmpeg_command(Path("out/intro.mp4"), "darkgreen", 2.5, with_tone=True)

    assert "color=c=darkgreen:s=1280x720:r=25:d=2.5" in cmd
    assert "sine=frequency=440:duration=2.5" in cmd
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_placeholders.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bajka.placeholders'`

- [ ] **Step 3: Zaimplementuj generator zaślepek**

`bajka/placeholders.py`:

```python
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
    """(ścieżka, kolor, czy z dźwiękiem) — klip sceny ma ton, pętla oczekiwania jest cicha."""
    clips = []
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        clips.append((scene.clip, color, True))
        if scene.idle is not None:
            clips.append((scene.idle, color, False))
    return clips


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
```

- [ ] **Step 4: Uruchom testy i wygeneruj klipy**

Run: `python -m pytest tests/test_placeholders.py -v`
Expected: `3 passed`

Generator wymaga ffmpeg w PATH. Jeśli `ffmpeg -version` nie działa: `winget install --id Gyan.FFmpeg -e` i otwórz nowy terminal (winget dopisuje PATH tylko dla nowych sesji).

Run: `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml`
Expected: cztery linie `utworzono: scenarios\clips\...` (`intro.mp4`, `intro_idle.mp4`, `las.mp4`, `jaskinia.mp4`). Ponowne uruchomienie wypisuje `pomijam, plik istnieje: ...`.

- [ ] **Step 5: Zaimplementuj odtwarzacz VLC**

`bajka/player.py`:

```python
"""Odtwarzacz VLC osadzony w jednym oknie tkinter, które trwa przez cały seans.

Moduł importuje `vlc`, który wymaga zainstalowanego VLC 64-bit, dlatego testy go nie importują.
Podgląd przejścia klip → pętla: python -m bajka.player KLIP [PĘTLA]   (Esc zamyka)
"""

from __future__ import annotations

import logging
import sys
import threading
import tkinter as tk
from pathlib import Path

import vlc

log = logging.getLogger(__name__)

LOOP_FOREVER = "input-repeat=65535"


class VlcPlayer:
    def __init__(self, root: tk.Tk, fullscreen: bool = True) -> None:
        root.title("Bajka")
        root.configure(background="black")
        if fullscreen:
            root.attributes("-fullscreen", True)
            root.configure(cursor="none")
        else:
            root.geometry("1280x720")
        surface = tk.Frame(root, background="black")
        surface.pack(fill=tk.BOTH, expand=True)
        root.update()  # okno musi istnieć, zanim przekażemy jego uchwyt do VLC

        self._instance = vlc.Instance("--quiet", "--no-video-title-show")
        self._player = self._instance.media_player_new()
        self._player.video_set_mouse_input(False)  # klawisze i mysz zostają w tkinter (Esc)
        self._player.video_set_key_input(False)
        _attach_to_window(self._player, surface.winfo_id())

        self._finished = threading.Event()
        events = self._player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_finished)
        events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_finished)

    def play(self, clip: Path) -> None:
        log.info("Wideo: %s", clip.name)
        self._finished.clear()
        self._start(self._instance.media_new(str(clip)))
        self._finished.wait()

    def loop(self, clip: Path) -> None:
        log.info("Pętla: %s", clip.name)
        media = self._instance.media_new(str(clip))
        media.add_option(LOOP_FOREVER)
        self._start(media)

    def stop(self) -> None:
        self._player.stop()

    def _start(self, media: vlc.Media) -> None:
        self._player.set_media(media)
        self._player.play()

    def _on_finished(self, _event: vlc.Event) -> None:
        # Wywoływane z wątku VLC: tu nie wolno wołać API libvlc, tylko dać sygnał.
        self._finished.set()


def _attach_to_window(player: vlc.MediaPlayer, handle: int) -> None:
    if sys.platform.startswith("win"):
        player.set_hwnd(handle)
    elif sys.platform.startswith("linux"):
        player.set_xwindow(handle)
    else:
        log.warning("Brak osadzania na %s: VLC otworzy własne okno", sys.platform)


def _preview(argv: list[str]) -> None:
    root = tk.Tk()
    player = VlcPlayer(root, fullscreen=False)

    def show() -> None:
        player.play(Path(argv[0]))
        if len(argv) > 1:
            player.loop(Path(argv[1]))

    def close(_event: object = None) -> None:
        player.stop()
        root.destroy()

    root.bind("<Escape>", close)
    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=show, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _preview(sys.argv[1:])
```

- [ ] **Step 6: Sprawdź odtwarzacz ręcznie**

Run: `python -c "import vlc; print(vlc.libvlc_get_version())"`
Expected: `b'3.0.…'` (bez `FileNotFoundError` dla `libvlc.dll`)

Run: `python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4`
Expected: okno „Bajka” 1280×720 bez nakładki z nazwą pliku; 4 s zielonej planszy z tonem 440 Hz, potem ta sama plansza w ciszy w pętli. Okno nie znika ani nie otwiera się na nowo przy przejściu klip → pętla. W logu `Wideo: intro.mp4`, potem `Pętla: intro_idle.mp4`. `Esc` zamyka okno.

- [ ] **Step 7: Uruchom cały zestaw testów**

Run: `python -m pytest`
Expected: `41 passed` (Taski 1–6)

- [ ] **Step 8: Commit**

```powershell
git add bajka/placeholders.py bajka/player.py tests/test_placeholders.py
git commit -m "feat: odtwarzacz VLC w oknie tkinter i generator klipów-zaślepek"
```

---

### Task 7: Aplikacja, tryb próbny `--text` i README

**Files:**
- Create: `bajka/console.py`, `bajka/app.py`, `bajka/__main__.py`, `README.md`
- Test: `tests/test_console.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: wszystko z Tasków 1–6: `load_scenario`, `missing_media`, `ScenarioError`, `load_settings`, `ConfigError`, `OPENAI_VARS`, `SPEECH_VARS`, `Settings`, `StoryEngine`, `Listener`, `Voice`, `AzureIntentResolver.from_settings(settings, hero)`, `make_speech_config(settings)`, `AzureListener.from_config(config)`, `AzureVoice.from_settings(config, settings)`, `VlcPlayer(root, fullscreen)`, `VlcPlayer.stop()`.
- Produces:
  - `ConsoleListener(read=input)`, `ConsoleVoice(write=print)` — implementują `Listener`/`Voice`
  - `parse_args(argv) -> argparse.Namespace` z polami `scenario: Path`, `text: bool`, `windowed: bool`
  - `build_speech(settings, text_mode) -> tuple[Listener, Voice]`
  - `main(argv: list[str] | None = None) -> int` — `2` przy błędzie scenariusza, ustawień albo brakujących klipach; `0` po zakończeniu bajki
  - `run_window(root, player, engine) -> None` — tkinter w wątku głównym, silnik w wątku-demonie, zamknięcie okna po końcu bajki albo `Esc`
  - `python -m bajka SCENARIUSZ [--text] [--windowed]`

Uwaga: `main()` importuje `tkinter`, `bajka.player` i `bajka.intent` dopiero po walidacji, więc testy ścieżek błędów nie potrzebują VLC ani okna.

- [ ] **Step 1: Napisz testy trybu konsolowego i CLI**

`tests/test_console.py`:

```python
from bajka.console import ConsoleListener, ConsoleVoice


def test_listener_returns_typed_answer():
    assert ConsoleListener(read=lambda prompt: "  do lasu ").listen() == "do lasu"


def test_empty_line_is_silence():
    assert ConsoleListener(read=lambda prompt: "   ").listen() is None


def test_end_of_input_is_silence():
    def read(prompt):
        raise EOFError

    assert ConsoleListener(read=read).listen() is None


def test_voice_prints_hero_line():
    printed = []

    ConsoleVoice(write=printed.append).say("Do lasu!")

    assert printed == ["Bohater: Do lasu!"]
```

`tests/test_app.py`:

```python
import yaml

from bajka.app import main, parse_args
from bajka.config import OPENAI_VARS, SPEECH_VARS


def write_scenario(path, scenario_dict):
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


def test_flags_are_parsed():
    args = parse_args(["bajka.yaml", "--text", "--windowed"])

    assert args.scenario.name == "bajka.yaml"
    assert args.text and args.windowed


def test_default_is_fullscreen_with_voice():
    args = parse_args(["bajka.yaml"])

    assert not args.text and not args.windowed


def test_missing_scenario_file_exits_with_code_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert main([str(tmp_path / "nie_ma.yaml")]) == 2


def test_missing_settings_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)  # w katalogu testu nie ma pliku .env
    for name in OPENAI_VARS + SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path)]) == 2


def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)
    for name in OPENAI_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--text"]) == 2
```

- [ ] **Step 2: Uruchom testy i sprawdź, że nie przechodzą**

Run: `python -m pytest tests/test_console.py tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bajka.console'` oraz `No module named 'bajka.app'`

- [ ] **Step 3: Zaimplementuj tryb konsolowy**

`bajka/console.py`:

```python
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
```

- [ ] **Step 4: Zaimplementuj aplikację i punkt wejścia**

`bajka/app.py`:

```python
"""Złożenie aplikacji: okno tkinter w wątku głównym, silnik bajki w wątku roboczym."""

from __future__ import annotations

import argparse
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from bajka.config import ConfigError, Settings, load_settings
from bajka.engine import StoryEngine
from bajka.ports import Listener, Voice
from bajka.scenario import ScenarioError, load_scenario, missing_media

if TYPE_CHECKING:
    import tkinter as tk

    from bajka.player import VlcPlayer

log = logging.getLogger("bajka")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m bajka", description="Interaktywna Bajka Głosowa Zero-UI")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument(
        "--text", action="store_true", help="tryb próbny: odpowiedzi z klawiatury, kwestie bohatera w konsoli"
    )
    parser.add_argument("--windowed", action="store_true", help="okno zamiast pełnego ekranu")
    return parser.parse_args(argv)


def build_speech(settings: Settings, text_mode: bool) -> tuple[Listener, Voice]:
    if text_mode:
        from bajka.console import ConsoleListener, ConsoleVoice

        return ConsoleListener(), ConsoleVoice()
    from bajka.speech import AzureListener, AzureVoice, make_speech_config

    config = make_speech_config(settings)
    return AzureListener.from_config(config), AzureVoice.from_settings(config, settings)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    args = parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        settings = load_settings(require_speech=not args.text)
    except (ScenarioError, ConfigError, OSError) as exc:
        log.error("%s", exc)
        return 2
    missing = missing_media(scenario)
    if missing:
        log.error("Brak plików wideo: %s", ", ".join(map(str, missing)))
        return 2

    import tkinter as tk

    from bajka.intent import AzureIntentResolver
    from bajka.player import VlcPlayer

    listener, voice = build_speech(settings, args.text)
    resolver = AzureIntentResolver.from_settings(settings, scenario.hero)
    root = tk.Tk()
    player = VlcPlayer(root, fullscreen=not args.windowed)
    engine = StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=settings.max_reprompts)
    run_window(root, player, engine)
    return 0


def run_window(root: tk.Tk, player: VlcPlayer, engine: StoryEngine) -> None:
    finished = threading.Event()

    def story() -> None:
        try:
            visited = engine.run()
            log.info("Koniec bajki, ścieżka: %s", " -> ".join(visited))
        except Exception:
            log.exception("Bajka przerwana błędem")
        finally:
            finished.set()

    def close(_event: object = None) -> None:
        player.stop()
        root.destroy()

    def poll() -> None:
        # tkinter nie jest wątkowo bezpieczny, więc koniec bajki sprawdzamy z wątku głównego.
        if finished.is_set():
            close()
        else:
            root.after(200, poll)

    root.bind("<Escape>", close)
    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=story, daemon=True).start()
    root.after(200, poll)
    root.mainloop()
```

`bajka/__main__.py`:

```python
from bajka.app import main

raise SystemExit(main())
```

- [ ] **Step 5: Uruchom cały zestaw testów**

Run: `python -m pytest`
Expected: `50 passed`

- [ ] **Step 6: Napisz README**

`README.md`:

````markdown
# Interaktywna Bajka Głosowa Zero-UI

Prototyp na hackathon FilmSpring Open 2026: bajka, w której ekran słucha i odpowiada.
Bohater odwraca się do widza i zadaje pytanie, dziecko odpowiada głosem, a historia idzie
w wybraną stronę. Bez myszki i klawiatury.

## Jak to działa

1. VLC odtwarza klip, w którym bohater zadaje pytanie (np. „las czy jaskinia?”).
2. Startuje cicha pętla oczekiwania, a Azure AI Speech słucha mikrofonu i sam wykrywa koniec wypowiedzi.
3. Azure OpenAI (GPT-4o-mini) rozpoznaje intencję dziecka i pisze reakcję bohatera.
4. Azure TTS wypowiada reakcję, potem startuje klip wybranej ścieżki.
5. Cisza albo niejasna odpowiedź: bohater dopytuje (domyślnie 2 razy), potem sam wybiera ścieżkę domyślną.

Mikrofon jest wyłączony, gdy bohater mówi, więc nie słyszy sam siebie. Awaria STT, LLM albo TTS
nie zatrzymuje bajki: zamiast tego wybierana jest ścieżka domyślna albo kwestia ze scenariusza.

## Wymagania

- Windows 10/11 (działa też na Linuksie; na macOS VLC otworzy osobne okno)
- Python 3.11+ w wersji 64-bit
- VLC 3.x 64-bit: `winget install --id VideoLAN.VLC -e`
- ffmpeg, tylko do klipów-zaślepek: `winget install --id Gyan.FFmpeg -e`
- Azure: zasób AI Speech oraz zasób Azure OpenAI z wdrożeniem modelu `gpt-4o-mini`

## Instalacja

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env   # uzupełnij klucze Azure
```

## Uruchomienie

```powershell
# klipy-zaślepki (kolorowe plansze), dopóki nie ma animacji
python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml

# próba bez mikrofonu: odpowiedzi wpisujesz w konsoli, kwestie bohatera są wypisywane
python -m bajka scenarios/las_czy_jaskinia.yaml --text --windowed

# pokaz: pełny ekran, mikrofon i głos bohatera
python -m bajka scenarios/las_czy_jaskinia.yaml
```

`Esc` zamyka aplikację. W trybie `--text` kliknij okno konsoli, żeby wpisać odpowiedź.
Podgląd przejścia klip → pętla bez reszty systemu: `python -m bajka.player KLIP PĘTLA`.

## Scenariusz

Bajka to graf scen w YAML ([przykład](scenarios/las_czy_jaskinia.yaml)). Ścieżki klipów są
względne wobec pliku scenariusza. Scena bez `choices` kończy bajkę.

| Pole | Opis |
|---|---|
| `hero` | Opis bohatera dla LLM: imię, charakter, sposób mówienia |
| `start` | Identyfikator pierwszej sceny |
| `scenes.<id>.clip` | Klip sceny (bohater zadaje pytanie albo kończy historię) |
| `scenes.<id>.idle` | Cicha pętla oczekiwania na odpowiedź (wymagana, gdy są `choices`) |
| `scenes.<id>.question` | Pytanie zadane w klipie; trafia do promptu LLM |
| `scenes.<id>.reprompt` | Kwestia bohatera, gdy dziecko milczy |
| `scenes.<id>.fallback` | Opcjonalnie: wstęp, gdy bohater sam wybiera (domyślnie „Dobrze, to ja wybiorę!”) |
| `scenes.<id>.default` | Wybór, gdy po dopytaniach nadal brak decyzji albo LLM zawiedzie |
| `choices.<id>.description` | Znaczenie wyboru dla LLM, np. „pójść do mrocznego lasu” |
| `choices.<id>.next` | Scena, która nastąpi po tym wyborze |
| `choices.<id>.reply` | Statyczna reakcja bohatera, gdy LLM nie odpowie |

## Wskazówki do klipów

- Pętla oczekiwania musi być bez dźwięku, bo w tym czasie słucha mikrofon.
- Ostatnia klatka klipu z pytaniem = pierwsza klatka pętli, wtedy przejście jest niewidoczne.
- Format: MP4, H.264 + AAC.
- Klipy nie są w repozytorium (`scenarios/clips/` jest w `.gitignore`), trzymajcie je na dysku współdzielonym.

## Architektura

| Moduł | Rola |
|---|---|
| `bajka/scenario.py` | Wczytanie i walidacja scenariusza YAML |
| `bajka/config.py` | Ustawienia z `.env` |
| `bajka/ports.py` | Interfejsy: `Player`, `Listener`, `Voice`, `IntentResolver` |
| `bajka/engine.py` | `StoryEngine`: przebieg bajki, dopytywanie, ścieżki awaryjne |
| `bajka/intent.py` | Azure OpenAI: intencja + kwestia bohatera (structured outputs) |
| `bajka/speech.py` | Azure AI Speech: STT z mikrofonu, TTS z odtwarzaniem do końca |
| `bajka/player.py` | VLC osadzony w pełnoekranowym oknie tkinter |
| `bajka/console.py` | Tryb `--text` do prób bez mikrofonu |
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg) |
| `bajka/app.py` | Złożenie całości i uruchomienie |

Silnik zależy tylko od interfejsów z `ports.py`, więc testy działają na atrapach,
bez Azure, mikrofonu i VLC.

## Testy

```powershell
python -m pytest
```

## Problemy

- `FileNotFoundError: ... libvlc.dll`: brak VLC albo zainstalowana wersja 32-bit.
- Bohater nie słyszy dziecka: Ustawienia Windows → Prywatność → Mikrofon → zezwól aplikacjom klasycznym;
  sprawdź domyślne urządzenie nagrywania.
- `STT anulowane: ... 401` albo `TTS anulowane`: zły `AZURE_SPEECH_KEY` lub `AZURE_SPEECH_REGION`.
- Dziecko musi długo czekać albo jest ucinane: dostrój `BAJKA_INITIAL_SILENCE_MS` i `BAJKA_END_SILENCE_MS`.
- Krzaki zamiast polskich znaków w konsoli: `$env:PYTHONUTF8 = "1"`.
````

- [ ] **Step 7: Próba end-to-end w trybie tekstowym**

Wymaga `.env` z kluczami Azure OpenAI (klucze Speech nie są potrzebne): `Copy-Item .env.example .env` i uzupełnij `AZURE_OPENAI_*`.

Run: `python -m bajka scenarios/las_czy_jaskinia.yaml --text --windowed`
Expected: okno z zieloną planszą i tonem, potem cicha pętla i w konsoli `Dziecko> `. Wpisz `chcę tam gdzie ciemno` → w logu `Intencja: las | …`, w konsoli `Bohater: …` (reakcja wygenerowana przez LLM), potem klip `las.mp4` i okno zamyka się samo; ostatni log `Koniec bajki, ścieżka: intro -> las`. Uruchom ponownie i wpisz `banan` → bohater dopytuje (`Intencja: None | …`).

- [ ] **Step 8: Próba end-to-end z mikrofonem**

Uzupełnij `AZURE_SPEECH_KEY` i `AZURE_SPEECH_REGION` w `.env`.

Run: `python -m bajka scenarios/las_czy_jaskinia.yaml --windowed`
Expected: po klipie log `Słucham…`; powiedz „do jaskini” → `Dziecko: 'Do jaskini.'`, bohater odpowiada głosem `pl-PL-MarekNeural`, potem klip `jaskinia.mp4`. Ponownie: milcz 6 s → bohater mówi `reprompt`; milcz trzy razy → „Dobrze, to ja wybiorę! Do lasu! …” i klip `las.mp4`. Na koniec bez `--windowed`: pełny ekran, brak kursora, `Esc` zamyka.

- [ ] **Step 9: Commit**

```powershell
git add bajka/console.py bajka/app.py bajka/__main__.py README.md tests/test_console.py tests/test_app.py
git commit -m "feat: uruchamianie bajki, tryb próbny --text i README"
```

---

## Poza zakresem szkieletu

Świadomie pominięte (YAGNI na hackathon), łatwe do dodania dzięki interfejsom z `ports.py`:

- ElevenLabs jako alternatywny `Voice`.
- Przenikanie (crossfade) między klipami — VLC przełącza z krótką czarną klatką; zalecenie montażowe w README (ostatnia klatka klipu = pierwsza klatka pętli) w praktyce to maskuje.
- Animacja „słucham” reagująca na głośność mikrofonu.
- Zapisywanie nagrań dziecka (prywatność: domyślnie nic nie jest zapisywane na dysku).

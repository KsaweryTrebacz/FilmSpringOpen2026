# Film, który czuje salę — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Usunąć z projektu rysowanie na żywo i w zamian pokazać jury film, który dopasowuje wersje scen do (symulowanego) tętna sali, z panelem w przeglądarce, który tłumaczy każdą decyzję filmu.

**Architecture:** Nowy moduł `bajka/pulse.py` (symulator tętna, stan sali, wybór wersji) za kontraktem `AudiencePulse`; scenariusz dostaje `mood` i `variants`; silnik przed sceną z wersjami czyta tętno i wybiera klip, a wszystkie decyzje wysyła do obserwatora `ShowObserver`. Panel (`bajka/panel.py` + `bajka/panel_app/index.html`) to serwer HTTP ze standardowej biblioteki, który trzyma stan seansu w pamięci i steruje symulatorem. Flaga `--panel` składa to w `bajka/app.py`.

**Tech Stack:** Python 3.11+, standardowa biblioteka (`http.server`, `threading`), PyYAML, pytest; strona panelu w czystym HTML/CSS/JS bez zewnętrznych bibliotek.

Spec: [docs/superpowers/specs/2026-10-16-film-czuje-sale-design.md](../specs/2026-10-16-film-czuje-sale-design.md).

## Global Constraints

- Pliki wspólne (`bajka/engine.py`, `bajka/app.py`, `bajka/scenario.py`, `bajka/ports.py`, `bajka/safety.py`, `bajka/placeholders.py`, dokumenty) zmieniamy wyłącznie blokami „Zamień … na …” z tego planu, nigdy przepisaniem całego pliku. Każdy blok „Zamień” występuje w pliku dokładnie raz. Zachowujemy końce linii plików (CRLF zostaje CRLF).
- Kod osoby A działa dalej: aplikacja mobilna (`Audience`, `_decide`, `_ask_audience`, `_collect`), krzykomierz (`_vote`, `_shout_round`), `bajka/mobile.py`. W jej kodzie dochodzą tylko wywołania zdarzeń dla panelu.
- Esc dalej zatrzymuje bajkę od razu (`StoryEngine.stop()`, `_Stopped`, twarde wyjście w `bajka/__main__.py`).
- Bez nowych zależności. Strona panelu nie ładuje niczego z internetu (bez `<link>`, bez `src="http…"`).
- Nazwy i wartości dokładnie jak w specu:
  - zdarzenia: `scena`, `odniesienie`, `wersja`, `glosy`, `decyzja`; sposób decyzji: `wiekszosc`, `okrzyk`, `odpowiedz`, `domyslna`; wersja bez zmian: `zwykla`,
  - `mood`: `spokojny` / `zywy`; klucze `variants`: `spokojna` / `zywa`,
  - stany sali: `pobudzona` / `w normie` / `znudzona`; progi `BAJKA_PULSE_EXCITED=1.15`, `BAJKA_PULSE_BORED=0.97`,
  - stany gotowe symulatora: `spokojna` 90, `ekscytuje-sie` 115, `nudzi-sie` 85; zakres 60–160; stała czasowa 5 s; drganie ±1,5,
  - panel: `BAJKA_PANEL_HOST=127.0.0.1`, `BAJKA_PANEL_PORT=8090`, historia tętna 120 próbek, dziennik 20 wpisów, odświeżanie strony co 0,5 s,
  - włączenie: flaga `--panel` albo `BAJKA_PANEL=1`.
- Teksty dla ludzi (komunikaty, logi, strona panelu, dokumenty) po polsku. Commity po polsku z przedrostkiem `feat:`, `fix:`, `test:` albo `docs:`.
- Testy działają bez sieci, mikrofonu i VLC: `python -m pytest`.

## Mapa plików

| Plik | Odpowiedzialność | Zadanie |
|---|---|---|
| `bajka/imagine.py`, `bajka/illustrate.py`, `bajka/motion.py` i ich testy, `scenarios/rysowanie_na_zywo.yaml`, `scenarios/pomiar_obrazow.yaml`, `scenarios/karta_postaci.yaml` | Usuwane: rysowanie na żywo | 1 |
| `bajka/scenario.py` | Graf scen; bez scen `open`/`generated`; nowe `mood` i `variants` | 1, 3 |
| `bajka/ports.py` | Kontrakty: bez `Vision`/`Imaginer`/`Illustrator`/`Animator`; nowe `Pulse`, `AudiencePulse`, `ShowObserver` | 1, 2, 4 |
| `bajka/pulse.py` (nowy) | Symulator tętna, `hall_state`, `pick_variant`, demo `python -m bajka.pulse` | 2, 3 |
| `bajka/engine.py` | Silnik: bez rysowania; wybór wersji według tętna; zdarzenia dla panelu | 1, 3, 4 |
| `bajka/placeholders.py` | Zaślepki: wersje scen i nazwa pliku na planszy | 1, 3 |
| `bajka/panel.py` (nowy) | `scenario_graph`, `PanelState`, `PanelServer`, demo `python -m bajka.panel` | 4 |
| `bajka/panel_app/index.html` (nowy) | Strona panelu dla jury | 5 |
| `bajka/app.py` | Złożenie: bez rysowania; `--panel`, `build_panel` | 1, 6 |
| `scenarios/klub_ciekawskich.yaml` | `mood: spokojny`, spokojne wersje `las`, `wiaterek`, `swieto` | 3 |
| `docs/DEMO_DLA_JURY.md` (nowy), README, `docs/*.md`, `.env.example`, `.gitignore` | Dokumentacja i konfiguracja | 1, 2, 6 |

---

### Task 1: Usunięcie rysowania na żywo

**Files:**
- Delete: `bajka/imagine.py`, `bajka/illustrate.py`, `bajka/motion.py`, `tests/test_imagine.py`, `tests/test_illustrate.py`, `tests/test_motion.py`, `tests/test_engine_open.py`, `tests/test_engine_generated.py`, `tests/test_scenario_live.py`, `tests/test_scenario_generated.py`, `tests/test_app_live.py`, `tests/live_fakes.py`, `scenarios/rysowanie_na_zywo.yaml`, `scenarios/pomiar_obrazow.yaml`, `scenarios/karta_postaci.yaml`
- Modify: `bajka/ports.py`, `bajka/scenario.py`, `bajka/engine.py`, `bajka/app.py`, `bajka/safety.py`, `bajka/placeholders.py`
- Modify (docs): `README.md`, `docs/ONBOARDING.md`, `docs/PODZIAL_PRACY.md`, `docs/ZGODNOSC_Z_REGULAMINEM.md`, `docs/DO_ZROBIENIA.md`, `docs/LOKALNE_AI.md`, `scenarios/klub_ciekawskich.md` (scena SC. 7b wycofana), `.gitignore`, `.env.example`
- Test: `tests/test_scenario.py`, `tests/test_engine.py`, `tests/test_app.py`, `tests/test_safety.py`

**Interfaces:**
- Consumes: obecny kod (main po commicie ze specem).
- Produces:
  - `Scene(id, clip: Path, idle, question, reprompt, fallback, default, choices, vote)` z `is_ending == not choices` (bez `kind`, `successors` i pól rysowania),
  - `Scenario(hero, start, scenes)` i `missing_media(scenario)` tylko dla klipów, pętli i `call_clip`,
  - `REMOVED_SCENE_FIELDS`, `REMOVED_SCENARIO_FIELDS` i `_reject_removed(data, removed, where)` w `bajka/scenario.py`,
  - `StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=2, meter=None, audience=None)` z `stop()`, `_play`, `_loop` i bez rysowania,
  - komunikat aplikacji o brakujących plikach: `Brak plików wideo: …`.

- [ ] **Step 1: Testy — stare pola scenariusza dają czytelny błąd, Esc działa na zwykłych scenach, komunikat o plikach**

Testy zatrzymania po Esc przenosimy z usuwanego `tests/test_engine_open.py` do `tests/test_engine.py` (na zwykłe sceny); one przechodzą już teraz i pilnują, żeby usunięcie niczego nie zepsuło.

<!-- edit: tests/test_scenario.py -->
Zamień w `tests/test_scenario.py`:

```python

def test_keywords_must_be_a_list_of_words(scenario_dict):
```

na:

```python

@pytest.mark.parametrize("field", ["kind", "image_prompt", "fallback_clips", "next"])
def test_live_drawing_scene_fields_are_rejected_with_a_clear_message(scenario_dict, field):
    scenario_dict["scenes"]["las"][field] = "open"
    with pytest.raises(ScenarioError, match=f"scena 'las': pola {field} .*rysowanie na żywo usunięto"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


@pytest.mark.parametrize("field", ["style", "references"])
def test_live_drawing_scenario_fields_are_rejected_with_a_clear_message(scenario_dict, field):
    scenario_dict[field] = "watercolor"
    with pytest.raises(ScenarioError, match=f"scenariusz: pola {field} .*rysowanie na żywo usunięto"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_keywords_must_be_a_list_of_words(scenario_dict):
```

<!-- edit: tests/test_engine.py -->
Zamień w `tests/test_engine.py`:

```python
        answer = self._answers[transcript]
        if isinstance(answer, Exception):
            raise answer
        return answer

```

na:

```python
        answer = self._answers[transcript]
        if isinstance(answer, Exception):
            raise answer
        return answer


class StoppingVoice(FakeVoice):
    """Esc po wskazanej kwestii: okno się zamyka, a silnik dostaje stop() z wątku okna."""

    def __init__(self, stop_after):
        super().__init__()
        self.engine = None  # silnik powstaje po głosie, test podstawia go przed run()
        self._stop_after = stop_after

    def say(self, text):
        super().say(text)
        if text == self._stop_after:
            self.engine.stop()


class StoppingListener(FakeListener):
    """Esc w trakcie słuchania: odpowiedź przychodzi, ale okno zamyka się, zanim silnik ją obsłuży."""

    def __init__(self, *answers):
        super().__init__(*answers)
        self.engine = None

    def listen(self):
        answer = super().listen()
        self.engine.stop()
        return answer

```

<!-- edit: tests/test_engine.py -->
Zamień w `tests/test_engine.py`:

```python
    assert voice.lines == ["Las!", "Hop, hop!"]

```

na:

```python
    assert voice.lines == ["Las!", "Hop, hop!"]


# Zamknięcie okna (Esc) w trakcie bajki


def test_stop_after_hero_reply_ends_the_run_without_playing_or_saying_more(scenario):
    resolver = FakeResolver({"las": Interpretation("las", LAS_REPLY)})
    voice = StoppingVoice(stop_after=LAS_REPLY)
    engine, player, _ = make_engine(scenario, FakeListener("las"), resolver, voice=voice)
    voice.engine = engine

    assert engine.run() == ["intro"]

    assert voice.lines == [LAS_REPLY]  # po Esc bohater już nic nie mówi
    assert ("play", "las.mp4") not in player.calls  # ani nie przechodzi do następnej sceny


def test_stop_while_listening_ends_the_run_before_the_answer_is_acted_on(scenario):
    listener = StoppingListener("las")
    resolver = FakeResolver({"las": Interpretation("las", LAS_REPLY)})
    engine, player, voice = make_engine(scenario, listener, resolver)
    listener.engine = engine

    assert engine.run() == ["intro"]

    assert voice.lines == []
    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4")]

```

<!-- edit: tests/test_app.py -->
Zamień w `tests/test_app.py`:

```python
def test_missing_media_files_exit_with_code_2_and_name_clips_and_reference_images(
    tmp_path, monkeypatch, scenario_dict, caplog
):
```

na:

```python
def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict, caplog):
```

<!-- edit: tests/test_app.py -->
Zamień w `tests/test_app.py`:

```python
    assert "Brak plików (klipy wideo, obrazy referencyjne)" in caplog.text
```

na:

```python
    assert "Brak plików wideo" in caplog.text
```

<!-- edit: tests/test_safety.py -->
Zamień w `tests/test_safety.py`:

```python
from bajka.ports import Imaginer, IntentResolver, Interpretation, Vision
from bajka.safety import MAX_REPLY_CHARS, SafeImaginer, SafeReplyResolver, is_safe_reply
```

na:

```python
from bajka.ports import IntentResolver, Interpretation
from bajka.safety import MAX_REPLY_CHARS, SafeReplyResolver, is_safe_reply
```

<!-- edit: tests/test_safety.py -->
Zamień w `tests/test_safety.py`:

```python

class FakeImaginer:
    def __init__(self, vision):
        self._vision = vision

    def imagine(self, scene, transcript):
        return self._vision


def test_safe_imaginer_passes_friendly_vision(scenario):
    vision = Vision("Tęczowe wstążki? Już rysuję!", "rainbow ribbons")
    safe = SafeImaginer(FakeImaginer(vision))

    assert isinstance(safe, Imaginer)
    assert safe.imagine(scenario.scene("intro"), "wstążkami") == vision


def test_safe_imaginer_drops_whole_idea_when_line_is_unsafe(scenario):
    safe = SafeImaginer(FakeImaginer(Vision("Narysuję potwora, który zabija!", "a monster")))

    assert safe.imagine(scenario.scene("intro"), "potwór") == Vision(reply="", idea="")

```

na:

```python

```

- [ ] **Step 2: Uruchom testy i sprawdź, że nowe padają**

Run: `python -m pytest tests/test_scenario.py tests/test_app.py tests/test_engine.py tests/test_safety.py -q`
Expected: FAIL — 6 przypadków `test_live_drawing_*_fields_are_rejected_with_a_clear_message` (`DID NOT RAISE`, bo parser dziś przyjmuje te pola) i `test_missing_video_files_exit_with_code_2` (w logu jest jeszcze stary komunikat). Testy Esc w `tests/test_engine.py` przechodzą.

- [ ] **Step 3: Usuń moduły, testy i scenariusze rysowania**

```bash
git rm -q bajka/imagine.py bajka/illustrate.py bajka/motion.py tests/test_imagine.py tests/test_illustrate.py tests/test_motion.py tests/test_engine_open.py tests/test_engine_generated.py tests/test_scenario_live.py tests/test_scenario_generated.py tests/test_app_live.py tests/live_fakes.py scenarios/rysowanie_na_zywo.yaml scenarios/pomiar_obrazow.yaml scenarios/karta_postaci.yaml
```

<!-- delete: bajka/imagine.py -->

<!-- delete: bajka/illustrate.py -->

<!-- delete: bajka/motion.py -->

<!-- delete: tests/test_imagine.py -->

<!-- delete: tests/test_illustrate.py -->

<!-- delete: tests/test_motion.py -->

<!-- delete: tests/test_engine_open.py -->

<!-- delete: tests/test_engine_generated.py -->

<!-- delete: tests/test_scenario_live.py -->

<!-- delete: tests/test_scenario_generated.py -->

<!-- delete: tests/test_app_live.py -->

<!-- delete: tests/live_fakes.py -->

<!-- delete: scenarios/rysowanie_na_zywo.yaml -->

<!-- delete: scenarios/pomiar_obrazow.yaml -->

<!-- delete: scenarios/karta_postaci.yaml -->

- [ ] **Step 4: Usuń rysowanie z kontraktów, scenariusza, silnika, aplikacji, filtra i zaślepek**

<!-- edit: bajka/ports.py -->
Zamień w `bajka/ports.py`:

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

na:

```python

```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
"""Scenariusz bajki: graf scen wczytywany z pliku YAML.

Rodzaje scen (`kind`):
- `clip` (domyślny): gotowy klip, opcjonalnie pytanie zamknięte z wyborami,
- `open`: gotowy klip z pytaniem otwartym; pomysł dziecka jest rysowany na żywo (bajka/imagine.py,
  bajka/illustrate.py, bajka/motion.py),
- `generated`: scena bez gotowego klipu, rysowana na żywo z zapamiętanych pomysłów dziecka, z narracją postaci.
"""

from __future__ import annotations

import string
from collections.abc import Mapping
```

na:

```python
"""Scenariusz bajki: graf scen wczytywany z pliku YAML."""

from __future__ import annotations

```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
KINDS = ("clip", "open", "generated")
LIVE_KINDS = ("open", "generated")  # sceny, które potrzebują generowania obrazów na żywo
```

na:

```python
# Rysowanie na żywo (sceny `open` i `generated`) usunięto z projektu. Parser pomija nieznane pola,
# więc stare pola dają wprost błąd, zamiast cicho zniknąć.
REMOVED_SCENE_FIELDS = (
    "kind", "drawing", "image_prompt", "remember", "default_idea", "fallback_clips", "next", "narration",
)
REMOVED_SCENARIO_FIELDS = ("style", "references")
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    clip: Path | None  # None tylko w scenach `generated`
```

na:

```python
    clip: Path
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    kind: str = "clip"
    drawing: Path | None = None  # pętla „postać rysuje” na czas generowania ilustracji
    image_prompt: str = ""  # szablon opisu ilustracji po angielsku: {idea} i zapamiętane pomysły
    remember: str = ""  # klucz, pod którym zapamiętujemy pomysł dziecka na resztę seansu
    default_idea: str = ""  # pomysł, gdy dziecko milczy albo pomysłu nie da się narysować
    fallback_clips: tuple[Path, ...] = ()  # gotowe klipy, gdy generowanie zawiedzie
    next: str = ""  # następna scena dla scen bez wyborów (open, generated)
    narration: str = ""  # kwestia postaci do sceny `generated`

    @property
    def is_ending(self) -> bool:
        return self.kind == "clip" and not self.choices

    @property
    def successors(self) -> tuple[str, ...]:
        if self.next:
            return (self.next,)
        return tuple(choice.next for choice in self.choices.values())
```

na:

```python

    @property
    def is_ending(self) -> bool:
        return not self.choices
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    style: str = ""  # opis stylu ilustracji po angielsku, dodawany do każdego obrazu
    references: tuple[Path, ...] = ()  # obrazy referencyjne postaci (karta postaci)

    def scene(self, scene_id: str) -> Scene:
        return self.scenes[scene_id]

    @property
    def needs_live_images(self) -> bool:
        return any(scene.kind in LIVE_KINDS for scene in self.scenes.values())
```

na:

```python

    def scene(self, scene_id: str) -> Scene:
        return self.scenes[scene_id]
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        raise ScenarioError("scenariusz: brak sekcji 'scenes'")
```

na:

```python
        raise ScenarioError("scenariusz: brak sekcji 'scenes'")
    _reject_removed(raw, REMOVED_SCENARIO_FIELDS, "scenariusz")
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
        style=str(raw.get("style") or "").strip(),
        references=_optional_paths(raw, "references", base_dir, "scenariusz"),
```

na:

```python
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    """Zwraca klipy, pętle i obrazy referencyjne, których nie ma na dysku."""
    paths: list[Path] = list(scenario.references)
    for scene in scenario.scenes.values():
        paths.extend(path for path in (scene.clip, scene.idle, scene.drawing) if path is not None)
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

na:

```python
    """Zwraca klipy i pętle oczekiwania, których nie ma na dysku."""
    paths: list[Path] = []
    for scene in scenario.scenes.values():
        paths.extend(path for path in (scene.clip, scene.idle) if path is not None)
        paths.extend(c.call_clip for c in scene.choices.values() if c.call_clip is not None)
    return [path for path in dict.fromkeys(paths) if not path.is_file()]
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    kind = data.get("kind", "clip")
    if kind not in KINDS:
        raise ScenarioError(f"{where}: nieznany rodzaj sceny {kind!r}, dostępne: {', '.join(KINDS)}")
    if kind == "open":
        return _parse_open(scene_id, data, base_dir, where)
    if kind == "generated":
        return _parse_generated(scene_id, data, base_dir, where)
```

na:

```python
    _reject_removed(data, REMOVED_SCENE_FIELDS, where)
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python

def _parse_open(scene_id: str, data: dict, base_dir: Path, where: str) -> Scene:
    image_prompt = _require_str(data, "image_prompt", where)
    try:
        fields = template_fields(image_prompt)
    except ValueError as exc:
        raise ScenarioError(f"{where}: niepoprawny szablon 'image_prompt': {exc}") from exc
    if "idea" not in fields:
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


```

na:

```python

```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
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

na:

```python
def _reject_removed(data: dict, removed: tuple[str, ...], where: str) -> None:
    found = [key for key in removed if key in data]
    if found:
        raise ScenarioError(
            f"{where}: pola {', '.join(found)} nie są już obsługiwane (rysowanie na żywo usunięto z projektu)"
        )
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        raise ScenarioError(f"scenariusz: scena startowa '{scenario.start}' nie istnieje")
    remembered = {scene.remember for scene in scenario.scenes.values() if scene.kind == "open"}
```

na:

```python
        raise ScenarioError(f"scenariusz: scena startowa '{scenario.start}' nie istnieje")
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        if scene.next and scene.next not in scenario.scenes:
            raise ScenarioError(f"scena '{scene.id}': następna scena '{scene.next}' (next) nie istnieje")
        allowed = remembered | ({"idea"} if scene.kind == "open" else set())
        _check_template(scene.image_prompt, allowed, f"scena '{scene.id}'")


def _check_template(template: str, allowed: set[str], where: str) -> None:
    """Literówka w szablonie ma wyjść przy wczytaniu scenariusza, a nie w trakcie seansu."""
    try:
        fields = template_fields(template)
        fill_prompt(template, dict.fromkeys(allowed, "x"))  # próbne wypełnienie łapie {} i złe formatowanie
    except (ValueError, IndexError, KeyError, AttributeError, TypeError) as exc:
        raise ScenarioError(f"{where}: niepoprawny szablon 'image_prompt': {exc}") from exc
    unknown = fields - allowed
    if unknown:
        raise ScenarioError(
            f"{where}: 'image_prompt' używa nieznanych pomysłów: {', '.join(sorted(unknown))}"
            " (dozwolone: {idea} i klucze 'remember' scen otwartych)"
        )

```

na:

```python

```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
"""Silnik bajki: odtwarza sceny, słucha dziecka (albo całej widowni) i wybiera kolejny klip.

Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo: Imaginer → Illustrator → Animator.
Sceny generowane (`kind: generated`) rysujemy w tle zawczasu: gdy pada pytanie, które może do nich prowadzić.
"""
```

na:

```python
"""Silnik bajki: odtwarza sceny, słucha dziecka (albo całej widowni) i wybiera kolejny klip."""
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
import random
import threading
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from bajka.ports import (
    Animator,
    Audience,
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
```

na:

```python
import threading
from collections import Counter
from pathlib import Path

from bajka.ports import Audience, IntentResolver, Interpretation, Listener, Player, ShoutMeter, Voice
from bajka.scenario import Choice, Scenario, Scene
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"
FALLBACK_VISION_LINE = "Zobacz, co mam w wyobraźni!"
```

na:

```python
DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        imaginer: Imaginer | None = None,
        illustrator: Illustrator | None = None,
        animator: Animator | None = None,
        image_timeout_s: float = 25.0,
        generated_seconds: float = 0.0,
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
        self._generated_seconds = generated_seconds  # tyle najmniej zostaje na ekranie obraz sceny generowanej
        self._rng = rng or random.Random()
        self._stopped = threading.Event()
        # Scena generowana może paść przed pytaniem otwartym (inna gałąź): domyślny pomysł jest od początku.
        self._memory: dict[str, str] = {
            scene.remember: scene.default_idea for scene in scenario.scenes.values() if scene.kind == "open"
        }
        self._prefetched: dict[str, tuple[Future[Path], float]] = {}  # scena → (rysowanie, termin)
```

na:

```python
    ) -> None:
        self._stopped = threading.Event()
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        self._audience = audience  # telefony widzów; gdy żaden nie jest połączony, słuchamy sali

    @property
    def memory(self) -> Mapping[str, str]:
        """Pomysły dziecka z tego seansu (klucz `remember` → opis po angielsku), do pytania: `default_idea`."""
        return dict(self._memory)
```

na:

```python
        self._audience = audience  # telefony widzów; gdy żaden nie jest połączony, słuchamy sali
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        scene = self._scenario.scene(self._scenario.start)
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rysowanie")
```

na:

```python
        scene = self._scenario.scene(self._scenario.start)
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                log.info("Scena: %s", scene.id)
                if scene.kind == "generated":
                    self._show_generated(scene)
                    scene = self._scenario.scene(scene.next)
                    continue
                self._prefetch(scene.successors if scene.choices else ())
```

na:

```python
                log.info("Scena: %s", scene.id)
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                if scene.kind == "open":
                    self._ask_open(scene)  # pomysł z mikrofonu na sali, także gdy działają telefony
                    scene = self._scenario.scene(scene.next)
                    continue
                choice = self._decide(scene)
                self._drop_prefetched(other for other in scene.successors if other != choice.next)
                scene = self._scenario.scene(choice.next)
        except _Stopped:
            log.info("Bajka zatrzymana")
            return visited
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)  # nie czekamy na spóźnione obrazy
```

na:

```python
                scene = self._scenario.scene(self._decide(scene).next)
        except _Stopped:
            log.info("Bajka zatrzymana")
            return visited
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python

    def _ask_open(self, scene: Scene) -> None:
        vision = self._hear_idea(scene)
        if vision is None:
            self._memory[scene.remember] = scene.default_idea
            self._prefetch((scene.next,))
            self._say(FALLBACK_VISION_LINE)
            self._play(self._fallback_clip(scene))
            return
        self._memory[scene.remember] = vision.idea
        prompt = fill_prompt(scene.image_prompt, {**self._memory, "idea": vision.idea})
        deadline = time.monotonic() + self._image_timeout_s
        future = self._pool.submit(self._render, prompt)
        self._prefetch((scene.next,))  # dopiero po rysunku dziecka: jego pomysł ma pierwszeństwo w kolejce
        if vision.reply:
            self._say(vision.reply)  # postać mówi, a obraz w tym czasie się rysuje
        self._play(self._clip_or_fallback(scene, future, deadline))

    def _hear_idea(self, scene: Scene) -> Vision | None:
        """Pomysł dziecka albo None: cisza po wszystkich dopytaniach, błąd LLM, pomysł nie do narysowania."""
        for attempt in range(self._max_reprompts + 1):
            transcript = self._listen()
            if transcript:
                if scene.drawing is not None:
                    self._loop(scene.drawing)  # od razu: odpowiedź modelu potrwa, a ekran nie może stać pusty
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

    def _show_generated(self, scene: Scene) -> None:
        self._prefetch((scene.id,))  # nic nie robi, jeśli scena już się rysuje
        future, deadline = self._prefetched.pop(scene.id)
        self._prefetch((scene.next,))
        clip = self._clip_or_fallback(scene, future, deadline, announce=False)
        self._loop(clip)
        shown_at = time.monotonic()
        self._say(scene.narration)  # postać mówi na tle zapętlonej ilustracji
        remaining = self._generated_seconds - (time.monotonic() - shown_at)
        if remaining > 0:  # krótka narracja albo brak głosu (--text): obraz i tak ma chwilę pobyć
            self._check_stopped()
            self._stopped.wait(remaining)  # Esc przerywa czekanie

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
            entry = self._prefetched.pop(scene_id, None)
            if entry is not None:
                entry[0].cancel()  # niewybrana gałąź: jeśli jeszcze czeka w kolejce, nie rysujemy jej wcale

    def _render(self, prompt: str) -> Path:
        started = time.monotonic()
        clip = self._animator.animate(self._illustrator.draw(prompt))
        log.info("Narysowane w %.1f s: %s", time.monotonic() - started, clip.name)
        return clip

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

    def _fallback_clip(self, scene: Scene) -> Path:
        return self._rng.choice(scene.fallback_clips)

```

na:

```python

```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
import shutil
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
```

na:

```python
import threading
from collections.abc import Mapping
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
from bajka.ports import Animator, Illustrator, Imaginer, IntentResolver, Listener, ShoutMeter, Voice
from bajka.safety import SafeImaginer, SafeReplyResolver
from bajka.scenario import Scenario, ScenarioError, load_scenario, missing_media
```

na:

```python
from bajka.ports import IntentResolver, Listener, ShoutMeter, Voice
from bajka.safety import SafeReplyResolver
from bajka.scenario import ScenarioError, load_scenario, missing_media
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python

@dataclass(frozen=True)
class LiveImages:
    """Moduły rysowania na żywo; puste, gdy scenariusz nie ma scen rysowanych na żywo."""

    imaginer: Imaginer | None = None
    illustrator: Illustrator | None = None
    animator: Animator | None = None
    timeout_s: float = 25.0
    motion_seconds: float = 6.0  # tyle trwa klip z ilustracji, więc tyle co najmniej pokazujemy scenę generowaną


def prepare_session_dir(base: Path | None = None) -> Path:
    """Nowy katalog na ilustracje seansu. Ilustracje poprzednich seansów usuwamy (prywatność dzieci)."""
    base = base or Path(tempfile.gettempdir()) / "bajka"
    base.mkdir(parents=True, exist_ok=True)
    for previous in list(base.glob("seans_*")):
        # Usuwamy wszystko, co się da, nawet gdy jeden plik jest zablokowany (np. otwarty w VLC), i zostawiamy ślad.
        shutil.rmtree(previous, ignore_errors=True)
        if previous.exists():
            log.warning("Nie udało się usunąć wszystkich ilustracji poprzedniego seansu %s", previous)
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
        imaginer=SafeImaginer(AzureImaginer.from_settings(imagine, scenario.hero)),  # filtr regulaminu §3 ust. 8
        illustrator=AzureIllustrator.from_settings(images, directory, scenario.style, scenario.references),
        animator=FfmpegAnimator.from_settings(motion, directory),
        timeout_s=float(images.timeout_s),
        motion_seconds=motion.seconds,
    )

```

na:

```python

```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        log.error("Brak plików (klipy wideo, obrazy referencyjne): %s", ", ".join(map(str, missing)))
```

na:

```python
        log.error("Brak plików wideo: %s", ", ".join(map(str, missing)))
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        log.info("Tryb: %s%s", backend, ", bez modelu językowego" if args.no_llm else "")
        live = build_live_images(env, scenario)  # szybkie sprawdzenie kluczy i ffmpeg przed ładowaniem modeli
```

na:

```python
        log.info("Tryb: %s%s", backend, ", bez modelu językowego" if args.no_llm else "")
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        audience=audience,
        imaginer=live.imaginer,
        illustrator=live.illustrator,
        animator=live.animator,
        image_timeout_s=live.timeout_s,
        generated_seconds=live.motion_seconds,
```

na:

```python
        audience=audience,
```

<!-- edit: bajka/safety.py -->
Zamień w `bajka/safety.py`:

```python
from bajka.ports import Imaginer, IntentResolver, Interpretation, Vision
```

na:

```python
from bajka.ports import IntentResolver, Interpretation
```

<!-- edit: bajka/safety.py -->
Zamień w `bajka/safety.py`:

```python

class SafeImaginer:
    """Opakowuje dowolny `Imaginer`. Podejrzana kwestia unieważnia cały pomysł: silnik pokaże wtedy
    klip zapasowy ze scenariusza i powie stałą, sprawdzoną kwestię."""

    def __init__(self, inner: Imaginer) -> None:
        self._inner = inner

    def imagine(self, scene: Scene, transcript: str) -> Vision:
        vision = self._inner.imagine(scene, transcript)
        if vision.reply and not is_safe_reply(vision.reply):
            log.warning("Kwestia wyobraźni odrzucona przez filtr, pokazuję klip zapasowy")
            return Vision(reply="", idea="")
        return vision

```

na:

```python

```

<!-- edit: bajka/placeholders.py -->
Zamień w `bajka/placeholders.py`:

```python
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen i zapasy scen otwartych mają ton; pętle (oczekiwanie,
    rysowanie) i zapasy scen generowanych są ciche, bo grają w pętli pod narracją postaci."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        tracks = [(scene.clip, True), (scene.idle, False), (scene.drawing, False)]
        tracks += [(path, scene.kind != "generated") for path in scene.fallback_clips]
        for path, with_tone in tracks:
            if path is not None and path not in clips:  # wspólna pętla rysowania tylko raz
```

na:

```python
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen mają ton, a pętle oczekiwania są ciche."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        for path, with_tone in ((scene.clip, True), (scene.idle, False)):
            if path is not None and path not in clips:  # ten sam plik w kilku scenach tylko raz
```

- [ ] **Step 5: Uruchom testy**

Run: `python -m pytest tests/test_scenario.py tests/test_app.py tests/test_engine.py tests/test_safety.py tests/test_placeholders.py tests/test_vote.py -q`
Expected: PASS.

- [ ] **Step 6: Dokumenty i konfiguracja bez rysowania na żywo**

<!-- edit: README.md -->
Zamień w `README.md`:

```markdown
Usługi Azure zostają jako alternatywa (`--backend azure`).

**Wyjątek: sceny rysowane na żywo** (`kind: open` i `kind: generated`, np. [`scenarios/rysowanie_na_zywo.yaml`](scenarios/rysowanie_na_zywo.yaml))
potrzebują Azure, kluczy w `.env` i ffmpeg. Rozpoznany lokalnie tekst odpowiedzi dziecka trafia do Azure OpenAI,
a obraz rysuje Azure AI Foundry (nagranie głosu nigdy nie opuszcza komputera). Flaga `--no-llm` nie wyłącza tego
kroku wyobraźni, wyłącza tylko model językowy przy wyborze ścieżki. Bez internetu te sceny pokazują klipy zapasowe.
```

na:

```markdown
Usługi Azure zostają jako alternatywa (`--backend azure`).
```

<!-- edit: README.md -->
Zamień w `README.md`:

````markdown
python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "złota korona"   # pomysł → kwestia + opis obrazu
python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml "a fox"     # opis → ilustracja (Azure AI Foundry)
python -m bajka.motion obraz.png                                         # ilustracja → klip z ruchem kamery
```

Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo; mechanikę pokazuje
[`scenarios/rysowanie_na_zywo.yaml`](scenarios/rysowanie_na_zywo.yaml), a zasady i dobór modeli
[projekt flow filmu](docs/superpowers/specs/2026-10-16-flow-filmu-design.md).
````

na:

````markdown
```
````

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
komputerze z Windows, bez chmury i bez nagrywania widzów. Wyjątek: sceny rysowane na żywo potrzebują Azure, internetu
i ffmpeg (patrz niżej).
```

na:

```markdown
komputerze z Windows, bez chmury i bez nagrywania widzów.
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
3. **Wymienne moduły.** Odtwarzacz, rozpoznawanie mowy, rozumienie odpowiedzi, głos postaci i rysowanie obrazów
```

na:

```markdown
3. **Wymienne moduły.** Odtwarzacz, rozpoznawanie mowy, rozumienie odpowiedzi i głos postaci
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

````markdown

## Pytania otwarte i obrazy na żywo (opcjonalnie)

Scena może też zadać **pytanie otwarte** („Jak to wygląda?”). Wtedy pomysł widza zamienia się w ilustrację:

```
wypowiedź ──▶ model językowy: kwestia postaci + bezpieczny opis obrazu ──▶ model obrazu ──▶ ruch kamery (ffmpeg) ──▶ nowy klip
```

W czasie rysowania leci pętla „postać rysuje”, a postać mówi swoją kwestię. Pomysł zostaje zapamiętany
i może wrócić w kolejnych scenach. Gdy rysowanie potrwa zbyt długo albo się nie uda, program pokazuje gotowy klip
zapasowy. Ta część korzysta z chmury (Azure OpenAI pisze kwestię i opis, Azure AI Foundry rysuje); do chmury
trafia tylko tekst, nigdy nagranie.

````

na:

```markdown

```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| `local` (domyślny) | Rozpoznawanie mowy, model językowy i głos postaci na komputerze; bez kluczy i internetu po pierwszym pobraniu modeli (wyjątek: sceny rysowane na żywo — klucze Azure, internet i ffmpeg) | `python -m bajka SCENARIUSZ` |
| `azure` | To samo przez usługi Azure | `--backend azure` |
| `--mobile` | Odpowiedzi z telefonów widzów | `python -m bajka SCENARIUSZ --mobile` |
| `--no-llm` | Bez modelu językowego przy wyborze ścieżki, tylko słowa kluczowe (sceny rysowane na żywo dalej korzystają z Azure) | na słabszym komputerze i do prób |
```

na:

```markdown
| `local` (domyślny) | Rozpoznawanie mowy, model językowy i głos postaci na komputerze; bez kluczy i internetu po pierwszym pobraniu modeli | `python -m bajka SCENARIUSZ` |
| `azure` | To samo przez usługi Azure | `--backend azure` |
| `--mobile` | Odpowiedzi z telefonów widzów | `python -m bajka SCENARIUSZ --mobile` |
| `--no-llm` | Bez modelu językowego, tylko słowa kluczowe | na słabszym komputerze i do prób |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| Interfejsy | `bajka/ports.py` — `Player`, `Listener`, `Voice`, `IntentResolver`, `Audience`, `ShoutMeter`, `Imaginer`, `Illustrator`, `Animator` |
```

na:

```markdown
| Interfejsy | `bajka/ports.py` — `Player`, `Listener`, `Voice`, `IntentResolver`, `Audience`, `ShoutMeter` |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| Głos postaci | `bajka/local_tts.py` (Windows), `bajka/tts.py` (Azure) |
| Obrazy na żywo | `bajka/imagine.py`, `bajka/illustrate.py`, `bajka/motion.py` |
```

na:

```markdown
| Głos postaci | `bajka/local_tts.py` (Windows), `bajka/tts.py` (Azure) |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
- **Lokalnie, jeśli się da.** Prywatność widzów i działanie bez internetu w kinie; chmura tylko tam, gdzie lokalnie
  się nie da (obrazy na żywo) albo jako alternatywa.
```

na:

```markdown
- **Lokalnie, jeśli się da.** Prywatność widzów i działanie bez internetu w kinie; chmura tylko jako alternatywa.
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
- **Prywatność.** Nagrania są przetwarzane w pamięci i nie są zapisywane; obrazy z seansu trafiają do katalogu
  tymczasowego, czyszczonego przy następnym starcie.
```

na:

```markdown
- **Prywatność.** Nagrania są przetwarzane w pamięci i nie są zapisywane.
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| **Scena `vote`** | Scena decyzji, którą bez telefonów rozstrzyga krzykomierz |
| **Scena `open`** | Pytanie otwarte; pomysł widza jest rysowany na żywo |
| **Klip zapasowy** | Gotowy klip na wypadek, gdy obraz na żywo się nie uda |
```

na:

```markdown
| **Scena `vote`** | Scena decyzji, którą bez telefonów rozstrzyga krzykomierz |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Obrazy na żywo i dobór modeli |
```

na:

```markdown
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Produkcja klipów i dobór modeli (rysowanie na żywo wycofane) |
```

<!-- edit: docs/PODZIAL_PRACY.md -->
Zamień w `docs/PODZIAL_PRACY.md`:

```markdown
**Osoba C — „obraz na żywo”**: ilustracje rysowane z pomysłów dziecka ([projekt](superpowers/specs/2026-10-16-flow-filmu-design.md), [plan](superpowers/plans/2026-10-16-obraz-na-zywo.md)).
```

na:

```markdown
**Osoba C — „film czuje salę”**: tętno widowni, wersje scen i panel dla jury ([projekt](superpowers/specs/2026-10-16-film-czuje-sale-design.md)).
```

<!-- edit: docs/PODZIAL_PRACY.md -->
Zamień w `docs/PODZIAL_PRACY.md`:

```markdown
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |
| [`bajka/imagine.py`](../bajka/imagine.py) — pomysł dziecka → kwestia postaci + opis obrazu | `Imaginer` | C | `python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "złota korona"` | `tests/test_imagine.py` |
| [`bajka/illustrate.py`](../bajka/illustrate.py) — opis → ilustracja (Azure AI Foundry) | `Illustrator` | C | `python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml "a fox"` | `tests/test_illustrate.py` |
| [`bajka/motion.py`](../bajka/motion.py) — ilustracja → klip z ruchem kamery (ffmpeg) | `Animator` | C | `python -m bajka.motion obraz.png` | `tests/test_motion.py` |
```

na:

```markdown
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
| §6 | Ochrona danych (RODO) | **OK** / **ZESPÓŁ** | Aplikacja nie zapisuje głosu ani wypowiedzi; lokalne AI przetwarza mowę na komputerze, bez wysyłania nagrań do chmury. Wyjątek: w scenach rysowanych na żywo (`kind: open`) rozpoznany tekst odpowiedzi dziecka trafia do Azure OpenAI, a obraz rysuje Azure AI Foundry (nagranie głosu nigdy); informacja dla opiekunów powinna o tym wspomnieć. Głos dzieci z telefonów — szczegóły niżej |
```

na:

```markdown
| §6 | Ochrona danych (RODO) | **OK** / **ZESPÓŁ** | Aplikacja nie zapisuje głosu ani wypowiedzi; lokalne AI przetwarza mowę na komputerze, bez wysyłania nagrań do chmury. Głos dzieci z telefonów — szczegóły niżej |
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
   odpowie jedna osoba; przy wielu Lila mówi teksty ze scenariusza.
4. **Ilustracje rysowane na żywo** (sceny `kind: open`, moduły Ksawerego): pomysł dziecka najpierw przepisuje
   model językowy na bezpieczny opis (`bajka/imagine.py`, te same zasady prawdy i kultury), podejrzana kwestia
   unieważnia cały pomysł (`SafeImaginer`), a model obrazu ma własny filtr treści (gpt-image; przy FLUX —
   Azure AI Content Safety). Przy każdym błędzie albo odrzuceniu pokazujemy przygotowany klip zapasowy.
   Ilustracje poprzednich seansów aplikacja usuwa przy starcie. **OK** w kodzie; **ZESPÓŁ**: filtr treści przy FLUX.
```

na:

```markdown
   odpowie jedna osoba; przy wielu Lila mówi teksty ze scenariusza.
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
| ffmpeg | LGPL/GPL (zależnie od kompilacji) | Narzędzie do zaślepek i ruchu kamery; nie jest częścią filmu |
```

na:

```markdown
| ffmpeg | LGPL/GPL (zależnie od kompilacji) | Narzędzie do zaślepek; nie jest częścią filmu |
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
| **Innowacyjność** | Bohaterka filmu słucha widowni i odpowiada na żywo: każdy widz mówi do własnego telefonu, a komputer w kinie liczy głosy całej sali. Rozpoznawanie mowy, wybór ścieżki i głos działają lokalnie (Copilot+ PC z NPU, Foundry Local), bez nagrywania dzieci; w chmurze Azure powstają tylko ilustracje scen rysowanych na żywo oraz, w scenach otwartych, kwestia bohaterki i pomysł na obraz (Azure OpenAI) — wszystko z samego tekstu, bez nagrania. Bez telefonów decyzje rozstrzyga krzykomierz |
```

na:

```markdown
| **Innowacyjność** | Bohaterka filmu słucha widowni i odpowiada na żywo: każdy widz mówi do własnego telefonu, a komputer w kinie liczy głosy całej sali. Rozpoznawanie mowy, wybór ścieżki i głos działają lokalnie (Copilot+ PC z NPU, Foundry Local), bez nagrywania dzieci. Bez telefonów decyzje rozstrzyga krzykomierz |
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
komputerze (z wyjątkiem scen rysowanych na żywo, które potrzebują Azure i internetu).
```

na:

```markdown
komputerze.
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
- [ ] Na nagraniach z pokazu nie ma dzieci bez zgody opiekunów.
- [x] Ilustracje z poprzednich seansów usuwane przy starcie aplikacji (zadanie 6 planu „obraz na żywo”).
```

na:

```markdown
- [ ] Na nagraniach z pokazu nie ma dzieci bez zgody opiekunów.
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
Stan na 16.10.2026 (322 testy przechodzą). Nowa osoba w zespole? Zacznij od [ONBOARDING.md](ONBOARDING.md). Prezentacja przed jury: **18.10.2026, 19:00**.
```

na:

```markdown
Stan na 16.10.2026 (226 testów przechodzi). Nowa osoba w zespole? Zacznij od [ONBOARDING.md](ONBOARDING.md). Prezentacja przed jury: **18.10.2026, 19:00**.
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
- [x] **Zadanie 6 [planu „obraz na żywo”](superpowers/plans/2026-10-16-obraz-na-zywo.md)** (Ksawery): moduły
  rysowania podpięte w `bajka/app.py` razem z aplikacją mobilną, zaślepki pętli „rysuje” i klipów zapasowych,
  wpisy w `.env.example` i README.
- [x] **Zadanie 7 planu „obraz na żywo”** (Ksawery): sceny generowane (`kind: generated`) rysowane w tle z pamięcią
  pomysłów dziecka (`remember`, `default_idea` od początku seansu); po przeglądzie: Esc zatrzymuje bajkę od razu,
  wyobraźnia ma krótki limit czasu (6 s), a obraz sceny generowanej zostaje na ekranie tyle, ile trwa klip.
- [ ] **Decyzja: czy scena ozdabiania ula (`kind: open`) wchodzi do filmu.** Sceny otwarte słuchają dziś tylko
  mikrofonu przy ekranie, nie telefonów; w kinie trzeba by dodać na telefonach wybór spośród trzech pomysłów
  (propozycja w [scenariuszu](../scenarios/klub_ciekawskich.md), SC. 7b).
- [x] `.gitignore` obejmuje `/ilustracje/`, `/pomiar/` i `scenarios/ilustracje/kandydaci/`, żeby wygenerowane obrazy
  (z nieznanymi jeszcze prawami) nie trafiły przypadkiem do repozytorium. Wybrane obrazy referencyjne trzeba skopiować
  do `scenarios/ilustracje/` i dodać do repozytorium.
```

na:

```markdown
- [x] Rysowanie na żywo usunięte z projektu (16.10): wszystkie animacje filmu są przygotowane wcześniej.
  W zamian [film, który czuje salę](superpowers/specs/2026-10-16-film-czuje-sale-design.md): tętno widowni,
  wersje scen i panel dla jury.
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
- [ ] Azure AI Foundry: dostęp, klucze w `.env`, pomiar czasu ilustracji i wybór modelu obrazu (gpt-image-1.5 albo FLUX.2).
- [ ] Próba generalna całego filmu obiema ścieżkami: z telefonami (`--mobile`) i bez.
- [ ] Próba generalna na laptopie pokazowym: prawdziwy Azure, VLC, TTS, pomiar z references, czas bajka.motion,
  Esc w trakcie rysowania, limit 5 obrazów/min.
```

na:

```markdown
- [ ] Próba generalna całego filmu obiema ścieżkami: z telefonami (`--mobile`) i bez.
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
- [ ] Informacja dla opiekunów o mikrofonie i prywatności; na nagraniach z pokazu bez dzieci bez zgody opiekunów.
- [x] Ilustracje z poprzednich seansów usuwane przy starcie aplikacji (katalog tymczasowy, zadanie 6).
```

na:

```markdown
- [ ] Informacja dla opiekunów o mikrofonie i prywatności; na nagraniach z pokazu bez dzieci bez zgody opiekunów.
```

<!-- edit: docs/LOKALNE_AI.md -->
Zamień w `docs/LOKALNE_AI.md`:

```markdown
dziecka nie opuszczają komputera. Tryb `azure` (usługi chmurowe) zostaje jako alternatywa.

Wyjątek: sceny rysowane na żywo (`kind: open`, [projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md))
korzystają z Azure AI Foundry — pomysł dziecka opisuje Azure OpenAI, a ilustrację rysuje model obrazu w chmurze.
Do modelu obrazu trafia tylko opis pomysłu przepisany przez model językowy, nigdy nagranie. Bez internetu
w trakcie seansu te sceny pokazują klipy zapasowe, a reszta bajki działa lokalnie.
```

na:

```markdown
dziecka nie opuszczają komputera. Tryb `azure` (usługi chmurowe) zostaje jako alternatywa.
```

<!-- edit: scenarios/klub_ciekawskich.md -->
Zamień w `scenarios/klub_ciekawskich.md`:

```markdown
| **Obraz** | 16:9, 1920×1080, 24 kl./s (kotwice); sceny generowane na żywo 1280×720, skalowane |
```

na:

```markdown
| **Obraz** | 16:9, 1920×1080, 24 kl./s |
```

<!-- edit: scenarios/klub_ciekawskich.md -->
Zamień w `scenarios/klub_ciekawskich.md`:

```markdown
### SC. 7b (planowana) — PLENER. UL — POPOŁUDNIE (`ozdoby`, obraz na żywo)

Scena z [projektu flow filmu](../docs/superpowers/specs/2026-10-16-flow-filmu-design.md) (obszar C, scena `open`):
Lila pyta, jak udekorujemy ul, a ilustracja powstaje na żywo z pomysłu widowni. Silnik i aplikacja obsługują już
sceny `kind: open` ([plan „obraz na żywo”](../docs/superpowers/plans/2026-10-16-obraz-na-zywo.md)); do YAML (między
SC. 6 a SC. 7) scena wejdzie po decyzji zespołu i z klipami: `07b_ozdoby.mp4`, cicha pętla oczekiwania, pętla
„Lila rysuje” i 1–3 klipy zapasowe. Wymaga kluczy Azure
(pomysł i ilustracja powstają w chmurze); bez internetu w trakcie seansu lecą klipy zapasowe.

**W kinie** pytanie otwarte do całej sali będzie nieczytelne, a scena otwarta słucha dziś tylko mikrofonu przy
ekranie, nie telefonów. Proponujemy: na telefonach wybór spośród trzech pomysłów (Kwiatki, Wstążki, Gwiazdki),
a zwycięski pomysł trafia do promptu ilustracji. Pytanie w pełni otwarte zostawiamy dla trybu jednego widza
(kiosk, jury).
```

na:

```markdown
### SC. 7b (wycofana) — PLENER. UL — POPOŁUDNIE (`ozdoby`)

Scena z ilustracją rysowaną na żywo z pomysłu widowni została wycofana razem z rysowaniem na żywo (16.10).
Wszystkie animacje filmu są przygotowane wcześniej; w zamian film dopasowuje wersje scen do tętna sali
([projekt](../docs/superpowers/specs/2026-10-16-film-czuje-sale-design.md)).
```

<!-- edit: .gitignore -->
Zamień w `.gitignore`:

```text
scenarios/clips/
# Obrazy z AI, których praw jeszcze nie sprawdzono, nie trafiają do repozytorium przypadkiem.
# Wybrane obrazy referencyjne kopiujemy ręcznie do scenarios/ilustracje/ (ten katalog jest w repozytorium).
/ilustracje/
/pomiar/
scenarios/ilustracje/kandydaci/
```

na:

```text
scenarios/clips/
```

<!-- edit: .env.example -->
Zamień w `.env.example`:

```text

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

na:

```text

```

- [ ] **Step 7: Pełny zestaw testów i sprawdzenie, że nic nie odwołuje się do usuniętych modułów**

Run: `python -m pytest -q`
Expected: `226 passed, 1 skipped` (pominięty test kolegi wymaga `cryptography`; jego `tests/test_mobile.py::test_server_rejects_bad_requests` bywa niestabilny — przy jedynej porażce powtórz).

Run: `git grep -n -E "imagine|illustrate|bajka\.motion|Vision|needs_live_images|fallback_clips|kind: open" -- bajka tests scenarios README.md docs/ONBOARDING.md docs/PODZIAL_PRACY.md docs/LOKALNE_AI.md .env.example`
Expected: tylko `bajka/scenario.py` (krotka `REMOVED_SCENE_FIELDS`) i `tests/test_scenario.py` (testy błędów).

<!-- checkpoint -->

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: rysowanie na żywo usunięte z projektu; animacje filmu są przygotowane wcześniej"
```

---

### Task 2: Tętno sali z symulatora

**Files:**
- Create: `bajka/pulse.py`, `tests/test_pulse.py`
- Modify: `bajka/ports.py`, `.env.example`, `docs/PODZIAL_PRACY.md`, `README.md`

**Interfaces:**
- Consumes: `bajka.config.ConfigError`, `get_float`, `get_int`, `load_env`.
- Produces:
  - w `bajka/ports.py`: `Pulse(bpm: float, viewers: int)` i `AudiencePulse` z `read() -> Pulse`,
  - w `bajka/pulse.py`: stałe `EXCITED = "pobudzona"`, `NORMAL = "w normie"`, `BORED = "znudzona"`, `PRESETS`, `DEMO_SCRIPT`, `MIN_BPM`, `MAX_BPM`; `PulseSettings(viewers=30, start_bpm=90.0, excited=1.15, bored=0.97)` z `from_env`; `hall_state(bpm, baseline, settings) -> str`; `script_value(script, seconds) -> float`; `SimulatedPulse(settings, clock=time.monotonic, rng=None)` z `target`, `set_target(bpm)`, `preset(name)`, `play_script(script=DEMO_SCRIPT)`, `read() -> Pulse`.

- [ ] **Step 1: Testy symulatora i stanu sali**

<!-- file: tests/test_pulse.py -->
Utwórz `tests/test_pulse.py`:

```python
import math
import random

import pytest

from bajka.config import ConfigError
from bajka.ports import AudiencePulse, Pulse
from bajka.pulse import (
    BORED,
    DEMO_SCRIPT,
    EXCITED,
    NORMAL,
    PRESETS,
    PulseSettings,
    SimulatedPulse,
    hall_state,
    script_value,
)


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class NoJitter:
    def uniform(self, low, high):
        return 0.0


def make_pulse(**settings):
    clock = FakeClock()
    return SimulatedPulse(PulseSettings(**settings), clock=clock, rng=NoJitter()), clock


def test_simulated_pulse_fulfils_contract_and_starts_at_start_bpm():
    pulse, _ = make_pulse(start_bpm=88.0, viewers=12)

    assert isinstance(pulse, AudiencePulse)
    assert pulse.read() == Pulse(bpm=88.0, viewers=12)


def test_pulse_approaches_target_smoothly():
    pulse, clock = make_pulse(start_bpm=90.0)
    pulse.set_target(120.0)

    clock.now += 5.0  # jedna stała czasowa: ok. 63% drogi
    assert pulse.read().bpm == pytest.approx(90.0 + 30.0 * (1 - math.exp(-1)), abs=0.05)

    clock.now += 60.0
    assert pulse.read().bpm == pytest.approx(120.0, abs=0.05)


def test_target_is_kept_within_human_range():
    pulse, _ = make_pulse()

    pulse.set_target(500)
    assert pulse.target == 160.0
    pulse.set_target(10)
    assert pulse.target == 60.0


def test_presets_set_the_target():
    pulse, _ = make_pulse()

    pulse.preset("ekscytuje-sie")

    assert pulse.target == PRESETS["ekscytuje-sie"] == 115.0


def test_unknown_preset_is_refused():
    pulse, _ = make_pulse()

    with pytest.raises(ValueError, match="nieznany stan sali"):
        pulse.preset("szaleje")


def test_script_moves_the_target_over_time_until_set_by_hand():
    pulse, clock = make_pulse()
    pulse.play_script(((0, 90.0), (10, 110.0)))

    clock.now += 5.0
    pulse.read()
    assert pulse.target == pytest.approx(100.0)

    pulse.set_target(95.0)  # ręczne ustawienie przerywa przebieg
    clock.now += 20.0
    pulse.read()
    assert pulse.target == 95.0


def test_script_value_interpolates_and_holds_the_ends():
    script = ((0, 90.0), (10, 110.0), (20, 100.0))

    assert script_value(script, -5) == 90.0
    assert script_value(script, 5) == pytest.approx(100.0)
    assert script_value(script, 15) == pytest.approx(105.0)
    assert script_value(script, 99) == 100.0


def test_demo_script_goes_calm_excited_calm():
    values = [bpm for _, bpm in DEMO_SCRIPT]

    assert values[0] < max(values) and values[-1] < max(values)


def test_jitter_stays_small():
    pulse = SimulatedPulse(PulseSettings(start_bpm=90.0), clock=FakeClock(), rng=random.Random(7))

    readings = [pulse.read().bpm for _ in range(50)]

    assert all(88.5 <= bpm <= 91.5 for bpm in readings)
    assert len(set(readings)) > 1


@pytest.mark.parametrize(
    ("bpm", "state"),
    [(115.0, EXCITED), (114.9, NORMAL), (100.0, NORMAL), (97.1, NORMAL), (97.0, BORED), (80.0, BORED)],
)
def test_hall_state_compares_pulse_with_baseline(bpm, state):
    assert hall_state(bpm, baseline=100.0, settings=PulseSettings()) == state


def test_settings_from_env_defaults_and_overrides():
    assert PulseSettings.from_env({}) == PulseSettings(viewers=30, start_bpm=90.0, excited=1.15, bored=0.97)

    env = {"BAJKA_PULSE_VIEWERS": "50", "BAJKA_PULSE_START_BPM": "85", "BAJKA_PULSE_EXCITED": "1.2",
           "BAJKA_PULSE_BORED": "0.9"}  # fmt: skip
    assert PulseSettings.from_env(env) == PulseSettings(viewers=50, start_bpm=85.0, excited=1.2, bored=0.9)


@pytest.mark.parametrize(("excited", "bored"), [("0.9", "0.97"), ("1.15", "1.05")])
def test_thresholds_must_lie_on_both_sides_of_baseline(excited, bored):
    with pytest.raises(ConfigError, match="BAJKA_PULSE_EXCITED"):
        PulseSettings.from_env({"BAJKA_PULSE_EXCITED": excited, "BAJKA_PULSE_BORED": bored})
```

- [ ] **Step 2: Uruchom testy i sprawdź, że padają**

Run: `python -m pytest tests/test_pulse.py -q`
Expected: FAIL — błąd importu (`AudiencePulse` w `bajka.ports` i moduł `bajka.pulse` jeszcze nie istnieją).

- [ ] **Step 3: Kontrakt i moduł tętna**

<!-- edit: bajka/ports.py -->
Zamień w `bajka/ports.py`:

```python
        """


```

na:

```python
        """


@dataclass(frozen=True)
class Pulse:
    bpm: float  # średnie tętno sali
    viewers: int  # od ilu widzów pochodzi średnia (w demo: symulowanych)


@runtime_checkable
class AudiencePulse(Protocol):
    """Tętno sali: średnia z zegarków widzów (na pokazie z symulatora, bajka/pulse.py)."""

    def read(self) -> Pulse:
        """Bieżące średnie tętno sali."""

```

<!-- file: bajka/pulse.py -->
Utwórz `bajka/pulse.py`:

```python
"""Tętno sali. Na pokazie pochodzi z symulatora sterowanego z panelu: bez zegarków i bez danych prawdziwych osób.

Wizja: aplikacja mobilna czyta tętno z zegarków widzów i wysyła do komputera z filmem tylko średnią całej sali.
Moduł spełnia kontrakt `bajka.ports.AudiencePulse`; `hall_state` porównuje tętno z punktem odniesienia.
Podgląd symulatora bez reszty aplikacji: python -m bajka.pulse [--script] [--seconds 30]
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from bajka.config import ConfigError, get_float, get_int, load_env
from bajka.ports import Pulse

EXCITED = "pobudzona"
NORMAL = "w normie"
BORED = "znudzona"

MIN_BPM, MAX_BPM = 60.0, 160.0
PRESETS = {"spokojna": 90.0, "ekscytuje-sie": 115.0, "nudzi-sie": 85.0}
# Przebieg demo: (sekunda od startu, tętno) — spokojny początek, ekscytacja, uspokojenie.
DEMO_SCRIPT: tuple[tuple[float, float], ...] = ((0, 90.0), (20, 90.0), (35, 118.0), (75, 118.0), (95, 92.0))

TIME_CONSTANT_S = 5.0  # po tylu sekundach tętno pokonuje ok. 63% drogi do wartości docelowej
JITTER_BPM = 1.5


@dataclass(frozen=True)
class PulseSettings:
    viewers: int = 30  # ilu widzów „ma zegarek” w symulacji
    start_bpm: float = 90.0
    excited: float = 1.15  # sala pobudzona: tętno co najmniej 15% powyżej punktu odniesienia
    bored: float = 0.97  # sala znudzona: tętno co najmniej 3% poniżej

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> PulseSettings:
        settings = cls(
            viewers=get_int(env, "BAJKA_PULSE_VIEWERS", cls.viewers),
            start_bpm=get_float(env, "BAJKA_PULSE_START_BPM", cls.start_bpm),
            excited=get_float(env, "BAJKA_PULSE_EXCITED", cls.excited),
            bored=get_float(env, "BAJKA_PULSE_BORED", cls.bored),
        )
        if not settings.bored < 1.0 < settings.excited:
            raise ConfigError("BAJKA_PULSE_EXCITED musi być większe od 1, a BAJKA_PULSE_BORED mniejsze od 1")
        return settings


def hall_state(bpm: float, baseline: float, settings: PulseSettings) -> str:
    """Stan sali względem punktu odniesienia (tętna tuż po pierwszej scenie)."""
    if bpm >= baseline * settings.excited:
        return EXCITED
    if bpm <= baseline * settings.bored:
        return BORED
    return NORMAL


def script_value(script: Sequence[tuple[float, float]], seconds: float) -> float:
    """Tętno z przebiegu w danej sekundzie: liniowo między punktami, poza nimi wartość skrajna."""
    if seconds <= script[0][0]:
        return script[0][1]
    for (t0, v0), (t1, v1) in zip(script, script[1:]):
        if seconds <= t1:
            return v0 + (v1 - v0) * (seconds - t0) / (t1 - t0)
    return script[-1][1]


class SimulatedPulse:
    """Symulowana sala: tętno płynnie dochodzi do wartości docelowej i lekko drga."""

    def __init__(
        self,
        settings: PulseSettings,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._rng = rng or random.Random()
        self._lock = threading.Lock()  # panel ustawia cel z wątku serwera, silnik czyta z wątku bajki
        self._bpm = settings.start_bpm
        self._target = settings.start_bpm
        self._updated = clock()
        self._script: tuple[tuple[float, float], ...] | None = None
        self._script_started = 0.0

    @property
    def target(self) -> float:
        with self._lock:
            return self._target

    def set_target(self, bpm: float) -> None:
        with self._lock:
            self._advance()
            self._script = None
            self._target = min(MAX_BPM, max(MIN_BPM, float(bpm)))

    def preset(self, name: str) -> None:
        if name not in PRESETS:
            raise ValueError(f"nieznany stan sali {name!r}, dostępne: {', '.join(PRESETS)}")
        self.set_target(PRESETS[name])

    def play_script(self, script: Sequence[tuple[float, float]] = DEMO_SCRIPT) -> None:
        with self._lock:
            self._advance()
            self._script = tuple(script)
            self._script_started = self._clock()

    def read(self) -> Pulse:
        with self._lock:
            self._advance()
            bpm = self._bpm + self._rng.uniform(-JITTER_BPM, JITTER_BPM)
        return Pulse(bpm=round(bpm, 1), viewers=self._settings.viewers)

    def _advance(self) -> None:
        now = self._clock()
        if self._script is not None:
            self._target = script_value(self._script, now - self._script_started)
        elapsed = max(0.0, now - self._updated)
        self._bpm += (self._target - self._bpm) * (1 - math.exp(-elapsed / TIME_CONSTANT_S))
        self._updated = now


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.pulse", description="Podgląd symulatora tętna sali.")
    parser.add_argument("--script", action="store_true", help="przebieg demo: spokojnie, ekscytacja, uspokojenie")
    parser.add_argument("--seconds", type=int, default=30, help="jak długo pokazywać odczyty (co sekundę)")
    args = parser.parse_args(argv)
    try:
        settings = PulseSettings.from_env(load_env())
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    pulse = SimulatedPulse(settings)
    if args.script:
        pulse.play_script()
    baseline = pulse.read().bpm
    for _ in range(args.seconds):
        reading = pulse.read()
        state = hall_state(reading.bpm, baseline, settings)
        line = f"tętno {reading.bpm:5.1f} (cel {pulse.target:5.1f}), widzów {reading.viewers}, sala: {state}"
        print(line, flush=True)
        time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_pulse.py -q`
Expected: `18 passed`.

Run: `python -m bajka.pulse --seconds 3`
Expected: trzy linie typu `tętno  90.6 (cel  90.0), widzów 30, sala: w normie`.

- [ ] **Step 5: Konfiguracja i dokumenty**

<!-- edit: .env.example -->
Zamień w `.env.example`:

```text
BAJKA_MOBILE_WORKERS=2

```

na:

```text
BAJKA_MOBILE_WORKERS=2

# --- bajka/pulse.py: tętno sali; na pokazie z symulatora sterowanego z panelu (flaga --panel) ---
BAJKA_PULSE_VIEWERS=30
BAJKA_PULSE_START_BPM=90
# Progi względem tętna tuż po pierwszej scenie: sala pobudzona (tętno ≥ ×1,15) albo znudzona (≤ ×0,97).
BAJKA_PULSE_EXCITED=1.15
BAJKA_PULSE_BORED=0.97

```

<!-- edit: docs/PODZIAL_PRACY.md -->
Zamień w `docs/PODZIAL_PRACY.md`:

```markdown
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |
```

na:

```markdown
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |
| [`bajka/pulse.py`](../bajka/pulse.py) — tętno sali (na pokazie z symulatora) i stan sali | `AudiencePulse` | C | `python -m bajka.pulse --script` | `tests/test_pulse.py` |
```

<!-- edit: README.md -->
Zamień w `README.md`:

```markdown
python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4   # klip → pętla (VLC)
```

na:

```markdown
python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4   # klip → pętla (VLC)
python -m bajka.pulse --script                       # symulator tętna sali: spokojnie, ekscytacja, uspokojenie
```

<!-- edit: README.md -->
Zamień w `README.md`:

```markdown
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg) |
```

na:

```markdown
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg) |
| `bajka/pulse.py` | Tętno sali: symulator na pokaz (`SimulatedPulse`) i stan sali (`hall_state`) |
```

- [ ] **Step 6: Pełny zestaw testów**

Run: `python -m pytest -q`
Expected: `244 passed, 1 skipped`.

<!-- checkpoint -->

- [ ] **Step 7: Commit**

```bash
git add bajka/pulse.py bajka/ports.py tests/test_pulse.py .env.example docs/PODZIAL_PRACY.md README.md
git commit -m "feat: symulowane tętno sali i stan sali względem punktu odniesienia"
```

---

### Task 3: Wersje scen według tętna sali

**Files:**
- Create: `tests/test_engine_pulse.py`
- Modify: `bajka/scenario.py`, `bajka/pulse.py`, `bajka/engine.py`, `bajka/placeholders.py`, `scenarios/klub_ciekawskich.yaml`
- Test: `tests/test_scenario.py`, `tests/test_pulse.py`, `tests/test_placeholders.py`, `tests/test_klub_ciekawskich.py`, `tests/test_engine_pulse.py`

**Interfaces:**
- Consumes: z Task 2 `AudiencePulse`, `Pulse`, `PulseSettings`, `hall_state`, `EXCITED`, `BORED`.
- Produces:
  - w `bajka/scenario.py`: `CALM_FILM = "spokojny"`, `LIVELY_FILM = "zywy"`, `MOODS`, `CALM = "spokojna"`, `LIVELY = "zywa"`, `VARIANTS`; `Scenario.mood: str = ""`; `Scene.variants: dict[str, Path]`; `variants` bez `mood` to `ScenarioError`; `missing_media` obejmuje klipy wersji,
  - w `bajka/pulse.py`: `pick_variant(mood, state) -> str | None`,
  - `StoryEngine(..., audience=None, pulse: AudiencePulse | None = None, pulse_settings: PulseSettings | None = None)`; punkt odniesienia = pierwszy udany odczyt po klipie sceny startowej; `_clip_for(scene)` wybiera klip; `_read_bpm()` łapie błędy odczytu,
  - w `bajka/placeholders.py`: `LABEL_FONT`; `ffmpeg_command(target, color, seconds, with_tone, label="", font=None)`; wersje scen w `planned_clips`.

- [ ] **Step 1: Testy scenariusza, reguły wersji, silnika, zaślepek i scenariusza Bzyczki**

<!-- edit: tests/test_scenario.py -->
Zamień w `tests/test_scenario.py`:

```python
    with pytest.raises(ScenarioError, match="keywords"):
        parse_scenario(scenario_dict, base_dir=Path("."))

```

na:

```python
    with pytest.raises(ScenarioError, match="keywords"):
        parse_scenario(scenario_dict, base_dir=Path("."))


# Nastrój filmu i wersje scen (tętno sali)


def calm_film(scenario_dict, variants):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = variants
    return scenario_dict


def test_mood_and_scene_versions_are_parsed(scenario_dict):
    scenario = parse_scenario(calm_film(scenario_dict, {"spokojna": "las_spokojna.mp4"}), base_dir=Path("film"))

    assert scenario.mood == "spokojny"
    assert scenario.scene("las").variants == {"spokojna": Path("film/las_spokojna.mp4")}
    assert scenario.scene("intro").variants == {}


def test_film_without_mood_does_not_adapt(scenario):
    assert scenario.mood == ""


def test_unknown_mood_is_refused(scenario_dict):
    scenario_dict["mood"] = "straszny"
    with pytest.raises(ScenarioError, match="'mood'.*spokojny, zywy"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_unknown_scene_version_is_refused(scenario_dict):
    with pytest.raises(ScenarioError, match="scena 'las': nieznane wersje sceny: szybka"):
        parse_scenario(calm_film(scenario_dict, {"szybka": "las_szybka.mp4"}), base_dir=Path("film"))


def test_scene_versions_must_be_a_mapping_of_files(scenario_dict):
    with pytest.raises(ScenarioError, match="'variants'"):
        parse_scenario(calm_film(scenario_dict, ["las_spokojna.mp4"]), base_dir=Path("film"))


def test_scene_versions_need_the_mood_of_the_film(scenario_dict):
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}
    with pytest.raises(ScenarioError, match="scena 'las': 'variants' wymaga pola 'mood'"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_missing_media_lists_missing_version_clips(tmp_path, scenario_dict):
    for name in ("intro.mp4", "intro_idle.mp4", "las.mp4", "jaskinia.mp4"):
        (tmp_path / name).touch()
    scenario = parse_scenario(calm_film(scenario_dict, {"spokojna": "las_spokojna.mp4"}), base_dir=tmp_path)

    assert missing_media(scenario) == [tmp_path / "las_spokojna.mp4"]

```

<!-- edit: tests/test_pulse.py -->
Zamień w `tests/test_pulse.py`:

```python
    hall_state,
```

na:

```python
    hall_state,
    pick_variant,
```

<!-- edit: tests/test_pulse.py -->
Zamień w `tests/test_pulse.py`:

```python
        PulseSettings.from_env({"BAJKA_PULSE_EXCITED": excited, "BAJKA_PULSE_BORED": bored})

```

na:

```python
        PulseSettings.from_env({"BAJKA_PULSE_EXCITED": excited, "BAJKA_PULSE_BORED": bored})


@pytest.mark.parametrize(
    ("mood", "state", "variant"),
    [
        ("spokojny", EXCITED, "spokojna"),
        ("spokojny", NORMAL, None),
        ("spokojny", BORED, None),
        ("zywy", BORED, "zywa"),
        ("zywy", NORMAL, None),
        ("zywy", EXCITED, None),
        ("", EXCITED, None),
    ],
)
def test_pick_variant_brings_the_hall_towards_the_mood_of_the_film(mood, state, variant):
    assert pick_variant(mood, state) == variant

```

<!-- file: tests/test_engine_pulse.py -->
Utwórz `tests/test_engine_pulse.py`:

```python
"""Silnik i tętno sali: wersja sceny według stanu widowni i nastroju filmu."""

from pathlib import Path

from bajka.engine import StoryEngine
from bajka.ports import Interpretation, Pulse
from bajka.pulse import PulseSettings
from bajka.scenario import parse_scenario


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, clip):
        self.calls.append(("play", clip.name))

    def loop(self, clip):
        self.calls.append(("loop", clip.name))


class AnswerListener:
    def listen(self):
        return "las"


class SilentVoice:
    def say(self, text):
        pass


class ChooseForest:
    def resolve(self, scene, transcript):
        return Interpretation("las", "Do lasu!")


class ScriptedPulse:
    """Kolejne odczyty tętna sali; wyjątek z listy zostaje rzucony."""

    def __init__(self, *readings):
        self._readings = list(readings)
        self.reads = 0

    def read(self):
        self.reads += 1
        reading = self._readings.pop(0)
        if isinstance(reading, Exception):
            raise reading
        return Pulse(bpm=reading, viewers=30)


def adaptive_scenario(scenario_dict, mood="spokojny", variants=None):
    scenario_dict["mood"] = mood
    scenario_dict["scenes"]["las"]["variants"] = variants or {"spokojna": "las_spokojna.mp4", "zywa": "las_zywa.mp4"}
    return parse_scenario(scenario_dict, base_dir=Path("film"))


def run(scenario, pulse):
    player = FakePlayer()
    engine = StoryEngine(
        scenario, player, AnswerListener(), SilentVoice(), ChooseForest(), pulse=pulse, pulse_settings=PulseSettings()
    )
    engine.run()
    return player.calls


def test_excited_hall_gets_the_calm_version_of_a_calm_film(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, 110.0))  # 110 ≥ 90 × 1,15

    assert calls[-1] == ("play", "las_spokojna.mp4")


def test_hall_in_normal_state_gets_the_regular_clip(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, 95.0))

    assert calls[-1] == ("play", "las.mp4")


def test_bored_hall_gets_the_lively_version_of_a_lively_film(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict, mood="zywy"), ScriptedPulse(90.0, 85.0))  # 85 ≤ 90 × 0,97

    assert calls[-1] == ("play", "las_zywa.mp4")


def test_scene_without_the_chosen_version_plays_the_regular_clip(scenario_dict):
    scenario = adaptive_scenario(scenario_dict, variants={"zywa": "las_zywa.mp4"})

    calls = run(scenario, ScriptedPulse(90.0, 120.0))

    assert calls[-1] == ("play", "las.mp4")


def test_baseline_is_read_after_the_first_scene_and_then_only_before_scenes_with_versions(scenario_dict):
    pulse = ScriptedPulse(90.0, 110.0)

    run(adaptive_scenario(scenario_dict), pulse)

    assert pulse.reads == 2  # punkt odniesienia po „intro” i jeden odczyt przed „las”


def test_pulse_error_plays_the_regular_clip(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, RuntimeError("zegarek milczy")))

    assert calls[-1] == ("play", "las.mp4")


def test_failed_baseline_means_no_adaptation(scenario_dict):
    pulse = ScriptedPulse(RuntimeError("zegarek milczy"))

    calls = run(adaptive_scenario(scenario_dict), pulse)

    assert calls[-1] == ("play", "las.mp4")
    assert pulse.reads == 1


def test_without_pulse_the_film_does_not_adapt(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), None)

    assert calls[-1] == ("play", "las.mp4")
```

<!-- edit: tests/test_placeholders.py -->
Zamień w `tests/test_placeholders.py`:

```python
from bajka.placeholders import ffmpeg_command, planned_clips
```

na:

```python
from bajka.placeholders import ffmpeg_command, planned_clips
from bajka.scenario import parse_scenario
```

<!-- edit: tests/test_placeholders.py -->
Zamień w `tests/test_placeholders.py`:

```python
    assert "sine=frequency=440:duration=2.5" in cmd

```

na:

```python
    assert "sine=frequency=440:duration=2.5" in cmd


def test_scene_versions_are_planned_with_tone_in_the_scene_color(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}

    clips = planned_clips(parse_scenario(scenario_dict, base_dir=Path("film")))

    las_color = next(color for path, color, _ in clips if path.name == "las.mp4")
    assert (Path("film/las_spokojna.mp4"), las_color, True) in clips


def test_ffmpeg_command_writes_the_label_with_the_given_font():
    font = Path("C:/Windows/Fonts/arial.ttf")
    cmd = ffmpeg_command(Path("out/las_spokojna.mp4"), "indigo", 2.0, with_tone=True, label="las_spokojna", font=font)

    video_filter = cmd[cmd.index("-vf") + 1]
    assert "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf'" in video_filter
    assert "text='las_spokojna'" in video_filter


def test_ffmpeg_command_without_font_has_no_label():
    cmd = ffmpeg_command(Path("out/las.mp4"), "indigo", 2.0, with_tone=True, label="las", font=None)

    assert "-vf" not in cmd

```

<!-- edit: tests/test_klub_ciekawskich.py -->
Zamień w `tests/test_klub_ciekawskich.py`:

```python
    assert all(labels) and max(map(len, labels)) <= 24

```

na:

```python
    assert all(labels) and max(map(len, labels)) <= 24


def test_calm_film_has_calm_versions_of_three_lively_scenes():
    assert SCENARIO.mood == "spokojny"
    assert {s.id for s in SCENARIO.scenes.values() if s.variants} == {"las", "wiaterek", "swieto"}
    assert all(set(s.variants) == {"spokojna"} for s in SCENARIO.scenes.values() if s.variants)

```

- [ ] **Step 2: Uruchom testy i sprawdź, że padają**

Run: `python -m pytest tests/test_scenario.py tests/test_engine_pulse.py tests/test_placeholders.py tests/test_klub_ciekawskich.py -q` i osobno `python -m pytest tests/test_pulse.py -q`
Expected: FAIL — m.in. `AttributeError: 'Scenario' object has no attribute 'mood'`, `TypeError: StoryEngine.__init__() got an unexpected keyword argument 'pulse'`, `TypeError: ffmpeg_command() got an unexpected keyword argument 'label'`, a w `tests/test_pulse.py` błąd importu `pick_variant`.

- [ ] **Step 3: Nastrój filmu, wersje scen, reguła wyboru, silnik, zaślepki i scenariusz Bzyczki**

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
REMOVED_SCENARIO_FIELDS = ("style", "references")
```

na:

```python
REMOVED_SCENARIO_FIELDS = ("style", "references")

CALM_FILM, LIVELY_FILM = "spokojny", "zywy"  # nastrój filmu (`mood`): czego widownia oczekuje od filmu
MOODS = (CALM_FILM, LIVELY_FILM)
CALM, LIVELY = "spokojna", "zywa"  # wersje montażu sceny (`variants`), wybierane według tętna sali
VARIANTS = (CALM, LIVELY)
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    vote: bool = False  # widownia wybiera okrzykiem: wygrywa najgłośniej wykrzyczana opcja (seans w kinie)
```

na:

```python
    vote: bool = False  # widownia wybiera okrzykiem: wygrywa najgłośniej wykrzyczana opcja (seans w kinie)
    variants: dict[str, Path] = field(default_factory=dict)  # wersje montażu: spokojna / zywa → klip
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    scenes: dict[str, Scene]
```

na:

```python
    scenes: dict[str, Scene]
    mood: str = ""  # nastrój filmu; bez niego film nie dopasowuje się do tętna sali
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    _reject_removed(raw, REMOVED_SCENARIO_FIELDS, "scenariusz")
```

na:

```python
    _reject_removed(raw, REMOVED_SCENARIO_FIELDS, "scenariusz")
    mood = str(raw.get("mood") or "").strip()
    if mood and mood not in MOODS:
        raise ScenarioError(f"scenariusz: 'mood' musi być jednym z: {', '.join(MOODS)}, jest: {mood!r}")
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
```

na:

```python
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
        mood=mood,
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        paths.extend(c.call_clip for c in scene.choices.values() if c.call_clip is not None)
```

na:

```python
        paths.extend(c.call_clip for c in scene.choices.values() if c.call_clip is not None)
        paths.extend(scene.variants.values())
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    if not choices:
        return Scene(id=scene_id, clip=clip)
```

na:

```python
    variants = _parse_variants(data, base_dir, where)
    if not choices:
        return Scene(id=scene_id, clip=clip, variants=variants)
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
        vote=vote,
```

na:

```python
        vote=vote,
        variants=variants,
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
    return value.strip()
```

na:

```python
    return value.strip()


def _parse_variants(data: dict, base_dir: Path, where: str) -> dict[str, Path]:
    raw = data.get("variants")
    if raw is None:
        return {}
    if not isinstance(raw, dict) or not raw:
        raise ScenarioError(f"{where}: 'variants' musi być słownikiem wersji sceny, np. spokojna: las_spokojna.mp4")
    unknown = [str(key) for key in raw if key not in VARIANTS]
    if unknown:
        raise ScenarioError(
            f"{where}: nieznane wersje sceny: {', '.join(unknown)} (dostępne: {', '.join(VARIANTS)})"
        )
    return {key: base_dir / _require_str(raw, key, f"{where}, wersje sceny") for key in raw}
```

<!-- edit: bajka/scenario.py -->
Zamień w `bajka/scenario.py`:

```python
            )
        for choice in scene.choices.values():
```

na:

```python
            )
        if scene.variants and not scenario.mood:
            raise ScenarioError(f"scena '{scene.id}': 'variants' wymaga pola 'mood' scenariusza ({', '.join(MOODS)})")
        for choice in scene.choices.values():
```

<!-- edit: bajka/pulse.py -->
Zamień w `bajka/pulse.py`:

```python
Moduł spełnia kontrakt `bajka.ports.AudiencePulse`; `hall_state` porównuje tętno z punktem odniesienia.
```

na:

```python
Moduł spełnia kontrakt `bajka.ports.AudiencePulse`; `hall_state` porównuje tętno z punktem odniesienia,
a `pick_variant` dobiera wersję sceny, która przybliża salę do nastroju filmu.
```

<!-- edit: bajka/pulse.py -->
Zamień w `bajka/pulse.py`:

```python
from bajka.ports import Pulse
```

na:

```python
from bajka.ports import Pulse
from bajka.scenario import CALM, CALM_FILM, LIVELY, LIVELY_FILM
```

<!-- edit: bajka/pulse.py -->
Zamień w `bajka/pulse.py`:

```python
    return NORMAL
```

na:

```python
    return NORMAL


def pick_variant(mood: str, state: str) -> str | None:
    """Wersja sceny, która przybliża salę do nastroju filmu; None oznacza zwykły klip."""
    if mood == CALM_FILM and state == EXCITED:
        return CALM  # spokojny film, a sala się ekscytuje: wolniejszy montaż
    if mood == LIVELY_FILM and state == BORED:
        return LIVELY
    return None
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
from bajka.ports import Audience, IntentResolver, Interpretation, Listener, Player, ShoutMeter, Voice
```

na:

```python
from bajka.ports import Audience, AudiencePulse, IntentResolver, Interpretation, Listener, Player, ShoutMeter, Voice
from bajka.pulse import PulseSettings, hall_state, pick_variant
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
    ) -> None:
        self._stopped = threading.Event()
```

na:

```python
        pulse: AudiencePulse | None = None,
        pulse_settings: PulseSettings | None = None,
    ) -> None:
        self._stopped = threading.Event()
        self._pulse = pulse  # tętno sali; bez niego sceny grają zawsze zwykłą wersję
        self._pulse_settings = pulse_settings or PulseSettings()
        self._baseline: float | None = None  # tętno tuż po pierwszej scenie, punkt odniesienia na cały seans
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python

    def run(self) -> list[str]:
```

na:

```python

    def _clip_for(self, scene: Scene) -> Path:
        """Wersja montażu według tętna sali; zwykły klip, gdy tętna nie ma albo sala jest w normie."""
        if not scene.variants or self._pulse is None or self._baseline is None:
            return scene.clip
        bpm = self._read_bpm()
        if bpm is None:
            return scene.clip
        state = hall_state(bpm, self._baseline, self._pulse_settings)
        variant = pick_variant(self._scenario.mood, state)
        chosen = variant if variant in scene.variants else None
        log.info("Tętno sali %.0f (odniesienie %.0f), sala %s: scena %s w wersji %s",
                 bpm, self._baseline, state, scene.id, chosen or "zwykłej")  # fmt: skip
        return scene.variants[chosen] if chosen else scene.clip

    def _read_bpm(self) -> float | None:
        try:
            return self._pulse.read().bpm
        except Exception:
            log.exception("Błąd odczytu tętna sali, scena w zwykłej wersji")
            return None

    def run(self) -> list[str]:
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                self._play(scene.clip)
                if scene.is_ending:
                    return visited
```

na:

```python
                self._play(self._clip_for(scene))
                if scene.is_ending:
                    return visited
                if self._pulse is not None and self._baseline is None:
                    self._baseline = self._read_bpm()  # sala dopiero usiadła
```

<!-- edit: bajka/placeholders.py -->
Zamień w `bajka/placeholders.py`:

```python


def planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]:
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen mają ton, a pętle oczekiwania są ciche."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        for path, with_tone in ((scene.clip, True), (scene.idle, False)):
```

na:

```python
LABEL_FONT = Path("C:/Windows/Fonts/arial.ttf")  # ffmpeg na Windows pisze na klipie tylko z podaną czcionką


def planned_clips(scenario: Scenario) -> list[tuple[Path, str, bool]]:
    """(ścieżka, kolor, czy z dźwiękiem) — klipy scen i ich wersje mają ton, a pętle oczekiwania są ciche."""
    clips: dict[Path, tuple[Path, str, bool]] = {}
    for index, scene in enumerate(scenario.scenes.values()):
        color = COLORS[index % len(COLORS)]
        tracks = [(scene.clip, True), (scene.idle, False)] + [(path, True) for path in scene.variants.values()]
        for path, with_tone in tracks:
```

<!-- edit: bajka/placeholders.py -->
Zamień w `bajka/placeholders.py`:

```python
def ffmpeg_command(target: Path, color: str, seconds: float, with_tone: bool) -> list[str]:
```

na:

```python
def ffmpeg_command(
    target: Path, color: str, seconds: float, with_tone: bool, label: str = "", font: Path | None = None
) -> list[str]:
```

<!-- edit: bajka/placeholders.py -->
Zamień w `bajka/placeholders.py`:

```python
        cmd += ["-an"]
```

na:

```python
        cmd += ["-an"]
    if label and font is not None:  # nazwa pliku na planszy: na próbie widać, która scena i wersja gra
        fontfile = str(font).replace("\\", "/").replace(":", "\\:")
        text = label.replace("'", "").replace(":", "\\:")
        position = "fontsize=56:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
        cmd += ["-vf", f"drawtext=fontfile='{fontfile}':text='{text}':{position}"]
```

<!-- edit: bajka/placeholders.py -->
Zamień w `bajka/placeholders.py`:

```python
        return 1
```

na:

```python
        return 1
    font = LABEL_FONT if LABEL_FONT.is_file() else None
```

<!-- edit: bajka/placeholders.py -->
Zamień w `bajka/placeholders.py`:

```python
        subprocess.run(ffmpeg_command(path, color, args.seconds, with_tone), check=True)
```

na:

```python
        subprocess.run(ffmpeg_command(path, color, args.seconds, with_tone, path.stem, font), check=True)
```

<!-- edit: scenarios/klub_ciekawskich.yaml -->
Zamień w `scenarios/klub_ciekawskich.yaml`:

```yaml
start: powitanie
```

na:

```yaml
start: powitanie
# Film jest spokojny. Gdy tętno sali skacze (flaga --panel, symulator tętna), sceny z `variants` grają wersję
# spokojną: dłuższe ujęcia, wolniejszy montaż. Bez --panel film leci zawsze w zwykłych wersjach.
mood: spokojny
```

<!-- edit: scenarios/klub_ciekawskich.yaml -->
Zamień w `scenarios/klub_ciekawskich.yaml`:

```yaml
    clip: clips/klub_ciekawskich/03b_las.mp4
```

na:

```yaml
    clip: clips/klub_ciekawskich/03b_las.mp4
    variants:
      spokojna: clips/klub_ciekawskich/03b_las_spokojna.mp4
```

<!-- edit: scenarios/klub_ciekawskich.yaml -->
Zamień w `scenarios/klub_ciekawskich.yaml`:

```yaml
    clip: clips/klub_ciekawskich/04_wiaterek.mp4
```

na:

```yaml
    clip: clips/klub_ciekawskich/04_wiaterek.mp4
    variants:
      spokojna: clips/klub_ciekawskich/04_wiaterek_spokojna.mp4
```

<!-- edit: scenarios/klub_ciekawskich.yaml -->
Zamień w `scenarios/klub_ciekawskich.yaml`:

```yaml
    clip: clips/klub_ciekawskich/07_swieto.mp4
```

na:

```yaml
    clip: clips/klub_ciekawskich/07_swieto.mp4
    variants:
      spokojna: clips/klub_ciekawskich/07_swieto_spokojna.mp4
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_scenario.py tests/test_pulse.py tests/test_engine_pulse.py tests/test_placeholders.py tests/test_klub_ciekawskich.py tests/test_engine.py tests/test_vote.py -q`
Expected: PASS.

Run (wymaga ffmpeg w PATH): `python -m bajka.placeholders scenarios/klub_ciekawskich.yaml --seconds 1`
Expected: wśród utworzonych plików `03b_las_spokojna.mp4`, `04_wiaterek_spokojna.mp4`, `07_swieto_spokojna.mp4`; na Windows plansze mają nazwę pliku na środku. Klipy w `scenarios/clips/` są w `.gitignore`.

- [ ] **Step 5: Pełny zestaw testów**

Run: `python -m pytest -q`
Expected: `270 passed, 1 skipped`.

<!-- checkpoint -->

- [ ] **Step 6: Commit**

```bash
git add bajka/scenario.py bajka/pulse.py bajka/engine.py bajka/placeholders.py scenarios/klub_ciekawskich.yaml tests/test_scenario.py tests/test_pulse.py tests/test_engine_pulse.py tests/test_placeholders.py tests/test_klub_ciekawskich.py
git commit -m "feat: wersje scen według tętna sali i nastroju filmu; spokojne wersje trzech scen Bzyczki"
```

---

### Task 4: Zdarzenia seansu i serwer panelu

**Files:**
- Create: `bajka/panel.py`, `tests/test_engine_events.py`, `tests/test_panel.py`
- Modify: `bajka/ports.py`, `bajka/engine.py`

**Interfaces:**
- Consumes: z Task 2 `Pulse`, `AudiencePulse`, `PulseSettings`, `SimulatedPulse`, `hall_state`; z Task 3 `Scenario.mood`, `Scene.variants`, `StoryEngine._clip_for`.
- Produces:
  - w `bajka/ports.py`: `ShowObserver` z `event(kind: str, data: Mapping[str, Any]) -> None`,
  - `StoryEngine(..., observer: ShowObserver | None = None)`; `_emit(kind, **data)` (błąd obserwatora tylko w logu „Błąd panelu, film leci dalej”); `_decided(scene, choice, how) -> Choice`; `_clip_for(scene) -> tuple[Path, str]`,
  - zdarzenia i ich dane:

    | Zdarzenie | Dane |
    |---|---|
    | `scena` | `scene`, `clip` (nazwa pliku), `variant` |
    | `odniesienie` | `bpm` |
    | `wersja` | `scene`, `bpm`, `baseline`, `state`, `variant` |
    | `glosy` | `scene`, `source` (`telefony` / `krzykomierz`), `counts` |
    | `decyzja` | `scene`, `choice`, `label`, `how` |

  - w `bajka/panel.py`: `PanelSettings(host="127.0.0.1", port=8090)` z `from_env`; `scenario_graph(scenario) -> dict`; `PanelState(scenario, pulse_settings, clock=time.monotonic)` z `event`, `record_pulse(reading)`, `snapshot()`; `PanelServer(state, graph, pulse, settings, sample_every_s=1.0)` z `start() -> str` (adres `http://127.0.0.1:PORT/`) i `stop()`; trasy `GET /`, `GET /graph`, `GET /state`, `POST /pulse`; `APP_DIR = bajka/panel_app`.

- [ ] **Step 1: Testy zdarzeń silnika i panelu**

<!-- file: tests/test_engine_events.py -->
Utwórz `tests/test_engine_events.py`:

```python
"""Silnik opowiada panelowi dla jury, co się dzieje: sceny, wersje według tętna, głosy i decyzje."""

import logging
from pathlib import Path

from bajka.engine import StoryEngine
from bajka.ports import Interpretation, Pulse, ShowObserver
from bajka.scenario import parse_scenario


class FakePlayer:
    def play(self, clip):
        pass

    def loop(self, clip):
        pass


class FakeListener:
    def __init__(self, *answers):
        self._answers = list(answers)

    def listen(self):
        return self._answers.pop(0)


class SilentVoice:
    def say(self, text):
        pass


class ChooseForest:
    def resolve(self, scene, transcript):
        return Interpretation("las", "Do lasu!")


class RecordingObserver:
    def __init__(self):
        self.events = []

    def event(self, kind, data):
        self.events.append((kind, dict(data)))


class BrokenObserver:
    def event(self, kind, data):
        raise RuntimeError("panel padł")


class ScriptedPulse:
    def __init__(self, *readings):
        self._readings = list(readings)

    def read(self):
        return Pulse(bpm=self._readings.pop(0), viewers=30)


class PhoneAudience:
    def __init__(self, answers):
        self._answers = answers

    def connected(self):
        return len(self._answers)

    def collect(self, scene):
        return [Interpretation(choice, "") for choice in self._answers]


class FakeMeter:
    def __init__(self, levels):
        self._levels = list(levels)

    def calibrate(self):
        pass

    def measure(self):
        return self._levels.pop(0)

    def winner(self, levels):
        return max(levels, key=levels.get)


def run(scenario, listener=None, **options):
    observer = RecordingObserver()
    engine = StoryEngine(
        scenario, FakePlayer(), listener or FakeListener("las"), SilentVoice(), ChooseForest(), observer=observer,
        **options,
    )  # fmt: skip
    visited = engine.run()
    return visited, observer.events


def test_recording_observer_fulfils_contract():
    assert isinstance(RecordingObserver(), ShowObserver)


def test_engine_reports_scenes_and_the_answer_from_the_microphone(scenario):
    _, events = run(scenario)

    assert events == [
        ("scena", {"scene": "intro", "clip": "intro.mp4", "variant": "zwykla"}),
        ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "odpowiedz"}),
        ("scena", {"scene": "las", "clip": "las.mp4", "variant": "zwykla"}),
    ]


def test_default_choice_after_silence_is_reported(scenario):
    _, events = run(scenario, FakeListener(None, None, None))

    assert ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "domyslna"}) in events


def test_baseline_and_version_by_pulse_are_reported(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))

    _, events = run(scenario, pulse=ScriptedPulse(90.0, 110.0))

    assert [kind for kind, _ in events] == ["scena", "odniesienie", "decyzja", "wersja", "scena"]
    assert events[1] == ("odniesienie", {"bpm": 90.0})
    assert events[3] == (
        "wersja", {"scene": "las", "bpm": 110.0, "baseline": 90.0, "state": "pobudzona", "variant": "spokojna"}
    )
    assert events[4] == ("scena", {"scene": "las", "clip": "las_spokojna.mp4", "variant": "spokojna"})


def test_phone_votes_and_majority_are_reported(scenario):
    _, events = run(scenario, audience=PhoneAudience(["las", "las", "jaskinia"]))

    assert ("glosy", {"scene": "intro", "source": "telefony", "counts": {"las": 2, "jaskinia": 1}}) in events
    assert ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "wiekszosc"}) in events


def test_shout_round_is_reported(scenario_dict):
    scene = scenario_dict["scenes"]["intro"]
    scene["vote"] = True
    scene["choices"]["las"]["call"] = "Kto do lasu?"
    scene["choices"]["jaskinia"]["call"] = "Kto do jaskini?"
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))

    _, events = run(scenario, meter=FakeMeter([3000.4, 1000.0]))

    assert ("glosy", {"scene": "intro", "source": "krzykomierz", "counts": {"las": 3000, "jaskinia": 1000}}) in events
    assert ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "okrzyk"}) in events


def test_broken_panel_does_not_stop_the_film(scenario, caplog):
    engine = StoryEngine(scenario, FakePlayer(), FakeListener("las"), SilentVoice(), ChooseForest(),
                         observer=BrokenObserver())  # fmt: skip

    with caplog.at_level(logging.ERROR):
        assert engine.run() == ["intro", "las"]

    assert "Błąd panelu" in caplog.text
```

<!-- file: tests/test_panel.py -->
Utwórz `tests/test_panel.py`:

```python
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from bajka.config import ConfigError
from bajka.panel import PanelServer, PanelSettings, PanelState, scenario_graph
from bajka.ports import Pulse, ShowObserver
from bajka.pulse import PulseSettings, SimulatedPulse
from bajka.scenario import parse_scenario

# Drzewo scen


def test_graph_lists_scenes_by_distance_from_start_and_labelled_edges(scenario):
    graph = scenario_graph(scenario)

    assert graph["start"] == "intro"
    assert graph["mood"] == ""
    assert graph["scenes"] == [
        {"id": "intro", "depth": 0, "question": "Idziemy do mrocznego lasu czy do jaskini?", "ending": False,
         "variants": []},
        {"id": "las", "depth": 1, "question": "", "ending": True, "variants": []},
        {"id": "jaskinia", "depth": 1, "question": "", "ending": True, "variants": []},
    ]  # fmt: skip
    assert graph["edges"] == [
        {"from": "intro", "to": "las", "choice": "las", "label": "Las"},
        {"from": "intro", "to": "jaskinia", "choice": "jaskinia", "label": "Jaskinia"},
    ]


def test_graph_shows_versions_and_puts_unreachable_scenes_last(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}
    scenario_dict["scenes"]["sekret"] = {"clip": "sekret.mp4"}

    graph = scenario_graph(parse_scenario(scenario_dict, base_dir=Path("film")))

    scenes = {scene["id"]: scene for scene in graph["scenes"]}
    assert graph["mood"] == "spokojny"
    assert scenes["las"]["variants"] == ["spokojna"]
    assert scenes["sekret"]["depth"] == 2


# Stan panelu ze zdarzeń silnika


def texts(snapshot):
    return [entry["text"] for entry in snapshot["log"]]


def test_state_fulfils_observer_contract_and_starts_empty(scenario):
    state = PanelState(scenario, PulseSettings())

    assert isinstance(state, ShowObserver)
    snapshot = state.snapshot()
    assert snapshot["scene"] is None
    assert snapshot["path"] == [] and snapshot["decisions"] == [] and snapshot["votes"] is None
    assert snapshot["pulse"]["history"] == [] and snapshot["pulse"]["baseline"] is None


def test_scenes_and_decisions_build_the_path_and_the_log(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("scena", {"scene": "intro", "clip": "intro.mp4", "variant": "zwykla"})
    state.event("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "wiekszosc"})
    state.event("scena", {"scene": "las", "clip": "las_spokojna.mp4", "variant": "spokojna"})

    snapshot = state.snapshot()
    assert snapshot["scene"] == "las"
    assert snapshot["path"] == [{"scene": "intro", "variant": "zwykla"}, {"scene": "las", "variant": "spokojna"}]
    assert snapshot["decisions"] == [{"scene": "intro", "choice": "las", "label": "Las", "how": "wiekszosc"}]
    assert texts(snapshot) == [
        "Scena intro",
        "Decyzja w scenie intro: Las (większość głosów z telefonów)",
        "Scena las w wersji spokojnej",
    ]


def test_votes_are_kept_and_described_with_option_labels(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("glosy", {"scene": "intro", "source": "telefony", "counts": {"las": 2, "jaskinia": 1}})

    snapshot = state.snapshot()
    assert snapshot["votes"] == {"scene": "intro", "source": "telefony", "counts": {"las": 2, "jaskinia": 1}}
    assert texts(snapshot) == ["Głosy (telefony): Las 2, Jaskinia 1"]


def test_pulse_samples_baseline_and_hall_state(scenario):
    clock = iter([10.0, 11.0, 12.0]).__next__
    state = PanelState(scenario, PulseSettings(), clock=clock)

    state.record_pulse(Pulse(bpm=90.0, viewers=30))
    state.event("odniesienie", {"bpm": 90.0})
    state.record_pulse(Pulse(bpm=110.0, viewers=30))

    pulse = state.snapshot()["pulse"]
    assert pulse["history"] == [[1.0, 90.0], [2.0, 110.0]]
    assert pulse["bpm"] == 110.0 and pulse["viewers"] == 30
    assert pulse["baseline"] == 90.0
    assert pulse["excited"] == pytest.approx(103.5) and pulse["bored"] == pytest.approx(87.3)
    assert pulse["state"] == "pobudzona"
    assert texts(state.snapshot()) == ["Punkt odniesienia tętna sali: 90"]


def test_version_choice_is_explained_in_one_sentence(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("wersja", {"scene": "las", "bpm": 110.0, "baseline": 90.0, "state": "pobudzona", "variant": "spokojna"})

    assert texts(state.snapshot()) == ["Tętno sali 110 (odniesienie 90), sala pobudzona: scena las w wersji spokojnej"]


def test_history_and_log_keep_only_the_latest_entries(scenario):
    state = PanelState(scenario, PulseSettings())

    for second in range(150):
        state.record_pulse(Pulse(bpm=90.0 + second % 3, viewers=30))
        state.event("scena", {"scene": "intro", "clip": "intro.mp4", "variant": "zwykla"})

    snapshot = state.snapshot()
    assert len(snapshot["pulse"]["history"]) == 120
    assert len(snapshot["log"]) == 20


def test_unknown_event_is_ignored(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("fajerwerki", {"ile": 3})

    assert state.snapshot()["log"] == []


# Ustawienia


def test_settings_from_env():
    assert PanelSettings.from_env({}) == PanelSettings(host="127.0.0.1", port=8090)
    assert PanelSettings.from_env({"BAJKA_PANEL_HOST": "0.0.0.0", "BAJKA_PANEL_PORT": "9000"}) == PanelSettings(
        host="0.0.0.0", port=9000
    )
    with pytest.raises(ConfigError, match="BAJKA_PANEL_PORT"):
        PanelSettings.from_env({"BAJKA_PANEL_PORT": "osiem"})


# Serwer


@pytest.fixture
def server(scenario):
    simulator = SimulatedPulse(PulseSettings())
    panel = PanelServer(PanelState(scenario, PulseSettings()), scenario_graph(scenario), simulator,
                        PanelSettings(port=0), sample_every_s=0.05)  # fmt: skip
    url = panel.start()
    yield panel, url, simulator
    panel.stop()


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read())


def post(url, body):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        with error:  # odpowiedź z błędem też trzyma połączenie: zamykamy ją
            return error.code, json.loads(error.read())


def test_server_serves_graph_and_state_with_the_simulator_target(server, scenario):
    _, url, _ = server

    assert url.startswith("http://") and url.endswith("/")
    assert get(url + "graph") == (200, scenario_graph(scenario))
    status, state = get(url + "state")
    assert status == 200
    assert state["scene"] is None
    assert state["pulse"]["target"] == 90.0


def test_server_samples_the_pulse_in_the_background(server):
    _, url, _ = server
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and not get(url + "state")[1]["pulse"]["history"]:
        time.sleep(0.05)

    assert get(url + "state")[1]["pulse"]["history"]


@pytest.mark.parametrize(
    ("body", "target"),
    [({"target": 120}, 120.0), ({"preset": "nudzi-sie"}, 85.0), ({"target": "130"}, 130.0)],
)
def test_pulse_commands_set_the_simulator(server, body, target):
    _, url, simulator = server

    assert post(url + "pulse", body) == (200, {"ok": True, "target": target})
    assert simulator.target == target


def test_demo_script_command_starts_the_scripted_run(server):
    _, url, _ = server

    status, answer = post(url + "pulse", {"script": "demo"})

    assert status == 200 and answer["ok"] is True


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ({"preset": "szaleje"}, "nieznany stan sali"),
        ({"target": "dużo"}, "liczbą"),
        ({}, "nieznane polecenie"),
        (b"nie json", "obiektu JSON"),
    ],
)
def test_bad_pulse_commands_get_400(server, body, error):
    _, url, _ = server

    status, answer = post(url + "pulse", body)

    assert status == 400
    assert error in answer["error"]


def test_unknown_page_is_404(server):
    _, url, _ = server

    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(url + "nie-ma", timeout=5)
    with caught.value as error:
        assert error.code == 404


def test_pulse_commands_without_simulator_get_409(scenario):
    panel = PanelServer(PanelState(scenario, PulseSettings()), scenario_graph(scenario), None, PanelSettings(port=0))
    url = panel.start()
    try:
        status, answer = post(url + "pulse", {"target": 100})
    finally:
        panel.stop()

    assert status == 409
    assert "symulator tętna jest wyłączony" in answer["error"]
```

- [ ] **Step 2: Uruchom testy i sprawdź, że padają**

Run: `python -m pytest tests/test_engine_events.py tests/test_panel.py -q`
Expected: FAIL — błąd importu (`ShowObserver` w `bajka.ports`, moduł `bajka.panel`).

- [ ] **Step 3: Kontrakt obserwatora, zdarzenia w silniku i moduł panelu**

<!-- edit: bajka/ports.py -->
Zamień w `bajka/ports.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
```

na:

```python
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
```

<!-- edit: bajka/ports.py -->
Zamień w `bajka/ports.py`:

```python
        """Bieżące średnie tętno sali."""

```

na:

```python
        """Bieżące średnie tętno sali."""


@runtime_checkable
class ShowObserver(Protocol):
    """Obserwator seansu: panel dla jury (bajka/panel.py) dostaje zdarzenia z silnika."""

    def event(self, kind: str, data: Mapping[str, Any]) -> None:
        """Zdarzenie seansu: `scena`, `odniesienie`, `wersja`, `glosy` albo `decyzja` z danymi do pokazania."""

```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python

from bajka.ports import Audience, AudiencePulse, IntentResolver, Interpretation, Listener, Player, ShoutMeter, Voice
```

na:

```python
from typing import Any

from bajka.ports import (
    Audience,
    AudiencePulse,
    IntentResolver,
    Interpretation,
    Listener,
    Player,
    ShoutMeter,
    ShowObserver,
    Voice,
)
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
    ) -> None:
        self._stopped = threading.Event()
```

na:

```python
        observer: ShowObserver | None = None,
    ) -> None:
        self._stopped = threading.Event()
        self._observer = observer  # panel dla jury; jego błędy nigdy nie zatrzymują filmu
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
    def _clip_for(self, scene: Scene) -> Path:
        """Wersja montażu według tętna sali; zwykły klip, gdy tętna nie ma albo sala jest w normie."""
        if not scene.variants or self._pulse is None or self._baseline is None:
            return scene.clip
        bpm = self._read_bpm()
        if bpm is None:
            return scene.clip
        state = hall_state(bpm, self._baseline, self._pulse_settings)
        variant = pick_variant(self._scenario.mood, state)
        chosen = variant if variant in scene.variants else None
        log.info("Tętno sali %.0f (odniesienie %.0f), sala %s: scena %s w wersji %s",
                 bpm, self._baseline, state, scene.id, chosen or "zwykłej")  # fmt: skip
        return scene.variants[chosen] if chosen else scene.clip
```

na:

```python
    def _emit(self, kind: str, **data: Any) -> None:
        if self._observer is None:
            return
        try:
            self._observer.event(kind, data)
        except Exception:
            log.exception("Błąd panelu, film leci dalej")

    def _clip_for(self, scene: Scene) -> tuple[Path, str]:
        """Klip i nazwa wersji według tętna sali; zwykła wersja, gdy tętna nie ma albo sala jest w normie."""
        if not scene.variants or self._pulse is None or self._baseline is None:
            return scene.clip, "zwykla"
        bpm = self._read_bpm()
        if bpm is None:
            return scene.clip, "zwykla"
        state = hall_state(bpm, self._baseline, self._pulse_settings)
        variant = pick_variant(self._scenario.mood, state)
        chosen = variant if variant in scene.variants else "zwykla"
        log.info("Tętno sali %.0f (odniesienie %.0f), sala %s: scena %s w wersji %s",
                 bpm, self._baseline, state, scene.id, chosen)  # fmt: skip
        self._emit("wersja", scene=scene.id, bpm=bpm, baseline=self._baseline, state=state, variant=chosen)
        return scene.variants.get(chosen, scene.clip), chosen
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                self._play(self._clip_for(scene))
```

na:

```python
                clip, variant = self._clip_for(scene)
                self._emit("scena", scene=scene.id, clip=clip.name, variant=variant)
                self._play(clip)
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                    self._baseline = self._read_bpm()  # sala dopiero usiadła
```

na:

```python
                    self._baseline = self._read_bpm()  # sala dopiero usiadła
                    if self._baseline is not None:
                        self._emit("odniesienie", bpm=self._baseline)
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        return self._ask(scene)
```

na:

```python
        return self._ask(scene)

    def _decided(self, scene: Scene, choice: Choice, how: str) -> Choice:
        self._emit("decyzja", scene=scene.id, choice=choice.id, label=choice.display_label, how=how)
        return choice
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
            log.info("Odpowiedzi z telefonów: %d, głosy: %s", len(answers), dict(votes))
```

na:

```python
            log.info("Odpowiedzi z telefonów: %d, głosy: %s", len(answers), dict(votes))
            self._emit("glosy", scene=scene.id, source="telefony", counts={cid: votes[cid] for cid in scene.choices})
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                self._say(personal or choice.reply)
                return choice
```

na:

```python
                self._say(personal or choice.reply)
                return self._decided(scene, choice, "wiekszosc")
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        log.info("Brak decyzji z telefonów, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

```

na:

```python
        log.info("Brak decyzji z telefonów, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return self._decided(scene, default, "domyslna")

```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                self._say(choice.reply)
                return choice
```

na:

```python
                self._say(choice.reply)
                return self._decided(scene, choice, "okrzyk")
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        log.info("Za cicho albo remis, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

```

na:

```python
        log.info("Za cicho albo remis, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return self._decided(scene, default, "domyslna")

```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        log.info("Okrzyki: %s -> %s", ", ".join(f"{k}={v:.0f}" for k, v in levels.items()), winner)
```

na:

```python
        log.info("Okrzyki: %s -> %s", ", ".join(f"{k}={v:.0f}" for k, v in levels.items()), winner)
        self._emit("glosy", scene=scene.id, source="krzykomierz", counts={k: round(v) for k, v in levels.items()})
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
                    return choice
```

na:

```python
                    return self._decided(scene, choice, "odpowiedz")
```

<!-- edit: bajka/engine.py -->
Zamień w `bajka/engine.py`:

```python
        return default
```

na:

```python
        return self._decided(scene, default, "domyslna")
```

<!-- file: bajka/panel.py -->
Utwórz `bajka/panel.py`:

```python
"""Panel dla jury: strona w przeglądarce, która pokazuje drzewo scen, głosy, tętno sali i decyzje filmu.

Silnik wysyła zdarzenia (`bajka.ports.ShowObserver`), `PanelState` trzyma z nich stan w pamięci, a `PanelServer`
serwuje go stronie `bajka/panel_app/index.html`. Z panelu steruje się też symulatorem tętna (`bajka/pulse.py`).
Podgląd bez filmu: python -m bajka.panel SCENARIUSZ (symulator tętna, przebieg demo)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bajka.config import ConfigError, get_int, load_env
from bajka.ports import AudiencePulse, Pulse
from bajka.pulse import PulseSettings, SimulatedPulse, hall_state
from bajka.scenario import Scenario, ScenarioError, load_scenario

log = logging.getLogger(__name__)

APP_DIR = Path(__file__).parent / "panel_app"
HISTORY_SAMPLES = 120  # ostatnie 2 minuty tętna przy próbce co sekundę
LOG_ENTRIES = 20
MAX_COMMAND_BYTES = 1024

HOW = {
    "wiekszosc": "większość głosów z telefonów",
    "okrzyk": "najgłośniejszy okrzyk",
    "odpowiedz": "odpowiedź z mikrofonu",
    "domyslna": "brak decyzji, postać wybrała sama",
}
VERSION = {"spokojna": "spokojnej", "zywa": "żywej", "zwykla": "zwykłej"}


@dataclass(frozen=True)
class PanelSettings:
    host: str = "127.0.0.1"  # 0.0.0.0 udostępnia panel tabletowi jury w tej samej sieci
    port: int = 8090

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> PanelSettings:
        return cls(
            host=env.get("BAJKA_PANEL_HOST") or cls.host,
            port=get_int(env, "BAJKA_PANEL_PORT", cls.port),
        )


def scenario_graph(scenario: Scenario) -> dict[str, Any]:
    """Drzewo scen dla strony panelu: sceny z odległością od startu i krawędzie z nazwami opcji."""
    depth = {scenario.start: 0}
    todo = [scenario.start]
    while todo:  # przeszukiwanie wszerz: najkrótsza droga od sceny startowej
        scene = scenario.scene(todo.pop(0))
        for choice in scene.choices.values():
            if choice.next not in depth:
                depth[choice.next] = depth[scene.id] + 1
                todo.append(choice.next)
    unreachable = max(depth.values()) + 1
    return {
        "start": scenario.start,
        "mood": scenario.mood,
        "scenes": [
            {
                "id": scene.id,
                "depth": depth.get(scene.id, unreachable),
                "question": scene.question,
                "ending": scene.is_ending,
                "variants": list(scene.variants),
            }
            for scene in scenario.scenes.values()
        ],
        "edges": [
            {"from": scene.id, "to": choice.next, "choice": choice.id, "label": choice.display_label}
            for scene in scenario.scenes.values()
            for choice in scene.choices.values()
        ],
    }


class PanelState:
    """Stan seansu dla panelu, budowany ze zdarzeń silnika i próbek tętna; bezpieczny dla wielu wątków."""

    def __init__(
        self, scenario: Scenario, pulse_settings: PulseSettings, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._scenario = scenario
        self._pulse_settings = pulse_settings
        self._clock = clock
        self._started = clock()
        self._lock = threading.Lock()
        self._scene: str | None = None
        self._path: list[dict[str, str]] = []
        self._decisions: list[dict[str, str]] = []
        self._votes: dict[str, Any] | None = None
        self._history: deque[list[float]] = deque(maxlen=HISTORY_SAMPLES)
        self._last: Pulse | None = None
        self._baseline: float | None = None
        self._log: deque[dict[str, str]] = deque(maxlen=LOG_ENTRIES)

    def event(self, kind: str, data: Mapping[str, Any]) -> None:
        handler = getattr(self, f"_on_{kind}", None)
        if handler is None:
            log.debug("Panel pomija nieznane zdarzenie %s", kind)
            return
        with self._lock:
            handler(data)

    def record_pulse(self, reading: Pulse) -> None:
        with self._lock:
            self._last = reading
            self._history.append([round(self._clock() - self._started, 1), reading.bpm])

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            baseline = self._baseline
            bpm = self._last.bpm if self._last else None
            state = hall_state(bpm, baseline, self._pulse_settings) if bpm is not None and baseline else None
            return {
                "scene": self._scene,
                "path": list(self._path),
                "decisions": list(self._decisions),
                "votes": self._votes,
                "pulse": {
                    "history": list(self._history),
                    "bpm": bpm,
                    "viewers": self._last.viewers if self._last else None,
                    "baseline": baseline,
                    "excited": baseline * self._pulse_settings.excited if baseline else None,
                    "bored": baseline * self._pulse_settings.bored if baseline else None,
                    "state": state,
                },
                "log": list(self._log),
            }

    def _say(self, text: str) -> None:
        self._log.append({"time": time.strftime("%H:%M:%S"), "text": text})

    def _on_scena(self, data: Mapping[str, Any]) -> None:
        self._scene = data["scene"]
        self._path.append({"scene": data["scene"], "variant": data["variant"]})
        version = "" if data["variant"] == "zwykla" else f" w wersji {VERSION.get(data['variant'], data['variant'])}"
        self._say(f"Scena {data['scene']}{version}")

    def _on_decyzja(self, data: Mapping[str, Any]) -> None:
        self._decisions.append({key: data[key] for key in ("scene", "choice", "label", "how")})
        self._say(f"Decyzja w scenie {data['scene']}: {data['label']} ({HOW.get(data['how'], data['how'])})")

    def _on_glosy(self, data: Mapping[str, Any]) -> None:
        self._votes = {"scene": data["scene"], "source": data["source"], "counts": dict(data["counts"])}
        choices = self._scenario.scene(data["scene"]).choices
        results = ", ".join(
            f"{choices[cid].display_label if cid in choices else cid} {count}" for cid, count in data["counts"].items()
        )
        self._say(f"Głosy ({data['source']}): {results}")

    def _on_odniesienie(self, data: Mapping[str, Any]) -> None:
        self._baseline = data["bpm"]
        self._say(f"Punkt odniesienia tętna sali: {data['bpm']:.0f}")

    def _on_wersja(self, data: Mapping[str, Any]) -> None:
        version = VERSION.get(data["variant"], data["variant"])
        self._say(
            f"Tętno sali {data['bpm']:.0f} (odniesienie {data['baseline']:.0f}), sala {data['state']}: "
            f"scena {data['scene']} w wersji {version}"
        )


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    state: PanelState
    graph: dict[str, Any]
    pulse: SimulatedPulse | None


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("%s %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html") and (APP_DIR / "index.html").is_file():
            self._send(200, (APP_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/graph":
            self._json(200, self.server.graph)
        elif path == "/state":
            snapshot = self.server.state.snapshot()
            snapshot["pulse"]["target"] = self.server.pulse.target if self.server.pulse else None
            self._json(200, snapshot)
        else:
            self._json(404, {"error": "nie ma takiej strony"})

    def do_POST(self) -> None:
        # Najpierw czytamy treść zapytania: odpowiedź bez jej wczytania Windows kończy zerwaniem połączenia (10053).
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        body = self.rfile.read(length) if 0 < length <= MAX_COMMAND_BYTES else b""
        if urlparse(self.path).path != "/pulse":
            self._json(404, {"error": "nie ma takiej strony"})
            return
        pulse = self.server.pulse
        if pulse is None:
            self._json(409, {"error": "symulator tętna jest wyłączony"})
            return
        try:
            if not body:
                self.close_connection = True  # nieprzeczytana treść: nie używamy dalej tego połączenia
                raise ValueError("puste albo za długie polecenie")
            command = json.loads(body)
            if not isinstance(command, dict):
                raise ValueError("oczekiwano obiektu JSON")
            self._apply(pulse, command)
        except ValueError as exc:  # json.JSONDecodeError też jest ValueError
            message = "oczekiwano obiektu JSON" if isinstance(exc, json.JSONDecodeError) else str(exc)
            self._json(400, {"error": message})
            return
        self._json(200, {"ok": True, "target": pulse.target})

    @staticmethod
    def _apply(pulse: SimulatedPulse, command: dict[str, Any]) -> None:
        if "target" in command:
            try:
                target = float(command["target"])
            except (TypeError, ValueError):
                raise ValueError("'target' musi być liczbą uderzeń na minutę") from None
            pulse.set_target(target)
        elif "preset" in command:
            pulse.preset(str(command["preset"]))
        elif command.get("script") == "demo":
            pulse.play_script()
        else:
            raise ValueError("nieznane polecenie; dostępne: target, preset, script")

    def _json(self, code: int, data: Any) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class PanelServer:
    """Serwer panelu w wątku w tle; co `sample_every_s` zapisuje próbkę tętna (wykres żyje w trakcie klipów)."""

    def __init__(
        self,
        state: PanelState,
        graph: dict[str, Any],
        pulse: SimulatedPulse | None,
        settings: PanelSettings,
        sample_every_s: float = 1.0,
    ) -> None:
        self._state = state
        self._graph = graph
        self._pulse = pulse
        self._settings = settings
        self._sample_every_s = sample_every_s
        self._server: _Server | None = None
        self._stopped = threading.Event()

    def start(self) -> str:
        server = _Server((self._settings.host, self._settings.port), _Handler)
        server.state, server.graph, server.pulse = self._state, self._graph, self._pulse
        serve = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, name="bajka-panel-server")
        serve.daemon = True
        serve.start()
        if self._pulse is not None:
            threading.Thread(target=self._sample, args=(self._pulse,), name="bajka-panel-tetno", daemon=True).start()
        self._server = server
        # 127.0.0.1, nie localhost: na Windows localhost najpierw próbuje IPv6 i każde odświeżenie czeka.
        host = "127.0.0.1" if self._settings.host == "0.0.0.0" else self._settings.host
        url = f"http://{host}:{server.server_address[1]}/"
        log.info("Panel dla jury: %s", url)
        if self._settings.host == "0.0.0.0":
            log.info("Na tablecie jury w tej samej sieci: adres IP tego komputera, port %d", server.server_address[1])
        return url

    def stop(self) -> None:
        self._stopped.set()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

    def _sample(self, pulse: AudiencePulse) -> None:
        while not self._stopped.is_set():
            try:
                self._state.record_pulse(pulse.read())
            except Exception:
                log.exception("Błąd odczytu tętna dla panelu")
            self._stopped.wait(self._sample_every_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.panel", description="Podgląd panelu dla jury bez filmu.")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        scenario = load_scenario(args.scenario)
        env = load_env()
        pulse_settings = PulseSettings.from_env(env)
        settings = PanelSettings.from_env(env)
    except (ScenarioError, ConfigError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    simulator = SimulatedPulse(pulse_settings)
    state = PanelState(scenario, pulse_settings)
    server = PanelServer(state, scenario_graph(scenario), simulator, settings)
    try:
        url = server.start()
    except OSError as exc:
        print(f"Nie udało się uruchomić panelu: {exc}", file=sys.stderr)
        return 2
    print(f"Panel: {url} — Ctrl+C kończy. Scena startowa i punkt odniesienia tętna są już na panelu.")
    start = scenario.scene(scenario.start)
    state.event("scena", {"scene": start.id, "clip": start.clip.name, "variant": "zwykla"})
    state.event("odniesienie", {"bpm": simulator.read().bpm})
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_engine_events.py tests/test_panel.py tests/test_engine.py tests/test_engine_pulse.py tests/test_vote.py -q`
Expected: PASS, a `tests/test_panel.py` w kilka sekund (adres `127.0.0.1`, nie `localhost`: na Windows `localhost` najpierw próbuje IPv6 i każde zapytanie czeka).

- [ ] **Step 5: Pełny zestaw testów**

Run: `python -m pytest -q`
Expected: `299 passed, 1 skipped`.

<!-- checkpoint -->

- [ ] **Step 6: Commit**

```bash
git add bajka/ports.py bajka/engine.py bajka/panel.py tests/test_engine_events.py tests/test_panel.py
git commit -m "feat: silnik opowiada panelowi o scenach, tętnie, głosach i decyzjach; serwer panelu z symulatorem"
```

---

### Task 5: Strona panelu dla jury

**Files:**
- Create: `bajka/panel_app/index.html`
- Test: `tests/test_panel.py`

**Interfaces:**
- Consumes: z Task 4 trasy `GET /graph`, `GET /state` (z `pulse.target`), `POST /pulse` z `{"target": liczba}`, `{"preset": nazwa}` albo `{"script": "demo"}`.
- Produces: strona `bajka/panel_app/index.html`: drzewo scen (SVG, od góry do dołu), wykres tętna z linią odniesienia i pasmem normy, słupki głosów, dziennik decyzji, symulator (suwak 60–160, przyciski stanów, „Przebieg demo”); elementy `id="tree-svg"`, `id="chart"`, `id="votes"`, `id="log"`, `id="slider"`, `data-preset="…"`.

- [ ] **Step 1: Test strony**

<!-- edit: tests/test_panel.py -->
Zamień w `tests/test_panel.py`:

```python

def test_unknown_page_is_404(server):
```

na:

```python

def test_panel_page_works_offline_and_has_all_sections(server):
    _, url, _ = server

    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/html")
        page = response.read().decode("utf-8")

    assert "<title>Film, który czuje salę" in page
    sections = ('id="tree-svg"', 'id="chart"', 'id="votes"', 'id="log"', 'id="slider"', 'data-preset="ekscytuje-sie"')
    for element in sections:
        assert element in page
    assert "<link" not in page and 'src="http' not in page  # bez internetu na sali: żadnych zewnętrznych plików


def test_unknown_page_is_404(server):
```

- [ ] **Step 2: Uruchom test i sprawdź, że pada**

Run: `python -m pytest tests/test_panel.py::test_panel_page_works_offline_and_has_all_sections -q`
Expected: FAIL — `HTTPError 404` (strony jeszcze nie ma).

- [ ] **Step 3: Strona panelu**

<!-- file: bajka/panel_app/index.html -->
Utwórz `bajka/panel_app/index.html`:

```html
<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Film, który czuje salę — panel</title>
<style>
  :root {
    --bg: #0e1120;
    --card: #171b2e;
    --line: #2a3050;
    --text: #eef0fa;
    --muted: #9aa1bd;
    --honey: #ffc94d;
    --calm: #5ec8ff;
    --excited: #ff7a59;
    --normal: #59d98e;
    --bored: #a98bff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font: 15px/1.45 system-ui, "Segoe UI", sans-serif;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 20px;
    padding: 18px 24px 6px;
  }
  h1 { margin: 0; font-size: 24px; letter-spacing: 0.2px; }
  h1 span { color: var(--honey); }
  .subtitle { color: var(--muted); }
  #connection { margin-left: auto; color: var(--muted); font-size: 13px; }
  #connection.offline { color: var(--excited); }
  main {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(320px, 2fr);
    gap: 16px;
    padding: 12px 24px 24px;
  }
  .column { display: grid; gap: 16px; align-content: start; min-width: 0; }
  section {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px 16px;
    min-width: 0;
  }
  h2 {
    margin: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--muted);
  }
  #tree svg { width: 100%; height: auto; display: block; margin: 0 auto; }
  .node rect { fill: #1e2340; stroke: var(--line); stroke-width: 1.5; }
  .node text { fill: var(--muted); font-size: 13px; }
  .node.visited rect { fill: #2a2f52; stroke: #6c7397; }
  .node.visited text { fill: var(--text); }
  .node.current rect { fill: #3b3214; stroke: var(--honey); stroke-width: 2.5; }
  .node.current text { fill: var(--honey); font-weight: 700; }
  .node .badge { fill: var(--calm); font-size: 11px; }
  .edge path { fill: none; stroke: #39406a; stroke-width: 1.5; }
  .edge text { fill: #6c7397; font-size: 11px; }
  .edge.taken path { stroke: var(--honey); stroke-width: 3; }
  .edge.taken text { fill: var(--honey); font-weight: 600; }
  .legend { display: flex; flex-wrap: wrap; gap: 14px; color: var(--muted); font-size: 12px; margin-top: 8px; }
  .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }
  .pulse-head { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
  #bpm { font-size: 44px; font-weight: 700; font-variant-numeric: tabular-nums; }
  #bpm small { font-size: 15px; color: var(--muted); font-weight: 400; }
  .chip { padding: 4px 12px; border-radius: 999px; font-weight: 600; background: #252a45; color: var(--muted); }
  .chip.excited { background: rgba(255, 122, 89, 0.18); color: var(--excited); }
  .chip.normal { background: rgba(89, 217, 142, 0.15); color: var(--normal); }
  .chip.bored { background: rgba(169, 139, 255, 0.18); color: var(--bored); }
  #pulse-meta { color: var(--muted); font-size: 13px; }
  #chart { width: 100%; height: 170px; display: block; margin-top: 8px; }
  .votes { display: grid; gap: 8px; }
  .vote { display: grid; grid-template-columns: 130px 1fr 44px; gap: 10px; align-items: center; }
  .vote .bar { height: 14px; border-radius: 7px; background: #252a45; overflow: hidden; }
  .vote .bar div { height: 100%; background: var(--honey); border-radius: 7px; transition: width 0.4s; }
  .vote .count { text-align: right; font-variant-numeric: tabular-nums; }
  .empty { color: var(--muted); font-style: italic; }
  .controls { display: grid; gap: 10px; }
  .slider { display: flex; align-items: center; gap: 12px; }
  .slider input { flex: 1; accent-color: var(--honey); }
  #target { width: 72px; text-align: right; font-variant-numeric: tabular-nums; }
  .buttons { display: flex; flex-wrap: wrap; gap: 8px; }
  button {
    background: #252a45;
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 8px 12px;
    font: inherit;
    cursor: pointer;
  }
  button:hover { border-color: var(--honey); }
  button.primary { background: var(--honey); color: #1b1503; border-color: var(--honey); font-weight: 600; }
  .note { color: var(--muted); font-size: 12px; }
  #log { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; max-height: 280px; overflow: auto; }
  #log li { display: grid; grid-template-columns: 70px 1fr; gap: 8px; }
  #log time { color: var(--muted); font-variant-numeric: tabular-nums; }
  #log li:first-child { color: var(--honey); }
  @media (max-width: 900px) {
    main { grid-template-columns: 1fr; padding: 12px 16px 24px; }
    header { padding: 16px 16px 4px; }
  }
</style>
</head>
<body>
<header>
  <h1>Film, który <span>czuje salę</span></h1>
  <div class="subtitle" id="mood">Drzewo scen, głosy widowni i tętno sali na żywo</div>
  <div id="connection">łączenie z filmem…</div>
</header>
<main>
  <div class="column">
    <section id="tree">
      <h2>Drzewo scen</h2>
      <svg id="tree-svg" role="img" aria-label="Drzewo scen filmu"></svg>
      <div class="legend">
        <span><i style="background:#3b3214;border:2px solid var(--honey)"></i>teraz na ekranie</span>
        <span><i style="background:#2a2f52"></i>już obejrzane</span>
        <span><i style="background:#1e2340;border:1px solid var(--line)"></i>przed nami</span>
        <span><i style="background:var(--honey)"></i>wybrana ścieżka</span>
        <span style="color:var(--calm)">≈ scena ma wersję spokojniejszą</span>
      </div>
    </section>
    <section>
      <h2>Dlaczego film zrobił to, co zrobił</h2>
      <ul id="log"><li class="empty">Czekam na pierwszą scenę…</li></ul>
    </section>
  </div>
  <div class="column">
    <section>
      <h2>Tętno sali</h2>
      <div class="pulse-head">
        <div id="bpm">–<small> uderzeń/min</small></div>
        <div class="chip" id="state">brak danych</div>
      </div>
      <div id="pulse-meta">Punkt odniesienia pojawi się po pierwszej scenie.</div>
      <svg id="chart" viewBox="0 0 600 170" preserveAspectRatio="none" aria-label="Wykres tętna sali"></svg>
    </section>
    <section>
      <h2 id="votes-title">Głosy widowni</h2>
      <div class="votes" id="votes"><div class="empty">Jeszcze nikt nie głosował.</div></div>
    </section>
    <section>
      <h2>Symulator tętna (demo)</h2>
      <div class="controls">
        <div class="slider">
          <input type="range" id="slider" min="60" max="160" step="1" value="90" aria-label="Tętno docelowe">
          <output id="target">90</output>
        </div>
        <div class="buttons">
          <button data-preset="spokojna">Spokojna sala</button>
          <button data-preset="ekscytuje-sie">Sala się ekscytuje</button>
          <button data-preset="nudzi-sie">Sala się nudzi</button>
          <button class="primary" id="script">▶ Przebieg demo</button>
        </div>
        <div class="note">
          Dane symulowane, żadne prawdziwe tętno. W przyszłości zegarki widzów, tylko średnia całej sali,
          za zgodą opiekunów i bez zapisywania.
        </div>
      </div>
    </section>
  </div>
</main>
<script>
"use strict";
const SVG = "http://www.w3.org/2000/svg";
const HOW = { wiekszosc: "telefony", okrzyk: "okrzyk", odpowiedz: "mikrofon", domyslna: "sama" };
const SOURCE = { telefony: "z telefonów", krzykomierz: "z krzykomierza" };
const STATE_CLASS = { pobudzona: "excited", "w normie": "normal", znudzona: "bored" };
let graph = null;

function el(name, attrs, text) {
  const node = document.createElementNS(SVG, name);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

async function getJSON(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(response.status);
  return response.json();
}

function layout(g) {
  // Od góry do dołu: rząd = odległość sceny od startu, sceny w rzędzie obok siebie.
  const rows = new Map();
  for (const scene of g.scenes) {
    if (!rows.has(scene.depth)) rows.set(scene.depth, []);
    rows.get(scene.depth).push(scene);
  }
  const widest = Math.max(...[...rows.values()].map((r) => r.length));
  const nodeW = 132, nodeH = 38, gapX = 40, rowHeight = 66, margin = 170;  // margines na podpisy krawędzi
  const inner = Math.max(widest, 2) * (nodeW + gapX);
  const width = inner + 2 * margin;
  const positions = {};
  for (const [depth, scenes] of rows) {
    scenes.forEach((scene, i) => {
      const x = margin + (inner / (scenes.length + 1)) * (i + 1);
      positions[scene.id] = { x: x - nodeW / 2, y: 12 + depth * rowHeight, w: nodeW, h: nodeH };
    });
  }
  return { positions, width, height: 12 + rows.size * rowHeight };
}

function renderTree(state) {
  const svg = document.getElementById("tree-svg");
  const { positions, width, height } = layout(graph);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.style.maxWidth = `${Math.round(width * 1.15)}px`;
  svg.replaceChildren();
  const visited = new Set(state.path.map((p) => p.scene));
  const taken = new Map(state.decisions.map((d) => [`${d.scene}>${d.choice}`, d]));
  const groups = new Map();
  for (const edge of graph.edges) {
    const key = `${edge.from}>${edge.to}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(edge);
  }
  for (const edges of groups.values()) {
    const a = positions[edges[0].from], b = positions[edges[0].to];
    const chosen = edges.map((e) => taken.get(`${e.from}>${e.choice}`)).find(Boolean);
    const x1 = a.x + a.w / 2, y1 = a.y + a.h, x2 = b.x + b.w / 2, y2 = b.y, mid = (y1 + y2) / 2;
    const group = el("g", { class: chosen ? "edge taken" : "edge" });
    group.append(el("path", { d: `M${x1},${y1} C${x1},${mid} ${x2},${mid} ${x2},${y2}` }));
    const label = chosen ? `${chosen.label} · ${HOW[chosen.how] || chosen.how}` : edges.map((e) => e.label).join(" / ");
    // Podpis na zewnątrz: scena po lewej stronie drzewa → w lewo, po prawej → w prawo.
    const leftward = x1 < width / 2 - 1 || (Math.abs(x1 - width / 2) <= 1 && x2 < x1);
    const lx = (x1 + x2) / 2 + (leftward ? -8 : 8);
    group.append(el("text", { x: lx, y: mid + 4, "text-anchor": leftward ? "end" : "start" }, shorten(label, 28)));
    svg.append(group);
  }
  for (const scene of graph.scenes) {
    const p = positions[scene.id];
    const kind = scene.id === state.scene ? "current" : visited.has(scene.id) ? "visited" : "";
    const group = el("g", { class: `node ${kind}` });
    group.append(el("title", {}, scene.question || (scene.ending ? "zakończenie" : scene.id)));
    group.append(el("rect", { x: p.x, y: p.y, width: p.w, height: p.h, rx: 10 }));
    group.append(el("text", { x: p.x + p.w / 2, y: p.y + p.h / 2 + 5, "text-anchor": "middle" }, shorten(scene.id, 15)));
    if (scene.variants.length) group.append(el("text", { x: p.x + p.w - 10, y: p.y + 13, class: "badge" }, "≈"));
    svg.append(group);
  }
}

function shorten(text, max) {
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}

function renderPulse(pulse) {
  const bpm = document.getElementById("bpm");
  bpm.firstChild.textContent = pulse.bpm == null ? "–" : Math.round(pulse.bpm);
  const chip = document.getElementById("state");
  chip.textContent = pulse.state ? `sala ${pulse.state}` : "brak punktu odniesienia";
  chip.className = `chip ${STATE_CLASS[pulse.state] || ""}`;
  const meta = document.getElementById("pulse-meta");
  meta.textContent = pulse.baseline == null
    ? "Punkt odniesienia pojawi się po pierwszej scenie."
    : `Odniesienie ${Math.round(pulse.baseline)} · norma ${Math.round(pulse.bored)}–${Math.round(pulse.excited)}`
      + ` · widzów ${pulse.viewers ?? "–"} · cel symulatora ${pulse.target == null ? "–" : Math.round(pulse.target)}`;
  const slider = document.getElementById("slider");
  if (pulse.target != null && document.activeElement !== slider) {  // przebieg demo też przesuwa suwak
    slider.value = Math.round(pulse.target);
    document.getElementById("target").textContent = Math.round(pulse.target);
  }
  renderChart(pulse);
}

function renderChart(pulse) {
  const svg = document.getElementById("chart");
  svg.replaceChildren();
  const points = pulse.history;
  if (!points.length) return;
  const W = 600, H = 170, pad = 8;
  const tEnd = points[points.length - 1][0];
  const span = Math.min(120, Math.max(10, tEnd - points[0][0]));  // na początku wykres i tak wypełnia szerokość
  const tStart = tEnd - span;
  const values = points.map((p) => p[1]).concat(pulse.baseline ? [pulse.bored, pulse.excited] : []);
  const low = Math.min(...values) - 6, high = Math.max(...values) + 6;
  const x = (t) => ((t - tStart) / span) * W;
  const y = (v) => H - pad - ((v - low) / (high - low)) * (H - 2 * pad);
  if (pulse.baseline) {
    svg.append(el("rect", {
      x: 0, y: y(pulse.excited), width: W, height: y(pulse.bored) - y(pulse.excited),
      fill: "rgba(89,217,142,0.08)",
    }));
    svg.append(el("line", {
      x1: 0, x2: W, y1: y(pulse.baseline), y2: y(pulse.baseline),
      stroke: "#59d98e", "stroke-dasharray": "6 6", "stroke-width": 1.5,
    }));
    svg.append(el("line", {
      x1: 0, x2: W, y1: y(pulse.excited), y2: y(pulse.excited),
      stroke: "rgba(255,122,89,0.6)", "stroke-dasharray": "2 6", "stroke-width": 1.5,
    }));
  }
  const d = points.filter((p) => p[0] >= tStart).map((p, i) => `${i ? "L" : "M"}${x(p[0])},${y(p[1])}`).join(" ");
  svg.append(el("path", { d, fill: "none", stroke: "#ffc94d", "stroke-width": 3, "stroke-linejoin": "round" }));
}

function renderVotes(votes) {
  const box = document.getElementById("votes");
  if (!votes) return;
  document.getElementById("votes-title").textContent =
    `Głosy widowni ${SOURCE[votes.source] || ""} — scena ${votes.scene}`;
  const labels = Object.fromEntries(graph.edges.filter((e) => e.from === votes.scene).map((e) => [e.choice, e.label]));
  const total = Object.values(votes.counts).reduce((a, b) => a + b, 0) || 1;
  box.replaceChildren(...Object.entries(votes.counts).map(([choice, count]) => {
    const row = document.createElement("div");
    row.className = "vote";
    const name = document.createElement("div");
    name.textContent = labels[choice] || choice;
    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("div");
    fill.style.width = `${(100 * count) / total}%`;
    bar.append(fill);
    const number = document.createElement("div");
    number.className = "count";
    number.textContent = count;
    row.append(name, bar, number);
    return row;
  }));
}

function renderLog(entries) {
  if (!entries.length) return;
  const list = document.getElementById("log");
  list.replaceChildren(...entries.slice().reverse().map((entry) => {
    const item = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = entry.time;
    const text = document.createElement("span");
    text.textContent = entry.text;
    item.append(time, text);
    return item;
  }));
}

async function refresh() {
  const connection = document.getElementById("connection");
  try {
    if (!graph) {
      graph = await getJSON("graph");
      document.getElementById("mood").textContent = graph.mood
        ? `Film ${graph.mood}: gdy sala odbiega od nastroju filmu, scena gra inną wersję montażu`
        : "Film bez nastroju (mood): wersje scen wyłączone";
    }
    const state = await getJSON("state");
    renderTree(state);
    renderPulse(state.pulse);
    renderVotes(state.votes);
    renderLog(state.log);
    connection.textContent = "połączono z filmem";
    connection.className = "";
  } catch (error) {
    connection.textContent = "brak połączenia z filmem — czy aplikacja działa z flagą --panel?";
    connection.className = "offline";
  }
}

async function command(body) {
  try {
    const response = await fetch("pulse", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const answer = await response.json();
    if (answer.target != null) {
      document.getElementById("slider").value = Math.round(answer.target);
      document.getElementById("target").textContent = Math.round(answer.target);
    }
  } catch (error) {
    document.getElementById("connection").textContent = "nie udało się wysłać polecenia do symulatora";
  }
}

const slider = document.getElementById("slider");
let sliderTimer = null;
slider.addEventListener("input", () => {
  document.getElementById("target").textContent = slider.value;
  clearTimeout(sliderTimer);
  sliderTimer = setTimeout(() => command({ target: Number(slider.value) }), 150);
});
for (const button of document.querySelectorAll("[data-preset]")) {
  button.addEventListener("click", () => command({ preset: button.dataset.preset }));
}
document.getElementById("script").addEventListener("click", () => command({ script: "demo" }));

refresh();
setInterval(refresh, 500);
</script>
</body>
</html>
```

- [ ] **Step 4: Uruchom testy i obejrzyj panel**

Run: `python -m pytest tests/test_panel.py -q`
Expected: `23 passed`.

Run: `python -m bajka.panel scenarios/klub_ciekawskich.yaml` i otwórz w przeglądarce adres z konsoli.
Expected: drzewo scen od `powitanie` do dwóch zakończeń (scena `powitanie` podświetlona), punkt odniesienia w dzienniku, wykres tętna rusza się co sekundę, „Sala się ekscytuje” podnosi wykres ponad pasmo normy, a stan sali zmienia się na „sala pobudzona”. Ctrl+C kończy.

- [ ] **Step 5: Pełny zestaw testów**

Run: `python -m pytest -q`
Expected: `300 passed, 1 skipped`.

<!-- checkpoint -->

- [ ] **Step 6: Commit**

```bash
git add bajka/panel_app/index.html tests/test_panel.py
git commit -m "feat: strona panelu dla jury — drzewo scen, głosy, tętno sali i dziennik decyzji"
```

---

### Task 6: Uruchomienie z panelem, dokumenty i przebieg pokazu

**Files:**
- Create: `docs/DEMO_DLA_JURY.md`
- Modify: `bajka/app.py`, `.env.example`, `README.md`, `docs/ONBOARDING.md`, `docs/PODZIAL_PRACY.md`, `docs/ZGODNOSC_Z_REGULAMINEM.md`, `docs/DO_ZROBIENIA.md`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: z Task 2–4 `PulseSettings`, `SimulatedPulse`, `PanelSettings`, `PanelState`, `PanelServer`, `scenario_graph`; `StoryEngine(..., pulse=, pulse_settings=, observer=)`.
- Produces: w `bajka/app.py` flaga `--panel`; `panel_enabled(args, env) -> bool`; `Panel(server, state, pulse, pulse_settings)` (frozen dataclass); `build_panel(env, scenario) -> Panel`; w `main()` panel startuje po aplikacji mobilnej, silnik dostaje `pulse`, `pulse_settings`, `observer`, a po filmie `panel.server.stop()`.

- [ ] **Step 1: Testy flagi i okablowania**

<!-- edit: tests/test_app.py -->
Zamień w `tests/test_app.py`:

```python
import threading
```

na:

```python
import threading
from dataclasses import replace
from types import SimpleNamespace
```

<!-- edit: tests/test_app.py -->
Zamień w `tests/test_app.py`:

```python
from bajka.app import build_meter, build_resolver, choose_backend, main, mobile_enabled, parse_args, run_window
from bajka.config import ConfigError
from bajka.keywords import KeywordIntentResolver
```

na:

```python
from bajka.app import (
    build_meter,
    build_panel,
    build_resolver,
    choose_backend,
    main,
    mobile_enabled,
    panel_enabled,
    parse_args,
    run_window,
)
from bajka.config import ConfigError
from bajka.keywords import KeywordIntentResolver
from bajka.ports import AudiencePulse, ShowObserver
from bajka.pulse import PulseSettings
```

<!-- edit: tests/test_app.py -->
Zamień w `tests/test_app.py`:

```python
    assert events == ["silnik zatrzymany", "odtwarzacz zatrzymany", "okno zamknięte"]

```

na:

```python
    assert events == ["silnik zatrzymany", "odtwarzacz zatrzymany", "okno zamknięte"]


# Panel dla jury i tętno sali


def test_panel_is_enabled_by_flag_or_env():
    assert not panel_enabled(parse_args(["b.yaml"]), {})
    assert panel_enabled(parse_args(["b.yaml", "--panel"]), {})
    assert panel_enabled(parse_args(["b.yaml"]), {"BAJKA_PANEL": "tak"})


def test_build_panel_connects_pulse_simulator_and_panel_state(scenario):
    panel = build_panel({"BAJKA_PULSE_START_BPM": "80"}, scenario)

    assert isinstance(panel.pulse, AudiencePulse)
    assert isinstance(panel.state, ShowObserver)
    assert panel.pulse_settings.start_bpm == 80.0
    assert panel.pulse.read().bpm == pytest.approx(80.0, abs=2)


def run_main_with_spies(tmp_path, monkeypatch, scenario_dict, *flags):
    monkeypatch.chdir(tmp_path)
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)
    created, events = {}, []

    class SpyEngine:
        def __init__(self, *args, **kwargs):
            created.update(kwargs)

    class SpyServer:
        def start(self):
            events.append("panel uruchomiony")
            return "http://127.0.0.1:8090/"

        def stop(self):
            events.append("panel zatrzymany")

    real_build_panel = build_panel
    monkeypatch.setattr("bajka.app.build_panel", lambda env, s: replace(real_build_panel(env, s), server=SpyServer()))
    monkeypatch.setattr("bajka.app.StoryEngine", SpyEngine)
    monkeypatch.setattr("bajka.app.run_window", lambda root, player, engine: events.append("film"))
    monkeypatch.setattr("tkinter.Tk", lambda: object())  # bez okna i bez VLC
    monkeypatch.setitem(sys.modules, "bajka.player", SimpleNamespace(VlcPlayer=lambda root, fullscreen=True: object()))

    assert main([str(path), "--text", "--no-llm", "--windowed", *flags]) == 0
    return created, events


def test_main_with_panel_starts_it_and_gives_pulse_and_observer_to_the_engine(tmp_path, monkeypatch, scenario_dict):
    created, events = run_main_with_spies(tmp_path, monkeypatch, scenario_dict, "--panel")

    assert events == ["panel uruchomiony", "film", "panel zatrzymany"]
    assert isinstance(created["pulse"], AudiencePulse)
    assert isinstance(created["observer"], ShowObserver)
    assert created["pulse_settings"] == PulseSettings()


def test_main_without_panel_runs_the_film_without_pulse(tmp_path, monkeypatch, scenario_dict):
    created, events = run_main_with_spies(tmp_path, monkeypatch, scenario_dict)

    assert events == ["film"]
    assert created["pulse"] is None and created["observer"] is None

```

- [ ] **Step 2: Uruchom testy i sprawdź, że padają**

Run: `python -m pytest tests/test_app.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_panel' from 'bajka.app'`.

- [ ] **Step 3: Flaga `--panel` w aplikacji i ustawienia panelu**

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
from collections.abc import Mapping
```

na:

```python
from collections.abc import Mapping
from dataclasses import dataclass
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
from bajka.scenario import ScenarioError, load_scenario, missing_media
```

na:

```python
from bajka.scenario import Scenario, ScenarioError, load_scenario, missing_media
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
    from bajka.mobile import MobileServer
```

na:

```python
    from bajka.mobile import MobileServer
    from bajka.panel import PanelServer, PanelState
    from bajka.pulse import PulseSettings, SimulatedPulse
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        help="odpowiedzi widowni z aplikacji mobilnej (mikrofony telefonów); także BAJKA_MOBILE=1 w .env",
```

na:

```python
        help="odpowiedzi widowni z aplikacji mobilnej (mikrofony telefonów); także BAJKA_MOBILE=1 w .env",
    )
    parser.add_argument(
        "--panel",
        action="store_true",
        help="panel dla jury w przeglądarce i symulator tętna sali (wersje scen według tętna); także BAJKA_PANEL=1",
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python

def build_mobile(env: Mapping[str, str], backend: str, resolver: IntentResolver) -> MobileServer:
```

na:

```python

def panel_enabled(args: argparse.Namespace, env: Mapping[str, str]) -> bool:
    return args.panel or (env.get("BAJKA_PANEL") or "0").strip().lower() in ("1", "tak", "true")


@dataclass(frozen=True)
class Panel:
    """Panel dla jury z symulatorem tętna sali: silnik dostaje tętno i opowiada panelowi, co robi."""

    server: PanelServer
    state: PanelState
    pulse: SimulatedPulse
    pulse_settings: PulseSettings


def build_panel(env: Mapping[str, str], scenario: Scenario) -> Panel:
    from bajka.panel import PanelServer, PanelSettings, PanelState, scenario_graph
    from bajka.pulse import PulseSettings, SimulatedPulse

    pulse_settings = PulseSettings.from_env(env)
    pulse = SimulatedPulse(pulse_settings)
    state = PanelState(scenario, pulse_settings)
    server = PanelServer(state, scenario_graph(scenario), pulse, PanelSettings.from_env(env))
    return Panel(server=server, state=state, pulse=pulse, pulse_settings=pulse_settings)


def build_mobile(env: Mapping[str, str], backend: str, resolver: IntentResolver) -> MobileServer:
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        log.info("Tryb: %s%s", backend, ", bez modelu językowego" if args.no_llm else "")
```

na:

```python
        log.info("Tryb: %s%s", backend, ", bez modelu językowego" if args.no_llm else "")
        panel = build_panel(env, scenario) if panel_enabled(args, env) else None  # tylko ustawienia, bez sieci
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        log.info("Widzowie: otwórzcie %s w telefonie. Kod QR na ekran kina: %sqr", url, url)
```

na:

```python
        log.info("Widzowie: otwórzcie %s w telefonie. Kod QR na ekran kina: %sqr", url, url)
    if panel is not None:
        try:
            url = panel.server.start()
        except OSError as exc:
            log.error("Nie udało się uruchomić panelu dla jury: %s", exc)
            if mobile is not None:
                mobile.stop()
            return 2
        log.info("Panel dla jury: otwórzcie %s w przeglądarce (ten komputer albo tablet jury)", url)
        if not scenario.mood:
            log.info("Scenariusz nie ma pola 'mood': panel pokazuje drzewo i głosy, a sceny grają zwykłe wersje")
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
        audience=audience,
```

na:

```python
        audience=audience,
        pulse=panel.pulse if panel else None,
        pulse_settings=panel.pulse_settings if panel else None,
        observer=panel.state if panel else None,
```

<!-- edit: bajka/app.py -->
Zamień w `bajka/app.py`:

```python
            mobile.stop()
    return 0
```

na:

```python
            mobile.stop()
        if panel is not None:
            panel.server.stop()
    return 0
```

<!-- edit: .env.example -->
Zamień w `.env.example`:

```text
BAJKA_PULSE_BORED=0.97

```

na:

```text
BAJKA_PULSE_BORED=0.97

# --- bajka/panel.py: panel dla jury w przeglądarce (flaga --panel albo BAJKA_PANEL=1) ---
BAJKA_PANEL=0
# 127.0.0.1 = tylko ten komputer; 0.0.0.0 = także tablet jury w tej samej sieci Wi-Fi
BAJKA_PANEL_HOST=127.0.0.1
BAJKA_PANEL_PORT=8090

```

- [ ] **Step 4: Uruchom testy**

Run: `python -m pytest tests/test_app.py -q`
Expected: `16 passed`.

- [ ] **Step 5: Dokumenty i przebieg pokazu dla jury**

<!-- file: docs/DEMO_DLA_JURY.md -->
Utwórz `docs/DEMO_DLA_JURY.md`:

````markdown
# Pokaz dla jury: film, który słucha i czuje salę

Prezentacja: **18.10.2026, 19:00**. Pokaz trwa około 3 minut i działa na jednym laptopie, bez internetu.
Jury jest widownią: mówi do swoich telefonów, a jedna osoba steruje tętnem sali na panelu.

## Przygotowanie (przed wejściem jury)

1. Klipy na miejscu: prawdziwe albo zastępcze z nazwą pliku na planszy
   (`python -m bajka.placeholders scenarios/klub_ciekawskich.yaml`).
2. Laptop i telefony w tej samej sieci Wi-Fi, port aplikacji mobilnej (8443) otwarty w zaporze Windows.
3. Start bajki z telefonami i panelem:

   ```powershell
   python -m bajka scenarios/klub_ciekawskich.yaml --mobile --panel
   ```

   Próba bez mikrofonu i bez telefonów: `python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed --panel`.
4. Panel otwarty w przeglądarce (adres w konsoli, domyślnie `http://127.0.0.1:8090/`) na ekranie laptopa albo
   na tablecie jury (`BAJKA_PANEL_HOST=0.0.0.0` w `.env`, adres IP laptopa i port 8090).
5. Na ekranie kina plansza z kodem QR (adres z konsoli z dopiskiem `qr`).

## Przebieg (około 3 minut)

| Czas | Co się dzieje | Co mówimy |
|---|---|---|
| 0:00–0:30 | Jury skanuje kod QR i dołącza telefonami | „To kino, które słucha widowni i czuje salę. Wy jesteście dziś widownią.” |
| 0:30–1:15 | Lila pyta, jury odpowiada do telefonów. Na panelu rosną słupki głosów, a w drzewie scen podświetla się wybrana ścieżka | „Każdy mówi do swojego telefonu, a komputer w kinie liczy głosy całej sali. Wygrywa większość.” |
| 1:15–2:15 | Przed sceną `wiaterek` ktoś z jury klika „Sala się ekscytuje” (albo wcześniej „Przebieg demo”). Wykres tętna wychodzi ponad normę, scena gra wersję spokojną, a dziennik pisze dlaczego | „Film jest spokojny, a sala się rozkręciła. Dlatego ta scena ma wolniejszy montaż i dłuższe ujęcia.” |
| 2:15–3:00 | Panel zostaje na ekranie | Wizja: zegarki widzów, tylko średnia sali, zgoda opiekunów, nic nie jest zapisywane. Twórcy filmu dostają mapę emocji widowni. Kinoautomat z 1967 roku dał widzom przyciski; my dajemy im głos i puls |

Scena `wiaterek` jest zawsze na ścieżce, więc to najpewniejsze miejsce na pokazanie wersji spokojnej.
Spokojne wersje mają też `las` (jeśli widownia go wybierze) i `swieto`.

## Gdy coś nie działa

- **Telefony się nie łączą:** bajka sama słucha sali; decyzje rozstrzyga krzykomierz („Krzyczymy: LAS!”).
- **Panel się nie odświeża:** film leci dalej, błędy panelu nigdy go nie zatrzymują. Wystarczy odświeżyć stronę.
- **Brak internetu:** nic nie szkodzi, wszystko działa lokalnie na laptopie.

## Pytania jury

| Pytanie | Odpowiedź |
|---|---|
| Czy zbieracie dane dzieci? | Nie. Nagrania z telefonów są rozpoznawane w pamięci i od razu znikają. Tętno w demo jest symulowane |
| Skąd naprawdę weźmiecie tętno? | Z zegarka sparowanego z telefonem: Health Connect (Android), HealthKit (iOS) albo standard Bluetooth „Heart Rate”. Do komputera trafia tylko średnia sali |
| A RODO? | Tętno to dane o zdrowiu (art. 9). Tylko za wyraźną zgodą opiekunów, dobrowolnie, w trakcie seansu i bez zapisywania |
| Ile to kosztuje kino? | Jeden laptop (na przykład Copilot+ PC) i Wi-Fi. Modele AI działają lokalnie, bez opłat za chmurę |
| Czy to zadziała z innym filmem? | Tak. Historia to plik ze scenariuszem: sceny, pytania, nastrój filmu i wersje scen. Silnik się nie zmienia |
````

<!-- edit: README.md -->
Zamień w `README.md`:

```markdown
## Pomysły na przyszłość

**Tętno widzów z zegarka** (tylko pomysł, niezaimplementowany). Aplikacja mobilna mogłaby odczytywać tętno
z zegarka sparowanego z telefonem — przez Health Connect (Android), HealthKit (iOS) albo standardową usługę
Bluetooth „Heart Rate” (w Chrome na Androidzie przez Web Bluetooth) — i wysyłać do komputera z filmem tylko
uśrednione, anonimowe tempo całej sali. Film mógłby wtedy dopasowywać się do emocji widowni: przy szybkim tętnie
wydłużyć wspólny oddech z Wiaterkiem Fiufiu albo zwolnić tempo, a przy spokojnym — dodać więcej ruchu i okrzyków.
Dane o zdrowiu to szczególna kategoria danych osobowych (RODO, art. 9), więc wymagałoby to wyraźnej zgody
opiekunów, udziału wyłącznie dobrowolnego, przetwarzania tylko w trakcie seansu i żadnego zapisywania.
```

na:

````markdown
## Film, który czuje salę (tętno i panel dla jury)

Film dopasowuje się do widowni nie tylko głosami. Scenariusz mówi, czego widzowie oczekują od filmu
(`mood: spokojny` albo `mood: zywy`), a wybrane sceny mają drugą wersję montażu (`variants`). Gdy tętno sali odbiega
od nastroju filmu (na spokojnym filmie sala się ekscytuje), scena gra wersję, która przywraca nastrój: dłuższe ujęcia,
wolniejszy montaż. Punktem odniesienia jest tętno sali tuż po pierwszej scenie
([projekt](docs/superpowers/specs/2026-10-16-film-czuje-sale-design.md)).

```powershell
python -m bajka scenarios/klub_ciekawskich.yaml --mobile --panel                     # telefony widzów + panel dla jury
python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed --panel   # próba bez mikrofonu
```

**Panel dla jury** otwiera się w przeglądarce (adres w konsoli, domyślnie `http://127.0.0.1:8090/`; tablet jury
w tej samej sieci: `BAJKA_PANEL_HOST=0.0.0.0`). Pokazuje drzewo scen z przebytą ścieżką, głosy z telefonów albo
krzykomierza, wykres tętna sali z pasmem normy i dziennik: jednym zdaniem, co film zrobił i dlaczego.
Przebieg pokazu krok po kroku: [docs/DEMO_DLA_JURY.md](docs/DEMO_DLA_JURY.md).

**Tętno jest na razie symulowane** (`bajka/pulse.py`): suwak, gotowe stany sali i „Przebieg demo” w panelu.
Wizja: aplikacja mobilna czyta tętno z zegarka sparowanego z telefonem — przez Health Connect (Android), HealthKit
(iOS) albo standardową usługę Bluetooth „Heart Rate” — i wysyła do komputera z filmem tylko uśrednione, anonimowe
tempo całej sali. Dane o zdrowiu to szczególna kategoria danych osobowych (RODO, art. 9), więc wymagałoby to
wyraźnej zgody opiekunów, udziału wyłącznie dobrowolnego, przetwarzania tylko w trakcie seansu i żadnego zapisywania.
````

<!-- edit: README.md -->
Zamień w `README.md`:

```markdown
python -m bajka.pulse --script                       # symulator tętna sali: spokojnie, ekscytacja, uspokojenie
```

na:

```markdown
python -m bajka.pulse --script                       # symulator tętna sali: spokojnie, ekscytacja, uspokojenie
python -m bajka.panel scenarios/klub_ciekawskich.yaml   # panel dla jury bez filmu (symulator tętna)
```

<!-- edit: README.md -->
Zamień w `README.md`:

```markdown
| `bajka/pulse.py` | Tętno sali: symulator na pokaz (`SimulatedPulse`) i stan sali (`hall_state`) |
```

na:

```markdown
| `bajka/pulse.py` | Tętno sali: symulator na pokaz (`SimulatedPulse`) i stan sali (`hall_state`) |
| `bajka/panel.py` | Panel dla jury: stan seansu ze zdarzeń silnika i serwer HTTP (`PanelState`, `PanelServer`) |
| `bajka/panel_app/` | Strona panelu: drzewo scen, głosy, wykres tętna, dziennik decyzji, symulator |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown

## Tryby działania
```

na:

```markdown

## Film, który czuje salę

Oprócz głosów film może słuchać **tętna sali**. Scenariusz mówi, czego widownia oczekuje od filmu (`mood`), a wybrane
sceny mają drugą wersję montażu (`variants`). Gdy sala odbiega od nastroju filmu (na spokojnym filmie tętno skacze),
scena gra wersję spokojniejszą. Na pokazie tętno pochodzi z symulatora sterowanego z **panelu dla jury**: strony
w przeglądarce, która pokazuje drzewo scen, głosy, wykres tętna i powód każdej decyzji filmu. Prawdziwe zegarki
widzów to wizja na przyszłość ([projekt](superpowers/specs/2026-10-16-film-czuje-sale-design.md)).

## Tryby działania
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| `--mobile` | Odpowiedzi z telefonów widzów | `python -m bajka SCENARIUSZ --mobile` |
```

na:

```markdown
| `--mobile` | Odpowiedzi z telefonów widzów | `python -m bajka SCENARIUSZ --mobile` |
| `--panel` | Panel dla jury i symulowane tętno sali (wersje scen) | `python -m bajka SCENARIUSZ --panel` |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| Interfejsy | `bajka/ports.py` — `Player`, `Listener`, `Voice`, `IntentResolver`, `Audience`, `ShoutMeter` |
```

na:

```markdown
| Interfejsy | `bajka/ports.py` — `Player`, `Listener`, `Voice`, `IntentResolver`, `Audience`, `ShoutMeter`, `AudiencePulse`, `ShowObserver` |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| Głos postaci | `bajka/local_tts.py` (Windows), `bajka/tts.py` (Azure) |
```

na:

```markdown
| Głos postaci | `bajka/local_tts.py` (Windows), `bajka/tts.py` (Azure) |
| Tętno i panel | `bajka/pulse.py` (symulator tętna, stan sali), `bajka/panel.py` + `bajka/panel_app/` (panel dla jury) |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| **Zaślepka** | Kolorowy klip zastępczy, dopóki nie ma prawdziwego wideo |
```

na:

```markdown
| **Zaślepka** | Kolorowy klip zastępczy, dopóki nie ma prawdziwego wideo |
| **Nastrój filmu** (`mood`) | Czego widownia oczekuje od filmu: `spokojny` albo `zywy` |
| **Wersja sceny** (`variants`) | Druga wersja montażu sceny, grana, gdy tętno sali odbiega od nastroju filmu |
| **Punkt odniesienia** | Tętno sali tuż po pierwszej scenie; z nim porównujemy kolejne odczyty |
```

<!-- edit: docs/ONBOARDING.md -->
Zamień w `docs/ONBOARDING.md`:

```markdown
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Produkcja klipów i dobór modeli (rysowanie na żywo wycofane) |
```

na:

```markdown
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Produkcja klipów i dobór modeli (rysowanie na żywo wycofane) |
| [Film, który czuje salę](superpowers/specs/2026-10-16-film-czuje-sale-design.md) | Tętno sali, wersje scen, panel dla jury |
| [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md) | Przebieg pokazu przed jury |
```

<!-- edit: docs/PODZIAL_PRACY.md -->
Zamień w `docs/PODZIAL_PRACY.md`:

```markdown
| [`bajka/pulse.py`](../bajka/pulse.py) — tętno sali (na pokazie z symulatora) i stan sali | `AudiencePulse` | C | `python -m bajka.pulse --script` | `tests/test_pulse.py` |
```

na:

```markdown
| [`bajka/pulse.py`](../bajka/pulse.py) — tętno sali (na pokazie z symulatora) i stan sali | `AudiencePulse` | C | `python -m bajka.pulse --script` | `tests/test_pulse.py` |
| [`bajka/panel.py`](../bajka/panel.py) + [`bajka/panel_app/`](../bajka/panel_app/) — panel dla jury: drzewo scen, głosy, tętno, dziennik | `ShowObserver` | C | `python -m bajka.panel scenarios/klub_ciekawskich.yaml` | `tests/test_panel.py` |
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
| Pomysł na przyszłość: tętno z zegarka | Dane o zdrowiu (RODO art. 9) — tylko za wyraźną zgodą opiekunów, dobrowolnie, uśrednione i bez zapisywania; na razie wyłącznie pomysł w README | — |
```

na:

```markdown
| Tętno widowni | W demo wyłącznie symulowane (`bajka/pulse.py`), bez danych prawdziwych osób. Prawdziwa wersja z zegarków to dane o zdrowiu (RODO art. 9): wyraźna zgoda opiekunów, udział dobrowolny, tylko średnia całej sali, przetwarzanie w trakcie seansu, bez zapisywania | **OK** (demo) |
```

<!-- edit: docs/ZGODNOSC_Z_REGULAMINEM.md -->
Zamień w `docs/ZGODNOSC_Z_REGULAMINEM.md`:

```markdown
| **Innowacyjność** | Bohaterka filmu słucha widowni i odpowiada na żywo: każdy widz mówi do własnego telefonu, a komputer w kinie liczy głosy całej sali. Rozpoznawanie mowy, wybór ścieżki i głos działają lokalnie (Copilot+ PC z NPU, Foundry Local), bez nagrywania dzieci. Bez telefonów decyzje rozstrzyga krzykomierz |
```

na:

```markdown
| **Innowacyjność** | Bohaterka filmu słucha widowni i odpowiada na żywo: każdy widz mówi do własnego telefonu, a komputer w kinie liczy głosy całej sali. Rozpoznawanie mowy, wybór ścieżki i głos działają lokalnie (Copilot+ PC z NPU, Foundry Local), bez nagrywania dzieci. Bez telefonów decyzje rozstrzyga krzykomierz. Film czuje też salę: gdy tętno widowni (w demo symulowane) odbiega od nastroju filmu, scena gra inną wersję montażu, a panel pokazuje jury każdą decyzję |
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
Stan na 16.10.2026 (226 testów przechodzi). Nowa osoba w zespole? Zacznij od [ONBOARDING.md](ONBOARDING.md). Prezentacja przed jury: **18.10.2026, 19:00**.
```

na:

```markdown
Stan na 16.10.2026 (304 testy przechodzą). Nowa osoba w zespole? Zacznij od [ONBOARDING.md](ONBOARDING.md). Prezentacja przed jury: **18.10.2026, 19:00**.
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
  wersje scen i panel dla jury.
```

na:

```markdown
  wersje scen i panel dla jury.
- [x] Film, który czuje salę: symulowane tętno sali, spokojne wersje scen `las`, `wiaterek` i `swieto`,
  panel dla jury (`--panel`) i [przebieg pokazu](DEMO_DLA_JURY.md).
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
- [ ] Kalibracja krzykomierza na sali: `python -m bajka.vote`.
```

na:

```markdown
- [ ] Kalibracja krzykomierza na sali: `python -m bajka.vote`.
- [ ] Próba z panelem na laptopie pokazowym: `--mobile --panel`, panel na ekranie laptopa albo tablecie jury
  (`BAJKA_PANEL_HOST=0.0.0.0`), „Przebieg demo” i ręczne „Sala się ekscytuje” przed sceną `wiaterek`.
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown
  ilustracje z ruchem kamery dla wszystkich scen i jedna scena w pełnej animacji (SC. 4, Wiaterek).
```

na:

```markdown
  ilustracje z ruchem kamery dla wszystkich scen i jedna scena w pełnej animacji (SC. 4, Wiaterek).
- [ ] Spokojne wersje montażu trzech scen (dłuższe ujęcia, wolniejsze tempo): `03b_las_spokojna.mp4`,
  `04_wiaterek_spokojna.mp4`, `07_swieto_spokojna.mp4` (pola `variants` w scenariuszu).
```

<!-- edit: docs/DO_ZROBIENIA.md -->
Zamień w `docs/DO_ZROBIENIA.md`:

```markdown

## Po hackathonie

- [ ] Tętno widzów z zegarka (pomysł opisany w [README](../README.md#pomysły-na-przyszłość)).
```

na:

```markdown
- [ ] Pokaz według [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md): drzewo scen, głosy i tętno sali na panelu.

## Po hackathonie

- [ ] Prawdziwe tętno z zegarków widzów zamiast symulatora (Health Connect, HealthKit albo Bluetooth „Heart Rate”
  w aplikacji mobilnej), za zgodą opiekunów; wizja w [README](../README.md#film-który-czuje-salę-tętno-i-panel-dla-jury).
```

- [ ] **Step 6: Pełny zestaw testów**

Run: `python -m pytest -q`
Expected: `304 passed, 1 skipped`.

<!-- checkpoint -->

- [ ] **Step 7: Commit**

```bash
git add bajka/app.py .env.example tests/test_app.py docs/DEMO_DLA_JURY.md README.md docs/ONBOARDING.md docs/PODZIAL_PRACY.md docs/ZGODNOSC_Z_REGULAMINEM.md docs/DO_ZROBIENIA.md
git commit -m "feat: flaga --panel składa bajkę z tętnem sali i panelem dla jury; przebieg pokazu"
```

- [ ] **Step 8: Próba ręczna (wymaga VLC i ffmpeg)**

```powershell
python -m bajka.placeholders scenarios/klub_ciekawskich.yaml
python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed --panel
```

Expected: konsola podaje adres panelu; w panelu kolejne sceny, decyzje z konsoli i wykres tętna. „Sala się ekscytuje” przed sceną `wiaterek` sprawia, że gra `04_wiaterek_spokojna.mp4`, a dziennik pisze „sala pobudzona: scena wiaterek w wersji spokojnej”. Esc zamyka bajkę i panel.

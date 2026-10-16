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


class ScenarioError(ValueError):
    """Scenariusz jest niepoprawny."""


@dataclass(frozen=True)
class Choice:
    id: str
    description: str  # znaczenie wyboru dla LLM, np. "pójść do mrocznego lasu"
    next: str  # identyfikator kolejnej sceny
    reply: str  # statyczna kwestia bohatera, gdy LLM nie odpowie
    keywords: tuple[str, ...] = ()  # słowa, po których wybór rozpozna się bez LLM (bajka/keywords.py)
    call: str = ""  # scena `vote`: wezwanie do okrzyku, np. "Kto za mostkiem? Krzyczymy: MOSTEK!" (TTS)
    call_clip: Path | None = None  # scena `vote`: to samo wezwanie jako nagrany klip (ma pierwszeństwo przed `call`)
    label: str = ""  # krótka nazwa opcji na ekranie telefonu widza (bajka/mobile.py), np. "Tęczowy Mostek"

    @property
    def display_label(self) -> str:
        return self.label or self.id.replace("_", " ").capitalize()


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


def _parse_scene(scene_id: str, data: object, base_dir: Path) -> Scene:
    where = f"scena '{scene_id}'"
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: oczekiwano słownika")
    kind = data.get("kind", "clip")
    if kind not in KINDS:
        raise ScenarioError(f"{where}: nieznany rodzaj sceny {kind!r}, dostępne: {', '.join(KINDS)}")
    if kind == "open":
        return _parse_open(scene_id, data, base_dir, where)
    raw_choices = data.get("choices") or {}
    if not isinstance(raw_choices, dict):
        raise ScenarioError(f"{where}: 'choices' musi być słownikiem")
    choices = {
        cid: Choice(
            id=cid,
            description=_require_str(c, "description", f"{where}, wybór '{cid}'"),
            next=_require_str(c, "next", f"{where}, wybór '{cid}'"),
            reply=_require_str(c, "reply", f"{where}, wybór '{cid}'"),
            keywords=_optional_words(c, "keywords", f"{where}, wybór '{cid}'"),
            call=str(c.get("call") or "").strip() if isinstance(c, dict) else "",
            label=str(c.get("label") or "").strip() if isinstance(c, dict) else "",
            call_clip=base_dir / c["call_clip"] if isinstance(c, dict) and c.get("call_clip") else None,
        )
        for cid, c in raw_choices.items()
    }
    vote = bool(data.get("vote", False))
    if vote:
        silent = [c.id for c in choices.values() if not c.call and c.call_clip is None]
        if silent:
            raise ScenarioError(f"{where}: scena 'vote' wymaga 'call' albo 'call_clip' w wyborach: {', '.join(silent)}")
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
        vote=vote,
    )


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


def _optional_words(data: object, key: str, where: str) -> tuple[str, ...]:
    value = data.get(key) if isinstance(data, dict) else None
    if value is None:
        return ()
    # YAML zamienia "3" na liczbę, więc liczby też przyjmujemy jako słowa.
    if not isinstance(value, list) or not all(isinstance(v, (str, int)) and str(v).strip() for v in value):
        raise ScenarioError(f"{where}: '{key}' musi być listą niepustych słów")
    return tuple(str(v).strip() for v in value)


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
        _check_template(scene.image_prompt, allowed, f"scena '{scene.id}'")


def _check_template(template: str, allowed: set[str], where: str) -> None:
    """Literówka w szablonie ma wyjść przy wczytaniu scenariusza, a nie w trakcie seansu."""
    try:
        fields = template_fields(template)
        fill_prompt(template, dict.fromkeys(allowed, "x"))  # próbne wypełnienie łapie {} i złe formatowanie
    except (ValueError, IndexError, KeyError, AttributeError) as exc:
        raise ScenarioError(f"{where}: niepoprawny szablon 'image_prompt': {exc}") from exc
    unknown = fields - allowed
    if unknown:
        raise ScenarioError(
            f"{where}: 'image_prompt' używa nieznanych pomysłów: {', '.join(sorted(unknown))}"
            " (dozwolone: {idea} i klucze 'remember' scen otwartych)"
        )

"""Scenariusz bajki: graf scen wczytywany z pliku YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Rysowanie na żywo (sceny `open` i `generated`) usunięto z projektu. Parser pomija nieznane pola,
# więc stare pola dają wprost błąd, zamiast cicho zniknąć.
REMOVED_SCENE_FIELDS = (
    "kind", "drawing", "image_prompt", "remember", "default_idea", "fallback_clips", "next", "narration",
)
REMOVED_SCENARIO_FIELDS = ("style", "references")


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
    _reject_removed(raw, REMOVED_SCENARIO_FIELDS, "scenariusz")
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
        paths.extend(path for path in (scene.clip, scene.idle) if path is not None)
        paths.extend(c.call_clip for c in scene.choices.values() if c.call_clip is not None)
    return [path for path in dict.fromkeys(paths) if not path.is_file()]


def _parse_scene(scene_id: str, data: object, base_dir: Path) -> Scene:
    where = f"scena '{scene_id}'"
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: oczekiwano słownika")
    _reject_removed(data, REMOVED_SCENE_FIELDS, where)
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


def _require_str(data: object, key: str, where: str) -> str:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where}: brak pola '{key}' (niepusty tekst)")
    return value.strip()


def _reject_removed(data: dict, removed: tuple[str, ...], where: str) -> None:
    found = [key for key in removed if key in data]
    if found:
        raise ScenarioError(
            f"{where}: pola {', '.join(found)} nie są już obsługiwane (rysowanie na żywo usunięto z projektu)"
        )


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

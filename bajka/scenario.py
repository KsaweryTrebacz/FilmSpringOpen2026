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

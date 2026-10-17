"""Scenariusz odcinka: graf scen wczytywany z pliku YAML.

Odcinek to sceny z gotowymi klipami. Scena z pytaniem kończy się oknem wyboru: widz wybiera pilotem,
dotykiem albo głosem, a gdy czas minie, gra wybór domyślny. Po wyborze może zagrać krótki klip reakcji.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Parser pomija nieznane pola, więc pola usuniętych funkcji dają wprost błąd, zamiast cicho zniknąć.
LIVE_DRAWING = "rysowanie na żywo usunięto z projektu"
CINEMA = "seans kinowy z krzykomierzem zastąpił odcinek w serwisie streamingowym z oknami wyboru"
REMOVED_SCENE_FIELDS = {
    **dict.fromkeys(
        ("kind", "drawing", "image_prompt", "remember", "default_idea", "fallback_clips", "next", "narration"),
        LIVE_DRAWING,
    ),
    "vote": CINEMA,
}
REMOVED_CHOICE_FIELDS = dict.fromkeys(("call", "call_clip"), CINEMA)
REMOVED_SCENARIO_FIELDS = dict.fromkeys(("style", "references"), LIVE_DRAWING)

# Nastrój odcinka (`mood`): jakiej dynamiki oczekujemy. Gdy tętno widza od niej odbiega, scena gra inną wersję.
CALM_FILM, LIVELY_FILM, BALANCED_FILM = "spokojny", "zywy", "zrownowazony"
MOODS = (CALM_FILM, LIVELY_FILM, BALANCED_FILM)
CALM, LIVELY = "spokojna", "zywa"  # wersje montażu sceny (`variants`), wybierane według tętna widza
VARIANTS = (CALM, LIVELY)


class ScenarioError(ValueError):
    """Scenariusz jest niepoprawny."""


@dataclass(frozen=True)
class Choice:
    id: str
    description: str  # znaczenie wyboru dla LLM, np. "pójść do mrocznego lasu"
    next: str  # identyfikator kolejnej sceny
    reply: str  # statyczna kwestia bohatera, gdy LLM nie odpowie
    keywords: tuple[str, ...] = ()  # słowa, po których wybór rozpozna się bez LLM (bajka/keywords.py)
    label: str = ""  # krótka nazwa opcji w oknie wyboru i na telefonie, np. "Tęczowy Mostek"
    icon: str = ""  # obrazek opcji dla dzieci, które jeszcze nie czytają (emoji w prototypie, miniatura w produkcji)
    reaction: Path | None = None  # nagrany klip reakcji postaci na ten wybór; bez niego postać mówi `reply`

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
    timeout: float | None = None  # ile sekund trwa okno wyboru; None = wartość domyślna aplikacji
    variants: dict[str, Path] = field(default_factory=dict)  # wersje montażu: spokojna / zywa → klip

    @property
    def is_ending(self) -> bool:
        return not self.choices


@dataclass(frozen=True)
class Scenario:
    hero: str
    start: str
    scenes: dict[str, Scene]
    mood: str = ""  # nastrój odcinka; bez niego odcinek nie dopasowuje się do tętna widza
    title: str = ""  # tytuł odcinka na ekranie startowym odtwarzacza i w manifeście dla serwisu

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
    mood = str(raw.get("mood") or "").strip()
    if mood and mood not in MOODS:
        raise ScenarioError(f"scenariusz: 'mood' musi być jednym z: {', '.join(MOODS)}, jest: {mood!r}")
    scenario = Scenario(
        hero=_require_str(raw, "hero", "scenariusz"),
        start=_require_str(raw, "start", "scenariusz"),
        scenes={sid: _parse_scene(sid, data, base_dir) for sid, data in raw_scenes.items()},
        mood=mood,
        title=str(raw.get("title") or "").strip(),
    )
    _validate_graph(scenario)
    return scenario


def media_files(scenario: Scenario) -> list[Path]:
    """Wszystkie pliki wideo odcinka bez powtórzeń: klipy scen, pętle oczekiwania, reakcje i wersje scen."""
    paths: list[Path] = []
    for scene in scenario.scenes.values():
        paths.extend(path for path in (scene.clip, scene.idle) if path is not None)
        paths.extend(c.reaction for c in scene.choices.values() if c.reaction is not None)
        paths.extend(scene.variants.values())
    return list(dict.fromkeys(paths))


def missing_media(scenario: Scenario) -> list[Path]:
    """Zwraca pliki wideo odcinka, których nie ma na dysku."""
    return [path for path in media_files(scenario) if not path.is_file()]


def _parse_scene(scene_id: str, data: object, base_dir: Path) -> Scene:
    where = f"scena '{scene_id}'"
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: oczekiwano słownika")
    _reject_removed(data, REMOVED_SCENE_FIELDS, where)
    raw_choices = data.get("choices") or {}
    if not isinstance(raw_choices, dict):
        raise ScenarioError(f"{where}: 'choices' musi być słownikiem")
    choices = {cid: _parse_choice(cid, c, base_dir, f"{where}, wybór '{cid}'") for cid, c in raw_choices.items()}
    clip = base_dir / _require_str(data, "clip", where)
    variants = _parse_variants(data, base_dir, where)
    if not choices:
        return Scene(id=scene_id, clip=clip, variants=variants)
    return Scene(
        id=scene_id,
        clip=clip,
        idle=base_dir / _require_str(data, "idle", where),
        question=_require_str(data, "question", where),
        reprompt=_require_str(data, "reprompt", where),
        fallback=str(data.get("fallback") or "").strip(),
        default=_require_str(data, "default", where),
        choices=choices,
        timeout=_optional_seconds(data, "timeout", where),
        variants=variants,
    )


def _parse_choice(cid: str, data: object, base_dir: Path, where: str) -> Choice:
    if isinstance(data, dict):
        _reject_removed(data, REMOVED_CHOICE_FIELDS, where)
    reaction = data.get("reaction") if isinstance(data, dict) else None
    return Choice(
        id=cid,
        description=_require_str(data, "description", where),
        next=_require_str(data, "next", where),
        reply=_require_str(data, "reply", where),
        keywords=_optional_words(data, "keywords", where),
        label=str(data.get("label") or "").strip(),
        icon=str(data.get("icon") or "").strip(),
        reaction=base_dir / _require_str(data, "reaction", where) if reaction is not None else None,
    )


def _optional_seconds(data: dict, key: str, where: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 3 <= value <= 60:
        raise ScenarioError(f"{where}: '{key}' to liczba sekund okna wyboru od 3 do 60, jest: {value!r}")
    return float(value)


def _require_str(data: object, key: str, where: str) -> str:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where}: brak pola '{key}' (niepusty tekst)")
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


def _reject_removed(data: dict, removed: dict[str, str], where: str) -> None:
    found = [key for key in removed if key in data]
    if found:
        reasons = "; ".join(dict.fromkeys(removed[key] for key in found))
        raise ScenarioError(f"{where}: pola {', '.join(found)} nie są już obsługiwane ({reasons})")


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
        if scene.variants and not scenario.mood:
            raise ScenarioError(f"scena '{scene.id}': 'variants' wymaga pola 'mood' scenariusza ({', '.join(MOODS)})")
        for choice in scene.choices.values():
            if choice.next not in scenario.scenes:
                raise ScenarioError(
                    f"scena '{scene.id}', wybór '{choice.id}': scena '{choice.next}' nie istnieje"
                )

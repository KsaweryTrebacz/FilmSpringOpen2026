"""Manifest odcinka: graf scen jako JSON dla odtwarzacza serwisu streamingowego.

Serwis z własnym odtwarzaczem interaktywnym (okna wyboru, gałęzie) nie musi uruchamiać naszego silnika:
wystarczą mu klipy i ten plik. Opisy wyborów i słowa kluczowe są w polu `voice`, żeby serwis mógł dodać
rozpoznawanie odpowiedzi głosem po swojej stronie (albo na urządzeniu widza). Montaż: `cut` przy każdym
przejściu to propozycja reguł (`bajka/montage.py`), `layers` sceny to miejsca na warstwy, które wypełnia
`layer` wybranej opcji. `linear_path` to ścieżka wyborów domyślnych, czyli wersja liniowa (`python -m bajka.linear`).

Użycie: python -m bajka.manifest SCENARIUSZ [--out odcinek.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from bajka.engine import DEFAULT_CHOICE_SECONDS, DEFAULT_FALLBACK
from bajka.montage import RuleEditor, context_for
from bajka.ports import Cut
from bajka.scenario import TRANSITIONS, Scenario, ScenarioError, load_scenario

FORMAT = "bajka-odcinek/2"


def build_manifest(scenario: Scenario, media_root: Path, choice_seconds: float = DEFAULT_CHOICE_SECONDS) -> dict[str, Any]:
    """Manifest z adresami klipów względnymi wobec `media_root` (katalogu, w którym leży manifest)."""

    def media(path: Path | None) -> str | None:
        return None if path is None else Path(os.path.relpath(path, media_root)).as_posix()

    rules = RuleEditor()

    def cut(scene: Any, target: str, edge: str, **choice: str) -> dict[str, Any]:
        suggestion: Cut = rules.cut(context_for(scenario, scene, target, edge, **choice))
        return {"transition": suggestion.transition, "seconds": suggestion.seconds}

    scenes: dict[str, Any] = {}
    for scene in scenario.scenes.values():
        entry: dict[str, Any] = {"clip": media(scene.clip), "ending": scene.is_ending}
        if scene.place:
            entry["place"] = scene.place
        if scene.layers:
            entry["layers"] = list(scene.layers)
        if scene.transition:
            entry["transition"] = scene.transition
        if scene.variants:
            entry["variants"] = {name: media(path) for name, path in scene.variants.items()}
        if scene.next and not scene.choices:
            entry.update(next=scene.next, cut=cut(scene, scene.next, "dalej"))
        elif not scene.is_ending:
            entry.update(
                idle=media(scene.idle),
                question=scene.question,
                reprompt=scene.reprompt,
                fallback=scene.fallback or DEFAULT_FALLBACK,
                default=scene.default,
                seconds=scene.timeout or choice_seconds,
                choices=[
                    {
                        "id": choice.id,
                        "label": choice.display_label,
                        "icon": choice.icon,
                        "next": choice.next,
                        "reply": choice.reply,
                        "reaction": media(choice.reaction),
                        "layer": {"slot": choice.slot, "clip": media(choice.layer)} if choice.layer else None,
                        "cut": cut(scene, choice.next, "wybor", choice=choice.display_label, meaning=choice.description),
                        "voice": {"description": choice.description, "keywords": list(choice.keywords)},
                    }
                    for choice in scene.choices.values()
                ],
            )
        scenes[scene.id] = entry
    return {
        "format": FORMAT,
        "title": scenario.title,
        "start": scenario.start,
        "mood": scenario.mood or None,
        "character": scenario.hero,
        "transitions": list(TRANSITIONS),
        "scenes": scenes,
        "linear_path": linear_path(scenario),
    }


def linear_path(scenario: Scenario) -> list[str]:
    path, scene = [], scenario.scene(scenario.start)
    while scene.id not in path:
        path.append(scene.id)
        if scene.is_ending:
            return path
        scene = scenario.scene(scene.choices[scene.default].next if scene.choices else scene.next)
    raise ScenarioError(f"wybory domyślne krążą w kółko (scena '{scene.id}'), odcinek bez wyborów nie ma końca")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.manifest", description="Manifest odcinka (JSON) dla serwisu.")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem odcinka")
    parser.add_argument("--out", type=Path, help="plik JSON (domyślnie na ekran; adresy klipów względem jego katalogu)")
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        root = (args.out or args.scenario).resolve().parent
        manifest = build_manifest(scenario, root)
    except (ScenarioError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Manifest odcinka: {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

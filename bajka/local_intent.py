"""Analiza intencji dziecka lokalnym modelem językowym przez Foundry Local (np. Phi-4-mini na NPU).

Moduł spełnia kontrakt `bajka.ports.IntentResolver`. Działa bez chmury i bez kluczy; prompt i wynik
są takie jak w `bajka/intent.py` (Azure OpenAI), więc oba moduły są wymienne.
Test promptu bez reszty aplikacji: python -m bajka.local_intent SCENARIUSZ "wypowiedź dziecka" [--scene ID]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bajka.config import ConfigError, get_float, load_env
from bajka.foundry import FoundryError, load_model, openai_base_url, read_device
from bajka.intent import UNKNOWN, build_messages, build_response_format, parse_interpretation
from bajka.ports import Interpretation
from bajka.scenario import Scene, ScenarioError, load_scenario

log = logging.getLogger(__name__)

# Małe modele lepiej trzymają się formatu, gdy widzą go także w prompcie, nie tylko w schemacie.
JSON_INSTRUCTION = """
Odpowiedz wyłącznie jednym obiektem JSON, bez żadnego innego tekstu:
{{"choice": "<jedno z: {ids}>", "reply": "<kwestia bohatera>"}}
"""

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class LocalLlmSettings:
    model: str = "phi-4-mini"  # alias z katalogu Foundry Local (python -m bajka.foundry)
    device: str = "auto"  # auto, NPU, GPU albo CPU
    temperature: float = 0.3

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LocalLlmSettings:
        return cls(
            model=env.get("FOUNDRY_CHAT_MODEL") or cls.model,
            device=read_device(env),
            temperature=get_float(env, "FOUNDRY_CHAT_TEMPERATURE", cls.temperature),
        )


def build_local_messages(hero: str, scene: Scene, transcript: str) -> list[dict[str, str]]:
    messages = build_messages(hero, scene, transcript)
    messages[0]["content"] += JSON_INSTRUCTION.format(ids=", ".join([*scene.choices, UNKNOWN]))
    return messages


def response_formats(scene: Scene) -> list[dict[str, Any]]:
    """Formaty odpowiedzi od najściślejszego; Foundry Local przyjmuje schemat jako tekst JSON."""
    schema = build_response_format(scene)["json_schema"]["schema"]
    return [{"type": "json_schema", "json_schema": json.dumps(schema)}, {"type": "json_object"}]


def parse_local_interpretation(content: str, scene: Scene) -> Interpretation:
    """Jak `parse_interpretation`, ale wybacza małym modelom ```json, tekst wokół JSON i wielkość liter."""
    found = _JSON_OBJECT.search(content)
    if found is None:
        raise ValueError(f"model nie zwrócił JSON: {content[:120]!r}")
    data = json.loads(found.group(0))
    if isinstance(data, dict) and isinstance(data.get("choice"), str):
        data["choice"] = data["choice"].strip().lower()
    return parse_interpretation(json.dumps(data), scene)


class LocalIntentResolver:
    def __init__(self, client: Any, model_id: str, hero: str, temperature: float = 0.3) -> None:
        self._client = client
        self._model_id = model_id
        self._hero = hero
        self._temperature = temperature
        self._format_level = 0  # indeks w response_formats(); rośnie, gdy serwer odrzuci format

    @classmethod
    def from_settings(cls, settings: LocalLlmSettings, hero: str) -> LocalIntentResolver:
        from openai import OpenAI

        model = load_model(settings.model, settings.device)
        client = OpenAI(base_url=openai_base_url(), api_key="lokalnie", timeout=20.0, max_retries=0)
        return cls(client, model.id, hero, settings.temperature)

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        formats = response_formats(scene)
        while True:
            try:
                response = self._client.chat.completions.create(
                    model=self._model_id,
                    messages=build_local_messages(self._hero, scene, transcript),
                    response_format=formats[self._format_level],
                    temperature=self._temperature,
                    max_tokens=200,
                )
                break
            except Exception as exc:
                # 400 = serwer nie obsługuje tego formatu; schodzimy do luźniejszego na stałe.
                if getattr(exc, "status_code", None) != 400 or self._format_level + 1 >= len(formats):
                    raise
                self._format_level += 1
                log.warning("Foundry Local odrzucił format odpowiedzi, przechodzę na: %s", formats[self._format_level])
        return parse_local_interpretation(response.choices[0].message.content or "", scene)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.local_intent", description="Test rozpoznawania intencji lokalnym modelem (Foundry Local)."
    )
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument("transcript", help="wypowiedź dziecka, np. \"tam gdzie ciemno\"")
    parser.add_argument("--scene", help="identyfikator sceny z pytaniem (domyślnie scena startowa)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        scenario = load_scenario(args.scenario)
        settings = LocalLlmSettings.from_env(load_env())
    except (ScenarioError, ConfigError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    scene_id = args.scene or scenario.start
    scene = scenario.scenes.get(scene_id)
    if scene is None or scene.is_ending:
        print(f"Scena '{scene_id}' nie istnieje albo nie ma wyborów", file=sys.stderr)
        return 2

    try:
        resolver = LocalIntentResolver.from_settings(settings, scenario.hero)
    except FoundryError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:  # demo ma pokazać każdy błąd Foundry Local, a nie wywrócić się
        print(f"Błąd Foundry Local: {exc}", file=sys.stderr)
        return 1
    print(f"Scena: {scene.id} — {scene.question}")
    print(f"Dziecko: {args.transcript!r}", flush=True)
    started = time.perf_counter()
    try:
        interpretation = resolver.resolve(scene, args.transcript)
    except Exception as exc:
        print(f"Błąd modelu lokalnego: {exc}", file=sys.stderr)
        return 1
    print(f"Wybór: {interpretation.choice_id or 'nie rozpoznano (bohater dopyta)'}")
    print(f"Bohater: {interpretation.reply}")
    print(f"({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

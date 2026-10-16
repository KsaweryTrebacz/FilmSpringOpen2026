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

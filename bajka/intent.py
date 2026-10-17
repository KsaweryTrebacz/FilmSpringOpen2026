"""Analiza intencji dziecka przez Azure OpenAI (np. wdrożenie GPT-4o-mini).

Moduł spełnia kontrakt `bajka.ports.IntentResolver`.
Test promptu bez reszty aplikacji: python -m bajka.intent SCENARIUSZ "wypowiedź dziecka" [--scene ID]
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
from bajka.ports import Interpretation
from bajka.scenario import Scene, ScenarioError, load_scenario

UNKNOWN = "nie_wiem"


@dataclass(frozen=True)
class LlmSettings:
    endpoint: str
    api_key: str
    deployment: str  # nazwa wdrożenia w Azure, nie nazwa modelu
    api_version: str = "2024-10-21"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LlmSettings:
        require(env, "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
        return cls(
            endpoint=env["AZURE_OPENAI_ENDPOINT"],
            api_key=env["AZURE_OPENAI_API_KEY"],
            deployment=env["AZURE_OPENAI_DEPLOYMENT"],
            api_version=env.get("AZURE_OPENAI_API_VERSION") or cls.api_version,
        )

SYSTEM_PROMPT = """\
Grasz postać z interaktywnej bajki dla dzieci w wieku 4-8 lat. Twoja postać: {hero}
Przed chwilą w bajce padło pytanie do dziecka siedzącego przed ekranem: "{question}"
Możliwe wybory (identyfikator: znaczenie):
{choices}

Twoje zadanie:
1. Ustal, który wybór ma na myśli dziecko. Interpretuj życzliwie i swobodnie: dzieci mówią
   nieprecyzyjnie, opisowo i z błędami (np. "tam gdzie ciemno", "do tej dziury w górze").
2. Jeśli intencja jest jasna, ustaw "choice" na identyfikator wyboru, a w "reply" napisz
   radosną reakcję bohatera na ten wybór.
3. Jeśli odpowiedź jest nie na temat albo nie da się rozstrzygnąć, ustaw "choice" na
   "{unknown}", a w "reply" ciepło dopytaj, przypominając możliwości.

Zasady dla "reply": mów jako twoja postać, w pierwszej osobie (w rodzaju zgodnym z opisem postaci),
po polsku, najwyżej dwa krótkie zdania, prostymi słowami, bez straszenia i bez emotikon.
Do dziecka zwracaj się bez form zależnych od płci: zamiast "zrobiłeś" czy "zrobiłaś" mów
"udało się", "brawo", "świetnie ci idzie". Jeśli opis postaci mówi o widowni albo kilkorgu dzieciach, mów do nich
w liczbie mnogiej, w czasie teraźniejszym lub przyszłym ("pomożecie?", "świetnie wam idzie").
Chwal starania; pomyłkę poprawiaj łagodnie, pokazując dobrą odpowiedź. Mów tylko prawdę o świecie
(zwierzęta, kolory, liczby, przedmioty); nie zmyślaj faktów. Nie powtarzaj brzydkich ani obraźliwych
słów, nawet jeśli padną, i nie mów o przemocy. Nigdy nie wychodź z roli.
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
    def from_settings(cls, settings: LlmSettings, hero: str) -> AzureIntentResolver:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            timeout=10.0,
            max_retries=1,
        )
        return cls(client, settings.deployment, hero)

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=build_messages(self._hero, scene, transcript),
            response_format=build_response_format(scene),
            temperature=self._temperature,
            max_tokens=200,
        )
        return parse_interpretation(response.choices[0].message.content or "", scene)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.intent", description="Test rozpoznawania intencji przez Azure OpenAI."
    )
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument("transcript", help="wypowiedź dziecka, np. \"tam gdzie ciemno\"")
    parser.add_argument("--scene", help="identyfikator sceny z pytaniem (domyślnie scena startowa)")
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        settings = LlmSettings.from_env(load_env())
    except (ScenarioError, ConfigError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    scene_id = args.scene or scenario.start
    scene = scenario.scenes.get(scene_id)
    if scene is None or scene.is_ending:
        print(f"Scena '{scene_id}' nie istnieje albo nie ma wyborów", file=sys.stderr)
        return 2

    resolver = AzureIntentResolver.from_settings(settings, scenario.hero)
    print(f"Scena: {scene.id} — {scene.question}")
    print(f"Dziecko: {args.transcript!r}", flush=True)
    started = time.perf_counter()
    try:
        interpretation = resolver.resolve(scene, args.transcript)
    except Exception as exc:  # demo ma pokazać każdy błąd Azure OpenAI, a nie wywrócić się
        print(f"Błąd Azure OpenAI: {exc}", file=sys.stderr)
        return 1
    print(f"Wybór: {interpretation.choice_id or 'nie rozpoznano (bohater dopyta)'}")
    print(f"Bohater: {interpretation.reply}")
    print(f"({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

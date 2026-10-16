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

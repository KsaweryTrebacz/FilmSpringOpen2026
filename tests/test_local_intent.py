import json
from types import SimpleNamespace

import pytest

from bajka.config import ConfigError
from bajka.intent import UNKNOWN
from bajka.local_intent import (
    LocalIntentResolver,
    LocalLlmSettings,
    build_local_messages,
    parse_local_interpretation,
    response_formats,
)
from bajka.ports import IntentResolver


class ServerError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class FakeCompletions:
    """Udaje lokalny serwer Foundry Local: zwraca odpowiedzi albo rzuca błędy z listy."""

    def __init__(self, *outcomes):
        self._outcomes = list(outcomes)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        message = SimpleNamespace(content=outcome)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_resolver(*outcomes):
    completions = FakeCompletions(*outcomes)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return LocalIntentResolver(client, "phi-4-mini-npu:1", hero="Lisek Feliks"), completions


def test_settings_defaults_need_no_keys():
    settings = LocalLlmSettings.from_env({})

    assert settings.model == "phi-4-mini"
    assert settings.device == "auto"


def test_settings_read_model_and_device():
    settings = LocalLlmSettings.from_env({"FOUNDRY_CHAT_MODEL": "qwen2.5-7b", "FOUNDRY_DEVICE": "npu"})

    assert settings.model == "qwen2.5-7b"
    assert settings.device == "NPU"


def test_unknown_device_is_rejected():
    with pytest.raises(ConfigError, match="FOUNDRY_DEVICE"):
        LocalLlmSettings.from_env({"FOUNDRY_DEVICE": "TPU"})


def test_resolver_meets_contract():
    resolver, _ = make_resolver()

    assert isinstance(resolver, IntentResolver)


def test_prompt_lists_allowed_choice_ids_for_small_model(scenario):
    system, user = build_local_messages("Lisek Feliks", scenario.scene("intro"), "do lasu")

    assert "Lisek Feliks" in system["content"]
    assert f"las, jaskinia, {UNKNOWN}" in system["content"]
    assert user == {"role": "user", "content": "do lasu"}


def test_schema_is_sent_as_json_text(scenario):
    strict, loose = response_formats(scenario.scene("intro"))

    assert strict["type"] == "json_schema"
    assert json.loads(strict["json_schema"])["properties"]["choice"]["enum"] == ["las", "jaskinia", UNKNOWN]
    assert loose == {"type": "json_object"}


def test_resolve_uses_loaded_model_and_strict_schema(scenario):
    resolver, completions = make_resolver('{"choice": "jaskinia", "reply": "Do jaskini, hura!"}')

    result = resolver.resolve(scenario.scene("intro"), "do tej dziury w górze")

    assert result.choice_id == "jaskinia"
    assert result.reply == "Do jaskini, hura!"
    assert completions.calls[0]["model"] == "phi-4-mini-npu:1"
    assert completions.calls[0]["response_format"]["type"] == "json_schema"


def test_rejected_schema_falls_back_to_json_object_and_stays_there(scenario):
    answer = '{"choice": "las", "reply": "Las!"}'
    resolver, completions = make_resolver(ServerError(400), answer, answer)

    resolver.resolve(scenario.scene("intro"), "las")
    resolver.resolve(scenario.scene("intro"), "las")

    assert [call["response_format"]["type"] for call in completions.calls] == ["json_schema", "json_object", "json_object"]


def test_other_server_errors_are_raised(scenario):
    resolver, _ = make_resolver(ServerError(500))

    with pytest.raises(ServerError):
        resolver.resolve(scenario.scene("intro"), "las")


def test_parser_tolerates_code_fences_and_capital_letters(scenario):
    content = 'Oto odpowiedź:\n```json\n{"choice": " Las ", "reply": "Do lasu!"}\n```'

    result = parse_local_interpretation(content, scenario.scene("intro"))

    assert result.choice_id == "las"
    assert result.reply == "Do lasu!"


def test_parser_maps_unknown_to_clarifying_question(scenario):
    result = parse_local_interpretation(json.dumps({"choice": UNKNOWN, "reply": "Las czy jaskinia?"}), scenario.scene("intro"))

    assert result.choice_id is None


def test_parser_rejects_text_without_json(scenario):
    with pytest.raises(ValueError, match="JSON"):
        parse_local_interpretation("Idziemy do lasu!", scenario.scene("intro"))

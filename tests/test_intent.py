import json
from types import SimpleNamespace

import pytest

from bajka.intent import UNKNOWN, AzureIntentResolver, parse_interpretation


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_resolver(content):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return AzureIntentResolver(client, deployment="gpt-4o-mini", hero="Lisek Feliks"), completions


def test_resolve_returns_choice_and_reply(scenario):
    resolver, _ = make_resolver(json.dumps({"choice": "jaskinia", "reply": "Do jaskini, hura!"}))

    result = resolver.resolve(scenario.scene("intro"), "chcę do tej dziury w górze")

    assert result.choice_id == "jaskinia"
    assert result.reply == "Do jaskini, hura!"


def test_request_uses_deployment_schema_and_prompt(scenario):
    resolver, completions = make_resolver(json.dumps({"choice": "las", "reply": "Las!"}))

    resolver.resolve(scenario.scene("intro"), "do lasu")

    kwargs = completions.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["response_format"]["json_schema"]["strict"] is True
    schema = kwargs["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["choice"]["enum"] == ["las", "jaskinia", UNKNOWN]
    system, user = kwargs["messages"]
    assert "Lisek Feliks" in system["content"]
    assert "Idziemy do mrocznego lasu czy do jaskini?" in system["content"]
    assert "- jaskinia: wejść do jaskini" in system["content"]
    assert user == {"role": "user", "content": "do lasu"}


def test_unknown_intent_returns_none_with_clarifying_reply(scenario):
    content = json.dumps({"choice": UNKNOWN, "reply": "Las czy jaskinia?"})

    result = parse_interpretation(content, scenario.scene("intro"))

    assert result.choice_id is None
    assert result.reply == "Las czy jaskinia?"


def test_choice_outside_scene_is_an_error(scenario):
    with pytest.raises(ValueError, match="rzeka"):
        parse_interpretation(json.dumps({"choice": "rzeka", "reply": "?"}), scenario.scene("intro"))


def test_malformed_json_is_an_error(scenario):
    with pytest.raises(ValueError):
        parse_interpretation("to nie jest JSON", scenario.scene("intro"))

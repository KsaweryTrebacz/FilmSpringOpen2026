import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bajka.config import ConfigError
from bajka.intent import UNKNOWN, AzureIntentResolver, LlmSettings, main, parse_interpretation
from bajka.ports import IntentResolver

EXAMPLE = Path(__file__).resolve().parents[1] / "scenarios" / "las_czy_jaskinia.yaml"
LLM_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
}


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


@pytest.fixture
def llm_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in LLM_ENV.items():
        monkeypatch.setenv(name, value)


def use_fake_llm(monkeypatch, content):
    resolver, completions = make_resolver(content)
    monkeypatch.setattr(AzureIntentResolver, "from_settings", classmethod(lambda cls, settings, hero: resolver))
    return completions


# Ustawienia


def test_settings_read_endpoint_key_and_deployment_with_default_api_version():
    settings = LlmSettings.from_env(LLM_ENV)

    assert settings.endpoint == "https://bajka.openai.azure.com/"
    assert settings.api_key == "klucz-llm"
    assert settings.deployment == "gpt-4o-mini"
    assert settings.api_version == "2024-10-21"


def test_settings_require_endpoint_key_and_deployment():
    with pytest.raises(ConfigError) as exc:
        LlmSettings.from_env({})

    for name in LLM_ENV:
        assert name in str(exc.value)


def test_settings_api_version_can_be_overridden():
    settings = LlmSettings.from_env({**LLM_ENV, "AZURE_OPENAI_API_VERSION": "2025-01-01-preview"})

    assert settings.api_version == "2025-01-01-preview"


def test_resolver_from_settings_fulfils_intent_resolver_contract():
    resolver = AzureIntentResolver.from_settings(LlmSettings.from_env(LLM_ENV), hero="Lisek Feliks")

    assert isinstance(resolver, IntentResolver)


# Demo: python -m bajka.intent


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for name in LLM_ENV:
        monkeypatch.delenv(name, raising=False)

    assert main([str(EXAMPLE), "do lasu"]) == 2
    assert "AZURE_OPENAI_ENDPOINT" in capsys.readouterr().err


def test_demo_prints_choice_and_reply_for_start_scene(llm_keys, monkeypatch, capsys):
    completions = use_fake_llm(monkeypatch, json.dumps({"choice": "las", "reply": "Do lasu, hura!"}))

    assert main([str(EXAMPLE), "tam gdzie ciemno"]) == 0

    out = capsys.readouterr().out
    assert "Wybór: las" in out
    assert "Bohater: Do lasu, hura!" in out
    assert "Idziemy do mrocznego lasu czy do jaskini?" in completions.kwargs["messages"][0]["content"]
    assert completions.kwargs["messages"][1]["content"] == "tam gdzie ciemno"


def test_demo_reports_unrecognized_intent(llm_keys, monkeypatch, capsys):
    use_fake_llm(monkeypatch, json.dumps({"choice": UNKNOWN, "reply": "Las czy jaskinia?"}))

    assert main([str(EXAMPLE), "banan"]) == 0

    assert "Wybór: nie rozpoznano" in capsys.readouterr().out


def test_demo_rejects_scene_without_choices(llm_keys, monkeypatch, capsys):
    use_fake_llm(monkeypatch, "{}")

    assert main([str(EXAMPLE), "do lasu", "--scene", "las"]) == 2
    assert "las" in capsys.readouterr().err

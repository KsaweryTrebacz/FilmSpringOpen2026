import os

import pytest

from bajka.config import ConfigError, get_int, load_env, load_settings, require


def test_require_passes_when_all_values_are_present():
    require({"A": "1", "B": "2"}, "A", "B")


def test_require_lists_every_missing_or_empty_variable():
    with pytest.raises(ConfigError) as exc:
        require({"A": "1", "B": ""}, "A", "B", "C")

    assert "B" in str(exc.value)
    assert "C" in str(exc.value)
    assert "A," not in str(exc.value)


def test_get_int_returns_default_when_variable_is_missing_or_empty():
    assert get_int({}, "LICZBA", 7) == 7
    assert get_int({"LICZBA": ""}, "LICZBA", 7) == 7


def test_get_int_parses_value():
    assert get_int({"LICZBA": "800"}, "LICZBA", 7) == 800


def test_get_int_rejects_non_numeric_value():
    with pytest.raises(ConfigError, match="LICZBA"):
        get_int({"LICZBA": "dużo"}, "LICZBA", 7)


def test_load_env_reads_dotenv_from_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BAJKA_TEST_VAR=z-pliku\n", encoding="utf-8")
    try:
        assert load_env()["BAJKA_TEST_VAR"] == "z-pliku"
    finally:
        os.environ.pop("BAJKA_TEST_VAR", None)


FULL_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
    "AZURE_SPEECH_KEY": "klucz-mowy",
    "AZURE_SPEECH_REGION": "westeurope",
}


def test_reads_required_values_and_applies_defaults():
    settings = load_settings(FULL_ENV)

    assert settings.openai_deployment == "gpt-4o-mini"
    assert settings.speech_region == "westeurope"
    assert settings.openai_api_version == "2024-10-21"
    assert settings.language == "pl-PL"
    assert settings.voice == "pl-PL-MarekNeural"
    assert settings.max_reprompts == 2


def test_missing_variables_are_listed_in_error():
    env = {k: v for k, v in FULL_ENV.items() if k not in ("AZURE_SPEECH_KEY", "AZURE_OPENAI_API_KEY")}

    with pytest.raises(ConfigError) as exc:
        load_settings(env)

    assert "AZURE_SPEECH_KEY" in str(exc.value)
    assert "AZURE_OPENAI_API_KEY" in str(exc.value)


def test_text_mode_does_not_need_speech_keys():
    env = {k: v for k, v in FULL_ENV.items() if not k.startswith("AZURE_SPEECH")}

    settings = load_settings(env, require_speech=False)

    assert settings.speech_key == ""


def test_numeric_overrides_are_parsed():
    settings = load_settings({**FULL_ENV, "BAJKA_MAX_REPROMPTS": "1", "BAJKA_END_SILENCE_MS": "800"})

    assert settings.max_reprompts == 1
    assert settings.end_silence_ms == 800


def test_non_numeric_override_is_rejected():
    with pytest.raises(ConfigError, match="BAJKA_MAX_REPROMPTS"):
        load_settings({**FULL_ENV, "BAJKA_MAX_REPROMPTS": "dwa"})

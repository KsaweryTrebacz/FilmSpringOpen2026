import pytest

from bajka.config import ConfigError, load_settings

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

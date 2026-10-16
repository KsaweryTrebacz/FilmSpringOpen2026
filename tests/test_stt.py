from types import SimpleNamespace

import azure.cognitiveservices.speech as speechsdk
import pytest

from bajka.config import ConfigError
from bajka.ports import Listener
from bajka.stt import AzureListener, RecognitionError, SttSettings, main, make_recognizer_config, text_from_result

Reason = speechsdk.ResultReason
KEYS = {"AZURE_SPEECH_KEY": "klucz-mowy", "AZURE_SPEECH_REGION": "westeurope"}


def recognized(text):
    return SimpleNamespace(reason=Reason.RecognizedSpeech, text=text)


def silence():
    return SimpleNamespace(reason=Reason.NoMatch, text="")


def canceled(error_details):
    details = SimpleNamespace(reason="Error", error_details=error_details)
    return SimpleNamespace(reason=Reason.Canceled, text="", cancellation_details=details)


class FakeRecognizer:
    """Udaje SpeechRecognizer z Azure SDK: każde rozpoznanie zwraca kolejny wynik z listy."""

    def __init__(self, *results):
        self._results = list(results)

    def recognize_once_async(self):
        result = self._results.pop(0)
        return SimpleNamespace(get=lambda: result)


def use_fake_microphone(monkeypatch, *results):
    listener = AzureListener(FakeRecognizer(*results))
    monkeypatch.setattr(AzureListener, "from_settings", classmethod(lambda cls, settings: listener))


@pytest.fixture
def speech_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in KEYS.items():
        monkeypatch.setenv(name, value)


# Ustawienia


def test_settings_read_keys_and_apply_defaults():
    settings = SttSettings.from_env(KEYS)

    assert settings.speech_key == "klucz-mowy"
    assert settings.speech_region == "westeurope"
    assert settings.language == "pl-PL"
    assert settings.initial_silence_ms == 6000
    assert settings.end_silence_ms == 1200


def test_settings_require_speech_key_and_region():
    with pytest.raises(ConfigError) as exc:
        SttSettings.from_env({})

    assert "AZURE_SPEECH_KEY" in str(exc.value)
    assert "AZURE_SPEECH_REGION" in str(exc.value)


def test_settings_apply_overrides():
    env = {**KEYS, "BAJKA_LANGUAGE": "en-US", "BAJKA_INITIAL_SILENCE_MS": "4000", "BAJKA_END_SILENCE_MS": "800"}

    settings = SttSettings.from_env(env)

    assert (settings.language, settings.initial_silence_ms, settings.end_silence_ms) == ("en-US", 4000, 800)


def test_recognizer_config_sets_language_and_silence_timeouts():
    config = make_recognizer_config(SttSettings.from_env({**KEYS, "BAJKA_END_SILENCE_MS": "900"}))

    assert config.speech_recognition_language == "pl-PL"
    assert config.get_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs) == "6000"
    assert config.get_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs) == "900"


# Wyniki rozpoznawania


def test_recognized_speech_is_stripped():
    assert text_from_result(recognized("  Do lasu.  ")) == "Do lasu."


def test_recognized_but_empty_text_counts_as_silence():
    assert text_from_result(recognized("   ")) is None


def test_no_match_counts_as_silence():
    assert text_from_result(silence()) is None


def test_canceled_recognition_raises_with_azure_details():
    with pytest.raises(RecognitionError, match="401"):
        text_from_result(canceled("401 zły klucz"))


# Listener


def test_listener_fulfils_listener_contract():
    assert isinstance(AzureListener(FakeRecognizer()), Listener)


def test_listener_returns_text_of_each_utterance():
    listener = AzureListener(FakeRecognizer(recognized("Jaskinia!"), silence()))

    assert listener.listen() == "Jaskinia!"
    assert listener.listen() is None


# Demo: python -m bajka.stt


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for name in KEYS:
        monkeypatch.delenv(name, raising=False)

    assert main([]) == 2
    assert "AZURE_SPEECH_KEY" in capsys.readouterr().err


def test_demo_prints_each_utterance(speech_keys, monkeypatch, capsys):
    use_fake_microphone(monkeypatch, recognized("Do lasu."), silence())

    assert main(["--repeat", "2"]) == 0

    out = capsys.readouterr().out
    assert "Rozpoznano: 'Do lasu.'" in out
    assert "Cisza" in out


def test_demo_reports_azure_error_with_code_1(speech_keys, monkeypatch, capsys):
    use_fake_microphone(monkeypatch, canceled("401 zły klucz"))

    assert main(["--repeat", "1"]) == 1
    assert "401" in capsys.readouterr().err

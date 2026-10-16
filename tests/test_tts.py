import io
import sys
import wave
from types import SimpleNamespace

import azure.cognitiveservices.speech as speechsdk
import pytest

from bajka.config import ConfigError
from bajka.ports import Voice
from bajka.tts import (
    AzureVoice,
    SynthesisError,
    TtsSettings,
    audio_from_result,
    build_ssml,
    main,
    make_synthesizer_config,
    play_wav_bytes,
)

Reason = speechsdk.ResultReason
KEYS = {"AZURE_SPEECH_KEY": "klucz-mowy", "AZURE_SPEECH_REGION": "westeurope"}


def synthesized(audio):
    return SimpleNamespace(reason=Reason.SynthesizingAudioCompleted, audio_data=audio)


def canceled(error_details):
    details = SimpleNamespace(reason="Error", error_details=error_details)
    return SimpleNamespace(reason=Reason.Canceled, cancellation_details=details)


class FakeSynthesizer:
    """Udaje SpeechSynthesizer z Azure SDK: zapamiętuje SSML i zwraca kolejny wynik z listy."""

    def __init__(self, *results):
        self._results = list(results)
        self.ssml = []

    def speak_ssml_async(self, ssml):
        self.ssml.append(ssml)
        result = self._results.pop(0)
        return SimpleNamespace(get=lambda: result)


def make_voice(*results):
    played = []
    synthesizer = FakeSynthesizer(*results)
    voice = AzureVoice(synthesizer, "pl-PL-MarekNeural", "pl-PL", "-10%", play_wav=played.append)
    return voice, synthesizer, played


def use_fake_speaker(monkeypatch, *results):
    voice, _, played = make_voice(*results)
    monkeypatch.setattr(AzureVoice, "from_settings", classmethod(lambda cls, settings: voice))
    return played


@pytest.fixture
def speech_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in KEYS.items():
        monkeypatch.setenv(name, value)


# Ustawienia


def test_settings_read_keys_and_apply_defaults():
    settings = TtsSettings.from_env(KEYS)

    assert settings.speech_key == "klucz-mowy"
    assert settings.speech_region == "westeurope"
    assert settings.language == "pl-PL"
    assert settings.voice == "pl-PL-MarekNeural"
    assert settings.voice_rate == "-10%"


def test_settings_require_speech_key_and_region():
    with pytest.raises(ConfigError) as exc:
        TtsSettings.from_env({})

    assert "AZURE_SPEECH_KEY" in str(exc.value)
    assert "AZURE_SPEECH_REGION" in str(exc.value)


def test_settings_apply_overrides():
    settings = TtsSettings.from_env({**KEYS, "BAJKA_VOICE": "pl-PL-ZofiaNeural", "BAJKA_VOICE_RATE": "-20%"})

    assert (settings.voice, settings.voice_rate) == ("pl-PL-ZofiaNeural", "-20%")


def test_synthesizer_config_outputs_16bit_wav():
    config = make_synthesizer_config(TtsSettings.from_env(KEYS))

    output_format = config.get_property(speechsdk.PropertyId.SpeechServiceConnection_SynthOutputFormat)
    assert output_format == "riff-24khz-16bit-mono-pcm"


# SSML i wyniki syntezy


def test_ssml_escapes_text_and_sets_voice_and_rate():
    ssml = build_ssml("Las <i> jaskinia & most", "pl-PL-MarekNeural", "pl-PL", "-10%")

    assert '<voice name="pl-PL-MarekNeural">' in ssml
    assert '<prosody rate="-10%">' in ssml
    assert "Las &lt;i&gt; jaskinia &amp; most" in ssml


def test_completed_synthesis_returns_audio():
    assert audio_from_result(synthesized(b"RIFF")) == b"RIFF"


def test_canceled_synthesis_raises_with_azure_details():
    with pytest.raises(SynthesisError, match="401"):
        audio_from_result(canceled("401 zły klucz"))


def test_play_wav_bytes_plays_samples_and_waits(monkeypatch):
    calls = []
    fake_sd = SimpleNamespace(
        play=lambda samples, rate: calls.append(("play", samples.shape, rate)),
        wait=lambda: calls.append(("wait",)),
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 240)

    play_wav_bytes(buffer.getvalue())

    assert calls == [("play", (240, 1), 24000), ("wait",)]


# Voice


def test_voice_fulfils_voice_contract():
    voice, _, _ = make_voice()

    assert isinstance(voice, Voice)


def test_voice_synthesizes_ssml_and_plays_audio():
    voice, synthesizer, played = make_voice(synthesized(b"WAV"))

    voice.say("Do lasu!")

    assert "Do lasu!" in synthesizer.ssml[0]
    assert played == [b"WAV"]


# Demo: python -m bajka.tts


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for name in KEYS:
        monkeypatch.delenv(name, raising=False)

    assert main([]) == 2
    assert "AZURE_SPEECH_KEY" in capsys.readouterr().err


def test_demo_speaks_given_text(speech_keys, monkeypatch, capsys):
    played = use_fake_speaker(monkeypatch, synthesized(b"WAV"))

    assert main(["Cześć, dzieciaki!"]) == 0

    assert played == [b"WAV"]
    assert "Cześć, dzieciaki!" in capsys.readouterr().out


def test_demo_reports_azure_error_with_code_1(speech_keys, monkeypatch, capsys):
    use_fake_speaker(monkeypatch, canceled("401 zły klucz"))

    assert main([]) == 1
    assert "401" in capsys.readouterr().err

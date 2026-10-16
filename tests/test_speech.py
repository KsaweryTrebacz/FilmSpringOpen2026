import io
import sys
import wave
from types import SimpleNamespace

import azure.cognitiveservices.speech as speechsdk
import pytest

from bajka.speech import (
    AzureListener,
    AzureVoice,
    SpeechError,
    audio_from_result,
    build_ssml,
    play_wav_bytes,
    text_from_result,
)

Reason = speechsdk.ResultReason


def canceled_result():
    details = SimpleNamespace(reason="Error", error_details="401 zły klucz")
    return SimpleNamespace(reason=Reason.Canceled, cancellation_details=details)


def test_recognized_speech_is_stripped():
    result = SimpleNamespace(reason=Reason.RecognizedSpeech, text="  do lasu  ")
    assert text_from_result(result) == "do lasu"


def test_no_match_means_silence():
    assert text_from_result(SimpleNamespace(reason=Reason.NoMatch, text="")) is None


def test_canceled_recognition_raises_with_details():
    with pytest.raises(SpeechError, match="401"):
        text_from_result(canceled_result())


def test_listener_returns_text_from_single_recognition():
    result = SimpleNamespace(reason=Reason.RecognizedSpeech, text="jaskinia")
    recognizer = SimpleNamespace(recognize_once_async=lambda: SimpleNamespace(get=lambda: result))

    assert AzureListener(recognizer).listen() == "jaskinia"


def test_ssml_escapes_text_and_sets_voice_and_rate():
    ssml = build_ssml("Las <i> jaskinia & most", "pl-PL-MarekNeural", "pl-PL", "-10%")

    assert '<voice name="pl-PL-MarekNeural">' in ssml
    assert '<prosody rate="-10%">' in ssml
    assert "Las &lt;i&gt; jaskinia &amp; most" in ssml


def test_voice_synthesizes_ssml_and_plays_audio():
    spoken, played = [], []
    done = SimpleNamespace(reason=Reason.SynthesizingAudioCompleted, audio_data=b"WAV")

    def speak_ssml_async(ssml):
        spoken.append(ssml)
        return SimpleNamespace(get=lambda: done)

    synthesizer = SimpleNamespace(speak_ssml_async=speak_ssml_async)
    voice = AzureVoice(synthesizer, "pl-PL-MarekNeural", "pl-PL", "-10%", play_wav=played.append)

    voice.say("Do lasu!")

    assert "Do lasu!" in spoken[0]
    assert played == [b"WAV"]


def test_canceled_synthesis_raises():
    with pytest.raises(SpeechError, match="401"):
        audio_from_result(canceled_result())


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

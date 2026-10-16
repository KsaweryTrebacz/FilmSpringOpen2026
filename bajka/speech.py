"""Azure AI Speech: rozpoznawanie mowy dziecka (STT) i głos bohatera (TTS)."""

from __future__ import annotations

import io
import logging
import wave
from collections.abc import Callable
from typing import Any
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk

from bajka.config import Settings

log = logging.getLogger(__name__)


class SpeechError(RuntimeError):
    """Azure Speech anulował rozpoznawanie lub syntezę (sieć, klucz, limit)."""


def make_speech_config(settings: Settings) -> speechsdk.SpeechConfig:
    config = speechsdk.SpeechConfig(subscription=settings.speech_key, region=settings.speech_region)
    config.speech_recognition_language = settings.language
    # Ile czekamy, aż dziecko zacznie mówić, i ile ciszy kończy wypowiedź.
    config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(settings.initial_silence_ms)
    )
    config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(settings.end_silence_ms))
    config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    return config


def text_from_result(result: Any) -> str | None:
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text.strip() or None
    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise SpeechError(f"STT anulowane: {details.reason}: {details.error_details}")
    return None  # NoMatch: dziecko milczało albo mówiło niewyraźnie


def audio_from_result(result: Any) -> bytes:
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    details = result.cancellation_details
    raise SpeechError(f"TTS anulowane: {details.reason}: {details.error_details}")


def build_ssml(text: str, voice: str, language: str, rate: str) -> str:
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">'
        f'<voice name="{voice}"><prosody rate="{rate}">{escape(text)}</prosody></voice></speak>'
    )


def play_wav_bytes(data: bytes) -> None:
    """Odtwarza WAV (PCM 16-bit) i blokuje do końca, więc mikrofon nie słyszy bohatera."""
    import numpy as np
    import sounddevice as sd

    with wave.open(io.BytesIO(data)) as wav:
        rate, channels = wav.getframerate(), wav.getnchannels()
        frames = wav.readframes(wav.getnframes())
    sd.play(np.frombuffer(frames, dtype=np.int16).reshape(-1, channels), rate)
    sd.wait()


class AzureListener:
    def __init__(self, recognizer: Any) -> None:
        self._recognizer = recognizer

    @classmethod
    def from_config(cls, config: speechsdk.SpeechConfig) -> AzureListener:
        audio = speechsdk.audio.AudioConfig(use_default_microphone=True)
        return cls(speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio))

    def listen(self) -> str | None:
        log.info("Słucham…")
        return text_from_result(self._recognizer.recognize_once_async().get())


class AzureVoice:
    def __init__(
        self,
        synthesizer: Any,
        voice: str,
        language: str,
        rate: str,
        play_wav: Callable[[bytes], None] = play_wav_bytes,
    ) -> None:
        self._synthesizer = synthesizer
        self._voice = voice
        self._language = language
        self._rate = rate
        self._play_wav = play_wav

    @classmethod
    def from_settings(cls, config: speechsdk.SpeechConfig, settings: Settings) -> AzureVoice:
        # audio_config=None: synteza do pamięci, odtwarzamy sami i wiemy, kiedy bohater skończył.
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        return cls(synthesizer, settings.voice, settings.language, settings.voice_rate)

    def say(self, text: str) -> None:
        log.info("Bohater: %s", text)
        ssml = build_ssml(text, self._voice, self._language, self._rate)
        result = self._synthesizer.speak_ssml_async(ssml).get()
        self._play_wav(audio_from_result(result))

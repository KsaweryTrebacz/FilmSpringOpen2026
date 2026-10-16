"""Rozpoznawanie mowy dziecka z mikrofonu przez Azure AI Speech (STT).

Moduł jest samodzielny: zależy tylko od `bajka.config` i spełnia kontrakt `bajka.ports.Listener`.
Test z prawdziwym mikrofonem: python -m bajka.stt [--repeat N]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import azure.cognitiveservices.speech as speechsdk

from bajka.config import ConfigError, get_int, load_env, require

log = logging.getLogger(__name__)


class RecognitionError(RuntimeError):
    """Azure anulował rozpoznawanie: brak sieci, zły klucz lub region, przekroczony limit."""


@dataclass(frozen=True)
class SttSettings:
    speech_key: str
    speech_region: str
    language: str = "pl-PL"
    initial_silence_ms: int = 6000  # ile czekamy, aż dziecko zacznie mówić
    end_silence_ms: int = 1200  # ile ciszy kończy wypowiedź

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> SttSettings:
        require(env, "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")
        return cls(
            speech_key=env["AZURE_SPEECH_KEY"],
            speech_region=env["AZURE_SPEECH_REGION"],
            language=env.get("BAJKA_LANGUAGE") or cls.language,
            initial_silence_ms=get_int(env, "BAJKA_INITIAL_SILENCE_MS", cls.initial_silence_ms),
            end_silence_ms=get_int(env, "BAJKA_END_SILENCE_MS", cls.end_silence_ms),
        )


def make_recognizer_config(settings: SttSettings) -> speechsdk.SpeechConfig:
    config = speechsdk.SpeechConfig(subscription=settings.speech_key, region=settings.speech_region)
    config.speech_recognition_language = settings.language
    config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(settings.initial_silence_ms)
    )
    config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(settings.end_silence_ms))
    return config


def text_from_result(result: Any) -> str | None:
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text.strip() or None
    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise RecognitionError(f"rozpoznawanie anulowane: {details.reason}: {details.error_details}")
    return None  # NoMatch: dziecko milczało albo mówiło niewyraźnie


class AzureListener:
    """Słucha domyślnego mikrofonu; Azure sam wykrywa początek i koniec wypowiedzi."""

    def __init__(self, recognizer: Any) -> None:
        self._recognizer = recognizer

    @classmethod
    def from_settings(cls, settings: SttSettings) -> AzureListener:
        audio = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(speech_config=make_recognizer_config(settings), audio_config=audio)
        return cls(recognizer)

    def listen(self) -> str | None:
        log.info("Słucham…")
        text = text_from_result(self._recognizer.recognize_once_async().get())
        log.info("Rozpoznano: %r", text)
        return text


class AzureFileTranscriber:
    """Nagranie z telefonu widza (16 kHz mono) → tekst przez Azure; używa go `bajka/mobile.py` w trybie azure."""

    def __init__(self, settings: SttSettings, recognize: Any = None) -> None:
        self._settings = settings
        self._recognize = recognize or self._recognize_file

    def _recognize_file(self, path: str) -> Any:
        audio = speechsdk.audio.AudioConfig(filename=path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=make_recognizer_config(self._settings), audio_config=audio)
        return recognizer.recognize_once_async().get()

    def __call__(self, samples: Any) -> str:
        import os
        import tempfile
        import wave

        handle, path = tempfile.mkstemp(suffix=".wav", prefix="bajka-")
        os.close(handle)
        try:
            with wave.open(path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(samples.astype("<i2").tobytes())
            return text_from_result(self._recognize(path)) or ""
        finally:
            os.remove(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.stt", description="Test rozpoznawania mowy z mikrofonu (Azure AI Speech)."
    )
    parser.add_argument("--repeat", type=int, default=3, help="ile wypowiedzi wysłuchać (domyślnie 3)")
    args = parser.parse_args(argv)
    try:
        settings = SttSettings.from_env(load_env())
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    listener = AzureListener.from_settings(settings)
    for _ in range(args.repeat):
        print("Mów teraz…", flush=True)
        started = time.perf_counter()
        try:
            text = listener.listen()
        except RecognitionError as exc:
            print(f"Błąd Azure: {exc}", file=sys.stderr)
            return 1
        elapsed = time.perf_counter() - started
        if text:
            print(f"Rozpoznano: {text!r} ({elapsed:.1f} s)")
        else:
            print(f"Cisza, nic nie rozpoznano ({elapsed:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

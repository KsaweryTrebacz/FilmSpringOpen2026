"""Głos bohatera przez Azure AI Speech (TTS).

Moduł jest samodzielny: zależy tylko od `bajka.config` i spełnia kontrakt `bajka.ports.Voice`.
Test z prawdziwym głośnikiem: python -m bajka.tts ["kwestia bohatera"]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk

from bajka.audio import play_wav_bytes
from bajka.config import ConfigError, load_env, require

log = logging.getLogger(__name__)

DEMO_TEXT = "Cześć! Idziemy do mrocznego lasu czy do jaskini?"


class SynthesisError(RuntimeError):
    """Azure anulował syntezę: brak sieci, zły klucz lub region, nieznany głos, przekroczony limit."""


@dataclass(frozen=True)
class TtsSettings:
    speech_key: str
    speech_region: str
    language: str = "pl-PL"
    voice: str = "pl-PL-MarekNeural"
    voice_rate: str = "-10%"  # wolniej niż domyślnie, żeby dzieci nadążały

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> TtsSettings:
        require(env, "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")
        return cls(
            speech_key=env["AZURE_SPEECH_KEY"],
            speech_region=env["AZURE_SPEECH_REGION"],
            language=env.get("BAJKA_LANGUAGE") or cls.language,
            voice=env.get("BAJKA_VOICE") or cls.voice,
            voice_rate=env.get("BAJKA_VOICE_RATE") or cls.voice_rate,
        )


def make_synthesizer_config(settings: TtsSettings) -> speechsdk.SpeechConfig:
    config = speechsdk.SpeechConfig(subscription=settings.speech_key, region=settings.speech_region)
    config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    return config


def audio_from_result(result: Any) -> bytes:
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    details = result.cancellation_details
    raise SynthesisError(f"synteza anulowana: {details.reason}: {details.error_details}")


def build_ssml(text: str, voice: str, language: str, rate: str) -> str:
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">'
        f'<voice name="{voice}"><prosody rate="{rate}">{escape(text)}</prosody></voice></speak>'
    )


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
    def from_settings(cls, settings: TtsSettings) -> AzureVoice:
        # audio_config=None: synteza do pamięci, odtwarzamy sami i wiemy, kiedy bohater skończył.
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=make_synthesizer_config(settings), audio_config=None)
        return cls(synthesizer, settings.voice, settings.language, settings.voice_rate)

    def say(self, text: str) -> None:
        log.info("Bohater: %s", text)
        ssml = build_ssml(text, self._voice, self._language, self._rate)
        result = self._synthesizer.speak_ssml_async(ssml).get()
        self._play_wav(audio_from_result(result))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.tts", description="Test głosu bohatera (Azure AI Speech).")
    parser.add_argument("text", nargs="?", default=DEMO_TEXT, help="kwestia do wypowiedzenia")
    args = parser.parse_args(argv)
    try:
        settings = TtsSettings.from_env(load_env())
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    voice = AzureVoice.from_settings(settings)
    print(f"Bohater mówi ({settings.voice}): {args.text}", flush=True)
    started = time.perf_counter()
    try:
        voice.say(args.text)
    except SynthesisError as exc:
        print(f"Błąd Azure: {exc}", file=sys.stderr)
        return 1
    print(f"Gotowe ({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

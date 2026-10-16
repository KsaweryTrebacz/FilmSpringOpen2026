"""Głos bohatera z syntezatora wbudowanego w Windows (Windows.Media.SpeechSynthesis) — offline, bez kluczy.

Moduł spełnia kontrakt `bajka.ports.Voice`. Polski głos to „Microsoft Paulina”: Ustawienia → Czas i język
→ Mowa → Zarządzaj głosami → dodaj polski. Synteza idzie do pamięci, a odtwarzanie blokuje do końca
wypowiedzi, więc mikrofon nie słyszy bohatera.
Test z prawdziwym głośnikiem: python -m bajka.local_tts ["kwestia bohatera"] [--list]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from bajka.audio import play_wav_bytes
from bajka.config import ConfigError, get_float, load_env

log = logging.getLogger(__name__)

DEMO_TEXT = "Cześć! Jestem gotowa na przygodę. A ty?"
INSTALL_HINT = 'pip install -e ".[local]" (tylko Windows)'


class VoiceNotFoundError(RuntimeError):
    """W Windows nie ma głosu dla wybranego języka albo nazwy."""


@dataclass(frozen=True)
class WindowsTtsSettings:
    language: str = "pl-PL"
    voice: str = ""  # fragment nazwy głosu, np. "Paulina"; pusto = pierwszy głos dla języka
    rate: float = 0.9  # tempo: 1.0 normalne, mniej = wolniej (dzieci lepiej nadążają)
    pitch: float = 1.0  # wysokość: 0.0–2.0, wyżej brzmi bardziej bajkowo

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> WindowsTtsSettings:
        return cls(
            language=env.get("BAJKA_LANGUAGE") or cls.language,
            voice=env.get("BAJKA_WINDOWS_VOICE") or cls.voice,
            rate=get_float(env, "BAJKA_WINDOWS_VOICE_RATE", cls.rate),
            pitch=get_float(env, "BAJKA_WINDOWS_VOICE_PITCH", cls.pitch),
        )


def pick_voice(voices: Sequence[Any], language: str, name: str = "") -> Any:
    matching = [v for v in voices if v.language.lower() == language.lower()]
    if name:
        matching = [v for v in matching if name.lower() in v.display_name.lower()]
    if not matching:
        available = ", ".join(f"{v.display_name} ({v.language})" for v in voices) or "brak"
        raise VoiceNotFoundError(
            f"Brak głosu Windows dla {language}{f' o nazwie {name!r}' if name else ''}. "
            f"Dodaj głos w Ustawienia → Czas i język → Mowa. Zainstalowane: {available}"
        )
    return matching[0]


async def synthesize_wav(synthesizer: Any, text: str) -> bytes:
    """Syntezuje tekst do pamięci i zwraca plik WAV."""
    from winrt.windows.storage.streams import DataReader

    stream = await synthesizer.synthesize_text_to_stream_async(text)
    size = stream.size
    reader = DataReader(stream.get_input_stream_at(0))
    await reader.load_async(size)
    data = bytearray(size)
    reader.read_bytes(data)
    return bytes(data)


def windows_voices() -> Sequence[Any]:
    try:
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    except ImportError as exc:
        raise VoiceNotFoundError(f"Brak pakietów WinRT do syntezy mowy. Zainstaluj: {INSTALL_HINT}") from exc
    return SpeechSynthesizer.all_voices


class WindowsVoice:
    def __init__(self, synthesize: Callable[[str], bytes], play_wav: Callable[[bytes], None] = play_wav_bytes) -> None:
        self._synthesize = synthesize
        self._play_wav = play_wav

    @classmethod
    def from_settings(cls, settings: WindowsTtsSettings) -> WindowsVoice:
        chosen = pick_voice(windows_voices(), settings.language, settings.voice)  # tu wychodzi brak pakietów WinRT
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer

        synthesizer = SpeechSynthesizer()
        synthesizer.voice = chosen
        synthesizer.options.speaking_rate = settings.rate
        synthesizer.options.audio_pitch = settings.pitch
        log.info("Głos bohatera: %s", synthesizer.voice.display_name)
        # Silnik bajki działa w zwykłym wątku, więc każdą syntezę uruchamiamy we własnej pętli asyncio.
        return cls(lambda text: asyncio.run(synthesize_wav(synthesizer, text)))

    def say(self, text: str) -> None:
        log.info("Bohater: %s", text)
        self._play_wav(self._synthesize(text))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.local_tts", description="Test głosu bohatera z syntezatora Windows (offline)."
    )
    parser.add_argument("text", nargs="?", default=DEMO_TEXT, help="kwestia do wypowiedzenia")
    parser.add_argument("--list", action="store_true", help="wypisz głosy zainstalowane w Windows")
    args = parser.parse_args(argv)
    try:
        settings = WindowsTtsSettings.from_env(load_env())
        if args.list:
            for voice in windows_voices():
                print(f"{voice.display_name} ({voice.language})")
            return 0
        voice = WindowsVoice.from_settings(settings)
    except (ConfigError, VoiceNotFoundError, ImportError) as exc:
        print(exc, file=sys.stderr)
        return 2

    print(f"Bohater mówi: {args.text}", flush=True)
    started = time.perf_counter()
    try:
        voice.say(args.text)
    except Exception as exc:  # demo ma pokazać każdy błąd syntezatora, a nie wywrócić się
        print(f"Błąd syntezatora Windows: {exc}", file=sys.stderr)
        return 1
    print(f"Gotowe ({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Wspólne odtwarzanie dźwięku dla modułów głosu bohatera (`bajka/tts.py`, `bajka/local_tts.py`)."""

from __future__ import annotations

import io
import wave


def play_wav_bytes(data: bytes) -> None:
    """Odtwarza WAV (PCM 16-bit) i blokuje do końca, więc mikrofon nie słyszy bohatera."""
    import numpy as np
    import sounddevice as sd

    with wave.open(io.BytesIO(data)) as wav:
        rate, channels = wav.getframerate(), wav.getnchannels()
        frames = wav.readframes(wav.getnframes())
    sd.play(np.frombuffer(frames, dtype=np.int16).reshape(-1, channels), rate)
    sd.wait()

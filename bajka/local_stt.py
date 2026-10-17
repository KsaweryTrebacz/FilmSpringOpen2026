"""Rozpoznawanie mowy dziecka lokalnie: mikrofon → Whisper w Foundry Local (NPU/GPU/CPU), bez chmury.

Moduł spełnia kontrakt `bajka.ports.Listener`. Lokalny Whisper dostaje gotowe nagranie, więc początek
i koniec wypowiedzi wykrywa tu prosty detektor głośności (VAD) — tak jak Azure robi to po swojej stronie.
Test z prawdziwym mikrofonem: python -m bajka.local_stt [--repeat N]
"""

from __future__ import annotations

import argparse
import logging
import os
import queue
import sys
import tempfile
import time
import wave
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from bajka.config import ConfigError, get_int, load_env
from bajka.foundry import FoundryError, load_model, read_device

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # Whisper pracuje na 16 kHz mono
FRAME_MS = 30
PRE_ROLL_MS = 300  # tyle nagrania sprzed wykrycia mowy dołączamy, żeby nie uciąć pierwszej głoski
MIN_SPEECH_MS = 200  # krótszy hałas (stuknięcie, kaszel) to nie wypowiedź

# Whisper na ciszy lub szumie potrafi "usłyszeć" napisy z filmów, na których się uczył.
HALLUCINATIONS = ("amara.org", "napisy stworzone", "napisy wykonane", "subskrybuj", "dziękuję za obejrzenie")


@dataclass(frozen=True)
class LocalSttSettings:
    model: str = "whisper-tiny"  # alias z katalogu Foundry Local (python -m bajka.foundry)
    device: str = "auto"
    language: str = "pl"  # Whisper oczekuje kodu języka bez regionu
    initial_silence_ms: int = 6000  # ile czekamy, aż dziecko zacznie mówić
    end_silence_ms: int = 1200  # ile ciszy kończy wypowiedź
    max_utterance_ms: int = 12000
    vad_threshold: int = 500  # głośność ramki (RMS próbek 16-bit), od której to mowa; w hałasie zwiększ

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LocalSttSettings:
        return cls(
            model=env.get("FOUNDRY_STT_MODEL") or cls.model,
            device=read_device(env),
            language=(env.get("BAJKA_LANGUAGE") or cls.language).split("-")[0].lower(),
            initial_silence_ms=get_int(env, "BAJKA_INITIAL_SILENCE_MS", cls.initial_silence_ms),
            end_silence_ms=get_int(env, "BAJKA_END_SILENCE_MS", cls.end_silence_ms),
            max_utterance_ms=get_int(env, "BAJKA_MAX_UTTERANCE_MS", cls.max_utterance_ms),
            vad_threshold=get_int(env, "BAJKA_VAD_THRESHOLD", cls.vad_threshold),
        )


def loudness(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float64) ** 2))) if frame.size else 0.0


def cut_utterance(frames: Iterable[np.ndarray], settings: LocalSttSettings, frame_ms: int = FRAME_MS) -> np.ndarray | None:
    """Wycina z ramek mikrofonu jedną wypowiedź albo zwraca None, gdy dziecko milczało."""
    pre_roll: deque[np.ndarray] = deque(maxlen=max(1, PRE_ROLL_MS // frame_ms))
    speech: list[np.ndarray] = []
    waited = silent = loud_ms = 0
    for frame in frames:
        loud = loudness(frame) >= settings.vad_threshold
        if not speech:
            pre_roll.append(frame)
            if loud:
                speech.extend(pre_roll)
                loud_ms = frame_ms
                continue
            waited += frame_ms
            if waited >= settings.initial_silence_ms:
                return None
            continue
        speech.append(frame)
        if loud:
            loud_ms += frame_ms
            silent = 0
        else:
            silent += frame_ms
        if silent >= settings.end_silence_ms or len(speech) * frame_ms >= settings.max_utterance_ms:
            break
    if loud_ms < MIN_SPEECH_MS:
        return None
    return np.concatenate(speech)


def clean_transcript(text: str) -> str | None:
    text = " ".join(text.split())
    if not text or any(phrase in text.lower() for phrase in HALLUCINATIONS):
        return None
    return text


def microphone_frames(sample_rate: int = SAMPLE_RATE, frame_ms: int = FRAME_MS) -> Iterator[np.ndarray]:
    """Ramki z domyślnego mikrofonu; mikrofon jest otwarty tylko na czas słuchania (półdupleks)."""
    import sounddevice as sd

    frames: queue.Queue[np.ndarray] = queue.Queue()

    def on_audio(indata: np.ndarray, _frames: int, _time: Any, _status: Any) -> None:
        frames.put(indata[:, 0].copy())

    with sd.InputStream(
        samplerate=sample_rate, channels=1, dtype="int16", blocksize=sample_rate * frame_ms // 1000, callback=on_audio
    ):
        while True:
            yield frames.get(timeout=2.0)  # brak ramek przez 2 s = mikrofon nie działa


def write_wav(path: str, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.astype("<i2").tobytes())


class FoundryTranscriber:
    """Whisper z Foundry Local; nagranie przekazujemy jako plik WAV, tak jak w przykładach Microsoftu."""

    def __init__(self, model: Any, language: str, alias: str = "whisper-tiny") -> None:
        self._model = model
        self._language = language
        self._alias = alias

    @classmethod
    def from_settings(cls, settings: LocalSttSettings) -> FoundryTranscriber:
        return cls(load_model(settings.model, settings.device), settings.language, settings.model)

    def _transcribe_file(self, path: str, options: Any) -> str:
        from foundry_local_sdk import AudioItem, AudioSession, Request, SpeechResultItem, TextItem

        with AudioSession(self._model) as session, Request() as request:
            request.add_item(AudioItem.from_uri(path))
            request.set_options(options)
            with session.process_request(request) as response:
                items = list(response)
                results = [item.text for item in items if isinstance(item, SpeechResultItem)]
                texts = results or [item.text for item in items if isinstance(item, TextItem)]
                return " ".join(texts)

    def __call__(self, samples: np.ndarray) -> str:
        from foundry_local_sdk import RequestOptions, SearchOptions

        handle, path = tempfile.mkstemp(suffix=".wav", prefix="bajka-")
        os.close(handle)
        try:
            write_wav(path, samples)
            options = RequestOptions(search=SearchOptions(temperature=0.0), additional_options={"language": self._language})
            try:
                return self._transcribe_file(path, options)
            except Exception as exc:
                if any(err in str(exc).lower() for err in ("cudnn", "cuda", "kernel image", "device")):
                    log.warning("Błąd akceleratora GPU (%s), przełączam Whisper na CPU...", exc)
                    self._model = load_model(self._alias, "CPU")
                    return self._transcribe_file(path, options)
                raise
        finally:
            os.remove(path)


class LocalListener:
    def __init__(
        self,
        transcribe: Callable[[np.ndarray], str],
        settings: LocalSttSettings,
        frames: Callable[[], Iterable[np.ndarray]] = microphone_frames,
    ) -> None:
        self._transcribe = transcribe
        self._settings = settings
        self._frames = frames

    @classmethod
    def from_settings(cls, settings: LocalSttSettings) -> LocalListener:
        return cls(FoundryTranscriber.from_settings(settings), settings)

    def listen(self) -> str | None:
        log.info("Słucham…")
        frames = self._frames()
        try:
            utterance = cut_utterance(frames, self._settings)
        finally:
            close = getattr(frames, "close", None)
            if close is not None:
                close()  # zamyka mikrofon, zanim bohater zacznie mówić
        if utterance is None:
            log.info("Cisza")
            return None
        text = clean_transcript(self._transcribe(utterance))
        log.info("Rozpoznano: %r", text)
        return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.local_stt", description="Test lokalnego rozpoznawania mowy (Whisper w Foundry Local)."
    )
    parser.add_argument("--repeat", type=int, default=3, help="ile wypowiedzi wysłuchać (domyślnie 3)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        settings = LocalSttSettings.from_env(load_env())
        listener = LocalListener.from_settings(settings)
    except (ConfigError, FoundryError) as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:  # demo ma pokazać każdy błąd Foundry Local, a nie wywrócić się
        print(f"Błąd Foundry Local: {exc}", file=sys.stderr)
        return 1

    for _ in range(args.repeat):
        print("Mów teraz…", flush=True)
        started = time.perf_counter()
        try:
            text = listener.listen()
        except Exception as exc:
            print(f"Błąd mikrofonu albo modelu: {exc}", file=sys.stderr)
            return 1
        elapsed = time.perf_counter() - started
        print(f"Rozpoznano: {text!r} ({elapsed:.1f} s)" if text else f"Cisza, nic nie rozpoznano ({elapsed:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import wave

import numpy as np
import pytest

from bajka.config import ConfigError
from bajka.local_stt import LocalListener, LocalSttSettings, clean_transcript, cut_utterance, write_wav
from bajka.ports import Listener

FRAME = 480  # 30 ms przy 16 kHz
SETTINGS = LocalSttSettings(initial_silence_ms=300, end_silence_ms=150, max_utterance_ms=3000, vad_threshold=500)


def quiet(count):
    return [np.zeros(FRAME, dtype=np.int16) for _ in range(count)]


def loud(count, value=3000):
    return [np.full(FRAME, value, dtype=np.int16) for _ in range(count)]


def test_settings_defaults_need_no_keys():
    settings = LocalSttSettings.from_env({})

    assert settings.model == "whisper-tiny"
    assert settings.language == "pl"
    assert settings.initial_silence_ms == 6000


def test_settings_strip_region_from_language_and_read_tuning():
    settings = LocalSttSettings.from_env(
        {"BAJKA_LANGUAGE": "pl-PL", "FOUNDRY_STT_MODEL": "whisper-small", "BAJKA_VAD_THRESHOLD": "900"}
    )

    assert settings.language == "pl"
    assert settings.model == "whisper-small"
    assert settings.vad_threshold == 900


def test_bad_threshold_is_rejected():
    with pytest.raises(ConfigError, match="BAJKA_VAD_THRESHOLD"):
        LocalSttSettings.from_env({"BAJKA_VAD_THRESHOLD": "głośno"})


def test_silence_until_timeout_means_no_utterance():
    assert cut_utterance(quiet(20), SETTINGS) is None


def test_utterance_keeps_pre_roll_and_ends_after_silence():
    frames = quiet(3) + loud(10) + quiet(5) + loud(10)  # druga wypowiedź już nie należy do tej

    utterance = cut_utterance(frames, SETTINGS)

    # 3 ramki ciszy przed mową (pre-roll), 10 ramek mowy, 5 ramek ciszy kończących wypowiedź
    assert len(utterance) == (3 + 10 + 5) * FRAME


def test_short_click_is_not_speech():
    assert cut_utterance(quiet(2) + loud(2) + quiet(20), SETTINGS) is None


def test_long_speech_is_cut_at_max_length():
    utterance = cut_utterance(loud(500), SETTINGS)

    assert len(utterance) == 3000 // 30 * FRAME


def test_whisper_hallucinations_count_as_silence():
    assert clean_transcript("  Do   lasu! ") == "Do lasu!"
    assert clean_transcript("Napisy stworzone przez społeczność Amara.org") is None
    assert clean_transcript("   ") is None


def test_listener_transcribes_cut_utterance_and_closes_microphone():
    heard = []
    closed = []

    def frames():
        try:
            yield from quiet(2) + loud(10) + quiet(10)
        finally:
            closed.append(True)

    def transcribe(samples):
        heard.append(len(samples))
        return " do jaskini "

    listener = LocalListener(transcribe, SETTINGS, frames=frames)

    assert isinstance(listener, Listener)
    assert listener.listen() == "do jaskini"
    assert heard and closed == [True]


def test_listener_returns_none_on_silence_without_calling_model():
    def transcribe(samples):
        pytest.fail("model nie powinien dostać ciszy")

    assert LocalListener(transcribe, SETTINGS, frames=lambda: iter(quiet(50))).listen() is None


def test_wav_is_16_bit_mono(tmp_path):
    path = tmp_path / "nagranie.wav"

    write_wav(str(path), np.array([0, 1000, -1000], dtype=np.int16))

    with wave.open(str(path)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) == (1, 2, 16000, 3)

import asyncio
from types import SimpleNamespace

import pytest

from bajka.config import ConfigError
from bajka.local_tts import VoiceNotFoundError, WindowsTtsSettings, WindowsVoice, main, pick_voice
from bajka.ports import Voice

VOICES = [
    SimpleNamespace(display_name="Microsoft David", language="en-US"),
    SimpleNamespace(display_name="Microsoft Paulina", language="pl-PL"),
    SimpleNamespace(display_name="Microsoft Adam", language="pl-PL"),
]


def test_settings_defaults_need_no_keys():
    settings = WindowsTtsSettings.from_env({})

    assert settings.language == "pl-PL"
    assert settings.rate == 0.9
    assert settings.pitch == 1.0


def test_settings_read_voice_rate_and_pitch():
    settings = WindowsTtsSettings.from_env(
        {"BAJKA_WINDOWS_VOICE": "Paulina", "BAJKA_WINDOWS_VOICE_RATE": "0,8", "BAJKA_WINDOWS_VOICE_PITCH": "1.3"}
    )

    assert (settings.voice, settings.rate, settings.pitch) == ("Paulina", 0.8, 1.3)


def test_bad_rate_is_rejected():
    with pytest.raises(ConfigError, match="BAJKA_WINDOWS_VOICE_RATE"):
        WindowsTtsSettings.from_env({"BAJKA_WINDOWS_VOICE_RATE": "szybko"})


def test_first_voice_for_language_is_picked():
    assert pick_voice(VOICES, "pl-pl").display_name == "Microsoft Paulina"


def test_voice_can_be_picked_by_name_fragment():
    assert pick_voice(VOICES, "pl-PL", "adam").display_name == "Microsoft Adam"


def test_missing_voice_lists_installed_voices():
    with pytest.raises(VoiceNotFoundError, match="Microsoft David"):
        pick_voice(VOICES, "de-DE")


def test_voice_synthesizes_and_plays_until_done():
    played = []
    voice = WindowsVoice(lambda text: f"WAV:{text}".encode(), play_wav=played.append)

    voice.say("Do lasu!")

    assert isinstance(voice, Voice)
    assert played == [b"WAV:Do lasu!"]


def test_synthesis_reads_whole_stream(monkeypatch):
    import sys

    from bajka import local_tts

    class FakeReader:
        def __init__(self, stream):
            self._data = stream.data

        async def load_async(self, size):
            return size

        def read_bytes(self, buffer):
            buffer[:] = self._data

    stream = SimpleNamespace(data=b"RIFF....WAVE", size=12, get_input_stream_at=lambda pos: stream)

    async def synthesize_text_to_stream_async(text):
        return stream

    streams_module = SimpleNamespace(DataReader=FakeReader)
    monkeypatch.setitem(sys.modules, "winrt.windows.storage.streams", streams_module)
    synthesizer = SimpleNamespace(synthesize_text_to_stream_async=synthesize_text_to_stream_async)

    assert asyncio.run(local_tts.synthesize_wav(synthesizer, "Hej")) == b"RIFF....WAVE"


def test_demo_without_winrt_explains_how_to_install(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "winrt.windows.media.speechsynthesis", None)  # import rzuci ImportError

    assert main(["--list"]) == 2
    assert "pip install" in capsys.readouterr().err

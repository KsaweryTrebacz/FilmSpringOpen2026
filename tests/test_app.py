import argparse
import sys
import threading

import pytest
import yaml

from bajka.app import build_meter, build_resolver, choose_backend, main, mobile_enabled, parse_args, run_window
from bajka.config import ConfigError
from bajka.keywords import KeywordIntentResolver

LLM_VARS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
SPEECH_VARS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")


def write_scenario(path, scenario_dict):
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


def write_media(directory, scenario_dict):
    for scene in scenario_dict["scenes"].values():
        for key in ("clip", "idle"):
            if key in scene:
                (directory / scene[key]).touch()


def test_flags_are_parsed():
    args = parse_args(["bajka.yaml", "--text", "--windowed"])

    assert args.scenario.name == "bajka.yaml"
    assert args.text and args.windowed


def test_default_is_fullscreen_with_voice():
    args = parse_args(["bajka.yaml"])

    assert not args.text and not args.windowed and not args.no_llm
    assert args.backend is None  # wybór z BAJKA_BACKEND albo "local"


def test_backend_defaults_to_local_and_can_come_from_env():
    assert choose_backend(parse_args(["b.yaml"]), {}) == "local"
    assert choose_backend(parse_args(["b.yaml"]), {"BAJKA_BACKEND": "azure"}) == "azure"
    assert choose_backend(parse_args(["b.yaml", "--backend", "local"]), {"BAJKA_BACKEND": "azure"}) == "local"
    with pytest.raises(ConfigError, match="BAJKA_BACKEND"):
        choose_backend(argparse.Namespace(backend=None), {"BAJKA_BACKEND": "chmura"})


def test_shout_meter_is_typed_in_text_mode_and_uses_microphone_otherwise():
    from bajka.console import ConsoleMeter
    from bajka.vote import MicrophoneMeter

    assert isinstance(build_meter({}, text_mode=True), ConsoleMeter)
    assert isinstance(build_meter({}, text_mode=False), MicrophoneMeter)  # mikrofon otwiera się dopiero przy pomiarze


def test_mobile_audience_is_enabled_by_flag_or_env():
    assert not mobile_enabled(parse_args(["b.yaml"]), {})
    assert mobile_enabled(parse_args(["b.yaml", "--mobile"]), {})
    assert mobile_enabled(parse_args(["b.yaml"]), {"BAJKA_MOBILE": "1"})


def test_no_llm_uses_keywords_without_loading_any_model():
    resolver = build_resolver({}, "local", use_llm=False, hero="Lisek")

    assert isinstance(resolver, KeywordIntentResolver)


def test_missing_scenario_file_exits_with_code_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert main([str(tmp_path / "nie_ma.yaml")]) == 2


def test_missing_settings_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)  # w katalogu testu nie ma pliku .env
    for name in LLM_VARS + SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--backend", "azure"]) == 2


def test_missing_speech_keys_exit_with_code_2_before_opening_window(tmp_path, monkeypatch, scenario_dict, caplog):
    monkeypatch.chdir(tmp_path)
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    for name in SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)  # klipy są, brakuje tylko kluczy mowy
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--backend", "azure"]) == 2
    assert "AZURE_SPEECH_KEY" in caplog.text


def test_local_backend_without_windows_voice_packages_exits_with_code_2(tmp_path, monkeypatch, scenario_dict, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BAJKA_BACKEND", raising=False)
    monkeypatch.setitem(sys.modules, "winrt.windows.media.speechsynthesis", None)  # jak na komputerze bez WinRT
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path)]) == 2
    assert "pip install" in caplog.text


def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--text"]) == 2


# Zamykanie okna (Esc)


class FakeRoot:
    """Okno tkinter bez ekranu: mainloop od razu „naciska Esc”."""

    def __init__(self, events):
        self._events = events
        self._handlers = {}

    def bind(self, sequence, handler):
        self._handlers[sequence] = handler

    def protocol(self, name, handler):
        self._handlers[name] = handler

    def after(self, _ms, _callback):
        pass

    def mainloop(self):
        self._handlers["<Escape>"]()

    def destroy(self):
        self._events.append("okno zamknięte")


def test_escape_stops_the_story_before_closing_player_and_window():
    events = []
    running = threading.Event()

    class FakeEngine:
        def run(self):
            running.wait(timeout=5)
            return []

        def stop(self):
            events.append("silnik zatrzymany")
            running.set()

    class FakePlayer:
        def stop(self):
            events.append("odtwarzacz zatrzymany")

    run_window(FakeRoot(events), FakePlayer(), FakeEngine())

    assert events == ["silnik zatrzymany", "odtwarzacz zatrzymany", "okno zamknięte"]

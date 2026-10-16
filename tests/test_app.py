import argparse
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest
import yaml

from bajka.app import (
    build_meter,
    build_panel,
    build_resolver,
    choose_backend,
    main,
    mobile_enabled,
    panel_enabled,
    parse_args,
    run_window,
)
from bajka.config import ConfigError
from bajka.keywords import KeywordIntentResolver
from bajka.ports import AudiencePulse, ShowObserver
from bajka.pulse import PulseSettings

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


def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict, caplog):
    monkeypatch.chdir(tmp_path)
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--text"]) == 2
    assert "Brak plików wideo" in caplog.text


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


# Panel dla jury i tętno sali


def test_panel_is_enabled_by_flag_or_env():
    assert not panel_enabled(parse_args(["b.yaml"]), {})
    assert panel_enabled(parse_args(["b.yaml", "--panel"]), {})
    assert panel_enabled(parse_args(["b.yaml"]), {"BAJKA_PANEL": "tak"})


def test_build_panel_connects_pulse_simulator_and_panel_state(scenario):
    panel = build_panel({"BAJKA_PULSE_START_BPM": "80"}, scenario)

    assert isinstance(panel.pulse, AudiencePulse)
    assert isinstance(panel.state, ShowObserver)
    assert panel.pulse_settings.start_bpm == 80.0
    assert panel.pulse.read().bpm == pytest.approx(80.0, abs=2)


# Zmienne środowiskowe, które z komputera dewelopera zmieniłyby wynik testów uruchamiających main()
ENV_VARS_THAT_CHANGE_MAIN = (
    "BAJKA_PANEL",
    "BAJKA_PANEL_HOST",
    "BAJKA_PANEL_PORT",
    "BAJKA_MOBILE",
    "BAJKA_BACKEND",
    "BAJKA_PULSE_VIEWERS",
    "BAJKA_PULSE_START_BPM",
    "BAJKA_PULSE_EXCITED",
    "BAJKA_PULSE_BORED",
)


class SpyServer:
    """Serwer panelu bez sieci: zapisuje, co się z nim działo."""

    def __init__(self, events):
        self._events = events

    def start(self):
        self._events.append("panel uruchomiony")
        return "http://127.0.0.1:8090/"

    def stop(self):
        self._events.append("panel zatrzymany")


def install_spies(tmp_path, monkeypatch, scenario_dict, make_server=SpyServer):
    """Podmienia panel, silnik, okno i odtwarzacz; zwraca ścieżkę scenariusza, argumenty silnika i zdarzenia."""
    monkeypatch.chdir(tmp_path)
    for name in ENV_VARS_THAT_CHANGE_MAIN:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)
    created, events = {}, []

    class SpyEngine:
        def __init__(self, *args, **kwargs):
            created.update(kwargs)

    real_build_panel = build_panel
    monkeypatch.setattr(
        "bajka.app.build_panel", lambda env, s: replace(real_build_panel(env, s), server=make_server(events))
    )
    monkeypatch.setattr("bajka.app.StoryEngine", SpyEngine)
    monkeypatch.setattr("bajka.app.run_window", lambda root, player, engine: events.append("film"))
    monkeypatch.setattr("tkinter.Tk", lambda: object())  # bez okna i bez VLC
    monkeypatch.setitem(sys.modules, "bajka.player", SimpleNamespace(VlcPlayer=lambda root, fullscreen=True: object()))
    return path, created, events


def run_main_with_spies(tmp_path, monkeypatch, scenario_dict, *flags):
    path, created, events = install_spies(tmp_path, monkeypatch, scenario_dict)

    assert main([str(path), "--text", "--no-llm", "--windowed", *flags]) == 0
    return created, events


def test_main_with_panel_starts_it_and_gives_pulse_and_observer_to_the_engine(tmp_path, monkeypatch, scenario_dict):
    created, events = run_main_with_spies(tmp_path, monkeypatch, scenario_dict, "--panel")

    assert events == ["panel uruchomiony", "film", "panel zatrzymany"]
    assert isinstance(created["pulse"], AudiencePulse)
    assert isinstance(created["observer"], ShowObserver)
    assert created["pulse_settings"] == PulseSettings()


def test_main_without_panel_runs_the_film_without_pulse(tmp_path, monkeypatch, scenario_dict):
    created, events = run_main_with_spies(tmp_path, monkeypatch, scenario_dict)

    assert events == ["film"]
    assert created["pulse"] is None and created["observer"] is None


def test_main_exits_with_code_2_when_the_panel_cannot_start(tmp_path, monkeypatch, scenario_dict, caplog):
    class BusyServer(SpyServer):
        def start(self):
            raise OSError("port zajęty")

    path, created, events = install_spies(tmp_path, monkeypatch, scenario_dict, make_server=BusyServer)

    assert main([str(path), "--text", "--no-llm", "--windowed", "--panel"]) == 2
    assert "Nie udało się uruchomić panelu dla jury" in caplog.text
    assert "film" not in events and created == {}  # okno filmu nie ruszyło, silnik nie powstał

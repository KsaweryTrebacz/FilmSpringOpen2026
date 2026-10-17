import argparse
import io
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest
import yaml

from bajka.app import (
    build_panel,
    build_resolver,
    choice_seconds,
    choose_backend,
    choose_player,
    main,
    mobile_enabled,
    panel_enabled,
    parse_args,
    run_episodes,
    run_window,
)
from bajka.config import ConfigError
from bajka.console import ConsolePlayer, ConsoleViewer, ConsoleVoice
from bajka.engine import DEFAULT_CHOICE_SECONDS
from bajka.keywords import KeywordIntentResolver
from bajka.ports import AudiencePulse, ShowObserver
from bajka.pulse import PulseSettings
from bajka.web_player import WebEpisode

LLM_VARS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
SPEECH_VARS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")
# Zmienne środowiskowe, które z komputera dewelopera zmieniłyby wynik testów uruchamiających main()
ENV_VARS_THAT_CHANGE_MAIN = (
    "BAJKA_PANEL",
    "BAJKA_PANEL_HOST",
    "BAJKA_PANEL_PORT",
    "BAJKA_MOBILE",
    "BAJKA_BACKEND",
    "BAJKA_PLAYER",
    "BAJKA_CHOICE_SECONDS",
    "BAJKA_MONTAGE",
    "BAJKA_WEB_HOST",
    "BAJKA_WEB_PORT",
    "BAJKA_WEB_OPEN",
    "BAJKA_PULSE_VIEWERS",
    "BAJKA_PULSE_START_BPM",
    "BAJKA_PULSE_EXCITED",
    "BAJKA_PULSE_BORED",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # w katalogu testu nie ma pliku .env
    for name in ENV_VARS_THAT_CHANGE_MAIN:
        monkeypatch.delenv(name, raising=False)
    # Odcinek w przeglądarce czekałby na stronę bez końca: w testach nikt jej nie otworzy.
    monkeypatch.setattr("bajka.app.run_episodes", lambda episode, make_engine: None)
    monkeypatch.setattr("bajka.app.webbrowser", SimpleNamespace(open=lambda url: None))
    monkeypatch.setenv("BAJKA_WEB_PORT", "0")


def write_scenario(path, scenario_dict):
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def write_media(directory, scenario_dict):
    for scene in scenario_dict["scenes"].values():
        for key in ("clip", "idle"):
            if key in scene:
                (directory / scene[key]).touch()


def test_flags_are_parsed():
    args = parse_args(["bajka.yaml", "--text", "--windowed", "--no-mic", "--no-browser"])

    assert args.scenario.name == "bajka.yaml"
    assert args.text and args.windowed and args.no_mic and args.no_browser


def test_default_is_the_web_player_with_voice_and_model():
    args = parse_args(["bajka.yaml"])

    assert not args.text and not args.no_mic and not args.no_llm
    assert args.backend is None and args.player is None  # wybór z .env albo domyślny
    assert choose_player(args, {}) == "web"


def test_player_can_come_from_flag_or_env():
    assert choose_player(parse_args(["b.yaml"]), {"BAJKA_PLAYER": "vlc"}) == "vlc"
    assert choose_player(parse_args(["b.yaml", "--player", "web"]), {"BAJKA_PLAYER": "vlc"}) == "web"
    with pytest.raises(ConfigError, match="BAJKA_PLAYER"):
        choose_player(argparse.Namespace(player=None), {"BAJKA_PLAYER": "kino"})


def test_backend_defaults_to_local_and_can_come_from_env():
    assert choose_backend(parse_args(["b.yaml"]), {}) == "local"
    assert choose_backend(parse_args(["b.yaml"]), {"BAJKA_BACKEND": "azure"}) == "azure"
    assert choose_backend(parse_args(["b.yaml", "--backend", "local"]), {"BAJKA_BACKEND": "azure"}) == "local"
    with pytest.raises(ConfigError, match="BAJKA_BACKEND"):
        choose_backend(argparse.Namespace(backend=None), {"BAJKA_BACKEND": "chmura"})


def test_choice_window_time_comes_from_env_within_limits():
    assert choice_seconds({}) == DEFAULT_CHOICE_SECONDS
    assert choice_seconds({"BAJKA_CHOICE_SECONDS": "20"}) == 20.0
    with pytest.raises(ConfigError, match="BAJKA_CHOICE_SECONDS"):
        choice_seconds({"BAJKA_CHOICE_SECONDS": "1"})


def test_mobile_second_screen_is_enabled_by_flag_or_env():
    assert not mobile_enabled(parse_args(["b.yaml"]), {})
    assert mobile_enabled(parse_args(["b.yaml", "--mobile"]), {})
    assert mobile_enabled(parse_args(["b.yaml"]), {"BAJKA_MOBILE": "1"})


def test_no_llm_uses_keywords_without_loading_any_model():
    resolver = build_resolver({}, "local", use_llm=False, hero="Lisek")

    assert isinstance(resolver, KeywordIntentResolver)


def test_missing_scenario_file_exits_with_code_2(tmp_path):
    assert main([str(tmp_path / "nie_ma.yaml")]) == 2


def test_missing_settings_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    for name in LLM_VARS + SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--backend", "azure"]) == 2


def test_missing_speech_keys_exit_with_code_2_before_the_vlc_episode_starts(tmp_path, monkeypatch, scenario_dict, caplog):
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    for name in SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)  # klipy są, brakuje tylko kluczy mowy
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--backend", "azure", "--player", "vlc"]) == 2
    assert "AZURE_SPEECH_KEY" in caplog.text


def test_web_player_without_speech_recognition_falls_back_to_the_browser(tmp_path, monkeypatch, scenario_dict, caplog):
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    for name in SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--backend", "azure"]) == 0  # odcinek rusza, głos rozpoznaje przeglądarka
    assert "działa rozpoznawanie w przeglądarce" in caplog.text


def test_local_web_player_without_foundry_local_exits_with_code_2(tmp_path, monkeypatch, scenario_dict, caplog):
    monkeypatch.setitem(sys.modules, "foundry_local_sdk", None)  # jak na komputerze bez Foundry Local
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--no-browser"]) == 2
    assert "foundry-local-sdk" in caplog.text


def test_local_vlc_player_without_windows_voice_packages_exits_with_code_2(tmp_path, monkeypatch, scenario_dict, caplog):
    monkeypatch.setitem(sys.modules, "winrt.windows.media.speechsynthesis", None)  # jak na komputerze bez WinRT
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--player", "vlc"]) == 2
    assert "pip install" in caplog.text


def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict, caplog):
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--no-llm", "--no-mic", "--no-browser"]) == 2
    assert "Brak plików wideo" in caplog.text and "placeholders" in caplog.text


def test_text_mode_runs_the_whole_episode_in_the_console_without_video(tmp_path, monkeypatch, scenario_dict, capsys):
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)  # bez klipów: w konsoli nie są potrzebne
    monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))  # widz wybiera opcję 2

    assert main([str(path), "--text", "--no-llm"]) == 0
    printed = capsys.readouterr().out
    assert "[klip] intro.mp4" in printed and "  2. Jaskinia" in printed
    assert "Postać: Do jaskini! Mam latarkę!" in printed and "[klip] jaskinia.mp4" in printed


# Zamykanie okna VLC (Esc)


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


# Odcinek w przeglądarce: ekran końcowy i „obejrzyj jeszcze raz”


class FakeEpisode:
    def __init__(self, *wants_again):
        self._wants_again = list(wants_again)
        self.finished = []
        self.on_stop = None

    def finish(self, visited, decisions=None):
        self.finished.append(visited)
        return self._wants_again.pop(0)


def test_episode_can_be_watched_again_until_the_viewer_closes_it():
    episode = FakeEpisode(True, False)
    engines = []

    class FakeEngine:
        def __init__(self):
            engines.append(self)

        def run(self):
            return ["intro", "las" if len(engines) == 1 else "jaskinia"]

        def stop(self):
            pass

    run_episodes(episode, FakeEngine)

    assert episode.finished == [["intro", "las"], ["intro", "jaskinia"]]
    assert len(engines) == 2 and episode.on_stop == engines[1].stop  # „Zakończ” zatrzymuje bieżący silnik


def test_engine_error_still_shows_the_end_screen(caplog):
    episode = FakeEpisode(False)

    class BrokenEngine:
        def run(self):
            raise RuntimeError("awaria")

        def stop(self):
            pass

    run_episodes(episode, BrokenEngine)

    assert episode.finished == [[]] and "Odcinek przerwany błędem" in caplog.text


# Panel podglądu i tętno widza


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
    """Podmienia serwer panelu i silnik; zwraca ścieżkę scenariusza, argumenty silnika i zdarzenia."""
    write_media(tmp_path, scenario_dict)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)
    created, events = {}, []

    class SpyEngine:
        def __init__(self, *args, **kwargs):
            created.update(kwargs, args=args)

        def run(self):
            events.append("odcinek")
            return []

        def stop(self):
            pass

    real_build_panel = build_panel
    monkeypatch.setattr(
        "bajka.app.build_panel", lambda env, s: replace(real_build_panel(env, s), server=make_server(events))
    )
    monkeypatch.setattr("bajka.app.StoryEngine", SpyEngine)
    return path, created, events


def test_main_with_panel_starts_it_and_gives_pulse_and_observer_to_the_engine(tmp_path, monkeypatch, scenario_dict):
    path, created, events = install_spies(tmp_path, monkeypatch, scenario_dict)

    assert main([str(path), "--text", "--no-llm", "--panel"]) == 0
    assert events == ["panel uruchomiony", "odcinek", "panel zatrzymany"]
    assert isinstance(created["pulse"], AudiencePulse)
    assert isinstance(created["observer"], ShowObserver)
    assert created["pulse_settings"] == PulseSettings()
    _, player, viewer, voice, _ = created["args"]
    assert (type(player), type(viewer), type(voice)) == (ConsolePlayer, ConsoleViewer, ConsoleVoice)


def test_main_without_panel_runs_the_episode_without_pulse(tmp_path, monkeypatch, scenario_dict):
    path, created, events = install_spies(tmp_path, monkeypatch, scenario_dict)
    monkeypatch.setenv("BAJKA_CHOICE_SECONDS", "15")

    assert main([str(path), "--text", "--no-llm"]) == 0
    assert events == ["odcinek"]
    assert created["pulse"] is None and created["observer"] is None
    assert created["choice_seconds"] == 15.0


def test_main_exits_with_code_2_when_the_panel_cannot_start(tmp_path, monkeypatch, scenario_dict, caplog):
    class BusyServer(SpyServer):
        def start(self):
            raise OSError("port zajęty")

    path, created, events = install_spies(tmp_path, monkeypatch, scenario_dict, make_server=BusyServer)

    assert main([str(path), "--text", "--no-llm", "--panel"]) == 2
    assert "Nie udało się uruchomić serwera" in caplog.text
    assert "odcinek" not in events and created == {}  # odcinek nie ruszył, silnik nie powstał


def test_main_web_player_serves_the_episode_and_opens_the_browser(tmp_path, monkeypatch, scenario_dict):
    path, created, events = install_spies(tmp_path, monkeypatch, scenario_dict)
    opened = []
    monkeypatch.setattr("bajka.app.webbrowser", SimpleNamespace(open=opened.append))

    def one_episode(episode, make_engine):
        make_engine().run()
        events.append("koniec")

    monkeypatch.setattr("bajka.app.run_episodes", one_episode)

    assert main([str(path), "--no-llm", "--no-mic"]) == 0
    assert events == ["odcinek", "koniec"]
    _, player, viewer, voice, _ = created["args"]
    assert isinstance(player, WebEpisode) and viewer is player and voice is player
    assert player.state()["voice"] is False  # --no-mic: bez rozpoznawania mowy, tylko pilot i dotyk
    assert len(opened) == 1 and opened[0].startswith("http://127.0.0.1:")


def test_montage_uses_rules_without_a_language_model():
    from bajka.app import build_montage

    assert build_montage({}, "local", use_llm=False)._editor is None
    assert build_montage({"BAJKA_MONTAGE": "reguly"}, "local", use_llm=True)._editor is None


def test_main_gives_the_engine_a_montage(tmp_path, monkeypatch, scenario_dict):
    from bajka.montage import Montage

    path, created, _ = install_spies(tmp_path, monkeypatch, scenario_dict)

    assert main([str(path), "--text", "--no-llm"]) == 0
    assert isinstance(created["montage"], Montage)

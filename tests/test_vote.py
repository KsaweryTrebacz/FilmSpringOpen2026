from pathlib import Path

import numpy as np
import pytest

from bajka.config import ConfigError
from bajka.console import ConsoleMeter
from bajka.engine import DEFAULT_FALLBACK, StoryEngine
from bajka.ports import ShoutMeter
from bajka.scenario import ScenarioError, missing_media, parse_scenario
from bajka.vote import MicrophoneMeter, VoteSettings, pick_winner, shout_level

SETTINGS = VoteSettings(min_ratio=2.0, min_level=500, margin=0.15)
FRAME = 480


def vote_scenario(scenario_dict, **intro):
    scene = scenario_dict["scenes"]["intro"]
    scene["vote"] = True
    scene["choices"]["las"]["call"] = "Kto do lasu? Krzyczymy: LAS!"
    scene["choices"]["jaskinia"]["call"] = "Kto do jaskini? Krzyczymy: JASKINIA!"
    scene.update(intro)
    return parse_scenario(scenario_dict, base_dir=Path("film"))


# Wybór zwycięzcy


def test_loudest_clear_shout_wins():
    assert pick_winner({"las": 3000, "jaskinia": 1200}, hall=400, settings=SETTINGS) == "las"


def test_shout_must_beat_hall_noise():
    assert pick_winner({"las": 1500, "jaskinia": 600}, hall=1000, settings=SETTINGS) is None


def test_close_result_is_a_tie():
    assert pick_winner({"las": 3000, "jaskinia": 2800}, hall=300, settings=SETTINGS) is None


def test_single_option_chant_only_needs_to_be_loud():
    assert pick_winner({"hopsasa": 2500}, hall=300, settings=SETTINGS) == "hopsasa"
    assert pick_winner({"hopsasa": 400}, hall=100, settings=SETTINGS) is None


def test_settings_read_tuning_from_env():
    settings = VoteSettings.from_env({"BAJKA_VOTE_SECONDS": "3", "BAJKA_VOTE_MIN_LEVEL": "900"})

    assert settings.shout_seconds == 3.0
    assert settings.min_level == 900.0
    with pytest.raises(ConfigError, match="BAJKA_VOTE_MARGIN"):
        VoteSettings.from_env({"BAJKA_VOTE_MARGIN": "dużo"})


# Pomiar z mikrofonu


def test_single_bang_does_not_make_a_shout():
    frames = [np.zeros(FRAME, dtype=np.int16)] * 9 + [np.full(FRAME, 20000, dtype=np.int16)]

    assert shout_level(frames, seconds=0.3) == 0.0


def test_meter_calibrates_hall_and_measures_each_shout():
    recordings = iter([200, 3000, 900])  # gwar sali, okrzyk "las", okrzyk "jaskinia"

    def frames():
        level = next(recordings)
        return iter([np.full(FRAME, level, dtype=np.int16)] * 200)

    meter = MicrophoneMeter(VoteSettings(shout_seconds=0.3, calibrate_seconds=0.3, min_level=500), frames=frames)
    meter.calibrate()
    levels = {"las": meter.measure(), "jaskinia": meter.measure()}

    assert isinstance(meter, ShoutMeter)
    assert meter.hall == pytest.approx(200)
    assert meter.winner(levels) == "las"


# Scenariusz


def test_vote_scene_requires_call_for_every_choice(scenario_dict):
    scenario_dict["scenes"]["intro"]["vote"] = True
    scenario_dict["scenes"]["intro"]["choices"]["las"]["call"] = "Kto do lasu?"
    with pytest.raises(ScenarioError, match="jaskinia"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_call_clips_are_media_to_produce(tmp_path, scenario_dict):
    scenario_dict["scenes"]["intro"]["vote"] = True
    scenario_dict["scenes"]["intro"]["choices"]["las"]["call_clip"] = "wezwanie_las.mp4"
    scenario_dict["scenes"]["intro"]["choices"]["jaskinia"]["call"] = "Kto do jaskini?"
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)

    assert scenario.scene("intro").vote
    assert tmp_path / "wezwanie_las.mp4" in missing_media(scenario)


# Silnik


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, clip):
        self.calls.append(("play", clip.name))

    def loop(self, clip):
        self.calls.append(("loop", clip.name))


class FakeVoice:
    def __init__(self):
        self.lines = []

    def say(self, text):
        self.lines.append(text)


class FakeMeter:
    """Kolejne rundy: słownik okrzyków na rundę albo wyjątek."""

    def __init__(self, *rounds):
        self._rounds = list(rounds)
        self._current = {}
        self.calibrations = 0

    def calibrate(self):
        self.calibrations += 1
        current = self._rounds.pop(0)
        if isinstance(current, Exception):
            raise current
        self._current = dict(current)

    def measure(self):
        return self._current.pop(next(iter(self._current)))

    def winner(self, levels):
        best = max(levels, key=levels.get)
        return best if levels[best] > 0 else None


class SilentListener:
    def listen(self):
        raise AssertionError("w scenie vote silnik nie powinien słuchać słów")


def run(scenario, meter):
    player, voice = FakePlayer(), FakeVoice()
    visited = StoryEngine(scenario, player, SilentListener(), voice, resolver=None, meter=meter).run()
    return visited, player, voice


def test_vote_calls_each_option_and_follows_the_loudest(scenario_dict):
    scenario = vote_scenario(scenario_dict)

    visited, _, voice = run(scenario, FakeMeter({"las": 100, "jaskinia": 900}))

    assert visited == ["intro", "jaskinia"]
    assert voice.lines == ["Kto do lasu? Krzyczymy: LAS!", "Kto do jaskini? Krzyczymy: JASKINIA!", "Do jaskini! Mam latarkę!"]


def test_quiet_round_reprompts_then_hero_picks_default(scenario_dict):
    scenario = vote_scenario(scenario_dict)
    silence = {"las": 0, "jaskinia": 0}

    visited, _, voice = run(scenario, FakeMeter(silence, silence, silence))

    assert visited == ["intro", "las"]
    assert voice.lines.count("Hmm, nie usłyszałem. Las czy jaskinia?") == 2
    assert voice.lines[-1] == f"{DEFAULT_FALLBACK} Do lasu! Trzymaj się blisko!"


def test_meter_failure_counts_as_quiet_round(scenario_dict):
    scenario = vote_scenario(scenario_dict)

    visited, _, _ = run(scenario, FakeMeter(OSError("brak mikrofonu"), {"las": 5, "jaskinia": 1}))

    assert visited == ["intro", "las"]


def test_call_clip_is_played_and_idle_loop_resumes(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["call_clip"] = "wezwanie_las.mp4"
    scenario = vote_scenario(scenario_dict)

    _, player, voice = run(scenario, FakeMeter({"las": 9, "jaskinia": 1}))

    assert ("play", "wezwanie_las.mp4") in player.calls
    assert player.calls[player.calls.index(("play", "wezwanie_las.mp4")) + 1] == ("loop", "intro_idle.mp4")
    assert "Kto do lasu? Krzyczymy: LAS!" not in voice.lines


def test_without_meter_vote_scene_falls_back_to_speech(scenario_dict):
    from bajka.ports import Interpretation

    scenario = vote_scenario(scenario_dict)

    class Listener:
        def listen(self):
            return "jaskinia"

    class Resolver:
        def resolve(self, scene, transcript):
            return Interpretation("jaskinia", "")

    visited = StoryEngine(scenario, FakePlayer(), Listener(), FakeVoice(), Resolver()).run()

    assert visited == ["intro", "jaskinia"]


# Krzykomierz konsolowy (tryb --text)


def test_console_meter_reads_typed_loudness():
    answers = iter(["8", "3,5", ""])
    meter = ConsoleMeter(read=lambda prompt: next(answers))

    levels = {"las": meter.measure(), "jaskinia": meter.measure(), "most": meter.measure()}

    assert isinstance(meter, ShoutMeter)
    assert levels == {"las": 8.0, "jaskinia": 3.5, "most": 0.0}
    assert meter.winner(levels) == "las"


def test_console_meter_tie_and_silence_have_no_winner():
    meter = ConsoleMeter(read=lambda prompt: "nie wiem")

    assert meter.measure() == 0.0
    assert meter.winner({"las": 5, "jaskinia": 5}) is None
    assert meter.winner({"las": 0, "jaskinia": 0}) is None

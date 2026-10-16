"""Silnik i tętno sali: wersja sceny według stanu widowni i nastroju filmu."""

from pathlib import Path

from bajka.engine import StoryEngine
from bajka.ports import Interpretation, Pulse
from bajka.pulse import PulseSettings
from bajka.scenario import parse_scenario


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, clip):
        self.calls.append(("play", clip.name))

    def loop(self, clip):
        self.calls.append(("loop", clip.name))


class AnswerListener:
    def listen(self):
        return "las"


class SilentVoice:
    def say(self, text):
        pass


class ChooseForest:
    def resolve(self, scene, transcript):
        return Interpretation("las", "Do lasu!")


class ScriptedPulse:
    """Kolejne odczyty tętna sali; wyjątek z listy zostaje rzucony."""

    def __init__(self, *readings):
        self._readings = list(readings)
        self.reads = 0

    def read(self):
        self.reads += 1
        reading = self._readings.pop(0)
        if isinstance(reading, Exception):
            raise reading
        return Pulse(bpm=reading, viewers=30)


def adaptive_scenario(scenario_dict, mood="spokojny", variants=None):
    scenario_dict["mood"] = mood
    scenario_dict["scenes"]["las"]["variants"] = variants or {"spokojna": "las_spokojna.mp4", "zywa": "las_zywa.mp4"}
    return parse_scenario(scenario_dict, base_dir=Path("film"))


def run(scenario, pulse):
    player = FakePlayer()
    engine = StoryEngine(
        scenario, player, AnswerListener(), SilentVoice(), ChooseForest(), pulse=pulse, pulse_settings=PulseSettings()
    )
    engine.run()
    return player.calls


def test_excited_hall_gets_the_calm_version_of_a_calm_film(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, 110.0))  # 110 ≥ 90 × 1,15

    assert calls[-1] == ("play", "las_spokojna.mp4")


def test_hall_in_normal_state_gets_the_regular_clip(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, 95.0))

    assert calls[-1] == ("play", "las.mp4")


def test_bored_hall_gets_the_lively_version_of_a_lively_film(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict, mood="zywy"), ScriptedPulse(90.0, 85.0))  # 85 ≤ 90 × 0,97

    assert calls[-1] == ("play", "las_zywa.mp4")


def test_scene_without_the_chosen_version_plays_the_regular_clip(scenario_dict):
    scenario = adaptive_scenario(scenario_dict, variants={"zywa": "las_zywa.mp4"})

    calls = run(scenario, ScriptedPulse(90.0, 120.0))

    assert calls[-1] == ("play", "las.mp4")


def test_baseline_is_read_after_the_first_scene_and_then_only_before_scenes_with_versions(scenario_dict):
    pulse = ScriptedPulse(90.0, 110.0)

    run(adaptive_scenario(scenario_dict), pulse)

    assert pulse.reads == 2  # punkt odniesienia po „intro” i jeden odczyt przed „las”


def test_pulse_error_plays_the_regular_clip(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, RuntimeError("zegarek milczy")))

    assert calls[-1] == ("play", "las.mp4")


def test_failed_baseline_means_no_adaptation(scenario_dict):
    pulse = ScriptedPulse(RuntimeError("zegarek milczy"))

    calls = run(adaptive_scenario(scenario_dict), pulse)

    assert calls[-1] == ("play", "las.mp4")
    assert pulse.reads == 1


def test_without_pulse_the_film_does_not_adapt(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), None)

    assert calls[-1] == ("play", "las.mp4")

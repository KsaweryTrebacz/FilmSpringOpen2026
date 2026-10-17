"""Silnik i tętno widza: wersja sceny według stanu widza i nastroju odcinka."""

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
    """Kolejne odczyty tętna widza; wyjątek z listy zostaje rzucony. Ostatni odczyt się powtarza, jak w czujniku."""

    def __init__(self, *readings):
        self._readings = list(readings)
        self.reads = 0

    def read(self):
        self.reads += 1
        reading = self._readings.pop(0) if len(self._readings) > 1 else self._readings[0]
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


def test_pulse_is_read_for_the_baseline_the_montage_and_scenes_with_versions(scenario_dict):
    pulse = ScriptedPulse(90.0, 110.0)

    run(adaptive_scenario(scenario_dict), pulse)

    assert pulse.reads == 3  # punkt odniesienia po „intro”, montaż po wyborze i wersja sceny „las”


def test_pulse_error_plays_the_regular_clip(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), ScriptedPulse(90.0, RuntimeError("zegarek milczy")))

    assert calls[-1] == ("play", "las.mp4")


def test_scene_right_after_a_failed_baseline_read_plays_the_regular_clip(scenario_dict):
    pulse = ScriptedPulse(RuntimeError("zegarek milczy"))

    calls = run(adaptive_scenario(scenario_dict), pulse)

    assert calls[-1] == ("play", "las.mp4")
    assert pulse.reads == 1


def test_failed_first_read_is_retried_after_the_next_scene(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"].update(
        {
            "idle": "las_idle.mp4",
            "question": "Idziemy dalej?",
            "reprompt": "Dalej?",
            "default": "las",
            "choices": {"las": {"description": "iść dalej", "next": "jaskinia", "reply": "Dalej!"}},
        }
    )
    scenario_dict["scenes"]["jaskinia"]["variants"] = {"spokojna": "jaskinia_spokojna.mp4"}
    pulse = ScriptedPulse(RuntimeError("zegarek milczy"), 90.0, 110.0)

    calls = run(parse_scenario(scenario_dict, base_dir=Path("film")), pulse)

    assert calls[-1] == ("play", "jaskinia_spokojna.mp4")  # odniesienie 90 z drugiego odczytu, po scenie „las”
    assert pulse.reads == 4  # bez odniesienia montaż nie czyta tętna; potem montaż po wyborze w „las” i wersja


def test_without_pulse_the_film_does_not_adapt(scenario_dict):
    calls = run(adaptive_scenario(scenario_dict), None)

    assert calls[-1] == ("play", "las.mp4")

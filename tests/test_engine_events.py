"""Silnik opowiada panelowi podglądu, co się dzieje: sceny, wersje według tętna, głosy i decyzje."""

import logging
from pathlib import Path

from bajka.engine import StoryEngine
from bajka.ports import Answer, Interpretation, Pulse, ShowObserver
from bajka.scenario import parse_scenario


class FakePlayer:
    def play(self, clip):
        pass

    def loop(self, clip):
        pass


class FakeListener:
    def __init__(self, *answers):
        self._answers = list(answers)

    def listen(self):
        return self._answers.pop(0)


class SilentVoice:
    def say(self, text):
        pass


class ChooseForest:
    def resolve(self, scene, transcript):
        return Interpretation("las", "Do lasu!")


class RecordingObserver:
    def __init__(self):
        self.events = []

    def event(self, kind, data):
        self.events.append((kind, dict(data)))


class BrokenObserver:
    def event(self, kind, data):
        raise RuntimeError("panel padł")


class ScriptedPulse:
    def __init__(self, *readings):
        self._readings = list(readings)

    def read(self):
        return Pulse(bpm=self._readings.pop(0), viewers=30)


class PhoneAudience:
    def __init__(self, answers):
        self._answers = answers

    def connected(self):
        return len(self._answers)

    def collect(self, scene):
        return [Interpretation(choice, "") for choice in self._answers]


class ButtonViewer:
    """Okno wyboru, w którym widz wskazuje opcję pilotem."""

    def __init__(self, choice_id):
        self._choice_id = choice_id

    def ask(self, scene, seconds):
        return Answer(choice_id=self._choice_id)


def run(scenario, listener=None, **options):
    observer = RecordingObserver()
    engine = StoryEngine(
        scenario, FakePlayer(), listener or FakeListener("las"), SilentVoice(), ChooseForest(), observer=observer,
        **options,
    )  # fmt: skip
    visited = engine.run()
    return visited, observer.events


def test_recording_observer_fulfils_contract():
    assert isinstance(RecordingObserver(), ShowObserver)


def test_engine_reports_scenes_and_the_answer_from_the_microphone(scenario):
    _, events = run(scenario)

    assert events == [
        ("scena", {"scene": "intro", "clip": "intro.mp4", "variant": "zwykla"}),
        ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "glos"}),
        ("scena", {"scene": "las", "clip": "las.mp4", "variant": "zwykla"}),
    ]


def test_default_choice_after_silence_is_reported(scenario):
    _, events = run(scenario, FakeListener(None, None, None))

    assert ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "domyslna"}) in events


def test_baseline_and_version_by_pulse_are_reported(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))

    _, events = run(scenario, pulse=ScriptedPulse(90.0, 110.0))

    assert [kind for kind, _ in events] == ["scena", "odniesienie", "decyzja", "wersja", "scena"]
    assert events[1] == ("odniesienie", {"bpm": 90.0})
    assert events[3] == (
        "wersja", {"scene": "las", "bpm": 110.0, "baseline": 90.0, "state": "pobudzenie", "variant": "spokojna"}
    )
    assert events[4] == ("scena", {"scene": "las", "clip": "las_spokojna.mp4", "variant": "spokojna"})


def test_phone_votes_and_majority_are_reported(scenario):
    _, events = run(scenario, audience=PhoneAudience(["las", "las", "jaskinia"]))

    assert ("glosy", {"scene": "intro", "source": "telefony", "counts": {"las": 2, "jaskinia": 1}}) in events
    assert ("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "wiekszosc"}) in events


def test_choice_from_the_remote_is_reported(scenario):
    _, events = run(scenario, ButtonViewer("jaskinia"))

    assert ("decyzja", {"scene": "intro", "choice": "jaskinia", "label": "Jaskinia", "how": "przycisk"}) in events


def test_broken_panel_does_not_stop_the_film(scenario, caplog):
    engine = StoryEngine(scenario, FakePlayer(), FakeListener("las"), SilentVoice(), ChooseForest(),
                         observer=BrokenObserver())  # fmt: skip

    with caplog.at_level(logging.ERROR):
        assert engine.run() == ["intro", "las"]

    assert "Błąd panelu" in caplog.text

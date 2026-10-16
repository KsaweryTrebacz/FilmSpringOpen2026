import threading
from concurrent.futures import Future
from pathlib import Path

import pytest
from live_fakes import FakeAnimator, FakeImaginer, FakeListener, FakePlayer, FakeResolver, FakeVoice

from bajka.engine import FALLBACK_VISION_LINE, StoryEngine
from bajka.ports import Interpretation, Vision
from bajka.scenario import parse_scenario

NARRATION = "Zobacz, jak pięknie wygląda nasz ul!"


class NamedIllustrator:
    """Nazwa obrazu wynika z pierwszego słowa promptu, więc kolejność rysowania w wątkach nie ma znaczenia."""

    def __init__(self, error=None):
        self.prompts = []
        self.started = threading.Event()
        self._lock = threading.Lock()
        self._error = error

    def draw(self, prompt):
        with self._lock:
            self.prompts.append(prompt)
        self.started.set()
        if self._error is not None:
            raise self._error
        return Path(f"{prompt.split()[0]}.png")


class WaitingListener(FakeListener):
    """Przed pierwszą odpowiedzią czeka, aż ruszy rysowanie w tle, i zapamiętuje, czy ruszyło."""

    def __init__(self, illustrator, *answers):
        super().__init__(*answers)
        self._illustrator = illustrator
        self.drawing_started_before_answer = None

    def listen(self):
        if self.drawing_started_before_answer is None:
            self.drawing_started_before_answer = self._illustrator.started.wait(timeout=2)
        return super().listen()


@pytest.fixture
def story(scenario_dict):
    """intro: las → ozdoby [open] → final_ul [generated] → las; jaskinia → gen_jaskinia [generated] → jaskinia."""
    scenes = scenario_dict["scenes"]
    scenes["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenes["intro"]["choices"]["jaskinia"]["next"] = "gen_jaskinia"
    scenes["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "beehive decorated with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "final_ul",
    }
    scenes["final_ul"] = {
        "kind": "generated",
        "image_prompt": "party at the beehive decorated with {ozdoby}",
        "narration": NARRATION,
        "fallback_clips": ["final_zapas.mp4"],
        "next": "las",
    }
    scenes["gen_jaskinia"] = {
        "kind": "generated",
        "image_prompt": "cave glowing with crystals",
        "narration": "Ale tu pięknie świeci!",
        "fallback_clips": ["jaskinia_zapas.mp4"],
        "next": "jaskinia",
    }
    return parse_scenario(scenario_dict, base_dir=Path("film"))


@pytest.fixture
def cave_story(story, scenario_dict):
    """Jak `story`, ale jaskinia (wybór prowadzi do niej wprost) korzysta z pomysłu o ozdobach z drugiej gałęzi."""
    scenario_dict["scenes"]["gen_jaskinia"]["image_prompt"] = "cave decorated for a party with {ozdoby}"
    return parse_scenario(scenario_dict, base_dir=Path("film"))


def make_engine(scenario, listener, illustrator, answer="las"):
    player, voice = FakePlayer(), FakeVoice()
    engine = StoryEngine(
        scenario,
        player,
        listener,
        voice,
        FakeResolver({answer: Interpretation(answer, f"{answer}!")}),
        imaginer=FakeImaginer({"wstążkami": Vision("Wstążki? Już rysuję!", "rainbow ribbons")}),
        illustrator=illustrator,
        animator=FakeAnimator(),
        image_timeout_s=2.0,
    )
    return engine, player, voice


def test_generated_scene_draws_remembered_idea_and_narrates_over_it(story):
    illustrator = NamedIllustrator()
    engine, player, voice = make_engine(story, FakeListener("las", "wstążkami"), illustrator)

    assert engine.run() == ["intro", "ozdoby", "final_ul", "las"]

    assert "party at the beehive decorated with rainbow ribbons" in illustrator.prompts
    assert player.calls[-2:] == [("loop", "party.mp4"), ("play", "las.mp4")]
    assert voice.lines[-1] == NARRATION


def test_generated_scene_reached_without_the_open_scene_uses_its_default_idea(cave_story):
    illustrator = NamedIllustrator()
    engine, _, _ = make_engine(cave_story, FakeListener("jaskinia"), illustrator, answer="jaskinia")

    assert engine.run() == ["intro", "gen_jaskinia", "jaskinia"]  # pytanie o ozdoby nie padło

    assert illustrator.prompts == ["cave decorated for a party with flowers"]  # nie „{ozdoby}” w promptcie
    assert engine.memory == {"ozdoby": "flowers"}


def test_choice_scene_draws_generated_branch_while_question_is_asked(story):
    illustrator = NamedIllustrator()
    listener = WaitingListener(illustrator, "jaskinia")
    engine, player, _ = make_engine(story, listener, illustrator, answer="jaskinia")

    assert engine.run() == ["intro", "gen_jaskinia", "jaskinia"]

    assert listener.drawing_started_before_answer
    assert illustrator.prompts.count("cave glowing with crystals") == 1  # nie rysujemy drugi raz
    assert ("loop", "cave.mp4") in player.calls


def test_generated_scene_failure_uses_fallback_clip_without_apology(story):
    engine, player, voice = make_engine(
        story, FakeListener("jaskinia"), NamedIllustrator(error=RuntimeError("429")), answer="jaskinia"
    )

    engine.run()

    assert ("loop", "jaskinia_zapas.mp4") in player.calls
    assert FALLBACK_VISION_LINE not in voice.lines
    assert voice.lines[-1] == "Ale tu pięknie świeci!"


class InlineExecutor:
    """Zamiast puli wątków: wykonuje zlecenia od razu, w kolejności zlecenia (deterministyczny test kolejki)."""

    def __init__(self, *args, **kwargs):
        pass

    def submit(self, fn, *args):
        future = Future()
        try:
            future.set_result(fn(*args))
        except Exception as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, wait=True, cancel_futures=False):
        pass


class QueueingExecutor(InlineExecutor):
    """Rysunki jaskini „czekają w kolejce” (nie startują), resztę wykonuje od razu."""

    def __init__(self, *args, **kwargs):
        self.waiting = []

    def submit(self, fn, *args):
        if args and str(args[0]).startswith("cave"):
            future = Future()
            self.waiting.append(future)
            return future
        return super().submit(fn, *args)


def test_childs_own_drawing_is_queued_before_background_drawing(story, monkeypatch):
    monkeypatch.setattr("bajka.engine.ThreadPoolExecutor", InlineExecutor)
    illustrator = NamedIllustrator()
    engine, _, _ = make_engine(story, FakeListener("las", "wstążkami"), illustrator)

    engine.run()

    own = illustrator.prompts.index("beehive decorated with rainbow ribbons")
    background = illustrator.prompts.index("party at the beehive decorated with rainbow ribbons")
    assert own < background


def test_dropped_branch_waiting_in_queue_is_cancelled(story, monkeypatch):
    executors = []

    def make_executor(*args, **kwargs):
        executors.append(QueueingExecutor())
        return executors[-1]

    monkeypatch.setattr("bajka.engine.ThreadPoolExecutor", make_executor)
    engine, _, _ = make_engine(story, FakeListener("las", "wstążkami"), NamedIllustrator())

    engine.run()

    (cave,) = executors[0].waiting  # gałąź jaskini zlecona przy pytaniu, dziecko wybrało las
    assert cave.cancelled()

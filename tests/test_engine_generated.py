import threading
import time
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


class SlowVoice(FakeVoice):
    """Kwestia wskazanego tekstu trwa tyle, ile potrzeba na wypowiedzenie jej na głos."""

    def __init__(self, slow_line, seconds):
        super().__init__()
        self._slow_line = slow_line
        self._seconds = seconds

    def say(self, text):
        if text == self._slow_line:
            time.sleep(self._seconds)
        super().say(text)


class StoppingVoice(FakeVoice):
    """Po wskazanej kwestii zatrzymuje silnik z opóźnieniem, więc stop zawsze trafia w czekanie na obraz (bez wyścigu)."""

    def __init__(self, line, delay):
        super().__init__()
        self.engine = None  # silnik powstaje dopiero po głosie, test podstawia go przed run()
        self._line = line
        self._delay = delay

    def say(self, text):
        super().say(text)
        if text == self._line:
            threading.Timer(self._delay, self.engine.stop).start()


def make_engine(scenario, listener, illustrator, answer="las", voice=None, **engine_options):
    player, voice = FakePlayer(), voice or FakeVoice()
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
        **engine_options,
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


def timed_run(engine):
    started = time.monotonic()
    visited = engine.run()
    return visited, time.monotonic() - started


def test_generated_scene_stays_on_screen_for_the_requested_time_after_short_narration(story):
    engine, _, _ = make_engine(
        story, FakeListener("jaskinia"), NamedIllustrator(), answer="jaskinia", generated_seconds=0.4
    )

    visited, elapsed = timed_run(engine)

    assert visited == ["intro", "gen_jaskinia", "jaskinia"]
    assert elapsed >= 0.4 - 0.03  # nie skraca pokazu obrazu (luz 0,03 s na zgrubny zegar Windows)


def test_narration_counts_towards_the_time_on_screen(story):
    voice = SlowVoice("Ale tu pięknie świeci!", seconds=0.3)
    engine, _, _ = make_engine(
        story, FakeListener("jaskinia"), NamedIllustrator(), answer="jaskinia", voice=voice, generated_seconds=0.4
    )

    _, elapsed = timed_run(engine)

    assert 0.35 <= elapsed < 0.69  # dochodzi tylko reszta (0,1 s), a nie całe 0,4 s po narracji


def test_stop_ends_the_wait_on_the_picture_at_once(story):
    voice = StoppingVoice("Ale tu pięknie świeci!", delay=0.1)  # stop dopiero, gdy scena generowana jest na ekranie
    engine, player, _ = make_engine(
        story, FakeListener("jaskinia"), NamedIllustrator(), answer="jaskinia", voice=voice, generated_seconds=5.0
    )
    voice.engine = engine

    visited, elapsed = timed_run(engine)

    assert visited == ["intro", "gen_jaskinia"]
    assert voice.lines[-1] == "Ale tu pięknie świeci!"  # scena generowana naprawdę doszła do głosu
    assert elapsed < 2.0
    assert ("play", "jaskinia.mp4") not in player.calls


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

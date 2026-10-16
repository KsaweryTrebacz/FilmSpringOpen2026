import threading
from pathlib import Path

import pytest
from live_fakes import (
    FakeAnimator,
    FakeIllustrator,
    FakeImaginer,
    FakeListener,
    FakePlayer,
    FakeResolver,
    FakeVoice,
)

from bajka.engine import FALLBACK_VISION_LINE, StoryEngine
from bajka.ports import Interpretation, Vision
from bajka.scenario import parse_scenario

REPROMPT = "Kwiatki, wstążki, a może coś innego?"
REPLY = "Tęczowe wstążki? Już rysuję!"
CHOOSE_FOREST = FakeResolver({"las": Interpretation("las", "Las!")})


@pytest.fixture
def live_scenario(scenario_dict):
    """intro → (las) → ozdoby [pytanie otwarte] → las."""
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul Bzyczki na święto?",
        "reprompt": REPROMPT,
        "image_prompt": "the beehive decorated for a party with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers and ribbons",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "las",
    }
    return parse_scenario(scenario_dict, base_dir=Path("film"))


class StoppingVoice(FakeVoice):
    """Po wskazanej kwestii okno zostaje zamknięte (Esc): silnik dostaje stop() z innego wątku."""

    def __init__(self, stop_after):
        super().__init__()
        self.engine = None
        self._stop_after = stop_after

    def say(self, text):
        super().say(text)
        if text == self._stop_after:
            self.engine.stop()


class StoppingListener(FakeListener):
    """Esc w trakcie słuchania: zwraca odpowiedź, ale zanim silnik ją obsłuży, okno już się zamyka."""

    def __init__(self, *answers):
        super().__init__(*answers)
        self.engine = None

    def listen(self):
        answer = super().listen()
        self.engine.stop()
        return answer


def make_engine(scenario, listener, imaginer=None, illustrator=None, animator=None, timeout_s=5.0, voice=None):
    player, voice = FakePlayer(), voice or FakeVoice()
    engine = StoryEngine(
        scenario,
        player,
        listener,
        voice,
        CHOOSE_FOREST,
        imaginer=imaginer or FakeImaginer({"wstążkami": Vision(REPLY, "rainbow ribbons")}),
        illustrator=illustrator or FakeIllustrator(),
        animator=animator or FakeAnimator(),
        image_timeout_s=timeout_s,
    )
    return engine, player, voice


def test_open_scene_draws_childs_idea_while_hero_talks(live_scenario):
    illustrator = FakeIllustrator()
    engine, player, voice = make_engine(live_scenario, FakeListener("las", "wstążkami"), illustrator=illustrator)

    assert engine.run() == ["intro", "ozdoby", "las"]

    assert player.calls == [
        ("play", "intro.mp4"),
        ("loop", "intro_idle.mp4"),
        ("play", "ozdoby.mp4"),
        ("loop", "ozdoby_idle.mp4"),
        ("loop", "rysuje.mp4"),
        ("play", "obraz_1.mp4"),
        ("play", "las.mp4"),
    ]
    assert voice.lines == ["Las!", REPLY]
    assert illustrator.prompts == ["the beehive decorated for a party with rainbow ribbons"]
    assert engine.memory == {"ozdoby": "rainbow ribbons"}


def test_silence_reprompts_then_draws(live_scenario):
    engine, player, voice = make_engine(live_scenario, FakeListener("las", None, "wstążkami"))

    engine.run()

    assert voice.lines == ["Las!", REPROMPT, REPLY]
    assert ("play", "obraz_1.mp4") in player.calls


def test_after_max_reprompts_default_idea_and_fallback_clip(live_scenario):
    illustrator = FakeIllustrator()
    engine, player, voice = make_engine(live_scenario, FakeListener("las", None, None, None), illustrator=illustrator)

    engine.run()

    assert voice.lines == ["Las!", REPROMPT, REPROMPT, FALLBACK_VISION_LINE]
    assert player.calls[-2:] == [("play", "ozdoby_zapas.mp4"), ("play", "las.mp4")]
    assert illustrator.prompts == []
    assert engine.memory == {"ozdoby": "flowers and ribbons"}


def test_unusable_idea_uses_default_and_fallback_clip(live_scenario):
    imaginer = FakeImaginer({"coś strasznego": Vision("Narysuję coś innego!", "")})
    engine, player, voice = make_engine(live_scenario, FakeListener("las", "coś strasznego"), imaginer=imaginer)

    engine.run()

    assert voice.lines == ["Las!", FALLBACK_VISION_LINE]
    assert ("play", "ozdoby_zapas.mp4") in player.calls
    assert engine.memory == {"ozdoby": "flowers and ribbons"}


def test_imaginer_error_uses_fallback_clip(live_scenario):
    imaginer = FakeImaginer({"wstążkami": TimeoutError("Azure OpenAI nie odpowiada")})
    engine, player, voice = make_engine(live_scenario, FakeListener("las", "wstążkami"), imaginer=imaginer)

    assert engine.run() == ["intro", "ozdoby", "las"]

    assert voice.lines == ["Las!", FALLBACK_VISION_LINE]
    assert ("play", "ozdoby_zapas.mp4") in player.calls


@pytest.mark.parametrize(
    "illustrator, animator",
    [
        (FakeIllustrator(error=RuntimeError("content_policy_violation")), FakeAnimator()),
        (FakeIllustrator(), FakeAnimator(error=RuntimeError("ffmpeg"))),
    ],
    ids=["blad_obrazu", "blad_ffmpeg"],
)
def test_render_error_after_hero_reply_shows_fallback(live_scenario, illustrator, animator):
    engine, player, voice = make_engine(
        live_scenario, FakeListener("las", "wstążkami"), illustrator=illustrator, animator=animator
    )

    engine.run()

    assert voice.lines == ["Las!", REPLY, FALLBACK_VISION_LINE]
    assert player.calls[-2:] == [("play", "ozdoby_zapas.mp4"), ("play", "las.mp4")]
    assert engine.memory == {"ozdoby": "rainbow ribbons"}  # pomysł zostaje, nawet gdy obraz zawiódł


def test_slow_drawing_times_out_to_fallback(live_scenario):
    gate = threading.Event()
    illustrator = FakeIllustrator(gate=gate)
    engine, player, voice = make_engine(
        live_scenario, FakeListener("las", "wstążkami"), illustrator=illustrator, timeout_s=0.05
    )
    try:
        engine.run()
    finally:
        gate.set()  # wypuszczamy wątek rysowania

    assert voice.lines[-1] == FALLBACK_VISION_LINE
    assert ("play", "ozdoby_zapas.mp4") in player.calls


def test_stop_after_hero_reply_ends_the_run_without_playing_or_saying_more(live_scenario):
    voice = StoppingVoice(stop_after=REPLY)
    engine, player, _ = make_engine(live_scenario, FakeListener("las", "wstążkami"), voice=voice)
    voice.engine = engine

    assert engine.run() == ["intro", "ozdoby"]

    assert voice.lines == ["Las!", REPLY]  # po Esc bohater już nic nie mówi
    assert ("play", "las.mp4") not in player.calls  # ani nie przechodzi do następnej sceny
    assert ("play", "obraz_1.mp4") not in player.calls


def test_stop_while_listening_ends_the_run_before_the_answer_is_acted_on(scenario):
    listener = StoppingListener("las")
    player, voice = FakePlayer(), FakeVoice()
    engine = StoryEngine(scenario, player, listener, voice, CHOOSE_FOREST)
    listener.engine = engine

    assert engine.run() == ["intro"]

    assert voice.lines == []
    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4")]


def test_open_scenario_without_live_image_modules_is_refused(live_scenario):
    with pytest.raises(ValueError, match="illustrator"):
        StoryEngine(live_scenario, FakePlayer(), FakeListener(), FakeVoice(), CHOOSE_FOREST)


def test_classic_scenario_needs_no_live_image_modules(scenario):
    engine = StoryEngine(scenario, FakePlayer(), FakeListener("las"), FakeVoice(), CHOOSE_FOREST)

    assert engine.run() == ["intro", "las"]

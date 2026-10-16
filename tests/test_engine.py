from pathlib import Path

from bajka.engine import DEFAULT_FALLBACK, StoryEngine
from bajka.ports import Interpretation
from bajka.scenario import parse_scenario

REPROMPT = "Hmm, nie usłyszałem. Las czy jaskinia?"
LAS_REPLY = "Do lasu! Trzymaj się blisko!"


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, clip):
        self.calls.append(("play", clip.name))

    def loop(self, clip):
        self.calls.append(("loop", clip.name))


class FakeListener:
    """Zwraca kolejne odpowiedzi; wyjątek z listy zostaje rzucony."""

    def __init__(self, *answers):
        self._answers = list(answers)

    def listen(self):
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeVoice:
    def __init__(self, broken=False):
        self.lines = []
        self._broken = broken

    def say(self, text):
        self.lines.append(text)
        if self._broken:
            raise RuntimeError("głośnik nie działa")


class FakeResolver:
    """Mapuje transkrypcję na Interpretation albo wyjątek."""

    def __init__(self, answers):
        self._answers = answers
        self.calls = []

    def resolve(self, scene, transcript):
        self.calls.append((scene.id, transcript))
        answer = self._answers[transcript]
        if isinstance(answer, Exception):
            raise answer
        return answer


def make_engine(scenario, listener, resolver=None, voice=None, max_reprompts=2):
    player = FakePlayer()
    voice = voice or FakeVoice()
    resolver = resolver or FakeResolver({})
    engine = StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=max_reprompts)
    return engine, player, voice


def test_recognized_answer_speaks_reply_and_plays_next_clip(scenario):
    resolver = FakeResolver({"do lasu": Interpretation("las", "Super, idziemy do lasu!")})
    engine, player, voice = make_engine(scenario, FakeListener("do lasu"), resolver)

    assert engine.run() == ["intro", "las"]
    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4"), ("play", "las.mp4")]
    assert voice.lines == ["Super, idziemy do lasu!"]
    assert resolver.calls == [("intro", "do lasu")]


def test_silence_triggers_reprompt_then_accepts_answer(scenario):
    resolver = FakeResolver({"jaskinia": Interpretation("jaskinia", "Do jaskini!")})
    engine, _, voice = make_engine(scenario, FakeListener(None, "jaskinia"), resolver)

    assert engine.run() == ["intro", "jaskinia"]
    assert voice.lines == [REPROMPT, "Do jaskini!"]


def test_unclear_answer_uses_reprompt_generated_by_llm(scenario):
    resolver = FakeResolver({
        "nie wiem": Interpretation(None, "To jak, las czy jaskinia?"),
        "las": Interpretation("las", "Las!"),
    })
    engine, _, voice = make_engine(scenario, FakeListener("nie wiem", "las"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == ["To jak, las czy jaskinia?", "Las!"]


def test_after_max_reprompts_hero_picks_default(scenario):
    engine, _, voice = make_engine(scenario, FakeListener(None, None, None))

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [REPROMPT, REPROMPT, f"{DEFAULT_FALLBACK} {LAS_REPLY}"]


def test_scene_fallback_line_overrides_default_one(scenario_dict):
    scenario_dict["scenes"]["intro"]["fallback"] = "No dobrze, ja decyduję!"
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    engine, _, voice = make_engine(scenario, FakeListener(None), max_reprompts=0)

    engine.run()

    assert voice.lines == [f"No dobrze, ja decyduję! {LAS_REPLY}"]


def test_listener_error_counts_as_silence(scenario):
    resolver = FakeResolver({"las": Interpretation("las", "Las!")})
    engine, _, voice = make_engine(scenario, FakeListener(RuntimeError("brak mikrofonu"), "las"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [REPROMPT, "Las!"]


def test_llm_error_goes_to_default_with_static_reply(scenario):
    resolver = FakeResolver({"jaskinia": TimeoutError("Azure OpenAI nie odpowiada")})
    engine, _, voice = make_engine(scenario, FakeListener("jaskinia"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [LAS_REPLY]


def test_unknown_choice_from_llm_goes_to_default(scenario):
    resolver = FakeResolver({"rzeka": Interpretation("rzeka", "Do rzeki!")})
    engine, _, voice = make_engine(scenario, FakeListener("rzeka"), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [LAS_REPLY]


def test_empty_llm_reply_falls_back_to_static_reply(scenario):
    resolver = FakeResolver({"jaskinia": Interpretation("jaskinia", "")})
    engine, _, voice = make_engine(scenario, FakeListener("jaskinia"), resolver)

    engine.run()

    assert voice.lines == ["Do jaskini! Mam latarkę!"]


def test_tts_failure_does_not_stop_the_story(scenario):
    resolver = FakeResolver({"las": Interpretation("las", "Las!")})
    engine, player, _ = make_engine(scenario, FakeListener("las"), resolver, voice=FakeVoice(broken=True))

    assert engine.run() == ["intro", "las"]
    assert player.calls[-1] == ("play", "las.mp4")


def test_story_chains_multiple_decisions(scenario_dict):
    scenario_dict["scenes"]["las"] = {
        "clip": "las.mp4",
        "idle": "las_idle.mp4",
        "question": "Przechodzimy przez most czy po kamieniach?",
        "reprompt": "Most czy kamienie?",
        "default": "most",
        "choices": {
            "most": {"description": "przejść przez most", "next": "jaskinia", "reply": "Most!"},
            "kamienie": {"description": "skakać po kamieniach", "next": "jaskinia", "reply": "Hop!"},
        },
    }
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    resolver = FakeResolver({
        "las": Interpretation("las", "Las!"),
        "kamienie": Interpretation("kamienie", "Hop, hop!"),
    })
    engine, player, voice = make_engine(scenario, FakeListener("las", "kamienie"), resolver)

    assert engine.run() == ["intro", "las", "jaskinia"]
    assert ("loop", "las_idle.mp4") in player.calls
    assert voice.lines == ["Las!", "Hop, hop!"]

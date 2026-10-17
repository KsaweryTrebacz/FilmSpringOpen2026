from pathlib import Path

from bajka.engine import DEFAULT_CHOICE_SECONDS, DEFAULT_FALLBACK, StoryEngine
from bajka.ports import Answer, Cut, Interpretation
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


class StoppingVoice(FakeVoice):
    """Esc po wskazanej kwestii: okno się zamyka, a silnik dostaje stop() z wątku okna."""

    def __init__(self, stop_after):
        super().__init__()
        self.engine = None  # silnik powstaje po głosie, test podstawia go przed run()
        self._stop_after = stop_after

    def say(self, text):
        super().say(text)
        if text == self._stop_after:
            self.engine.stop()


class StoppingListener(FakeListener):
    """Esc w trakcie słuchania: odpowiedź przychodzi, ale okno zamyka się, zanim silnik ją obsłuży."""

    def __init__(self, *answers):
        super().__init__(*answers)
        self.engine = None

    def listen(self):
        answer = super().listen()
        self.engine.stop()
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


# Zamknięcie okna (Esc) w trakcie bajki


def test_stop_after_hero_reply_ends_the_run_without_playing_or_saying_more(scenario):
    resolver = FakeResolver({"las": Interpretation("las", LAS_REPLY)})
    voice = StoppingVoice(stop_after=LAS_REPLY)
    engine, player, _ = make_engine(scenario, FakeListener("las"), resolver, voice=voice)
    voice.engine = engine

    assert engine.run() == ["intro"]

    assert voice.lines == [LAS_REPLY]  # po Esc bohater już nic nie mówi
    assert ("play", "las.mp4") not in player.calls  # ani nie przechodzi do następnej sceny


def test_stop_while_listening_ends_the_run_before_the_answer_is_acted_on(scenario):
    listener = StoppingListener("las")
    resolver = FakeResolver({"las": Interpretation("las", LAS_REPLY)})
    engine, player, voice = make_engine(scenario, listener, resolver)
    listener.engine = engine

    assert engine.run() == ["intro"]

    assert voice.lines == []
    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4")]


# Okno wyboru: pilot, dotyk i głos


class ScriptedViewer:
    """Okno wyboru z kolejnymi odpowiedziami (Answer albo wyjątek); zapisuje, ile trwało każde okno."""

    def __init__(self, *answers):
        self._answers = list(answers)
        self.windows = []

    def ask(self, scene, seconds):
        self.windows.append((scene.id, seconds))
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_button_choice_skips_intent_recognition(scenario):
    resolver = FakeResolver({})  # pusty: każde wywołanie modelu skończyłoby się błędem testu
    engine, _, voice = make_engine(scenario, ScriptedViewer(Answer(choice_id="jaskinia")), resolver)

    assert engine.run() == ["intro", "jaskinia"]
    assert resolver.calls == [] and voice.lines == ["Do jaskini! Mam latarkę!"]


def test_spoken_answer_in_the_choice_window_goes_through_intent_recognition(scenario):
    resolver = FakeResolver({"do lasu": Interpretation("las", "")})
    engine, _, voice = make_engine(scenario, ScriptedViewer(Answer(transcript="do lasu")), resolver)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [LAS_REPLY]


def test_unknown_button_and_viewer_error_count_as_no_answer(scenario):
    viewer = ScriptedViewer(Answer(choice_id="most"), OSError("pilot"), Answer(choice_id="las"))
    engine, _, voice = make_engine(scenario, viewer)

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [REPROMPT, REPROMPT, LAS_REPLY]


def test_choice_window_time_comes_from_the_scene_or_the_app(scenario_dict):
    scenario_dict["scenes"]["intro"]["timeout"] = 20
    timed = parse_scenario(scenario_dict, base_dir=Path("film"))
    default = parse_scenario({**scenario_dict, "scenes": {**scenario_dict["scenes"], "intro": {
        k: v for k, v in scenario_dict["scenes"]["intro"].items() if k != "timeout"}}}, base_dir=Path("film"))
    viewer = ScriptedViewer(Answer(choice_id="las"), Answer(choice_id="las"))

    StoryEngine(timed, FakePlayer(), viewer, FakeVoice(), FakeResolver({})).run()
    StoryEngine(default, FakePlayer(), viewer, FakeVoice(), FakeResolver({}), choice_seconds=8).run()

    assert viewer.windows == [("intro", 20.0), ("intro", 8)]
    assert DEFAULT_CHOICE_SECONDS >= 10  # dzieci potrzebują więcej czasu niż dorośli


def test_recorded_reaction_clip_replaces_the_spoken_reply(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["reaction"] = "reakcja_las.mp4"
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    engine, player, voice = make_engine(scenario, ScriptedViewer(Answer(choice_id="las")))

    engine.run()

    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4"), ("play", "reakcja_las.mp4"),
                            ("play", "las.mp4")]  # fmt: skip
    assert voice.lines == []


def test_default_choice_says_the_fallback_before_the_reaction_clip(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["reaction"] = "reakcja_las.mp4"
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    engine, player, voice = make_engine(scenario, ScriptedViewer(Answer(), Answer(), Answer()))

    assert engine.run() == ["intro", "las"]
    assert voice.lines == [REPROMPT, REPROMPT, DEFAULT_FALLBACK]
    assert ("play", "reakcja_las.mp4") in player.calls


# Gałęzie, sceny przejściowe, warstwy i montaż


class FakeCompositor:
    """Odtwarzacz, który nakłada warstwy i robi przejścia: zapisuje ujęcia."""

    def __init__(self):
        self.shots = []

    def play(self, clip):
        raise AssertionError("kompozytor dostaje ujęcia, nie gołe klipy")

    loop = play

    def play_shot(self, shot):
        self.shots.append(("play", shot.clip.name, tuple(p.name for p in shot.layers), shot.cut.transition))

    def loop_shot(self, shot):
        self.shots.append(("loop", shot.clip.name, tuple(p.name for p in shot.layers), shot.cut.transition))


def branching_scenario(scenario_dict):
    """Las ma własną scenę dalszego ciągu („polana”), a wybór lasu nakłada latarkę na kolejne sceny."""
    scenes = scenario_dict["scenes"]
    scenes["intro"]["choices"]["las"].update(layer="latarka.webm", slot="pomocnik")
    scenes["las"] = {"clip": "las.mp4", "next": "polana", "place": "Las", "layers": ["pomocnik"]}
    scenes["polana"] = {"clip": "polana.mp4", "layers": ["pomocnik"], "transition": "rozjasnienie"}
    return parse_scenario(scenario_dict, base_dir=Path("film"))


def test_scene_without_question_leads_on_and_layers_follow_the_choice(scenario_dict):
    player = FakeCompositor()
    engine = StoryEngine(branching_scenario(scenario_dict), player, ScriptedViewer(Answer(choice_id="las")),
                         FakeVoice(), FakeResolver({}))  # fmt: skip

    assert engine.run() == ["intro", "las", "polana"]
    assert player.shots == [
        ("play", "intro.mp4", (), "ciecie"),
        ("loop", "intro_idle.mp4", (), "ciecie"),
        ("play", "las.mp4", ("latarka.webm",), "przenikanie"),  # reguły: miejsce nieznane → przenikanie
        ("play", "polana.mp4", ("latarka.webm",), "rozjasnienie"),  # podpowiedź autora sceny
    ]


def test_other_answer_takes_another_branch_without_the_layer(scenario_dict):
    player = FakeCompositor()
    engine = StoryEngine(branching_scenario(scenario_dict), player, ScriptedViewer(Answer(choice_id="jaskinia")),
                         FakeVoice(), FakeResolver({}))  # fmt: skip

    assert engine.run() == ["intro", "jaskinia"]
    assert player.shots[-1] == ("play", "jaskinia.mp4", (), "zaciemnienie")  # zakończenie


def test_montage_gets_what_the_viewer_said(scenario_dict):
    seen = []

    class Recording:
        def cut(self, context):
            seen.append(context)
            return Cut("przenikanie", 1.0, "Do lasu.", "model")

    from bajka.montage import Montage

    resolver = FakeResolver({"do lasu": Interpretation("las", "")})
    engine = StoryEngine(branching_scenario(scenario_dict), FakeCompositor(), ScriptedViewer(Answer(transcript="do lasu")),
                         FakeVoice(), resolver, montage=Montage(Recording()))  # fmt: skip

    engine.run()

    choice = next(c for c in seen if c.edge == "wybor")
    assert (choice.from_scene, choice.to_scene, choice.choice, choice.how, choice.transcript) == (
        "intro", "las", "Las", "glos", "do lasu",
    )
    assert any(c.edge == "dalej" and c.to_scene == "polana" for c in seen)


def test_vlc_without_layers_still_plays_every_clip(scenario_dict):
    player = FakePlayer()
    engine = StoryEngine(branching_scenario(scenario_dict), player, ScriptedViewer(Answer(choice_id="las")),
                         FakeVoice(), FakeResolver({}))  # fmt: skip

    engine.run()

    assert player.calls == [("play", "intro.mp4"), ("loop", "intro_idle.mp4"), ("play", "las.mp4"), ("play", "polana.mp4")]


def test_loop_enters_with_the_scenario_loop_transition(scenario_dict):
    scenario_dict["loop_transition"] = "przenikanie"  # klipy z generatora nie kończą się klatką pętli
    player = FakeCompositor()
    engine = StoryEngine(parse_scenario(scenario_dict, base_dir=Path("film")), player,
                         ScriptedViewer(Answer(choice_id="las")), FakeVoice(), FakeResolver({}))  # fmt: skip

    engine.run()

    assert ("loop", "intro_idle.mp4", (), "przenikanie") in player.shots

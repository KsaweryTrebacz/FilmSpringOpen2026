"""Scenariusz „Klub Ciekawskich”: poprawny graf i typowe odpowiedzi dzieci rozpoznawane bez modelu językowego."""

import re
from pathlib import Path

import pytest

from bajka.keywords import KeywordIntentResolver
from bajka.scenario import load_scenario

SCENARIO = load_scenario(Path(__file__).resolve().parents[1] / "scenarios" / "klub_ciekawskich.yaml")


def reachable(scenario):
    seen, todo = set(), [scenario.start]
    while todo:
        scene = scenario.scene(todo.pop())
        if scene.id not in seen:
            seen.add(scene.id)
            todo.extend(choice.next for choice in scene.choices.values())
    return seen


def test_every_scene_is_reachable_and_story_has_two_endings():
    assert reachable(SCENARIO) == set(SCENARIO.scenes)
    assert {s.id for s in SCENARIO.scenes.values() if s.is_ending} == {"koniec_taniec", "koniec_piosenka"}


LIVE_LINES = [line for s in SCENARIO.scenes.values() for line in (s.question, s.reprompt, s.fallback)] + [
    line for s in SCENARIO.scenes.values() for c in s.choices.values() for line in (c.reply, c.call)
]
# Czas przeszły zdradza płeć: "zrobiłeś/zrobiłaś", "zrobiliście/zrobiłyście", "obudziliśmy/obudziłyśmy".
GENDERED_PAST = re.compile(r"\w+(łeś|łaś|liście|łyście|liśmy|łyśmy)\b")


def test_hero_is_lila_and_talks_to_a_cinema_audience():
    assert "Lila Lupka" in SCENARIO.hero
    assert "widownia" in SCENARIO.hero


def test_live_lines_have_no_gendered_forms():
    assert [line for line in LIVE_LINES if GENDERED_PAST.search(line)] == []


def test_decisions_in_the_cinema_are_shouted_and_every_option_is_called():
    voting = {s.id for s in SCENARIO.scenes.values() if s.vote}

    assert voting == {"powitanie", "kuferek", "wiaterek", "pomocnik", "swieto"}
    assert all(c.call for s in SCENARIO.scenes.values() if s.vote for c in s.choices.values())


@pytest.mark.parametrize(
    ("scene", "answer", "choice"),
    [
        ("powitanie", "Hop sasa!", "hopsasa"),
        ("kuferek", "przez ten kolorowy mostek", "most"),
        ("kuferek", "do lasu", "las"),
        ("most", "czerwoną", "czerwona"),
        ("most", "niebieską deskę", "niebieska"),
        ("las", "to sówka", "sowa"),
        ("las", "żabka!", "zaba"),
        ("wiaterek", "już!", "spokojnie"),
        ("pomocnik", "lornetkę", "lornetka"),
        ("pomocnik", "latarkę", "latarka"),
        ("laka", "trzy", "trzy"),
        ("laka", "5", "inna_liczba"),
        ("swieto", "chcę tańczyć", "taniec"),
        ("swieto", "zaśpiewajmy piosenkę", "piosenka"),
    ],
)
def test_typical_answers_are_recognized_offline(scene, answer, choice):
    assert KeywordIntentResolver().resolve(SCENARIO.scene(scene), answer).choice_id == choice


def test_counting_aloud_to_two_is_not_taken_as_an_answer():
    # „jedna, dwie” to liczenie w trakcie — bohaterka dopyta, zamiast uznać to za złą odpowiedź
    assert KeywordIntentResolver().resolve(SCENARIO.scene("laka"), "jedna, dwie").choice_id is None


def test_screenplay_dialogue_has_no_gendered_forms_towards_the_audience():
    screenplay = (Path(__file__).resolve().parents[1] / "scenarios" / "klub_ciekawskich.md").read_text(encoding="utf-8")
    dialogue = [line for line in screenplay.splitlines() if line.startswith("> **")]

    assert dialogue  # scenariusz ma dialogi w formacie "> **POSTAĆ**: ..."
    assert [line for line in dialogue if GENDERED_PAST.search(line)] == []


def test_every_option_has_a_short_label_for_audience_phones():
    labels = [c.label for s in SCENARIO.scenes.values() for c in s.choices.values()]

    assert all(labels) and max(map(len, labels)) <= 24

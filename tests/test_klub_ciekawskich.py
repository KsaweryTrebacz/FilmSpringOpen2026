"""Scenariusz „Klub Ciekawskich”: poprawny graf i typowe odpowiedzi dzieci rozpoznawane bez modelu językowego."""

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


def test_hero_is_lila_and_addresses_child_without_gendered_forms():
    assert "Lila Lupka" in SCENARIO.hero
    lines = [s.reprompt for s in SCENARIO.scenes.values()] + [
        c.reply for s in SCENARIO.scenes.values() for c in s.choices.values()
    ]
    for gendered in ("zrobiłeś", "zrobiłaś", "pomogłeś", "pomogłaś", "wybrałeś", "wybrałaś"):
        assert not any(gendered in line for line in lines)


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

"""Odcinek „Klub Ciekawskich”: poprawny graf, okna wyboru i typowe odpowiedzi dzieci rozpoznawane bez modelu."""

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
            todo.extend(scene.successors)
    return seen


def test_every_scene_is_reachable_and_story_has_two_endings():
    assert reachable(SCENARIO) == set(SCENARIO.scenes)
    assert {s.id for s in SCENARIO.scenes.values() if s.is_ending} == {"koniec_taniec", "koniec_piosenka"}


LIVE_LINES = [line for s in SCENARIO.scenes.values() for line in (s.question, s.reprompt, s.fallback)] + [
    c.reply for s in SCENARIO.scenes.values() for c in s.choices.values()
]
# Czas przeszły zdradza płeć: "zrobiłeś/zrobiłaś", "zrobiliście/zrobiłyście", "obudziliśmy/obudziłyśmy".
GENDERED_PAST = re.compile(r"\w+(łeś|łaś|liście|łyście|liśmy|łyśmy)\b")


def test_hero_is_lila_and_talks_to_one_viewer_at_home():
    assert "Lila Lupka" in SCENARIO.hero
    assert "liczbie pojedynczej" in SCENARIO.hero
    assert "widowni" not in SCENARIO.hero  # prompt modelu przechodzi na liczbę mnogą, gdy opis postaci mówi o widowni
    assert SCENARIO.title == "Klub Ciekawskich: Bzyczka szuka domu"


# Zwroty do grupy w liczbie mnogiej: odcinek ogląda zwykle jedno dziecko.
PLURAL_ADDRESS = re.compile(r"\b(pomożecie|macie|wybierzcie|powiedzcie|posłuchajcie|popatrzcie|zobaczcie|liczycie|"
                            r"wstańcie|śpiewajcie|krzyknijcie|krzyczymy|sala|widownia)\b", re.IGNORECASE)


def test_live_lines_have_no_gendered_forms():
    assert [line for line in LIVE_LINES if GENDERED_PAST.search(line)] == []


def test_live_lines_talk_to_one_viewer():
    assert [line for line in LIVE_LINES if PLURAL_ADDRESS.search(line)] == []


def test_every_choice_window_has_two_or_three_options_with_pictures():
    windows = [s for s in SCENARIO.scenes.values() if s.choices]

    assert all(2 <= len(s.choices) <= 3 for s in windows)
    assert all(c.icon for s in windows for c in s.choices.values())  # dla dzieci, które jeszcze nie czytają


def test_choice_windows_give_children_enough_time():
    assert {s.id: s.timeout for s in SCENARIO.scenes.values() if s.timeout} == {
        "powitanie": 15.0, "wiaterek": 20.0, "laka": 15.0,
    }


def test_first_window_shows_recorded_reactions():
    assert all(c.reaction is not None for c in SCENARIO.scene("powitanie").choices.values())


@pytest.mark.parametrize(
    ("scene", "answer", "choice"),
    [
        ("powitanie", "Hop sasa!", "hopsasa"),
        ("powitanie", "puk, puk", "pukanie"),
        ("kuferek", "przez ten kolorowy mostek", "most"),
        ("kuferek", "do lasu", "las"),
        ("most", "czerwoną", "czerwona"),
        ("most", "niebieską deskę", "niebieska"),
        ("las", "to sówka", "sowa"),
        ("las", "żabka!", "zaba"),
        ("wiaterek", "już!", "spokojnie"),
        ("wiaterek", "jeszcze raz", "jeszcze"),
        ("kwiatek", "słonecznik", "slonecznik"),
        ("kwiatek", "ten żółty", "slonecznik"),
        ("kwiatek", "koniczynkę", "koniczyna"),
        ("kwiatek", "stokrotkę", "stokrotka"),
        ("pomocnik", "lornetkę", "lornetka"),
        ("pomocnik", "latarkę", "latarka"),
        ("laka", "trzy", "trzy"),
        ("laka", "5", "inna_liczba"),
        ("laka", "cztery", "inna_liczba"),
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


def test_every_option_has_a_short_label_for_the_choice_window():
    labels = [c.label for s in SCENARIO.scenes.values() for c in s.choices.values()]

    assert all(labels) and max(map(len, labels)) <= 24


def test_balanced_episode_has_calm_and_lively_versions_of_scenes():
    assert SCENARIO.mood == "zrownowazony"
    assert {s.id: set(s.variants) for s in SCENARIO.scenes.values() if s.variants} == {
        "las": {"spokojna", "zywa"}, "wiaterek": {"spokojna"}, "swieto": {"spokojna", "zywa"},
    }


def test_screenplay_talks_to_one_viewer_when_characters_face_the_camera():
    screenplay = (Path(__file__).resolve().parents[1] / "scenarios" / "klub_ciekawskich.md").read_text(encoding="utf-8")
    to_camera = [line for line in screenplay.splitlines() if line.startswith("> **") and "do kamery" in line]

    assert len(to_camera) >= 8
    assert [line for line in to_camera if PLURAL_ADDRESS.search(line)] == []


def test_puzzle_answers_lead_to_their_own_scenes_and_rejoin_the_common_path():
    branches = {
        "most": {"czerwona": "most_przejscie", "niebieska": "most_chwiejny"},
        "las": {"sowa": "las_sowa", "zaba": "las_zaba"},
        "wiaterek": {"spokojnie": "pomocnik", "jeszcze": "wiaterek_jeszcze"},
        "laka": {"trzy": "kwiatek", "inna_liczba": "laka_liczenie"},
    }
    for scene, targets in branches.items():
        assert {cid: c.next for cid, c in SCENARIO.scene(scene).choices.items()} == targets
    rejoin = {s.id: s.next for s in SCENARIO.scenes.values() if s.next}
    assert rejoin == {
        "most_przejscie": "wiaterek", "most_chwiejny": "wiaterek", "las_sowa": "wiaterek", "las_zaba": "wiaterek",
        "wiaterek_jeszcze": "pomocnik", "laka_liczenie": "kwiatek",
    }


def test_every_flower_leads_to_the_celebration():
    # Warstwa kwiatka jest w odcinku na razie wyłączona; nakładanie warstw sprawdzają testy silnika i odtwarzacza.
    assert {c.next for c in SCENARIO.scene("kwiatek").choices.values()} == {"swieto"}


def test_every_scene_tells_the_montage_where_it_happens():
    assert all(s.place for s in SCENARIO.scenes.values())
    assert {s.id: s.transition for s in SCENARIO.scenes.values() if s.transition} == {
        "koniec_taniec": "rozjasnienie", "koniec_piosenka": "rozjasnienie",
    }

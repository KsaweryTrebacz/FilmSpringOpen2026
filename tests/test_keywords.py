from pathlib import Path

import pytest

from bajka.keywords import FallbackResolver, KeywordIntentResolver, main, normalize, same_word
from bajka.ports import IntentResolver, Interpretation
from bajka.scenario import parse_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_normalize_drops_case_and_polish_letters():
    assert normalize("Żółta Łódź, JASKINIĄ!") == "zolta lodz, jaskinia!"


@pytest.mark.parametrize(
    ("spoken", "keyword", "expected"),
    [
        ("lasu", "las", True),
        ("jaskini", "jaskinia", True),
        ("jaskiniach", "jaskinia", True),
        ("lato", "las", False),
        ("3", "3", True),
        ("13", "3", False),
        ("do", "dom", False),
        ("nie", "niebo", False),
        ("most", "mostek", True),
    ],
)
def test_same_word_tolerates_polish_inflection(spoken, keyword, expected):
    assert same_word(spoken, keyword) is expected


def test_resolver_meets_contract():
    assert isinstance(KeywordIntentResolver(), IntentResolver)


def test_choice_id_is_a_keyword(scenario):
    result = KeywordIntentResolver().resolve(scenario.scene("intro"), "Chcę do lasu!")

    assert result == Interpretation(choice_id="las", reply="")


def test_keywords_from_scenario_are_used(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["jaskinia"]["keywords"] = ["dziura w górze", "grota"]
    scene = parse_scenario(scenario_dict, base_dir=Path(".")).scene("intro")

    assert KeywordIntentResolver().resolve(scene, "do tej dziury w górze").choice_id == "jaskinia"
    assert KeywordIntentResolver().resolve(scene, "dziura jest daleko").choice_id is None  # niepełna fraza
    assert KeywordIntentResolver().resolve(scene, "do groty").choice_id == "jaskinia"


def test_answer_matching_two_choices_is_unclear(scenario):
    result = KeywordIntentResolver().resolve(scenario.scene("intro"), "las albo jaskinia")

    assert result.choice_id is None


def test_off_topic_answer_is_unclear(scenario):
    assert KeywordIntentResolver().resolve(scenario.scene("intro"), "banan").choice_id is None


@pytest.mark.parametrize("answer", ["nie wiem", "Nie wiem, las?", "nie umiem", "nie pamiętam"])
def test_dont_know_is_unclear_even_with_similar_words(scenario, answer):
    # „Nie wiem” ma prowadzić do dopytania, nawet gdy w zdaniu jest słowo pasujące do wyboru.
    assert KeywordIntentResolver().resolve(scenario.scene("intro"), answer).choice_id is None


def test_short_keyword_counts_only_as_a_whole_word(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["jaskinia"]["keywords"] = ["nie"]
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    resolver = KeywordIntentResolver()

    assert resolver.resolve(scenario.scene("intro"), "nie, do lasu nie").choice_id is None  # oba wybory: dopytanie
    assert resolver.resolve(scenario.scene("intro"), "spokojnie do lasu").choice_id == "las"  # „…nie” to nie „nie”


def test_short_fragment_does_not_pick_a_choice_by_its_name(scenario):
    # Strzęp rozpoznawanej mowy („jas…”) nie wybiera opcji, której nazwa się od niego zaczyna.
    assert KeywordIntentResolver().resolve(scenario.scene("intro"), "jas").choice_id is None


class BrokenResolver:
    def resolve(self, scene, transcript):
        raise TimeoutError("model nie odpowiada")


class FixedResolver:
    def resolve(self, scene, transcript):
        return Interpretation("jaskinia", "Do jaskini, hura!")


def test_fallback_uses_primary_when_it_works(scenario):
    resolver = FallbackResolver(FixedResolver(), KeywordIntentResolver())

    assert resolver.resolve(scenario.scene("intro"), "do lasu") == Interpretation("jaskinia", "Do jaskini, hura!")


def test_fallback_uses_keywords_when_primary_fails(scenario):
    resolver = FallbackResolver(BrokenResolver(), KeywordIntentResolver())

    assert isinstance(resolver, IntentResolver)
    assert resolver.resolve(scenario.scene("intro"), "do lasu").choice_id == "las"


def test_demo_prints_recognized_choice(capsys):
    assert main([str(ROOT / "scenarios" / "las_czy_jaskinia.yaml"), "do jaskini"]) == 0

    assert "-> jaskinia" in capsys.readouterr().out


def test_demo_rejects_ending_scene(capsys):
    assert main([str(ROOT / "scenarios" / "las_czy_jaskinia.yaml"), "cokolwiek", "--scene", "las"]) == 2

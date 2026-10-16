from pathlib import Path

import pytest

from bajka.scenario import ScenarioError, fill_prompt, load_scenario, missing_media, parse_scenario

OPEN_SCENE = {
    "kind": "open",
    "clip": "ozdoby.mp4",
    "idle": "ozdoby_idle.mp4",
    "drawing": "rysuje.mp4",
    "question": "Jak udekorujemy ul Bzyczki na święto?",
    "reprompt": "Kwiatki, wstążki, a może coś innego?",
    "image_prompt": "the beehive decorated for a party with {idea}",
    "remember": "ozdoby",
    "default_idea": "colorful flowers and ribbons",
    "fallback_clips": ["ozdoby_zapas_1.mp4", "ozdoby_zapas_2.mp4"],
    "next": "las",
}


@pytest.fixture
def live_dict(scenario_dict):
    """Scenariusz z conftest + styl, referencje i scena otwarta między wyborem a lasem."""
    scenario_dict["style"] = "soft watercolor children's book illustration"
    scenario_dict["references"] = ["ref_lila.png", "ref_fiku.png"]
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = dict(OPEN_SCENE)
    return scenario_dict


def test_style_and_references_are_read_relative_to_scenario(live_dict):
    scenario = parse_scenario(live_dict, base_dir=Path("film"))

    assert scenario.style == "soft watercolor children's book illustration"
    assert scenario.references == (Path("film/ref_lila.png"), Path("film/ref_fiku.png"))
    assert scenario.needs_live_images


def test_classic_scenario_has_no_style_and_needs_no_live_images(scenario):
    assert scenario.style == ""
    assert scenario.references == ()
    assert not scenario.needs_live_images


def test_open_scene_is_parsed_with_paths_and_next(live_dict):
    scene = parse_scenario(live_dict, base_dir=Path("film")).scene("ozdoby")

    assert scene.kind == "open"
    assert scene.clip == Path("film/ozdoby.mp4")
    assert scene.drawing == Path("film/rysuje.mp4")
    assert scene.remember == "ozdoby"
    assert scene.default_idea == "colorful flowers and ribbons"
    assert scene.fallback_clips == (Path("film/ozdoby_zapas_1.mp4"), Path("film/ozdoby_zapas_2.mp4"))
    assert scene.successors == ("las",)
    assert not scene.is_ending


def test_successors_of_choice_scene_are_its_choices(scenario):
    assert scenario.scene("intro").successors == ("las", "jaskinia")
    assert scenario.scene("las").successors == ()


@pytest.mark.parametrize("field", ["drawing", "image_prompt", "remember", "default_idea", "fallback_clips", "next"])
def test_open_scene_requires_field(live_dict, field):
    del live_dict["scenes"]["ozdoby"][field]

    with pytest.raises(ScenarioError, match=field):
        parse_scenario(live_dict, base_dir=Path("."))


def test_open_image_prompt_must_use_idea(live_dict):
    live_dict["scenes"]["ozdoby"]["image_prompt"] = "the beehive decorated for a party"

    with pytest.raises(ScenarioError, match="idea"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_open_next_must_exist(live_dict):
    live_dict["scenes"]["ozdoby"]["next"] = "bagno"

    with pytest.raises(ScenarioError, match="bagno"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_template_may_only_use_remembered_ideas(live_dict):
    live_dict["scenes"]["ozdoby"]["image_prompt"] = "the beehive with {idea} and {smok}"

    with pytest.raises(ScenarioError, match="smok"):
        parse_scenario(live_dict, base_dir=Path("."))


@pytest.mark.parametrize(
    "template",
    [
        "the beehive with {} and {idea}",
        "the beehive with {idea",
        "the beehive } with {idea}",
        "the beehive with {idea!z}",
        "the beehive with {idea} and {ozdoby[x]}",
    ],
    ids=["puste_pole", "niedomkniety", "samotny_nawias", "zla_konwersja", "zly_indeks"],
)
def test_malformed_image_prompt_is_rejected_when_loading(live_dict, template):
    live_dict["scenes"]["ozdoby"]["image_prompt"] = template

    with pytest.raises(ScenarioError, match="ozdoby"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_unknown_kind_is_rejected(live_dict):
    live_dict["scenes"]["ozdoby"]["kind"] = "film"

    with pytest.raises(ScenarioError, match="film"):
        parse_scenario(live_dict, base_dir=Path("."))


def test_missing_media_includes_drawing_fallbacks_and_references(tmp_path, live_dict):
    scenario = parse_scenario(live_dict, base_dir=tmp_path)

    missing = {path.name for path in missing_media(scenario)}

    assert {"rysuje.mp4", "ozdoby_zapas_1.mp4", "ozdoby_zapas_2.mp4", "ref_lila.png", "ref_fiku.png"} <= missing


def test_fill_prompt_fills_known_values_and_keeps_unknown():
    assert fill_prompt("ul z {idea} i {smok}", {"idea": "wstążkami"}) == "ul z wstążkami i {smok}"


def test_live_drawing_example_is_valid():
    path = Path(__file__).resolve().parents[1] / "scenarios" / "rysowanie_na_zywo.yaml"

    scenario = load_scenario(path)

    assert scenario.needs_live_images
    assert scenario.scene("skarb").kind == "open"
    assert scenario.scene("intro").choices["jaskinia"].next == "skarb"

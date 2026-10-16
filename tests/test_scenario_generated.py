from pathlib import Path

import pytest

from bajka.placeholders import planned_clips
from bajka.scenario import ScenarioError, load_scenario, missing_media, parse_scenario

GENERATED_SCENE = {
    "kind": "generated",
    "image_prompt": "Lila and Fiku celebrating in a meadow",
    "narration": "Zobacz, jak pięknie świętujemy!",
    "fallback_clips": ["final_zapas.mp4"],
    "next": "las",
}


@pytest.fixture
def generated_dict(scenario_dict):
    """intro → (las) → final_ul [scena generowana] → las."""
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "final_ul"
    scenario_dict["scenes"]["final_ul"] = dict(GENERATED_SCENE)
    return scenario_dict


def test_generated_scene_has_no_clip_and_goes_to_next(generated_dict):
    scenario = parse_scenario(generated_dict, base_dir=Path("film"))
    scene = scenario.scene("final_ul")

    assert scene.kind == "generated"
    assert scene.clip is None
    assert scene.narration == "Zobacz, jak pięknie świętujemy!"
    assert scene.fallback_clips == (Path("film/final_zapas.mp4"),)
    assert scene.successors == ("las",)
    assert not scene.is_ending
    assert scenario.needs_live_images


@pytest.mark.parametrize("field", ["image_prompt", "narration", "fallback_clips", "next"])
def test_generated_scene_requires_field(generated_dict, field):
    del generated_dict["scenes"]["final_ul"][field]

    with pytest.raises(ScenarioError, match=field):
        parse_scenario(generated_dict, base_dir=Path("."))


def test_generated_scene_cannot_use_idea_of_the_moment(generated_dict):
    generated_dict["scenes"]["final_ul"]["image_prompt"] = "a meadow with {idea}"

    with pytest.raises(ScenarioError, match="idea"):
        parse_scenario(generated_dict, base_dir=Path("."))


def test_generated_scene_may_use_remembered_idea(generated_dict):
    generated_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    generated_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "the beehive with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "final_ul",
    }
    generated_dict["scenes"]["final_ul"]["image_prompt"] = "a party at the beehive decorated with {ozdoby}"

    scenario = parse_scenario(generated_dict, base_dir=Path("."))

    assert scenario.scene("final_ul").image_prompt.endswith("{ozdoby}")


def test_missing_media_and_placeholders_cover_only_fallbacks_of_generated_scene(tmp_path, generated_dict):
    scenario = parse_scenario(generated_dict, base_dir=tmp_path)

    assert tmp_path / "final_zapas.mp4" in missing_media(scenario)
    assert (tmp_path / "final_zapas.mp4", "darkred", False) in planned_clips(scenario)  # cichy: pętla pod narracją


def test_live_drawing_example_returns_home_with_remembered_treasure():
    path = Path(__file__).resolve().parents[1] / "scenarios" / "rysowanie_na_zywo.yaml"

    scenario = load_scenario(path)

    assert scenario.scene("skarb").next == "powrot"
    assert "{skarb}" in scenario.scene("powrot").image_prompt

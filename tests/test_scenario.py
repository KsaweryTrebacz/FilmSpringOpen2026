from pathlib import Path

import pytest

from bajka.scenario import ScenarioError, load_scenario, missing_media, parse_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_parses_scenes_choices_and_resolves_paths(scenario_dict):
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))

    intro = scenario.scene("intro")
    assert scenario.start == "intro"
    assert intro.clip == Path("film/intro.mp4")
    assert intro.idle == Path("film/intro_idle.mp4")
    assert intro.default == "las"
    assert intro.choices["jaskinia"].next == "jaskinia"
    assert not intro.is_ending
    assert scenario.scene("las").is_ending


def test_missing_start_scene_is_rejected(scenario_dict):
    scenario_dict["start"] = "prolog"
    with pytest.raises(ScenarioError, match="prolog"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_choice_pointing_to_unknown_scene_is_rejected(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "bagno"
    with pytest.raises(ScenarioError, match="bagno"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_default_must_be_one_of_choices(scenario_dict):
    scenario_dict["scenes"]["intro"]["default"] = "rzeka"
    with pytest.raises(ScenarioError, match="default"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_scene_with_choices_requires_idle_loop(scenario_dict):
    del scenario_dict["scenes"]["intro"]["idle"]
    with pytest.raises(ScenarioError, match="idle"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_choice_requires_reply(scenario_dict):
    del scenario_dict["scenes"]["intro"]["choices"]["las"]["reply"]
    with pytest.raises(ScenarioError, match="reply"):
        parse_scenario(scenario_dict, base_dir=Path("."))


def test_missing_media_lists_files_that_do_not_exist(tmp_path, scenario_dict):
    (tmp_path / "intro.mp4").touch()
    (tmp_path / "las.mp4").touch()
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)

    assert missing_media(scenario) == [tmp_path / "intro_idle.mp4", tmp_path / "jaskinia.mp4"]


def test_invalid_yaml_raises_scenario_error(tmp_path):
    bad = tmp_path / "zly.yaml"
    bad.write_text("scenes: [niezamknięta", encoding="utf-8")
    with pytest.raises(ScenarioError, match="YAML"):
        load_scenario(bad)


def test_bundled_example_scenario_is_valid():
    scenario = load_scenario(ROOT / "scenarios" / "las_czy_jaskinia.yaml")

    assert scenario.start == "intro"
    assert set(scenario.scene("intro").choices) == {"las", "jaskinia"}
    assert scenario.scene("intro").clip == ROOT / "scenarios" / "clips" / "intro.mp4"

from pathlib import Path

import pytest

from bajka.scenario import (
    ScenarioError,
    load_scenario,
    media_files,
    missing_media,
    parse_scenario,
)

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


def test_keywords_are_optional_and_numbers_become_words(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["keywords"] = ["drzewa", 3]
    scenario = parse_scenario(scenario_dict, base_dir=Path("."))

    assert scenario.scene("intro").choices["las"].keywords == ("drzewa", "3")
    assert scenario.scene("intro").choices["jaskinia"].keywords == ()


@pytest.mark.parametrize("field", ["kind", "image_prompt", "fallback_clips", "narration"])
def test_live_drawing_scene_fields_are_rejected_with_a_clear_message(scenario_dict, field):
    scenario_dict["scenes"]["las"][field] = "open"
    with pytest.raises(ScenarioError, match=f"scena 'las': pola {field} .*rysowanie na żywo usunięto"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


@pytest.mark.parametrize("field", ["style", "references"])
def test_live_drawing_scenario_fields_are_rejected_with_a_clear_message(scenario_dict, field):
    scenario_dict[field] = "watercolor"
    with pytest.raises(ScenarioError, match=f"scenariusz: pola {field} .*rysowanie na żywo usunięto"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_keywords_must_be_a_list_of_words(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["keywords"] = "drzewa"
    with pytest.raises(ScenarioError, match="keywords"):
        parse_scenario(scenario_dict, base_dir=Path("."))


# Nastrój filmu i wersje scen (tętno sali)


def calm_film(scenario_dict, variants):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = variants
    return scenario_dict


def test_mood_and_scene_versions_are_parsed(scenario_dict):
    scenario = parse_scenario(calm_film(scenario_dict, {"spokojna": "las_spokojna.mp4"}), base_dir=Path("film"))

    assert scenario.mood == "spokojny"
    assert scenario.scene("las").variants == {"spokojna": Path("film/las_spokojna.mp4")}
    assert scenario.scene("intro").variants == {}


def test_film_without_mood_does_not_adapt(scenario):
    assert scenario.mood == ""


def test_unknown_mood_is_refused(scenario_dict):
    scenario_dict["mood"] = "straszny"
    with pytest.raises(ScenarioError, match="'mood'.*spokojny, zywy"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_unknown_scene_version_is_refused(scenario_dict):
    with pytest.raises(ScenarioError, match="scena 'las': nieznane wersje sceny: szybka"):
        parse_scenario(calm_film(scenario_dict, {"szybka": "las_szybka.mp4"}), base_dir=Path("film"))


def test_scene_versions_must_be_a_mapping_of_files(scenario_dict):
    with pytest.raises(ScenarioError, match="'variants'"):
        parse_scenario(calm_film(scenario_dict, ["las_spokojna.mp4"]), base_dir=Path("film"))


def test_scene_versions_need_the_mood_of_the_film(scenario_dict):
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}
    with pytest.raises(ScenarioError, match="scena 'las': 'variants' wymaga pola 'mood'"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_missing_media_lists_missing_version_clips(tmp_path, scenario_dict):
    for name in ("intro.mp4", "intro_idle.mp4", "las.mp4", "jaskinia.mp4"):
        (tmp_path / name).touch()
    scenario = parse_scenario(calm_film(scenario_dict, {"spokojna": "las_spokojna.mp4"}), base_dir=tmp_path)

    assert missing_media(scenario) == [tmp_path / "las_spokojna.mp4"]


@pytest.mark.parametrize(
    ("where", "field"), [("scene", "vote"), ("choice", "call"), ("choice", "call_clip")]
)
def test_cinema_shout_fields_are_rejected_with_a_clear_message(scenario_dict, where, field):
    intro = scenario_dict["scenes"]["intro"]
    (intro if where == "scene" else intro["choices"]["las"])[field] = "Kto do lasu?"
    with pytest.raises(ScenarioError, match=f"pola {field} .*oknami wyboru"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_choice_window_fields_title_icon_reaction_and_timeout(scenario_dict):
    scenario_dict["title"] = "Lisek i las"
    scenario_dict["scenes"]["intro"]["timeout"] = 15
    scenario_dict["scenes"]["intro"]["choices"]["las"].update(icon="🌲", reaction="reakcja_las.mp4")
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))

    intro = scenario.scene("intro")
    assert scenario.title == "Lisek i las"
    assert intro.timeout == 15.0
    assert intro.choices["las"].icon == "🌲"
    assert intro.choices["las"].reaction == Path("film/reakcja_las.mp4")
    assert intro.choices["jaskinia"].reaction is None and intro.choices["jaskinia"].display_label == "Jaskinia"
    assert parse_scenario({**scenario_dict, "title": None}, base_dir=Path(".")).title == ""


@pytest.mark.parametrize("timeout", [2, 61, "długo", True])
def test_choice_window_time_must_be_reasonable(scenario_dict, timeout):
    scenario_dict["scenes"]["intro"]["timeout"] = timeout
    with pytest.raises(ScenarioError, match="timeout"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_reaction_clips_are_media_files_of_the_episode(tmp_path, scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["reaction"] = "reakcja_las.mp4"
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)

    assert media_files(scenario) == [tmp_path / name for name in
                                     ("intro.mp4", "intro_idle.mp4", "reakcja_las.mp4", "las.mp4", "jaskinia.mp4")]
    assert tmp_path / "reakcja_las.mp4" in missing_media(scenario)


# Gałęzie, sceny przejściowe i warstwy


def branching(scenario_dict):
    """Las ma własną scenę dalszego ciągu bez pytania, która wraca do wspólnej drogi (jaskini)."""
    scenario_dict["scenes"]["las"] = {"clip": "las.mp4", "next": "jaskinia", "place": "Las", "transition": "przetarcie"}
    return scenario_dict


def test_scene_without_question_goes_on_by_itself(scenario_dict):
    scenario = parse_scenario(branching(scenario_dict), base_dir=Path("film"))

    las = scenario.scene("las")
    assert not las.is_ending and las.next == "jaskinia" and las.successors == ["jaskinia"]
    assert las.place == "Las" and las.transition == "przetarcie"
    assert scenario.scene("intro").successors == ["las", "jaskinia"]
    assert scenario.scene("jaskinia").is_ending and scenario.scene("jaskinia").successors == []


def test_next_must_point_to_a_scene_and_cannot_mix_with_choices(scenario_dict):
    scenario_dict["scenes"]["las"]["next"] = "gory"
    with pytest.raises(ScenarioError, match="'gory'"):
        parse_scenario(scenario_dict, base_dir=Path("film"))

    scenario_dict["scenes"]["las"]["next"] = "jaskinia"
    scenario_dict["scenes"]["intro"]["next"] = "las"
    with pytest.raises(ScenarioError, match="bez pola 'next'"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_scenes_without_questions_cannot_go_in_circles(scenario_dict):
    scenario_dict["scenes"]["las"]["next"] = "jaskinia"
    scenario_dict["scenes"]["jaskinia"]["next"] = "las"
    with pytest.raises(ScenarioError, match="w koło"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_unknown_transition_hint_is_refused(scenario_dict):
    scenario_dict["scenes"]["las"]["transition"] = "eksplozja"
    with pytest.raises(ScenarioError, match="transition"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_loop_transition_is_read_and_checked(scenario_dict):
    assert parse_scenario(scenario_dict, base_dir=Path("film")).loop_transition == ""
    scenario_dict["loop_transition"] = "przenikanie"
    assert parse_scenario(scenario_dict, base_dir=Path("film")).loop_transition == "przenikanie"
    scenario_dict["loop_transition"] = "eksplozja"
    with pytest.raises(ScenarioError, match="loop_transition"):
        parse_scenario(scenario_dict, base_dir=Path("film"))


def test_choice_layer_fills_a_slot_shown_by_later_scenes(tmp_path, scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"].update(layer="warstwa_latarka.webm", slot="pomocnik")
    scenario_dict["scenes"]["intro"]["choices"]["jaskinia"]["layer"] = "warstwa_lina.webm"
    scenario_dict["scenes"]["las"]["layers"] = ["pomocnik"]
    scenario_dict["scenes"]["jaskinia"]["layers"] = ["intro"]  # bez `slot` miejscem jest scena wyboru
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)

    las, lina = scenario.scene("intro").choices["las"], scenario.scene("intro").choices["jaskinia"]
    assert (las.layer, las.slot) == (tmp_path / "warstwa_latarka.webm", "pomocnik")
    assert lina.slot == "intro"
    assert scenario.scene("las").layers == ("pomocnik",)
    assert tmp_path / "warstwa_latarka.webm" in missing_media(scenario)


def test_layer_needs_transparency_and_a_filled_slot(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["layer"] = "warstwa.mp4"
    with pytest.raises(ScenarioError, match="przezroczystość"):
        parse_scenario(scenario_dict, base_dir=Path("film"))

    scenario_dict["scenes"]["intro"]["choices"]["las"]["layer"] = "warstwa.webm"
    scenario_dict["scenes"]["las"]["layers"] = ["kwiatek"]
    with pytest.raises(ScenarioError, match="kwiatek"):
        parse_scenario(scenario_dict, base_dir=Path("film"))

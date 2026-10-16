from pathlib import Path

import pytest
import yaml

from bajka.app import LiveImages, build_live_images, main, prepare_session_dir
from bajka.config import ConfigError
from bajka.placeholders import planned_clips
from bajka.ports import Animator, Illustrator, Imaginer
from bajka.safety import SafeImaginer
from bajka.scenario import parse_scenario

FULL_ENV = {
    "AZURE_IMAGE_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_IMAGE_API_KEY": "klucz-obrazow",
    "AZURE_IMAGE_DEPLOYMENT": "gpt-image-2",
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
}


@pytest.fixture
def live_dict(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "ozdoby"
    scenario_dict["scenes"]["ozdoby"] = {
        "kind": "open",
        "clip": "ozdoby.mp4",
        "idle": "ozdoby_idle.mp4",
        "drawing": "rysuje.mp4",
        "question": "Jak udekorujemy ul Bzyczki na święto?",
        "reprompt": "Kwiatki czy wstążki?",
        "image_prompt": "the beehive decorated for a party with {idea}",
        "remember": "ozdoby",
        "default_idea": "flowers",
        "fallback_clips": ["ozdoby_zapas.mp4"],
        "next": "las",
    }
    return scenario_dict


@pytest.fixture
def live_scenario(live_dict):
    return parse_scenario(live_dict, base_dir=Path("film"))


def test_classic_scenario_builds_no_live_modules(scenario):
    assert build_live_images({}, scenario) == LiveImages()


def test_live_scenario_lists_missing_image_keys(live_scenario, tmp_path):
    with pytest.raises(ConfigError) as exc:
        build_live_images({}, live_scenario, lambda: tmp_path)

    assert "AZURE_IMAGE_ENDPOINT" in str(exc.value)


def test_live_scenario_needs_ffmpeg(live_scenario, monkeypatch, tmp_path):
    monkeypatch.setattr("bajka.app.shutil.which", lambda name: None)

    with pytest.raises(ConfigError, match="ffmpeg"):
        build_live_images(FULL_ENV, live_scenario, lambda: tmp_path)


def test_live_scenario_builds_modules_that_fulfil_contracts(live_scenario, monkeypatch, tmp_path):
    monkeypatch.setattr("bajka.app.shutil.which", lambda name: "ffmpeg")

    live = build_live_images({**FULL_ENV, "BAJKA_IMAGE_TIMEOUT_S": "20"}, live_scenario, lambda: tmp_path)

    assert isinstance(live.imaginer, Imaginer)
    assert isinstance(live.imaginer, SafeImaginer)  # kwestie wyobraźni przechodzą przez filtr regulaminu
    assert isinstance(live.illustrator, Illustrator)
    assert isinstance(live.animator, Animator)
    assert live.timeout_s == 20.0


def test_new_session_dir_removes_pictures_of_previous_sessions(tmp_path):
    old = prepare_session_dir(tmp_path / "bajka")
    (old / "obraz.png").write_bytes(b"PNG")

    new = prepare_session_dir(tmp_path / "bajka")

    assert new.is_dir()
    assert not old.exists()


def test_new_session_dir_leaves_unrelated_files_alone(tmp_path):
    base = tmp_path / "bajka"
    base.mkdir()
    (base / "notatki.txt").write_text("nie ruszać", encoding="utf-8")
    (base / "inne").mkdir()

    prepare_session_dir(base)

    assert (base / "notatki.txt").is_file()
    assert (base / "inne").is_dir()


def test_failed_cleanup_is_logged_and_does_not_stop_the_show(tmp_path, monkeypatch, caplog):
    old = prepare_session_dir(tmp_path / "bajka")

    def locked(path):
        raise PermissionError("plik używany przez inny proces")

    monkeypatch.setattr("bajka.app.shutil.rmtree", locked)

    new = prepare_session_dir(tmp_path / "bajka")

    assert new.is_dir() and new != old
    assert "Nie udało się usunąć" in caplog.text


def test_main_with_open_scene_and_no_image_keys_exits_with_code_2(tmp_path, monkeypatch, live_dict, caplog):
    monkeypatch.chdir(tmp_path)  # w katalogu testu nie ma pliku .env
    for name in FULL_ENV:
        monkeypatch.delenv(name, raising=False)
    for path, _, _ in planned_clips(parse_scenario(live_dict, base_dir=tmp_path)):
        path.touch()
    scenario_file = tmp_path / "bajka.yaml"
    scenario_file.write_text(yaml.safe_dump(live_dict, allow_unicode=True), encoding="utf-8")

    assert main([str(scenario_file), "--text", "--no-llm"]) == 2
    assert "AZURE_IMAGE_ENDPOINT" in caplog.text


def test_missing_image_keys_are_reported_before_loading_speech_and_models(tmp_path, monkeypatch, live_dict, caplog):
    monkeypatch.chdir(tmp_path)
    for name in FULL_ENV:
        monkeypatch.delenv(name, raising=False)
    for path, _, _ in planned_clips(parse_scenario(live_dict, base_dir=tmp_path)):
        path.touch()
    scenario_file = tmp_path / "bajka.yaml"
    scenario_file.write_text(yaml.safe_dump(live_dict, allow_unicode=True), encoding="utf-8")

    def must_not_load(*args, **kwargs):
        raise AssertionError("mowa i modele ładowane przed sprawdzeniem kluczy obrazów")

    monkeypatch.setattr("bajka.app.build_speech", must_not_load)
    monkeypatch.setattr("bajka.app.build_resolver", must_not_load)

    assert main([str(scenario_file), "--text", "--no-llm"]) == 2
    assert "AZURE_IMAGE_ENDPOINT" in caplog.text


# Klipy-zaślepki dla scen otwartych


def test_open_scene_gets_silent_drawing_loop_and_fallback_clips_with_sound(live_scenario):
    tone = {path.name: with_tone for path, _, with_tone in planned_clips(live_scenario)}

    assert tone["ozdoby.mp4"] is True
    assert tone["ozdoby_idle.mp4"] is False
    assert tone["rysuje.mp4"] is False
    assert tone["ozdoby_zapas.mp4"] is True


def test_shared_drawing_loop_is_planned_once(live_dict):
    live_dict["scenes"]["ozdoby2"] = {**live_dict["scenes"]["ozdoby"], "clip": "ozdoby2.mp4", "remember": "druga"}
    live_dict["scenes"]["ozdoby"]["next"] = "ozdoby2"

    names = [path.name for path, _, _ in planned_clips(parse_scenario(live_dict, base_dir=Path("film")))]

    assert names.count("rysuje.mp4") == 1

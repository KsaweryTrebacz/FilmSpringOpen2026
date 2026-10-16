import yaml

from bajka.app import main, parse_args
from bajka.config import OPENAI_VARS, SPEECH_VARS


def write_scenario(path, scenario_dict):
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


def test_flags_are_parsed():
    args = parse_args(["bajka.yaml", "--text", "--windowed"])

    assert args.scenario.name == "bajka.yaml"
    assert args.text and args.windowed


def test_default_is_fullscreen_with_voice():
    args = parse_args(["bajka.yaml"])

    assert not args.text and not args.windowed


def test_missing_scenario_file_exits_with_code_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert main([str(tmp_path / "nie_ma.yaml")]) == 2


def test_missing_settings_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)  # w katalogu testu nie ma pliku .env
    for name in OPENAI_VARS + SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path)]) == 2


def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)
    for name in OPENAI_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--text"]) == 2

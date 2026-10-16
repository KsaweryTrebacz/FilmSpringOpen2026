import yaml

from bajka.app import main, parse_args

LLM_VARS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
SPEECH_VARS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")


def write_scenario(path, scenario_dict):
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


def write_media(directory, scenario_dict):
    for scene in scenario_dict["scenes"].values():
        for key in ("clip", "idle"):
            if key in scene:
                (directory / scene[key]).touch()


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
    for name in LLM_VARS + SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path)]) == 2


def test_missing_speech_keys_exit_with_code_2_before_opening_window(tmp_path, monkeypatch, scenario_dict, caplog):
    monkeypatch.chdir(tmp_path)
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    for name in SPEECH_VARS:
        monkeypatch.delenv(name, raising=False)
    write_media(tmp_path, scenario_dict)  # klipy są, brakuje tylko kluczy mowy
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path)]) == 2
    assert "AZURE_SPEECH_KEY" in caplog.text


def test_missing_video_files_exit_with_code_2(tmp_path, monkeypatch, scenario_dict):
    monkeypatch.chdir(tmp_path)
    for name in LLM_VARS:
        monkeypatch.setenv(name, "wartosc-testowa")
    path = write_scenario(tmp_path / "bajka.yaml", scenario_dict)

    assert main([str(path), "--text"]) == 2

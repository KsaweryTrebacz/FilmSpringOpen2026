import os

import pytest

from bajka.config import ConfigError, get_int, load_env, require


def test_require_passes_when_all_values_are_present():
    require({"A": "1", "B": "2"}, "A", "B")


def test_require_lists_every_missing_or_empty_variable():
    with pytest.raises(ConfigError) as exc:
        require({"A": "1", "B": ""}, "A", "B", "C")

    assert "B" in str(exc.value)
    assert "C" in str(exc.value)
    assert "A," not in str(exc.value)


def test_get_int_returns_default_when_variable_is_missing_or_empty():
    assert get_int({}, "LICZBA", 7) == 7
    assert get_int({"LICZBA": ""}, "LICZBA", 7) == 7


def test_get_int_parses_value():
    assert get_int({"LICZBA": "800"}, "LICZBA", 7) == 800


def test_get_int_rejects_non_numeric_value():
    with pytest.raises(ConfigError, match="LICZBA"):
        get_int({"LICZBA": "dużo"}, "LICZBA", 7)


def test_load_env_reads_dotenv_from_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BAJKA_TEST_VAR=z-pliku\n", encoding="utf-8")
    try:
        assert load_env()["BAJKA_TEST_VAR"] == "z-pliku"
    finally:
        os.environ.pop("BAJKA_TEST_VAR", None)

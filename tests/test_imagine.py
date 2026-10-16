import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from bajka.config import ConfigError
from bajka.imagine import AzureImaginer, ImagineSettings, main, parse_vision
from bajka.ports import Imaginer, Vision
from bajka.scenario import Scene

LLM_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "klucz-llm",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
}
OPEN_SCENE = Scene(
    id="ozdoby",
    clip=Path("ozdoby.mp4"),
    kind="open",
    question="Jak udekorujemy ul Bzyczki na święto?",
    image_prompt="the beehive decorated for a party with {idea}",
)


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))])


def make_imaginer(content):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return AzureImaginer(client, deployment="gpt-4o-mini", hero="Lila Lupka, odkrywczyni"), completions


def answer(reply, idea):
    return json.dumps({"reply": reply, "idea": idea})


def test_imagine_returns_reply_and_idea():
    imaginer, _ = make_imaginer(answer("Tęczowe wstążki? Już rysuję!", "rainbow ribbons"))

    vision = imaginer.imagine(OPEN_SCENE, "tęczowymi wstążkami")

    assert isinstance(imaginer, Imaginer)
    assert vision == Vision(reply="Tęczowe wstążki? Już rysuję!", idea="rainbow ribbons")


def test_request_sends_hero_question_and_childs_words_with_strict_schema():
    imaginer, completions = make_imaginer(answer("Super!", "ribbons"))

    imaginer.imagine(OPEN_SCENE, "wstążkami")

    kwargs = completions.kwargs
    system, user = kwargs["messages"]
    assert kwargs["model"] == "gpt-4o-mini"
    assert "Lila Lupka" in system["content"]
    assert "Jak udekorujemy ul Bzyczki na święto?" in system["content"]
    assert "bez form zależnych od płci" in system["content"]
    assert user == {"role": "user", "content": "wstążkami"}
    schema = kwargs["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["required"] == ["reply", "idea"]


def test_prompt_carries_regulamin_rules_for_spoken_lines():
    imaginer, completions = make_imaginer(answer("Super!", "ribbons"))

    imaginer.imagine(OPEN_SCENE, "wstążkami")

    system = completions.kwargs["messages"][0]["content"]
    assert "Nie powtarzaj brzydkich ani obraźliwych słów" in system
    assert "nie mów o przemocy" in system
    assert "liczbie mnogiej" in system
    assert "mów tylko\n   prawdę" in system or "mów tylko prawdę" in system


def test_unusable_idea_comes_back_empty():
    vision = parse_vision(answer("Hmm, narysuję coś innego!", ""))

    assert vision.idea == ""


def test_malformed_answer_is_an_error():
    with pytest.raises(ValueError):
        parse_vision("to nie jest JSON")
    with pytest.raises(ValueError):
        parse_vision(json.dumps(["reply", "idea"]))


def test_settings_use_the_same_azure_openai_variables_as_intent():
    settings = ImagineSettings.from_env(LLM_ENV)

    assert (settings.deployment, settings.api_version) == ("gpt-4o-mini", "2024-10-21")
    with pytest.raises(ConfigError, match="AZURE_OPENAI_ENDPOINT"):
        ImagineSettings.from_env({})


def test_live_client_gives_up_fast_so_the_fallback_clip_comes_in_time(monkeypatch):
    created = {}

    def spy(**kwargs):
        created.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("openai.AzureOpenAI", spy)

    AzureImaginer.from_settings(ImagineSettings.from_env(LLM_ENV), "Lila Lupka")

    assert created["timeout"] == 6.0
    assert created["max_retries"] == 0


# Demo: python -m bajka.imagine


@pytest.fixture
def scenario_file(tmp_path, scenario_dict):
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
        "fallback_clips": ["zapas.mp4"],
        "next": "las",
    }
    path = tmp_path / "bajka.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def llm_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in LLM_ENV.items():
        monkeypatch.setenv(name, value)


def use_fake_llm(monkeypatch, content):
    imaginer, completions = make_imaginer(content)
    monkeypatch.setattr(AzureImaginer, "from_settings", classmethod(lambda cls, settings, hero: imaginer))
    return completions


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, scenario_file, capsys):
    monkeypatch.chdir(tmp_path)
    for name in LLM_ENV:
        monkeypatch.delenv(name, raising=False)

    assert main([str(scenario_file), "wstążkami"]) == 2
    assert "AZURE_OPENAI_ENDPOINT" in capsys.readouterr().err


def test_demo_uses_first_open_scene_and_shows_image_prompt(llm_keys, monkeypatch, scenario_file, capsys):
    use_fake_llm(monkeypatch, answer("Tęczowe wstążki? Już rysuję!", "rainbow ribbons"))

    assert main([str(scenario_file), "tęczowymi wstążkami"]) == 0

    out = capsys.readouterr().out
    assert "Scena: ozdoby" in out
    assert "Postać: Tęczowe wstążki? Już rysuję!" in out
    assert "Obraz: the beehive decorated for a party with rainbow ribbons" in out


def test_demo_reports_unusable_idea(llm_keys, monkeypatch, scenario_file, capsys):
    use_fake_llm(monkeypatch, answer("Narysuję coś innego!", ""))

    assert main([str(scenario_file), "coś strasznego"]) == 0

    assert "nie do użycia" in capsys.readouterr().out


def test_demo_rejects_scene_without_question(llm_keys, monkeypatch, scenario_file, capsys):
    use_fake_llm(monkeypatch, answer("x", "y"))

    assert main([str(scenario_file), "cokolwiek", "--scene", "las"]) == 2
    assert "las" in capsys.readouterr().err

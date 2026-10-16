import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from bajka.config import ConfigError
from bajka.illustrate import AzureIllustrator, ImageSettings, build_prompt, load_shots, main
from bajka.ports import Illustrator

IMAGE_ENV = {
    "AZURE_IMAGE_ENDPOINT": "https://bajka.openai.azure.com/",
    "AZURE_IMAGE_API_KEY": "klucz-obrazow",
    "AZURE_IMAGE_DEPLOYMENT": "gpt-image-2",
}


class FakeImages:
    """Udaje client.images z SDK openai: zapamiętuje wywołania i zwraca obraz w base64."""

    def __init__(self, png=b"PNG", error=None):
        self.calls = []
        self._result = SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(png).decode())])
        self._error = error

    def generate(self, **kwargs):
        return self._answer("generate", kwargs)

    def edit(self, **kwargs):
        # pliki są otwarte tylko w trakcie wywołania, więc zapamiętujemy ich nazwy
        return self._answer("edit", {**kwargs, "image": [Path(f.name).name for f in kwargs["image"]]})

    def _answer(self, method, kwargs):
        self.calls.append((method, kwargs))
        if self._error is not None:
            raise self._error
        return self._result


def make_illustrator(tmp_path, images, references=()):
    client = SimpleNamespace(images=images)
    return AzureIllustrator(client, "gpt-image-2", tmp_path / "sesja", style="watercolor", references=references)


def write_references(tmp_path):
    paths = [tmp_path / "ref_lila.png", tmp_path / "ref_fiku.png"]
    for path in paths:
        path.write_bytes(b"REF")
    return tuple(paths)


# Prompt i ustawienia


def test_prompt_adds_style_safety_and_reference_hint():
    prompt = build_prompt("the beehive decorated with ribbons.", "soft watercolor", with_references=True)

    assert prompt.startswith("the beehive decorated with ribbons.")
    assert "Style: soft watercolor." in prompt
    assert "reference images" in prompt
    assert "not photorealistic" in prompt


def test_prompt_without_style_and_references_has_only_safety_hint():
    prompt = build_prompt("a red apple", "", with_references=False)

    assert "Style" not in prompt and "reference" not in prompt
    assert "no text" in prompt


def test_settings_read_keys_and_apply_defaults():
    settings = ImageSettings.from_env(IMAGE_ENV)

    assert settings.deployment == "gpt-image-2"
    assert settings.api_version == "2025-04-01-preview"
    assert (settings.size, settings.quality, settings.timeout_s) == ("1536x1024", "medium", 25)


def test_settings_require_endpoint_key_and_deployment():
    with pytest.raises(ConfigError) as exc:
        ImageSettings.from_env({})

    for name in IMAGE_ENV:
        assert name in str(exc.value)


def test_settings_overrides():
    env = {**IMAGE_ENV, "BAJKA_IMAGE_SIZE": "1024x1024", "BAJKA_IMAGE_QUALITY": "low", "BAJKA_IMAGE_TIMEOUT_S": "15"}

    settings = ImageSettings.from_env(env)

    assert (settings.size, settings.quality, settings.timeout_s) == ("1024x1024", "low", 15)


# Rysowanie


def test_without_references_generates_and_saves_png(tmp_path):
    images = FakeImages(png=b"OBRAZ")
    illustrator = make_illustrator(tmp_path, images)

    path = illustrator.draw("the beehive decorated with ribbons")

    method, kwargs = images.calls[0]
    assert isinstance(illustrator, Illustrator)
    assert method == "generate"
    assert kwargs["model"] == "gpt-image-2"
    assert (kwargs["size"], kwargs["quality"]) == ("1536x1024", "medium")
    assert "Style: watercolor." in kwargs["prompt"]
    assert path.parent == tmp_path / "sesja" and path.suffix == ".png"
    assert path.read_bytes() == b"OBRAZ"


def test_with_references_edits_with_all_reference_images(tmp_path):
    images = FakeImages()
    illustrator = make_illustrator(tmp_path, images, references=write_references(tmp_path))

    illustrator.draw("Lila decorates the beehive")

    method, kwargs = images.calls[0]
    assert method == "edit"
    assert kwargs["image"] == ["ref_lila.png", "ref_fiku.png"]
    assert "reference images" in kwargs["prompt"]


def test_named_drawing_uses_given_file_name(tmp_path):
    path = make_illustrator(tmp_path, FakeImages()).draw("a meadow", name="02_kuferek_01")

    assert path.name == "02_kuferek_01.png"


def test_each_drawing_gets_its_own_file(tmp_path):
    illustrator = make_illustrator(tmp_path, FakeImages())

    assert illustrator.draw("a") != illustrator.draw("b")


def test_service_errors_are_passed_to_the_caller(tmp_path):
    illustrator = make_illustrator(tmp_path, FakeImages(error=RuntimeError("content_policy_violation")))

    with pytest.raises(RuntimeError, match="content_policy_violation"):
        illustrator.draw("a scary monster")


# Plik ujęć do produkcji


def test_load_shots_reads_names_and_prompts(tmp_path):
    shots = tmp_path / "ujecia.yaml"
    shots.write_text(yaml.safe_dump([{"name": "01", "prompt": "Lila waves"}, {"name": "02", "prompt": "Fiku jumps"}]))

    assert load_shots(shots) == [("01", "Lila waves"), ("02", "Fiku jumps")]


def test_load_shots_rejects_shot_without_prompt(tmp_path):
    shots = tmp_path / "ujecia.yaml"
    shots.write_text(yaml.safe_dump([{"name": "01"}]))

    with pytest.raises(ValueError, match="prompt"):
        load_shots(shots)


# Demo: python -m bajka.illustrate


@pytest.fixture
def scenario_file(tmp_path, scenario_dict):
    scenario_dict["style"] = "soft watercolor"
    path = tmp_path / "bajka.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def image_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # żeby testy nie czytały prawdziwego .env z repozytorium
    for name, value in IMAGE_ENV.items():
        monkeypatch.setenv(name, value)


def use_fake_images(monkeypatch, images):
    def from_settings(cls, settings, out_dir, style="", references=(), max_retries=0):
        return AzureIllustrator(SimpleNamespace(images=images), settings.deployment, out_dir, style, references)

    monkeypatch.setattr(AzureIllustrator, "from_settings", classmethod(from_settings))


def test_demo_without_keys_exits_with_code_2(tmp_path, monkeypatch, scenario_file, capsys):
    monkeypatch.chdir(tmp_path)
    for name in IMAGE_ENV:
        monkeypatch.delenv(name, raising=False)

    assert main([str(scenario_file), "a meadow"]) == 2
    assert "AZURE_IMAGE_ENDPOINT" in capsys.readouterr().err


def test_demo_needs_prompt_or_batch(scenario_file):
    with pytest.raises(SystemExit):
        main([str(scenario_file)])


def test_demo_draws_one_picture_with_scenario_style(image_keys, monkeypatch, scenario_file, tmp_path, capsys):
    images = FakeImages()
    use_fake_images(monkeypatch, images)

    assert main([str(scenario_file), "a meadow", "--out", str(tmp_path / "out")]) == 0

    assert "Style: soft watercolor." in images.calls[0][1]["prompt"]
    assert ".png" in capsys.readouterr().out


def test_demo_batch_reports_median_and_keeps_going_after_error(image_keys, monkeypatch, scenario_file, tmp_path, capsys):
    shots = tmp_path / "ujecia.yaml"
    shots.write_text(yaml.safe_dump([{"name": "01", "prompt": "a"}, {"name": "02", "prompt": "b"}]))
    images = FakeImages()
    use_fake_images(monkeypatch, images)

    assert main([str(scenario_file), "--batch", str(shots), "--out", str(tmp_path / "out")]) == 0

    out = capsys.readouterr().out
    assert "01.png" in out and "02.png" in out
    assert "Mediana" in out


def test_demo_returns_1_when_every_picture_fails(image_keys, monkeypatch, scenario_file, capsys):
    use_fake_images(monkeypatch, FakeImages(error=RuntimeError("401 zły klucz")))

    assert main([str(scenario_file), "a meadow"]) == 1
    assert "401" in capsys.readouterr().err

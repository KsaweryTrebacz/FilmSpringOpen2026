import json
from pathlib import Path

import yaml

from bajka.manifest import FORMAT, build_manifest, main
from bajka.scenario import parse_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_describes_scenes_windows_and_the_linear_path(scenario_dict):
    scenario_dict["title"] = "Lisek i las"
    scenario_dict["scenes"]["intro"]["choices"]["las"].update(icon="🌲", reaction="reakcje/las.mp4", keywords=["drzewa"])
    manifest = build_manifest(parse_scenario(scenario_dict, base_dir=Path("/odcinek")), media_root=Path("/odcinek"))

    intro = manifest["scenes"]["intro"]
    assert manifest["format"] == FORMAT and manifest["title"] == "Lisek i las" and manifest["start"] == "intro"
    assert intro["clip"] == "intro.mp4" and intro["idle"] == "intro_idle.mp4" and intro["seconds"] == 12.0
    assert intro["choices"][0] == {
        "id": "las", "label": "Las", "icon": "🌲", "next": "las", "reply": "Do lasu! Trzymaj się blisko!",
        "reaction": "reakcje/las.mp4", "voice": {"description": "pójść do mrocznego lasu", "keywords": ["drzewa"]},
    }
    assert manifest["scenes"]["las"] == {"clip": "las.mp4", "ending": True}
    assert manifest["linear_path"] == ["intro", "las"]


def test_bundled_episode_exports_to_json(tmp_path, capsys):
    out = tmp_path / "odcinek.json"

    assert main([str(ROOT / "scenarios" / "klub_ciekawskich.yaml"), "--out", str(out)]) == 0
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["title"] == "Klub Ciekawskich: Bzyczka szuka domu"
    assert manifest["linear_path"][0] == "powitanie" and manifest["linear_path"][-1] == "koniec_taniec"
    assert manifest["scenes"]["las"]["variants"].keys() == {"spokojna", "zywa"}
    assert manifest["scenes"]["powitanie"]["clip"].endswith("clips/klub_ciekawskich/01_powitanie.mp4")


def test_manifest_goes_to_screen_without_out(tmp_path, scenario_dict, capsys):
    path = tmp_path / "odcinek.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")

    assert main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["scenes"]["intro"]["clip"] == "intro.mp4"

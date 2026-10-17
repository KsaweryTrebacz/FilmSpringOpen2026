import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from bajka.clips import LOOP_VOLUME, SEAM_SECONDS, Assignment, convert_command, main, read_map
from bajka.linear import probe
from bajka.scenario import ScenarioError

ROOT = Path(__file__).resolve().parents[1]


def write_map(tmp_path, scenario_dict, clips):
    (tmp_path / "odcinek.yaml").write_text(yaml.safe_dump(scenario_dict, allow_unicode=True), encoding="utf-8")
    mapping = tmp_path / "klipy.yaml"
    mapping.write_text(yaml.safe_dump({"scenario": "odcinek.yaml", "clips": clips}), encoding="utf-8")
    return mapping


def test_map_names_scene_files_and_marks_waiting_loops(tmp_path, scenario_dict):
    mapping = write_map(tmp_path, scenario_dict, {"intro.mp4": "Girl_waves.mp4", "intro_idle.mp4": "Listening.mp4"})

    assert read_map(mapping) == [
        Assignment(tmp_path / "Girl_waves.mp4", tmp_path / "intro.mp4", loop=False),
        Assignment(tmp_path / "Listening.mp4", tmp_path / "intro_idle.mp4", loop=True),
    ]


def test_map_with_a_file_the_scenario_does_not_have_is_refused(tmp_path, scenario_dict):
    mapping = write_map(tmp_path, scenario_dict, {"intro_v2.mp4": "Girl_waves.mp4"})

    with pytest.raises(ScenarioError, match="intro_v2.mp4"):
        read_map(mapping)


def test_scene_clip_is_only_brought_to_the_common_format():
    cmd = convert_command(Assignment(Path("gen.mp4"), Path("intro.mp4"), loop=False), 8.0, has_audio=True)

    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "scale=1280:720" in graph and "fps=24" in graph and "xfade" not in graph
    assert cmd[-3:] == ["-movflags", "+faststart", "intro.mp4"]


def test_waiting_loop_gets_a_seam_and_quieter_sound():
    cmd = convert_command(Assignment(Path("gen.mp4"), Path("intro_idle.mp4"), loop=True), 10.0, has_audio=False)

    graph = cmd[cmd.index("-filter_complex") + 1]
    assert f"xfade=transition=fade:duration={SEAM_SECONDS}:offset=8.000" in graph  # koniec przenika w początek
    assert "anullsrc=r=48000:cl=stereo" in cmd  # klip bez dźwięku dostaje ciszę długości pętli
    assert cmd[cmd.index("anullsrc=r=48000:cl=stereo") - 2] == f"{10.0 - SEAM_SECONDS:.3f}"


def test_waiting_loop_sound_crossfades_its_end_into_its_start_quieter():
    cmd = convert_command(Assignment(Path("gen.mp4"), Path("intro_idle.mp4"), loop=True), 10.0, has_audio=True)

    graph = cmd[cmd.index("-filter_complex") + 1]
    assert cmd.count("gen.mp4") == 2  # dźwięk początku czytany drugi raz
    assert f"acrossfade=d={SEAM_SECONDS},volume={LOOP_VOLUME}" in graph


def test_plan_lists_the_episode_clips_from_download():
    assert main([str(ROOT / "download" / "klipy.yaml"), "--plan"]) == 0


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="brak ffmpeg")
def test_imported_loop_is_one_seam_shorter(tmp_path, scenario_dict):
    source = tmp_path / "gen.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:d=5",
                    "-f", "lavfi", "-i", "sine=d=5", "-shortest", str(source)], check=True)  # fmt: skip
    mapping = write_map(tmp_path, scenario_dict, {"intro.mp4": "gen.mp4", "intro_idle.mp4": "gen.mp4"})

    assert main([str(mapping)]) == 0

    assert probe(tmp_path / "intro.mp4") == pytest.approx((5.0, True), abs=0.1)
    assert probe(tmp_path / "intro_idle.mp4") == pytest.approx((5.0 - SEAM_SECONDS, True), abs=0.1)

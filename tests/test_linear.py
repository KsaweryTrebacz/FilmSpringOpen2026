import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from bajka.engine import DEFAULT_FALLBACK
from bajka.linear import (
    PAUSE_SECONDS,
    Segment,
    build,
    default_path,
    main,
    probe,
    reading_seconds,
    segment_command,
    subtitles,
)
from bajka.placeholders import ffmpeg_command
from bajka.scenario import ScenarioError, parse_scenario

LINE = f"{DEFAULT_FALLBACK} Do lasu! Trzymaj się blisko!"


def test_linear_cut_follows_default_choices_and_the_hero_decides(scenario):
    segments = default_path(scenario)

    assert segments == [
        Segment(Path("film/intro.mp4")),
        Segment(Path("film/intro_idle.mp4"), PAUSE_SECONDS),
        Segment(Path("film/intro_idle.mp4"), reading_seconds(LINE), LINE),
        Segment(Path("film/las.mp4")),
    ]


def test_recorded_reaction_is_used_instead_of_a_subtitled_line(scenario_dict):
    scenario_dict["scenes"]["intro"]["fallback"] = "To ja wybiorę."
    scenario_dict["scenes"]["intro"]["choices"]["las"]["reaction"] = "reakcja_las.mp4"

    segments = default_path(parse_scenario(scenario_dict, base_dir=Path("film")))

    assert [(s.clip.name, s.line) for s in segments[2:]] == [
        ("intro_idle.mp4", "To ja wybiorę."), ("reakcja_las.mp4", ""), ("las.mp4", ""),
    ]


def test_defaults_going_in_circles_are_refused(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "intro"

    with pytest.raises(ScenarioError, match="w kółko"):
        default_path(parse_scenario(scenario_dict, base_dir=Path("film")))


def test_subtitles_are_timed_with_the_segments():
    segments = [Segment(Path("a.mp4")), Segment(Path("b.mp4"), 3.0), Segment(Path("b.mp4"), 4.5, "Do lasu!")]

    assert subtitles(segments, [61.25, 3.0, 4.5]) == "1\n00:01:04,250 --> 00:01:08,750\nDo lasu!\n"


def test_silent_loop_gets_a_silent_track_and_is_cut_to_length():
    cmd = segment_command(Segment(Path("idle.mp4"), 3.0), has_audio=False, target=Path("out.mp4"))

    assert cmd[cmd.index("-stream_loop") + 1] == "-1"
    assert any(part.startswith("anullsrc") for part in cmd) and "1:a:0" in cmd
    assert cmd[cmd.index("-t") + 1] == "3.000"


def test_plan_is_printed_without_ffmpeg(tmp_path, scenario_dict, capsys):
    path = tmp_path / "odcinek.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")

    assert main([str(path), "--plan"]) == 0
    assert "intro_idle.mp4" in capsys.readouterr().out


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="brak ffmpeg")
def test_linear_film_and_subtitles_are_built(tmp_path, scenario_dict):
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)
    for name, tone in [("intro.mp4", True), ("intro_idle.mp4", False), ("las.mp4", True)]:
        subprocess.run(ffmpeg_command(tmp_path / name, "indigo", 1.0, with_tone=tone), check=True)
    out = tmp_path / "liniowy.mp4"

    assert build(default_path(scenario), out) == out.with_suffix(".srt")
    seconds, has_audio = probe(out)
    assert has_audio and seconds == pytest.approx(1 + PAUSE_SECONDS + reading_seconds(LINE) + 1, abs=0.3)
    assert LINE in out.with_suffix(".srt").read_text(encoding="utf-8")


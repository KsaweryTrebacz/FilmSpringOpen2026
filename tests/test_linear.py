import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from bajka.engine import DEFAULT_FALLBACK
from bajka.linear import (
    FRAME,
    PAUSE_SECONDS,
    Segment,
    build,
    default_path,
    join_command,
    main,
    probe,
    reading_seconds,
    segment_command,
    subtitles,
    timeline,
)
from bajka.placeholders import ffmpeg_command, layer_command
from bajka.ports import Cut
from bajka.scenario import ScenarioError, parse_scenario

LINE = f"{DEFAULT_FALLBACK} Do lasu! Trzymaj się blisko!"


def test_linear_cut_follows_default_choices_and_the_hero_decides(scenario):
    segments = default_path(scenario)

    assert [(s.clip.name, s.seconds, s.line, s.line_at, s.cut.transition) for s in segments] == [
        ("intro.mp4", None, "", 0.0, "ciecie"),
        ("intro_idle.mp4", PAUSE_SECONDS + reading_seconds(LINE), LINE, PAUSE_SECONDS, "ciecie"),
        ("las.mp4", None, "", 0.0, "zaciemnienie"),  # reguły montażu: zakończenie historii
    ]


def test_pause_loop_enters_with_the_scenario_loop_transition(scenario_dict):
    scenario_dict["loop_transition"] = "przenikanie"

    segments = default_path(parse_scenario(scenario_dict, base_dir=Path("film")))

    assert (segments[1].clip.name, segments[1].cut.transition) == ("intro_idle.mp4", "przenikanie")


def test_recorded_reaction_is_used_instead_of_a_subtitled_line(scenario_dict):
    scenario_dict["scenes"]["intro"]["fallback"] = "To ja wybiorę."
    scenario_dict["scenes"]["intro"]["choices"]["las"]["reaction"] = "reakcja_las.mp4"

    segments = default_path(parse_scenario(scenario_dict, base_dir=Path("film")))

    assert [(s.clip.name, s.line, s.cut.transition) for s in segments[1:]] == [
        ("intro_idle.mp4", "To ja wybiorę.", "ciecie"), ("reakcja_las.mp4", "", "przenikanie"), ("las.mp4", "", "zaciemnienie"),
    ]


def test_scenes_without_questions_and_default_layers_are_in_the_linear_cut(scenario_dict):
    scenes = scenario_dict["scenes"]
    scenes["intro"]["choices"]["las"].update(layer="latarka.webm", slot="pomocnik")
    scenes["las"] = {"clip": "las.mp4", "next": "polana", "place": "Las", "layers": ["pomocnik"]}
    scenes["polana"] = {"clip": "polana.mp4", "place": "Las", "layers": ["pomocnik"], "transition": "rozjasnienie"}
    scenes["intro"]["place"] = "Nora"

    segments = default_path(parse_scenario(scenario_dict, base_dir=Path("film")))

    assert [(s.clip.name, tuple(p.name for p in s.layers), s.cut.transition) for s in segments[2:]] == [
        ("las.mp4", ("latarka.webm",), "przetarcie"), ("polana.mp4", ("latarka.webm",), "rozjasnienie"),
    ]


def test_defaults_going_in_circles_are_refused(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["next"] = "intro"

    with pytest.raises(ScenarioError, match="w kółko"):
        default_path(parse_scenario(scenario_dict, base_dir=Path("film")))


def test_timeline_overlaps_each_segment_with_the_end_of_the_previous_one():
    segments = [Segment(Path("a.mp4")), Segment(Path("b.mp4"), cut=Cut()), Segment(Path("c.mp4"), cut=Cut("przenikanie", 1.0))]

    starts, overlaps = timeline(segments, [10.0, 5.0, 4.0])

    assert overlaps == [0.0, FRAME, 1.0]  # cięcie to jedna klatka
    assert starts == [0.0, pytest.approx(10.0 - FRAME), pytest.approx(15.0 - FRAME - 1.0)]


def test_subtitles_are_timed_with_the_segments_and_their_transitions():
    segments = [Segment(Path("a.mp4")), Segment(Path("b.mp4"), 7.5, "Do lasu!", 3.0, cut=Cut("przenikanie", 1.0))]

    assert subtitles(segments, [61.25, 7.5]) == "1\n00:01:03,250 --> 00:01:07,750\nDo lasu!\n"


def test_segment_overlays_transparent_layers_and_pads_the_sound():
    segment = Segment(Path("las.mp4"), layers=(Path("latarka.webm"),))
    cmd = segment_command(segment, has_audio=False, target=Path("out.mp4"), clip_seconds=4.0)

    graph = cmd[cmd.index("-filter_complex") + 1]
    assert cmd[cmd.index("latarka.webm") - 2] == "libvpx-vp9"  # dekoder z kanałem alfa, przed -i warstwy
    assert "[b0][l0]overlay" in graph and "apad" in graph and "[2:v]format=yuva420p" in graph
    assert cmd[cmd.index("-t") + 1] == "4.000"


def test_silent_loop_is_cut_to_the_pause_length():
    cmd = segment_command(Segment(Path("idle.mp4"), 3.0), has_audio=False, target=Path("out.mp4"), clip_seconds=6.0)

    assert cmd[cmd.index("-stream_loop") + 1] == "-1"
    assert any(part.startswith("anullsrc") for part in cmd)
    assert cmd[cmd.index("-t") + 1] == "3.000"


def test_join_uses_the_montage_transitions():
    segments = [Segment(Path("a.mp4")), Segment(Path("b.mp4"), cut=Cut("przetarcie", 0.8)),
                Segment(Path("c.mp4"), cut=Cut("zaciemnienie", 1.2))]  # fmt: skip

    cmd = join_command([Path("0.mp4"), Path("1.mp4"), Path("2.mp4")], segments, [3.0, 3.0, 3.0], Path("out.mp4"))

    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade=transition=wiperight:duration=0.800:offset=2.200" in graph
    assert "xfade=transition=fadeblack:duration=1.200:offset=4.000" in graph
    assert "acrossfade=d=0.800" in graph


def test_plan_is_printed_without_ffmpeg(tmp_path, scenario_dict, capsys):
    path = tmp_path / "odcinek.yaml"
    path.write_text(yaml.safe_dump(scenario_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")

    assert main([str(path), "--plan"]) == 0
    printed = capsys.readouterr().out
    assert "intro_idle.mp4" in printed and "zaciemnienie 1,2 s" in printed


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="brak ffmpeg")
def test_linear_film_with_a_layer_and_transitions_is_built(tmp_path, scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["layer"] = "latarka.webm"
    scenario_dict["scenes"]["las"]["layers"] = ["intro"]
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)
    for name, tone in [("intro.mp4", True), ("intro_idle.mp4", False), ("las.mp4", True)]:
        subprocess.run(ffmpeg_command(tmp_path / name, "indigo", 1.0, with_tone=tone), check=True)
    subprocess.run(layer_command(tmp_path / "latarka.webm", "gold", 1.0), check=True)
    out = tmp_path / "liniowy.mp4"

    assert build(default_path(scenario), out) == out.with_suffix(".srt")
    seconds, has_audio = probe(out)
    # cięcie do pętli (jedna klatka), zaciemnienie na koniec skrócone do długości 1-sekundowego klipu
    expected = 1 + PAUSE_SECONDS + reading_seconds(LINE) + 1 - FRAME - (1 - FRAME)
    assert has_audio and seconds == pytest.approx(expected, abs=0.1)
    assert LINE in out.with_suffix(".srt").read_text(encoding="utf-8")

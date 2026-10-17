from pathlib import Path

from bajka.placeholders import ffmpeg_command, planned_clips
from bajka.scenario import parse_scenario


def test_scene_clip_has_tone_and_idle_loop_is_silent(scenario):
    clips = planned_clips(scenario)

    assert clips[0] == (Path("film/intro.mp4"), "darkgreen", True)
    assert clips[1] == (Path("film/intro_idle.mp4"), "darkgreen", False)
    assert [path.name for path, _, _ in clips] == ["intro.mp4", "intro_idle.mp4", "las.mp4", "jaskinia.mp4"]


def test_ffmpeg_command_for_silent_loop_has_no_audio():
    cmd = ffmpeg_command(Path("out/idle.mp4"), "indigo", 4.0, with_tone=False)

    assert "-an" in cmd
    assert not any(part.startswith("sine=") for part in cmd)
    assert cmd[-1] == str(Path("out/idle.mp4"))


def test_ffmpeg_command_for_clip_adds_tone():
    cmd = ffmpeg_command(Path("out/intro.mp4"), "darkgreen", 2.5, with_tone=True)

    assert "color=c=darkgreen:s=1280x720:r=25:d=2.5" in cmd
    assert "sine=frequency=440:duration=2.5" in cmd


def test_scene_versions_are_planned_with_tone_in_the_scene_color(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}

    clips = planned_clips(parse_scenario(scenario_dict, base_dir=Path("film")))

    las_color = next(color for path, color, _ in clips if path.name == "las.mp4")
    assert (Path("film/las_spokojna.mp4"), las_color, True) in clips


def test_ffmpeg_command_writes_the_label_with_the_given_font():
    font = Path("C:/Windows/Fonts/arial.ttf")
    cmd = ffmpeg_command(Path("out/las_spokojna.mp4"), "indigo", 2.0, with_tone=True, label="las_spokojna", font=font)

    video_filter = cmd[cmd.index("-vf") + 1]
    assert "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf'" in video_filter
    assert "text='las_spokojna'" in video_filter


def test_ffmpeg_command_without_font_has_no_label():
    cmd = ffmpeg_command(Path("out/las.mp4"), "indigo", 2.0, with_tone=True, label="las", font=None)

    assert "-vf" not in cmd


def test_reaction_clips_are_planned_with_tone(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"]["reaction"] = "reakcja_las.mp4"

    clips = planned_clips(parse_scenario(scenario_dict, base_dir=Path("film")))

    assert (Path("film/reakcja_las.mp4"), "darkgreen", True) in clips


def test_mp4_starts_fast_in_a_browser_and_webm_uses_open_codecs():
    mp4 = ffmpeg_command(Path("out/intro.mp4"), "indigo", 2.0, with_tone=True)
    webm = ffmpeg_command(Path("out/intro.webm"), "indigo", 2.0, with_tone=True)

    assert mp4[mp4.index("-movflags") + 1] == "+faststart"
    assert "libvpx-vp9" in webm and "libopus" in webm and "-movflags" not in webm

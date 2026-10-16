from pathlib import Path

from bajka.placeholders import ffmpeg_command, planned_clips


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

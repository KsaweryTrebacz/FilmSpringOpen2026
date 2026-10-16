import shutil
import subprocess
from pathlib import Path

import pytest

from bajka.ports import Animator
from bajka.motion import FfmpegAnimator, MotionError, MotionSettings, ffmpeg_command, main

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="brak ffmpeg w PATH")


class FakeRun:
    """Udaje subprocess.run: zapamiętuje polecenie albo rzuca podanym wyjątkiem."""

    def __init__(self, error=None):
        self.commands = []
        self._error = error

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        if self._error is not None:
            raise self._error


def make_png(path):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=skyblue:s=1536x1024", "-frames:v", "1",
         str(path)],
        check=True,
    )
    return path


def test_zoom_in_crops_to_16_9_and_zooms_slowly_for_whole_clip():
    cmd = ffmpeg_command(Path("ul.png"), Path("ul.mp4"), seconds=6, move="zoom_in")

    video_filter = cmd[cmd.index("-vf") + 1]
    assert cmd[cmd.index("-i") + 1] == "ul.png"
    assert "crop=iw:min(ih\\,iw*9/16)" in video_filter
    assert "zoompan=z='min(zoom+0.001000,1.15)'" in video_filter
    assert "s=1280x720" in video_filter
    assert cmd[cmd.index("-frames:v") + 1] == "150"
    assert "-an" in cmd
    assert cmd[-1] == "ul.mp4"


def test_pan_moves_across_the_picture():
    cmd = ffmpeg_command(Path("ul.png"), Path("ul.mp4"), seconds=6, move="pan")

    video_filter = cmd[cmd.index("-vf") + 1]
    assert "z='1.15'" in video_filter
    assert "x='(iw-iw/zoom)*on/150'" in video_filter


def test_unknown_move_is_rejected():
    with pytest.raises(ValueError, match="obrot"):
        ffmpeg_command(Path("ul.png"), Path("ul.mp4"), seconds=6, move="obrot")


def test_animator_fulfils_contract_and_returns_clip_next_to_session_files(tmp_path):
    run = FakeRun()
    animator = FfmpegAnimator(tmp_path, seconds=6, run=run)

    clip = animator.animate(tmp_path / "obraz_1.png")

    assert isinstance(animator, Animator)
    assert clip == tmp_path / "obraz_1.mp4"
    assert run.commands[0][-1] == str(clip)


def test_missing_ffmpeg_raises_motion_error(tmp_path):
    animator = FfmpegAnimator(tmp_path, run=FakeRun(FileNotFoundError("ffmpeg")))

    with pytest.raises(MotionError, match="ffmpeg"):
        animator.animate(tmp_path / "obraz.png")


def test_ffmpeg_failure_raises_motion_error_with_its_message(tmp_path):
    error = subprocess.CalledProcessError(1, ["ffmpeg"], stderr="Invalid data found\n")
    animator = FfmpegAnimator(tmp_path, run=FakeRun(error))

    with pytest.raises(MotionError, match="Invalid data found"):
        animator.animate(tmp_path / "obraz.png")


def test_settings_default_and_override():
    assert MotionSettings.from_env({}).seconds == 6.0
    assert MotionSettings.from_env({"BAJKA_MOTION_SECONDS": "4,5"}).seconds == 4.5


@needs_ffmpeg
def test_real_ffmpeg_makes_clip_from_illustration(tmp_path):
    image = make_png(tmp_path / "ul.png")

    clip = FfmpegAnimator(tmp_path / "klipy", seconds=1).animate(image)

    assert clip.is_file() and clip.stat().st_size > 0


@needs_ffmpeg
def test_demo_makes_clip_and_prints_time(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    image = make_png(tmp_path / "ul.png")

    assert main([str(image), "--seconds", "1", "--move", "pan"]) == 0

    assert "ul.mp4" in capsys.readouterr().out

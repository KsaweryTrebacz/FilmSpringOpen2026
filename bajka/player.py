"""Odtwarzacz VLC osadzony w jednym oknie tkinter, które trwa przez cały odcinek (`--player vlc`).

Moduł importuje `vlc`, który wymaga zainstalowanego VLC 64-bit, dlatego testy go nie importują.
Podgląd przejścia klip → pętla: python -m bajka.player KLIP [PĘTLA]   (Esc zamyka)
"""

from __future__ import annotations

import logging
import sys
import threading
import tkinter as tk
from pathlib import Path

import vlc

log = logging.getLogger(__name__)

LOOP_FOREVER = "input-repeat=65535"


class VlcPlayer:
    def __init__(self, root: tk.Tk, fullscreen: bool = True) -> None:
        root.title("Bajka")
        root.configure(background="black")
        if fullscreen:
            root.attributes("-fullscreen", True)
            root.configure(cursor="none")
        else:
            root.geometry("1280x720")
        surface = tk.Frame(root, background="black")
        surface.pack(fill=tk.BOTH, expand=True)
        root.update()  # okno musi istnieć, zanim przekażemy jego uchwyt do VLC

        self._instance = vlc.Instance("--quiet", "--no-video-title-show")
        self._player = self._instance.media_player_new()
        self._player.video_set_mouse_input(False)  # klawisze i mysz zostają w tkinter (Esc)
        self._player.video_set_key_input(False)
        _attach_to_window(self._player, surface.winfo_id())

        self._finished = threading.Event()
        events = self._player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_finished)
        events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_finished)

    def play(self, clip: Path) -> None:
        log.info("Wideo: %s", clip.name)
        self._finished.clear()
        self._start(self._instance.media_new(str(clip)))
        self._finished.wait()

    def loop(self, clip: Path) -> None:
        log.info("Pętla: %s", clip.name)
        media = self._instance.media_new(str(clip))
        media.add_option(LOOP_FOREVER)
        self._start(media)

    def stop(self) -> None:
        self._player.stop()

    def _start(self, media: vlc.Media) -> None:
        self._player.set_media(media)
        self._player.play()

    def _on_finished(self, _event: vlc.Event) -> None:
        # Wywoływane z wątku VLC: tu nie wolno wołać API libvlc, tylko dać sygnał.
        self._finished.set()


def _attach_to_window(player: vlc.MediaPlayer, handle: int) -> None:
    if sys.platform.startswith("win"):
        player.set_hwnd(handle)
    elif sys.platform.startswith("linux"):
        player.set_xwindow(handle)
    else:
        log.warning("Brak osadzania na %s: VLC otworzy własne okno", sys.platform)


def _preview(argv: list[str]) -> None:
    root = tk.Tk()
    player = VlcPlayer(root, fullscreen=False)

    def show() -> None:
        player.play(Path(argv[0]))
        if len(argv) > 1:
            player.loop(Path(argv[1]))

    def close(_event: object = None) -> None:
        player.stop()
        root.destroy()

    root.bind("<Escape>", close)
    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=show, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _preview(sys.argv[1:])

"""Złożenie aplikacji: okno tkinter w wątku głównym, silnik bajki w wątku roboczym."""

from __future__ import annotations

import argparse
import logging
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from bajka.config import ConfigError, get_int, load_env
from bajka.engine import StoryEngine
from bajka.intent import AzureIntentResolver, LlmSettings
from bajka.ports import Listener, Voice
from bajka.scenario import ScenarioError, load_scenario, missing_media

if TYPE_CHECKING:
    import tkinter as tk

    from bajka.player import VlcPlayer

log = logging.getLogger("bajka")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m bajka", description="Interaktywna Bajka Głosowa Zero-UI")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument(
        "--text", action="store_true", help="tryb próbny: odpowiedzi z klawiatury, kwestie bohatera w konsoli"
    )
    parser.add_argument("--windowed", action="store_true", help="okno zamiast pełnego ekranu")
    return parser.parse_args(argv)


def build_speech(env: Mapping[str, str], text_mode: bool) -> tuple[Listener, Voice]:
    if text_mode:
        from bajka.console import ConsoleListener, ConsoleVoice

        return ConsoleListener(), ConsoleVoice()
    from bajka.stt import AzureListener, SttSettings
    from bajka.tts import AzureVoice, TtsSettings

    return AzureListener.from_settings(SttSettings.from_env(env)), AzureVoice.from_settings(TtsSettings.from_env(env))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    args = parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        env = load_env()
        resolver = AzureIntentResolver.from_settings(LlmSettings.from_env(env), scenario.hero)
        listener, voice = build_speech(env, args.text)
        max_reprompts = get_int(env, "BAJKA_MAX_REPROMPTS", 2)
    except (ScenarioError, ConfigError, OSError) as exc:
        log.error("%s", exc)
        return 2
    missing = missing_media(scenario)
    if missing:
        log.error("Brak plików wideo: %s", ", ".join(map(str, missing)))
        return 2

    import tkinter as tk

    from bajka.player import VlcPlayer

    root = tk.Tk()
    player = VlcPlayer(root, fullscreen=not args.windowed)
    engine = StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=max_reprompts)
    run_window(root, player, engine)
    return 0


def run_window(root: tk.Tk, player: VlcPlayer, engine: StoryEngine) -> None:
    finished = threading.Event()

    def story() -> None:
        try:
            visited = engine.run()
            log.info("Koniec bajki, ścieżka: %s", " -> ".join(visited))
        except Exception:
            log.exception("Bajka przerwana błędem")
        finally:
            finished.set()

    def close(_event: object = None) -> None:
        player.stop()
        root.destroy()

    def poll() -> None:
        # tkinter nie jest wątkowo bezpieczny, więc koniec bajki sprawdzamy z wątku głównego.
        if finished.is_set():
            close()
        else:
            root.after(200, poll)

    root.bind("<Escape>", close)
    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=story, daemon=True).start()
    root.after(200, poll)
    root.mainloop()

"""Złożenie aplikacji: okno tkinter w wątku głównym, silnik bajki w wątku roboczym.

Domyślnie wszystko działa lokalnie na komputerze z Windows (`--backend local`): Whisper i Phi przez
Foundry Local (NPU/GPU/CPU) oraz głos z syntezatora Windows. `--backend azure` przełącza na usługi Azure.
"""

from __future__ import annotations

import argparse
import logging
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from bajka.config import ConfigError, get_int, load_env
from bajka.engine import StoryEngine
from bajka.foundry import FoundryError
from bajka.intent import AzureIntentResolver, LlmSettings
from bajka.keywords import FallbackResolver, KeywordIntentResolver
from bajka.local_tts import VoiceNotFoundError
from bajka.ports import IntentResolver, Listener, ShoutMeter, Voice
from bajka.safety import SafeReplyResolver
from bajka.scenario import ScenarioError, load_scenario, missing_media

if TYPE_CHECKING:
    import tkinter as tk

    from bajka.player import VlcPlayer

log = logging.getLogger("bajka")

BACKENDS = ("local", "azure")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m bajka", description="Interaktywna Bajka Głosowa Zero-UI")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument(
        "--text", action="store_true", help="tryb próbny: odpowiedzi z klawiatury, kwestie bohatera w konsoli"
    )
    parser.add_argument("--windowed", action="store_true", help="okno zamiast pełnego ekranu")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        help="local: Foundry Local + głos Windows, bez chmury (domyślnie, albo BAJKA_BACKEND z .env); azure: usługi Azure",
    )
    parser.add_argument(
        "--no-llm", action="store_true", help="bez modelu językowego: wybór po słowach kluczowych ze scenariusza"
    )
    return parser.parse_args(argv)


def choose_backend(args: argparse.Namespace, env: Mapping[str, str]) -> str:
    backend = args.backend or env.get("BAJKA_BACKEND") or "local"
    if backend not in BACKENDS:
        raise ConfigError(f"BAJKA_BACKEND musi być jednym z: {', '.join(BACKENDS)}, jest: {backend!r}")
    return backend


def build_resolver(env: Mapping[str, str], backend: str, use_llm: bool, hero: str) -> IntentResolver:
    """Model językowy z filtrem kwestii i zapasem w postaci słów kluczowych albo same słowa kluczowe (`--no-llm`)."""
    keywords = KeywordIntentResolver()
    if not use_llm:
        return keywords
    if backend == "azure":
        llm: IntentResolver = AzureIntentResolver.from_settings(LlmSettings.from_env(env), hero)
    else:
        from bajka.local_intent import LocalIntentResolver, LocalLlmSettings

        llm = LocalIntentResolver.from_settings(LocalLlmSettings.from_env(env), hero)
    return FallbackResolver(SafeReplyResolver(llm), keywords)


def build_speech(env: Mapping[str, str], text_mode: bool, backend: str = "azure") -> tuple[Listener, Voice]:
    if text_mode:
        from bajka.console import ConsoleListener, ConsoleVoice

        return ConsoleListener(), ConsoleVoice()
    if backend == "local":
        from bajka.local_stt import LocalListener, LocalSttSettings
        from bajka.local_tts import WindowsTtsSettings, WindowsVoice

        voice = WindowsVoice.from_settings(WindowsTtsSettings.from_env(env))  # szybko, więc przed pobieraniem modelu
        return LocalListener.from_settings(LocalSttSettings.from_env(env)), voice
    from bajka.stt import AzureListener, SttSettings
    from bajka.tts import AzureVoice, TtsSettings

    return AzureListener.from_settings(SttSettings.from_env(env)), AzureVoice.from_settings(TtsSettings.from_env(env))


def build_meter(env: Mapping[str, str], text_mode: bool) -> ShoutMeter:
    """Krzykomierz do scen `vote`: mikrofon na sali albo głośność wpisywana w konsoli przy próbach."""
    if text_mode:
        from bajka.console import ConsoleMeter

        return ConsoleMeter()
    from bajka.vote import MicrophoneMeter, VoteSettings

    return MicrophoneMeter(VoteSettings.from_env(env))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    args = parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
    except (ScenarioError, OSError) as exc:
        log.error("%s", exc)
        return 2
    missing = missing_media(scenario)  # przed ładowaniem modeli, które za pierwszym razem pobierają się minutami
    if missing:
        log.error("Brak plików wideo: %s", ", ".join(map(str, missing)))
        return 2
    try:
        env = load_env()
        backend = choose_backend(args, env)
        max_reprompts = get_int(env, "BAJKA_MAX_REPROMPTS", 2)
        log.info("Tryb: %s%s", backend, ", bez modelu językowego" if args.no_llm else "")
        meter = build_meter(env, args.text)
        listener, voice = build_speech(env, args.text, backend)
        resolver = build_resolver(env, backend, not args.no_llm, scenario.hero)
    except (ConfigError, FoundryError, VoiceNotFoundError, OSError) as exc:
        log.error("%s", exc)
        return 2
    except Exception:
        log.exception("Nie udało się uruchomić rozpoznawania mowy, głosu albo modelu językowego")
        return 1

    import tkinter as tk

    from bajka.player import VlcPlayer

    root = tk.Tk()
    player = VlcPlayer(root, fullscreen=not args.windowed)
    engine = StoryEngine(scenario, player, listener, voice, resolver, max_reprompts=max_reprompts, meter=meter)
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

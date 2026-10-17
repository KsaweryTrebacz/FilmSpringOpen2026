"""Złożenie aplikacji: odcinek w przeglądarce (domyślnie), w oknie VLC albo w konsoli.

Domyślnie wszystko działa lokalnie na komputerze z Windows (`--backend local`): Whisper i Phi przez
Foundry Local (NPU/GPU/CPU). `--backend azure` przełącza rozpoznawanie mowy, model językowy i głos na usługi Azure.

`--player web`: odcinek w przeglądarce jak w serwisie streamingowym: okna wyboru na ekranie, wybór pilotem,
dotykiem albo głosem (mikrofon w przeglądarce), napisy i głos postaci z przeglądarki.
`--player vlc`: pełny ekran VLC, odpowiedzi tylko głosem z mikrofonu komputera, głos postaci z syntezatora Windows.
`--text`: próba w konsoli, bez wideo, mikrofonu i modeli mowy.

Montaż: o przejściach między klipami decyduje model (ten sam co do rozumienia odpowiedzi), a bez modelu
(`--no-llm` albo `BAJKA_MONTAGE=reguly`) — reguły z `bajka/montage.py`.
"""

from __future__ import annotations

import argparse
import logging
import threading
import webbrowser
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bajka.config import ConfigError, get_float, get_int, load_env
from bajka.engine import DEFAULT_CHOICE_SECONDS, StoryEngine
from bajka.foundry import FoundryError
from bajka.intent import AzureIntentResolver, LlmSettings
from bajka.keywords import (
    FallbackResolver,
    KeywordIntentResolver,
    KeywordsFirstResolver,
)
from bajka.local_tts import VoiceNotFoundError
from bajka.montage import ModelEditor, Montage, MontageSettings
from bajka.ports import IntentResolver, Listener, Player, Viewer, Voice
from bajka.safety import SafeReplyResolver
from bajka.scenario import Scenario, ScenarioError, load_scenario, missing_media

if TYPE_CHECKING:
    import tkinter as tk

    import numpy as np

    from bajka.mobile import MobileServer
    from bajka.panel import PanelServer, PanelState
    from bajka.player import VlcPlayer
    from bajka.pulse import PulseSettings, SimulatedPulse
    from bajka.web_player import WebEpisode, WebPlayerServer

log = logging.getLogger("bajka")

BACKENDS = ("local", "azure")
PLAYERS = ("web", "vlc")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m bajka", description="Bajka interaktywna z oknami wyboru i głosem")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem odcinka")
    parser.add_argument(
        "--player",
        choices=PLAYERS,
        help="web: odcinek w przeglądarce z oknami wyboru (domyślnie, albo BAJKA_PLAYER z .env); "
        "vlc: pełny ekran, odpowiedzi tylko głosem",
    )
    parser.add_argument(
        "--text", action="store_true", help="tryb próbny w konsoli: bez wideo, mikrofonu i głosu (cyfra = przycisk)"
    )
    parser.add_argument(
        "--no-mic", action="store_true", help="bez rozpoznawania mowy: wybór tylko pilotem, dotykiem albo myszą (web)"
    )
    parser.add_argument("--no-browser", action="store_true", help="nie otwieraj przeglądarki samodzielnie (web)")
    parser.add_argument("--windowed", action="store_true", help="okno zamiast pełnego ekranu (vlc)")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        help="local: Foundry Local, bez chmury (domyślnie, albo BAJKA_BACKEND z .env); azure: usługi Azure",
    )
    parser.add_argument(
        "--no-llm", action="store_true", help="bez modelu językowego: wybór po słowach kluczowych ze scenariusza"
    )
    parser.add_argument(
        "--mobile",
        action="store_true",
        help="drugi ekran: telefony domowników jako pilot z mikrofonem (np. przy telewizorze bez mikrofonu); "
        "także BAJKA_MOBILE=1",
    )
    parser.add_argument(
        "--panel",
        action="store_true",
        help="panel podglądu w przeglądarce i symulator tętna widza (wersje scen według tętna); także BAJKA_PANEL=1",
    )
    return parser.parse_args(argv)


def choose_backend(args: argparse.Namespace, env: Mapping[str, str]) -> str:
    backend = args.backend or env.get("BAJKA_BACKEND") or "local"
    if backend not in BACKENDS:
        raise ConfigError(f"BAJKA_BACKEND musi być jednym z: {', '.join(BACKENDS)}, jest: {backend!r}")
    return backend


def choose_player(args: argparse.Namespace, env: Mapping[str, str]) -> str:
    player = args.player or env.get("BAJKA_PLAYER") or "web"
    if player not in PLAYERS:
        raise ConfigError(f"BAJKA_PLAYER musi być jednym z: {', '.join(PLAYERS)}, jest: {player!r}")
    return player


def choice_seconds(env: Mapping[str, str]) -> float:
    seconds = get_float(env, "BAJKA_CHOICE_SECONDS", DEFAULT_CHOICE_SECONDS)
    if not 3 <= seconds <= 60:
        raise ConfigError(f"BAJKA_CHOICE_SECONDS to czas okna wyboru od 3 do 60 sekund, jest: {seconds:g}")
    return seconds


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


def build_montage(env: Mapping[str, str], backend: str, use_llm: bool) -> Montage:
    """Montażysta: model decyduje o przejściach w tle, a reguły odpowiadają, gdy modelu nie ma albo nie zdąży."""
    settings = MontageSettings.from_env(env)
    if not use_llm or not settings.use_model:
        return Montage(settings=settings)
    if backend == "azure":
        return Montage(ModelEditor.azure(LlmSettings.from_env(env)), settings)
    from bajka.local_intent import LocalLlmSettings

    return Montage(ModelEditor.local(LocalLlmSettings.from_env(env)), settings)


def build_transcriber(env: Mapping[str, str], backend: str) -> Callable[[np.ndarray], str]:
    """Rozpoznawanie krótkich nagrań (16 kHz mono) z przeglądarki i telefonów: Whisper lokalnie albo Azure."""
    if backend == "azure":
        from bajka.stt import AzureFileTranscriber, SttSettings

        return AzureFileTranscriber(SttSettings.from_env(env))
    from bajka.local_stt import FoundryTranscriber, LocalSttSettings

    return FoundryTranscriber.from_settings(LocalSttSettings.from_env(env))


def build_speech(env: Mapping[str, str], backend: str = "azure") -> tuple[Listener, Voice]:
    """Mikrofon i głośnik komputera dla odtwarzacza VLC."""
    if backend == "local":
        from bajka.local_stt import LocalListener, LocalSttSettings
        from bajka.local_tts import WindowsTtsSettings, WindowsVoice

        voice = WindowsVoice.from_settings(WindowsTtsSettings.from_env(env))  # szybko, więc przed pobieraniem modelu
        return LocalListener.from_settings(LocalSttSettings.from_env(env)), voice
    from bajka.stt import AzureListener, SttSettings
    from bajka.tts import AzureVoice, TtsSettings

    return AzureListener.from_settings(SttSettings.from_env(env)), AzureVoice.from_settings(TtsSettings.from_env(env))


def env_flag(env: Mapping[str, str], name: str, default: str = "0") -> bool:
    return (env.get(name) or default).strip().lower() in ("1", "tak", "true")


def mobile_enabled(args: argparse.Namespace, env: Mapping[str, str]) -> bool:
    return args.mobile or env_flag(env, "BAJKA_MOBILE")


def panel_enabled(args: argparse.Namespace, env: Mapping[str, str]) -> bool:
    return args.panel or env_flag(env, "BAJKA_PANEL")


@dataclass(frozen=True)
class Panel:
    """Panel podglądu z symulatorem tętna widza: silnik dostaje tętno i opowiada panelowi, co robi."""

    server: PanelServer
    state: PanelState
    pulse: SimulatedPulse
    pulse_settings: PulseSettings


def build_panel(env: Mapping[str, str], scenario: Scenario) -> Panel:
    from bajka.panel import PanelServer, PanelSettings, PanelState, scenario_graph
    from bajka.pulse import PulseSettings, SimulatedPulse

    pulse_settings = PulseSettings.from_env(env)
    pulse = SimulatedPulse(pulse_settings)
    state = PanelState(scenario, pulse_settings)
    server = PanelServer(state, scenario_graph(scenario), pulse, PanelSettings.from_env(env))
    return Panel(server=server, state=state, pulse=pulse, pulse_settings=pulse_settings)


def build_mobile(env: Mapping[str, str], backend: str, resolver: IntentResolver) -> MobileServer:
    """Serwer drugiego ekranu: nagrania z telefonów rozpoznaje ten sam backend co resztę bajki."""
    from bajka.mobile import MobileAudience, MobileServer, MobileSettings

    settings = MobileSettings.from_env(env)
    # Wiele krótkich odpowiedzi naraz: słowa kluczowe od razu, model tylko dla niejasnych.
    resolver = KeywordsFirstResolver(KeywordIntentResolver(), resolver)
    return MobileServer(MobileAudience(build_transcriber(env, backend), resolver, settings), settings)


@dataclass(frozen=True)
class Web:
    """Odtwarzacz w przeglądarce: ten sam obiekt odtwarza klipy, mówi kwestie i pokazuje okna wyboru."""

    episode: WebEpisode
    server: WebPlayerServer


def build_web(env: Mapping[str, str], scenario: Scenario, backend: str, use_mic: bool) -> Web:
    from bajka.web_player import WebEpisode, WebPlayerServer, WebPlayerSettings

    settings = WebPlayerSettings.from_env(env)
    episode = WebEpisode(scenario, None, settings, browser_voice=use_mic)
    if use_mic:
        def load_transcriber() -> None:
            try:
                t = build_transcriber(env, backend)
                episode.set_transcribe(t)
                log.info("Lokalny model rozpoznawania mowy (Whisper) gotowy w tle")
            except Exception as exc:
                log.warning("Rozpoznawanie mowy w backendzie niedostępne (%s), działa rozpoznawanie w przeglądarce", exc)

        threading.Thread(target=load_transcriber, daemon=True).start()
    return Web(episode=episode, server=WebPlayerServer(episode, settings))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    args = parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
    except (ScenarioError, OSError) as exc:
        log.error("%s", exc)
        return 2
    missing = missing_media(scenario)  # przed ładowaniem modeli, które za pierwszym razem pobierają się minutami
    if missing and not args.text:
        log.error("Brak plików wideo: %s (zastępcze: python -m bajka.placeholders)", ", ".join(map(str, missing)))
        return 2
    web: Web | None = None
    speech: tuple[Listener, Voice] | None = None
    try:
        env = load_env()
        backend = choose_backend(args, env)
        player = "konsola" if args.text else choose_player(args, env)
        max_reprompts = get_int(env, "BAJKA_MAX_REPROMPTS", 2)
        seconds = choice_seconds(env)
        log.info("Odtwarzacz: %s, tryb: %s%s", player, backend, ", bez modelu językowego" if args.no_llm else "")
        panel = build_panel(env, scenario) if panel_enabled(args, env) else None  # tylko ustawienia, bez sieci
        if player == "web":
            web = build_web(env, scenario, backend, use_mic=not args.no_mic)
        elif player == "vlc":
            speech = build_speech(env, backend)
        resolver = build_resolver(env, backend, not args.no_llm, scenario.hero)
        montage = build_montage(env, backend, not args.no_llm)
        mobile = build_mobile(env, backend, resolver) if mobile_enabled(args, env) else None
    except (ConfigError, FoundryError, VoiceNotFoundError, OSError) as exc:
        log.error("%s", exc)
        return 2
    except Exception:
        log.exception("Nie udało się uruchomić rozpoznawania mowy, głosu albo modelu językowego")
        return 1

    def make_engine(player: Player, viewer: Viewer | Listener, voice: Voice) -> StoryEngine:
        return StoryEngine(
            scenario,
            player,
            viewer,
            voice,
            resolver,
            max_reprompts=max_reprompts,
            audience=mobile.audience if mobile else None,
            pulse=panel.pulse if panel else None,
            pulse_settings=panel.pulse_settings if panel else None,
            observer=panel.state if panel else None,
            choice_seconds=seconds,
            montage=montage,
        )

    servers: list[MobileServer | PanelServer | WebPlayerServer] = []
    try:
        if mobile is not None:
            url = mobile.start()
            servers.append(mobile)
            log.info("Drugi ekran: otwórzcie %s w telefonach (kod QR: %sqr)", url, url)
        if panel is not None:
            panel.server.start()  # adres panelu wypisuje sam PanelServer
            servers.append(panel.server)
            if not scenario.mood:
                log.info("Scenariusz nie ma pola 'mood': panel pokazuje drzewo i wybory, a sceny grają zwykłe wersje")
        if web is not None:
            url = web.server.start()
            servers.append(web.server)
            if not args.no_browser and env_flag(env, "BAJKA_WEB_OPEN", "1"):
                webbrowser.open(url)
    except OSError as exc:
        log.error("Nie udało się uruchomić serwera (port zajęty?): %s", exc)
        for server in servers:
            server.stop()
        montage.close()
        return 2
    try:
        if web is not None:
            run_episodes(web.episode, lambda: make_engine(web.episode, web.episode, web.episode))
        elif speech is not None:
            import tkinter as tk

            from bajka.player import VlcPlayer

            root = tk.Tk()
            vlc = VlcPlayer(root, fullscreen=not args.windowed)
            run_window(root, vlc, make_engine(vlc, *speech))
        else:
            from bajka.console import ConsolePlayer, ConsoleViewer, ConsoleVoice

            visited = make_engine(ConsolePlayer(), ConsoleViewer(), ConsoleVoice()).run()
            log.info("Koniec odcinka, ścieżka: %s", " -> ".join(visited))
    except KeyboardInterrupt:
        log.info("Odcinek przerwany (Ctrl+C)")
    finally:
        for server in servers:
            server.stop()
        montage.close()
    return 0


def run_episodes(episode: WebEpisode, make_engine: Callable[[], StoryEngine]) -> None:
    """Odcinek w przeglądarce; z ekranu końcowego widz może obejrzeć go jeszcze raz i wybrać inaczej."""
    while True:
        engine = make_engine()
        episode.on_stop = engine.stop
        try:
            visited = engine.run()
            log.info("Koniec odcinka, ścieżka: %s", " -> ".join(visited))
        except Exception:
            log.exception("Odcinek przerwany błędem")
            visited = []
        if not episode.finish(visited, getattr(engine, "decisions", None)):
            return


def run_window(root: tk.Tk, player: VlcPlayer, engine: StoryEngine) -> None:
    finished = threading.Event()

    def story() -> None:
        try:
            visited = engine.run()
            log.info("Koniec odcinka, ścieżka: %s", " -> ".join(visited))
        except Exception:
            log.exception("Odcinek przerwany błędem")
        finally:
            finished.set()

    def close(_event: object = None) -> None:
        engine.stop()  # zanim zgasimy ekran, wątek odcinka ma przestać mówić i przechodzić do kolejnych scen
        player.stop()
        root.destroy()

    def poll() -> None:
        # tkinter nie jest wątkowo bezpieczny, więc koniec odcinka sprawdzamy z wątku głównego.
        if finished.is_set():
            close()
        else:
            root.after(200, poll)

    root.bind("<Escape>", close)
    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=story, daemon=True).start()
    root.after(200, poll)
    root.mainloop()

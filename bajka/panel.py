"""Panel dla jury: strona w przeglądarce, która pokazuje drzewo scen, głosy, tętno sali i decyzje filmu.

Silnik wysyła zdarzenia (`bajka.ports.ShowObserver`), `PanelState` trzyma z nich stan w pamięci, a `PanelServer`
serwuje go stronie `bajka/panel_app/index.html`. Z panelu steruje się też symulatorem tętna (`bajka/pulse.py`).
Podgląd bez filmu: python -m bajka.panel SCENARIUSZ (symulator tętna, przebieg demo)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bajka.config import ConfigError, get_int, load_env
from bajka.ports import AudiencePulse, Pulse
from bajka.pulse import PulseSettings, SimulatedPulse, hall_state
from bajka.scenario import Scenario, ScenarioError, load_scenario

log = logging.getLogger(__name__)

APP_DIR = Path(__file__).parent / "panel_app"
HISTORY_SAMPLES = 120  # ostatnie 2 minuty tętna przy próbce co sekundę
LOG_ENTRIES = 20
MAX_COMMAND_BYTES = 1024

HOW = {
    "wiekszosc": "większość głosów z telefonów",
    "okrzyk": "najgłośniejszy okrzyk",
    "odpowiedz": "odpowiedź z mikrofonu",
    "domyslna": "brak decyzji, postać wybrała sama",
}
VERSION = {"spokojna": "spokojnej", "zywa": "żywej", "zwykla": "zwykłej"}


@dataclass(frozen=True)
class PanelSettings:
    host: str = "127.0.0.1"  # 0.0.0.0 udostępnia panel tabletowi jury w tej samej sieci
    port: int = 8090

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> PanelSettings:
        return cls(
            host=env.get("BAJKA_PANEL_HOST") or cls.host,
            port=get_int(env, "BAJKA_PANEL_PORT", cls.port),
        )


def scenario_graph(scenario: Scenario) -> dict[str, Any]:
    """Drzewo scen dla strony panelu: sceny z odległością od startu i krawędzie z nazwami opcji."""
    depth = {scenario.start: 0}
    todo = [scenario.start]
    while todo:  # przeszukiwanie wszerz: najkrótsza droga od sceny startowej
        scene = scenario.scene(todo.pop(0))
        for choice in scene.choices.values():
            if choice.next not in depth:
                depth[choice.next] = depth[scene.id] + 1
                todo.append(choice.next)
    unreachable = max(depth.values()) + 1
    return {
        "start": scenario.start,
        "mood": scenario.mood,
        "scenes": [
            {
                "id": scene.id,
                "depth": depth.get(scene.id, unreachable),
                "question": scene.question,
                "ending": scene.is_ending,
                "variants": list(scene.variants),
            }
            for scene in scenario.scenes.values()
        ],
        "edges": [
            {"from": scene.id, "to": choice.next, "choice": choice.id, "label": choice.display_label}
            for scene in scenario.scenes.values()
            for choice in scene.choices.values()
        ],
    }


class PanelState:
    """Stan seansu dla panelu, budowany ze zdarzeń silnika i próbek tętna; bezpieczny dla wielu wątków."""

    def __init__(
        self, scenario: Scenario, pulse_settings: PulseSettings, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._scenario = scenario
        self._pulse_settings = pulse_settings
        self._clock = clock
        self._started = clock()
        self._lock = threading.Lock()
        self._scene: str | None = None
        self._path: list[dict[str, str]] = []
        self._decisions: list[dict[str, Any]] = []
        self._votes: dict[str, Any] | None = None
        self._tallies: dict[str, dict[str, Any]] = {}  # ostatnie głosy w każdej scenie, do podpisu decyzji
        self._history: deque[list[float]] = deque(maxlen=HISTORY_SAMPLES)
        self._last: Pulse | None = None
        self._baseline: float | None = None
        self._log: deque[dict[str, str]] = deque(maxlen=LOG_ENTRIES)

    def event(self, kind: str, data: Mapping[str, Any]) -> None:
        handler = getattr(self, f"_on_{kind}", None)
        if handler is None:
            log.debug("Panel pomija nieznane zdarzenie %s", kind)
            return
        with self._lock:
            handler(data)

    def record_pulse(self, reading: Pulse) -> None:
        with self._lock:
            self._last = reading
            self._history.append([round(self._clock() - self._started, 1), reading.bpm])

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            baseline = self._baseline
            bpm = self._last.bpm if self._last else None
            state = hall_state(bpm, baseline, self._pulse_settings) if bpm is not None and baseline else None
            return {
                "scene": self._scene,
                "path": list(self._path),
                "decisions": list(self._decisions),
                "votes": self._votes,
                "pulse": {
                    "history": list(self._history),
                    "bpm": bpm,
                    "viewers": self._last.viewers if self._last else None,
                    "baseline": baseline,
                    "excited": baseline * self._pulse_settings.excited if baseline else None,
                    "bored": baseline * self._pulse_settings.bored if baseline else None,
                    "state": state,
                },
                "log": list(self._log),
            }

    def _say(self, text: str) -> None:
        self._log.append({"time": time.strftime("%H:%M:%S"), "text": text})

    def _on_scena(self, data: Mapping[str, Any]) -> None:
        self._scene = data["scene"]
        self._path.append({"scene": data["scene"], "variant": data["variant"]})
        version = "" if data["variant"] == "zwykla" else f" w wersji {VERSION.get(data['variant'], data['variant'])}"
        self._say(f"Scena {data['scene']}{version}")

    def _on_decyzja(self, data: Mapping[str, Any]) -> None:
        # Głosy poprzedzają decyzję i służą jej raz: przy kolejnej wizycie w scenie nie wrócą nieaktualne.
        tally = self._tallies.pop(data["scene"], None)
        decision: dict[str, Any] = {key: data[key] for key in ("scene", "choice", "label", "how")}
        decision["source"] = tally["source"] if tally else None
        decision["counts"] = tally["counts"] if tally else None
        self._decisions.append(decision)
        self._say(f"Decyzja w scenie {data['scene']}: {data['label']} ({HOW.get(data['how'], data['how'])})")

    def _on_glosy(self, data: Mapping[str, Any]) -> None:
        self._votes = {"scene": data["scene"], "source": data["source"], "counts": dict(data["counts"])}
        self._tallies[data["scene"]] = {"source": data["source"], "counts": dict(data["counts"])}
        choices = self._scenario.scene(data["scene"]).choices
        results = ", ".join(
            f"{choices[cid].display_label if cid in choices else cid} {count}" for cid, count in data["counts"].items()
        )
        self._say(f"Głosy ({data['source']}): {results}")

    def _on_odniesienie(self, data: Mapping[str, Any]) -> None:
        self._baseline = data["bpm"]
        self._say(f"Punkt odniesienia tętna sali: {data['bpm']:.0f}")

    def _on_wersja(self, data: Mapping[str, Any]) -> None:
        version = VERSION.get(data["variant"], data["variant"])
        self._say(
            f"Tętno sali {data['bpm']:.0f} (odniesienie {data['baseline']:.0f}), sala {data['state']}: "
            f"scena {data['scene']} w wersji {version}"
        )


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    # Na Windows SO_REUSEADDR pozwala drugiemu procesowi zająć port, na którym ktoś już nasłuchuje:
    # zapomniany podgląd panelu po cichu wygrywałby z panelem filmu. Tam więc wyłączamy ponowne użycie portu.
    allow_reuse_address = sys.platform != "win32"
    state: PanelState
    graph: dict[str, Any]
    pulse: SimulatedPulse | None


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("%s %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html") and (APP_DIR / "index.html").is_file():
            self._send(200, (APP_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/graph":
            self._json(200, self.server.graph)
        elif path == "/state":
            snapshot = self.server.state.snapshot()
            snapshot["pulse"]["target"] = self.server.pulse.target if self.server.pulse else None
            self._json(200, snapshot)
        else:
            self._json(404, {"error": "nie ma takiej strony"})

    def do_POST(self) -> None:
        # Najpierw czytamy treść zapytania: odpowiedź bez jej wczytania Windows kończy zerwaniem połączenia (10053).
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        body = self.rfile.read(length) if 0 < length <= MAX_COMMAND_BYTES else b""
        if urlparse(self.path).path != "/pulse":
            self._json(404, {"error": "nie ma takiej strony"})
            return
        if self.headers.get_content_type() != "application/json":
            # Formularz z obcej strony potrafi wysłać tylko text/plain albo urlencoded: nie dajemy mu sterować tętnem.
            self.close_connection = True
            self._json(415, {"error": "oczekiwano Content-Type: application/json"})
            return
        pulse = self.server.pulse
        if pulse is None:
            self._json(409, {"error": "symulator tętna jest wyłączony"})
            return
        try:
            if not body:
                self.close_connection = True  # nieprzeczytana treść: nie używamy dalej tego połączenia
                raise ValueError("puste albo za długie polecenie")
            command = json.loads(body)
            if not isinstance(command, dict):
                raise ValueError("oczekiwano obiektu JSON")
            self._apply(pulse, command)
        except ValueError as exc:  # json.JSONDecodeError też jest ValueError
            message = "oczekiwano obiektu JSON" if isinstance(exc, json.JSONDecodeError) else str(exc)
            self._json(400, {"error": message})
            return
        self._json(200, {"ok": True, "target": pulse.target})

    @staticmethod
    def _apply(pulse: SimulatedPulse, command: dict[str, Any]) -> None:
        if "target" in command:
            try:
                target = float(command["target"])
            except (TypeError, ValueError):
                raise ValueError("'target' musi być liczbą uderzeń na minutę") from None
            pulse.set_target(target)
        elif "preset" in command:
            pulse.preset(str(command["preset"]))
        elif command.get("script") == "demo":
            pulse.play_script()
        else:
            raise ValueError("nieznane polecenie; dostępne: target, preset, script")

    def _json(self, code: int, data: Any) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class PanelServer:
    """Serwer panelu w wątku w tle; co `sample_every_s` zapisuje próbkę tętna (wykres żyje w trakcie klipów)."""

    def __init__(
        self,
        state: PanelState,
        graph: dict[str, Any],
        pulse: SimulatedPulse | None,
        settings: PanelSettings,
        sample_every_s: float = 1.0,
    ) -> None:
        self._state = state
        self._graph = graph
        self._pulse = pulse
        self._settings = settings
        self._sample_every_s = sample_every_s
        self._server: _Server | None = None
        self._stopped = threading.Event()

    def start(self) -> str:
        server = _Server((self._settings.host, self._settings.port), _Handler)
        server.state, server.graph, server.pulse = self._state, self._graph, self._pulse
        serve = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, name="bajka-panel-server")
        serve.daemon = True
        serve.start()
        if self._pulse is not None:
            threading.Thread(target=self._sample, args=(self._pulse,), name="bajka-panel-tetno", daemon=True).start()
        self._server = server
        # 127.0.0.1, nie localhost: na Windows localhost najpierw próbuje IPv6 i każde odświeżenie czeka.
        host = "127.0.0.1" if self._settings.host == "0.0.0.0" else self._settings.host
        url = f"http://{host}:{server.server_address[1]}/"
        log.info("Panel dla jury: %s", url)
        if self._settings.host == "0.0.0.0":
            log.info("Na tablecie jury w tej samej sieci: adres IP tego komputera, port %d", server.server_address[1])
        return url

    def stop(self) -> None:
        self._stopped.set()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

    def _sample(self, pulse: AudiencePulse) -> None:
        while not self._stopped.is_set():
            try:
                self._state.record_pulse(pulse.read())
            except Exception:
                log.exception("Błąd odczytu tętna dla panelu")
            self._stopped.wait(self._sample_every_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.panel", description="Podgląd panelu dla jury bez filmu.")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        scenario = load_scenario(args.scenario)
        env = load_env()
        pulse_settings = PulseSettings.from_env(env)
        settings = PanelSettings.from_env(env)
    except (ScenarioError, ConfigError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    simulator = SimulatedPulse(pulse_settings)
    state = PanelState(scenario, pulse_settings)
    server = PanelServer(state, scenario_graph(scenario), simulator, settings)
    try:
        url = server.start()
    except OSError as exc:
        print(f"Nie udało się uruchomić panelu: {exc}", file=sys.stderr)
        return 2
    print(f"Panel: {url} — Ctrl+C kończy. Scena startowa i punkt odniesienia tętna są już na panelu.")
    start = scenario.scene(scenario.start)
    state.event("scena", {"scene": start.id, "clip": start.clip.name, "variant": "zwykla"})
    state.event("odniesienie", {"bpm": simulator.read().bpm})
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

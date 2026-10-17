"""Odtwarzacz w przeglądarce: odcinek wygląda i działa jak w serwisie streamingowym, z oknami wyboru na ekranie.

Silnik bajki prowadzi odcinek po stronie komputera, a strona `player_app/index.html` tylko wykonuje jego polecenia:
odtwarza klip, zapętla tło okna wyboru, pokazuje opcje z odliczaniem, wyświetla napisy i czyta kwestie postaci
syntezą mowy przeglądarki (na Windows to te same lokalne głosy systemu). Gdy rodzic zostawi włączony mikrofon,
strona nagrywa odpowiedź widza w trakcie okna wyboru, a komputer rozpoznaje ją lokalnie (Whisper z Foundry Local).
Nagranie trafia na chwilę do pliku tymczasowego, usuwanego zaraz po rozpoznaniu, i nie jest przechowywane.

Montaż: strona ma dwa „pokłady” wideo i nakłada klipy na siebie. Kolejne ujęcie wchodzi przejściem wybranym przez
montażystę (cięcie, przenikanie, zaciemnienie, rozjaśnienie, przetarcie), a warstwy wybrane przez widza
(przezroczyste klipy WebM) leżą nad klipem sceny. Strona zgłasza koniec klipu chwilę przed jego końcem, żeby
następne ujęcie mogło na niego zajść; cięcie czeka do ostatniej klatki (pętla zaczyna się od niej).

Widz wybiera strzałkami i OK na pilocie (w przeglądarce: strzałki i Enter), cyframi 1–9, dotykiem, myszą albo głosem.
Zamknięcie karty wstrzymuje odcinek: po ponownym otwarciu strony bieżący klip gra od początku, a odliczanie
okna wyboru stoi, dopóki nikt nie patrzy. Moduł spełnia kontrakty `Player`, `Compositor`, `Voice` i `Viewer`
z `bajka.ports`.
"""

from __future__ import annotations

import ipaddress
import itertools
import json
import logging
import mimetypes
import re
import socket
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import numpy as np

from bajka.config import get_float, get_int
from bajka.local_stt import clean_transcript
from bajka.mobile import samples_from_wav
from bajka.ports import Answer, Shot
from bajka.scenario import Scenario, Scene, media_files

log = logging.getLogger(__name__)

APP_DIR = Path(__file__).with_name("player_app")
STALE_SECONDS = 3.0  # strona, która tyle nie pytała o stan, jest zamknięta albo uśpiona: odliczanie stoi
MAX_TRANSCRIBE_SECONDS = 15.0  # dłużej na rozpoznanie nagrania po końcu odliczania nie czekamy
MAX_UPLOAD_BYTES = 2_000_000  # ok. minuta nagrania 16 kHz mono; więcej to błąd albo nadużycie
MAX_EVENT_BYTES = 4096
CHUNK_BYTES = 256 * 1024
LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1"}
# Typy wprost, nie z mimetypes: na Windows mimetypes czyta rejestr, a tam bywają błędne wpisy.
VIDEO_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}


@dataclass(frozen=True)
class WebPlayerSettings:
    host: str = "127.0.0.1"  # localhost to bezpieczny kontekst: przeglądarka da mikrofon bez certyfikatu HTTPS
    port: int = 8080
    answer_seconds: float = 6.0  # najdłuższe nagranie jednej odpowiedzi głosem
    grace_seconds: float = 4.0  # zapas ponad odliczanie na ekranie, zanim komputer sam zamknie okno wyboru

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> WebPlayerSettings:
        return cls(
            host=env.get("BAJKA_WEB_HOST") or cls.host,
            port=get_int(env, "BAJKA_WEB_PORT", cls.port),
            answer_seconds=get_float(env, "BAJKA_WEB_ANSWER_SECONDS", cls.answer_seconds),
            grace_seconds=get_float(env, "BAJKA_WEB_GRACE_SECONDS", cls.grace_seconds),
        )


class WebEpisode:
    """Stan odcinka dzielony przez silnik (Player, Voice, Viewer) i stronę odtwarzacza (zapytania HTTP).

    Każde polecenie dla strony ma kolejny numer `seq`; silnik czeka, aż strona zgłosi jego wykonanie.
    """

    def __init__(
        self,
        scenario: Scenario,
        transcribe: Callable[[np.ndarray], str] | None = None,
        settings: WebPlayerSettings = WebPlayerSettings(),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._urls = {path: f"media/{index}/{quote(path.name)}" for index, path in enumerate(media_files(scenario))}
        self._files = {"/" + url: path for path, url in self._urls.items()}
        self._scenario = scenario
        self._title = scenario.title or "Bajka interaktywna"
        self._transcribe = transcribe
        self._settings = settings
        self._clock = clock
        self._cond = threading.Condition()
        self._seq = 0
        self._command: dict[str, Any] = {"kind": "idle"}
        self._done = 0
        self._background: dict[str, Any] | None = None  # pętla oczekiwania z warstwami pod oknem wyboru
        self._scene: Scene | None = None  # scena otwartego okna wyboru
        self._answer: Answer | None = None
        self._remaining = 0.0  # sekundy do zamknięcia okna wyboru, razem z zapasem
        self._pending_voice = 0
        self._seen = float("-inf")
        self._closed = False
        self._restart = False
        self.on_stop: Callable[[], None] | None = None  # zatrzymanie silnika, gdy widz zamknie odcinek

    # --- kontrakty Player, Voice i Viewer (wątek silnika) ---

    def play(self, clip: Path) -> None:
        self.play_shot(Shot(clip))

    def loop(self, clip: Path) -> None:
        self.loop_shot(Shot(clip))

    def play_shot(self, shot: Shot) -> None:
        with self._cond:
            self._background = None
            self._wait_done(self._issue({"kind": "play", **self._shot(shot)}))

    def loop_shot(self, shot: Shot) -> None:
        with self._cond:
            self._background = self._shot(shot)
            self._issue({"kind": "idle"})

    def say(self, text: str) -> None:
        with self._cond:
            self._wait_done(self._issue({"kind": "say", "text": text}))

    def ask(self, scene: Scene, seconds: float) -> Answer:
        choices = [{"id": c.id, "label": c.display_label, "icon": c.icon} for c in scene.choices.values()]
        with self._cond:
            self._issue({"kind": "ask", "scene": scene.id, "question": scene.question, "choices": choices,
                         "seconds": seconds})  # fmt: skip
            self._scene, self._answer = scene, None
            self._remaining = seconds + self._settings.grace_seconds
            last = self._clock()
            while self._answer is None and not self._closed:
                now = self._clock()
                if now - self._seen < STALE_SECONDS:
                    self._remaining -= now - last
                last = now
                if self._remaining <= 0 and (self._pending_voice == 0 or self._remaining < -MAX_TRANSCRIBE_SECONDS):
                    break
                self._cond.wait(0.1)
            answer, self._scene, self._answer = self._answer or Answer(), None, None
            self._issue({"kind": "idle"})  # okno wyboru znika z ekranu
            return answer

    # --- koniec odcinka (wątek aplikacji) ---

    def finish(self, visited: list[str], decisions: list[tuple[str, str]] | None = None) -> bool:
        """Ekran końcowy; zwraca True, gdy widz chce obejrzeć jeszcze raz, False, gdy zamknął odcinek."""
        path = story_labels(self._scenario, decisions) if decisions else branch_labels(self._scenario, visited)
        with self._cond:
            self._restart = False
            self._background = None
            self._issue({"kind": "end", "path": path})
            while not self._restart and not self._closed:
                self._cond.wait(0.25)
            return self._restart and not self._closed

    def close(self) -> None:
        with self._cond:
            if self._closed:
                return
            self._closed = True
            self._issue({"kind": "closed"})
            self._cond.notify_all()
        if self.on_stop is not None:
            self.on_stop()

    # --- strona odtwarzacza (wątki serwera HTTP) ---

    def state(self) -> dict[str, Any]:
        with self._cond:
            self._seen = self._clock()
            state = {**self._command, "seq": self._seq, "background": self._background, "title": self._title,
                     "voice": self._transcribe is not None, "answer_seconds": self._settings.answer_seconds}  # fmt: skip
            if state["kind"] == "ask":
                state["seconds_left"] = max(0.0, min(state["seconds"], self._remaining - self._settings.grace_seconds))
            return state

    def media(self, path: str) -> Path | None:
        """Plik wideo pod adresem strony; tylko klipy ze scenariusza, nic więcej z dysku."""
        return self._files.get(path)

    def event(self, data: Mapping[str, Any]) -> str:
        kind = data.get("type")
        if kind == "stop":
            self.close()
            return "ok"
        with self._cond:
            seq = data.get("seq")
            if kind == "restart":
                if self._command["kind"] != "end":
                    return "stale"
                self._restart = True
            elif seq != self._seq:
                return "stale"  # spóźnione zgłoszenie po poprzednim poleceniu
            elif kind == "done":
                self._done = seq
            elif kind == "choice":
                if self._scene is None or data.get("choice") not in self._scene.choices:
                    return "closed"
                self._answer = Answer(choice_id=str(data["choice"]))
            elif kind == "timeout":
                if self._scene is None:
                    return "closed"
                self._remaining = min(self._remaining, 0.0)
            else:
                return "unknown"
            self._cond.notify_all()
            return "ok"

    def submit_voice(self, seq: int, wav: bytes) -> tuple[str, str]:
        """Nagranie odpowiedzi z okna wyboru; zwraca status i rozpoznany tekst (dla podpowiedzi na ekranie)."""
        with self._cond:
            if self._transcribe is None:
                return "off", ""
            if self._scene is None or seq != self._seq:
                return "closed", ""
            self._pending_voice += 1
        try:
            transcript = clean_transcript(self._transcribe(samples_from_wav(wav))) or ""
        except ValueError as exc:
            log.warning("Odrzucone nagranie z odtwarzacza: %s", exc)
            transcript = ""
        except Exception:
            log.exception("Nie udało się rozpoznać nagrania z odtwarzacza")
            transcript = ""
        with self._cond:
            self._pending_voice -= 1
            self._cond.notify_all()
            if not transcript:
                return "empty", ""
            if self._scene is None or seq != self._seq:
                return "closed", transcript
            self._answer = Answer(transcript=transcript)
            return "ok", transcript

    # --- pomocnicze (wywoływane z blokadą) ---

    def _shot(self, shot: Shot) -> dict[str, Any]:
        cut = {"transition": shot.cut.transition, "seconds": shot.cut.seconds}
        return {"clip": self._url(shot.clip), "layers": [self._url(layer) for layer in shot.layers], "cut": cut}

    def _url(self, clip: Path) -> str:
        return self._urls.get(clip) or self._register(clip)

    def _register(self, clip: Path) -> str:
        url = f"media/{len(self._urls)}/{quote(clip.name)}"
        self._urls[clip], self._files["/" + url] = url, clip
        return url

    def _issue(self, command: dict[str, Any]) -> int:
        if self._closed and command["kind"] != "closed":
            return self._seq
        self._seq += 1
        self._command = command
        self._cond.notify_all()
        return self._seq

    def _wait_done(self, seq: int) -> None:
        # Bez limitu czasu: zamknięta karta wstrzymuje odcinek, a po powrocie widza klip gra od początku.
        while self._done < seq and not self._closed:
            self._cond.wait(0.25)


def story_labels(scenario: Scenario, decisions: list[tuple[str, str]]) -> list[str]:
    """Nazwy wyborów, które zmieniły odcinek: poprowadziły inną drogą albo nałożyły warstwę (np. kwiatek)."""
    labels = []
    for scene_id, choice_id in decisions:
        scene = scenario.scene(scene_id)
        choice = scene.choices[choice_id]
        if len({c.next for c in scene.choices.values()}) > 1 or choice.layer is not None:
            labels.append(choice.display_label)
    return labels


def branch_labels(scenario: Scenario, visited: list[str]) -> list[str]:
    """Nazwy wyborów, które zmieniły bieg odcinka (np. „Tęczowy Mostek”), do ekranu końcowego.

    Zagadki, w których każda odpowiedź prowadzi do tej samej sceny, pomijamy: liczą się rozgałęzienia.
    """
    labels = []
    for here, there in itertools.pairwise(visited):
        leading = [c for c in scenario.scene(here).choices.values() if c.next == there]
        if len(leading) == 1 and len({c.next for c in scenario.scene(here).choices.values()}) > 1:
            labels.append(leading[0].display_label)
    return labels


# --- serwer HTTP ---


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    # Na Windows SO_REUSEADDR pozwala drugiemu procesowi zająć port, na którym ktoś już nasłuchuje. Wyłączamy to.
    allow_reuse_address = sys.platform != "win32"
    episode: WebEpisode
    loopback: bool = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        log.debug("Błąd połączenia z %s", client_address, exc_info=True)


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    protocol_version = "HTTP/1.1"  # przeglądarka trzyma połączenie przy kolejnych fragmentach wideo

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("%s %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        if not self._host_allowed():
            return
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, (APP_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/state":
            self._json(200, self.server.episode.state())
        elif (media := self.server.episode.media(path)) is not None and media.is_file():
            self._send_file(media)
        else:
            self._json(404, {"error": "nie ma takiej strony"})

    def do_POST(self) -> None:
        # Najpierw czytamy treść zapytania: odpowiedź bez jej wczytania Windows kończy zerwaniem połączenia (10053).
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        body = b""
        if 0 < length <= MAX_UPLOAD_BYTES:
            body = self.rfile.read(length)
        elif length != 0:
            self.close_connection = True  # nieprzeczytana treść: nie używamy dalej tego połączenia
        if not self._host_allowed():
            return
        url = urlparse(self.path)
        # Obca strona otwarta w tej samej przeglądarce wyśle bez zgody tylko text/plain albo formularz,
        # więc wymagamy typów, które przeglądarka przepuszcza wyłącznie ze strony odtwarzacza.
        if url.path == "/api/event":
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"error": "oczekiwano Content-Type: application/json"})
                return
            try:
                data = json.loads(body) if len(body) <= MAX_EVENT_BYTES else None
            except ValueError:
                data = None
            if not isinstance(data, dict):
                self._json(400, {"error": "oczekiwano obiektu JSON"})
                return
            status = self.server.episode.event(data)
            self._json(200 if status == "ok" else 409, {"status": status})
        elif url.path == "/api/voice":
            if self.headers.get_content_type() != "audio/wav":
                self._json(415, {"error": "oczekiwano Content-Type: audio/wav"})
                return
            try:
                seq = int(parse_qs(url.query).get("seq", [""])[0])
            except ValueError:
                self._json(400, {"error": "zły numer polecenia"})
                return
            if not body:
                self._json(413, {"error": "za duże albo puste nagranie"})
                return
            status, transcript = self.server.episode.submit_voice(seq, body)
            self._json(200, {"status": status, "transcript": transcript})
        else:
            self._json(404, {"error": "nie ma takiej strony"})

    def _host_allowed(self) -> bool:
        """Na localhost przyjmujemy tylko nagłówek Host localhost: chroni przed podszyciem domeny (DNS rebinding)."""
        if not self.server.loopback:
            return True
        host = urlparse(f"//{self.headers.get('Host') or ''}").hostname or ""
        if host in LOOPBACK_NAMES:
            return True
        self.close_connection = True
        self._json(403, {"error": "odtwarzacz działa tylko pod adresem 127.0.0.1 albo localhost"})
        return False

    def _send_file(self, path: Path) -> None:
        size = path.stat().st_size
        start, end, code = 0, size - 1, 200
        requested = self.headers.get("Range")
        if requested:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested.strip())
            if match and match[1]:
                start, end = int(match[1]), min(int(match[2]) if match[2] else size - 1, size - 1)
            elif match and match[2]:
                start = max(0, size - int(match[2]))  # ostatnie N bajtów
            if not match or not (match[1] or match[2]) or start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        content_type = VIDEO_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            with path.open("rb") as file:
                file.seek(start)
                left = end - start + 1
                while left > 0 and (chunk := file.read(min(CHUNK_BYTES, left))):
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True  # przeglądarka przerwała pobieranie, np. przy przewijaniu albo nowym klipie

    def _json(self, code: int, data: dict[str, Any]) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class WebPlayerServer:
    """Serwer odtwarzacza w wątku w tle; `start()` zwraca adres do otwarcia w przeglądarce."""

    def __init__(self, episode: WebEpisode, settings: WebPlayerSettings) -> None:
        self._episode = episode
        self._settings = settings
        self._server: _Server | None = None

    @property
    def episode(self) -> WebEpisode:
        return self._episode

    def start(self) -> str:
        server = _Server((self._settings.host, self._settings.port), _Handler)
        server.episode = self._episode
        server.loopback = _is_loopback(self._settings.host)
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, name="bajka-web", daemon=True).start()
        self._server = server
        # 127.0.0.1, nie localhost: na Windows localhost najpierw próbuje IPv6 i każde zapytanie czeka.
        host = "127.0.0.1" if self._settings.host == "0.0.0.0" else self._settings.host
        url = f"http://{host}:{server.server_address[1]}/"
        log.info("Odcinek w przeglądarce: %s", url)
        if not server.loopback:
            log.warning("Odtwarzacz poza localhost działa przez HTTP: przeglądarka innego urządzenia nie da mikrofonu")
        return url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()


def _is_loopback(host: str) -> bool:
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(socket.gethostbyname(host)).is_loopback
    except (OSError, ValueError):
        return False

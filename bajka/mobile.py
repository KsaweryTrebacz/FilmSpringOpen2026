"""Aplikacja mobilna widowni: telefony widzów nagrywają odpowiedzi mikrofonem i wysyłają je do komputera z filmem.

Komputer z filmem uruchamia lokalny serwer w tej samej sieci Wi-Fi. Widz skanuje kod QR z ekranu kina,
otwiera aplikację w przeglądarce telefonu (bez instalacji; można dodać do ekranu głównego) i zezwala na
mikrofon. Gdy Lila zadaje pytanie, telefon pokazuje je z opcjami i sam nagrywa odpowiedź, a komputer
rozpoznaje ją lokalnie (Whisper), ustala wybór (słowa kluczowe, w razie potrzeby model językowy) i liczy głosy.
Moduł spełnia kontrakt `bajka.ports.Audience`. Nagrania są przetwarzane w pamięci i nie są zapisywane.

Próba z telefonami bez filmu: python -m bajka.mobile SCENARIUSZ [--scene ID] [--no-llm]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import io
import ipaddress
import json
import logging
import re
import socket
import ssl
import sys
import threading
import time
import wave
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np

from bajka.config import ConfigError, get_float, get_int, load_env
from bajka.local_stt import SAMPLE_RATE, clean_transcript
from bajka.ports import IntentResolver, Interpretation
from bajka.scenario import Scene, ScenarioError, load_scenario

log = logging.getLogger(__name__)

APP_DIR = Path(__file__).with_name("mobile_app")
CERT_DIR = Path.home() / ".bajka"
ACTIVE_SECONDS = 6.0  # telefon, który tyle nie pytał o stan, uznajemy za rozłączony
MAX_UPLOAD_BYTES = 2_000_000  # ok. minuta nagrania 16 kHz mono; więcej to błąd albo nadużycie
_DEVICE_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


@dataclass(frozen=True)
class MobileSettings:
    host: str = "0.0.0.0"
    port: int = 8443
    https: bool = True  # przeglądarki dają dostęp do mikrofonu tylko na stronach HTTPS
    cert: str = ""  # własny certyfikat i klucz; puste = samopodpisany, tworzony raz w ~/.bajka
    key: str = ""
    round_seconds: float = 8.0  # ile czekamy na odpowiedzi z telefonów
    resolve_seconds: float = 4.0  # ile po zamknięciu rundy czekamy na rozpoznanie ostatnich nagrań
    answer_seconds: float = 6.0  # najdłuższe nagranie jednej odpowiedzi na telefonie
    workers: int = 2  # ile nagrań rozpoznajemy naraz

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> MobileSettings:
        https = (env.get("BAJKA_MOBILE_HTTPS") or "1").strip().lower()
        if https not in ("0", "1", "tak", "nie", "true", "false"):
            raise ConfigError(f"BAJKA_MOBILE_HTTPS musi być 1 albo 0, jest: {https!r}")
        return cls(
            host=env.get("BAJKA_MOBILE_HOST") or cls.host,
            port=get_int(env, "BAJKA_MOBILE_PORT", cls.port),
            https=https in ("1", "tak", "true"),
            cert=env.get("BAJKA_MOBILE_CERT") or "",
            key=env.get("BAJKA_MOBILE_KEY") or "",
            round_seconds=get_float(env, "BAJKA_MOBILE_ROUND_SECONDS", cls.round_seconds),
            resolve_seconds=get_float(env, "BAJKA_MOBILE_RESOLVE_SECONDS", cls.resolve_seconds),
            answer_seconds=get_float(env, "BAJKA_MOBILE_ANSWER_SECONDS", cls.answer_seconds),
            workers=max(1, get_int(env, "BAJKA_MOBILE_WORKERS", cls.workers)),
        )


def samples_from_wav(data: bytes) -> np.ndarray:
    """Nagranie z telefonu (WAV PCM 16-bit) → próbki 16 kHz mono do rozpoznawania mowy."""
    try:
        with wave.open(io.BytesIO(data)) as wav:
            channels, width, rate = wav.getnchannels(), wav.getsampwidth(), wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"to nie jest plik WAV: {exc}") from exc
    if width != 2 or channels < 1 or rate <= 0:
        raise ValueError(f"oczekiwano WAV PCM 16-bit, jest: {width * 8}-bit, {channels} kan., {rate} Hz")
    samples = np.frombuffer(frames, dtype="<i2").reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE and samples.size:
        positions = np.arange(0, samples.size, rate / SAMPLE_RATE)
        samples = np.interp(positions, np.arange(samples.size), samples)
    return samples.astype(np.int16)


@dataclass
class _Round:
    id: int
    scene: Scene
    deadline: float
    answered: set[str] = field(default_factory=set)
    pending: list[concurrent.futures.Future] = field(default_factory=list)
    open: bool = True


class MobileAudience:
    def __init__(
        self,
        transcribe: Callable[[np.ndarray], str],
        resolver: IntentResolver,
        settings: MobileSettings = MobileSettings(),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._transcribe = transcribe
        self._resolver = resolver
        self._settings = settings
        self._clock = clock
        self._lock = threading.Lock()
        self._devices: dict[str, float] = {}
        self._round: _Round | None = None
        self._next_round = 1
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=settings.workers, thread_name_prefix="bajka-mobile")

    # --- kontrakt Audience (wątek silnika) ---

    def connected(self) -> int:
        with self._lock:
            return len(self._active_devices())

    def collect(self, scene: Scene) -> list[Interpretation]:
        with self._lock:
            current = _Round(
                id=self._next_round,
                scene=scene,
                deadline=self._clock() + self._settings.round_seconds,
            )
            phones = len(self._active_devices())
            self._next_round += 1
            self._round = current
        log.info("Runda %d na telefonach: %s (połączonych: %d)", current.id, scene.id, phones)
        while self._clock() < current.deadline:
            with self._lock:
                if current.answered and self._active_devices() <= current.answered:
                    break  # odpowiedzieli wszyscy połączeni, także ci, którzy dołączyli w trakcie rundy
            time.sleep(0.1)
        with self._lock:
            current.open = False
            pending = list(current.pending)
        done, late = concurrent.futures.wait(pending, timeout=self._settings.resolve_seconds)
        if late:
            log.warning("Runda %d: %d nagrań nie zdążyło się rozpoznać", current.id, len(late))
        return [future.result() for future in done if future.exception() is None and future.result() is not None]

    # --- API dla telefonów (wątki serwera) ---

    def state(self, device: str) -> dict[str, Any]:
        with self._lock:
            self._devices[device] = self._clock()
            current = self._round
            if current is None or not current.open:
                return {"round": None}
            return {
                "round": current.id,
                "question": current.scene.question,
                "choices": [{"id": c.id, "label": c.display_label} for c in current.scene.choices.values()],
                "seconds_left": round(max(0.0, current.deadline - self._clock()), 1),
                "answer_seconds": self._settings.answer_seconds,
                "answered": device in current.answered,
            }

    def submit(
        self, device: str, round_id: int, *, audio: bytes | None = None, text: str | None = None, choice: str | None = None
    ) -> str:
        """Przyjmuje odpowiedź z telefonu: "ok", "closed" (runda zamknięta) albo "duplicate"."""
        with self._lock:
            self._devices[device] = self._clock()
            current = self._round
            if current is None or not current.open or current.id != round_id:
                return "closed"
            if device in current.answered:
                return "duplicate"
            current.answered.add(device)
            current.pending.append(self._pool.submit(self._interpret, current.scene, audio, text, choice))
            return "ok"

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _active_devices(self) -> set[str]:
        now = self._clock()
        return {device for device, seen in self._devices.items() if now - seen <= ACTIVE_SECONDS}

    def _interpret(self, scene: Scene, audio: bytes | None, text: str | None, choice: str | None) -> Interpretation | None:
        try:
            if choice is not None:  # widz dotknął opcji zamiast mówić (np. dziecko, które nie chce mówić)
                return Interpretation(choice, "") if choice in scene.choices else None
            text = clean_transcript(self._transcribe(samples_from_wav(audio)) if audio is not None else text or "")
            if not text:
                return None
            interpretation = self._resolver.resolve(scene, text)
            log.info("Telefon: %r -> %s", text, interpretation.choice_id)
            return interpretation
        except Exception:
            log.exception("Nie udało się rozpoznać odpowiedzi z telefonu")
            return None


# --- serwer HTTP(S) ---


def lan_address() -> str:
    """Adres komputera w sieci lokalnej (bez wysyłania czegokolwiek)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def ensure_certificate(directory: Path, address: str) -> tuple[Path, Path]:
    """Samopodpisany certyfikat dla seansu; telefon raz pokaże ostrzeżenie, które trzeba zaakceptować."""
    cert_path, key_path = directory / "bajka-mobile.crt", directory / "bajka-mobile.key"
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Bajka - seans")])
    names: list[x509.GeneralName] = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    if address != "127.0.0.1":
        names.append(x509.IPAddress(ipaddress.ip_address(address)))
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .sign(key, hashes.SHA256())
    )
    directory.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def join_page(url: str) -> str:
    """Strona do wyświetlenia na ekranie kina przed seansem: duży kod QR i adres."""
    try:
        import segno

        qr = segno.make(url, error="m").svg_inline(scale=10, dark="#1b1b1b", light="#fffdf4")
    except ImportError:
        qr = ""
    return (
        "<!doctype html><html lang=pl><meta charset=utf-8><title>Dołącz do seansu</title>"
        "<body style='margin:0;background:#1b1b1b;color:#fffdf4;font:28px system-ui;display:grid;place-items:center;"
        "min-height:100vh;text-align:center'><div><h1>Zeskanuj i dołącz do Klubu Ciekawskich!</h1>"
        f"<div style='background:#fffdf4;display:inline-block;padding:16px;border-radius:16px'>{qr}</div>"
        f"<p>{url}</p><p style='font-size:20px;opacity:.7'>Zezwól na mikrofon. Nagrania nie są zapisywane.</p>"
        "</div></body></html>"
    )


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    ssl_context: ssl.SSLContext | None = None
    audience: MobileAudience
    public_url: str = ""

    def get_request(self) -> tuple[socket.socket, Any]:
        sock, address = super().get_request()
        if self.ssl_context is not None:
            # Uścisk TLS w wątku obsługi (setup), żeby jeden wolny telefon nie blokował pozostałych.
            sock = self.ssl_context.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)
        return sock, address

    def handle_error(self, request: Any, client_address: Any) -> None:
        log.debug("Błąd połączenia z %s", client_address, exc_info=True)


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    STATIC = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/index.html": ("index.html", "text/html; charset=utf-8"),
        "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
        "/icon.svg": ("icon.svg", "image/svg+xml"),
    }

    def setup(self) -> None:
        if isinstance(self.request, ssl.SSLSocket):
            self.request.settimeout(10)
            self.request.do_handshake()
        super().setup()

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("%s %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path in self.STATIC:
            name, content_type = self.STATIC[url.path]
            self._send(200, (APP_DIR / name).read_bytes(), content_type)
        elif url.path == "/api/state":
            device = self._device(url)
            if device:
                self._json(200, self.server.audience.state(device))
        elif url.path == "/qr":
            self._send(200, join_page(self.server.public_url).encode(), "text/html; charset=utf-8")
        else:
            self._json(404, {"error": "nie ma takiej strony"})

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if url.path != "/api/answer":
            self._json(404, {"error": "nie ma takiej strony"})
            return
        device = self._device(url)
        if not device:
            return
        try:
            round_id = int(parse_qs(url.query).get("round", [""])[0])
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._json(400, {"error": "zły numer rundy"})
            return
        if not 0 < length <= MAX_UPLOAD_BYTES:
            self._json(413, {"error": "za duże albo puste nagranie"})
            return
        body = self.rfile.read(length)
        if (self.headers.get("Content-Type") or "").startswith("application/json"):
            try:
                data = json.loads(body)
            except ValueError:
                self._json(400, {"error": "zły JSON"})
                return
            status = self.server.audience.submit(
                device, round_id, text=str(data.get("text") or "") or None, choice=data.get("choice")
            )
        else:
            status = self.server.audience.submit(device, round_id, audio=body)
        self._json(200 if status == "ok" else 409, {"status": status})

    def _device(self, url: Any) -> str | None:
        device = parse_qs(url.query).get("device", [""])[0]
        if not _DEVICE_ID.match(device):
            self._json(400, {"error": "brak identyfikatora telefonu"})
            return None
        return device

    def _json(self, code: int, data: dict[str, Any]) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class MobileServer:
    """Serwer aplikacji mobilnej w wątku w tle; `start()` zwraca adres do zeskanowania przez widzów."""

    def __init__(self, audience: MobileAudience, settings: MobileSettings) -> None:
        self._audience = audience
        self._settings = settings
        self._server: _Server | None = None

    @property
    def audience(self) -> MobileAudience:
        return self._audience

    def start(self) -> str:
        server = _Server((self._settings.host, self._settings.port), _Handler)
        server.audience = self._audience
        address = lan_address()
        scheme = "http"
        if self._settings.https:
            context = self._ssl_context(address)
            if context is not None:
                server.ssl_context, scheme = context, "https"
        port = server.server_address[1]
        server.public_url = f"{scheme}://{address}:{port}/"
        threading.Thread(target=server.serve_forever, name="bajka-mobile-server", daemon=True).start()
        self._server = server
        log.info("Aplikacja mobilna widowni: %s (kod QR na ekran: %sqr)", server.public_url, server.public_url)
        return server.public_url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        self._audience.close()

    def _ssl_context(self, address: str) -> ssl.SSLContext | None:
        try:
            if self._settings.cert and self._settings.key:
                cert, key = Path(self._settings.cert), Path(self._settings.key)
            else:
                cert, key = ensure_certificate(CERT_DIR, address)
        except ImportError:
            log.warning(
                "Brak pakietu cryptography do certyfikatu HTTPS (pip install -e \".[mobile]\"). Serwer działa przez HTTP, "
                "ale przeglądarki w telefonach mogą zablokować mikrofon"
            )
            return None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        return context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.mobile", description="Próba aplikacji mobilnej widowni bez filmu: rundy pytań na telefonach."
    )
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument("--scene", help="scena z pytaniem (domyślnie scena startowa)")
    parser.add_argument("--rounds", type=int, default=3, help="ile rund przeprowadzić (domyślnie 3)")
    parser.add_argument("--no-llm", action="store_true", help="wybór tylko po słowach kluczowych")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        scenario = load_scenario(args.scenario)
        env = load_env()
        settings = MobileSettings.from_env(env)
        from bajka.local_stt import FoundryTranscriber, LocalSttSettings

        transcribe = FoundryTranscriber.from_settings(LocalSttSettings.from_env(env))
        resolver = _demo_resolver(env, scenario.hero, use_llm=not args.no_llm)
    except (ScenarioError, ConfigError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:  # demo ma pokazać każdy błąd modeli, a nie wywrócić się
        print(f"Błąd modeli lokalnych: {exc}", file=sys.stderr)
        return 1
    scene = scenario.scenes.get(args.scene or scenario.start)
    if scene is None or scene.is_ending:
        print(f"Scena '{args.scene or scenario.start}' nie istnieje albo nie ma wyborów", file=sys.stderr)
        return 2

    audience = MobileAudience(transcribe, resolver, settings)
    server = MobileServer(audience, settings)
    url = server.start()
    _print_qr(url)
    print(f"Telefony: otwórzcie {url} i zezwólcie na mikrofon. Na ekran kina: {url}qr", flush=True)
    try:
        for number in range(1, args.rounds + 1):
            input(f"\nEnter = runda {number}: {scene.question} (połączonych: {audience.connected()}) ")
            answers = audience.collect(scene)
            votes: dict[str, int] = {}
            for answer in answers:
                if answer.choice_id:
                    votes[answer.choice_id] = votes.get(answer.choice_id, 0) + 1
            print(f"Odpowiedzi: {len(answers)}, głosy: {votes or 'brak'}")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        server.stop()
    return 0


def _demo_resolver(env: Mapping[str, str], hero: str, use_llm: bool) -> IntentResolver:
    from bajka.keywords import KeywordIntentResolver, KeywordsFirstResolver

    keywords = KeywordIntentResolver()
    if not use_llm:
        return keywords
    from bajka.local_intent import LocalIntentResolver, LocalLlmSettings
    from bajka.safety import SafeReplyResolver

    return KeywordsFirstResolver(keywords, SafeReplyResolver(LocalIntentResolver.from_settings(LocalLlmSettings.from_env(env), hero)))


def _print_qr(url: str) -> None:
    try:
        import segno
    except ImportError:
        return
    segno.make(url, error="m").terminal(compact=True)


if __name__ == "__main__":
    sys.exit(main())

import http.client
import io
import json
import threading
import time
import urllib.error
import urllib.request
import wave

import numpy as np
import pytest

from bajka.config import ConfigError
from bajka.engine import StoryEngine
from bajka.keywords import KeywordIntentResolver
from bajka.mobile import MAX_UPLOAD_BYTES, MobileAudience, MobileServer, MobileSettings, join_page, samples_from_wav
from bajka.ports import Audience, Interpretation

FAST = MobileSettings(round_seconds=0.6, resolve_seconds=1.0, https=False, host="127.0.0.1", port=0)
PHONE_A, PHONE_B = "telefon-aaaa", "telefon-bbbb"


def wav_bytes(samples, rate=16000, channels=1):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(np.asarray(samples, dtype="<i2").tobytes())
    return buffer.getvalue()


def audience(transcribe=lambda samples: "do lasu", settings=FAST):
    return MobileAudience(transcribe, KeywordIntentResolver(), settings)


def collect_in_background(mobile, scene):
    result = {}
    worker = threading.Thread(target=lambda: result.update(answers=mobile.collect(scene)))
    worker.start()
    for _ in range(50):  # czekamy, aż runda się otworzy
        if mobile.state(PHONE_A)["round"]:
            break
        time.sleep(0.02)
    return worker, result


# Ustawienia i nagrania


def test_settings_defaults_and_env():
    assert MobileSettings.from_env({}).https is True
    settings = MobileSettings.from_env({"BAJKA_MOBILE_PORT": "9000", "BAJKA_MOBILE_HTTPS": "0", "BAJKA_MOBILE_ROUND_SECONDS": "5"})
    assert (settings.port, settings.https, settings.round_seconds) == (9000, False, 5.0)
    with pytest.raises(ConfigError, match="BAJKA_MOBILE_HTTPS"):
        MobileSettings.from_env({"BAJKA_MOBILE_HTTPS": "może"})


def test_wav_from_phone_is_mixed_to_mono_and_resampled_to_16k():
    stereo_48k = np.zeros((4800, 2), dtype=np.int16)
    stereo_48k[:, 0] = 1000

    samples = samples_from_wav(wav_bytes(stereo_48k.ravel(), rate=48000, channels=2))

    assert samples.dtype == np.int16
    assert len(samples) == 1600  # 0,1 s przy 16 kHz
    assert samples[100] == 500


def test_non_wav_upload_is_rejected():
    with pytest.raises(ValueError):
        samples_from_wav(b"to nie jest dzwiek")


# Rundy


def test_audience_meets_contract_and_counts_recent_phones():
    mobile = audience()
    mobile.state(PHONE_A)

    assert isinstance(mobile, Audience)
    assert mobile.connected() == 1


def test_round_shows_question_and_labels_on_phones(scenario):
    mobile = audience()
    worker, _ = collect_in_background(mobile, scenario.scene("intro"))

    state = mobile.state(PHONE_A)
    worker.join()

    assert state["question"] == "Idziemy do mrocznego lasu czy do jaskini?"
    assert [c["id"] for c in state["choices"]] == ["las", "jaskinia"]
    assert state["choices"][0]["label"] == "Las"
    assert state["answered"] is False
    assert mobile.state(PHONE_A) == {"round": None}  # po zamknięciu rundy


def test_voice_text_and_tap_answers_are_resolved(scenario):
    mobile = audience(transcribe=lambda samples: "chcę do jaskini")
    mobile.state(PHONE_B)
    worker, result = collect_in_background(mobile, scenario.scene("intro"))
    round_id = mobile.state(PHONE_A)["round"]

    assert mobile.submit(PHONE_A, round_id, audio=wav_bytes(np.zeros(1600))) == "ok"
    assert mobile.submit(PHONE_B, round_id, choice="las") == "ok"
    worker.join()

    assert sorted(a.choice_id for a in result["answers"]) == ["jaskinia", "las"]


def test_round_closes_early_when_every_phone_answered(scenario):
    slow = MobileSettings(round_seconds=5.0, resolve_seconds=1.0, https=False)
    mobile = audience(settings=slow)
    started = time.monotonic()
    worker, _ = collect_in_background(mobile, scenario.scene("intro"))

    mobile.submit(PHONE_A, mobile.state(PHONE_A)["round"], text="do lasu")
    worker.join()

    assert time.monotonic() - started < 2.0


def test_one_answer_per_phone_and_none_after_round(scenario):
    mobile = audience()
    mobile.state(PHONE_B)  # drugi telefon, żeby runda nie zamknęła się po pierwszej odpowiedzi
    worker, _ = collect_in_background(mobile, scenario.scene("intro"))
    round_id = mobile.state(PHONE_A)["round"]

    assert mobile.submit(PHONE_A, round_id, text="las") == "ok"
    assert mobile.submit(PHONE_A, round_id, text="jaskinia") == "duplicate"
    assert mobile.state(PHONE_A)["answered"] is True
    worker.join()
    assert mobile.submit(PHONE_A, round_id, text="las") == "closed"


def test_failed_transcription_and_silence_are_skipped(scenario):
    def broken(samples):
        raise RuntimeError("model nie działa")

    mobile = audience(transcribe=broken)
    mobile.state(PHONE_B)
    worker, result = collect_in_background(mobile, scenario.scene("intro"))
    round_id = mobile.state(PHONE_A)["round"]
    mobile.submit(PHONE_A, round_id, audio=wav_bytes(np.zeros(160)))
    mobile.submit(PHONE_B, round_id, text="   ")
    worker.join()

    assert result["answers"] == []


# Silnik: większość głosów z telefonów


class FakeAudience:
    def __init__(self, *rounds, phones=3):
        self._rounds = list(rounds)
        self._phones = phones

    def connected(self):
        return self._phones

    def collect(self, scene):
        return self._rounds.pop(0)


class FakePlayer:
    def play(self, clip):
        pass

    def loop(self, clip):
        pass


class FakeVoice:
    def __init__(self):
        self.lines = []

    def say(self, text):
        self.lines.append(text)


class SilentListener:
    def listen(self):
        raise AssertionError("z telefonami silnik nie słucha sali")


def run(scenario, audience_):
    voice = FakeVoice()
    visited = StoryEngine(scenario, FakePlayer(), SilentListener(), voice, KeywordIntentResolver(), audience=audience_).run()
    return visited, voice


def test_majority_of_phones_decides(scenario):
    answers = [Interpretation("jaskinia", ""), Interpretation("las", ""), Interpretation("jaskinia", "")]

    visited, voice = run(scenario, FakeAudience(answers))

    assert visited == ["intro", "jaskinia"]
    assert voice.lines == ["Do jaskini! Mam latarkę!"]


def test_single_answer_gets_personal_reply_from_model(scenario):
    visited, voice = run(scenario, FakeAudience([Interpretation("las", "Super, idziemy do lasu!")], phones=1))

    assert voice.lines == ["Super, idziemy do lasu!"]


def test_tie_and_silence_repeat_round_then_default(scenario):
    tie = [Interpretation("las", ""), Interpretation("jaskinia", "")]

    visited, voice = run(scenario, FakeAudience(tie, [], []))

    assert visited == ["intro", "las"]
    assert voice.lines[:2] == ["Hmm, nie usłyszałem. Las czy jaskinia?"] * 2
    assert voice.lines[-1].endswith("Do lasu! Trzymaj się blisko!")


def test_without_phones_engine_listens_to_the_hall(scenario):
    class Listener:
        def listen(self):
            return "do jaskini"

    engine = StoryEngine(scenario, FakePlayer(), Listener(), FakeVoice(), KeywordIntentResolver(), audience=FakeAudience(phones=0))

    assert engine.run() == ["intro", "jaskinia"]


# Serwer HTTP


@pytest.fixture
def server(scenario):
    mobile = audience(transcribe=lambda samples: "jaskinia")
    server = MobileServer(mobile, FAST)
    url = server.start().replace(server_host(server), "127.0.0.1")
    yield mobile, url
    server.stop()


def server_host(server):
    return server._server.public_url.split("//")[1].split(":")[0]


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def post(url, body, content_type):
    request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_server_serves_the_phone_app_and_manifest(server):
    _, url = server

    status, content_type, body = get(url)
    assert status == 200 and content_type.startswith("text/html")
    assert b"getUserMedia" in body and b"manifest.webmanifest" in body
    assert json.loads(get(url + "manifest.webmanifest")[2])["display"] == "standalone"
    assert b"Zeskanuj" in get(url + "qr")[2]


def test_server_round_trip_from_phone_to_engine(server, scenario):
    mobile, url = server
    result = {}
    worker = threading.Thread(target=lambda: result.update(answers=mobile.collect(scenario.scene("intro"))))
    worker.start()
    time.sleep(0.1)

    state = json.loads(get(f"{url}api/state?device={PHONE_A}")[2])
    status, answer = post(f"{url}api/answer?device={PHONE_A}&round={state['round']}", wav_bytes(np.zeros(1600)), "audio/wav")
    worker.join()

    assert status == 200 and answer == {"status": "ok"}
    assert [a.choice_id for a in result["answers"]] == ["jaskinia"]


def test_server_rejects_bad_requests(server):
    _, url = server

    assert post(f"{url}api/answer?device=x&round=1", b"{}", "application/json")[0] == 400  # zły identyfikator
    assert post(f"{url}api/answer?device={PHONE_A}&round=1", b"[1, 2]", "application/json")[0] == 400  # nie obiekt
    assert post(f"{url}api/answer?device={PHONE_A}&round=1", b"{nie json", "application/json")[0] == 400
    assert post(f"{url}api/answer?device={PHONE_A}&round=1", b'{"text": "las"}', "application/json") == (409, {"status": "closed"})
    with pytest.raises(urllib.error.HTTPError):
        get(url + "../../etc/passwd")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("api/answer?device=x&round=1", 400),  # zły identyfikator telefonu
        (f"api/answer?device={PHONE_A}&round=abc", 400),  # zły numer rundy
        (f"api/nie-ma?device={PHONE_A}&round=1", 404),  # nieznany adres
    ],
)
def test_rejected_upload_is_answered_only_after_its_body_was_read(server, path, expected):
    # Odpowiedź przed wczytaniem treści Windows kończy zerwaniem połączenia (WinError 10053) po stronie telefonu.
    _, url = server

    status, _ = post(url + path, bytes(MAX_UPLOAD_BYTES), "audio/wav")

    assert status == expected


def test_empty_and_oversized_uploads_get_413(server):
    _, url = server
    answer = f"api/answer?device={PHONE_A}&round=1"

    assert post(url + answer, b"", "audio/wav")[0] == 413
    host, port = url.split("//")[1].rstrip("/").split(":")
    connection = http.client.HTTPConnection(host, int(port), timeout=5)
    try:  # treści nie wysyłamy: serwer ma odmówić po samym nagłówku Content-Length
        connection.request("POST", "/" + answer, headers={"Content-Length": str(MAX_UPLOAD_BYTES + 1)})
        assert connection.getresponse().status == 413
    finally:
        connection.close()


def test_second_server_cannot_take_a_port_that_is_already_listening(server):
    # Zapomniany podgląd (python -m bajka.mobile) nie może po cichu dzielić portu z serwerem filmu (Windows + SO_REUSEADDR).
    _, url = server
    port = int(url.rstrip("/").rsplit(":", 1)[1])
    second = MobileServer(audience(), MobileSettings(https=False, host="127.0.0.1", port=port))

    with pytest.raises(OSError):
        second.start()


def test_https_uses_self_signed_certificate(tmp_path, monkeypatch, scenario):
    pytest.importorskip("cryptography")
    import ssl

    from bajka import mobile as mobile_module

    monkeypatch.setattr(mobile_module, "CERT_DIR", tmp_path)
    server = MobileServer(audience(), MobileSettings(https=True, host="127.0.0.1", port=0))
    url = server.start()
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # certyfikat samopodpisany, jak w telefonie po akceptacji ostrzeżenia
        local = url.replace(server_host(server), "127.0.0.1")
        with urllib.request.urlopen(local, timeout=5, context=context) as response:
            assert response.status == 200
        assert url.startswith("https://")
        assert (tmp_path / "bajka-mobile.crt").is_file()
    finally:
        server.stop()


def test_join_page_contains_address():
    assert "https://10.0.0.5:8443/" in join_page("https://10.0.0.5:8443/")

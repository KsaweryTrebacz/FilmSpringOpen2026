import http.client
import io
import json
import threading
import time
import wave
from pathlib import Path

import pytest

from bajka.engine import StoryEngine
from bajka.keywords import KeywordIntentResolver
from bajka.ports import Answer, Compositor, Cut, Player, Shot, Viewer, Voice
from bajka.scenario import load_scenario, parse_scenario
from bajka.web_player import (
    APP_DIR,
    WebEpisode,
    WebPlayerServer,
    WebPlayerSettings,
    branch_labels,
    story_labels,
)

FAST = WebPlayerSettings(port=0, grace_seconds=0.1)


def episode_for(scenario, transcribe=None, settings=FAST):
    return WebEpisode(scenario, transcribe, settings)


def in_thread(function, *args):
    result = {}
    thread = threading.Thread(target=lambda: result.setdefault("value", function(*args)), daemon=True)
    thread.start()
    return thread, result


def wait_for(episode, kind, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = episode.state()
        if state["kind"] == kind:
            return state
        time.sleep(0.01)
    raise AssertionError(f"strona nie dostała polecenia {kind}, ostatnie: {state}")


def wav(seconds=0.5):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        file.writeframes(b"\x00\x10" * int(16000 * seconds))
    return buffer.getvalue()


def test_episode_fulfils_player_voice_and_viewer_contracts(scenario):
    episode = episode_for(scenario)

    assert isinstance(episode, Player) and isinstance(episode, Voice) and isinstance(episode, Viewer)


def test_play_waits_until_the_page_reports_the_end_of_the_clip(scenario):
    episode = episode_for(scenario)
    thread, _ = in_thread(episode.play, scenario.scene("intro").clip)

    state = wait_for(episode, "play")
    assert state["clip"] == "media/0/intro.mp4" and state["background"] is None
    assert episode.event({"type": "done", "seq": state["seq"] - 1}) == "stale"
    thread.join(0.2)
    assert thread.is_alive()  # spóźnione zgłoszenie po poprzednim klipie nie kończy bieżącego

    assert episode.event({"type": "done", "seq": state["seq"]}) == "ok"
    thread.join(1)
    assert not thread.is_alive()


def test_idle_loop_is_the_background_of_lines_and_choice_windows(scenario):
    episode = episode_for(scenario)
    episode.loop(scenario.scene("intro").idle)  # nie czeka na stronę
    thread, _ = in_thread(episode.say, "Las czy jaskinia?")

    state = wait_for(episode, "say")
    assert state["text"] == "Las czy jaskinia?"
    assert state["background"] == {"clip": "media/1/intro_idle.mp4", "layers": [], "cut": {"transition": "ciecie", "seconds": 0.0}}
    episode.event({"type": "done", "seq": state["seq"]})
    thread.join(1)
    assert not thread.is_alive()


def test_shot_brings_layers_and_the_montage_cut_to_the_page(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["las"].update(layer="latarka.webm", slot="pomocnik")
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    episode = episode_for(scenario)
    shot = Shot(Path("film/las.mp4"), (Path("film/latarka.webm"),), Cut("przetarcie", 0.8, "Do lasu.", "model"))
    thread, _ = in_thread(episode.play_shot, shot)

    state = wait_for(episode, "play")
    assert isinstance(episode, Compositor)
    assert (state["clip"], state["layers"]) == ("media/3/las.mp4", ["media/2/latarka.webm"])
    assert state["cut"] == {"transition": "przetarcie", "seconds": 0.8}
    episode.event({"type": "done", "seq": state["seq"]})
    thread.join(1)


def test_button_choice_closes_the_window(scenario):
    episode = episode_for(scenario)
    thread, result = in_thread(episode.ask, scenario.scene("intro"), 30)

    state = wait_for(episode, "ask")
    assert state["question"] == scenario.scene("intro").question
    assert state["choices"] == [{"id": "las", "label": "Las", "icon": ""}, {"id": "jaskinia", "label": "Jaskinia", "icon": ""}]
    assert 29 < state["seconds_left"] <= 30
    assert episode.event({"type": "choice", "seq": state["seq"], "choice": "most"}) == "closed"
    assert episode.event({"type": "choice", "seq": state["seq"], "choice": "jaskinia"}) == "ok"
    thread.join(1)

    assert result["value"] == Answer(choice_id="jaskinia")
    assert episode.state()["kind"] == "idle"


def test_window_closes_after_the_countdown_while_the_page_is_open(scenario):
    episode = episode_for(scenario)
    thread, result = in_thread(episode.ask, scenario.scene("intro"), 0.2)

    while thread.is_alive():
        episode.state()  # strona odpytuje co 250 ms
        time.sleep(0.02)

    assert result["value"] == Answer()


def test_countdown_stands_still_while_nobody_watches(scenario):
    episode = episode_for(scenario)
    thread, result = in_thread(episode.ask, scenario.scene("intro"), 0.1)

    thread.join(0.6)  # karta zamknięta: nikt nie pyta o stan
    assert thread.is_alive()

    state = wait_for(episode, "ask")
    episode.event({"type": "timeout", "seq": state["seq"]})  # odliczanie na stronie doszło do zera
    thread.join(1)
    assert result["value"] == Answer()


def test_spoken_answer_is_transcribed_and_returned(scenario):
    heard = []

    def transcribe(samples):
        heard.append(len(samples))
        return "  do   lasu "

    episode = episode_for(scenario, transcribe)
    thread, result = in_thread(episode.ask, scenario.scene("intro"), 30)
    state = wait_for(episode, "ask")

    assert state["voice"] is True
    assert episode.submit_voice(state["seq"], wav()) == ("ok", "do lasu")
    thread.join(1)
    assert result["value"] == Answer(transcript="do lasu")
    assert heard == [8000]
    assert episode.submit_voice(state["seq"], wav()) == ("closed", "")  # okno już zamknięte


def test_noise_keeps_the_window_open_and_bad_audio_is_ignored(scenario):
    episode = episode_for(scenario, transcribe=lambda samples: "Napisy stworzone przez społeczność Amara.org")
    thread, result = in_thread(episode.ask, scenario.scene("intro"), 30)
    state = wait_for(episode, "ask")

    assert episode.submit_voice(state["seq"], wav()) == ("empty", "")  # znana halucynacja Whispera to cisza
    assert episode.submit_voice(state["seq"], b"to nie jest wav") == ("empty", "")
    assert thread.is_alive()
    episode.event({"type": "choice", "seq": state["seq"], "choice": "las"})
    thread.join(1)
    assert result["value"] == Answer(choice_id="las")


def test_speech_event_submits_transcript_answer(scenario):
    episode = episode_for(scenario)
    thread, result = in_thread(episode.ask, scenario.scene("intro"), 30)
    state = wait_for(episode, "ask")

    assert episode.event({"type": "speech", "seq": state["seq"], "transcript": "do lasu"}) == "ok"
    thread.join(1)
    assert result["value"] == Answer(transcript="do lasu")


def test_without_transcriber_voice_is_off(scenario):
    episode = episode_for(scenario)
    thread, _ = in_thread(episode.ask, scenario.scene("intro"), 30)
    state = wait_for(episode, "ask")

    assert state["voice"] is False
    assert episode.submit_voice(state["seq"], wav()) == ("off", "")
    episode.close()
    thread.join(1)


def test_closing_the_episode_stops_the_engine_and_wakes_every_wait(scenario):
    episode = episode_for(scenario)
    stopped = []
    episode.on_stop = lambda: stopped.append(True)
    thread, _ = in_thread(episode.play, scenario.scene("intro").clip)
    wait_for(episode, "play")

    assert episode.event({"type": "stop"}) == "ok"
    thread.join(1)

    assert not thread.is_alive() and stopped == [True]
    assert episode.state()["kind"] == "closed"
    episode.say("już nikt nie słucha")  # po zamknięciu nic nie czeka na stronę
    assert episode.ask(scenario.scene("intro"), 30) == Answer()
    assert episode.finish(["intro"]) is False


def test_end_screen_can_restart_the_episode(scenario):
    episode = episode_for(scenario)
    thread, result = in_thread(episode.finish, ["intro", "las"])

    state = wait_for(episode, "end")
    assert state["path"] == ["Las"]  # nazwy wyborów, nie identyfikatory scen
    assert episode.event({"type": "restart"}) == "ok"
    thread.join(1)
    assert result["value"] is True


def test_end_screen_lists_only_choices_that_changed_the_story():
    scenario = load_scenario(Path(__file__).resolve().parents[1] / "scenarios" / "klub_ciekawskich.yaml")
    visited = ["powitanie", "kuferek", "most", "most_chwiejny", "wiaterek", "pomocnik", "laka", "kwiatek", "swieto",
               "koniec_piosenka"]  # fmt: skip
    decisions = [("powitanie", "pukanie"), ("kuferek", "most"), ("most", "niebieska"), ("wiaterek", "spokojnie"),
                 ("pomocnik", "mapa"), ("laka", "trzy"), ("kwiatek", "stokrotka"), ("swieto", "piosenka")]  # fmt: skip

    assert story_labels(scenario, decisions) == [
        "Tęczowy Mostek", "Niebieska deska", "Udało się!", "Trzy", "Stokrotka", "Piosenka o kwiatkach",
    ]  # bez „Puk, puk!” i mapy: wszystkie opcje prowadzą tam samo i nic nie nakładają
    assert branch_labels(scenario, visited) == ["Tęczowy Mostek", "Niebieska deska", "Udało się!", "Trzy",
                                                "Piosenka o kwiatkach"]  # fmt: skip


class FakePage:
    """Strona odtwarzacza w teście: kończy klipy i kwestie od razu, a w oknach wyboru klika kolejne opcje."""

    def __init__(self, episode, picks):
        self._episode, self._picks, self.seen = episode, list(picks), []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        handled = None
        while True:
            state = self._episode.state()
            if state["kind"] in ("closed", "end"):
                self.seen.append(state["kind"])
                return
            if state["seq"] != handled and state["kind"] in ("play", "say", "ask"):
                handled = state["seq"]
                self.seen.append(state.get("clip") or state.get("text") or state["question"])
                if state["kind"] == "ask":
                    pick = self._picks.pop(0)
                    self._episode.event({"type": "choice", "seq": state["seq"], "choice": pick})
                else:
                    self._episode.event({"type": "done", "seq": state["seq"]})
            time.sleep(0.005)


def test_whole_episode_runs_in_the_page(scenario_dict):
    scenario_dict["scenes"]["intro"]["choices"]["jaskinia"]["reaction"] = "reakcja_jaskinia.mp4"
    scenario = parse_scenario(scenario_dict, base_dir=Path("film"))
    episode = episode_for(scenario)
    page = FakePage(episode, ["jaskinia"])

    visited = StoryEngine(scenario, episode, episode, episode, KeywordIntentResolver()).run()
    thread, _ = in_thread(episode.finish, visited)
    thread.join(1)
    episode.close()

    assert visited == ["intro", "jaskinia"]
    assert page.seen == ["media/0/intro.mp4", scenario.scene("intro").question, "media/2/reakcja_jaskinia.mp4",
                         "media/4/jaskinia.mp4", "end"]  # fmt: skip


# Serwer HTTP


@pytest.fixture
def server(tmp_path, scenario_dict):
    (tmp_path / "intro.mp4").write_bytes(bytes(range(256)) * 4)
    scenario = parse_scenario(scenario_dict, base_dir=tmp_path)
    episode = episode_for(scenario)
    server = WebPlayerServer(episode, FAST)
    url = server.start()
    yield server, int(url.rsplit(":", 1)[1].strip("/"))
    episode.close()
    server.stop()


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response, data


def test_page_and_state_are_served(server):
    _, port = server

    page, html = request(port, "GET", "/")
    _, data = request(port, "GET", "/api/state")

    assert page.status == 200 and b'id="choice"' in html
    assert json.loads(data)["title"] == "Bajka interaktywna"


def test_clips_are_served_with_byte_ranges_for_the_video_element(server):
    _, port = server

    whole, data = request(port, "GET", "/media/0/intro.mp4")
    part, chunk = request(port, "GET", "/media/0/intro.mp4", headers={"Range": "bytes=10-19"})
    tail, last = request(port, "GET", "/media/0/intro.mp4", headers={"Range": "bytes=-4"})
    wrong, _ = request(port, "GET", "/media/0/intro.mp4", headers={"Range": "bytes=5000-"})

    assert whole.status == 200 and len(data) == 1024 and whole.getheader("Content-Type") == "video/mp4"
    assert part.status == 206 and chunk == bytes(range(10, 20))
    assert part.getheader("Content-Range") == "bytes 10-19/1024"
    assert tail.status == 206 and last == bytes([252, 253, 254, 255])
    assert wrong.status == 416


@pytest.mark.parametrize("path", ["/media/9/intro.mp4", "/media/0/../../etc/passwd", "/media/1/intro_idle.mp4"])
def test_only_existing_clips_of_the_scenario_are_served(server, path):
    _, port = server

    response, _ = request(port, "GET", path)

    assert response.status == 404


def test_events_need_json_and_voice_needs_wav(server):
    _, port = server

    form, _ = request(port, "POST", "/api/event", body=b'{"type":"stop"}', headers={"Content-Type": "text/plain"})
    voice, _ = request(port, "POST", "/api/voice?seq=1", body=b"x", headers={"Content-Type": "text/plain"})
    stale, data = request(port, "POST", "/api/event", body=b'{"type":"done","seq":99}',
                          headers={"Content-Type": "application/json"})  # fmt: skip

    assert form.status == 415 and voice.status == 415
    assert stale.status == 409 and json.loads(data) == {"status": "stale"}


def test_foreign_host_name_is_refused(server):
    _, port = server

    response, _ = request(port, "GET", "/api/state", headers={"Host": "zly.example:8080"})

    assert response.status == 403


def test_settings_read_from_env():
    settings = WebPlayerSettings.from_env({"BAJKA_WEB_PORT": "9000", "BAJKA_WEB_HOST": "0.0.0.0"})

    assert settings.port == 9000 and settings.host == "0.0.0.0"
    assert WebPlayerSettings.from_env({}) == WebPlayerSettings()


def test_player_page_works_offline_and_has_the_choice_window():
    page = (APP_DIR / "index.html").read_text(encoding="utf-8")

    for section in ('id="start"', 'id="choice"', 'id="caption"', 'id="end"', 'id="timer"', "speechSynthesis",
                    'id="deckA"', 'id="deckB"', 'id="veil"', "przetarcie", "zaciemnienie"):
        assert section in page
    for external in ("http://", "https://", "//cdn"):
        assert external not in page  # bez internetu: żadnych zewnętrznych plików

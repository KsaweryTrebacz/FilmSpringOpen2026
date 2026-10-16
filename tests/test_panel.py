import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from bajka.config import ConfigError
from bajka.panel import PanelServer, PanelSettings, PanelState, scenario_graph
from bajka.ports import Pulse, ShowObserver
from bajka.pulse import PulseSettings, SimulatedPulse
from bajka.scenario import parse_scenario

# Drzewo scen


def test_graph_lists_scenes_by_distance_from_start_and_labelled_edges(scenario):
    graph = scenario_graph(scenario)

    assert graph["start"] == "intro"
    assert graph["mood"] == ""
    assert graph["scenes"] == [
        {"id": "intro", "depth": 0, "question": "Idziemy do mrocznego lasu czy do jaskini?", "ending": False,
         "variants": []},
        {"id": "las", "depth": 1, "question": "", "ending": True, "variants": []},
        {"id": "jaskinia", "depth": 1, "question": "", "ending": True, "variants": []},
    ]  # fmt: skip
    assert graph["edges"] == [
        {"from": "intro", "to": "las", "choice": "las", "label": "Las"},
        {"from": "intro", "to": "jaskinia", "choice": "jaskinia", "label": "Jaskinia"},
    ]


def test_graph_shows_versions_and_puts_unreachable_scenes_last(scenario_dict):
    scenario_dict["mood"] = "spokojny"
    scenario_dict["scenes"]["las"]["variants"] = {"spokojna": "las_spokojna.mp4"}
    scenario_dict["scenes"]["sekret"] = {"clip": "sekret.mp4"}

    graph = scenario_graph(parse_scenario(scenario_dict, base_dir=Path("film")))

    scenes = {scene["id"]: scene for scene in graph["scenes"]}
    assert graph["mood"] == "spokojny"
    assert scenes["las"]["variants"] == ["spokojna"]
    assert scenes["sekret"]["depth"] == 2


# Stan panelu ze zdarzeń silnika


def texts(snapshot):
    return [entry["text"] for entry in snapshot["log"]]


def test_state_fulfils_observer_contract_and_starts_empty(scenario):
    state = PanelState(scenario, PulseSettings())

    assert isinstance(state, ShowObserver)
    snapshot = state.snapshot()
    assert snapshot["scene"] is None
    assert snapshot["path"] == [] and snapshot["decisions"] == [] and snapshot["votes"] is None
    assert snapshot["pulse"]["history"] == [] and snapshot["pulse"]["baseline"] is None


def test_scenes_and_decisions_build_the_path_and_the_log(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("scena", {"scene": "intro", "clip": "intro.mp4", "variant": "zwykla"})
    state.event("decyzja", {"scene": "intro", "choice": "las", "label": "Las", "how": "wiekszosc"})
    state.event("scena", {"scene": "las", "clip": "las_spokojna.mp4", "variant": "spokojna"})

    snapshot = state.snapshot()
    assert snapshot["scene"] == "las"
    assert snapshot["path"] == [{"scene": "intro", "variant": "zwykla"}, {"scene": "las", "variant": "spokojna"}]
    assert snapshot["decisions"] == [{"scene": "intro", "choice": "las", "label": "Las", "how": "wiekszosc"}]
    assert texts(snapshot) == [
        "Scena intro",
        "Decyzja w scenie intro: Las (większość głosów z telefonów)",
        "Scena las w wersji spokojnej",
    ]


def test_votes_are_kept_and_described_with_option_labels(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("glosy", {"scene": "intro", "source": "telefony", "counts": {"las": 2, "jaskinia": 1}})

    snapshot = state.snapshot()
    assert snapshot["votes"] == {"scene": "intro", "source": "telefony", "counts": {"las": 2, "jaskinia": 1}}
    assert texts(snapshot) == ["Głosy (telefony): Las 2, Jaskinia 1"]


def test_pulse_samples_baseline_and_hall_state(scenario):
    clock = iter([10.0, 11.0, 12.0]).__next__
    state = PanelState(scenario, PulseSettings(), clock=clock)

    state.record_pulse(Pulse(bpm=90.0, viewers=30))
    state.event("odniesienie", {"bpm": 90.0})
    state.record_pulse(Pulse(bpm=110.0, viewers=30))

    pulse = state.snapshot()["pulse"]
    assert pulse["history"] == [[1.0, 90.0], [2.0, 110.0]]
    assert pulse["bpm"] == 110.0 and pulse["viewers"] == 30
    assert pulse["baseline"] == 90.0
    assert pulse["excited"] == pytest.approx(103.5) and pulse["bored"] == pytest.approx(87.3)
    assert pulse["state"] == "pobudzona"
    assert texts(state.snapshot()) == ["Punkt odniesienia tętna sali: 90"]


def test_version_choice_is_explained_in_one_sentence(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("wersja", {"scene": "las", "bpm": 110.0, "baseline": 90.0, "state": "pobudzona", "variant": "spokojna"})

    assert texts(state.snapshot()) == ["Tętno sali 110 (odniesienie 90), sala pobudzona: scena las w wersji spokojnej"]


def test_history_and_log_keep_only_the_latest_entries(scenario):
    state = PanelState(scenario, PulseSettings())

    for second in range(150):
        state.record_pulse(Pulse(bpm=90.0 + second % 3, viewers=30))
        state.event("scena", {"scene": "intro", "clip": "intro.mp4", "variant": "zwykla"})

    snapshot = state.snapshot()
    assert len(snapshot["pulse"]["history"]) == 120
    assert len(snapshot["log"]) == 20


def test_unknown_event_is_ignored(scenario):
    state = PanelState(scenario, PulseSettings())

    state.event("fajerwerki", {"ile": 3})

    assert state.snapshot()["log"] == []


# Ustawienia


def test_settings_from_env():
    assert PanelSettings.from_env({}) == PanelSettings(host="127.0.0.1", port=8090)
    assert PanelSettings.from_env({"BAJKA_PANEL_HOST": "0.0.0.0", "BAJKA_PANEL_PORT": "9000"}) == PanelSettings(
        host="0.0.0.0", port=9000
    )
    with pytest.raises(ConfigError, match="BAJKA_PANEL_PORT"):
        PanelSettings.from_env({"BAJKA_PANEL_PORT": "osiem"})


# Serwer


@pytest.fixture
def server(scenario):
    simulator = SimulatedPulse(PulseSettings())
    panel = PanelServer(PanelState(scenario, PulseSettings()), scenario_graph(scenario), simulator,
                        PanelSettings(port=0), sample_every_s=0.05)  # fmt: skip
    url = panel.start()
    yield panel, url, simulator
    panel.stop()


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read())


def post(url, body):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        with error:  # odpowiedź z błędem też trzyma połączenie: zamykamy ją
            return error.code, json.loads(error.read())


def test_server_serves_graph_and_state_with_the_simulator_target(server, scenario):
    _, url, _ = server

    assert url.startswith("http://") and url.endswith("/")
    assert get(url + "graph") == (200, scenario_graph(scenario))
    status, state = get(url + "state")
    assert status == 200
    assert state["scene"] is None
    assert state["pulse"]["target"] == 90.0


def test_server_samples_the_pulse_in_the_background(server):
    _, url, _ = server
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and not get(url + "state")[1]["pulse"]["history"]:
        time.sleep(0.05)

    assert get(url + "state")[1]["pulse"]["history"]


@pytest.mark.parametrize(
    ("body", "target"),
    [({"target": 120}, 120.0), ({"preset": "nudzi-sie"}, 85.0), ({"target": "130"}, 130.0)],
)
def test_pulse_commands_set_the_simulator(server, body, target):
    _, url, simulator = server

    assert post(url + "pulse", body) == (200, {"ok": True, "target": target})
    assert simulator.target == target


def test_demo_script_command_starts_the_scripted_run(server):
    _, url, _ = server

    status, answer = post(url + "pulse", {"script": "demo"})

    assert status == 200 and answer["ok"] is True


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ({"preset": "szaleje"}, "nieznany stan sali"),
        ({"target": "dużo"}, "liczbą"),
        ({}, "nieznane polecenie"),
        (b"nie json", "obiektu JSON"),
    ],
)
def test_bad_pulse_commands_get_400(server, body, error):
    _, url, _ = server

    status, answer = post(url + "pulse", body)

    assert status == 400
    assert error in answer["error"]


def test_panel_page_works_offline_and_has_all_sections(server):
    _, url, _ = server

    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/html")
        page = response.read().decode("utf-8")

    assert "<title>Film, który czuje salę" in page
    sections = ('id="tree-svg"', 'id="chart"', 'id="votes"', 'id="log"', 'id="slider"', 'data-preset="ekscytuje-sie"')
    for element in sections:
        assert element in page
    assert "<link" not in page and 'src="http' not in page  # bez internetu na sali: żadnych zewnętrznych plików


def test_unknown_page_is_404(server):
    _, url, _ = server

    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(url + "nie-ma", timeout=5)
    with caught.value as error:
        assert error.code == 404


def test_pulse_commands_without_simulator_get_409(scenario):
    panel = PanelServer(PanelState(scenario, PulseSettings()), scenario_graph(scenario), None, PanelSettings(port=0))
    url = panel.start()
    try:
        status, answer = post(url + "pulse", {"target": 100})
    finally:
        panel.stop()

    assert status == 409
    assert "symulator tętna jest wyłączony" in answer["error"]

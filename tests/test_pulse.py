import math
import random

import pytest

from bajka.config import ConfigError
from bajka.ports import AudiencePulse, Pulse
from bajka.pulse import (
    BORED,
    DEMO_SCRIPT,
    EXCITED,
    NORMAL,
    PRESETS,
    PulseSettings,
    SimulatedPulse,
    hall_state,
    pick_variant,
    script_value,
)


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class NoJitter:
    def uniform(self, low, high):
        return 0.0


def make_pulse(**settings):
    clock = FakeClock()
    return SimulatedPulse(PulseSettings(**settings), clock=clock, rng=NoJitter()), clock


def test_simulated_pulse_fulfils_contract_and_starts_at_start_bpm():
    pulse, _ = make_pulse(start_bpm=88.0, viewers=12)

    assert isinstance(pulse, AudiencePulse)
    assert pulse.read() == Pulse(bpm=88.0, viewers=12)


def test_pulse_approaches_target_smoothly():
    pulse, clock = make_pulse(start_bpm=90.0)
    pulse.set_target(120.0)

    clock.now += 5.0  # jedna stała czasowa: ok. 63% drogi
    assert pulse.read().bpm == pytest.approx(90.0 + 30.0 * (1 - math.exp(-1)), abs=0.05)

    clock.now += 60.0
    assert pulse.read().bpm == pytest.approx(120.0, abs=0.05)


def test_target_is_kept_within_human_range():
    pulse, _ = make_pulse()

    pulse.set_target(500)
    assert pulse.target == 160.0
    pulse.set_target(10)
    assert pulse.target == 60.0


def test_presets_set_the_target():
    pulse, _ = make_pulse()

    pulse.preset("ekscytuje-sie")

    assert pulse.target == PRESETS["ekscytuje-sie"] == 115.0


def test_unknown_preset_is_refused():
    pulse, _ = make_pulse()

    with pytest.raises(ValueError, match="nieznany stan sali"):
        pulse.preset("szaleje")


def test_script_moves_the_target_over_time_until_set_by_hand():
    pulse, clock = make_pulse()
    pulse.play_script(((0, 90.0), (10, 110.0)))

    clock.now += 5.0
    pulse.read()
    assert pulse.target == pytest.approx(100.0)

    pulse.set_target(95.0)  # ręczne ustawienie przerywa przebieg
    clock.now += 20.0
    pulse.read()
    assert pulse.target == 95.0


def test_script_value_interpolates_and_holds_the_ends():
    script = ((0, 90.0), (10, 110.0), (20, 100.0))

    assert script_value(script, -5) == 90.0
    assert script_value(script, 5) == pytest.approx(100.0)
    assert script_value(script, 15) == pytest.approx(105.0)
    assert script_value(script, 99) == 100.0


def test_demo_script_goes_calm_excited_calm():
    values = [bpm for _, bpm in DEMO_SCRIPT]

    assert values[0] < max(values) and values[-1] < max(values)


def test_jitter_stays_small():
    pulse = SimulatedPulse(PulseSettings(start_bpm=90.0), clock=FakeClock(), rng=random.Random(7))

    readings = [pulse.read().bpm for _ in range(50)]

    assert all(88.5 <= bpm <= 91.5 for bpm in readings)
    assert len(set(readings)) > 1


@pytest.mark.parametrize(
    ("bpm", "state"),
    [(115.0, EXCITED), (114.9, NORMAL), (100.0, NORMAL), (97.1, NORMAL), (97.0, BORED), (80.0, BORED)],
)
def test_hall_state_compares_pulse_with_baseline(bpm, state):
    assert hall_state(bpm, baseline=100.0, settings=PulseSettings()) == state


def test_settings_from_env_defaults_and_overrides():
    assert PulseSettings.from_env({}) == PulseSettings(viewers=30, start_bpm=90.0, excited=1.15, bored=0.97)

    env = {"BAJKA_PULSE_VIEWERS": "50", "BAJKA_PULSE_START_BPM": "85", "BAJKA_PULSE_EXCITED": "1.2",
           "BAJKA_PULSE_BORED": "0.9"}  # fmt: skip
    assert PulseSettings.from_env(env) == PulseSettings(viewers=50, start_bpm=85.0, excited=1.2, bored=0.9)


@pytest.mark.parametrize(("excited", "bored"), [("0.9", "0.97"), ("1.15", "1.05")])
def test_thresholds_must_lie_on_both_sides_of_baseline(excited, bored):
    with pytest.raises(ConfigError, match="BAJKA_PULSE_EXCITED"):
        PulseSettings.from_env({"BAJKA_PULSE_EXCITED": excited, "BAJKA_PULSE_BORED": bored})


@pytest.mark.parametrize(
    ("mood", "state", "variant"),
    [
        ("spokojny", EXCITED, "spokojna"),
        ("spokojny", NORMAL, None),
        ("spokojny", BORED, None),
        ("zywy", BORED, "zywa"),
        ("zywy", NORMAL, None),
        ("zywy", EXCITED, None),
        ("", EXCITED, None),
    ],
)
def test_pick_variant_brings_the_hall_towards_the_mood_of_the_film(mood, state, variant):
    assert pick_variant(mood, state) == variant

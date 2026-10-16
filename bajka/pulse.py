"""Tętno sali. Na pokazie pochodzi z symulatora sterowanego z panelu: bez zegarków i bez danych prawdziwych osób.

Wizja: aplikacja mobilna czyta tętno z zegarków widzów i wysyła do komputera z filmem tylko średnią całej sali.
Moduł spełnia kontrakt `bajka.ports.AudiencePulse`; `hall_state` porównuje tętno z punktem odniesienia.
Podgląd symulatora bez reszty aplikacji: python -m bajka.pulse [--script] [--seconds 30]
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from bajka.config import ConfigError, get_float, get_int, load_env
from bajka.ports import Pulse

EXCITED = "pobudzona"
NORMAL = "w normie"
BORED = "znudzona"

MIN_BPM, MAX_BPM = 60.0, 160.0
PRESETS = {"spokojna": 90.0, "ekscytuje-sie": 115.0, "nudzi-sie": 85.0}
# Przebieg demo: (sekunda od startu, tętno) — spokojny początek, ekscytacja, uspokojenie.
DEMO_SCRIPT: tuple[tuple[float, float], ...] = ((0, 90.0), (20, 90.0), (35, 118.0), (75, 118.0), (95, 92.0))

TIME_CONSTANT_S = 5.0  # po tylu sekundach tętno pokonuje ok. 63% drogi do wartości docelowej
JITTER_BPM = 1.5


@dataclass(frozen=True)
class PulseSettings:
    viewers: int = 30  # ilu widzów „ma zegarek” w symulacji
    start_bpm: float = 90.0
    excited: float = 1.15  # sala pobudzona: tętno co najmniej 15% powyżej punktu odniesienia
    bored: float = 0.97  # sala znudzona: tętno co najmniej 3% poniżej

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> PulseSettings:
        settings = cls(
            viewers=get_int(env, "BAJKA_PULSE_VIEWERS", cls.viewers),
            start_bpm=get_float(env, "BAJKA_PULSE_START_BPM", cls.start_bpm),
            excited=get_float(env, "BAJKA_PULSE_EXCITED", cls.excited),
            bored=get_float(env, "BAJKA_PULSE_BORED", cls.bored),
        )
        if not settings.bored < 1.0 < settings.excited:
            raise ConfigError("BAJKA_PULSE_EXCITED musi być większe od 1, a BAJKA_PULSE_BORED mniejsze od 1")
        return settings


def hall_state(bpm: float, baseline: float, settings: PulseSettings) -> str:
    """Stan sali względem punktu odniesienia (tętna tuż po pierwszej scenie)."""
    if bpm >= baseline * settings.excited:
        return EXCITED
    if bpm <= baseline * settings.bored:
        return BORED
    return NORMAL


def script_value(script: Sequence[tuple[float, float]], seconds: float) -> float:
    """Tętno z przebiegu w danej sekundzie: liniowo między punktami, poza nimi wartość skrajna."""
    if seconds <= script[0][0]:
        return script[0][1]
    for (t0, v0), (t1, v1) in zip(script, script[1:]):
        if seconds <= t1:
            return v0 + (v1 - v0) * (seconds - t0) / (t1 - t0)
    return script[-1][1]


class SimulatedPulse:
    """Symulowana sala: tętno płynnie dochodzi do wartości docelowej i lekko drga."""

    def __init__(
        self,
        settings: PulseSettings,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._rng = rng or random.Random()
        self._lock = threading.Lock()  # panel ustawia cel z wątku serwera, silnik czyta z wątku bajki
        self._bpm = settings.start_bpm
        self._target = settings.start_bpm
        self._updated = clock()
        self._script: tuple[tuple[float, float], ...] | None = None
        self._script_started = 0.0

    @property
    def target(self) -> float:
        with self._lock:
            return self._target

    def set_target(self, bpm: float) -> None:
        with self._lock:
            self._advance()
            self._script = None
            self._target = min(MAX_BPM, max(MIN_BPM, float(bpm)))

    def preset(self, name: str) -> None:
        if name not in PRESETS:
            raise ValueError(f"nieznany stan sali {name!r}, dostępne: {', '.join(PRESETS)}")
        self.set_target(PRESETS[name])

    def play_script(self, script: Sequence[tuple[float, float]] = DEMO_SCRIPT) -> None:
        with self._lock:
            self._advance()
            self._script = tuple(script)
            self._script_started = self._clock()

    def read(self) -> Pulse:
        with self._lock:
            self._advance()
            bpm = self._bpm + self._rng.uniform(-JITTER_BPM, JITTER_BPM)
        return Pulse(bpm=round(bpm, 1), viewers=self._settings.viewers)

    def _advance(self) -> None:
        now = self._clock()
        if self._script is not None:
            self._target = script_value(self._script, now - self._script_started)
        elapsed = max(0.0, now - self._updated)
        self._bpm += (self._target - self._bpm) * (1 - math.exp(-elapsed / TIME_CONSTANT_S))
        self._updated = now


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.pulse", description="Podgląd symulatora tętna sali.")
    parser.add_argument("--script", action="store_true", help="przebieg demo: spokojnie, ekscytacja, uspokojenie")
    parser.add_argument("--seconds", type=int, default=30, help="jak długo pokazywać odczyty (co sekundę)")
    args = parser.parse_args(argv)
    try:
        settings = PulseSettings.from_env(load_env())
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    pulse = SimulatedPulse(settings)
    if args.script:
        pulse.play_script()
    baseline = pulse.read().bpm
    for _ in range(args.seconds):
        reading = pulse.read()
        state = hall_state(reading.bpm, baseline, settings)
        line = f"tętno {reading.bpm:5.1f} (cel {pulse.target:5.1f}), widzów {reading.viewers}, sala: {state}"
        print(line, flush=True)
        time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

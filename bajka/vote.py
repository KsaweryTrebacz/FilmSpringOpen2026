"""Krzykomierz: głosowanie okrzykiem widowni w kinie (sceny `vote` w scenariuszu).

Gdy na sali siedzi wiele dzieci, rozpoznawanie słów z gwaru jest zawodne. Dlatego w scenach `vote`
bohaterka wzywa po kolei do każdej opcji („Kto za mostkiem? Krzyczymy: MOSTEK!”), a krzykomierz
porównuje głośność okrzyków. Moduł spełnia kontrakt `bajka.ports.ShoutMeter`.
Kalibracja na sali: python -m bajka.vote
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from bajka.config import ConfigError, get_float, load_env
from bajka.local_stt import FRAME_MS, loudness, microphone_frames

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoteSettings:
    shout_seconds: float = 2.5  # jak długo mierzymy okrzyk po każdym wezwaniu
    calibrate_seconds: float = 1.0  # pomiar gwaru sali przed rundą
    min_ratio: float = 1.8  # okrzyk musi być tyle razy głośniejszy od gwaru sali
    min_level: float = 700.0  # i co najmniej tak głośny (RMS próbek 16-bit), żeby cisza nie wygrała
    margin: float = 0.15  # zwycięzca musi być o tyle głośniejszy od drugiej opcji, inaczej remis

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> VoteSettings:
        return cls(
            shout_seconds=get_float(env, "BAJKA_VOTE_SECONDS", cls.shout_seconds),
            calibrate_seconds=get_float(env, "BAJKA_VOTE_CALIBRATE_SECONDS", cls.calibrate_seconds),
            min_ratio=get_float(env, "BAJKA_VOTE_MIN_RATIO", cls.min_ratio),
            min_level=get_float(env, "BAJKA_VOTE_MIN_LEVEL", cls.min_level),
            margin=get_float(env, "BAJKA_VOTE_MARGIN", cls.margin),
        )


def pick_winner(levels: Mapping[str, float], hall: float, settings: VoteSettings) -> str | None:
    """Najgłośniejsza opcja, jeśli wyraźnie przebiła gwar sali i drugą opcję; inaczej None."""
    loud_enough = max(settings.min_level, hall * settings.min_ratio)
    ranked = sorted(levels.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] < loud_enough:
        return None
    if len(ranked) > 1 and ranked[1][1] * (1 + settings.margin) > ranked[0][1]:
        return None  # remis — bohaterka poprosi o jeszcze jedną rundę
    return ranked[0][0]


def shout_level(frames: Iterable[np.ndarray], seconds: float, frame_ms: int = FRAME_MS) -> float:
    """Głośność okrzyku: 75. percentyl głośności ramek, więc jedno stuknięcie nie wygrywa głosowania."""
    levels = []
    for frame in frames:
        levels.append(loudness(frame))
        if len(levels) * frame_ms >= seconds * 1000:
            break
    return float(np.percentile(levels, 75)) if levels else 0.0


class MicrophoneMeter:
    def __init__(
        self,
        settings: VoteSettings,
        frames: Callable[[], Iterable[np.ndarray]] = microphone_frames,
    ) -> None:
        self._settings = settings
        self._frames = frames
        self._hall = 0.0

    def _record(self, seconds: float) -> float:
        frames = self._frames()
        try:
            return shout_level(frames, seconds)
        finally:
            close = getattr(frames, "close", None)
            if close is not None:
                close()  # mikrofon zamknięty, gdy bohaterka mówi

    @property
    def hall(self) -> float:
        """Gwar sali z ostatniej kalibracji."""
        return self._hall

    def calibrate(self) -> None:
        self._hall = self._record(self._settings.calibrate_seconds)
        log.info("Gwar sali: %.0f", self._hall)

    def measure(self) -> float:
        return self._record(self._settings.shout_seconds)

    def winner(self, levels: dict[str, float]) -> str | None:
        return pick_winner(levels, self._hall, self._settings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.vote", description="Kalibracja krzykomierza na sali: gwar, okrzyk i podpowiedź progów."
    )
    parser.add_argument("--rounds", type=int, default=2, help="ile okrzyków zmierzyć (domyślnie 2)")
    args = parser.parse_args(argv)
    try:
        settings = VoteSettings.from_env(load_env())
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    meter = MicrophoneMeter(settings)
    try:
        print("Cisza na sali… mierzę gwar.", flush=True)
        meter.calibrate()
        hall = meter.hall
        print(f"Gwar sali: {hall:.0f}")
        shouts = []
        for number in range(1, args.rounds + 1):
            print(f"Okrzyk {number}: krzyczcie teraz!", flush=True)
            shouts.append(meter.measure())
            print(f"  głośność: {shouts[-1]:.0f}")
            time.sleep(1.0)
    except Exception as exc:  # demo ma pokazać każdy błąd mikrofonu, a nie wywrócić się
        print(f"Błąd mikrofonu: {exc}", file=sys.stderr)
        return 1
    quietest = min(shouts) if shouts else 0.0
    print(f"Próg teraz: {max(settings.min_level, hall * settings.min_ratio):.0f} (BAJKA_VOTE_MIN_LEVEL, BAJKA_VOTE_MIN_RATIO)")
    if quietest and hall:
        print(f"Podpowiedź: BAJKA_VOTE_MIN_LEVEL={quietest * 0.5:.0f}, BAJKA_VOTE_MIN_RATIO={max(1.2, quietest / hall / 2):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

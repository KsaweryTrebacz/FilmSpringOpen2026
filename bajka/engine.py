"""Silnik bajki: odtwarza sceny, słucha dziecka (albo całej widowni) i wybiera kolejny klip.

Sceny z pytaniem otwartym (`kind: open`) rysują pomysł dziecka na żywo: Imaginer → Illustrator → Animator.
Sceny generowane (`kind: generated`) rysujemy w tle zawczasu: gdy pada pytanie, które może do nich prowadzić.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from bajka.ports import (
    Animator,
    Audience,
    Illustrator,
    Imaginer,
    IntentResolver,
    Interpretation,
    Listener,
    Player,
    ShoutMeter,
    Vision,
    Voice,
)
from bajka.scenario import Choice, Scenario, Scene, fill_prompt

log = logging.getLogger(__name__)

DEFAULT_FALLBACK = "Dobrze, to ja wybiorę!"
FALLBACK_VISION_LINE = "Zobacz, co mam w wyobraźni!"


class _Stopped(Exception):
    """Okno zostało zamknięte (Esc): bajka kończy się natychmiast, bez dalszych scen i kwestii."""


class StoryEngine:
    """Prowadzi bajkę od sceny startowej do zakończenia.

    Błędy mikrofonu, LLM i TTS są tu logowane i obsłużone, żeby bajka nigdy nie stanęła.
    """

    def __init__(
        self,
        scenario: Scenario,
        player: Player,
        listener: Listener,
        voice: Voice,
        resolver: IntentResolver,
        max_reprompts: int = 2,
        meter: ShoutMeter | None = None,
        audience: Audience | None = None,
        imaginer: Imaginer | None = None,
        illustrator: Illustrator | None = None,
        animator: Animator | None = None,
        image_timeout_s: float = 25.0,
        rng: random.Random | None = None,
    ) -> None:
        missing = [name for name, module in (("imaginer", imaginer), ("illustrator", illustrator),
                                             ("animator", animator)) if module is None]  # fmt: skip
        if scenario.needs_live_images and missing:
            raise ValueError("Scenariusz ma sceny rysowane na żywo, a brakuje modułów: " + ", ".join(missing))
        self._imaginer = imaginer
        self._illustrator = illustrator
        self._animator = animator
        self._image_timeout_s = image_timeout_s
        self._rng = rng or random.Random()
        self._stopped = threading.Event()
        # Scena generowana może paść przed pytaniem otwartym (inna gałąź): domyślny pomysł jest od początku.
        self._memory: dict[str, str] = {
            scene.remember: scene.default_idea for scene in scenario.scenes.values() if scene.kind == "open"
        }
        self._prefetched: dict[str, tuple[Future[Path], float]] = {}  # scena → (rysowanie, termin)
        self._scenario = scenario
        self._player = player
        self._listener = listener
        self._voice = voice
        self._resolver = resolver
        self._max_reprompts = max_reprompts
        self._meter = meter  # bez krzykomierza sceny `vote` rozpoznają wybór z mowy, jak pozostałe
        self._audience = audience  # telefony widzów; gdy żaden nie jest połączony, słuchamy sali

    @property
    def memory(self) -> Mapping[str, str]:
        """Pomysły dziecka z tego seansu (klucz `remember` → opis po angielsku), do pytania: `default_idea`."""
        return dict(self._memory)

    def stop(self) -> None:
        """Przerywa bajkę przy najbliższej okazji; wywoływane z wątku okna, np. po Esc."""
        self._stopped.set()

    def _check_stopped(self) -> None:
        if self._stopped.is_set():
            raise _Stopped

    def _play(self, clip: Path) -> None:
        self._check_stopped()
        self._player.play(clip)

    def _loop(self, clip: Path) -> None:
        self._check_stopped()
        self._player.loop(clip)

    def run(self) -> list[str]:
        """Odtwarza bajkę i zwraca identyfikatory odwiedzonych scen."""
        visited: list[str] = []
        scene = self._scenario.scene(self._scenario.start)
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rysowanie")
        try:
            while True:
                self._check_stopped()
                visited.append(scene.id)
                log.info("Scena: %s", scene.id)
                if scene.kind == "generated":
                    self._show_generated(scene)
                    scene = self._scenario.scene(scene.next)
                    continue
                self._prefetch(scene.successors if scene.choices else ())
                self._play(scene.clip)
                if scene.is_ending:
                    return visited
                if scene.idle is not None:
                    self._loop(scene.idle)
                if scene.kind == "open":
                    self._ask_open(scene)  # pomysł z mikrofonu na sali, także gdy działają telefony
                    scene = self._scenario.scene(scene.next)
                    continue
                choice = self._decide(scene)
                self._drop_prefetched(other for other in scene.successors if other != choice.next)
                scene = self._scenario.scene(choice.next)
        except _Stopped:
            log.info("Bajka zatrzymana")
            return visited
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)  # nie czekamy na spóźnione obrazy

    def _decide(self, scene: Scene) -> Choice:
        if self._audience is not None and self._phones_connected():
            return self._ask_audience(scene)
        if scene.vote and self._meter is not None:
            return self._vote(scene)
        return self._ask(scene)

    def _phones_connected(self) -> bool:
        try:
            return self._audience.connected() > 0
        except Exception:
            log.exception("Błąd aplikacji mobilnej, słucham sali")
            return False

    def _ask_audience(self, scene: Scene) -> Choice:
        """Runda na telefonach widowni: wygrywa wybór, który wskazało najwięcej osób."""
        for attempt in range(self._max_reprompts + 1):
            answers = self._collect(scene)
            votes = Counter(a.choice_id for a in answers if a.choice_id in scene.choices)
            ranked = votes.most_common(2)
            log.info("Odpowiedzi z telefonów: %d, głosy: %s", len(answers), dict(votes))
            if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
                choice = scene.choices[ranked[0][0]]
                # Jedna odpowiedź = osobista reakcja modelu; przy wielu Lila mówi stałą kwestię ze scenariusza.
                personal = answers[0].reply if len(answers) == 1 else ""
                self._say(personal or choice.reply)
                return choice
            if attempt < self._max_reprompts:
                unclear = answers[0].reply if len(answers) == 1 and not votes else ""
                self._say(unclear or scene.reprompt)
        default = scene.choices[scene.default]
        log.info("Brak decyzji z telefonów, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _collect(self, scene: Scene) -> list[Interpretation]:
        try:
            return self._audience.collect(scene)
        except Exception:
            log.exception("Błąd aplikacji mobilnej, traktuję rundę jak ciszę")
            return []

    def _vote(self, scene: Scene) -> Choice:
        """Runda okrzyków: bohaterka wzywa po kolei do każdej opcji, wygrywa najgłośniejsza."""
        for attempt in range(self._max_reprompts + 1):
            winner = self._shout_round(scene)
            if winner is not None:
                choice = scene.choices[winner]
                self._say(choice.reply)
                return choice
            if attempt < self._max_reprompts:
                self._say(scene.reprompt)
        default = scene.choices[scene.default]
        log.info("Za cicho albo remis, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _shout_round(self, scene: Scene) -> str | None:
        try:
            self._meter.calibrate()
            levels: dict[str, float] = {}
            for choice in scene.choices.values():
                if choice.call_clip is not None:
                    self._play(choice.call_clip)
                    self._loop(scene.idle)
                else:
                    self._say(choice.call)
                levels[choice.id] = self._meter.measure()
            winner = self._meter.winner(levels)
        except _Stopped:
            raise
        except Exception:
            log.exception("Błąd krzykomierza, traktuję jak ciszę")
            return None
        log.info("Okrzyki: %s -> %s", ", ".join(f"{k}={v:.0f}" for k, v in levels.items()), winner)
        return winner if winner in scene.choices else None

    def _ask(self, scene: Scene) -> Choice:
        for attempt in range(self._max_reprompts + 1):
            transcript = self._listen()
            if transcript:
                interpretation = self._interpret(scene, transcript)
                if interpretation.choice_id is not None:
                    choice = scene.choices[interpretation.choice_id]
                    self._say(interpretation.reply or choice.reply)
                    return choice
                retry_line = interpretation.reply or scene.reprompt
            else:
                retry_line = scene.reprompt
            if attempt < self._max_reprompts:
                self._say(retry_line)
        default = scene.choices[scene.default]
        log.info("Brak decyzji, bohater wybiera sam: %s", default.id)
        self._say(f"{scene.fallback or DEFAULT_FALLBACK} {default.reply}")
        return default

    def _ask_open(self, scene: Scene) -> None:
        vision = self._hear_idea(scene)
        if vision is None:
            self._memory[scene.remember] = scene.default_idea
            self._prefetch((scene.next,))
            self._say(FALLBACK_VISION_LINE)
            self._play(self._fallback_clip(scene))
            return
        self._memory[scene.remember] = vision.idea
        prompt = fill_prompt(scene.image_prompt, {**self._memory, "idea": vision.idea})
        deadline = time.monotonic() + self._image_timeout_s
        future = self._pool.submit(self._render, prompt)
        self._prefetch((scene.next,))  # dopiero po rysunku dziecka: jego pomysł ma pierwszeństwo w kolejce
        if vision.reply:
            self._say(vision.reply)  # postać mówi, a obraz w tym czasie się rysuje
        self._play(self._clip_or_fallback(scene, future, deadline))

    def _hear_idea(self, scene: Scene) -> Vision | None:
        """Pomysł dziecka albo None: cisza po wszystkich dopytaniach, błąd LLM, pomysł nie do narysowania."""
        for attempt in range(self._max_reprompts + 1):
            transcript = self._listen()
            if transcript:
                if scene.drawing is not None:
                    self._loop(scene.drawing)  # od razu: odpowiedź modelu potrwa, a ekran nie może stać pusty
                try:
                    vision = self._imaginer.imagine(scene, transcript)
                except Exception:
                    log.exception("Błąd LLM przy pomyśle dziecka, pokazuję klip zapasowy")
                    return None
                log.info("Pomysł: %r | %s", vision.idea, vision.reply)
                return vision if vision.idea else None
            if attempt < self._max_reprompts:
                self._say(scene.reprompt)
        return None

    def _show_generated(self, scene: Scene) -> None:
        self._prefetch((scene.id,))  # nic nie robi, jeśli scena już się rysuje
        future, deadline = self._prefetched.pop(scene.id)
        self._prefetch((scene.next,))
        clip = self._clip_or_fallback(scene, future, deadline, announce=False)
        self._loop(clip)
        self._say(scene.narration)  # postać mówi na tle zapętlonej ilustracji

    def _prefetch(self, scene_ids: Iterable[str]) -> None:
        for scene_id in scene_ids:
            target = self._scenario.scene(scene_id)
            if target.kind != "generated" or scene_id in self._prefetched:
                continue
            prompt = fill_prompt(target.image_prompt, self._memory)
            log.info("Rysuję w tle scenę %s", scene_id)
            self._prefetched[scene_id] = (
                self._pool.submit(self._render, prompt),
                time.monotonic() + self._image_timeout_s,
            )

    def _drop_prefetched(self, scene_ids: Iterable[str]) -> None:
        for scene_id in scene_ids:
            entry = self._prefetched.pop(scene_id, None)
            if entry is not None:
                entry[0].cancel()  # niewybrana gałąź: jeśli jeszcze czeka w kolejce, nie rysujemy jej wcale

    def _render(self, prompt: str) -> Path:
        started = time.monotonic()
        clip = self._animator.animate(self._illustrator.draw(prompt))
        log.info("Narysowane w %.1f s: %s", time.monotonic() - started, clip.name)
        return clip

    def _clip_or_fallback(self, scene: Scene, future: Future[Path], deadline: float, announce: bool = True) -> Path:
        try:
            return future.result(timeout=max(0.0, deadline - time.monotonic()))
        except TimeoutError:
            log.warning("Rysowanie trwa dłużej niż %.0f s, pokazuję klip zapasowy", self._image_timeout_s)
        except Exception:
            log.exception("Błąd rysowania, pokazuję klip zapasowy")
        if announce:
            self._say(FALLBACK_VISION_LINE)
        return self._fallback_clip(scene)

    def _fallback_clip(self, scene: Scene) -> Path:
        return self._rng.choice(scene.fallback_clips)

    def _listen(self) -> str | None:
        self._check_stopped()
        try:
            transcript = self._listener.listen()
        except Exception:
            log.exception("Błąd rozpoznawania mowy, traktuję jak ciszę")
            return None
        log.info("Dziecko: %r", transcript)
        return transcript or None

    def _interpret(self, scene: Scene, transcript: str) -> Interpretation:
        default = scene.choices[scene.default]
        try:
            interpretation = self._resolver.resolve(scene, transcript)
        except Exception:
            log.exception("Błąd LLM, wybieram domyślnie: %s", default.id)
            return Interpretation(choice_id=default.id, reply=default.reply)
        if interpretation.choice_id is not None and interpretation.choice_id not in scene.choices:
            log.error("LLM zwrócił nieznany wybór %r, wybieram: %s", interpretation.choice_id, default.id)
            return Interpretation(choice_id=default.id, reply=default.reply)
        log.info("Intencja: %s | %s", interpretation.choice_id, interpretation.reply)
        return interpretation

    def _say(self, text: str) -> None:
        self._check_stopped()  # przed try: zatrzymanie nie jest błędem TTS
        try:
            self._voice.say(text)
        except Exception:
            log.exception("Błąd TTS, bajka leci dalej bez kwestii: %s", text)

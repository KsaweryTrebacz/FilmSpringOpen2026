"""Montaż AI: model decyduje, jak połączyć klipy wybrane przez widza, a odtwarzacz robi płynne przejście.

Po każdym wyborze montażysta dostaje informacje o przejściu (skąd i dokąd, co i jak widz wybrał, co powiedział,
stan widza według tętna, nastrój odcinka, podpowiedź autora) i zwraca rodzaj przejścia, jego długość i powód
jednym zdaniem dla panelu podglądu. Model (Phi przez Foundry Local albo Azure OpenAI) pracuje w tle, gdy gra
reakcja postaci; jeśli nie zdąży albo zawiedzie, decydują reguły (`RuleEditor`) — odcinek nigdy nie czeka na montaż.
Przejścia wykonuje odtwarzacz (`bajka/web_player.py`), a w wersji liniowej ffmpeg (`bajka/linear.py`).
Moduł spełnia kontrakt `bajka.ports.Editor`.

Test bez reszty aplikacji: python -m bajka.montage SCENARIUSZ [--from ID] [--choice ID] [--viewer pobudzenie] [--no-llm]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import re
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from bajka.config import ConfigError, get_float, load_env
from bajka.ports import Cut, CutContext, Editor
from bajka.pulse import BORED, EXCITED
from bajka.safety import is_safe_reply
from bajka.scenario import (
    CUT,
    DISSOLVE,
    FADE_BLACK,
    FADE_WHITE,
    TRANSITIONS,
    WIPE,
    Scenario,
    ScenarioError,
    Scene,
    load_scenario,
)

log = logging.getLogger(__name__)

# Najkrótsze i najdłuższe przejście każdego rodzaju. Rozjaśnienie nigdy szybko: bez błysków.
TIMING = {CUT: (0.0, 0.0), DISSOLVE: (0.3, 2.0), FADE_BLACK: (0.6, 2.5), FADE_WHITE: (0.8, 2.5), WIPE: (0.4, 1.5)}
DEFAULT_SECONDS = {CUT: 0.0, DISSOLVE: 0.6, FADE_BLACK: 1.2, FADE_WHITE: 1.0, WIPE: 0.8}
MAX_REASON_CHARS = 140
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def checked_cut(transition: str, seconds: float, reason: str = "", source: str = "reguly") -> Cut:
    """Przejście w dozwolonych granicach: znany rodzaj, długość w widełkach, krótki i bezpieczny powód."""
    if transition not in TRANSITIONS:
        raise ValueError(f"nieznane przejście {transition!r}, dostępne: {', '.join(TRANSITIONS)}")
    low, high = TIMING[transition]
    reason = " ".join(str(reason).split())
    if len(reason) > MAX_REASON_CHARS or not is_safe_reply(reason):
        reason = ""
    return Cut(transition=transition, seconds=round(min(high, max(low, float(seconds))), 2), reason=reason, source=source)


def loop_cut(scenario: Scenario) -> Cut:
    """Wejście pętli oczekiwania po klipie sceny (`loop_transition` scenariusza); domyślnie cięcie."""
    kind = scenario.loop_transition or CUT
    return checked_cut(kind, DEFAULT_SECONDS[kind], "Pętla oczekiwania po klipie sceny.")


def describe_cut(cut: Cut) -> str:
    """„przenikanie 0,6 s” — do dziennika i panelu."""
    return cut.transition if cut.transition == CUT else f"{cut.transition} {cut.seconds:.1f} s".replace(".", ",")


class RuleEditor:
    """Reguły montażu: przewidywalne, natychmiastowe; zapas dla modelu i montaż wersji liniowej."""

    def cut(self, context: CutContext) -> Cut:
        if context.edge == "reakcja":
            if context.viewer == BORED:
                return checked_cut(CUT, 0.0, "Tętno widza spada (znużenie) -> dynamiczny montaż: natychmiastowa reakcja cięciem (0 s).")
            if context.viewer == EXCITED:
                return checked_cut(DISSOLVE, 0.8, "Tętno widza wysokie (pobudzenie) -> wolniejszy montaż: łagodne przenikanie reakcji (0,8 s), aby wyciszyć.")
            return checked_cut(DISSOLVE, 0.4, "Reakcja postaci w tym samym miejscu: krótkie przenikanie.")

        moving = bool(context.from_place and context.to_place and context.from_place != context.to_place)

        if context.to_ending:
            transition, base_why = FADE_BLACK, "Zakończenie historii"
        elif context.hint and context.viewer not in (EXCITED, BORED):
            transition, base_why = context.hint, "Przejście wskazane przez autora scenariusza"
        elif moving:
            transition, base_why = WIPE, f"Nowe miejsce ({context.to_place})"
        else:
            transition, base_why = DISSOLVE, "Ciąg dalszy w tym samym miejscu"

        seconds = DEFAULT_SECONDS[transition]

        # Adaptacja dynamiki montażu wg biofeedbacku tętna:
        if context.viewer == BORED:
            # Tętno widza spada (znużenie) -> montaż staje się bardziej dynamiczny!
            if context.to_ending:
                transition = FADE_BLACK
                seconds = 0.8
                why = "Tętno widza spada (znużenie) -> dynamiczne, krótsze zaciemnienie (0,8 s) na finał."
            elif moving:
                transition = WIPE
                seconds = 0.35
                why = f"Tętno widza spada (znużenie) -> dynamiczny montaż w {context.to_place}: szybkie przetarcie (0,35 s) dla ożywienia uwagi."
            else:
                transition = CUT
                seconds = 0.0
                why = "Tętno widza spada (znużenie) -> dynamiczny montaż: natychmiastowe cięcie (0 s), aby obudzić ciekawość i zdynamizować film."
        elif context.viewer == EXCITED:
            # Tętno widza za wysokie (pobudzenie) -> montaż staje się wolniejszy, aby zrelaksować widza!
            if context.to_ending:
                transition = FADE_BLACK
                seconds = 2.0
                why = "Tętno widza za wysokie (pobudzenie) -> wolne, 2-sekundowe zaciemnienie, wyciszające emocje."
            else:
                transition = DISSOLVE
                seconds = 1.8
                why = "Tętno widza za wysokie (pobudzenie) -> wolniejszy montaż: długie, łagodne przenikanie (1,8 s), aby zrelaksować i uspokoić widza."
        else:
            why = f"{base_why}: {describe_cut(Cut(transition, seconds))}."

        return checked_cut(transition, seconds, why)


SYSTEM_PROMPT = """\
Jesteś montażystą animowanej bajki interaktywnej dla dzieci w wieku 4-7 lat, oglądanej w domu w serwisie
streamingowym. Widz właśnie wpłynął na historię. Dostosowujesz montaż filmu do tętna i stanu emocjonalnego dziecka:
- Gdy tętno widza SPADA i widz się nudzi (stan: znużenie): montaż staje się bardziej DYNAMICZNY i energiczny!
  Wybieraj natychmiastowe cięcie (ciecie, 0.0 s) lub szybkie, dynamiczne przetarcie (0.3-0.4 s), aby ożywić tempo i skupić uwagę.
- Gdy tętno widza jest ZA WYSOKIE (stan: pobudzenie): montaż staje się WOLNIEJSZY i kojący, aby zrelaksować widza!
  Wybieraj długie, miękkie i powolne przenikanie (przenikanie, 1.5-2.2 s), aby uspokoić oddech i zrelaksować dziecko.
- W stanie normy: standardowe przejścia (przenikanie 0.6 s, przetarcie 0.8 s przy zmianie miejsca).
Dostępne rodzaje przejść:
- ciecie: natychmiastowa zmiana (0 s), dynamiczny montaż w tym samym miejscu;
- przenikanie: łagodne nałożenie klipów na siebie (0.3 - 2.5 s);
- przetarcie: nowy obraz wsuwa się na stary przy zmianie miejsca (0.3 - 1.5 s);
- zaciemnienie: przez ciemność, na zakończenie historii lub uspokojenie (0.6 - 2.5 s);
- rozjasnienie: przez jasność przy radosnej chwili, powoli i bez błysków (0.8 - 2.5 s).
W polu "reason" napisz jedno krótkie zdanie po polsku dla twórców: dlaczego takie przejście w odniesieniu do tętna i dynamiki.
Odpowiedz wyłącznie jednym obiektem JSON, bez żadnego innego tekstu:
{"transition": "<jedno z: ciecie, przenikanie, przetarcie, zaciemnienie, rozjasnienie>", "seconds": <liczba>, "reason": "<zdanie>"}
"""

HOW = {"przycisk": "pilotem albo dotykiem", "glos": "głosem", "wiekszosc": "większością głosów z telefonów",
       "domyslna": "nie wybrał, postać zdecydowała sama"}  # fmt: skip


def build_messages(context: CutContext, suggestion: Cut) -> list[dict[str, str]]:
    facts = [
        f"Przejście: scena {context.from_scene} -> scena {context.to_scene}"
        + (" (zakończenie historii)" if context.to_ending else ""),
        f"Miejsce: {context.from_place or 'nieznane'} -> {context.to_place or 'nieznane'}",
        f"Nastrój odcinka: {context.mood or 'nieokreślony'}",
        f"Stan widza według tętna: {context.viewer or 'brak pomiaru'}",
    ]
    if context.choice:
        facts.append(f"Wybór widza: {context.choice} ({context.meaning}); widz wybrał {HOW.get(context.how, context.how)}")
    if context.transcript:
        facts.append(f'Widz powiedział: "{context.transcript}"')
    if context.hint:
        facts.append(f"Podpowiedź autora: {context.hint}")
    facts.append(f"Propozycja reguł: {suggestion.transition}, {suggestion.seconds} s")
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "\n".join(facts)}]


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "transition": {"type": "string", "enum": list(TRANSITIONS)},
        "seconds": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["transition", "seconds", "reason"],
    "additionalProperties": False,
}


def parse_cut(content: str) -> Cut:
    """Odpowiedź modelu → przejście; wybacza ```json i tekst wokół obiektu, odrzuca nieznane rodzaje."""
    found = _JSON_OBJECT.search(content)
    if found is None:
        raise ValueError(f"model nie zwrócił JSON: {content[:120]!r}")
    data = json.loads(found.group(0))
    if not isinstance(data, dict):
        raise ValueError("model nie zwrócił obiektu JSON")
    transition = str(data.get("transition", "")).strip().lower()
    return checked_cut(transition, float(data.get("seconds", 0)), str(data.get("reason", "")), source="model")


class ModelEditor:
    """Montażysta z modelem językowym (klient zgodny z OpenAI: Foundry Local albo Azure OpenAI)."""

    def __init__(
        self, client: Any, model_id: str, formats: list[dict[str, Any]], temperature: float = 0.4,
        rules: Editor | None = None,
    ) -> None:  # fmt: skip
        self._client = client
        self._model_id = model_id
        self._formats = formats
        self._format_level = 0  # rośnie, gdy serwer odrzuci format odpowiedzi (jak w bajka/local_intent.py)
        self._temperature = temperature
        self._rules = rules or RuleEditor()

    @classmethod
    def local(cls, settings: Any) -> ModelEditor:
        """Phi przez Foundry Local; `settings` to `bajka.local_intent.LocalLlmSettings`."""
        from openai import OpenAI

        from bajka.foundry import load_model, openai_base_url

        model = load_model(settings.model, settings.device)
        client = OpenAI(base_url=openai_base_url(), api_key="lokalnie", timeout=20.0, max_retries=0)
        formats = [{"type": "json_schema", "json_schema": json.dumps(RESPONSE_SCHEMA)}, {"type": "json_object"}]
        return cls(client, model.id, formats)

    @classmethod
    def azure(cls, settings: Any) -> ModelEditor:
        """Azure OpenAI; `settings` to `bajka.intent.LlmSettings`."""
        from openai import AzureOpenAI

        client = AzureOpenAI(azure_endpoint=settings.endpoint, api_key=settings.api_key,
                             api_version=settings.api_version, timeout=10.0, max_retries=1)  # fmt: skip
        schema = {"name": "przejscie", "strict": True, "schema": RESPONSE_SCHEMA}
        return cls(client, settings.deployment, [{"type": "json_schema", "json_schema": schema}])

    def cut(self, context: CutContext) -> Cut:
        messages = build_messages(context, self._rules.cut(context))
        while True:
            try:
                response = self._client.chat.completions.create(
                    model=self._model_id,
                    messages=messages,
                    response_format=self._formats[self._format_level],
                    temperature=self._temperature,
                    max_tokens=120,
                )
                break
            except Exception as exc:
                if getattr(exc, "status_code", None) != 400 or self._format_level + 1 >= len(self._formats):
                    raise
                self._format_level += 1
                log.warning("Serwer odrzucił format odpowiedzi montażu, przechodzę na: %s", self._formats[self._format_level])
        return parse_cut(response.choices[0].message.content or "")


@dataclass(frozen=True)
class MontageSettings:
    use_model: bool = True  # BAJKA_MONTAGE=model; "reguly" = bez modelu, same reguły
    wait_seconds: float = 0.5  # ile najdłużej czekamy na model, gdy przejście trzeba już zagrać

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> MontageSettings:
        mode = (env.get("BAJKA_MONTAGE") or "model").strip().lower()
        if mode not in ("model", "reguly"):
            raise ConfigError(f"BAJKA_MONTAGE musi być: model albo reguly, jest: {mode!r}")
        return cls(use_model=mode == "model", wait_seconds=get_float(env, "BAJKA_MONTAGE_WAIT", cls.wait_seconds))


@dataclass
class PendingCut:
    """Decyzja montażowa w toku: model myśli w tle, a reguły mają gotową odpowiedź na wypadek, gdyby nie zdążył."""

    context: CutContext
    fallback: Cut
    future: concurrent.futures.Future[Cut] | None = None


class Montage:
    """Montażysta odcinka: zleca decyzję zaraz po wyborze widza i odbiera ją, gdy przejście trzeba zagrać."""

    def __init__(self, editor: Editor | None = None, settings: MontageSettings | None = None,
                 rules: Editor | None = None) -> None:  # fmt: skip
        self._editor = editor
        self._settings = settings or MontageSettings()
        self._rules = rules or RuleEditor()
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="bajka-montaz")

    def request(self, context: CutContext) -> PendingCut:
        fallback = self._rules.cut(context)
        if self._editor is None:
            return PendingCut(context, fallback)
        return PendingCut(context, fallback, self._pool.submit(self._editor.cut, context))

    def result(self, pending: PendingCut) -> Cut:
        if pending.future is None:
            return pending.fallback
        try:
            return pending.future.result(timeout=self._settings.wait_seconds)
        except concurrent.futures.TimeoutError:
            log.info("Montaż %s -> %s: model nie zdążył, przejście z reguł", pending.context.from_scene,
                     pending.context.to_scene)  # fmt: skip
            return replace(pending.fallback, reason=f"{pending.fallback.reason} Model nie zdążył, zdecydowały reguły.")
        except Exception:
            log.exception("Błąd modelu montażu, przejście z reguł")
            return pending.fallback

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


def context_for(scenario: Scenario, scene: Scene, target: str, edge: str, viewer: str = "", **choice: str) -> CutContext:
    """Kontekst przejścia ze sceny `scene` do sceny `target` (pomocnicze dla silnika, wersji liniowej i dema)."""
    to = scenario.scene(target)
    return CutContext(
        from_scene=scene.id, to_scene=to.id, edge=edge, from_place=scene.place, to_place=to.place,
        to_ending=to.is_ending, hint=to.transition, viewer=viewer, mood=scenario.mood, **choice,
    )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.montage", description="Test decyzji montażowych.")
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem odcinka")
    parser.add_argument("--from", dest="scene", help="scena, z której wychodzimy (domyślnie startowa)")
    parser.add_argument("--choice", help="wybór widza w tej scenie (domyślnie wybór domyślny)")
    parser.add_argument("--viewer", choices=("pobudzenie", "norma", "znużenie"), default="", help="stan widza")
    parser.add_argument("--said", default="", help="co widz powiedział, np. \"przez ten kolorowy mostek\"")
    parser.add_argument("--no-llm", action="store_true", help="tylko reguły, bez modelu")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        scenario = load_scenario(args.scenario)
        scene = scenario.scene(args.scene or scenario.start)
    except (ScenarioError, OSError, KeyError) as exc:
        print(exc, file=sys.stderr)
        return 2
    if scene.choices:
        choice = scene.choices.get(args.choice or scene.default or "")
        if choice is None:
            print(f"Scena {scene.id} nie ma wyboru {args.choice!r}", file=sys.stderr)
            return 2
        context = context_for(scenario, scene, choice.next, "wybor", args.viewer, choice=choice.display_label,
                              meaning=choice.description, how="glos" if args.said else "przycisk",
                              transcript=args.said)  # fmt: skip
    elif scene.next:
        context = context_for(scenario, scene, scene.next, "dalej", args.viewer)
    else:
        print(f"Scena {scene.id} kończy odcinek", file=sys.stderr)
        return 2
    rules = RuleEditor().cut(context)
    print(f"Reguły: {describe_cut(rules)} — {rules.reason}")
    if args.no_llm:
        return 0
    try:
        from bajka.local_intent import LocalLlmSettings

        editor = ModelEditor.local(LocalLlmSettings.from_env(load_env()))
        started = time.perf_counter()
        cut = editor.cut(context)
    except Exception as exc:  # demo ma pokazać każdy błąd modelu, a nie wywrócić się
        print(f"Błąd modelu: {exc}", file=sys.stderr)
        return 1
    print(f"Model:  {describe_cut(cut)} — {cut.reason} ({time.perf_counter() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

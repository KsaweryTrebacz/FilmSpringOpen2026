"""Rozpoznawanie wyboru dziecka po słowach kluczowych — bez modelu językowego i bez sieci.

Moduł spełnia kontrakt `bajka.ports.IntentResolver`. Służy jako zapas, gdy lokalny model językowy
zawiedzie (`FallbackResolver`), i do prób na słabszym komputerze (`python -m bajka --no-llm`).
Test bez reszty aplikacji: python -m bajka.keywords SCENARIUSZ "wypowiedź dziecka" [--scene ID]
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import unicodedata
from pathlib import Path

from bajka.ports import IntentResolver, Interpretation
from bajka.scenario import Choice, Scene, ScenarioError, load_scenario

log = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """Małe litery bez polskich znaków: "Jaskinią!" -> "jaskinia"."""
    text = text.lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def words(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def same_word(spoken: str, keyword: str) -> bool:
    """Ten sam wyraz mimo odmiany: "lasu" ~ "las", "jaskini" ~ "jaskinia", ale nie "lato" ~ "las"."""
    if spoken == keyword:
        return True
    if spoken.isdigit() or keyword.isdigit() or min(len(spoken), len(keyword)) < 3:
        return False
    common = 0
    for a, b in zip(spoken, keyword):
        if a != b:
            break
        common += 1
    return common >= max(3, min(len(spoken), len(keyword)) - 2)


def choice_keywords(choice: Choice) -> list[str]:
    """Słowa z identyfikatora wyboru ("jaskinia", "inna_liczba") i z pola `keywords` scenariusza."""
    return [*choice.id.split("_"), *choice.keywords]


def matches(transcript: str, choice: Choice) -> bool:
    """Czy wypowiedź zawiera któreś słowo albo frazę wyboru (każdy wyraz frazy może być odmieniony)."""
    spoken = words(transcript)
    for keyword in choice_keywords(choice):
        parts = words(keyword)
        for start in range(len(spoken) - len(parts) + 1) if parts else ():
            if all(same_word(word, part) for word, part in zip(spoken[start:], parts)):
                return True
    return False


class KeywordIntentResolver:
    """Wybór rozpoznany, gdy wypowiedź pasuje do słów dokładnie jednego wyboru.

    Zwraca pustą kwestię, więc silnik powie statyczne `reply` ze scenariusza, a przy braku
    dopasowania — `reprompt` sceny.
    """

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        found = [choice.id for choice in scene.choices.values() if matches(transcript, choice)]
        if len(found) == 1:
            return Interpretation(choice_id=found[0], reply="")
        if found:
            log.info("Wypowiedź pasuje do kilku wyborów (%s), dopytuję", ", ".join(found))
        return Interpretation(choice_id=None, reply="")


class FallbackResolver:
    """Najpierw `primary` (np. lokalny model językowy), a przy jego błędzie `fallback` (słowa kluczowe)."""

    def __init__(self, primary: IntentResolver, fallback: IntentResolver) -> None:
        self._primary = primary
        self._fallback = fallback

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        try:
            return self._primary.resolve(scene, transcript)
        except Exception:
            log.exception("Model językowy zawiódł, rozpoznaję po słowach kluczowych")
            return self._fallback.resolve(scene, transcript)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.keywords", description="Test rozpoznawania wyboru po słowach kluczowych (offline)."
    )
    parser.add_argument("scenario", type=Path, help="plik YAML ze scenariuszem bajki")
    parser.add_argument("transcript", help="wypowiedź dziecka, np. \"do lasu\"")
    parser.add_argument("--scene", help="identyfikator sceny z pytaniem (domyślnie scena startowa)")
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
    except (ScenarioError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    scene = scenario.scenes.get(args.scene or scenario.start)
    if scene is None or scene.is_ending:
        print(f"Scena '{args.scene or scenario.start}' nie istnieje albo nie ma wyborów", file=sys.stderr)
        return 2

    interpretation = KeywordIntentResolver().resolve(scene, args.transcript)
    print(f"Scena: {scene.id} — {scene.question}")
    for choice in scene.choices.values():
        print(f"  {choice.id}: {', '.join(choice_keywords(choice))}")
    if interpretation.choice_id is None:
        print(f"Dziecko: {args.transcript!r} -> nie rozpoznano (bohater dopyta: {scene.reprompt})")
    else:
        choice = scene.choices[interpretation.choice_id]
        print(f"Dziecko: {args.transcript!r} -> {choice.id} (bohater: {choice.reply})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

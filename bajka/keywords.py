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


def compact(text: str) -> str:
    """Małe litery bez polskich znaków i znaków interpunkcyjnych."""
    return re.sub(r"[^a-z0-9]", "", normalize(text))


def words(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def same_word(spoken: str, keyword: str) -> bool:
    """Ten sam wyraz mimo odmiany: "lasu" ~ "las", "jaskini" ~ "jaskinia", ale nie "lato" ~ "las"."""
    if spoken == keyword:
        return True
    if spoken.isdigit() or keyword.isdigit():
        return False
    if min(len(spoken), len(keyword)) < 3:
        return False
    if spoken.startswith(keyword) or keyword.startswith(spoken):
        return True
    common = 0
    for a, b in zip(spoken, keyword):
        if a != b:
            break
        common += 1
    return common >= max(3, min(len(spoken), len(keyword)) - 2)


SYNONYMS: dict[str, list[str]] = {
    "hopsasa": [
        "hop", "sasa", "hopsasa", "hopsa", "zawolam", "zawolaj", "zawol", "wolam", "krzycz",
        "obudz", "budz", "glosno", "tak", "ho-pisa", "hopisa", "hop-sa-sa", "pisa", "kuferek"
    ],
    "pukanie": ["puk", "pukpuk", "zapukaj", "zapuk", "pukam", "pukanie", "stuk", "wieko", "zapukac", "puknij", "puk-puk", "stukanie"],
    "most": ["most", "mostek", "tecza", "teczowy", "kolory", "rzeka", "strumyk", "kolorowy", "teczowymostek", "teczowy mostek", "woda", "mostkiem", "mostka"],
    "las": ["las", "lasek", "drzewa", "drzewo", "szumi", "szumiacy", "szumiac", "szumiacylas", "szumiacy las", "lasem", "lasu", "dolasu", "borem", "bor"],
    "czerwona": ["czerwon", "czerwona", "czerwone", "czerwony", "czerwien", "truskawka"],
    "niebieska": ["niebiesk", "niebieska", "niebieskie", "niebieski", "blekit", "niebo"],
    "sowa": ["sow", "sowa", "sowe", "ptak", "dziupla"],
    "krecik": ["kret", "krecik", "kreta"],
    "zaba": ["zab", "zaba", "zabka", "kum"],
    "rumianek": ["rumianek", "rumian", "bialy", "biala"],
    "chaber": ["chaber", "chabry", "niebieski"],
    "mak": ["mak", "maki", "czerwony", "czerwona"],
}

ORDINALS: list[list[str]] = [
    ["1", "jeden", "pierwsz", "jedynka", "pierwsza", "pierwsze", "pierwszy"],
    ["2", "dwa", "drug", "dwojka", "druga", "drugie", "drugi"],
    ["3", "trzy", "trzec", "trojka", "trzecia", "trzecie", "trzeci"],
]


def choice_keywords(choice: Choice) -> list[str]:
    """Słowa z identyfikatora wyboru ("jaskinia", "inna_liczba") i z pola `keywords` scenariusza."""
    return [*choice.id.split("_"), *choice.keywords]


def matches(transcript: str, choice: Choice, index: int | None = None) -> bool:
    """Czy wypowiedź pasuje do danego wyboru (po numerze, słowach kluczowych, synonimach lub rdzeniu)."""
    clean_spoken = compact(transcript)
    if not clean_spoken:
        return False

    # 1. Numer wyboru (np. "jeden", "pierwsza", "dwa")
    if index is not None and index < len(ORDINALS):
        if any(ord_word in clean_spoken for ord_word in ORDINALS[index]):
            return True

    # 2. Identyfikator i etykieta wyboru
    clean_id = compact(choice.id)
    clean_label = compact(choice.display_label)
    if clean_id and (clean_id in clean_spoken or (len(clean_spoken) >= 3 and clean_spoken in clean_id)):
        return True
    if clean_label and (clean_label in clean_spoken or (len(clean_spoken) >= 3 and clean_spoken in clean_label)):
        return True

    # 3. Synonimy i słowa kluczowe
    kws = [*choice_keywords(choice), *SYNONYMS.get(choice.id, [])]
    for kw in kws:
        clean_kw = compact(kw)
        if not clean_kw:
            continue
        if clean_kw in clean_spoken or (len(clean_spoken) >= 3 and clean_spoken in clean_kw):
            return True

    # 4. Dopasowanie wyraz po wyrazie
    spoken_words = words(transcript)
    for kw in kws:
        parts = words(kw)
        for start in range(len(spoken_words) - len(parts) + 1) if parts else ():
            if all(same_word(w, p) for w, p in zip(spoken_words[start:], parts)):
                return True

    return False


class KeywordIntentResolver:
    """Wybór rozpoznany, gdy wypowiedź pasuje do słów dokładnie jednego wyboru.

    Zwraca pustą kwestię, więc silnik powie statyczne `reply` ze scenariusza, a przy braku
    dopasowania — `reprompt` sceny.
    """

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        choices = list(scene.choices.values())
        found = [choice.id for idx, choice in enumerate(choices) if matches(transcript, choice, idx)]
        if len(found) == 1:
            log.info("Rozpoznano wybór '%s' z mowy: %r", found[0], transcript)
            return Interpretation(choice_id=found[0], reply="")
        if found:
            log.info("Wypowiedź pasuje do kilku wyborów (%s), dopytuję", ", ".join(found))
        else:
            log.info("Wypowiedź %r nie pasuje do żadnego wyboru w scenie %s", transcript, scene.id)
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


class KeywordsFirstResolver:
    """Najpierw słowa kluczowe (natychmiast), model językowy tylko dla odpowiedzi, których nie rozpoznały.

    Przy wielu odpowiedziach z telefonów (drugi ekran, `bajka/mobile.py`) większość krótkich odpowiedzi
    („mostek!”) rozpoznają słowa kluczowe, więc wolniejszy model nie spowalnia rundy.
    """

    def __init__(self, keywords: IntentResolver, model: IntentResolver) -> None:
        self._keywords = keywords
        self._model = model

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        quick = self._keywords.resolve(scene, transcript)
        if quick.choice_id is not None:
            return quick
        return self._model.resolve(scene, transcript)


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

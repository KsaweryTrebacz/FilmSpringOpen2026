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


# „Nie wiem” to odpowiedź, a nie wybór: postać ma dopytać, zamiast zgadywać po podobnych słowach („nie” ~ „niebo”).
_DONT_KNOW = re.compile(r"\bnie (wiem|umiem|pamietam|rozumiem|mam pojecia)\b")


def dont_know(transcript: str) -> bool:
    return _DONT_KNOW.search(" ".join(words(transcript))) is not None


def same_word(spoken: str, keyword: str) -> bool:
    """Ten sam wyraz mimo odmiany: "lasu" ~ "las", "jaskini" ~ "jaskinia", ale nie "lato" ~ "las"."""
    if spoken == keyword:
        return True
    # Krótkie wyrazy i liczby tylko dosłownie: inaczej „do” pasowałoby do „dom”, a „lato” do „las”.
    if spoken.isdigit() or keyword.isdigit() or min(len(spoken), len(keyword)) < 3:
        return False
    if len(keyword) <= 3:
        if spoken.startswith(keyword):
            return spoken[len(keyword):] in ("u", "a", "em", "ie", "y", "ow", "ach", "ami")
        return False
    if spoken.startswith(keyword):  # odmiana: "mostkiem" ~ "mostek"
        return True
    if len(spoken) < 4:  # krótkie słowo dziecka to nie początek dłuższego: „nie” to nie „niebo”
        return False
    if keyword.startswith(spoken):  # skrót: "most" ~ "mostek"
        return True
    common = 0
    for a, b in zip(spoken, keyword):
        if a != b:
            break
        common += 1
    return common >= max(4, min(len(spoken), len(keyword)) - 1)


def edit_distance(s1: str, s2: str) -> int:
    if s1 == s2:
        return 0
    if abs(len(s1) - len(s2)) > 2:
        return abs(len(s1) - len(s2))
    d = {}
    l1, l2 = len(s1), len(s2)
    for i in range(-1, l1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, l2 + 1):
        d[(-1, j)] = j + 1
    for i in range(l1):
        for j in range(l2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,
                d[(i, j - 1)] + 1,
                d[(i - 1, j - 1)] + cost
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + 1)
    return d[(l1 - 1, l2 - 1)]


SYNONYMS: dict[str, list[str]] = {
    "hopsasa": [
        "hop", "sasa", "hopsasa", "hopsa", "zawolam", "zawolaj", "zawol", "wolam", "krzycz",
        "obudz", "budz", "glosno", "tak", "ho-pisa", "hopisa", "hop-sa-sa", "pisa", "kuferek",
        "krope", "kropie", "kroce", "kroczę", "kropa", "krop", "hopsy", "hopla", "chopsasa", "chop",
        "hops", "zawolajmy", "krzyczymy", "krzyknij"
    ],
    "pukanie": [
        "puk", "pukpuk", "zapukaj", "zapuk", "pukam", "pukanie", "stuk", "wieko", "zapukac", "puknij", "puk-puk", "stukanie",
        "bog", "buk", "pogo", "pog", "buku", "stuku", "pukpukpuk", "puk puk", "stuk stuk", "pukaj", "puknij", "puku",
        "bogbog", "pogpog", "bukbuk", "buki", "bogow", "boga", "boki", "boku", "zapukam", "stuknij", "stukac", "pukne", "zapukamy", "stukamy", "pugu"
    ],
    "most": [
        "most", "mostek", "tecza", "teczowy", "kolory", "rzeka", "strumyk", "kolorowy", "teczowymostek", "teczowy mostek",
        "woda", "mostkiem", "mostka", "mostu", "mosty", "mostku", "na most", "przez most", "przez mostek", "do mostka",
        "tenczowy", "tenczowym", "teczowym", "lastek", "mastek", "trawym"
    ],
    "las": [
        "las", "lasek", "drzewa", "drzewo", "szumi", "szumiacy", "szumiac", "szumiacylas", "szumiacy las", "lasem", "lasu",
        "dolasu", "borem", "bor", "szum", "szumiaco", "szumia", "szumi las", "szumilas", "przez las", "do lasu", "lasku", "laskiem"
    ],
    "czerwona": [
        "czerwon", "czerwona", "czerwone", "czerwony", "czerwien", "czerwonka", "truskawka",
        "czerowny", "czerowna", "czerowne", "czerwonadeska", "czerwona deska", "pierwsza", "pierwszy", "jeden", "1"
    ],
    "niebieska": [
        "niebiesk", "niebieska", "niebieskie", "niebieski", "blekit", "blekitna", "niebo",
        "niebjeska", "niebeska", "niebieskadeska", "niebieska deska", "druga", "drugi", "dwa", "2"
    ],
    "sowa": ["sow", "sowa", "sowe", "sowka", "ptak", "dziupla", "hu", "huhu", "hu-hu", "hu hu", "u-hu", "uhu", "pierwsza", "pierwszy", "1"],
    "zaba": ["zab", "zaba", "zabe", "zabka", "kum", "kumkum", "kum-kum", "kum kum", "rechot", "druga", "drugi", "2"],
    "rumianek": ["rumianek", "rumian", "bialy", "biala"],
    "chaber": ["chaber", "chabry", "niebieski"],
    "mak": ["mak", "maki", "czerwony", "czerwona"],
    "spokojnie": ["spokojnie", "udalo", "udalo sie", "tak", "juz", "fu", "fuu", "uff", "dmucham", "wdech", "wydech", "pierwsza", "pierwszy", "1"],
    "jeszcze": ["jeszcze", "jeszcze raz", "znowu", "powtorz", "powtorzmy", "nie", "druga", "drugi", "2"],
    "mapa": ["mapa", "mape", "mapy", "mapie", "mapka", "mapa rozkladanka", "rozkladanka", "plan", "droga", "pierwsza", "pierwszy", "1"],
    "latarka": ["latarka", "latarke", "latarki", "latarce", "swietliczka", "swiatlo", "swieci", "druga", "drugi", "2"],
    "lornetka": [
        "lornetka", "lornetke", "lornetki", "lornetce", "lornetko", "lornetka patrzalka",
        "patrzalka", "patrzalke", "patrzalki", "patrzec", "patrze", "daleko", "przybliz", "przybliza",
        "lupa", "lupka", "szkielka", "loretka", "ornetka", "lornet", "trzecia", "trzeci", "3"
    ],
    "trzy": [
        "trzy", "3", "trzech", "trzem", "trzema", "trzecia", "trzeci", "trojka",
        "jeden dwa trzy", "raz dwa trzy", "jedna dwie trzy", "raz dwa", "dwie trzy",
        "czy", "drzy", "tszy", "tzy", "trzi", "pszczoly", "pszczolki", "trzy pszczoly", "trzy pszczolki", "sa trzy", "widze trzy"
    ],
    "slonecznik": ["slonecznik", "slonecznika", "sloneczniki", "slonecznikiem", "slonce", "zolty", "duzy", "kwiat", "kwiatek", "pierwszy", "pierwsza", "1"],
    "koniczyna": ["koniczyna", "koniczyne", "koniczynka", "koniczynke", "koniczynki", "zielona", "drugi", "druga", "2"],
    "stokrotka": ["stokrotka", "stokrotke", "stokrotki", "stokrotce", "biala", "mala", "trzeci", "trzecia", "3"],
    "taniec": [
        "taniec", "tanca", "tancem", "tanczyc", "tanczymy", "zatanczyc", "zatanczmy", "tanczmy",
        "skaczemy", "skakac", "ruch", "machac", "bzz", "pszczolkowy taniec", "pszczolkowy", "pierwszy", "pierwsza", "1"
    ],
    "piosenka": [
        "piosenka", "piosenke", "piosenki", "piosence", "spiewac", "spiewamy", "zaspiewac", "zaspiewajmy",
        "muzyka", "la la la", "piosenka o kwiatkach", "druga", "drugi", "2"
    ],
    "inna_liczba": ["cztery", "piec", "szesc", "siedem", "osiem", "czworka", "piatka", "duzo", "wiele", "4", "5", "6", "czworeczka", "inna", "wiecej"]
}

ORDINALS: list[list[str]] = [
    ["1", "jeden", "pierwsz", "jedynka", "pierwsza", "pierwsze", "pierwszy"],
    ["2", "dwa", "drug", "dwojka", "druga", "drugie", "drugi"],
    ["3", "trzy", "trzec", "trojka", "trzecia", "trzecie", "trzeci"],
]


def choice_keywords(choice: Choice) -> list[str]:
    """Słowa z identyfikatora wyboru ("jaskinia", "inna_liczba") i z pola `keywords` scenariusza."""
    return [*choice.id.split("_"), *choice.keywords]


def score_choice(transcript: str, choice: Choice, index: int, scene_id: str) -> int:
    clean_spoken = compact(transcript)
    spoken_words = words(transcript)
    if not clean_spoken:
        return 0

    # Scena liczenia pszczółek: priorytet dla fraz liczenia i liczby 3
    if scene_id == "laka":
        counting_phrases = ["jedendwatrzy", "razdwatrzy", "jednadwietrzy", "dwietrzy", "trzy", "czy", "trojka", "trzech", "3", "pszczoly", "pszczolki"]
        if choice.id == "trzy":
            if any(p in clean_spoken for p in counting_phrases):
                return 50
        elif choice.id == "inna_liczba":
            other_nums = ["cztery", "piec", "szesc", "czworka", "duzo", "4", "5", "6", "inna", "wiecej"]
            if any(n in clean_spoken for n in other_nums):
                return 50
            return 0

    score = 0
    clean_id = compact(choice.id)
    clean_label = compact(choice.display_label)

    # 1. Pełna etykieta i identyfikator
    if clean_label and clean_label in clean_spoken:
        score += 25
    elif clean_id and len(clean_id) >= 4 and clean_id in clean_spoken:
        score += 15

    # 2. Ordinals (pozycja przycisku: 1, 2, 3)
    if index < len(ORDINALS):
        for ord_word in ORDINALS[index]:
            if ord_word in spoken_words or (len(ord_word) >= 4 and ord_word in clean_spoken):
                score += 8
                break

    # 3. Synonimy i słowa kluczowe
    kws = [*choice_keywords(choice), *SYNONYMS.get(choice.id, [])]
    for syn in kws:
        clean_syn = compact(syn)
        if not clean_syn:
            continue
        if " " in syn and compact(syn) in clean_spoken:
            score += 20
            continue
        for w in spoken_words:
            if w == clean_syn:
                score += 12
            elif len(clean_syn) >= 4 and (w.startswith(clean_syn) or clean_syn.startswith(w)):
                score += 9
            elif len(w) >= 5 and len(clean_syn) >= 5 and edit_distance(w, clean_syn) <= 1:
                score += 8
            elif len(w) >= 8 and len(clean_syn) >= 8 and edit_distance(w, clean_syn) <= 2:
                score += 7

    return score


def matches(transcript: str, choice: Choice, index: int | None = None) -> bool:
    """Kompatybilność wsteczna: czy wypowiedź daje dodatni wynik dla wyboru."""
    return score_choice(transcript, choice, index or 0, "") > 0


class KeywordIntentResolver:
    """Wybór rozpoznany po słowach kluczowych i dopasowaniu rozmytym (fuzzy scoring)."""

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        if dont_know(transcript):
            log.info("Dziecko nie wie (%r), dopytuję", transcript)
            return Interpretation(choice_id=None, reply="")

        choices = list(scene.choices.values())
        scores = {choice.id: score_choice(transcript, choice, idx, scene.id) for idx, choice in enumerate(choices)}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_id, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0

        if top_score > 0 and (top_score > second_score or second_score == 0):
            log.info("Rozpoznano wybór '%s' (punkty: %d vs %d) z mowy: %r", top_id, top_score, second_score, transcript)
            return Interpretation(choice_id=top_id, reply="")

        if top_score > 0:
            log.info("Niejednoznaczna wypowiedź %r (remis punktów: %s), dopytuję", transcript, scores)
        else:
            log.info("Wypowiedź %r nie pasuje do żadnego wyboru w scenie %s (punkty: %s)", transcript, scene.id, scores)
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

"""Eksperyment: jak często zapasowe rozpoznawanie po słowach kluczowych trafia w wybór dziecka.

Tryb bez modelu językowego (`--no-llm`) i zapas, gdy model zawiedzie. Dla każdej wypowiedzi z `wypowiedzi.yaml`
sprawdza wynik `KeywordIntentResolver`: dobry wybór, zły wybór (najgorszy przypadek: historia idzie nie tam,
gdzie dziecko chciało) albo brak wyboru (postać dopytuje — bezpieczne). Uruchomienie z katalogu repozytorium:

    python docs/prezentacja/eksperyment/slowa_kluczowe.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

from bajka.keywords import KeywordIntentResolver
from bajka.scenario import load_scenario

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UNCLEAR = "brak"


def main() -> int:
    scenario = load_scenario(ROOT / "scenarios" / "klub_ciekawskich.yaml")
    phrases = yaml.safe_load((HERE / "wypowiedzi.yaml").read_text(encoding="utf-8"))
    resolver = KeywordIntentResolver()
    clear, unclear, misses = Counter(), Counter(), []
    for scene_id, by_choice in phrases.items():
        scene = scenario.scene(scene_id)
        for expected, lines in by_choice.items():
            for line in lines:
                got = resolver.resolve(scene, line).choice_id
                if expected == UNCLEAR:
                    unclear["dopytanie" if got is None else "zły wybór"] += 1
                    outcome = "dopytanie" if got is None else "zły wybór"
                else:
                    outcome = "dobry" if got == expected else "dopytanie" if got is None else "zły wybór"
                    clear[outcome] += 1
                if outcome != "dobry" and not (expected == UNCLEAR and got is None):
                    misses.append(f"  {scene_id:9} {line!r:28} oczekiwane: {expected:11} wynik: {got or '— (dopytanie)'}")
    total = sum(clear.values())
    print(f"Wypowiedzi z jasnym wyborem: {total}")
    for key in ("dobry", "dopytanie", "zły wybór"):
        print(f"  {key:10} {clear[key]:3}  ({100 * clear[key] / total:.0f}%)")
    print(f"Wypowiedzi niejasne: {sum(unclear.values())} — dopytanie {unclear['dopytanie']}, zły wybór {unclear['zły wybór']}")
    print("Pomyłki i dopytania:")
    print("\n".join(misses) or "  brak")
    return 0


if __name__ == "__main__":
    sys.exit(main())

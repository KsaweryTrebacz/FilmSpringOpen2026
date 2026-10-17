"""Siatka bezpieczeństwa dla kwestii pisanych na żywo przez model językowy.

Regulamin hackathonu (§3 ust. 8) wyklucza treści wulgarne, obraźliwe, propagujące przemoc i nieprawdziwe,
a kwestie Lili słyszą małe dzieci. Prompt (`bajka/intent.py`) prosi model o bezpieczne odpowiedzi;
ten moduł sprawdza wynik. Kwestia podejrzana albo za długa zostaje pusta — silnik powie wtedy stałą,
sprawdzoną kwestię ze scenariusza (`reply` albo `reprompt`). Sam wybór dziecka zostaje uszanowany.
"""

from __future__ import annotations

import logging

from bajka.keywords import words
from bajka.ports import IntentResolver, Interpretation
from bajka.scenario import Scene

log = logging.getLogger(__name__)

MAX_REPLY_CHARS = 220  # ok. dwa krótkie zdania; dłuższe kwestie męczą dzieci i zdradzają „gadanie” modelu

# Początki słów (bez polskich znaków), których bohaterka bajki dla dzieci nigdy nie mówi.
BLOCKED_STEMS = (
    "kurw", "chuj", "huj", "pierdol", "pierdal", "spierd", "wypierd", "jeba", "jebi", "jebn", "zajeb",
    "pizd", "cipa", "skurw", "dupek", "debil", "idiot", "kretyn", "glupek", "zabij", "zabic", "zabil",
    "smierc", "trup", "krew", "bron", "pistolet", "nienawidz",
)


def is_safe_reply(text: str) -> bool:
    if len(text) > MAX_REPLY_CHARS or "http" in text.lower():
        return False
    return not any(word.startswith(BLOCKED_STEMS) for word in words(text))


class SafeReplyResolver:
    """Opakowuje dowolny `IntentResolver` i usuwa kwestie, które nie przeszły sprawdzenia."""

    def __init__(self, inner: IntentResolver) -> None:
        self._inner = inner

    def resolve(self, scene: Scene, transcript: str) -> Interpretation:
        interpretation = self._inner.resolve(scene, transcript)
        if interpretation.reply and not is_safe_reply(interpretation.reply):
            log.warning("Kwestia modelu odrzucona przez filtr, mówię stałą kwestię ze scenariusza")
            return Interpretation(choice_id=interpretation.choice_id, reply="")
        return interpretation


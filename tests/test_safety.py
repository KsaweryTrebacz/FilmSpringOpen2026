import pytest

from bajka.ports import IntentResolver, Interpretation
from bajka.safety import MAX_REPLY_CHARS, SafeReplyResolver, is_safe_reply


@pytest.mark.parametrize(
    "reply",
    ["Do lasu! Trzymajcie się blisko mnie!", "Brawo, świetnie liczycie!", "Lornetka przybliża to, co daleko."],
)
def test_friendly_lines_pass(reply):
    assert is_safe_reply(reply)


@pytest.mark.parametrize(
    "reply",
    [
        "Ty debilu, idziemy do lasu!",
        "Zabijemy smoka!",
        "Wejdźcie na http://przyklad.pl",
        "Do lasu! " * 40,
        "Kurwa, ale las!",
    ],
)
def test_vulgar_violent_long_or_linking_lines_are_rejected(reply):
    assert not is_safe_reply(reply)


def test_polish_letters_do_not_hide_blocked_words():
    assert not is_safe_reply("Śmierć komarom!")


class FixedResolver:
    def __init__(self, interpretation):
        self._interpretation = interpretation

    def resolve(self, scene, transcript):
        return self._interpretation


def test_unsafe_reply_is_dropped_but_choice_is_kept(scenario):
    resolver = SafeReplyResolver(FixedResolver(Interpretation("las", "Ty kretynie, do lasu!")))

    assert isinstance(resolver, IntentResolver)
    assert resolver.resolve(scenario.scene("intro"), "do lasu") == Interpretation("las", "")


def test_safe_reply_passes_through(scenario):
    interpretation = Interpretation(None, "Las czy jaskinia? " * 2)
    assert len(interpretation.reply) < MAX_REPLY_CHARS

    assert SafeReplyResolver(FixedResolver(interpretation)).resolve(scenario.scene("intro"), "?") == interpretation

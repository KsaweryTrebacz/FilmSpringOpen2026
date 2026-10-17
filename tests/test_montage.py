import json
import threading
from types import SimpleNamespace

import pytest

from bajka.config import ConfigError
from bajka.montage import (
    ModelEditor,
    Montage,
    MontageSettings,
    PendingCut,
    RuleEditor,
    build_messages,
    checked_cut,
    describe_cut,
    parse_cut,
)
from bajka.ports import Cut, CutContext, Editor


def context(**fields):
    return CutContext(**{"from_scene": "kuferek", "to_scene": "las", "edge": "wybor", **fields})


# Reguły


def test_rules_fulfil_the_editor_contract():
    assert isinstance(RuleEditor(), Editor)


@pytest.mark.parametrize(
    ("fields", "transition", "seconds"),
    [
        ({}, "przenikanie", 0.6),
        ({"from_place": "Dziupla", "to_place": "Las"}, "przetarcie", 0.8),
        ({"to_ending": True}, "zaciemnienie", 1.2),
        ({"hint": "rozjasnienie"}, "rozjasnienie", 1.0),
        ({"edge": "reakcja"}, "przenikanie", 0.4),
    ],
)
def test_rules_pick_the_transition_from_place_ending_and_author_hint(fields, transition, seconds):
    cut = RuleEditor().cut(context(**fields))

    assert (cut.transition, cut.seconds, cut.source) == (transition, seconds, "reguly")
    assert cut.reason.endswith(".")


def test_excited_viewer_gets_longer_and_softer_transitions():
    cut = RuleEditor().cut(context(from_place="Dziupla", to_place="Las", viewer="pobudzenie"))

    assert (cut.transition, cut.seconds) == ("przenikanie", 1.2)
    assert "pobudzony" in cut.reason


def test_bored_viewer_gets_shorter_and_livelier_transitions():
    cut = RuleEditor().cut(context(viewer="znużenie"))

    assert (cut.transition, cut.seconds) == ("przetarcie", 0.4)
    assert "znużony" in cut.reason


def test_cut_is_kept_within_safe_limits():
    assert checked_cut("rozjasnienie", 0.1).seconds == 0.8  # bez błysków
    assert checked_cut("ciecie", 3.0).seconds == 0.0
    assert checked_cut("przenikanie", 9.0).seconds == 2.0
    assert checked_cut("przenikanie", 1.0, "x" * 200).reason == ""
    with pytest.raises(ValueError, match="nieznane przejście"):
        checked_cut("eksplozja", 1.0)


def test_cut_description_for_the_log():
    assert describe_cut(Cut("przenikanie", 0.6)) == "przenikanie 0,6 s"
    assert describe_cut(Cut()) == "ciecie"


# Model


def test_model_answer_is_parsed_leniently_and_checked():
    cut = parse_cut('```json\n{"transition": "Przetarcie", "seconds": 0.9, "reason": "Ruszamy do lasu."}\n```')

    assert cut == Cut("przetarcie", 0.9, "Ruszamy do lasu.", "model")
    with pytest.raises(ValueError):
        parse_cut("nie wiem")
    with pytest.raises(ValueError):
        parse_cut('{"transition": "wybuch", "seconds": 1}')


def test_prompt_tells_the_model_what_the_viewer_chose_said_and_felt():
    messages = build_messages(
        context(choice="Szumiący Las", meaning="iść przez las", how="glos", transcript="do lasu!", viewer="pobudzenie",
                from_place="Dziupla", to_place="Las", mood="zrownowazony"),
        Cut("przetarcie", 0.8),
    )  # fmt: skip

    facts = messages[1]["content"]
    for expected in ("Szumiący Las", "głosem", '"do lasu!"', "pobudzenie", "Dziupla -> Las", "przetarcie, 0.8 s"):
        assert expected in facts
    assert "JSON" in messages[0]["content"]


class FakeCompletions:
    def __init__(self, *replies):
        self._replies = list(replies)
        self.formats = []

    def create(self, **request):
        self.formats.append(request["response_format"])
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])


def model_editor(*replies, formats=({"type": "json_schema"}, {"type": "json_object"})):
    completions = FakeCompletions(*replies)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return ModelEditor(client, "phi", list(formats)), completions


def test_model_editor_falls_back_to_a_looser_format_when_the_server_refuses_the_schema():
    refused = Exception("400")
    refused.status_code = 400
    editor, completions = model_editor(refused, json.dumps({"transition": "przenikanie", "seconds": 1.4, "reason": "Spokojnie."}))

    assert isinstance(editor, Editor)
    assert editor.cut(context()) == Cut("przenikanie", 1.4, "Spokojnie.", "model")
    assert completions.formats == [{"type": "json_schema"}, {"type": "json_object"}]


# Montażysta: model w tle, reguły w zapasie


class SlowEditor:
    def __init__(self, cut=None, error=None):
        self.release = threading.Event()
        self._cut, self._error = cut, error

    def cut(self, context):
        self.release.wait(5)
        if self._error:
            raise self._error
        return self._cut


def test_model_decision_is_used_when_ready():
    editor = SlowEditor(Cut("rozjasnienie", 1.5, "Radosna chwila.", "model"))
    montage = Montage(editor, MontageSettings(wait_seconds=1.0))
    pending = montage.request(context())

    editor.release.set()  # model skończył, zanim przejście trzeba zagrać

    assert montage.result(pending) == Cut("rozjasnienie", 1.5, "Radosna chwila.", "model")


def test_rules_decide_when_the_model_is_late_or_fails():
    late = SlowEditor(Cut("rozjasnienie", 1.5))
    montage = Montage(late, MontageSettings(wait_seconds=0.05))

    cut = montage.result(montage.request(context()))
    late.release.set()

    assert (cut.transition, cut.source) == ("przenikanie", "reguly") and "nie zdążył" in cut.reason

    broken = SlowEditor(error=RuntimeError("model padł"))
    broken.release.set()
    montage = Montage(broken)
    assert montage.result(montage.request(context())).source == "reguly"


def test_without_a_model_the_rules_answer_at_once():
    pending = Montage().request(context(to_ending=True))

    assert isinstance(pending, PendingCut) and pending.future is None
    assert Montage().result(pending).transition == "zaciemnienie"


def test_settings_from_env():
    assert MontageSettings.from_env({}) == MontageSettings(use_model=True, wait_seconds=0.5)
    assert MontageSettings.from_env({"BAJKA_MONTAGE": "reguly", "BAJKA_MONTAGE_WAIT": "1.5"}) == MontageSettings(False, 1.5)
    with pytest.raises(ConfigError, match="BAJKA_MONTAGE"):
        MontageSettings.from_env({"BAJKA_MONTAGE": "magia"})

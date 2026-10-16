from bajka.console import ConsoleListener, ConsoleVoice


def test_listener_returns_typed_answer():
    assert ConsoleListener(read=lambda prompt: "  do lasu ").listen() == "do lasu"


def test_empty_line_is_silence():
    assert ConsoleListener(read=lambda prompt: "   ").listen() is None


def test_end_of_input_is_silence():
    def read(prompt):
        raise EOFError

    assert ConsoleListener(read=read).listen() is None


def test_voice_prints_hero_line():
    printed = []

    ConsoleVoice(write=printed.append).say("Do lasu!")

    assert printed == ["Bohater: Do lasu!"]

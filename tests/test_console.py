from bajka.console import ConsolePlayer, ConsoleViewer, ConsoleVoice
from bajka.ports import Answer, Compositor, Cut, Player, Shot, Viewer, Voice


def viewer(*typed):
    answers, printed = iter(typed), []

    def read(prompt):
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    return ConsoleViewer(read=read, write=printed.append), printed


def test_number_works_like_a_remote_button(scenario):
    console, printed = viewer("2")

    assert isinstance(console, Viewer)
    assert console.ask(scenario.scene("intro"), 12) == Answer(choice_id="jaskinia")
    assert printed[1:] == ["  1. Las", "  2. Jaskinia"]


def test_words_go_to_intent_recognition(scenario):
    console, _ = viewer("  do lasu ")

    assert console.ask(scenario.scene("intro"), 12) == Answer(transcript="do lasu")


def test_empty_line_number_out_of_range_and_end_of_input(scenario):
    scene = scenario.scene("intro")

    assert viewer("   ")[0].ask(scene, 12) == Answer()
    assert viewer("7")[0].ask(scene, 12) == Answer(transcript="7")  # „7” może być odpowiedzią na pytanie o liczbę
    assert viewer()[0].ask(scene, 12) == Answer()


def test_player_and_voice_print_what_would_be_on_screen(tmp_path):
    printed = []
    player, voice = ConsolePlayer(write=printed.append), ConsoleVoice(write=printed.append)

    player.play(tmp_path / "intro.mp4")
    player.loop(tmp_path / "intro_idle.mp4")
    voice.say("Do lasu!")

    assert isinstance(player, Player) and isinstance(voice, Voice)
    assert printed == ["[klip] intro.mp4", "[w pętli] intro_idle.mp4", "Postać: Do lasu!"]


def test_player_shows_the_montage_cut_and_layers(tmp_path):
    printed = []
    player = ConsolePlayer(write=printed.append)

    player.play_shot(Shot(tmp_path / "las.mp4", (tmp_path / "latarka.webm",), Cut("przetarcie", 0.8)))

    assert isinstance(player, Compositor)
    assert printed == ["[klip] las.mp4 (przetarcie 0,8 s; warstwy: latarka.webm)"]

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_process_ends_at_once_even_if_a_drawing_thread_is_still_running():
    """Wątki rysowania nie są demonami: bez twardego wyjścia Esc czekałby na obraz w toku (do 25 s + ffmpeg)."""
    script = (
        "import runpy, threading, time\n"
        "import bajka.app\n"
        "threading.Thread(target=time.sleep, args=(30,)).start()  # rysowanie w toku\n"
        "bajka.app.main = lambda argv=None: 7\n"
        "runpy.run_module('bajka', run_name='__main__')\n"
    )

    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, timeout=15, capture_output=True)

    assert result.returncode == 7


def test_logs_are_written_before_the_hard_exit():
    script = (
        "import logging, runpy\n"
        "import bajka.app\n"
        "def main(argv=None):\n"
        "    logging.basicConfig(level=logging.INFO, format='%(message)s')\n"
        "    logging.getLogger('bajka').info('ostatni wpis')\n"
        "    print('wynik na stdout')\n"
        "    return 0\n"
        "bajka.app.main = main\n"
        "runpy.run_module('bajka', run_name='__main__')\n"
    )

    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, timeout=20, capture_output=True, text=True)

    assert result.returncode == 0
    assert "wynik na stdout" in result.stdout
    assert "ostatni wpis" in result.stderr

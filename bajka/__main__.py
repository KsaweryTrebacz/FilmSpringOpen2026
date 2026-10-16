import logging
import os
import sys
import traceback

from bajka.app import main

try:
    code = main()
except SystemExit as exc:  # np. błędne argumenty: kod wyjścia bez zmian
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
except BaseException:  # Ctrl+C albo awaria: ślad błędu na stderr, a proces i tak kończymy twardo
    traceback.print_exc()
    code = 1
# Wątki rysowania (pula w silniku) nie są demonami: zwykłe wyjście czekałoby na obraz w toku (do 25 s + ffmpeg),
# a okno i mikrofon zostałyby w tle po Esc albo po wyjątku. Zamykamy proces od razu, po zapisaniu logów.
sys.stdout.flush()
sys.stderr.flush()
logging.shutdown()
os._exit(code)

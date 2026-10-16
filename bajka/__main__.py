import logging
import os
import sys

from bajka.app import main

code = main()
# Wątki rysowania (pula w silniku) nie są demonami: zwykłe wyjście czekałoby na obraz w toku (do 25 s + ffmpeg),
# a okno i mikrofon zostałyby w tle po Esc. Zamykamy proces od razu, po zapisaniu logów.
sys.stdout.flush()
sys.stderr.flush()
logging.shutdown()
os._exit(code)

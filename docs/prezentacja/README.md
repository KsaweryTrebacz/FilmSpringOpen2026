# Prezentacja produktu

Materiały do zgłoszenia (18.10, 19:00), pokazu online (29.10) i rozmów z serwisem albo wydawcą.

| Plik | Do czego |
|---|---|
| **[ZGLOSZENIE.md](ZGLOSZENIE.md)** / [PDF](ZGLOSZENIE.pdf) | **Zgłoszenie na 18.10, 19:00**: co to jest, problem, kto skorzysta, wyzwania, co sprawdziliśmy, co powstało na hackathonie. Czyta się bez prelegenta |
| [eksperyment/](eksperyment/) | Eksperyment z rozpoznawaniem odpowiedzi po słowach kluczowych (`python docs/prezentacja/eksperyment/slowa_kluczowe.py`) |
| **Prezentacja** ([link](https://claude.ai/artifact/LhY5PzguvLUpW7VHhCCYtg)) | 25 slajdów z notatkami prelegenta: zwiastun z dźwiękiem, cały odcinek do odtworzenia kliknięciem, mapa odcinka, galeria trzech wersji montażu lasu, nagranie „tętno a montaż”, zrzuty odtwarzacza, telefonu i panelu, makiety; jedna czcionka (Nunito). Link jest prywatny, dopóki właściciel nie udostępni go w menu Share; eksport do PDF i PowerPoint jest w tym samym menu |
| [PITCH.md](PITCH.md) | Scenariusz wystąpienia slajd po slajdzie: sesja online 29.10 (7 min) i rozmowa sprzedażowa, pytania i odpowiedzi |
| [ONE_PAGER.md](ONE_PAGER.md) / [PDF](ONE_PAGER.pdf) | Jedna strona do wysłania po spotkaniu |
| [KREATOR_RODZICA.md](KREATOR_RODZICA.md) | Koncepcja: rodzic składa odcinek (cele, liczba zagadek, czas, głos, limit), raport po odcinku |
| [BADANIA.md](BADANIA.md) | Badania nad bajkami interaktywnymi i wnioski dla produktu, ze źródłami |
| [mockupy/](mockupy/) | Makiety HTML Kreatora i raportu (otwórz w przeglądarce; zrzuty w `media/`) |
| [media/](media/) | Kadry z klipów, zrzuty prawdziwego odtwarzacza, telefonu i panelu, zwiastun i nagranie odtwarzacza |

## Skąd są materiały w `media/`

- `odcinek_przejscie.mp4` (ok. 3 min) i `odcinek.gif` — jedno przejście całego odcinka w **prawdziwym odtwarzaczu**
  (`python -m bajka … --no-llm --no-mic`, Chromium sterowany automatycznie) z klipami z 18.10. Obraz z nagrania
  przeglądarki, dźwięk z klipów odcinka, napisy u góry objaśniają kroki. Dwie odpowiedzi głosem są zainscenizowane
  (napis „Słyszę…” wstawiony ręcznie, bo nagranie powstało bez modelu mowy) i tak opisane w nagraniu.
- `tetno_montaz.mp4` (47 s), `tetno-dynamiczny.jpg`, `panel-tetno.jpg` — odtwarzacz i panel (`--panel`) obok siebie:
  symulator tętna (znużenie, potem pobudzenie) zmienia tempo, przejścia i wersje scen. Tętno jest symulowane.
- `zwiastun.mp4` (32 s, 1080p) — klipy z 18.10 połączone przejściami, które wybrałby montażysta: przenikanie
  w tym samym miejscu, przetarcie przy nowym miejscu, rozjaśnienie przed finałem.
- `mapa_odcinka.jpg` — etapy odcinka, odpowiedzi i gałęzie z kadrami klipów; paski oznaczają klipy jeszcze
  niewygenerowane.
- `okno-wyboru.jpg`, `okno-glos.jpg`, `galaz-sowa.jpg`, `start.jpg`, `koniec.jpg` — zrzuty z tego samego nagrania.
- `demo_z_napisami.mp4`, `okno-kuferek.jpg`, `okno-droga-glos.jpg`, `okno-deski.jpg`, `po-desce.jpg`,
  `przejscie-most.jpg`, `reakcja-hopsasa.jpg`, `scena-powitanie.jpg` — wcześniejsze nagranie i zrzuty z 17.10
  (pierwsza partia klipów, droga przez mostek).
- `kadr_*.jpg` — klatki z pierwszej partii klipów w [`download/`](../../download/) (17.10).
- `panel.jpg`, `panel-drzewo.jpg`, `panel-dziennik.jpg` — panel podglądu (`--panel`) po pełnym przejściu odcinka.
- `telefon-*.jpg` — aplikacja na telefon (`--mobile`): dołączanie, pytanie z odpowiedziami, strona z kodem QR.
  Zrzuty telefonu powstały bez modelu mowy (odpowiedzi dotykiem).
- `kreator.png`, `raport.png` — zrzuty makiet z `mockupy/`.
- Wszystkie ekrany aplikacji, makiety, PDF-y, nagrania i slajdy używają jednej czcionki: Nunito (SIL OFL, `bajka/fonts/`).

Zrzuty odtwarzacza odświeżysz, uruchamiając odcinek i robiąc zrzuty ekranu przy oknach wyboru
([DEMO_DLA_JURY.md](../DEMO_DLA_JURY.md)).

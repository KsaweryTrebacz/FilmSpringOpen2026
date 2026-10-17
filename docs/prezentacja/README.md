# Prezentacja produktu

Materiały do zgłoszenia (18.10, 19:00), pokazu online (29.10) i rozmów z serwisem albo wydawcą.

| Plik | Do czego |
|---|---|
| **[ZGLOSZENIE.md](ZGLOSZENIE.md)** / [PDF](ZGLOSZENIE.pdf) | **Zgłoszenie na 18.10, 19:00**: co to jest, problem, kto skorzysta, wyzwania, co sprawdziliśmy, co powstało na hackathonie. Czyta się bez prelegenta |
| [eksperyment/](eksperyment/) | Eksperyment z rozpoznawaniem odpowiedzi po słowach kluczowych (`python docs/prezentacja/eksperyment/slowa_kluczowe.py`) |
| **Slajdy** (Claude, [link](https://claude.ai/artifact/LhY5PzguvLUpW7VHhCCYtg)) | 24 slajdy z notatkami prelegenta: zrzuty odtwarzacza, telefonu i panelu w ramkach urządzeń, nagranie odtwarzacza, zwiastun i makiety; jedna czcionka (Nunito), tytuły-tezy, numery stron. Link jest prywatny, dopóki właściciel nie udostępni go w menu Share; eksport do PDF i PowerPoint jest w tym samym menu |
| [PITCH.md](PITCH.md) | Scenariusz wystąpienia slajd po slajdzie: sesja online 29.10 (7 min) i rozmowa sprzedażowa, pytania i odpowiedzi |
| [ONE_PAGER.md](ONE_PAGER.md) / [PDF](ONE_PAGER.pdf) | Jedna strona do wysłania po spotkaniu |
| [KREATOR_RODZICA.md](KREATOR_RODZICA.md) | Koncepcja: rodzic składa odcinek (cele, liczba zagadek, czas, głos, limit), raport po odcinku |
| [BADANIA.md](BADANIA.md) | Badania nad bajkami interaktywnymi i wnioski dla produktu, ze źródłami |
| [mockupy/](mockupy/) | Makiety HTML Kreatora i raportu (otwórz w przeglądarce; zrzuty w `media/`) |
| [media/](media/) | Kadry z klipów, zrzuty prawdziwego odtwarzacza, telefonu i panelu, zwiastun i nagranie odtwarzacza |

## Skąd są materiały w `media/`

- `kadr_*.jpg` — klatki z klipów w [`download/`](../../download/) (generator wideo, 17.10).
- `zwiastun.mp4` (35 s) — klipy powitania, kuferka, mapy i mostka połączone przejściami, które wybrałby montażysta:
  przenikanie w tej samej dziupli, przetarcie przy wyjściu w nowe miejsce, zaciemnienie na końcu.
- `demo_z_napisami.mp4` — to samo nagranie z napisami, które objaśniają każdy krok (do zgłoszenia).
- `demo_odtwarzacz.mp4` (60 s), `okno-*.jpg`, `reakcja-*.jpg`, `przejscie-*.jpg`, `scena-*.jpg` — nagranie
  i zrzuty **prawdziwego odtwarzacza** (`python -m bajka … --no-llm --no-mic`) z klipami z `download/`.
  Wybór głosem w nagraniu jest zainscenizowany (napis „Słyszę…” wstawiony ręcznie, bo nagranie powstało bez
  mikrofonu); w odcinku robi to mikrofon i Whisper.
- `start.jpg`, `koniec.jpg` — ekran startowy (z opcją odpowiedzi głosem, jak przy włączonym mikrofonie) i ekran końcowy.
- `panel.jpg`, `panel-drzewo.jpg`, `panel-dziennik.jpg` — panel podglądu (`--panel`) po pełnym przejściu odcinka.
- `telefon-*.jpg` — aplikacja na telefon (`--mobile`): dołączanie, pytanie z odpowiedziami, strona z kodem QR.
  Zrzuty telefonu powstały bez modelu mowy (odpowiedzi dotykiem).
- Wszystkie ekrany aplikacji, makiety, PDF-y i slajdy używają jednej czcionki: Nunito (SIL OFL, `bajka/fonts/`).
- `kreator.png`, `raport.png` — zrzuty makiet z `mockupy/`.

Zrzuty odtwarzacza odświeżysz, uruchamiając odcinek i robiąc zrzuty ekranu przy oknach wyboru
([DEMO_DLA_JURY.md](../DEMO_DLA_JURY.md)).

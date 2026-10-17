# Prezentacja produktu

Materiały do pokazania i sprzedaży projektu: od pitchu na jury po rozmowę z serwisem albo wydawcą.

| Plik | Do czego |
|---|---|
| **Slajdy** (Claude, [link](https://claude.ai/artifact/LhY5PzguvLUpW7VHhCCYtg)) | 18 slajdów z notatkami prelegenta, kadrami z klipów, nagraniem odtwarzacza i makietami. Link jest prywatny, dopóki właściciel nie udostępni go w menu Share; eksport do PDF i PowerPoint jest w tym samym menu |
| [PITCH.md](PITCH.md) | Scenariusz wystąpienia slajd po slajdzie, wersja na jury (7 min) i sprzedażowa, pytania i odpowiedzi |
| [ONE_PAGER.md](ONE_PAGER.md) | Jedna strona do wysłania po spotkaniu |
| [KREATOR_RODZICA.md](KREATOR_RODZICA.md) | Koncepcja: rodzic składa odcinek (cele, liczba zagadek, czas, głos, limit), raport po odcinku |
| [BADANIA.md](BADANIA.md) | Badania nad bajkami interaktywnymi i wnioski dla produktu, ze źródłami |
| [mockupy/](mockupy/) | Makiety HTML Kreatora i raportu (otwórz w przeglądarce; zrzuty w `media/`) |
| [media/](media/) | Kadry z klipów, zrzuty prawdziwego odtwarzacza i panelu, zwiastun i nagranie odtwarzacza |

## Skąd są materiały w `media/`

- `kadr_*.jpg` — klatki z klipów w [`download/`](../../download/) (generator wideo, 17.10).
- `zwiastun.mp4` (35 s) — klipy powitania, kuferka, mapy i mostka połączone przejściami, które wybrałby montażysta:
  przenikanie w tej samej dziupli, przetarcie przy wyjściu w nowe miejsce, zaciemnienie na końcu.
- `demo_odtwarzacz.mp4` (60 s), `okno-*.jpg`, `reakcja-*.jpg`, `przejscie-*.jpg`, `scena-*.jpg` — nagranie
  i zrzuty **prawdziwego odtwarzacza** (`python -m bajka … --no-llm --no-mic`) z klipami z `download/`.
  Wybór głosem w nagraniu jest zainscenizowany (napis „Słyszę…” wstawiony ręcznie, bo nagranie powstało bez
  mikrofonu); w odcinku robi to mikrofon i Whisper.
- `panel.jpg`, `koniec.jpg` — panel podglądu (`--panel`) i ekran końcowy po pełnym przejściu odcinka.
- `kreator.png`, `raport.png` — zrzuty makiet z `mockupy/`.

Zrzuty odtwarzacza odświeżysz, uruchamiając odcinek i robiąc zrzuty ekranu przy oknach wyboru
([DEMO_DLA_JURY.md](../DEMO_DLA_JURY.md)).

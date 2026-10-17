# Wprowadzenie: jak działa program

Ten tekst tłumaczy **zamysł i działanie programu** — bez wchodzenia w fabułę konkretnego odcinka. Czytanie zajmie
ok. 10 minut. Szczegóły techniczne są w dokumentach podlinkowanych po drodze.

## Zamysł w jednym akapicie

Program zamienia zwykły odcinek animowany w **bajkę interaktywną do oglądania w serwisie streamingowym**. Odcinek
jest pocięty na sceny. Po scenie z pytaniem na ekranie pojawia się **okno wyboru**: dziecko wybiera pilotem,
dotykiem albo mówi odpowiedź na głos. Program rozpoznaje, co wybrało, postać reaguje, a odcinek idzie dalej
wybraną ścieżką. Sam program nie zna żadnej historii: historia jest wymiennym plikiem — **scenariuszem** —
a program to **silnik**, który ją odtwarza. Rozpoznawanie mowy i modele działają na urządzeniu widza, bez chmury
i bez przechowywania nagrań. W przyszłości tempo odcinka może się dopasowywać do **tętna** dziecka z zegarka.

## Trzy filary

1. **Scenariusz jako graf scen.** Plik YAML opisuje sceny, ich klipy wideo, pytania, opcje w oknie wyboru
   (z obrazkami), reakcje postaci i to, dokąd prowadzi każda odpowiedź. Zmiana historii = zmiana pliku, bez kodu.
2. **Silnik, który nigdy nie staje.** Prowadzi widza po grafie, a każdy błąd (mikrofon, model, głos, sieć) obsługuje
   po cichu: dopytuje albo wybiera ścieżkę domyślną. Odcinek ma trwać, cokolwiek się zepsuje.
3. **Wymienne moduły.** Odtwarzacz, okno wyboru, rozpoznawanie mowy, rozumienie odpowiedzi i głos postaci to osobne
   moduły, które rozmawiają z silnikiem tylko przez umówione interfejsy (`bajka/ports.py`). Każdy można wymienić —
   np. odtwarzacz w przeglądarce na VLC albo lokalne AI na chmurę — i testować bez reszty programu.

## Cykl jednej sceny

```
klip ──▶ pętla oczekiwania + okno wyboru ──▶ wybór (pilot / dotyk / głos) ──▶ reakcja postaci ──▶ następna scena
                     ▲                                                               │
                     └──── czas minął / niejasna odpowiedź: dopytanie ◀──────────────┘
                           (po dwóch dopytaniach: postać wybiera sama)
```

1. **Klip** — gotowe wideo kończy się pytaniem postaci do widza.
2. **Okno wyboru** — klip przechodzi w cichą pętlę oczekiwania, a na dole ekranu pojawiają się 2–3 opcje z obrazkami
   i paskiem odliczania (domyślnie 12 s). Jeśli rodzic włączył mikrofon, strona w tym czasie nasłuchuje.
3. **Wybór** — przycisk rozstrzyga od razu; wypowiedź przechodzi przez rozpoznawanie (niżej).
4. **Reakcja** — gra nagrany klip reakcji postaci; jeśli go nie ma, postać mówi kwestię ze scenariusza
   (napisy + głos syntezatora). Przy odpowiedzi głosem model może dopisać krótką osobistą kwestię.
5. **Następna scena** — według grafu. Scena bez pytań kończy odcinek; ekran końcowy pokazuje wybory widza
   i proponuje obejrzenie jeszcze raz.

## Skąd przychodzą odpowiedzi

| Kanał | Kiedy | Jak działa |
|---|---|---|
| **Okno wyboru w odtwarzaczu** | Zawsze (domyślny `--player web`) | Strona w przeglądarce: strzałki i OK na pilocie (Enter na klawiaturze), dotyk, mysz, cyfry. Odpowiedź głosem: strona nagrywa wypowiedź, a komputer rozpoznaje ją lokalnie |
| **Drugi ekran** (`--mobile`) | Telewizor bez mikrofonu albo kilkoro dzieci | Telefon domownika jako pilot z mikrofonem: skanuje kod QR, pokazuje opcje, nagrywa odpowiedź. Przy kilku telefonach wygrywa większość |
| **Mikrofon komputera** (`--player vlc`) | Dawny tryb pełnoekranowy | Bez przycisków: tylko głos z mikrofonu komputera |
| **Konsola** (`--text`) | Próby bez sprzętu | Cyfra = przycisk, tekst = odpowiedź głosem; klipy są tylko wypisywane |

Czas minął, cisza albo niezrozumiała odpowiedź oznaczają dopytanie i ponowne okno wyboru. Po dwóch nieudanych
próbach postać sama wybiera ścieżkę domyślną ze scenariusza i mówi to wprost.

## Jak program rozumie odpowiedź głosem

Rozpoznanie idzie od najtańszego do najmądrzejszego kroku:

1. **Mowa → tekst** — model Whisper działający lokalnie (Foundry Local, także na NPU w Copilot+ PC).
2. **Słowa kluczowe** — natychmiastowe dopasowanie do słów zapisanych przy każdej opcji w scenariuszu, z tolerancją
   na odmianę („lasu” ≈ „las”). Większość krótkich odpowiedzi kończy się tutaj.
3. **Model językowy** — dla odpowiedzi opisowych („tam, gdzie ciemno”): lokalny model Phi rozpoznaje wybór i pisze
   reakcję postaci. Odpowiedź modelu jest wymuszona jako JSON z dozwolonymi opcjami.
4. **Filtr bezpieczeństwa** — kwestia z modelu z wulgaryzmem, przemocą, linkiem albo za długa nie zostaje
   wypowiedziana; postać mówi wtedy sprawdzoną kwestię ze scenariusza.

Gdy model zawiedzie, wybór i tak rozpoznają słowa kluczowe. Program nie zgaduje, gdy nie wie: wtedy dopytuje.

## Odcinek, który czuje widza (tętno — przyszłość)

Scenariusz mówi, jakiej dynamiki chcemy (`mood`), a wybrane sceny mają inne wersje montażu (`variants`: spokojna,
żywa). Gdy tętno dziecka mocno rośnie, scena gra wersję spokojną; gdy spada (znużenie) — żywą. Dziś tętno pochodzi
z symulatora sterowanego z **panelu podglądu** (strona z drzewem scen, wyborami, wykresem tętna i powodem każdej
decyzji odcinka). Zegarek to plan na przyszłość, z twardymi zasadami prywatności ([STREAMING.md](STREAMING.md)).

## Jak odcinek trafia do widza

| Droga | Polecenie | Co to daje |
|---|---|---|
| Nasz odtwarzacz | `python -m bajka SCENARIUSZ` | Pełna interakcja: okna wyboru, głos, reakcje, tętno |
| Manifest JSON | `python -m bajka.manifest SCENARIUSZ` | Graf scen dla odtwarzacza interaktywnego serwisu |
| Wersja liniowa | `python -m bajka.linear SCENARIUSZ` | Zwykły film z tych samych klipów (+ napisy) dla serwisów bez interakcji |

## Tryby działania

| Tryb | Co robi | Przykład |
|---|---|---|
| domyślny | Odtwarzacz w przeglądarce, okna wyboru, głos; AI lokalnie (`local`) | `python -m bajka SCENARIUSZ` |
| `--no-mic` / `--no-llm` | Bez rozpoznawania mowy / bez modelu językowego (tylko słowa kluczowe) | `--no-llm --no-mic`: szybki pokaz bez modeli |
| `--text` | Cały odcinek w konsoli, bez wideo | `--text --no-llm` |
| `--player vlc` | Pełny ekran VLC, odpowiedzi tylko głosem | stary tryb pokazowy |
| `--mobile` | Drugi ekran: telefony jako pilot z mikrofonem | `--mobile` |
| `--panel` | Panel podglądu i symulowane tętno widza | `--panel` |
| `--backend azure` | Rozpoznawanie mowy, model i głos przez usługi Azure | `--backend azure` |

## Mapa kodu

| Warstwa | Moduły |
|---|---|
| Scenariusz | `bajka/scenario.py` — wczytanie i walidacja grafu scen |
| Silnik | `bajka/engine.py` — cykl scen, okna wyboru, dopytywanie, reakcje, wersje scen; `bajka/app.py` — złożenie całości |
| Interfejsy | `bajka/ports.py` — `Player`, `Viewer`, `Listener`, `Voice`, `IntentResolver`, `Audience`, `AudiencePulse`, `ShowObserver` |
| Odtwarzacz | `bajka/web_player.py` + `bajka/player_app/` (przeglądarka), `bajka/player.py` (VLC), `bajka/console.py` (próby) |
| Dystrybucja | `bajka/manifest.py` (JSON), `bajka/linear.py` (wersja liniowa), `bajka/placeholders.py` (klipy zastępcze) |
| Odpowiedzi | okno wyboru w `player_app`, `bajka/mobile.py` + `bajka/mobile_app/` (drugi ekran), `bajka/local_stt.py`, `bajka/stt.py` (mowa) |
| Rozumienie | `bajka/keywords.py`, `bajka/local_intent.py`, `bajka/intent.py`, `bajka/foundry.py`, `bajka/safety.py` |
| Głos postaci | synteza mowy przeglądarki (odtwarzacz web), `bajka/local_tts.py` (Windows, VLC), `bajka/tts.py` (Azure) |
| Tętno i panel | `bajka/pulse.py` (symulator, stan widza), `bajka/panel.py` + `bajka/panel_app/` (panel podglądu) |

Każdy moduł ma własne demo uruchamiane bez reszty programu, np. `python -m bajka.keywords`, `python -m bajka.manifest`,
`python -m bajka.mobile` (pełna lista w README). Testy (`python -m pytest`) działają bez sieci, mikrofonu,
przeglądarki i VLC.

## Założenia projektowe

- **Odporność ponad wszystko.** Każdy kontakt ze światem zewnętrznym (mikrofon, model, sieć, syntezator, przeglądarka)
  jest opakowany obsługą błędu z zapasowym zachowaniem.
- **Pilot przede wszystkim, głos jako dodatek.** Okno wyboru działa na każdym telewizorze; głos tam, gdzie jest
  mikrofon i zgoda rodzica.
- **Lokalnie, jeśli się da.** Prywatność dzieci i działanie bez internetu; chmura tylko jako alternatywa.
- **Najpierw prosto, potem mądrze.** Słowa kluczowe przed modelem językowym; nagrane reakcje i stałe kwestie
  ze scenariusza jako siatka bezpieczeństwa dla kwestii pisanych przez model.
- **Treść oddzielona od kodu.** Pytania, opcje, obrazki, słowa kluczowe, reakcje i klipy żyją w scenariuszu, więc autor
  historii nie potrzebuje programisty.
- **Uczciwie wobec dziecka.** Odcinek ma koniec, nie startuje sam kolejny; tętno zmienia tylko tempo sceny.
- **Prywatność.** Mikrofon działa tylko w oknie wyboru; nagranie trafia na chwilę do pliku tymczasowego (dla
  rozpoznawania mowy) i jest usuwane zaraz po rozpoznaniu.

## Słowniczek

| Pojęcie | Znaczenie |
|---|---|
| **Scenariusz** | Plik YAML z grafem scen — jedyne miejsce, gdzie żyje historia |
| **Scena** | Klip wideo, opcjonalnie z pytaniem, oknem wyboru i przejściami do kolejnych scen |
| **Okno wyboru** | Opcje z obrazkami i odliczaniem na dole ekranu, po pytaniu postaci |
| **Pętla oczekiwania** (`idle`) | Cichy, zapętlony klip — tło okna wyboru |
| **Reakcja** (`reaction`) | Krótki nagrany klip: jak postać reaguje na konkretny wybór |
| **Drugi ekran** | Telefon domownika jako pilot z mikrofonem (`--mobile`) |
| **Wersja liniowa** | Zwykły film z tych samych klipów, bez okien wyboru |
| **Manifest** | Graf scen jako JSON dla odtwarzacza serwisu |
| **Backend** | Skąd bierzemy AI: `local` (urządzenie) albo `azure` (chmura) |
| **Zaślepka** | Kolorowy klip zastępczy, dopóki nie ma prawdziwego wideo |
| **Nastrój odcinka** (`mood`) | Jakiej dynamiki chcemy: `spokojny`, `zywy` albo `zrownowazony` |
| **Wersja sceny** (`variants`) | Inny montaż sceny (spokojna, żywa), grany według tętna widza |
| **Punkt odniesienia** | Tętno widza tuż po pierwszej scenie; z nim porównujemy kolejne odczyty |

## Gdzie dalej

| Dokument | Po co |
|---|---|
| [README](../README.md) | Instalacja, uruchamianie, wszystkie tryby, rozwiązywanie problemów |
| [STREAMING.md](STREAMING.md) | Dlaczego streaming, realia rynku, drogi do serwisów, tętno i prywatność, propozycje |
| [PODZIAL_PRACY.md](PODZIAL_PRACY.md) | Kto rozwija który moduł, zasady modułów i pracy w Git |
| [LOKALNE_AI.md](LOKALNE_AI.md) | Foundry Local, Whisper, Phi, NPU, głos |
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Produkcja klipów i dobór modeli (rysowanie na żywo wycofane) |
| [Odcinek, który czuje widza](superpowers/specs/2026-10-16-film-czuje-sale-design.md) | Tętno, wersje scen, panel (projekt z czasów seansu kinowego) |
| [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md) | Przebieg pokazu przed jury |
| [DO_ZROBIENIA.md](DO_ZROBIENIA.md) | Co zostało do zrobienia |

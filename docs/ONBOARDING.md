# Wprowadzenie: jak działa program

Ten tekst tłumaczy **zamysł i działanie programu** — bez wchodzenia w fabułę konkretnego filmu. Czytanie zajmie
ok. 10 minut. Szczegóły techniczne są w dokumentach podlinkowanych po drodze.

## Zamysł w jednym akapicie

Program zamienia zwykły film w **film, który słucha widowni**. Film jest pocięty na sceny. Po scenie z pytaniem
program zbiera odpowiedzi widzów (głosem — do telefonu albo okrzykiem całej sali), rozpoznaje, co wybrali,
pozwala postaci zareagować na żywo i wybiera kolejną scenę. Sam program nie zna żadnej historii: historia jest
wymiennym plikiem — **scenariuszem** — a program to **silnik**, który ją odtwarza. Wszystko może działać na jednym
komputerze z Windows, bez chmury i bez nagrywania widzów. Wyjątek: sceny rysowane na żywo potrzebują Azure, internetu
i ffmpeg (patrz niżej).

## Trzy filary

1. **Scenariusz jako graf scen.** Plik YAML opisuje sceny, ich klipy wideo, pytania, możliwe odpowiedzi i to,
   dokąd prowadzi każda odpowiedź. Zmiana historii = zmiana pliku, bez zmian w kodzie.
2. **Silnik, który nigdy nie staje.** Prowadzi widza po grafie, a każdy błąd (mikrofon, model, głos, sieć) obsługuje
   po cichu: dopytuje, wybiera ścieżkę domyślną albo pokazuje klip zapasowy. Pokaz ma trwać, cokolwiek się zepsuje.
3. **Wymienne moduły.** Odtwarzacz, rozpoznawanie mowy, rozumienie odpowiedzi, głos postaci i rysowanie obrazów
   to osobne moduły, które rozmawiają z silnikiem tylko przez umówione interfejsy (`bajka/ports.py`). Każdy można
   wymienić — np. lokalne AI na usługi w chmurze — i testować bez reszty programu.

## Cykl jednej sceny

```
klip ──▶ cicha pętla oczekiwania ──▶ odpowiedzi widowni ──▶ rozpoznanie wyboru ──▶ reakcja postaci ──▶ następna scena
                                          ▲                                                  │
                                          └──── cisza / niejasna odpowiedź: dopytanie ◀──────┘
                                                (po kilku próbach: wybór domyślny)
```

1. **Klip** — gotowe wideo kończy się pytaniem postaci do widowni.
2. **Pętla oczekiwania** — krótki, cichy, zapętlony klip trwa, dopóki zbieramy odpowiedzi (cisza jest ważna, bo wtedy
   słucha mikrofon).
3. **Odpowiedzi** — przychodzą jednym z kanałów opisanych niżej.
4. **Rozpoznanie** — z wypowiedzi powstaje wybór spośród opcji zapisanych w scenariuszu.
5. **Reakcja** — postać mówi na żywo (syntezator mowy) krótką kwestię dopasowaną do odpowiedzi.
6. **Następna scena** — według grafu. Scena bez pytań kończy film.

## Skąd przychodzą odpowiedzi

Program sam wybiera kanał, zależnie od tego, co jest dostępne na sali:

| Kanał | Kiedy | Jak działa |
|---|---|---|
| **Aplikacja mobilna** | Widzowie połączyli telefony | Komputer uruchamia lokalny serwer HTTPS; widz skanuje kod QR i otwiera aplikację w przeglądarce (bez instalacji). Przy pytaniu telefon pokazuje opcje i sam nagrywa odpowiedź, wykrywając początek i koniec mowy. Komputer rozpoznaje nagrania i **liczy głosy — wygrywa większość** |
| **Krzykomierz** | Brak telefonów, scena decyzji (`vote`) | Postać wzywa po kolei do każdej opcji („Kto za opcją A? Krzyczymy!”), mikrofon przy ekranie mierzy głośność okrzyków — **wygrywa najgłośniejsza** |
| **Mikrofon na sali** | Brak telefonów, pozostałe pytania | Mikrofon słucha odpowiedzi wykrzyczanej chórem albo jednej osoby (np. na pokazie dla jury) |
| **Konsola** | Próby bez sprzętu (`--text`) | Odpowiedzi i głośność okrzyków wpisuje się z klawiatury |

Remis, cisza albo niezrozumiała odpowiedź oznaczają dopytanie i kolejną rundę. Po kilku nieudanych próbach postać
sama wybiera ścieżkę domyślną ze scenariusza.

## Jak program rozumie odpowiedź

Rozpoznanie idzie od najtańszego do najmądrzejszego kroku:

1. **Mowa → tekst** — model Whisper działający lokalnie (Foundry Local, także na NPU w Copilot+ PC).
2. **Słowa kluczowe** — natychmiastowe dopasowanie do słów zapisanych przy każdej opcji w scenariuszu, z tolerancją
   na odmianę („lasu” ≈ „las”). Większość krótkich odpowiedzi kończy się tutaj.
3. **Model językowy** — tylko dla odpowiedzi niejasnych: lokalny model Phi rozumie opisowe wypowiedzi („tam, gdzie
   ciemno”) i od razu pisze reakcję postaci. Odpowiedź modelu jest wymuszona jako JSON z dozwolonymi opcjami.
4. **Filtr bezpieczeństwa** — kwestia z modelu z wulgaryzmem, przemocą, linkiem albo za długa nie zostaje
   wypowiedziana; postać mówi wtedy sprawdzoną kwestię ze scenariusza.

Gdy model zawiedzie, wybór i tak rozpoznają słowa kluczowe. Program nie zgaduje, gdy nie wie: wtedy dopytuje.

## Pytania otwarte i obrazy na żywo (opcjonalnie)

Scena może też zadać **pytanie otwarte** („Jak to wygląda?”). Wtedy pomysł widza zamienia się w ilustrację:

```
wypowiedź ──▶ model językowy: kwestia postaci + bezpieczny opis obrazu ──▶ model obrazu ──▶ ruch kamery (ffmpeg) ──▶ nowy klip
```

W czasie rysowania leci pętla „postać rysuje”, a postać mówi swoją kwestię. Pomysł zostaje zapamiętany
i może wrócić w kolejnych scenach. Gdy rysowanie potrwa zbyt długo albo się nie uda, program pokazuje gotowy klip
zapasowy. Ta część korzysta z chmury (Azure OpenAI pisze kwestię i opis, Azure AI Foundry rysuje); do chmury
trafia tylko tekst, nigdy nagranie.

## Tryby działania

| Tryb | Co robi | Przykład |
|---|---|---|
| `local` (domyślny) | Rozpoznawanie mowy, model językowy i głos postaci na komputerze; bez kluczy i internetu po pierwszym pobraniu modeli (wyjątek: sceny rysowane na żywo — klucze Azure, internet i ffmpeg) | `python -m bajka SCENARIUSZ` |
| `azure` | To samo przez usługi Azure | `--backend azure` |
| `--mobile` | Odpowiedzi z telefonów widzów | `python -m bajka SCENARIUSZ --mobile` |
| `--no-llm` | Bez modelu językowego przy wyborze ścieżki, tylko słowa kluczowe (sceny rysowane na żywo dalej korzystają z Azure) | na słabszym komputerze i do prób |
| `--text` | Próba bez mikrofonu i głośnika (konsola) | `--text --no-llm --windowed` |

## Mapa kodu

| Warstwa | Moduły |
|---|---|
| Scenariusz | `bajka/scenario.py` — wczytanie i walidacja grafu scen |
| Silnik | `bajka/engine.py` — cykl scen, kanały odpowiedzi, dopytywanie, ścieżki awaryjne; `bajka/app.py` — złożenie całości |
| Interfejsy | `bajka/ports.py` — `Player`, `Listener`, `Voice`, `IntentResolver`, `Audience`, `ShoutMeter`, `Imaginer`, `Illustrator`, `Animator` |
| Obraz | `bajka/player.py` (VLC), `bajka/placeholders.py` (klipy zastępcze) |
| Odpowiedzi widowni | `bajka/mobile.py` + `bajka/mobile_app/` (telefony), `bajka/vote.py` (krzykomierz), `bajka/local_stt.py`, `bajka/stt.py` (mikrofon), `bajka/console.py` (próby) |
| Rozumienie | `bajka/keywords.py`, `bajka/local_intent.py`, `bajka/intent.py`, `bajka/foundry.py`, `bajka/safety.py` |
| Głos postaci | `bajka/local_tts.py` (Windows), `bajka/tts.py` (Azure) |
| Obrazy na żywo | `bajka/imagine.py`, `bajka/illustrate.py`, `bajka/motion.py` |

Każdy moduł ma własne demo uruchamiane bez reszty programu, np. `python -m bajka.keywords`, `python -m bajka.vote`,
`python -m bajka.mobile` (pełna lista w README). Testy (`python -m pytest`) działają bez sieci, mikrofonu i VLC.

## Założenia projektowe

- **Odporność ponad wszystko.** Każdy kontakt ze światem zewnętrznym (mikrofon, model, sieć, syntezator) jest
  opakowany obsługą błędu z zapasowym zachowaniem.
- **Lokalnie, jeśli się da.** Prywatność widzów i działanie bez internetu w kinie; chmura tylko tam, gdzie lokalnie
  się nie da (obrazy na żywo) albo jako alternatywa.
- **Najpierw prosto, potem mądrze.** Słowa kluczowe przed modelem językowym; stałe kwestie ze scenariusza jako
  siatka bezpieczeństwa dla kwestii pisanych przez model.
- **Treść oddzielona od kodu.** Pytania, opcje, słowa kluczowe, reakcje i klipy żyją w scenariuszu, więc autor
  historii nie potrzebuje programisty.
- **Prywatność.** Nagrania są przetwarzane w pamięci i nie są zapisywane; obrazy z seansu trafiają do katalogu
  tymczasowego, czyszczonego przy następnym starcie.

## Słowniczek

| Pojęcie | Znaczenie |
|---|---|
| **Scenariusz** | Plik YAML z grafem scen — jedyne miejsce, gdzie żyje historia |
| **Scena** | Klip wideo, opcjonalnie z pytaniem, opcjami i przejściami do kolejnych scen |
| **Pętla oczekiwania** (`idle`) | Cichy, zapętlony klip po pytaniu, w trakcie którego zbieramy odpowiedzi |
| **Runda** | Jedna próba zebrania odpowiedzi na pytanie |
| **Scena `vote`** | Scena decyzji, którą bez telefonów rozstrzyga krzykomierz |
| **Scena `open`** | Pytanie otwarte; pomysł widza jest rysowany na żywo |
| **Klip zapasowy** | Gotowy klip na wypadek, gdy obraz na żywo się nie uda |
| **Backend** | Skąd bierzemy AI: `local` (komputer) albo `azure` (chmura) |
| **Zaślepka** | Kolorowy klip zastępczy, dopóki nie ma prawdziwego wideo |

## Gdzie dalej

| Dokument | Po co |
|---|---|
| [README](../README.md) | Instalacja, uruchamianie, wszystkie tryby, rozwiązywanie problemów |
| [PODZIAL_PRACY.md](PODZIAL_PRACY.md) | Kto rozwija który moduł, zasady modułów i pracy w Git |
| [LOKALNE_AI.md](LOKALNE_AI.md) | Foundry Local, Whisper, Phi, NPU, głos Windows |
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Obrazy na żywo i dobór modeli |
| [DO_ZROBIENIA.md](DO_ZROBIENIA.md) | Co zostało do zrobienia |

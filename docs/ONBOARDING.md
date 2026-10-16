# Witaj w projekcie „Bzyczka szuka domu”

Ten tekst to pierwsze wprowadzenie do projektu — dla programistów, ale też dla osób od scenariusza, animacji,
dźwięku i pitchu. Czytanie zajmie ok. 10 minut. Szczegóły są w dokumentach podlinkowanych po drodze.

## W jednym akapicie

Tworzymy **interaktywny animowany film krótkometrażowy dla dzieci (4–7 lat)**, który ogląda się w kinie i który
**słucha widowni**. Bohaterka, Lila Lupka, zadaje pytania, a dzieci odpowiadają głosem — do telefonu albo
okrzykiem całej sali. Od odpowiedzi zależy dalszy ciąg filmu, a Lila reaguje na nie na żywo. Całe AI może działać
na jednym komputerze w kinie, bez chmury i bez nagrywania dzieci. Projekt powstaje na hackathonie
**„Kino szuka nowej formy. Znajdź ją.”** (21. Plenery Film Spring Open, Kraków, 16–18.10.2026). Prezentacja przed
jury: **18.10.2026, 19:00**.

## Co przeżywa widz

1. Przed seansem na ekranie wisi kod QR. Opiekun skanuje go telefonem, otwiera aplikację w przeglądarce
   i zezwala na mikrofon. Niczego nie trzeba instalować.
2. Zaczyna się film. Lila i jej przyjaciel Fiku prowadzą Klub Ciekawskich w dziupli starego dębu. Wpada zagubiona
   pszczółka Bzyczka — trzeba jej pomóc wrócić do ula.
3. Kiedy w rogu ekranu pulsuje **Świecąca Lupka**, przychodzi kolej widowni. Telefon wibruje i pokazuje pytanie,
   np. „Przez Tęczowy Mostek czy przez Szumiący Las?”. Dziecko mówi odpowiedź do telefonu albo dotyka opcji.
4. Komputer w kinie liczy głosy całej sali. Lila mówi na żywo: „Wygrywa Tęczowy Mostek!” i film idzie tą drogą.
5. Po drodze widownia rozwiązuje zagadki (kolory, zwierzęta, liczenie), uspokaja rozbrykany Wiaterek wspólnym
   oddechem i na koniec wybiera, jak świętować: tańcem albo piosenką.

Pełny scenariusz z dialogami: [scenarios/klub_ciekawskich.md](../scenarios/klub_ciekawskich.md).

## Jak to działa pod spodem

Film to **graf scen** w pliku YAML ([klub_ciekawskich.yaml](../scenarios/klub_ciekawskich.yaml)). Każda scena
z pytaniem przechodzi ten sam cykl:

```
klip z pytaniem → cicha pętla oczekiwania → odpowiedzi widowni → rozpoznanie wyboru → reakcja Lili → następna scena
```

| Krok | Czym | Gdzie w kodzie |
|---|---|---|
| Odtwarzanie klipów | VLC w pełnoekranowym oknie | `bajka/player.py` |
| Odpowiedzi z telefonów | Aplikacja mobilna w przeglądarce + lokalny serwer HTTPS na komputerze | `bajka/mobile.py`, `bajka/mobile_app/` |
| Odpowiedzi bez telefonów | Krzykomierz (wygrywa najgłośniejszy okrzyk) albo mikrofon przy ekranie | `bajka/vote.py`, `bajka/local_stt.py` |
| Mowa → tekst | Whisper w Foundry Local (lokalnie, także na NPU) | `bajka/local_stt.py`, `bajka/foundry.py` |
| Tekst → wybór | Najpierw słowa kluczowe ze scenariusza, dla niejasnych odpowiedzi model Phi w Foundry Local | `bajka/keywords.py`, `bajka/local_intent.py` |
| Bezpieczeństwo kwestii | Filtr wulgaryzmów, przemocy i zbyt długich kwestii modelu | `bajka/safety.py` |
| Głos Lili | Syntezator wbudowany w Windows (polski głos) | `bajka/local_tts.py` |
| Ilustracje na żywo (opcjonalnie) | Pomysł widza → opis (Azure OpenAI) → ilustracja (Azure AI Foundry) → ruch kamery (ffmpeg) | `bajka/imagine.py`, `bajka/illustrate.py`, `bajka/motion.py` |
| Całość | Silnik prowadzący film po grafie scen | `bajka/engine.py`, `bajka/app.py` |

Kilka zasad, które warto znać od początku:

- **Bajka nigdy nie staje.** Gdy coś zawiedzie (mikrofon, model, głos, sieć), silnik loguje błąd i idzie dalej:
  dopytuje, wybiera domyślną ścieżkę albo pokazuje klip zapasowy.
- **Moduły rozmawiają tylko przez kontrakty** z `bajka/ports.py` (`Player`, `Listener`, `Voice`,
  `IntentResolver`, `Audience`, …). Dzięki temu każdą część można wymienić — np. lokalne AI na usługi Azure
  (`--backend azure`) — i testować osobno na atrapach.
- **Dwa tryby AI:** `local` (domyślny; Foundry Local + głos Windows, bez kluczy) i `azure` (Azure Speech i Azure
  OpenAI). Ilustracje na żywo korzystają zawsze z Azure; bez internetu pokazują klipy zapasowe.
- **Pętle oczekiwania są ciche**, bo wtedy słucha mikrofon.

Więcej: [README](../README.md), [lokalne AI na Windows](LOKALNE_AI.md),
[projekt flow filmu i rysowania na żywo](superpowers/specs/2026-10-16-flow-filmu-design.md).

## Pierwsze kroki (Windows)

```powershell
git clone https://github.com/KsaweryTrebacz/FilmSpringOpen2026.git
cd FilmSpringOpen2026
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,local,mobile]"
Copy-Item .env.example .env          # tryb lokalny działa bez zmian; klucze Azure tylko do trybu azure i ilustracji
winget install --id VideoLAN.VLC -e  # VLC 64-bit
winget install --id Gyan.FFmpeg -e   # do klipów-zaślepek i ruchu kamery
```

Potem, w tej kolejności:

1. `python -m pytest` — wszystkie testy powinny przejść (działają bez sieci, mikrofonu i VLC).
2. `python -m bajka.placeholders scenarios/klub_ciekawskich.yaml` — kolorowe klipy-zaślepki zamiast animacji.
3. `python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed` — cały film bez mikrofonu i bez AI:
   odpowiedzi i głośność okrzyków wpisujesz w konsoli. Najszybszy sposób, żeby zobaczyć, jak działa graf scen.
4. Gdy to działa: tryb z lokalnym AI (`--text --windowed`), potem pełny (`python -m bajka scenarios/klub_ciekawskich.yaml`),
   a na koniec z telefonami (`--mobile`).

Każdy moduł ma też własne demo, które działa bez reszty aplikacji (lista w README, sekcja „Sprawdzanie modułów osobno”),
np. `python -m bajka.local_tts "Cześć! Jestem Lila Lupka!"` albo `python -m bajka.vote`.

## Jak pracujemy

- **Wszystko na `main`**, bez gałęzi. Przed pracą `git pull --rebase origin main`, przed wypchnięciem
  `python -m pytest`, potem `git push origin main`. Małe commity, wypychane od razu.
- **Podział na obszary** ([PODZIAL_PRACY.md](PODZIAL_PRACY.md)):
  - **A — „ucho i mózg”**: wszystko, co zamienia głos widowni na decyzję (rozpoznawanie mowy, wybór, aplikacja mobilna,
    krzykomierz, filtr treści),
  - **B — „oko i głos”**: to, co widz widzi i słyszy (odtwarzacz, głos Lili, zaślepki),
  - **C — „obraz na żywo”**: ilustracje rysowane z pomysłów widowni.
- **Zasady modułu:** własny plik i testy, ustawienia `…Settings.from_env`, demo `python -m bajka.<moduł>`, testy bez sieci
  na atrapach. Pliki wspólne (`ports.py`, `engine.py`, `app.py`, `scenario.py`, `.env.example`, README) zmieniamy małymi
  commitami i mówimy o tym reszcie zespołu.
- **Język:** identyfikatory w kodzie po angielsku; komunikaty, logi, kwestie, dokumentacja i commity po polsku.
- **Ustawienia i klucze** tylko w `.env` (nie trafia do repozytorium); wzór i opis zmiennych w `.env.example`.

## Zasady treści — obowiązują wszystkich

Film oglądają małe dzieci, a regulamin hackathonu stawia jasne wymagania
([raport zgodności](ZGODNOSC_Z_REGULAMINEM.md)):

- **Do widowni w liczbie mnogiej i bez form zależnych od płci**: „Pomożecie?”, „Brawo, świetnie wam idzie!”,
  nigdy „zrobiłeś/zrobiłaś” ani „zrobiliście”. Pilnują tego testy scenariusza.
- **Tylko prawdziwe fakty** o świecie (zwierzęta, kolory, liczby). Nowy fakt w scenariuszu = wpis w tabeli
  „Sprawdzone fakty”.
- **Bez wulgaryzmów, przemocy i straszenia** — także w tym, co mówi model na żywo (dlatego filtr w `bajka/safety.py`).
- **Tylko własne utwory**: postacie, muzyka, melodie, efekty. Każde narzędzie generatywne sprawdzamy pod kątem licencji,
  bo lider oświadcza, że zespół ma wyłączne prawa do pracy.
- **Prywatność dzieci**: nie zapisujemy nagrań; ilustracje z seansu żyją tylko w katalogu tymczasowym.

## Słowniczek

| Pojęcie | Znaczenie |
|---|---|
| **Kotwica** | Klip przygotowany przed pokazem (animacja albo ilustracja z ruchem kamery) |
| **Pętla oczekiwania** (`idle`) | Cichy, zapętlony klip po pytaniu, w trakcie którego zbieramy odpowiedzi |
| **Runda** | Czas na odpowiedzi z telefonów po jednym pytaniu (domyślnie do 8 s) |
| **Krzykomierz** | Głosowanie okrzykiem: Lila wzywa do każdej opcji, wygrywa najgłośniejsza (tryb bez telefonów) |
| **Scena `vote`** | Scena decyzji, którą bez telefonów rozstrzyga krzykomierz |
| **Scena `open`** | Pytanie otwarte; pomysł widza jest rysowany na żywo |
| **Świecąca Lupka** | Sygnał na ekranie i w telefonie: „teraz mówicie wy” |
| **Backend** | Skąd bierzemy AI: `local` (na komputerze) albo `azure` (chmura) |
| **Zaślepka** | Kolorowy klip zastępczy, dopóki nie ma prawdziwej animacji |

## Co dalej

Aktualna lista zadań — co trzeba zrobić przed pokazem i co po hackathonie — jest w [DO_ZROBIENIA.md](DO_ZROBIENIA.md).
Najwięcej pracy zostało na prawdziwym sprzęcie (testy na laptopie z Windows i na telefonach) i w produkcji filmu
(karta postaci, klipy, nagrania, muzyka). Wybierz punkt, dopisz przy nim swoje imię i daj znać zespołowi.

### Gdzie czego szukać

| Dokument | Po co |
|---|---|
| [README](../README.md) | Instalacja, uruchamianie, wszystkie tryby, rozwiązywanie problemów |
| [scenarios/klub_ciekawskich.md](../scenarios/klub_ciekawskich.md) | Scenariusz filmu: postacie, sceny, dialogi, lista klipów |
| [PODZIAL_PRACY.md](PODZIAL_PRACY.md) | Kto rozwija który moduł, zasady modułów i pracy w Git |
| [LOKALNE_AI.md](LOKALNE_AI.md) | Foundry Local, Whisper, Phi, NPU, głos Windows |
| [ZGODNOSC_Z_REGULAMINEM.md](ZGODNOSC_Z_REGULAMINEM.md) | Regulamin hackathonu, prawa autorskie, prywatność, pitch |
| [Projekt flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) | Rysowanie na żywo i dobór modeli |
| [DO_ZROBIENIA.md](DO_ZROBIENIA.md) | Co zostało do zrobienia |

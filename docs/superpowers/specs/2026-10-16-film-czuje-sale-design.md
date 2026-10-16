# Film, który czuje salę — projekt demo dla jury

Data: 16.10.2026. Zastępuje część „obraz na żywo” z [projektu flow filmu](2026-10-16-flow-filmu-design.md):
rysowanie na żywo znika z projektu, a jego miejsce zajmuje dopasowanie filmu do tętna widowni i panel dla jury.

## 1. Cel

Sprzedać jury pomysł na wysokim poziomie: **film dopasowuje się do widowni**.
- W punktach decyzji postać nie wie, co zrobić, i pyta salę. Każdy widz odpowiada do mikrofonu swojego telefonu,
  a ścieżkę wybiera większość głosów. Bez telefonów decyduje krzykomierz sali.
- Film jest drzewem scen, a wszystkie animacje są przygotowane wcześniej (nic nie rysuje się na żywo).
- Przyszłość: tętno z zegarków widzów. Jeśli widownia przyszła na spokojny film, a tętno sali skacze, film
  przechodzi na spokojniejszy montaż.

Demo działa na jednym laptopie, bez internetu. Głosowanie telefonami, krzykomierz i drzewo scen już działają.
Nowe są: symulowane tętno sali, wersje scen wybierane według tętna i panel, który pokazuje jury, co się dzieje
i dlaczego. Prawdziwe zegarki to wizja z pitchu, nie kod demo.

## 2. Decyzje

| Kwestia | Decyzja |
|---|---|
| Forma | Działające demo: bajka na ekranie kina i panel dla jury w przeglądarce |
| Rysowanie na żywo | Usunięte z projektu (zostaje w historii gita) |
| Co zmienia tętno | Wybrane sceny mają dwie wersje montażu: spokojną i żywą |
| Źródło tętna | Symulator sterowany z panelu; bez zegarków i bez danych prawdziwych osób |
| Panel | Strona serwowana lokalnie przez aplikację (bez nowych bibliotek, bez internetu) |

## 3. Usuwamy rysowanie na żywo

- **Moduły:** `bajka/imagine.py`, `bajka/illustrate.py`, `bajka/motion.py`.
- **Kontrakty w `bajka/ports.py`:** `Vision`, `Imaginer`, `Illustrator`, `Animator`.
- **Scenariusz (`bajka/scenario.py`):**
  - rodzaje scen (`kind`, `KINDS`, `LIVE_KINDS`) — zostaje jeden rodzaj sceny z klipem; `Scene.clip` znów
    jest wymagany,
  - pola `drawing`, `image_prompt`, `remember`, `default_idea`, `fallback_clips`, `next`, `narration`,
  - pola scenariusza `style`, `references`, `needs_live_images`,
  - funkcje `fill_prompt`, `template_fields`, `_parse_open`, `_parse_generated`, `_check_template`
    i ich walidacja.
  Parser pomija nieznane pola, więc scena z `kind` albo scenariusz z `style` lub `references` dostaje wprost
  `ScenarioError` z informacją, że rysowanie na żywo zostało usunięte.
- **Silnik (`bajka/engine.py`):** pula wątków, rysowanie w tle (`_prefetch`, `_drop_prefetched`), `_ask_open`,
  `_hear_idea`, `_render`, `_clip_or_fallback`, `_fallback_clip`, `_show_generated`, pamięć pomysłów,
  `FALLBACK_VISION_LINE` i parametry `imaginer`, `illustrator`, `animator`, `image_timeout_s`,
  `generated_seconds`, `rng`.
  **Zostaje** natychmiastowe zatrzymanie po Esc (`stop()`, `_Stopped`, `_play`, `_loop`) i twarde wyjście
  w `bajka/__main__.py`.
- **Aplikacja (`bajka/app.py`):** `LiveImages`, `prepare_session_dir`, `build_live_images`. Komunikat o brakujących
  plikach wraca do „Brak plików wideo”.
- **`bajka/safety.py`:** `SafeImaginer` (kod osoby A — do przekazania zespołowi).
- **`bajka/placeholders.py`:** obsługa `drawing` i klipów zapasowych scen generowanych.
- **Testy:** testy usuwanych modułów i scen `open`/`generated` (`test_imagine`, `test_illustrate`, `test_motion`,
  `test_engine_open`, `test_engine_generated`, `test_scenario_live`, `test_scenario_generated`, `test_app_live`,
  `live_fakes`). Testy zatrzymania po Esc przenosimy do `tests/test_engine.py` na zwykłe sceny.
- **Scenariusze:** `rysowanie_na_zywo.yaml`, `pomiar_obrazow.yaml`, `karta_postaci.yaml`.
- **Konfiguracja:** sekcje obrazu i ruchu kamery w `.env.example`; wpisy `ilustracje/`, `pomiar/`
  i `scenarios/ilustracje/kandydaci/` w `.gitignore`.
- **Dokumenty:**
  - README, `docs/ONBOARDING.md`, `docs/PODZIAL_PRACY.md`, `docs/ZGODNOSC_Z_REGULAMINEM.md`,
    `docs/DO_ZROBIENIA.md` i `docs/LOKALNE_AI.md` przestają mówić o rysowaniu na żywo i o chmurze w scenach na żywo.
  - Scenariusz filmowy `scenarios/klub_ciekawskich.md`: planowana scena SC. 7b (`ozdoby`, obraz na żywo) wycofana.
  - Zrobione razem z tym specem: spec darmowego rysowania (Cloudflare) jest usunięty, a projekt flow filmu
    i plan „obraz na żywo” mają na górze notkę, że rysowanie na żywo usunięto.

## 4. Tętno sali (`bajka/pulse.py`)

- **Kontrakt** w `bajka/ports.py`:
  - `Pulse(bpm: float, viewers: int)` — średnie tętno sali i liczba widzów,
  - `AudiencePulse` z metodą `read() -> Pulse`.
- **`SimulatedPulse`** — symulator, który spełnia ten kontrakt:
  - tętno płynnie dochodzi do wartości docelowej (stała czasowa około 5 s) i lekko drga (±1,5 uderzenia),
  - `set_target(bpm)` — wartość z suwaka panelu (zakres 60–160),
  - `preset(nazwa)` — gotowe stany: `spokojna` (90), `ekscytuje-sie` (115), `nudzi-sie` (85),
  - `play_script()` — wbudowany przebieg demo: spokojnie, potem ekscytacja, potem uspokojenie,
  - zegar i generator losowy wstrzykiwane, więc testy są deterministyczne.
- **Ustawienia `PulseSettings.from_env`:**
  - `BAJKA_PULSE_VIEWERS` (domyślnie 30) — liczba symulowanych widzów,
  - `BAJKA_PULSE_START_BPM` (domyślnie 90),
  - `BAJKA_PULSE_EXCITED` (domyślnie 1,15) i `BAJKA_PULSE_BORED` (domyślnie 0,97) — progi względem punktu
    odniesienia.
- **Stan sali** (funkcja czysta `hall_state(bpm, baseline, settings)`):

  | Stan | Warunek |
  |---|---|
  | `pobudzona` | tętno ≥ punkt odniesienia × `BAJKA_PULSE_EXCITED` |
  | `znudzona` | tętno ≤ punkt odniesienia × `BAJKA_PULSE_BORED` |
  | `w normie` | pomiędzy |

- **Punkt odniesienia:** silnik odczytuje tętno zaraz po klipie pierwszej sceny (sala dopiero usiadła)
  i trzyma tę wartość do końca seansu. Gdy ten odczyt się nie uda, próbuje ponownie po kolejnych scenach:
  punktem odniesienia jest pierwszy udany odczyt (decyzja zespołu). Wcześniej film się nie dopasowuje.

## 5. Wersje scen

- **Scenariusz:**
  - pole filmu `mood: spokojny | zywy` — czego widownia oczekuje od filmu (opcjonalne; bez niego film się
    nie dopasowuje),
  - pole sceny `variants:` z kluczami `spokojna` i/lub `zywa` i ścieżkami klipów (względnymi jak `clip`).
    Inne klucze to `ScenarioError`, tak samo `variants` w scenariuszu bez `mood`. Klipy wersji wchodzą do
    `missing_media` i do klipów zastępczych `bajka.placeholders`; na Windows zaślepki mają na planszy nazwę pliku
    (czcionka Arial), żeby na próbie było widać, która wersja gra.
- **Reguła wyboru wersji** (funkcja czysta `pick_variant(mood, state)`):

  | Film (`mood`) | Stan sali | Wersja |
  |---|---|---|
  | `spokojny` | `pobudzona` | `spokojna` — wolniejszy montaż |
  | `zywy` | `znudzona` | `zywa` |
  | dowolny | inny | zwykły `clip` |

  Gdy scena nie ma wybranej wersji, gra zwykły `clip`.
- **Silnik:** przed odtworzeniem sceny z `variants` czyta tętno, ustala stan sali, wybiera klip i wysyła
  zdarzenie z uzasadnieniem do panelu. Bez źródła tętna wszystko działa jak dziś.
- **„Bzyczka szuka domu”:** `mood: spokojny` i spokojne wersje scen `las`, `wiaterek` i `swieto`.
  Do prób wystarczą klipy zastępcze; prawdziwe wersje montażu przygotowuje zespół.

## 6. Panel dla jury (`bajka/panel.py`, `bajka/panel_app/index.html`)

- **Kontrakt `ShowObserver`** w `bajka/ports.py`: `event(kind: str, data: Mapping[str, Any]) -> None`.
  Silnik wysyła zdarzenia:

  | Zdarzenie | Kiedy | Dane |
  |---|---|---|
  | `scena` | start sceny | id sceny, odtwarzany klip, wersja |
  | `odniesienie` | po klipie pierwszej sceny | tętno punktu odniesienia |
  | `wersja` | przed każdą sceną z `variants`, także gdy gra zwykły klip | scena, tętno, punkt odniesienia, stan sali, wybrana wersja albo `zwykla` |
  | `glosy` | koniec rundy na telefonach albo krzykomierzu | scena, źródło (`telefony` / `krzykomierz`), wyniki opcji |
  | `decyzja` | wybór ścieżki | scena, wybrana opcja, sposób (`wiekszosc` / `okrzyk` / `odpowiedz` / `domyslna`) |

  Wywołania obserwatora są w `try/except`: błąd panelu nigdy nie zatrzymuje filmu. W kodzie głosowania osoby A
  (`_ask_audience`, `_vote`, `_ask`) dochodzą tylko wywołania `event`.
- **Serwer** `PanelServer` — `ThreadingHTTPServer` ze standardowej biblioteki, jak serwer telefonów:
  - `BAJKA_PANEL_HOST` (domyślnie `127.0.0.1`; `0.0.0.0` udostępnia panel tabletowi jury w tej samej sieci),
  - `BAJKA_PANEL_PORT` (domyślnie 8090), zwykłe HTTP (panel nie używa mikrofonu),
  - `GET /` — strona panelu,
  - `GET /graph` — drzewo scen: sceny, krawędzie z etykietami opcji, wersje scen, `mood`, scena startowa,
  - `GET /state` — bieżąca scena, przebyta ścieżka z podpisami decyzji, ostatnie głosy, historia tętna
    z ostatnich 120 s, punkt odniesienia, progi, stan sali, dziennik ostatnich 20 decyzji,
  - `POST /pulse` — sterowanie symulatorem: `{"target": bpm}`, `{"preset": nazwa}` albo `{"script": "demo"}`.
    Serwer najpierw wczytuje treść zapytania, a dopiero potem odpowiada (inaczej Windows zrywa połączenie).
  - Adres w konsoli to `http://127.0.0.1:PORT/`, nie `localhost` (na Windows `localhost` najpierw próbuje IPv6).
  - Panel sam co sekundę czyta tętno, więc wykres rusza się także w trakcie klipów.
- **Strona** (po polsku, ciemna, bez zewnętrznych bibliotek i bez internetu; odświeża `/state` co 0,5 s):
  - **drzewo scen** (SVG, warstwy według odległości od startu): sceny odwiedzone, bieżąca i przyszłe,
    a przy krawędziach decyzje, np. „telefony 18:7” albo „tętno ↑ → wersja spokojna”,
  - **tętno sali**: wykres z linią punktu odniesienia i pasmem normy,
  - **głosy**: słupki ostatniej rundy ze źródłem,
  - **dziennik decyzji**: jednym zdaniem, co film zrobił i dlaczego,
  - **symulator**: suwak tętna, przyciski stanów i „Przebieg demo”, z napisem, że dane są symulowane.

## 7. Uruchomienie

- Flaga `--panel` (albo `BAJKA_PANEL=1`) włącza symulator tętna i panel; konsola wypisuje adres panelu.
- Bez `--panel` film działa jak dziś: bez tętna i bez dopasowania.
- Działa razem z `--text`, `--windowed`, `--mobile` i krzykomierzem.

## 8. Dokumenty i pitch

- **README:** sekcja „Film, który czuje salę” w miejscu pomysłu o tętnie, z opisem demo i wizji.
- **`docs/ONBOARDING.md`, `docs/PODZIAL_PRACY.md`:** obszar C to teraz tętno i panel.
- **`docs/ZGODNOSC_Z_REGULAMINEM.md`:** demo używa wyłącznie symulowanego tętna. Prawdziwa wersja to dane
  o zdrowiu (RODO art. 9): wyraźna zgoda opiekunów, udział dobrowolny, tylko średnia całej sali, przetwarzanie
  w trakcie seansu i żadnego zapisywania.
- **`docs/DO_ZROBIENIA.md`:** spokojne wersje trzech scen, próba z panelem na laptopie pokazowym.
- **Nowy `docs/DEMO_DLA_JURY.md`:** pokaz w około 3 minutach:
  1. jury skanuje kod QR i dołącza telefonami,
  2. pierwsza decyzja głosami, panel pokazuje drzewo i wyniki,
  3. ktoś z jury klika „sala się ekscytuje”; scena `las` albo `wiaterek` idzie w wersji spokojnej,
     a dziennik mówi dlaczego,
  4. wizja: zegarki widzów, zgody opiekunów, statystyki emocji dla twórców filmu.

## 9. Testy

- **Symulator:** dochodzenie do wartości docelowej i stany gotowe na fałszywym zegarze ze stałym seedem.
- **Reguły:** `hall_state` i `pick_variant` jako tabele przypadków.
- **Scenariusz:** `mood`, `variants`, błędne klucze wersji, błąd przy `kind`, `style` i `references`.
- **Silnik:** wybór wersji według tętna, zwykły klip bez źródła tętna, zdarzenia dla panelu w kolejności,
  błąd obserwatora nie zatrzymuje filmu, Esc nadal działa.
- **Panel:** `/graph`, `/state` i `POST /pulse` na serwerze z losowym portem; błędne zapytania dostają 400.
- **Ręcznie:** pełny przebieg `python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed --panel`
  z panelem w przeglądarce.

## 10. Ryzyka

| Ryzyko | Co robimy |
|---|---|
| Brak prawdziwych spokojnych wersji scen na pokaz | Klipy zastępcze z napisem wersji; dziennik w panelu i tak tłumaczy decyzję |
| Jury nie zrozumie, co się dzieje | Panel mówi zdaniami, a `docs/DEMO_DLA_JURY.md` prowadzi pokaz krok po kroku |
| Zarzut o dane o zdrowiu dzieci | W demo wyłącznie symulacja; zasady RODO opisane w raporcie zgodności i w pitchu |
| Panel spowalnia film | Panel czyta tylko stan w pamięci, a strona odpytuje go dwa razy na sekundę |

# Do zrobienia

Stan na 17.10.2026 (368 testów przechodzi). Nowa osoba w zespole? Zacznij od [ONBOARDING.md](ONBOARDING.md).
Prezentacja przed jury: **18.10.2026, 19:00**. Odhaczajcie punkty w tym pliku (`- [x]`) i dopisujcie nowe.
Szczegóły formalne: [ZGODNOSC_Z_REGULAMINEM.md](ZGODNOSC_Z_REGULAMINEM.md). Dlaczego streaming: [STREAMING.md](STREAMING.md).

## Zrobione

- [x] Rysowanie na żywo usunięte z projektu (16.10): wszystkie animacje są przygotowane wcześniej.
- [x] Panel podglądu, symulowane tętno i wersje scen (16.10).
- [x] **Zmiana formy na odcinek do serwisów streamingowych (17.10):**
  - okno wyboru z obrazkami i odliczaniem; wybór pilotem, dotykiem, myszą, cyframi albo głosem (`bajka/web_player.py`
    + `bajka/player_app/`), sprawdzone w Chromium: przyciski, dopytanie po ciszy, wybór domyślny, „obejrzyj jeszcze raz”
    i odpowiedź z mikrofonu (udawany mikrofon w przeglądarce, udawany Whisper),
  - nagrane klipy reakcji (`reaction`) zamiast kwestii z syntezatora, napisy dla kwestii na żywo,
  - krzykomierz usunięty; telefony to teraz opcjonalny drugi ekran,
  - tętno jednego widza, nastrój zrównoważony z wersjami spokojną i żywą,
  - wersja liniowa (`python -m bajka.linear`) i manifest JSON (`python -m bajka.manifest`),
  - scenariusz przepisany na odcinek: zwroty do jednego widza bez form zależnych od płci, obrazki opcji,
  - tryb `--text` przechodzi cały odcinek w konsoli, bez wideo.

## Testy na prawdziwym sprzęcie (przed pokazem)

- [ ] Odtwarzacz w Edge albo Chrome na laptopie pokazowym: płynne przejście klip → pętla, okno wyboru na projektorze,
  pełny ekran (F), pilot do prezentacji (strzałki i Enter).
- [ ] Mikrofon w przeglądarce z prawdziwym głosem: czy wykrywanie mowy łapie dzieci i nie łapie dźwięku z pętli
  (redukcja echa), ewentualnie `BAJKA_WEB_ANSWER_SECONDS`.
- [ ] Foundry Local na laptopie do pokazu:
  - pobranie `phi-4-mini` i `whisper-tiny`, wariant na NPU (`python -m bajka.foundry --device NPU`),
  - jak Whisper rozumie polską mowę dzieci (ewentualnie większy wariant Whispera),
  - czy serwer przyjmuje odpowiedź w formacie wymuszonym schematem JSON (w logu: „odrzucił format odpowiedzi”).
- [ ] Polski głos syntezatora w przeglądarce (lokalny głos Windows) i jego tempo; bez głosu zostają napisy.
- [ ] Panel z symulowanym tętnem: „Pobudzenie” przed Wiaterkiem (wersja spokojna), „Znużenie” przed Świętem (wersja żywa).
- [ ] Wersja liniowa z prawdziwymi klipami (`python -m bajka.linear …`): długość, napisy, dźwięk w pętlach.
- [ ] Drugi ekran na prawdziwych telefonach (Android i iPhone): certyfikat, mikrofon, Wi-Fi bez izolacji urządzeń.
- [ ] `--player vlc` na laptopie pokazowym (zapasowy tryb): VLC 64-bit, mikrofon komputera.
- [ ] Próba generalna według [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md), także wariant `--no-llm --no-mic`.

## Produkcja odcinka

- [ ] Karta postaci (Lila, Fiku, Bzyczka, Fiufiu, Kuferek) z oryginalnym wyglądem; Bzyczka nie może przypominać
  znanych pszczółek z animacji.
- [ ] Klipy z [listy w scenariuszu](../scenarios/klub_ciekawskich.md#lista-klipów-do-produkcji). Minimum na pokaz:
  ilustracje z ruchem kamery dla wszystkich scen i jedna scena w pełnej animacji (SC. 4, Wiaterek).
- [ ] Pętle oczekiwania z wolną dolną jedną trzecią kadru (tam jest okno wyboru).
- [ ] Klipy reakcji SC. 1 (`01_reakcja_hopsasa.mp4`, `01_reakcja_pukanie.mp4`); w kolejnej wersji reakcje na wszystkie wybory.
- [ ] Wersje montażu: spokojne (`03b_las`, `04_wiaterek`, `07_swieto`) i żywe (`03b_las`, `07_swieto`).
- [ ] Obrazki opcji w produkcji: miniatury w stylu odcinka zamiast emoji.
- [ ] Nagrania dialogów aktorskich, własna muzyka i piosenki.
- [ ] Napisy końcowe z nazwiskami i informacją o AI.

## Regulamin i formalności

- [ ] Potwierdzenie z organizatorem, że forma streamingowa mieści się w zadaniu (hasło „Kino szuka nowej formy”).
- [ ] Zgłoszenie wysłane przez formularz; nikt z zespołu nie podlega wykluczeniu z §3 ust. 7.
- [ ] Zespół przerabia scenariusz i zapisuje, kto co zrobił (wymóg własnych praw autorskich, §3 ust. 9).
- [ ] Sprawdzone licencje: generatory obrazu (i wideo, jeśli użyte), głosy syntezatora do publikacji, fonty w napisach.
- [ ] Data prezentacji potwierdzona z organizatorem (w §2 ust. 3 regulaminu stoi „18.10.2022”).
- [ ] Na nagraniach z pokazu i testów nie ma dzieci bez zgody rodziców.
- [ ] Decyzja o licencji repozytorium (dziś nie ma pliku `LICENSE`).

## Pokaz dla jury (18.10, 19:00)

- [ ] Prezentacja oparta na kryteriach jury — argumenty w [raporcie zgodności](ZGODNOSC_Z_REGULAMINEM.md#pitch-wobec-kryteriów-jury-4-ust-5),
  realia rynku w [STREAMING.md](STREAMING.md#realia-rynku-dlaczego-urealnić).
- [ ] Demo na żywo według [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md): pilot, głos, wersje scen na panelu, ekran końcowy,
  wersja liniowa.

## Po hackathonie

Propozycje z uzasadnieniem: [STREAMING.md](STREAMING.md#propozycje-usprawnień).

- [ ] Sygnały uwagi bez biometrii (czas reakcji, serie cisz) jako wejście dla wersji scen — przed zegarkiem.
- [ ] Prawdziwe tętno z zegarka (Health Connect, HealthKit, Bluetooth „Heart Rate”) za osobną zgodą rodzica.
- [ ] Napisy WebVTT do klipów, audiodeskrypcja opcji, profil dziecka z ustawieniami tylko na urządzeniu.
- [ ] Pakowanie HLS/DASH i wstępne wczytywanie tylko klipów możliwych po bieżącym oknie wyboru.
- [ ] Aplikacja na telewizor (Tizen, webOS, Android TV) z tym samym `player_app`; Whisper w przeglądarce przez WebNN.
- [ ] Natywna aplikacja z Phi Silica i dostrajaniem LoRA ([LOKALNE_AI.md](LOKALNE_AI.md)).
- [ ] Testy uruchamiane automatycznie na GitHubie (GitHub Actions z `pytest`).
- [ ] Limity w serwerach (czas połączeń HTTP, liczba telefonów) przed publicznym udostępnieniem.
- [ ] Sprawdzenie patentów na odtwarzanie rozgałęzionych treści przed komercjalizacją.
- [ ] Test z rodzinami (plan w [raporcie zgodności](ZGODNOSC_Z_REGULAMINEM.md#test-z-prawdziwą-publicznością-5-ust-3)).

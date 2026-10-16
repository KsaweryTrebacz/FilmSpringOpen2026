# Do zrobienia

Stan na 16.10.2026 (308 testów przechodzi). Nowa osoba w zespole? Zacznij od [ONBOARDING.md](ONBOARDING.md). Prezentacja przed jury: **18.10.2026, 19:00**.
Odhaczajcie punkty w tym pliku (`- [x]`) i dopisujcie nowe. Szczegóły formalne: [ZGODNOSC_Z_REGULAMINEM.md](ZGODNOSC_Z_REGULAMINEM.md).

## Kod i podpięcie (przed pokazem)

- [x] Rysowanie na żywo usunięte z projektu (16.10): wszystkie animacje filmu są przygotowane wcześniej.
  W zamian [film, który czuje salę](superpowers/specs/2026-10-16-film-czuje-sale-design.md): tętno widowni,
  wersje scen i panel dla jury.
- [x] Film, który czuje salę: symulowane tętno sali, panel dla jury (`--panel`) i [przebieg pokazu](DEMO_DLA_JURY.md).
  Pola `variants` (spokojne wersje) scen `las`, `wiaterek` i `swieto` są w scenariuszu, a same klipy spokojnych
  wersji jeszcze trzeba przygotować (punkt „Spokojne wersje montażu” niżej).

## Testy na prawdziwym sprzęcie (nic z tego nie było jeszcze uruchomione)

- [ ] VLC 64-bit i płynne przejście klip → pętla: `python -m bajka.player KLIP PĘTLA`.
- [ ] Foundry Local na laptopie do pokazu:
  - pobranie `phi-4-mini` i `whisper-tiny`, wariant na NPU (`python -m bajka.foundry --device NPU`),
  - jak Whisper rozumie polską mowę dzieci (ewentualnie większy wariant Whispera),
  - czy serwer przyjmuje odpowiedź w formacie wymuszonym schematem JSON (w logu: „odrzucił format odpowiedzi”).
- [ ] Polski głos Windows (`python -m bajka.local_tts --list`), dobór wysokości i tempa głosu Lili.
- [ ] Aplikacja mobilna na prawdziwych telefonach (Android i iPhone):
  - akceptacja ostrzeżenia o certyfikacie i dostęp do mikrofonu,
  - Wi-Fi bez izolacji urządzeń, port 8443 otwarty w zaporze Windows,
  - kilka telefonów naraz i czas rozpoznania odpowiedzi.
- [ ] Kalibracja krzykomierza na sali: `python -m bajka.vote`.
- [ ] Próba z panelem na laptopie pokazowym: `--mobile --panel`, panel na ekranie laptopa albo tablecie jury
  (`BAJKA_PANEL_HOST=0.0.0.0`), „Przebieg demo” i ręczne „Sala się ekscytuje” przed sceną `wiaterek`.
- [ ] Próba generalna całego filmu obiema ścieżkami: z telefonami (`--mobile`) i bez.

## Produkcja filmu

- [ ] Karta postaci (Lila, Fiku, Bzyczka, Fiufiu, Kuferek) z oryginalnym wyglądem; Bzyczka nie może przypominać
  znanych pszczółek z animacji.
- [ ] 18 klipów z [listy w scenariuszu](../scenarios/klub_ciekawskich.md#lista-klipów-do-produkcji). Minimum na pokaz:
  ilustracje z ruchem kamery dla wszystkich scen i jedna scena w pełnej animacji (SC. 4, Wiaterek).
- [ ] Spokojne wersje montażu trzech scen (dłuższe ujęcia, wolniejsze tempo): `03b_las_spokojna.mp4`,
  `04_wiaterek_spokojna.mp4`, `07_swieto_spokojna.mp4` (pola `variants` w scenariuszu).
- [ ] Nagrania dialogów (głos Lili zbliżony do syntezatora), własna muzyka i piosenki.
- [ ] Plansza z kodem QR (`…/qr`), sygnał „Świecąca Lupka” w pętlach oczekiwania.
- [ ] Napisy końcowe z nazwiskami i informacją o AI.

## Regulamin i formalności

- [ ] Zgłoszenie wysłane przez formularz; nikt z zespołu nie podlega wykluczeniu z §3 ust. 7.
- [ ] Zespół przerabia scenariusz i zapisuje, kto co zrobił (wymóg własnych praw autorskich, §3 ust. 9).
- [ ] Sprawdzone licencje: generatory obrazu (i wideo, jeśli użyte), głosy syntezatora do publikacji, fonty w napisach.
- [ ] Data prezentacji potwierdzona z organizatorem (w §2 ust. 3 regulaminu stoi „18.10.2022”).
- [ ] Informacja dla opiekunów o mikrofonie i prywatności; na nagraniach z pokazu bez dzieci bez zgody opiekunów.
- [ ] Decyzja o licencji repozytorium (dziś nie ma pliku `LICENSE`).

## Pokaz dla jury (18.10, 19:00)

- [ ] Prezentacja oparta na kryteriach jury (innowacyjność, adekwatność, oryginalność, kreatywność) —
  argumenty w [raporcie zgodności](ZGODNOSC_Z_REGULAMINEM.md#pitch-wobec-kryteriów-jury-4-ust-5).
- [ ] Demo na żywo z jury jako widownią, najlepiej na telefonach jurorów.
- [ ] Pokaz według [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md): drzewo scen, głosy i tętno sali na panelu.

## Po hackathonie

- [ ] Prawdziwe tętno z zegarków widzów zamiast symulatora (Health Connect, HealthKit albo Bluetooth „Heart Rate”
  w aplikacji mobilnej), za zgodą opiekunów; wizja w [README](../README.md#film-który-czuje-salę-tętno-i-panel-dla-jury).
- [ ] Natywna aplikacja z Phi Silica i dostrajaniem LoRA ([LOKALNE_AI.md](LOKALNE_AI.md)).
- [ ] Testy uruchamiane automatycznie na GitHubie (GitHub Actions z `pytest`).
- [ ] Limity w serwerze aplikacji mobilnej (limit czasu połączeń HTTP, limit liczby telefonów). W sieci lokalnej to
  niskie ryzyko, ale przed publicznym pokazem warto je dodać.
- [ ] Seans próbny z prawdziwą publicznością (plan w [raporcie zgodności](ZGODNOSC_Z_REGULAMINEM.md#test-z-prawdziwą-publicznością-5-ust-3)).

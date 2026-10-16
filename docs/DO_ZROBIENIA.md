# Do zrobienia

Stan na 16.10.2026, po przeglądzie repozytorium (284 testy przechodzą). Prezentacja przed jury: **18.10.2026, 19:00**.
Odhaczajcie punkty w tym pliku (`- [x]`) i dopisujcie nowe. Szczegóły formalne: [ZGODNOSC_Z_REGULAMINEM.md](ZGODNOSC_Z_REGULAMINEM.md).

## Kod i podpięcie (przed pokazem)

- [ ] **Zadanie 6 [planu „obraz na żywo”](superpowers/plans/2026-10-16-obraz-na-zywo.md)** (Ksawery). Dziś
  `python -m bajka scenarios/rysowanie_na_zywo.yaml` nie rusza: zaślepki nie tworzą pętli „rysuje” ani klipów
  zapasowych, a aplikacja nie podaje silnikowi modułów rysowania. Do zrobienia:
  - podpięcie modułów rysowania w `bajka/app.py`. **Uwaga:** kroki 4–5 planu podmieniają fragmenty `app.py`,
    które zmieniły się po dodaniu aplikacji mobilnej (`build_mobile`, `audience=audience` w `StoryEngine`) — trzeba
    je scalić ręcznie,
  - zaślepki dla `drawing` i `fallback_clips` w `bajka/placeholders.py`,
  - wpisy w `.env.example` i README.
- [ ] **Decyzja: czy scena ozdabiania ula (`kind: open`) wchodzi do filmu.** Sceny otwarte słuchają dziś tylko
  mikrofonu przy ekranie, nie telefonów; w kinie trzeba by dodać na telefonach wybór spośród trzech pomysłów
  (propozycja w [scenariuszu](../scenarios/klub_ciekawskich.md), SC. 7b).
- [ ] Dopisać `scenarios/ilustracje/kandydaci/` do `.gitignore`, żeby wygenerowane obrazy z karty postaci nie trafiły
  przypadkiem do repozytorium.

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
- [ ] Azure AI Foundry: dostęp, klucze w `.env`, pomiar czasu ilustracji i wybór modelu obrazu (gpt-image-1.5 albo FLUX.2).
- [ ] Próba generalna całego filmu obiema ścieżkami: z telefonami (`--mobile`) i bez.

## Produkcja filmu

- [ ] Karta postaci (Lila, Fiku, Bzyczka, Fiufiu, Kuferek) z oryginalnym wyglądem; Bzyczka nie może przypominać
  znanych pszczółek z animacji.
- [ ] 18 klipów z [listy w scenariuszu](../scenarios/klub_ciekawskich.md#lista-klipów-do-produkcji). Minimum na pokaz:
  ilustracje z ruchem kamery dla wszystkich scen i jedna scena w pełnej animacji (SC. 4, Wiaterek).
- [ ] Nagrania dialogów (głos Lili zbliżony do syntezatora), własna muzyka i piosenki.
- [ ] Plansza z kodem QR (`…/qr`), sygnał „Świecąca Lupka” w pętlach oczekiwania.
- [ ] Napisy końcowe z nazwiskami i informacją o AI.

## Regulamin i formalności

- [ ] Zgłoszenie wysłane przez formularz; nikt z zespołu nie podlega wykluczeniu z §3 ust. 7.
- [ ] Zespół przerabia scenariusz i zapisuje, kto co zrobił (wymóg własnych praw autorskich, §3 ust. 9).
- [ ] Sprawdzone licencje: generatory obrazu (i wideo, jeśli użyte), głosy syntezatora do publikacji, fonty w napisach.
- [ ] Data prezentacji potwierdzona z organizatorem (w §2 ust. 3 regulaminu stoi „18.10.2022”).
- [ ] Informacja dla opiekunów o mikrofonie i prywatności; na nagraniach z pokazu bez dzieci bez zgody opiekunów.
- [ ] Ilustracje z seansu usuwane po pokazie (katalog tymczasowy — część zadania 6).
- [ ] Decyzja o licencji repozytorium (dziś nie ma pliku `LICENSE`).

## Pokaz dla jury (18.10, 19:00)

- [ ] Prezentacja oparta na kryteriach jury (innowacyjność, adekwatność, oryginalność, kreatywność) —
  argumenty w [raporcie zgodności](ZGODNOSC_Z_REGULAMINEM.md#pitch-wobec-kryteriów-jury-4-ust-5).
- [ ] Demo na żywo z jury jako widownią, najlepiej na telefonach jurorów.

## Po hackathonie

- [ ] Sceny generowane w tle z pamięcią opowieści (zadanie 7 planu „obraz na żywo”).
- [ ] Tętno widzów z zegarka (pomysł opisany w [README](../README.md#pomysły-na-przyszłość)).
- [ ] Natywna aplikacja z Phi Silica i dostrajaniem LoRA ([LOKALNE_AI.md](LOKALNE_AI.md)).
- [ ] Testy uruchamiane automatycznie na GitHubie (GitHub Actions z `pytest`).
- [ ] Limity w serwerze aplikacji mobilnej (limit czasu połączeń HTTP, limit liczby telefonów). W sieci lokalnej to
  niskie ryzyko, ale przed publicznym pokazem warto je dodać.
- [ ] Seans próbny z prawdziwą publicznością (plan w [raporcie zgodności](ZGODNOSC_Z_REGULAMINEM.md#test-z-prawdziwą-publicznością-5-ust-3)).

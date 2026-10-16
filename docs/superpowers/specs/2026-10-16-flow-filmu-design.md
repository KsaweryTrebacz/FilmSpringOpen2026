# Flow filmu i dobór modeli — projekt

**Projekt:** Interaktywna Bajka Głosowa Zero-UI (hackathon Film Spring Open 2026)
**Data:** 2026-10-16 · **Status:** zaakceptowany
**Obszar pracy:** „obraz na żywo” — trzeci obok „ucha i mózgu” (A) i „oka i głosu” (B) z [podziału pracy](../../PODZIAL_PRACY.md)

## 1. Kontekst

**Hackathon** „Kino szuka nowej formy. Znajdź ją.” trwa od 16.10.2026, 10:00 do 18.10.2026, 19:00
(Hotel Forest, Kraków i online). Prezentacja przed jury odbywa się 18.10 o 19:00.

**Ocena (regulamin, §4):**
- Jury ocenia innowacyjność, adekwatność do zadania, oryginalność i kreatywność.
- Brief: wygrywa nie najbardziej zaawansowany kod, tylko pomysł wart dalszego testowania z publicznością.
- Organizatorzy zakładają, że w 3 dni powstają raczej scenariusze z przekonującym prototypem niż gotowe produkty.

**Narzędzia od partnerów (brief):** Microsoft i Lenovo udostępniają:
- AI lokalnie na Copilot+ PC (Windows AI Foundry, Foundry Local),
- AI w chmurze Azure AI Foundry,
- konkretnie: modele językowe i wizyjne, rozpoznawanie mowy, generowanie obrazów.

Generowania wideo w briefie nie ma.

**Stan modeli (sprawdzony 16.10.2026):**
- **Wideo:** API Sora zostało wyłączone 24.09.2026. Innego modelu wideo w katalogu Azure AI Foundry nie znaleźliśmy.
- **Obraz w Azure AI Foundry:**
  - gpt-image-1.5 i gpt-image-2 mają wbudowany filtr treści.
  - FLUX.2 pro / flex przyjmują do 8–10 obrazów referencyjnych. Filtr treści trzeba skonfigurować samodzielnie.
- **Lokalnie:** Whisper i Phi przez Foundry Local już działają w projekcie (`local_stt.py`, `local_intent.py`).

**Prawa (regulamin, §3 ust. 9):** lider oświadcza, że ma wyłączne prawa do pracy, wolne od roszczeń osób
trzecich. Każde zewnętrzne narzędzie generatywne (wideo, muzyka) wymaga więc sprawdzenia licencji darmowego planu.

## 2. Decyzje

| Kwestia | Decyzja |
|---|---|
| Co po odpowiedzi dziecka | **Hybryda**: sceny-kotwice przygotowane przed pokazem, scena po odpowiedzi generowana na żywo |
| Styl | **Ilustrowana książka 2D** — kotwice i sceny na żywo z tych samych modeli obrazu i tego samego opisu stylu |
| Pytania bohatera | **Mieszane**: zamknięte prowadzą fabułę po grafie, otwarte wpisują pomysł dziecka w ilustrację |
| Gdzie generujemy obrazy | **Chmura (Azure AI Foundry) + zapas offline**: gotowe klipy zapasowe na każdą scenę generowaną |
| Scena po odpowiedzi | **Ilustracja + ruch kamery składany lokalnie przez ffmpeg** (podejście A); warstwy 2.5D to ulepszenie na później |
| Scenariusz | Dostarcza autor scenariusza; przykład w tym dokumencie to [Klub Ciekawskich](../../../scenarios/klub_ciekawskich.md) |

## 3. Przebieg seansu na żywo

Istniejący przebieg sceny z pytaniem zamkniętym zostaje bez zmian:
klip-kotwica → cicha pętla → nasłuch → wybór (LLM albo słowa kluczowe) → reakcja Lili (TTS) → następna scena.

Dochodzą trzy rzeczy:

**3.1. Scena z pytaniem otwartym (`kind: open`)** — priorytet P1
1. Klip-kotwica: Lila zadaje pytanie otwarte, np. „Jak udekorujemy ul Bzyczki na święto?”.
2. Cicha pętla `idle` i nasłuch, jak w scenach zamkniętych.
3. Model językowy (`Imaginer`) zwraca dwie rzeczy:
   - `reply`: kwestię Lili po polsku, np. „Tęczowe wstążki? Już to sobie wyobrażam!”, w neutralnym języku
     wobec dziecka (zasady koedukacyjne scenariusza),
   - `idea`: pomysł dziecka streszczony po angielsku, przepisany na treść bezpieczną dla dzieci.
4. Przełączenie na pętlę `drawing` („Lila rysuje”, bez dźwięku) i wypowiedzenie `reply` przez TTS.
   Jednocześnie w tle startuje generowanie ilustracji.
5. Prompt obrazu = opis stylu ze scenariusza + szablon `image_prompt` sceny z podstawionym `{idea}`
   oraz zapamiętanymi wcześniej pomysłami. Do tego dochodzą obrazy referencyjne postaci.
6. Ilustracja → klip MP4 z ruchem kamery (ffmpeg, ok. 6 s) → odtworzenie. Pętla `drawing` trwa, dopóki
   klip nie jest gotowy.
7. Pomysł zostaje zapamiętany pod kluczem `remember` (pamięć opowieści, tylko w RAM na czas seansu).
8. Przejście do sceny `next`.

Gdy dziecko milczy, scena dopytuje (`reprompt`, limit `BAJKA_MAX_REPROMPTS`). Po wyczerpaniu prób
zapisuje `default_idea` i odtwarza klip zapasowy.

**3.2. Scena generowana (`kind: generated`)** — priorytet P2
- Scena bez gotowego klipu. Ilustracja powstaje z `image_prompt`, w którym są zapamiętane pomysły dziecka
  (np. udekorowany ul pojawia się w finale), a Lila mówi `narration`.
- Gdy zaczyna się pytanie zamknięte, silnik **od razu generuje w tle wszystkie sceny `generated`**, do których
  prowadzą jego wybory. Po odpowiedzi wybrana scena jest zwykle gotowa.

**3.3. Napisy jako początek (`credits`)** — priorytet P3
Zakończenie pokazuje montaż ilustracji powstałych z pomysłów dziecka z podpisem „Członek Klubu Ciekawskich”.
Odpowiada to pytaniu z briefu, czy napisy końcowe mogą być początkiem doświadczenia.

**3.4. Budżet czasu (od końca wypowiedzi dziecka)**

| Krok | Cel | Uwagi |
|---|---|---|
| Wykrycie końca wypowiedzi | ~1,2 s | `BAJKA_END_SILENCE_MS` |
| Mowa → tekst + `Imaginer` | ≤ 4 s | Lila zaczyna mówić najpóźniej po ok. 5 s |
| Kwestia Lili (TTS) | 3–5 s | zakrywa początek generowania |
| Ilustracja | ≤ 20 s | limit czasu `BAJKA_IMAGE_TIMEOUT_S=25` |
| Ruch kamery (ffmpeg) | ≤ 3 s | lokalnie |
| **Nowa scena na ekranie** | **≤ 25 s** | czekanie wypełnia pętla „Lila rysuje” |

Wartości obrazu i ruchu kamery są celami. Mierzymy je pierwszego dnia na prawdziwym Azure (sekcja 8).

## 4. Produkcja przed pokazem

1. **Biblia stylu i postaci.**
   - Opis stylu (po angielsku, np. miękka akwarela, ciepłe pastele) trafia do pola `style` w scenariuszu.
   - Karta postaci to 2–4 ujęcia każdej postaci (Lila, Fiku, Bzyczka) wygenerowane raz i wybrane przez zespół.
     Trafiają do pola `references` i są obrazami referencyjnymi każdej ilustracji, także tych na żywo.
2. **Kotwice** (lista w [scenariuszu](../../../scenarios/klub_ciekawskich.md#lista-klipów-do-produkcji)):
   - Klatki generujemy wsadowo: `python -m bajka.illustrate --batch ujecia.yaml`.
   - Ruch kamery robi `python -m bajka.motion`.
   - Kwestie postaci nagrywamy głosami TTS albo aktorsko. Lila ma mieć ten sam głos co na żywo.
   - Montaż w dowolnym edytorze wideo.
   - Opcjonalnie wybrane ujęcia można ożywić zewnętrznym modelem image-to-video (Kling, Runway, Veo) na
     własnym koncie, po sprawdzeniu licencji (sekcja 1).
3. **Pętla „Lila rysuje”:** jeden wspólny, cichy klip na wszystkie sceny otwarte.
4. **Klipy zapasowe:** dla każdej sceny `open` i `generated` 1–3 klipy wygenerowane tym samym procesem,
   pokrywające typowe odpowiedzi (np. ul z kwiatami, ul ze wstążkami).

## 5. Modele

| Etap | Model | Gdzie | Kiedy | Kto |
|---|---|---|---|---|
| Mowa → tekst | Whisper (Foundry Local) / Azure Speech | lokalnie / chmura | na żywo | A (gotowe) |
| Wybór w pytaniu zamkniętym | Phi-4-mini / gpt-4o-mini + słowa kluczowe | lokalnie / chmura | na żywo | A (gotowe) |
| `Imaginer`: kwestia Lili + pomysł po angielsku | gpt-4o-mini w Azure. Phi lokalnie tylko jako zapas, bo słabiej pisze po polsku i tłumaczy na angielski. | chmura | na żywo | C |
| Ilustracje | **gpt-image-1.5** (domyślnie: wbudowany filtr treści, obrazy wejściowe jako referencje) albo **FLUX.2 pro** (lepsza spójność postaci, filtr przez Azure AI Content Safety). Wybór po pomiarze z dnia 1. | Azure AI Foundry | na żywo i przed pokazem | C |
| Ruch kamery | ffmpeg (bez modelu) | lokalnie | na żywo i przed pokazem | C |
| Głos Lili | Azure TTS / głos Windows | chmura / lokalnie | na żywo i kotwice | B (gotowe) |
| Ożywienie kotwic (opcja) | Kling / Runway / Veo | własne konta | przed pokazem | zespół filmowy |

## 6. Architektura w kodzie

Nowe moduły powstają według wzorca z [podziału pracy](../../PODZIAL_PRACY.md): własny plik, testy,
`<Coś>Settings.from_env`, demo `python -m bajka.<moduł>` i brak importów modułów innych osób.

**6.1. Nowe kontrakty w `bajka/ports.py`** (plik wspólny — uzgadniamy z A i B)

```python
@dataclass(frozen=True)
class Vision:
    reply: str  # kwestia Lili po polsku, wypowiadana podczas rysowania
    idea: str   # pomysł dziecka po angielsku, bezpieczny dla dzieci; "" gdy nie da się go użyć


@runtime_checkable
class Imaginer(Protocol):
    def imagine(self, scene: Scene, transcript: str) -> Vision: ...


@runtime_checkable
class Illustrator(Protocol):
    def draw(self, prompt: str) -> Path: ...  # PNG w katalogu sesji


@runtime_checkable
class Animator(Protocol):
    def animate(self, image: Path) -> Path: ...  # MP4 z ruchem kamery
```

**6.2. Nowe moduły (obszar C)**

| Moduł | Zawartość | Ustawienia `.env` | Demo |
|---|---|---|---|
| `bajka/imagine.py` | `AzureImaginer` (structured outputs: `{"reply", "idea"}`), prompt z zasadami neutralnego języka i bezpieczeństwa | korzysta z `LlmSettings` z `intent.py` | `python -m bajka.imagine SCENARIUSZ "wypowiedź" --scene ID` |
| `bajka/illustrate.py` | `AzureIllustrator`: styl + referencje ze scenariusza, zapis PNG do katalogu sesji; tryb `--batch` do produkcji | `AZURE_IMAGE_ENDPOINT`, `AZURE_IMAGE_API_KEY`, `AZURE_IMAGE_DEPLOYMENT`, `AZURE_IMAGE_API_VERSION`, `BAJKA_IMAGE_SIZE=1536x1024`, `BAJKA_IMAGE_QUALITY=medium`, `BAJKA_IMAGE_TIMEOUT_S=25` | `python -m bajka.illustrate SCENARIUSZ "prompt"` (wypisuje czas) |
| `bajka/motion.py` | `FfmpegAnimator`: ruch `zoom_in` (domyślny, używa go silnik) albo `pan` (do produkcji kotwic) → MP4 1280×720, ok. 6 s, bez dźwięku | `BAJKA_MOTION_SECONDS=6` | `python -m bajka.motion obraz.png [--move zoom_in\|pan]` |

Dokładne parametry API obrazów (generowanie z obrazami wejściowymi, rozmiary, jakość) potwierdzamy
w dokumentacji Azure AI Foundry przy implementacji `illustrate.py`.

**6.3. Rozszerzenie scenariusza (`bajka/scenario.py`, plik wspólny)**

Pola na poziomie bajki:

```yaml
style: "soft watercolor children's book illustration, warm pastel colors, gentle light"
references: [ilustracje/ref_lila.png, ilustracje/ref_fiku.png, ilustracje/ref_bzyczka.png]
```

Scena otwarta (przykład; to, czy i gdzie ją dodać, zależy od autora scenariusza):

```yaml
  ozdoby:
    kind: open
    clip: clips/klub_ciekawskich/07b_ozdoby.mp4
    idle: clips/klub_ciekawskich/07b_ozdoby_idle.mp4
    drawing: clips/wspolne/lila_rysuje.mp4
    question: Jak udekorujemy ul Bzyczki na święto?
    reprompt: Kwiatki, wstążki, a może coś zupełnie innego? Jak ozdobimy ul?
    image_prompt: "Bzyczka's beehive on the flower meadow, decorated for a party with {idea}"
    remember: ozdoby
    default_idea: colorful flowers and ribbons
    fallback_clips: [clips/klub_ciekawskich/07b_ozdoby_zapas_1.mp4]
    next: swieto
```

Scena generowana (P2):

```yaml
  final_ul:
    kind: generated
    image_prompt: "Lila, Fiku and Bzyczka celebrating in front of the beehive decorated with {ozdoby}"
    narration: Zobacz, jak pięknie wygląda ul, który razem ozdobiliśmy!
    fallback_clips: [clips/klub_ciekawskich/final_ul_zapas.mp4]
    next: koniec_taniec
```

**Walidacja:**
- Brak `kind` oznacza dotychczasową scenę z klipem.
- `open` wymaga: `clip`, `idle`, `drawing`, `question`, `reprompt`, `image_prompt` zawierającego `{idea}`,
  `remember`, `default_idea`, co najmniej jednego `fallback_clips` oraz istniejącej sceny `next`.
- `generated` wymaga: `image_prompt`, `narration`, co najmniej jednego `fallback_clips` oraz istniejącej
  sceny `next`.
- Każdy `{klucz}` w szablonach poza `{idea}` musi być `remember` jakiejś sceny `open`. Dzięki `default_idea`
  wartość jest zawsze dostępna w czasie seansu.

**6.4. Silnik (`bajka/engine.py`, plik wspólny)**
- `StoryEngine` dostaje opcjonalnie `Imaginer`, `Illustrator` i `Animator`. Bez nich scenariusz ze scenami
  `open` lub `generated` jest odrzucany przy starcie z czytelnym komunikatem.
- Generowanie (rysowanie i ruch kamery) działa w puli wątków z limitem `BAJKA_IMAGE_TIMEOUT_S`.
  Odtwarzanie i mowa zostają w wątku silnika.
- Pamięć opowieści to słownik `remember → idea` żyjący tylko w trakcie seansu.
- P2: przy starcie sceny z pytaniem zamkniętym silnik zleca w tle sceny `generated` osiągalne z jej
  wyborów i trzyma wyniki w pamięci podręcznej.

## 7. Błędy, bezpieczeństwo, prywatność

| Sytuacja | Reakcja |
|---|---|
| Przekroczony limit czasu lub błąd generowania obrazu | losowy klip z `fallback_clips`; Lila mówi stałą kwestię „Pokażę ci, co ja sobie wyobraziłam!” |
| Filtr treści odrzuca prompt | jak wyżej; w logu powód, bez treści wypowiedzi dziecka |
| `Imaginer` zawodzi albo zwraca `idea == ""` | `default_idea` + klip zapasowy; Lila mówi tę samą stałą kwestię co przy błędzie obrazu |
| Brak internetu na sali | wszystkie sceny `open` i `generated` lecą z klipów zapasowych, reszta bajki działa lokalnie |
| Błąd ffmpeg | klip zapasowy |

**Bezpieczeństwo dzieci:**
- Wypowiedź dziecka nigdy nie trafia do modelu obrazu bezpośrednio, tylko jako `idea` przepisana przez LLM.
- gpt-image ma wbudowany filtr. Przy FLUX dokładamy Azure AI Content Safety na prompt.

**Prywatność:**
- Nie zapisujemy nagrań głosu.
- Ilustracje sesji trafiają do katalogu tymczasowego (`%TEMP%/bajka/<sesja>/`), który aplikacja czyści przy
  następnym starcie.
- Imię dziecka (P3, napisy) jest tylko na ekranie.

**Prawa:**
- Do pracy konkursowej trafiają tylko treści z narzędzi, których licencja pozwala zespołowi mieć do nich prawa (sekcja 1).
- Ilustracje z Azure AI Foundry, klipy z zewnętrznych modeli i muzykę sprawdzamy przed prezentacją.

## 8. Testy i pomiary

**Testy jednostkowe na atrapach, bez sieci:**
- parsowanie odpowiedzi `Imaginer`,
- budowanie zapytania w `illustrate.py` (atrapa klienta),
- polecenie ffmpeg w `motion.py`, plus jeden test tworzący prawdziwy 1-sekundowy klip, pomijany bez ffmpeg,
- walidacja nowych pól scenariusza i podstawianie pamięci w szablonach,
- ścieżki silnika: sukces, limit czasu → klip zapasowy, błąd `Imaginer`, cisza → `default_idea`.

**Pomiar dnia 1** (`python -m bajka.illustrate` wypisuje czas):
- 10 promptów w stylu bajki dla gpt-image-1.5 i FLUX.2 pro,
- mediana i maksimum czasu,
- ocena zespołu: czy Lila wygląda jak Lila.

**Decyzja o modelu:** wygrywa model z medianą ≤ 20 s i lepszą spójnością postaci. Przy remisie wybieramy
gpt-image-1.5 ze względu na wbudowany filtr.

## 9. Kolejność prac

1. **Dzień 1:**
   - dostęp do Azure AI Foundry od mentorów Microsoftu (wdrożenia gpt-image-1.5 i FLUX.2 pro),
   - `illustrate.py` i `motion.py` z demami,
   - biblia stylu i karta postaci,
   - pomiar i wybór modelu.
2. **Dzień 2:**
   - `imagine.py`, nowe pola scenariusza, scena `open` w silniku, pętla „Lila rysuje”, klipy zapasowe,
   - pierwsza scena otwarta w scenariuszu (decyzja autora).
3. **Dzień 3:**
   - P2 (sceny `generated` z generowaniem w tle i pamięcią opowieści), jeśli P1 działa stabilnie,
   - P3 (napisy) albo próby generalne i pitch.

## 10. Poza zakresem

- Warstwy 2.5D (postać z przezroczystym tłem nad tłem z paralaksą) — ulepszenie po hackathonie.
- Generowanie wideo na żywo — brak modelu u partnerów, a czas generowania wykracza poza budżet z sekcji 3.4.
- Rozmowa głosowa w czasie rzeczywistym (gpt-realtime) — nie potwierdziliśmy obsługi polskiego.
- Generowanie obrazów lokalnie przez Windows AI APIs — API dostępne głównie z C#; do sprawdzenia po hackathonie.
- Muzyka generowana przez AI — tylko po sprawdzeniu licencji.

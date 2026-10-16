# Darmowe rysowanie na żywo — projekt

Data: 16.10.2026. Ten dokument zmienia modele z [projektu flow filmu](2026-10-16-flow-filmu-design.md).
Przebieg seansu, silnik, sceny `open` i `generated`, ruch kamery (ffmpeg) i klipy zapasowe zostają bez zmian.

## 1. Cel i ograniczenia

- Prototyp powstaje na 2–3 dni hackathonu, więc **żadnych płatnych usług i żadnej karty płatniczej**.
- Mowa, wybór ścieżki i głos postaci już są darmowe. Tryb `local` (domyślny) korzysta z Foundry Local
  i głosu Windows. Tej części nie zmieniamy.
- Płatne było tylko rysowanie na żywo:
  - Azure OpenAI pisał kwestię postaci i opis obrazu (`AzureImaginer`),
  - gpt-image-2 w Azure AI Foundry rysował obraz (`AzureIllustrator`).
- Decyzja człowieka: **Azure znika całkiem z rysowania i wyobraźni** — z kodu, konfiguracji i dokumentacji.
  Backend `azure` osoby A dla mowy i intencji (`stt.py`, `tts.py`, `intent.py`) zostaje nietknięty.

## 2. Decyzje

| Kwestia | Decyzja |
|---|---|
| Obraz | Cloudflare Workers AI, model `@cf/black-forest-labs/flux-1-schnell`, darmowy plan (10 000 neuronów na dobę, bez karty) |
| Kwestia postaci i opis obrazu | Lokalny model z Foundry Local, ten sam alias co intencje (domyślnie `phi-4-mini`) |
| Azure w rysowaniu i wyobraźni | Usunięty |
| Obrazy referencyjne postaci | Usunięte: FLUX.1 [schnell] ich nie przyjmuje. Wygląd postaci trzyma opis w prompcie i w `style` |
| Filtr treści obrazu | Dotąd robił go gpt-image. Teraz `SafeImaginer` sprawdza też angielski opis obrazu |

## 3. Obraz: `CloudflareIllustrator` (`bajka/illustrate.py`)

- Zastępuje `AzureIllustrator` w tym samym module. Spełnia ten sam kontrakt `bajka.ports.Illustrator`.
  Narzędzie `python -m bajka.illustrate` zostaje z opcjami `--batch`, `--out` i `--retries`.
- `ImageSettings.from_env`:
  - wymagane: `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`,
  - opcjonalne: `CLOUDFLARE_IMAGE_MODEL` (domyślnie `@cf/black-forest-labs/flux-1-schnell`),
    `BAJKA_IMAGE_STEPS` (domyślnie 4, najwyżej 8), `BAJKA_IMAGE_TIMEOUT_S` (domyślnie 25).
- Wywołanie:
  - `POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}`,
  - nagłówek `Authorization: Bearer {token}`,
  - treść JSON `{"prompt": ..., "steps": 4, "seed": <losowa liczba dodatnia>}`.
- Odpowiedź: JSON, w którym `result.image` to obraz JPEG 1024×1024 zakodowany w base64. Zapis jako `<nazwa>.jpg`
  w katalogu seansu.
- Klient HTTP: `httpx`. Już jest instalowany razem z `openai`; dopisujemy go jawnie do zależności.
  Klient trafia do konstruktora, więc testy podstawiają `httpx.MockTransport` i nie potrzebują sieci.
- Prompt: `build_prompt(scene_prompt, style)` jak dziś, bez zdania o obrazach referencyjnych, plus stałe zdanie
  o bezpiecznej, łagodnej ilustracji dla małych dzieci. Całość przycinamy do 2048 znaków (limit API).
- Błędy: kod HTTP inny niż 200 albo `success: false` w odpowiedzi kończy się wyjątkiem z komunikatem Cloudflare
  (np. wyczerpany dzienny limit neuronów, zły token).
  - Na żywo bez ponowień: silnik od razu pokazuje klip zapasowy.
  - W `--batch` domyślnie 3 ponowienia przy kodzie 429 i 5xx.
- Kadr: obraz jest kwadratowy, a `FfmpegAnimator` już przycina go do 16:9. Opisy scen powinny trzymać ważne
  rzeczy w środku kadru („wide shot, subject in the middle”).
- Limit darmowego planu:
  - jeden obraz kosztuje około 58 neuronów (4 kafelki 512×512 po 4,8 + 4 kroki po 9,6),
  - to około 170 obrazów na dobę na konto,
  - licznik zeruje się o 00:00 UTC (w październiku o 2:00 w Polsce),
  - po wyczerpaniu limitu lecą klipy zapasowe, a log mówi wprost, co się stało.

  Obrazy do scen przygotowanych wcześniej i kartę postaci generujcie dzień wcześniej, żeby nie zjadały limitu
  w dniu pokazu.

## 4. Kwestia i opis obrazu: `LocalImaginer` (`bajka/imagine.py`)

- Zastępuje `AzureImaginer` w tym samym module. `IMAGINE_PROMPT`, `parse_vision` i demo
  `python -m bajka.imagine` zostają.
- `ImagineSettings.from_env`:
  - `FOUNDRY_CHAT_MODEL` (domyślnie `phi-4-mini`) i `FOUNDRY_DEVICE` — te same zmienne co intencje,
  - `BAJKA_IMAGINE_TIMEOUT_S` (domyślnie 12).
- Działa wzorem `local_intent.py`:
  - `load_model` i klient `OpenAI(base_url=openai_base_url(), api_key="lokalnie", timeout=12, max_retries=0)`,
  - do promptu systemowego dopisana instrukcja formatu JSON (małe modele lepiej się go trzymają),
  - formaty odpowiedzi od `json_schema` do `json_object`; gdy serwer odrzuci format (400), schodzimy na stałe
    do luźniejszego,
  - wyrozumiałe czytanie JSON: ```` ```json ````, tekst przed i po obiekcie.
- Wyobraźnia zawsze działa lokalnie, niezależnie od `--backend` i `--no-llm`: bez modelu nie da się zamienić
  pomysłu dziecka na opis obrazu. Gdy scenariusz ma sceny rysowane na żywo, a Foundry Local nie działa,
  aplikacja kończy się błędem konfiguracji na starcie, tak jak dziś przy braku kluczy.
- Prywatność: słowa dziecka zostają na laptopie. Do Cloudflare trafia tylko angielski opis obrazu (`idea`)
  razem ze stylem sceny.
- Czas: model lokalny jest wolniejszy od Azure. Pętla „postać rysuje” startuje zaraz po słowach dziecka
  (już tak jest). Dalej obowiązuje termin 25 s na obraz i klip zapasowy po nim.

## 5. Bezpieczeństwo (`bajka/safety.py`)

- `SafeImaginer` sprawdza:
  - polską kwestię (`is_safe_reply`, już jest),
  - **nowe:** angielski opis obrazu funkcją `is_safe_idea`. To lista angielskich słów z tych samych kategorii
    co filtr kwestii: przemoc, broń, krew, nagość, wulgaryzmy, rzeczy straszne.
- Niebezpieczna kwestia albo opis kończy się `Vision("", "")`. Silnik pokazuje wtedy klip zapasowy i mówi stałą,
  sprawdzoną kwestię.
- To zmiana w pliku osoby A, trzeba ją przekazać zespołowi.

## 6. Co usuwamy

- `AzureIllustrator`, `AzureImaginer`, ich ustawienia (`AZURE_IMAGE_*`, `BAJKA_IMAGE_SIZE`, `BAJKA_IMAGE_QUALITY`)
  i ich testy.
- Pole `references` scenariusza (klasa `Scenario`, parser, `missing_media`) i ścieżkę `images.edit`.
  Parser i tak pomija nieznane pola, więc scenariusz, który nadal ma `references`, dostaje wprost błąd
  `ScenarioError`: pole nie jest już obsługiwane, opis postaci trzeba wpisać do `style` albo `image_prompt`.
  Bez tego obrazy referencyjne cicho by zniknęły.
  Komentarz w `scenarios/karta_postaci.yaml` mówi odtąd, że wybrane ujęcia są wzorem dla zespołu,
  a opis postaci trafia do promptów.
- Zapisy o Azure przy rysowaniu i wyobraźni w README, `.env.example`, `docs/ONBOARDING.md`,
  `docs/PODZIAL_PRACY.md`, `docs/ZGODNOSC_Z_REGULAMINEM.md`, `docs/DO_ZROBIENIA.md` i w komentarzach
  `scenarios/pomiar_obrazow.yaml`.

## 7. Konfiguracja i dokumentacja

- `.env.example`: sekcja Cloudflare z opisem, skąd wziąć wartości:
  - darmowe konto na dash.cloudflare.com, bez karty,
  - Account ID z panelu konta,
  - token: My Profile → API Tokens → Create Token → szablon „Workers AI”.
- README i ONBOARDING: sceny rysowane na żywo potrzebują internetu, darmowego tokenu Cloudflare,
  Foundry Local i ffmpeg.
- `docs/ZGODNOSC_Z_REGULAMINEM.md`:
  - §6: do chmury trafia tylko angielski opis obrazu, nigdy słowa dziecka ani nagranie,
  - §3 ust. 9: FLUX.1 [schnell] ma licencję Apache 2.0; warunki Cloudflare i Black Forest Labs dotyczące
    wygenerowanych obrazów zespół sprawdza przed oświadczeniem lidera.
- `pyproject.toml`: `httpx` w zależnościach.

## 8. Testy

- Automatyczne, bez sieci:
  - `CloudflareIllustrator` na `httpx.MockTransport`: sukces z zapisem pliku, błąd 4xx z komunikatem,
    `success: false`, ponowienia w `--batch`, przycięcie promptu,
  - `LocalImaginer` na fałszywym kliencie: JSON z tekstem wokół, zejście z formatu przy 400,
    klient z `timeout=12` i `max_retries=0`,
  - `is_safe_idea` i `SafeImaginer` z niebezpiecznym opisem,
  - okablowanie w `build_live_images` i komunikaty przy braku tokenu.
- Ręcznie, z prawdziwym tokenem (zespół):
  - `python -m bajka.illustrate scenarios/rysowanie_na_zywo.yaml "opis"` — czas jednego obrazu,
  - `python -m bajka.illustrate ... --batch scenarios/pomiar_obrazow.yaml` — mediana czasu i wygląd postaci,
  - `python -m bajka.imagine scenarios/rysowanie_na_zywo.yaml "pomysł"` — czas Phi na laptopie pokazowym,
  - próba generalna całej bajki.

## 9. Ryzyka

| Ryzyko | Co robimy |
|---|---|
| Postać wygląda inaczej na każdym obrazie (brak referencji) | Na obrazach na żywo postacie są małe albo w tle; główne ujęcia postaci to przygotowane wcześniej klipy |
| Wyczerpany dzienny limit | Obrazy przygotowywane wcześniej generujemy dzień przed pokazem; w razie czego klipy zapasowe |
| Phi po polsku pisze słabiej niż GPT | Filtr kwestii, stała kwestia zapasowa, krótka kwestia (najwyżej dwa zdania) |
| Brak internetu na sali | Klipy zapasowe; mowa, wybór ścieżki i głos działają offline |
| Phi odpowiada wolno na laptopie bez NPU | Limit 12 s, potem klip zapasowy; pomiar w próbie generalnej |

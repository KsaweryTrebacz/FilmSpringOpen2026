# Interaktywna Bajka Głosowa Zero-UI

Prototyp na hackathon FilmSpring Open 2026: bajka, w której ekran słucha i odpowiada.
Bohater odwraca się do widza i zadaje pytanie, dziecko odpowiada głosem, a historia idzie
w wybraną stronę. Bez myszki i klawiatury.

Pracujemy w dwie osoby na niezależnych modułach — kto co robi i zasady: [docs/PODZIAL_PRACY.md](docs/PODZIAL_PRACY.md).

Domyślnie całe AI działa **lokalnie na Windows** (Foundry Local z Whisper i Phi na NPU/GPU/CPU, głos
z syntezatora Windows) — bez chmury i bez kluczy: [docs/LOKALNE_AI.md](docs/LOKALNE_AI.md).
Usługi Azure zostają jako alternatywa (`--backend azure`).

Film: **„Bzyczka szuka domu”** — interaktywny animowany film krótkometrażowy dla widowni kinowej
([scenariusz filmowy](scenarios/klub_ciekawskich.md), [graf scen dla aplikacji](scenarios/klub_ciekawskich.yaml)).
Zgodność z regulaminem hackathonu: [docs/ZGODNOSC_Z_REGULAMINEM.md](docs/ZGODNOSC_Z_REGULAMINEM.md).

## Jak to działa

1. VLC odtwarza klip, w którym bohater zadaje pytanie (np. „mostek czy las?”).
2. Startuje cicha pętla oczekiwania, a mikrofon słucha; koniec wypowiedzi wykrywa detektor ciszy.
3. Whisper (Foundry Local) zamienia mowę na tekst; Phi (Foundry Local) rozpoznaje intencję dziecka
   i pisze reakcję bohatera. Gdy model zawiedzie, wybór rozpoznają słowa kluczowe ze scenariusza.
4. Syntezator Windows wypowiada reakcję, potem startuje klip wybranej ścieżki.
5. Cisza albo niejasna odpowiedź: bohater dopytuje (domyślnie 2 razy), potem sam wybiera ścieżkę domyślną.

W trybie `--backend azure` kroki 2–4 wykonują Azure AI Speech i Azure OpenAI.

**W kinie** na sali siedzi wiele dzieci, więc decyzje (sceny `vote: true`) rozstrzyga **krzykomierz**: bohaterka
wzywa po kolei do każdej opcji („Kto za mostkiem? Krzyczymy… Mostek!”), a wygrywa najgłośniejszy okrzyk. Zagadki
sala rozwiązuje chórem, a odpowiedź rozpoznaje Whisper z modelem językowym. Kwestie pisane na żywo przez model
przechodzą przez filtr treści (`bajka/safety.py`).

Mikrofon jest wyłączony, gdy bohater mówi, więc nie słyszy sam siebie. Awaria STT, LLM albo TTS
nie zatrzymuje bajki: zamiast tego wybierana jest ścieżka domyślna albo kwestia ze scenariusza.

## Wymagania

- Windows 10/11 (działa też na Linuksie; na macOS VLC otworzy osobne okno)
- Python 3.11+ w wersji 64-bit
- VLC 3.x 64-bit: `winget install --id VideoLAN.VLC -e`
- ffmpeg, tylko do klipów-zaślepek: `winget install --id Gyan.FFmpeg -e`
- Tryb lokalny (domyślny): Windows 11, polski głos w Ustawienia → Czas i język → Mowa; najlepiej Copilot+ PC z NPU
- Tryb `azure`: zasób AI Speech oraz zasób Azure OpenAI z wdrożeniem modelu `gpt-4o-mini`

## Instalacja

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,local]"
Copy-Item .env.example .env   # tryb lokalny działa bez zmian; klucze tylko dla --backend azure
```

## Uruchomienie

```powershell
# klipy-zaślepki (kolorowe plansze), dopóki nie ma animacji
python -m bajka.placeholders scenarios/klub_ciekawskich.yaml

# próba bez mikrofonu i bez żadnego AI: odpowiedzi z konsoli, wybór po słowach kluczowych
python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed

# próba bez mikrofonu z lokalnym modelem językowym (Phi w Foundry Local)
python -m bajka scenarios/klub_ciekawskich.yaml --text --windowed

# pokaz: pełny ekran, mikrofon i głos bohaterki, wszystko lokalnie
python -m bajka scenarios/klub_ciekawskich.yaml

# to samo na usługach Azure
python -m bajka scenarios/klub_ciekawskich.yaml --backend azure
```

`Esc` zamyka aplikację. W trybie `--text` kliknij okno konsoli, żeby wpisać odpowiedź.

## Sprawdzanie modułów osobno

Każdy moduł ma własne demo, które działa bez reszty aplikacji:

```powershell
python -m bajka.foundry --device NPU                 # katalog modeli Foundry Local i ich warianty
python -m bajka.local_stt --repeat 3                 # mikrofon → tekst (Whisper lokalnie)
python -m bajka.local_tts "Cześć! Jestem Lila Lupka!"  # tekst → głos bohaterki (Windows)
python -m bajka.local_intent scenarios/klub_ciekawskich.yaml "tam gdzie ciemno" --scene kuferek   # wypowiedź → wybór (Phi)
python -m bajka.keywords scenarios/klub_ciekawskich.yaml "lornetkę" --scene pomocnik   # wypowiedź → wybór (słowa kluczowe)
python -m bajka.vote                                 # kalibracja krzykomierza na sali: gwar i okrzyk
python -m bajka.stt --repeat 3                       # mikrofon → tekst (Azure STT)
python -m bajka.tts "Idziemy do lasu czy do jaskini?" # tekst → głos bohatera (Azure TTS)
python -m bajka.intent scenarios/las_czy_jaskinia.yaml "tam gdzie ciemno"   # wypowiedź → wybór (Azure OpenAI)
python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4   # klip → pętla (VLC)
```

Każde demo wypisuje czas odpowiedzi, co pomaga stroić `BAJKA_INITIAL_SILENCE_MS`, `BAJKA_END_SILENCE_MS`
i prompt. Bez kluczy w `.env` demo kończy się komunikatem, których zmiennych brakuje.

## Scenariusz

Bajka to graf scen w YAML ([pełna bajka](scenarios/klub_ciekawskich.yaml),
[najprostszy przykład](scenarios/las_czy_jaskinia.yaml)). Ścieżki klipów są względne wobec pliku
scenariusza. Scena bez `choices` kończy bajkę.

| Pole | Opis |
|---|---|
| `hero` | Opis bohatera dla LLM: imię, charakter, sposób mówienia |
| `start` | Identyfikator pierwszej sceny |
| `scenes.<id>.clip` | Klip sceny (bohater zadaje pytanie albo kończy historię) |
| `scenes.<id>.idle` | Cicha pętla oczekiwania na odpowiedź (wymagana, gdy są `choices`) |
| `scenes.<id>.question` | Pytanie zadane w klipie; trafia do promptu LLM |
| `scenes.<id>.reprompt` | Kwestia bohatera, gdy dziecko milczy |
| `scenes.<id>.fallback` | Opcjonalnie: wstęp, gdy bohater sam wybiera (domyślnie „Dobrze, to ja wybiorę!”) |
| `scenes.<id>.default` | Wybór, gdy po dopytaniach nadal brak decyzji albo LLM zawiedzie |
| `choices.<id>.description` | Znaczenie wyboru dla LLM, np. „pójść do mrocznego lasu” |
| `choices.<id>.next` | Scena, która nastąpi po tym wyborze |
| `choices.<id>.reply` | Statyczna reakcja bohatera, gdy LLM nie odpowie |
| `choices.<id>.keywords` | Opcjonalnie: słowa, po których wybór rozpozna się bez LLM (identyfikator wyboru liczy się zawsze) |
| `scenes.<id>.vote` | Opcjonalnie `true`: widownia wybiera okrzykiem (krzykomierz) zamiast słowami |
| `choices.<id>.call` | W scenie `vote`: wezwanie do okrzyku mówione przez bohaterkę, np. „Kto za mostkiem? Krzyczymy… Mostek!” |
| `choices.<id>.call_clip` | W scenie `vote`: to samo wezwanie jako nagrany klip (ma pierwszeństwo przed `call`) |

## Wskazówki do klipów

- Pętla oczekiwania musi być bez dźwięku, bo w tym czasie słucha mikrofon.
- Ostatnia klatka klipu z pytaniem = pierwsza klatka pętli, wtedy przejście jest niewidoczne.
- Format: MP4, H.264 + AAC.
- Klipy nie są w repozytorium (`scenarios/clips/` jest w `.gitignore`), trzymajcie je na dysku współdzielonym.

## Architektura

| Moduł | Rola |
|---|---|
| `bajka/scenario.py` | Wczytanie i walidacja scenariusza YAML |
| `bajka/config.py` | Wspólne narzędzia ustawień: `load_env`, `require`, `get_int` |
| `bajka/ports.py` | Kontrakty: `Player`, `Listener`, `Voice`, `IntentResolver` |
| `bajka/engine.py` | `StoryEngine`: przebieg bajki, dopytywanie, ścieżki awaryjne |
| `bajka/stt.py` | Azure AI Speech: rozpoznawanie mowy z mikrofonu (`SttSettings`, `AzureListener`) |
| `bajka/tts.py` | Azure AI Speech: głos bohatera, odtwarzanie do końca (`TtsSettings`, `AzureVoice`) |
| `bajka/intent.py` | Azure OpenAI: intencja + kwestia bohatera (`LlmSettings`, `AzureIntentResolver`) |
| `bajka/foundry.py` | Foundry Local: modele lokalne na NPU/GPU/CPU, serwer zgodny z OpenAI |
| `bajka/local_stt.py` | Whisper lokalnie + wykrywanie wypowiedzi (`LocalSttSettings`, `LocalListener`) |
| `bajka/local_intent.py` | Phi lokalnie: intencja + kwestia bohatera (`LocalLlmSettings`, `LocalIntentResolver`) |
| `bajka/local_tts.py` | Głos z syntezatora Windows (`WindowsTtsSettings`, `WindowsVoice`) |
| `bajka/keywords.py` | Wybór po słowach kluczowych, offline (`KeywordIntentResolver`, `FallbackResolver`) |
| `bajka/audio.py` | Wspólne odtwarzanie WAV do końca wypowiedzi |
| `bajka/vote.py` | Krzykomierz: głosowanie okrzykiem widowni (`VoteSettings`, `MicrophoneMeter`) |
| `bajka/safety.py` | Filtr kwestii modelu językowego (`SafeReplyResolver`) |
| `bajka/player.py` | VLC osadzony w pełnoekranowym oknie tkinter |
| `bajka/console.py` | Tryb `--text` do prób bez mikrofonu |
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg) |
| `bajka/app.py` | Złożenie całości i uruchomienie |

Silnik zależy tylko od kontraktów z `ports.py`, a każdy moduł czyta własne ustawienia
(`XxxSettings.from_env`). Testy działają na atrapach, bez Azure, mikrofonu i VLC.

## Testy

```powershell
python -m pytest
```

## Problemy

- `FileNotFoundError: ... libvlc.dll`: brak VLC albo zainstalowana wersja 32-bit.
- Bohater nie słyszy dziecka: Ustawienia Windows → Prywatność → Mikrofon → zezwól aplikacjom klasycznym;
  sprawdź domyślne urządzenie nagrywania.
- `rozpoznawanie anulowane: ... 401` albo `synteza anulowana: ... 401`: zły `AZURE_SPEECH_KEY` lub `AZURE_SPEECH_REGION`.
- Dziecko musi długo czekać albo jest ucinane: dostrój `BAJKA_INITIAL_SILENCE_MS` i `BAJKA_END_SILENCE_MS`.
- Krzaki zamiast polskich znaków w konsoli: `$env:PYTHONUTF8 = "1"`.
- `Brak pakietu foundry-local-sdk` albo `Brak pakietów WinRT`: `pip install -e ".[local]"`.
- `Brak głosu Windows dla pl-PL`: dodaj polski głos w Ustawienia → Czas i język → Mowa.
- `Foundry Local nie zna modelu …`: sprawdź aliasy przez `python -m bajka.foundry` i popraw `FOUNDRY_CHAT_MODEL` / `FOUNDRY_STT_MODEL`.
- Dziecko jest ucinane albo hałas uruchamia nasłuch (tryb lokalny): dostrój `BAJKA_VAD_THRESHOLD` i `BAJKA_END_SILENCE_MS`.
- Krzykomierz ciągle mówi „za cicho” albo każdą ciszę uznaje za okrzyk: `python -m bajka.vote` na sali i ustaw
  `BAJKA_VOTE_MIN_LEVEL` / `BAJKA_VOTE_MIN_RATIO` według podpowiedzi.

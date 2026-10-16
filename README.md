# Interaktywna Bajka Głosowa Zero-UI

Prototyp na hackathon FilmSpring Open 2026: bajka, w której ekran słucha i odpowiada.
Bohater odwraca się do widza i zadaje pytanie, dziecko odpowiada głosem, a historia idzie
w wybraną stronę. Bez myszki i klawiatury.

## Jak to działa

1. VLC odtwarza klip, w którym bohater zadaje pytanie (np. „las czy jaskinia?”).
2. Startuje cicha pętla oczekiwania, a Azure AI Speech słucha mikrofonu i sam wykrywa koniec wypowiedzi.
3. Azure OpenAI (GPT-4o-mini) rozpoznaje intencję dziecka i pisze reakcję bohatera.
4. Azure TTS wypowiada reakcję, potem startuje klip wybranej ścieżki.
5. Cisza albo niejasna odpowiedź: bohater dopytuje (domyślnie 2 razy), potem sam wybiera ścieżkę domyślną.

Mikrofon jest wyłączony, gdy bohater mówi, więc nie słyszy sam siebie. Awaria STT, LLM albo TTS
nie zatrzymuje bajki: zamiast tego wybierana jest ścieżka domyślna albo kwestia ze scenariusza.

## Wymagania

- Windows 10/11 (działa też na Linuksie; na macOS VLC otworzy osobne okno)
- Python 3.11+ w wersji 64-bit
- VLC 3.x 64-bit: `winget install --id VideoLAN.VLC -e`
- ffmpeg, tylko do klipów-zaślepek: `winget install --id Gyan.FFmpeg -e`
- Azure: zasób AI Speech oraz zasób Azure OpenAI z wdrożeniem modelu `gpt-4o-mini`

## Instalacja

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env   # uzupełnij klucze Azure
```

## Uruchomienie

```powershell
# klipy-zaślepki (kolorowe plansze), dopóki nie ma animacji
python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml

# próba bez mikrofonu: odpowiedzi wpisujesz w konsoli, kwestie bohatera są wypisywane
python -m bajka scenarios/las_czy_jaskinia.yaml --text --windowed

# pokaz: pełny ekran, mikrofon i głos bohatera
python -m bajka scenarios/las_czy_jaskinia.yaml
```

`Esc` zamyka aplikację. W trybie `--text` kliknij okno konsoli, żeby wpisać odpowiedź.
Podgląd przejścia klip → pętla bez reszty systemu: `python -m bajka.player KLIP PĘTLA`.

## Scenariusz

Bajka to graf scen w YAML ([przykład](scenarios/las_czy_jaskinia.yaml)). Ścieżki klipów są
względne wobec pliku scenariusza. Scena bez `choices` kończy bajkę.

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

## Wskazówki do klipów

- Pętla oczekiwania musi być bez dźwięku, bo w tym czasie słucha mikrofon.
- Ostatnia klatka klipu z pytaniem = pierwsza klatka pętli, wtedy przejście jest niewidoczne.
- Format: MP4, H.264 + AAC.
- Klipy nie są w repozytorium (`scenarios/clips/` jest w `.gitignore`), trzymajcie je na dysku współdzielonym.

## Architektura

| Moduł | Rola |
|---|---|
| `bajka/scenario.py` | Wczytanie i walidacja scenariusza YAML |
| `bajka/config.py` | Ustawienia z `.env` |
| `bajka/ports.py` | Interfejsy: `Player`, `Listener`, `Voice`, `IntentResolver` |
| `bajka/engine.py` | `StoryEngine`: przebieg bajki, dopytywanie, ścieżki awaryjne |
| `bajka/intent.py` | Azure OpenAI: intencja + kwestia bohatera (structured outputs) |
| `bajka/speech.py` | Azure AI Speech: STT z mikrofonu, TTS z odtwarzaniem do końca |
| `bajka/player.py` | VLC osadzony w pełnoekranowym oknie tkinter |
| `bajka/console.py` | Tryb `--text` do prób bez mikrofonu |
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg) |
| `bajka/app.py` | Złożenie całości i uruchomienie |

Silnik zależy tylko od interfejsów z `ports.py`, więc testy działają na atrapach,
bez Azure, mikrofonu i VLC.

## Testy

```powershell
python -m pytest
```

## Problemy

- `FileNotFoundError: ... libvlc.dll`: brak VLC albo zainstalowana wersja 32-bit.
- Bohater nie słyszy dziecka: Ustawienia Windows → Prywatność → Mikrofon → zezwól aplikacjom klasycznym;
  sprawdź domyślne urządzenie nagrywania.
- `STT anulowane: ... 401` albo `TTS anulowane`: zły `AZURE_SPEECH_KEY` lub `AZURE_SPEECH_REGION`.
- Dziecko musi długo czekać albo jest ucinane: dostrój `BAJKA_INITIAL_SILENCE_MS` i `BAJKA_END_SILENCE_MS`.
- Krzaki zamiast polskich znaków w konsoli: `$env:PYTHONUTF8 = "1"`.

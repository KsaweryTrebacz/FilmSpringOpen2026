# Podział pracy: dwie osoby, niezależne moduły

Bajka składa się z modułów, które porozumiewają się tylko przez kontrakty z
[`bajka/ports.py`](../bajka/ports.py). Każdy moduł ma własny plik, własne testy, własne ustawienia
i własne demo, więc dwie osoby mogą commitować równolegle na `main` bez wchodzenia sobie w drogę.

## Kto co rozwija

**Osoba A — „ucho i mózg”**: wszystko, co zamienia głos dziecka na decyzję.
**Osoba B — „oko i głos”**: wszystko, co dziecko widzi i słyszy.

| Moduł | Kontrakt | Osoba | Demo bez reszty aplikacji | Testy |
|---|---|---|---|---|
| [`bajka/stt.py`](../bajka/stt.py) — mowa dziecka → tekst | `Listener` | A | `python -m bajka.stt --repeat 3` | `tests/test_stt.py` |
| [`bajka/intent.py`](../bajka/intent.py) — tekst → wybór + kwestia bohatera | `IntentResolver` | A | `python -m bajka.intent scenarios/las_czy_jaskinia.yaml "tam gdzie ciemno"` | `tests/test_intent.py` |
| [`bajka/console.py`](../bajka/console.py) — zastępstwo mikrofonu i głosu do prób | `Listener`, `Voice` | A | `python -m bajka scenarios/las_czy_jaskinia.yaml --text --windowed` | `tests/test_console.py` |
| [`bajka/foundry.py`](../bajka/foundry.py) — modele Foundry Local na NPU/GPU/CPU | — | A | `python -m bajka.foundry --device NPU` | `tests/test_foundry.py` |
| [`bajka/local_stt.py`](../bajka/local_stt.py) — mowa dziecka → tekst lokalnie (Whisper) | `Listener` | A | `python -m bajka.local_stt --repeat 3` | `tests/test_local_stt.py` |
| [`bajka/local_intent.py`](../bajka/local_intent.py) — tekst → wybór lokalnie (Phi) | `IntentResolver` | A | `python -m bajka.local_intent scenarios/klub_ciekawskich.yaml "lornetkę" --scene pomocnik` | `tests/test_local_intent.py` |
| [`bajka/keywords.py`](../bajka/keywords.py) — tekst → wybór po słowach kluczowych, zapas dla LLM | `IntentResolver` | A | `python -m bajka.keywords scenarios/klub_ciekawskich.yaml "lornetkę" --scene pomocnik` | `tests/test_keywords.py` |
| [`bajka/vote.py`](../bajka/vote.py) — krzykomierz: decyzje widowni w kinie okrzykiem | `ShoutMeter` | A | `python -m bajka.vote` (kalibracja na sali) | `tests/test_vote.py` |
| [`bajka/safety.py`](../bajka/safety.py) — filtr kwestii modelu (regulamin §3 ust. 8) | `IntentResolver` | A | — | `tests/test_safety.py` |
| [`bajka/mobile.py`](../bajka/mobile.py) + [`bajka/mobile_app/`](../bajka/mobile_app/) — aplikacja mobilna widowni: odpowiedzi z mikrofonów telefonów | `Audience` | A | `python -m bajka.mobile scenarios/klub_ciekawskich.yaml --scene kuferek` | `tests/test_mobile.py` |
| [`bajka/tts.py`](../bajka/tts.py) — kwestia bohatera → głos | `Voice` | B | `python -m bajka.tts "Idziemy do lasu?"` | `tests/test_tts.py` |
| [`bajka/local_tts.py`](../bajka/local_tts.py) — kwestia bohatera → głos Windows, offline | `Voice` | B | `python -m bajka.local_tts "Cześć!"` | `tests/test_local_tts.py` |
| [`bajka/player.py`](../bajka/player.py) — VLC w pełnoekranowym oknie | `Player` | B | `python -m bajka.player KLIP PĘTLA` | ręcznie (wymaga VLC) |
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |

Wszystkie moduły działają na poziomie szkieletu (testy na atrapach). Najbliższe kroki:

- **A:** `pip install -e ".[dev,local]"`, pobrać modele (`python -m bajka.foundry --device NPU`, potem
  `python -m bajka.local_stt` i `python -m bajka.local_intent`); sprawdzić Whisper z dziećmi i w hałasie,
  dostroić `BAJKA_VAD_THRESHOLD` / `BAJKA_END_SILENCE_MS`; stroić prompt w `intent.py` i `keywords`
  w scenariuszu na prawdziwych wypowiedziach.
- **B:** zainstalować VLC 64-bit (`winget install --id VideoLAN.VLC -e`) i sprawdzić przejście klip → pętla;
  dodać polski głos Windows i dobrać wysokość i tempo Lili (`BAJKA_WINDOWS_VOICE_PITCH`, `BAJKA_WINDOWS_VOICE_RATE`)
  przez `python -m bajka.local_tts`; przygotować klipy z [listy w scenariuszu](../scenarios/klub_ciekawskich.md#lista-klipów-do-produkcji).

## Zasady modułu

Wzór: [`bajka/stt.py`](../bajka/stt.py) i [`tests/test_stt.py`](../tests/test_stt.py).

1. **Własny plik** `bajka/<moduł>.py` i **własne testy** `tests/test_<moduł>.py`.
2. **Własne ustawienia**: klasa `<Coś>Settings.from_env(env)` (jak `SttSettings`, `TtsSettings`, `LlmSettings`)
   korzystająca z `require` i `get_int` z [`bajka/config.py`](../bajka/config.py). Nowa zmienna = nowe pole
   w ustawieniach własnego modułu + wpis w jego sekcji `.env.example`.
3. **Własne demo** `python -m bajka.<moduł>`, które sprawdza moduł bez reszty aplikacji i kończy się kodem
   2 przy braku ustawień, a 1 przy błędzie usługi.
4. **Brak importów modułów drugiej osoby** — moduł importuje tylko `bajka.config`, `bajka.ports`
   i ewentualnie `bajka.scenario`.
5. **Kontrakt sprawdzony testem**: `isinstance(moduł, Listener)` itp. (kontrakty są `@runtime_checkable`).
6. **Testy bez sieci, mikrofonu i VLC** — zewnętrzne SDK zastępujemy atrapami (np. `FakeRecognizer`,
   `FakeSynthesizer`). Testy nie importują `bajka.player`.

## Pliki wspólne

Zmieniajcie je małymi, osobnymi commitami, od razu wypychajcie i dajcie znać drugiej osobie:

- `bajka/ports.py` — kontrakty; zmiana sygnatury wymaga zmian po obu stronach,
- `bajka/scenario.py` — model scenariusza; używają go `intent.py` (A) i `placeholders.py` (B),
- `bajka/engine.py` i `bajka/app.py` — składają moduły; rozwijacie je razem,
- `bajka/config.py`, `bajka/audio.py`, `tests/conftest.py`, `pyproject.toml`, `.env.example`, `README.md`,
- scenariusze w `scenarios/` (np. [`klub_ciekawskich.yaml`](../scenarios/klub_ciekawskich.yaml) — test
  `tests/test_klub_ciekawskich.py` pilnuje grafu i rozpoznawania typowych odpowiedzi).

Moduły lokalnego AI (`local_*`, `foundry.py`, `keywords.py`) korzystają z promptu z `intent.py` (A) i odtwarzania
z `audio.py` — szczegóły w [LOKALNE_AI.md](LOKALNE_AI.md).

## Git

Wszystko idzie bezpośrednio na `main`, bez gałęzi.

```powershell
git pull --rebase origin main
python -m pytest
git push origin main
```

Commitujcie często i wypychajcie po każdym działającym kroku, żeby druga osoba miała świeży stan.

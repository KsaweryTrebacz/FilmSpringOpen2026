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
| [`bajka/tts.py`](../bajka/tts.py) — kwestia bohatera → głos | `Voice` | B | `python -m bajka.tts "Idziemy do lasu?"` | `tests/test_tts.py` |
| [`bajka/player.py`](../bajka/player.py) — VLC w pełnoekranowym oknie | `Player` | B | `python -m bajka.player KLIP PĘTLA` | ręcznie (wymaga VLC) |
| [`bajka/placeholders.py`](../bajka/placeholders.py) — klipy-zaślepki | — | B | `python -m bajka.placeholders scenarios/las_czy_jaskinia.yaml` | `tests/test_placeholders.py` |

Wszystkie moduły działają na poziomie szkieletu (testy na atrapach). Najbliższe kroki:

- **A:** sprawdzić `python -m bajka.stt` z dziećmi i w hałasie, dostroić `BAJKA_INITIAL_SILENCE_MS` /
  `BAJKA_END_SILENCE_MS`; stroić prompt w `intent.py` na prawdziwych wypowiedziach przez `python -m bajka.intent`.
- **B:** zainstalować VLC 64-bit (`winget install --id VideoLAN.VLC -e`) i sprawdzić przejście klip → pętla;
  dobrać głos i tempo bohatera (`BAJKA_VOICE`, `BAJKA_VOICE_RATE`) przez `python -m bajka.tts`.

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
- `bajka/config.py`, `tests/conftest.py`, `pyproject.toml` (wszystkie zależności już są), `.env.example`, `README.md`.

## Git

Wszystko idzie bezpośrednio na `main`, bez gałęzi.

```powershell
git pull --rebase origin main
python -m pytest
git push origin main
```

Commitujcie często i wypychajcie po każdym działającym kroku, żeby druga osoba miała świeży stan.

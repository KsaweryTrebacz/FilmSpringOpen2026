# Bajka interaktywna: odcinek, w którym decyduje widz

Prototyp na hackathon FilmSpring Open 2026: animowana bajka dla dzieci do oglądania w serwisie streamingowym.
W kluczowych momentach postać zadaje pytanie, a na ekranie pojawia się **okno wyboru** z obrazkami i odliczaniem.
Dziecko wybiera **pilotem, dotykiem albo głosem** („przez ten kolorowy mostek!”), a historia idzie w wybraną stronę.
W przyszłości tempo odcinka może dopasowywać się do **tętna widza** z zegarka (dziś: symulator).

Domyślnie całe AI działa **lokalnie na urządzeniu** (Foundry Local z Whisper i Phi na NPU/GPU/CPU) — bez chmury
i bez kluczy: [docs/LOKALNE_AI.md](docs/LOKALNE_AI.md). Usługi Azure zostają jako alternatywa (`--backend azure`).

Odcinek: **„Klub Ciekawskich: Bzyczka szuka domu”** ([scenariusz odcinka](scenarios/klub_ciekawskich.md),
[graf scen dla aplikacji](scenarios/klub_ciekawskich.yaml)). Dlaczego streaming, jak to wygląda na rynku i jak
odcinek trafia do serwisów: [docs/STREAMING.md](docs/STREAMING.md). Zgodność z regulaminem hackathonu:
[docs/ZGODNOSC_Z_REGULAMINEM.md](docs/ZGODNOSC_Z_REGULAMINEM.md).
**Nowa osoba w zespole? Zacznij od [docs/ONBOARDING.md](docs/ONBOARDING.md).** Podział pracy:
[docs/PODZIAL_PRACY.md](docs/PODZIAL_PRACY.md). Co zostało do zrobienia: [docs/DO_ZROBIENIA.md](docs/DO_ZROBIENIA.md).

## Jak to działa

1. Odtwarzacz (strona w przeglądarce, jak w serwisie streamingowym) gra klip, w którym postać zadaje pytanie.
2. Klip przechodzi w cichą pętlę oczekiwania, a na dole ekranu wysuwa się okno wyboru: 2–3 opcje z obrazkami,
   nazwami i paskiem odliczania (domyślnie 12 s). Pytanie jest też w napisach i czytane na głos.
3. Widz wybiera:
   - **pilotem** (strzałki i OK; w przeglądarce strzałki i Enter), **dotykiem**, myszą albo cyfrą 1–3 — wybór od razu;
   - **głosem**, jeśli rodzic zostawił włączony mikrofon: strona nagrywa odpowiedź w trakcie okna wyboru, Whisper
     (Foundry Local) zamienia ją na tekst, a Phi (Foundry Local) rozpoznaje intencję i może dopisać krótką osobistą
     kwestię. Gdy model zawiedzie, wybór rozpoznają słowa kluczowe ze scenariusza.
4. Po wyborze gra nagrany klip reakcji postaci, a gdzie go nie ma — postać mówi kwestię ze scenariusza
   (napisy + głos syntezatora przeglądarki). Potem startuje klip wybranej ścieżki.
5. Czas minął bez wyboru albo odpowiedź była niejasna: postać dopytuje (domyślnie 2 razy), potem wybiera sama.
   Odcinek nigdy nie staje.
6. Na końcu ekran „Koniec odcinka!” pokazuje wybory widza i proponuje obejrzenie jeszcze raz (cztery zakończenia).

Kwestie pisane na żywo przez model przechodzą przez filtr treści (`bajka/safety.py`). Awaria rozpoznawania mowy,
modelu albo głosu nie zatrzymuje odcinka: zostaje wybór pilotem, a w ostateczności wybór domyślny.

## Wymagania

- Windows 10/11 (działa też na Linuksie i macOS), Python 3.11+ w wersji 64-bit
- Przeglądarka: Edge albo Chrome (odtwarzacz i mikrofon); polski głos syntezatora w Ustawienia → Czas i język → Mowa
- ffmpeg do klipów-zaślepek i wersji liniowej: `winget install --id Gyan.FFmpeg -e`
- Tryb lokalny (domyślny): najlepiej Copilot+ PC z NPU; bez NPU modele idą na GPU albo CPU
- Opcjonalnie VLC 3.x 64-bit (`--player vlc`): `winget install --id VideoLAN.VLC -e`
- Tryb `azure`: zasób AI Speech oraz zasób Azure OpenAI z wdrożeniem modelu `gpt-4o-mini`

## Instalacja

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,local,mobile]"
Copy-Item .env.example .env   # tryb lokalny działa bez zmian; klucze tylko dla --backend azure
```

## Uruchomienie

```powershell
# klipy-zaślepki (kolorowe plansze z nazwą pliku), dopóki nie ma animacji
python -m bajka.placeholders scenarios/klub_ciekawskich.yaml

# najszybsza próba: cały odcinek w konsoli, bez wideo, mikrofonu i AI (cyfra = przycisk pilota, tekst = głos)
python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm

# odcinek w przeglądarce bez modeli: okna wyboru pilotem i dotykiem, wybór po słowach kluczowych
python -m bajka scenarios/klub_ciekawskich.yaml --no-llm --no-mic

# pełny prototyp: okna wyboru, odpowiedzi głosem, Whisper i Phi lokalnie
python -m bajka scenarios/klub_ciekawskich.yaml

# z panelem podglądu (drzewo wyborów, symulowane tętno widza) i drugim ekranem (telefony jako pilot z mikrofonem)
python -m bajka scenarios/klub_ciekawskich.yaml --panel --mobile

# dawny tryb: pełny ekran VLC, odpowiedzi tylko głosem z mikrofonu komputera
python -m bajka scenarios/klub_ciekawskich.yaml --player vlc
```

Aplikacja sama otwiera przeglądarkę z odcinkiem (`http://127.0.0.1:8080/`; `--no-browser`, żeby nie otwierać).
Przycisk **▶ Oglądaj** odblokowuje dźwięk i mikrofon (zasada przeglądarek), **⚙** to ustawienia rodzica
(mikrofon, głos postaci, napisy), **F** — pełny ekran, **✕** kończy odcinek i aplikację. Zamknięta karta wstrzymuje
odcinek: po ponownym otwarciu bieżący klip gra od początku. Ctrl+C w konsoli kończy aplikację.

## Odcinek w serwisie streamingowym

Prototyp sam jest odtwarzaczem (`bajka/web_player.py`), ale odcinek da się też oddać serwisowi:

| Droga | Polecenie | Dla kogo |
|---|---|---|
| **Wersja interaktywna z naszym silnikiem** | `python -m bajka …` | Pokaz, aplikacja na tablet/PC, test z rodzinami |
| **Manifest odcinka** (JSON) | `python -m bajka.manifest scenarios/klub_ciekawskich.yaml --out odcinek.json` | Serwis z własnym odtwarzaczem interaktywnym: graf scen, okna wyboru, reakcje, wersje scen, opisy do rozpoznawania głosu |
| **Wersja liniowa** (zwykły film) | `python -m bajka.linear scenarios/klub_ciekawskich.yaml` | Serwisy i telewizory bez interakcji: ścieżka wyborów domyślnych, postać sama wybiera, kwestie w napisach `.srt` |

Szczegóły, realia rynku i plan dystrybucji: [docs/STREAMING.md](docs/STREAMING.md).

## Drugi ekran: telefon jako pilot z mikrofonem

Telewizor często nie ma mikrofonu. Wtedy domownik może odpowiadać z telefonu (`--mobile` albo `BAJKA_MOBILE=1`):

1. Komputer z odcinkiem uruchamia lokalny serwer HTTPS i wypisuje adres, np. `https://192.168.1.20:8443/`
   (pod `…/qr` jest strona z kodem QR).
2. Telefon w tej samej sieci Wi-Fi otwiera stronę (bez instalowania) i po dotknięciu „Dołączam” zezwala na mikrofon.
3. Gdy postać zadaje pytanie, telefon wibruje, pokazuje opcje i sam nagrywa odpowiedź; można też dotknąć opcji.
   Komputer rozpoznaje nagrania lokalnie i liczy głosy — przy kilku telefonach (rodzeństwo) wygrywa większość.

Gdy połączony jest choć jeden telefon, decyzje zbierają telefony; okno wyboru na dużym ekranie wraca, gdy telefony
się rozłączą. Przeglądarki dają mikrofon tylko przez HTTPS: aplikacja tworzy samopodpisany certyfikat, więc telefon
raz pokaże ostrzeżenie do zaakceptowania (bez ostrzeżeń: `BAJKA_MOBILE_CERT` i `BAJKA_MOBILE_KEY`). Nagrania trafiają
do komputera na chwilę do pliku tymczasowego i są usuwane zaraz po rozpoznaniu. Próba bez odcinka:
`python -m bajka.mobile scenarios/klub_ciekawskich.yaml --scene kuferek --no-llm`.

## Odcinek, który czuje widza (tętno — pomysł na przyszłość)

Scenariusz mówi, jakiej dynamiki chcemy (`mood: spokojny`, `zywy` albo `zrownowazony`), a wybrane sceny mają
inne wersje montażu (`variants: spokojna / zywa`). Gdy tętno widza odbiega od punktu odniesienia z początku odcinka,
scena gra wersję, która przywraca uwagę albo spokój: przy pobudzeniu — spokojną (dłuższe ujęcia, cichszy dźwięk),
przy znużeniu — żywą (szybszy montaż, zabawny gag). Odcinek „Bzyczka” jest zrównoważony i ma obie wersje
w trzech scenach ([projekt](docs/superpowers/specs/2026-10-16-film-czuje-sale-design.md)).

**Tętno jest dziś symulowane** (`bajka/pulse.py`), a **panel podglądu** (`--panel`, `http://127.0.0.1:8090/`)
pokazuje drzewo scen z przebytą ścieżką, wybory widza, wykres tętna z pasmem normy i dziennik decyzji odcinka;
suwak i gotowe stany (spokój, pobudzenie, znużenie) sterują symulatorem. Przebieg pokazu: [docs/DEMO_DLA_JURY.md](docs/DEMO_DLA_JURY.md).

Wizja: zegarek dziecka sparowany z telefonem rodzica przekazuje tętno przez Health Connect (Android), HealthKit (iOS)
albo standardową usługę Bluetooth „Heart Rate” do urządzenia, na którym gra odcinek. Dane o zdrowiu to szczególna
kategoria danych osobowych (RODO, art. 9), więc: wyraźna zgoda rodzica, przetwarzanie tylko na urządzeniu i tylko
w trakcie odcinka, żadnego zapisywania ani wysyłania do serwisu, a tętno służy wyłącznie do wyboru wersji sceny.

## Sprawdzanie modułów osobno

Każdy moduł ma własne demo, które działa bez reszty aplikacji:

```powershell
python -m bajka.foundry --device NPU                 # katalog modeli Foundry Local i ich warianty
python -m bajka.local_stt --repeat 3                 # mikrofon → tekst (Whisper lokalnie)
python -m bajka.local_tts "Cześć! Jestem Lila Lupka!"  # tekst → głos postaci (Windows)
python -m bajka.local_intent scenarios/klub_ciekawskich.yaml "tam gdzie ciemno" --scene kuferek   # wypowiedź → wybór (Phi)
python -m bajka.keywords scenarios/klub_ciekawskich.yaml "lornetkę" --scene pomocnik   # wypowiedź → wybór (słowa kluczowe)
python -m bajka.mobile scenarios/klub_ciekawskich.yaml --scene kuferek   # rundy pytań na telefonach (drugi ekran)
python -m bajka.manifest scenarios/klub_ciekawskich.yaml   # manifest odcinka (JSON) na ekran
python -m bajka.linear scenarios/klub_ciekawskich.yaml --plan   # plan montażu wersji liniowej
python -m bajka.stt --repeat 3                       # mikrofon → tekst (Azure STT)
python -m bajka.tts "Idziemy do lasu czy do jaskini?" # tekst → głos postaci (Azure TTS)
python -m bajka.intent scenarios/las_czy_jaskinia.yaml "tam gdzie ciemno"   # wypowiedź → wybór (Azure OpenAI)
python -m bajka.player scenarios/clips/intro.mp4 scenarios/clips/intro_idle.mp4   # klip → pętla (VLC)
python -m bajka.pulse --script                       # symulator tętna widza: spokój, pobudzenie, uspokojenie
python -m bajka.panel scenarios/klub_ciekawskich.yaml   # panel podglądu bez odcinka (symulator tętna)
```

## Scenariusz

Odcinek to graf scen w YAML ([pełny odcinek](scenarios/klub_ciekawskich.yaml),
[najprostszy przykład](scenarios/las_czy_jaskinia.yaml)). Ścieżki klipów są względne wobec pliku
scenariusza. Scena bez `choices` kończy odcinek.

| Pole | Opis |
|---|---|
| `title` | Opcjonalnie: tytuł odcinka na ekranie startowym i w manifeście |
| `hero` | Opis postaci dla modelu językowego: imię, charakter, sposób mówienia, do kogo mówi |
| `start` | Identyfikator pierwszej sceny |
| `mood` | Opcjonalnie: `spokojny`, `zywy` albo `zrownowazony` — jak odcinek reaguje na tętno widza |
| `scenes.<id>.clip` | Klip sceny (postać zadaje pytanie albo kończy historię) |
| `scenes.<id>.variants` | Opcjonalnie: wersje montażu sceny według tętna, np. `spokojna: las_spokojna.mp4`, `zywa: …` |
| `scenes.<id>.idle` | Cicha pętla oczekiwania, tło okna wyboru (wymagana, gdy są `choices`) |
| `scenes.<id>.question` | Pytanie zadane w klipie; nagłówek okna wyboru i kontekst dla modelu |
| `scenes.<id>.reprompt` | Kwestia postaci, gdy czas minie bez wyboru |
| `scenes.<id>.fallback` | Opcjonalnie: wstęp, gdy postać sama wybiera (domyślnie „Dobrze, to ja wybiorę!”) |
| `scenes.<id>.default` | Wybór, gdy po dopytaniach nadal brak decyzji albo model zawiedzie |
| `scenes.<id>.timeout` | Opcjonalnie: ile sekund trwa okno wyboru (3–60; domyślnie `BAJKA_CHOICE_SECONDS`, 12 s) |
| `choices.<id>.label` | Krótka nazwa opcji w oknie wyboru i na telefonie (domyślnie identyfikator) |
| `choices.<id>.icon` | Obrazek opcji dla dzieci, które nie czytają (w prototypie emoji) |
| `choices.<id>.description` | Znaczenie wyboru dla modelu, np. „pójść do mrocznego lasu” |
| `choices.<id>.next` | Scena, która nastąpi po tym wyborze |
| `choices.<id>.reply` | Kwestia postaci po wyborze (gdy nie ma klipu reakcji) |
| `choices.<id>.reaction` | Opcjonalnie: nagrany klip reakcji postaci na ten wybór (ma pierwszeństwo przed `reply`) |
| `choices.<id>.keywords` | Opcjonalnie: słowa, po których odpowiedź głosem rozpozna się bez modelu |

## Wskazówki do klipów

- Pętla oczekiwania z bardzo cichym podkładem i bez dialogów; dolna jedna trzecia kadru wolna (tam jest okno wyboru).
- Ostatnia klatka klipu z pytaniem = pierwsza klatka pętli, wtedy przejście jest niewidoczne.
- Format: MP4, H.264 + AAC z indeksem na początku pliku (`-movflags +faststart`) — szybki start w przeglądarce.
- Klipy nie są w repozytorium (`scenarios/clips/` jest w `.gitignore`), trzymajcie je na dysku współdzielonym.

## Architektura

| Moduł | Rola |
|---|---|
| `bajka/scenario.py` | Wczytanie i walidacja scenariusza YAML (`media_files`, `missing_media`) |
| `bajka/config.py` | Wspólne narzędzia ustawień: `load_env`, `require`, `get_int`, `get_float` |
| `bajka/ports.py` | Kontrakty: `Player`, `Viewer` (okno wyboru → `Answer`), `Listener`, `Voice`, `IntentResolver`, `Audience`, `AudiencePulse`, `ShowObserver` |
| `bajka/engine.py` | `StoryEngine`: przebieg odcinka, okna wyboru, dopytywanie, reakcje, wersje scen, ścieżki awaryjne |
| `bajka/web_player.py` | Odtwarzacz w przeglądarce: serwer HTTP, klipy z zakresami bajtów, okna wyboru, głos z przeglądarki (`WebEpisode`, `WebPlayerServer`) |
| `bajka/player_app/` | Strona odtwarzacza: wideo, okno wyboru z odliczaniem, pilot/dotyk/głos, napisy, ustawienia rodzica, ekran końcowy |
| `bajka/linear.py` | Wersja liniowa odcinka (ffmpeg) i napisy `.srt` |
| `bajka/manifest.py` | Manifest odcinka (JSON) dla odtwarzacza serwisu |
| `bajka/foundry.py` | Foundry Local: modele lokalne na NPU/GPU/CPU, serwer zgodny z OpenAI |
| `bajka/local_stt.py` | Whisper lokalnie + wykrywanie wypowiedzi (`LocalListener`, `FoundryTranscriber`) |
| `bajka/local_intent.py` | Phi lokalnie: intencja + kwestia postaci (`LocalIntentResolver`) |
| `bajka/local_tts.py` | Głos z syntezatora Windows dla `--player vlc` (`WindowsVoice`) |
| `bajka/stt.py`, `bajka/tts.py`, `bajka/intent.py` | To samo na usługach Azure (`--backend azure`) |
| `bajka/keywords.py` | Wybór po słowach kluczowych, offline (`KeywordIntentResolver`, `FallbackResolver`) |
| `bajka/safety.py` | Filtr kwestii modelu językowego (`SafeReplyResolver`) |
| `bajka/mobile.py`, `bajka/mobile_app/` | Drugi ekran: telefony jako pilot z mikrofonem (`MobileAudience`, `MobileServer`) |
| `bajka/pulse.py` | Tętno widza: symulator (`SimulatedPulse`), stan widza (`hall_state`), wybór wersji (`pick_variant`) |
| `bajka/panel.py`, `bajka/panel_app/` | Panel podglądu: drzewo scen, wybory, tętno, dziennik decyzji (`PanelState`, `PanelServer`) |
| `bajka/player.py` | VLC osadzony w pełnoekranowym oknie tkinter (`--player vlc`) |
| `bajka/console.py` | Tryb `--text`: odcinek w konsoli (`ConsolePlayer`, `ConsoleViewer`, `ConsoleVoice`) |
| `bajka/placeholders.py` | Generator klipów-zaślepek (ffmpeg; MP4 albo WebM) |
| `bajka/app.py` | Złożenie całości i uruchomienie |

Silnik zależy tylko od kontraktów z `ports.py`, a każdy moduł czyta własne ustawienia
(`XxxSettings.from_env`). Testy działają na atrapach, bez Azure, mikrofonu, przeglądarki i VLC.

## Testy

```powershell
python -m pytest
```

Test strony telefonu (`tests/test_mobile.py`) uruchamia jej skrypt w `node`; bez `node` jest pomijany.
Test wersji liniowej buduje mały film przez ffmpeg; bez ffmpeg jest pomijany.

## Problemy

- Przeglądarka się nie otwiera: wejdź ręcznie na adres z konsoli (`http://127.0.0.1:8080/`).
- `Nie udało się uruchomić serwera (port zajęty?)` (`WinError 10048`): port zajmuje inny proces, np. zapomniany
  podgląd. Zamknij go (`netstat -ano | findstr 8080`) albo zmień `BAJKA_WEB_PORT` / `BAJKA_PANEL_PORT` / `BAJKA_MOBILE_PORT`.
- Wideo nie gra albo jest czarne: przeglądarka bez kodeka H.264 (np. Chromium) — użyj Edge/Chrome albo klipów `.webm`.
- Okno wyboru nie słucha głosu: w ustawieniach (⚙) włącz mikrofon i zezwól przeglądarce na mikrofon; strona musi być
  otwarta pod `127.0.0.1` albo `localhost` (inaczej przeglądarka nie da mikrofonu bez HTTPS). Bez `--no-mic`.
- Postać nie mówi, są tylko napisy: brak polskiego głosu syntezatora — dodaj go w Ustawienia → Czas i język → Mowa.
- Dziecko jest ucinane albo nie zdąża: wydłuż `BAJKA_CHOICE_SECONDS` albo `timeout` sceny i `BAJKA_WEB_ANSWER_SECONDS`.
- `Brak pakietu foundry-local-sdk` albo `Brak pakietów WinRT`: `pip install -e ".[local]"`.
- `Foundry Local nie zna modelu …`: sprawdź aliasy przez `python -m bajka.foundry` i popraw `FOUNDRY_CHAT_MODEL` / `FOUNDRY_STT_MODEL`.
- `Brak plików wideo`: `python -m bajka.placeholders scenarios/klub_ciekawskich.yaml` (albo `--text`, które działa bez wideo).
- Krzaki zamiast polskich znaków w konsoli: `$env:PYTHONUTF8 = "1"`.
- `--player vlc`: `FileNotFoundError: ... libvlc.dll` — brak VLC albo wersja 32-bit; postać nie słyszy dziecka —
  Ustawienia Windows → Prywatność → Mikrofon → zezwól aplikacjom klasycznym; dostrój `BAJKA_VAD_THRESHOLD`.
- Telefon (drugi ekran) nie pyta o mikrofon: otwórz adres `https://…` i zaakceptuj ostrzeżenie o certyfikacie;
  ta sama sieć Wi-Fi co komputer, port `BAJKA_MOBILE_PORT` otwarty w zaporze; sieci gościnne blokują ruch między urządzeniami.
- `rozpoznawanie anulowane: ... 401` (tryb azure): zły `AZURE_SPEECH_KEY` lub `AZURE_SPEECH_REGION`.

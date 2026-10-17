# Lokalne AI na Windows (On-Device AI)

Domyślnie bajka działa w całości na urządzeniu (`BAJKA_BACKEND=local`): rozpoznawanie mowy, model językowy
i głos postaci. Po pierwszym pobraniu modeli nie potrzeba internetu ani kluczy, a nagrania dziecka nie opuszczają
urządzenia. Tryb `azure` (usługi chmurowe) zostaje jako alternatywa.

**Droga głosu w odtwarzaczu w przeglądarce** (`--player web`, domyślnie): strona nagrywa odpowiedź tylko w trakcie
okna wyboru (wykrywanie początku i końca mowy w przeglądarce), wysyła WAV 16 kHz do lokalnej aplikacji
(`127.0.0.1`), a ta rozpoznaje ją Whisperem przez Foundry Local i usuwa plik tymczasowy zaraz po rozpoznaniu.
Głos postaci w kwestiach na żywo czyta synteza mowy przeglądarki — na Windows to te same lokalne głosy systemu
(np. Paulina), z których korzysta `bajka/local_tts.py` w trybie `--player vlc`.

## Co z zestawu Microsoftu i gdzie

| Element zestawu | Użycie w bajce | Moduł |
|---|---|---|
| **Foundry Local** (`foundry-local-sdk` 2.x) | Pobiera, ładuje i uruchamia modele lokalnie; wystawia serwer zgodny z OpenAI | [`bajka/foundry.py`](../bajka/foundry.py) |
| **Windows ML** | Silnik pod Foundry Local: na Windows pakiet SDK zawiera Windows ML i rejestruje akceleratory (NPU, GPU) — `download_and_register_eps()` | `bajka/foundry.py` |
| **Model Phi** (domyślnie `phi-4-mini`) z katalogu Foundry Local | Rozumie odpowiedź dziecka i pisze reakcję Lili (JSON wymuszony schematem) | [`bajka/local_intent.py`](../bajka/local_intent.py) |
| Ten sam **model Phi** jako montażysta | Wybiera przejście między klipami (rodzaj, długość, powód) na podstawie wyboru widza, jego słów i tętna; pracuje w tle, w zapasie reguły | [`bajka/montage.py`](../bajka/montage.py) |
| **Whisper** (domyślnie `whisper-tiny`) z katalogu Foundry Local | Mowa dziecka → tekst | [`bajka/local_stt.py`](../bajka/local_stt.py) |
| **Windows.Media.SpeechSynthesis** (WinRT, wbudowany w Windows) | Głos Lili w trybie `--player vlc`, polski głos „Microsoft Paulina”, offline | [`bajka/local_tts.py`](../bajka/local_tts.py) |
| **Rozpoznawanie mowy przeglądarki** (Web Speech API w Edge/Chrome) | Zapasowe rozpoznawanie odpowiedzi w odtwarzaczu, gdy Whisper nie działa. Lektor syntezatora w przeglądarce jest wyłączony: kwestie na żywo są w napisach | [`bajka/player_app/`](../bajka/player_app/index.html) |
| — (bez modelu) | Rozpoznawanie po słowach kluczowych: zapas, gdy model zawiedzie, i tryb `--no-llm` | [`bajka/keywords.py`](../bajka/keywords.py) |

Na **Copilot+ PC** Foundry Local sam wybiera wariant modelu na NPU, jeśli taki jest w katalogu.
Można to wymusić: `FOUNDRY_DEVICE=NPU` (albo `GPU`, `CPU`). Jeśli model nie ma wariantu na dane urządzenie,
aplikacja zapisze ostrzeżenie w logu i zostanie przy wyborze automatycznym.

## Instalacja i pierwsze uruchomienie

```powershell
pip install -e ".[dev,local]"
python -m bajka.foundry                 # katalog modeli i warianty (CPU/GPU/NPU); pierwszy raz pobiera akceleratory
python -m bajka.foundry --device NPU    # tylko modele z wariantem na NPU
python -m bajka.local_tts --list        # głosy zainstalowane w Windows; potrzebny polski
python -m bajka.local_tts "Cześć! Jestem Lila Lupka!"
python -m bajka.local_stt --repeat 3    # mikrofon → Whisper (pierwszy raz pobiera model)
python -m bajka.local_intent scenarios/klub_ciekawskich.yaml "chcę przez ten kolorowy mostek" --scene kuferek
python -m bajka scenarios/klub_ciekawskich.yaml        # odcinek w przeglądarce, odpowiedzi głosem
```

Polski głos: Ustawienia → Czas i język → Mowa → Zarządzaj głosami → Dodaj głosy → polski.

Pierwsze uruchomienie pobiera modele (Phi to kilka GB), więc zróbcie je przed pokazem, na dobrym łączu.
Kolejne uruchomienia korzystają z pamięci podręcznej Foundry Local.

## Strojenie

| Ustawienie | Domyślnie | Kiedy zmienić |
|---|---|---|
| `FOUNDRY_CHAT_MODEL` | `phi-4-mini` | Inny alias z `python -m bajka.foundry`, np. lepszy w polskim albo mniejszy na słabszym sprzęcie |
| `FOUNDRY_STT_MODEL` | `whisper-tiny` | Większy Whisper (jeśli jest w katalogu) lepiej rozumie dzieci, ale jest wolniejszy |
| `FOUNDRY_DEVICE` | `auto` | `NPU` na Copilot+ PC, `GPU` przy mocnej karcie |
| `BAJKA_VAD_THRESHOLD` | `500` | `--player vlc`: w głośnym pokoju zwiększ (np. 900), przy cichym dziecku zmniejsz |
| `BAJKA_WEB_ANSWER_SECONDS` | `6` | Odtwarzacz w przeglądarce: najdłuższe nagranie odpowiedzi |
| `BAJKA_MONTAGE` | `model` | `reguly`: przejścia bez modelu (słabszy komputer, przewidywalny pokaz) |
| `BAJKA_MONTAGE_WAIT` | `0.5` | Ile sekund czekać na decyzję modelu, gdy przejście trzeba już zagrać |
| `BAJKA_END_SILENCE_MS` | `1200` | Dzieci robią przerwy w zdaniu — przy ucinaniu zwiększ |
| `BAJKA_WINDOWS_VOICE_PITCH` | `1.0` | 1.1–1.3 brzmi bardziej bajkowo |
| `BAJKA_WINDOWS_VOICE_RATE` | `0.9` | Wolniej dla młodszych dzieci |

## Odporność na błędy

- Model językowy zawiedzie (błąd, zły JSON) → wybór po słowach kluczowych ze scenariusza (`keywords`).
- Montażysta nie zdąży albo zwróci bzdurę → przejście z reguł; decyzja modelu jest zawsze przycinana do dozwolonych
  rodzajów i długości (rozjaśnienie co najmniej 0,8 s, bez błysków).
- Serwer odrzuci format odpowiedzi ze schematem → aplikacja przechodzi na `json_object` i zostaje przy nim.
- Whisper „usłyszy” w szumie napisy z filmów (np. „Amara.org”) → traktujemy to jak ciszę.
- Brak pakietów, głosu albo modelu → aplikacja kończy się kodem 2 z komunikatem, co doinstalować.

## Czego nie używamy i dlaczego

- **Phi Silica** (Windows App SDK) — API jest Limited Access Feature (token od Microsoftu albo wersja
  eksperymentalna), wymaga aplikacji z tożsamością pakietu (MSIX) i Copilot+ PC z Windows 11 25H2+.
  Skrypt w Pythonie tych warunków nie spełnia. To dobra droga dla przyszłej natywnej aplikacji
  WinUI 3 / .NET MAUI; wtedy także **LoRA** do dostrojenia Phi Silica do stylu Lili. Interfejs
  `IntentResolver` w `bajka/ports.py` pozwala podmienić model bez zmian w silniku.
- **Edge / WebNN** — odtwarzacz działa już w przeglądarce, ale modele uruchamia lokalna aplikacja w Pythonie
  (Foundry Local). WebNN to kierunek na przyszłość: Whisper i mały model językowy w samej przeglądarce telewizora
  albo tabletu, bez aplikacji na komputerze — wtedy odcinek z serwisu działałby z głosem na samym urządzeniu widza.

## Co sprawdzić na prawdziwym sprzęcie

Kod lokalnego AI jest przetestowany na atrapach (bez sieci, mikrofonu i Windows). Na komputerze z Windows
trzeba potwierdzić: pobranie i załadowanie `phi-4-mini` i `whisper-tiny`, wariant na NPU (`python -m bajka.foundry
--device NPU`), jakość rozpoznawania polskiej mowy dzieci przez Whisper, polski głos Windows i czasy
odpowiedzi (każde demo je wypisuje).

Źródła: [Foundry Local](https://github.com/microsoft/Foundry-Local) (przykłady `samples/python`,
`docs/Structured Outputs.md`), [Phi Silica](https://learn.microsoft.com/windows/ai/apis/phi-silica),
[Windows AI — rozwiązywanie problemów](https://learn.microsoft.com/windows/ai/apis/troubleshooting).

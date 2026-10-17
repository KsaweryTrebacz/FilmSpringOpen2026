# Zgodność z regulaminem hackathonu

Podstawa: Regulamin konkursu programistyczno-filmowego „KINO SZUKA NOWEJ FORMY. ZNAJDŹ JĄ. Hackathon o przyszłości
odbioru dzieł audiowizualnych” (Fundacja Film Spring Open, 21. Plenery Film Spring Open, Kraków, 16–18.10.2026).
Dotyczy odcinka interaktywnego [„Bzyczka szuka domu”](../scenarios/klub_ciekawskich.md) i aplikacji `bajka`.
Od 17.10.2026 projekt to bajka interaktywna do serwisów streamingowych (okna wyboru, odpowiedź pilotem albo głosem),
a nie seans kinowy z udziałem widowni ([co się zmieniło](STREAMING.md#co-się-zmieniło-17102026)).

Oznaczenia: **OK** — spełnione · **POPRAWIONE** — naprawione w repozytorium · **ZESPÓŁ** — do zrobienia przez
zespół · **ZAPYTAĆ** — do wyjaśnienia z organizatorem.

## Przegląd

| Regulamin | Wymóg | Stan | Co zrobiliśmy / co zostaje |
|---|---|---|---|
| §2 ust. 2 | „Zarys filmów, aplikacji, gier… umożliwiających odbiór dzieł sztuki na nowej, interakcyjnej płaszczyźnie” | **OK** / **ZAPYTAĆ** | Interaktywny odcinek animowany: widz w domu współdecyduje o przebiegu w oknach wyboru (pilot, dotyk, głos), a postacie reagują. Do tego działający prototyp odtwarzacza i aplikacji. Regulamin obejmuje „filmy, aplikacje, gry”, a temat to „przyszłość odbioru dzieł audiowizualnych”, więc odbiór w serwisie streamingowym mieści się w zadaniu. Hasło hackathonu brzmi jednak „Kino szuka nowej formy” — warto potwierdzić z organizatorem, że forma poza salą kinową jest w porządku, i w pitchu powiedzieć, że ten sam odcinek da się pokazać w kinie (wersja liniowa albo pokaz z jednym „pilotem” dla sali) |
| §2 ust. 3 i 5 | Prezentacja przed jury 18.10 o 19:00 | **POPRAWIONE** / **ZAPYTAĆ** | Scenariusz ma [plan na hackathon](../scenarios/klub_ciekawskich.md#plan-na-hackathon-prezentacja-18102026-1900) (zarys całego odcinka + jedna scena w pełnej animacji), a [DEMO_DLA_JURY.md](DEMO_DLA_JURY.md) — przebieg pokazu. W §2 ust. 3 jest data „18.10.2022” — oczywista literówka, ale warto ją potwierdzić z organizatorem |
| §3 ust. 4, 6, 7 | Zgłoszenie przez formularz (nazwa zespołu, lider, e-mail); uczestnicy pełnoletni albo 13+ za zgodą opiekunów; wykluczenie pracowników organizatora i partnerów oraz ich rodzin | **ZESPÓŁ** | Sprawdzić, czy zgłoszenie jest wysłane i czy żaden członek zespołu nie podlega wykluczeniu |
| §3 ust. 8 | Bez treści obraźliwych, wulgarnych, propagujących przemoc, niemoralnych, nieprawdziwych lub wprowadzających w błąd | **POPRAWIONE** | Szczegóły niżej: filtr kwestii AI, zasady w prompcie, sprawdzone fakty, poprawione dwa fakty w scenariuszu, informacja o AI w napisach |
| §3 ust. 9 | Lider oświadcza, że zespołowi przysługują wyłączne prawa autorskie do pracy, która jest oryginalna i wolna od roszczeń osób trzecich | **POPRAWIONE** / **ZESPÓŁ** | Szczegóły niżej: oryginalne postacie, muzyka tylko własna, treści z AI jako szkic do opracowania przez zespół, licencje narzędzi |
| §3 ust. 10 | Praca może zostać opublikowana na stronie i w mediach społecznościowych organizatora | **ZESPÓŁ** | Wszystko, co pokażemy, musi nadawać się do publikacji: bez nagrań dzieci bez zgody opiekunów, bez cudzych utworów |
| §4 ust. 5 | Kryteria: innowacyjność, adekwatność do zadania, oryginalność, kreatywność | **OK** | Mapowanie na pitch niżej |
| §5 ust. 3 | Najlepszy projekt to pomysł wart dalszego rozwijania i testowania z prawdziwą publicznością | **OK** / **ZESPÓŁ** | Odcinek da się przetestować w domach rodzin z dziećmi na zwykłym laptopie albo tablecie; plan testu niżej |
| §6 | Ochrona danych (RODO) | **OK** / **ZESPÓŁ** | Aplikacja nie przechowuje głosu ani wypowiedzi (nagranie trafia na chwilę do pliku tymczasowego, usuwanego zaraz po rozpoznaniu); lokalne AI przetwarza mowę na urządzeniu, bez wysyłania nagrań do chmury. Mikrofon tylko w oknie wyboru i tylko za zgodą rodzica — szczegóły niżej |

## §3 ust. 8 — treści

Odcinek oglądają małe dzieci, a część kwestii Lili pisze na żywo model językowy. Dlatego zabezpieczenia są w trzech
warstwach:

1. **Scenariusz** — wszystkie kwestie stałe są napisane i sprawdzone przez ludzi. Nie ma przemocy ani straszenia.
   Fakty edukacyjne są zebrane i sprawdzone w tabeli [„Sprawdzone fakty”](../scenarios/klub_ciekawskich.md#sprawdzone-fakty-regulamin-3-ust-8-bez-treści-nieprawdziwych).
2. **Prompt modelu** (`bajka/intent.py`, używany też lokalnie): mów tylko prawdę o świecie, nie zmyślaj faktów,
   nie powtarzaj brzydkich ani obraźliwych słów, nie mów o przemocy, poprawiaj pomyłki łagodnie. **POPRAWIONE**
3. **Filtr kwestii** (`bajka/safety.py`): kwestia z wulgaryzmem, słowami o przemocy, linkiem albo dłuższa niż ok.
   dwa zdania nie zostaje wypowiedziana — Lila mówi zamiast niej sprawdzoną kwestię ze scenariusza. **POPRAWIONE**
   Przy wyborze pilotem model w ogóle nie pisze kwestii; tam, gdzie jest nagrany klip reakcji, gra klip.
   Przy odpowiedziach z kilku telefonów Lila mówi teksty ze scenariusza.

**Poprawione fakty w scenariuszu:**
- Sowa w dzień: sowy są aktywne głównie nocą, więc Lila mówi teraz „Sowy w dzień zwykle śpią, a my ją chyba budzimy!”.
- Ul: wcześniej „na wysokim drzewie”, co bardziej pasuje do dzikiego gniazda. Teraz ul stoi na końcu łąki pod lipą.

**Bez wprowadzania w błąd:** napisy końcowe informują, że część kwestii postaci tworzy na żywo sztuczna inteligencja
i że nagrań odpowiedzi nie przechowujemy; kwestie na żywo mają zawsze napisy. **POPRAWIONE**

## §3 ust. 9 — prawa autorskie

| Element | Stan | Uwagi |
|---|---|---|
| Postacie, imiona, świat, fabuła | **OK** | Oryginalne. Scenariusz zastrzega, że projektując postacie nie wzorujemy się na postaciach z innych filmów i seriali. W szczególności Bzyczka ma własny wygląd (miętowy sweterek w miodowe paski) i nie może przypominać znanych pszczółek z animacji. W materiałach i pitchu nie odwołujemy się do cudzych marek |
| Tekst scenariusza powstał z pomocą AI | **ZESPÓŁ** | Prawo autorskie chroni twórczość człowieka. Traktujcie tekst jako szkic: zespół go przerabia, wybiera i uzupełnia (dialogi, ujęcia, napisy) i zapisuje, kto co zrobił. Dopiero wtedy lider może z czystym sumieniem złożyć oświadczenie z §3 ust. 9 |
| Ilustracje i animacje z generatorów (Azure AI Foundry, ewentualnie Kling, Runway, Veo) | **ZESPÓŁ** | Zgodnie z [projektem flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) przed prezentacją sprawdzamy warunki każdej usługi: czy zespół może korzystać z wyników i je publikować |
| Muzyka, piosenki, efekty dźwiękowe | **POPRAWIONE** / **ZESPÓŁ** | Scenariusz wymaga muzyki i melodii skomponowanych przez zespół. Bez znanych melodii, gotowych podkładów i efektów z sieci — nawet darmowe licencje nie dają *wyłącznych* praw. Muzyka generowana przez AI tylko po sprawdzeniu licencji |
| Głos syntezatora (Lila na żywo) | **ZESPÓŁ** | Sprawdzić warunki głosów Windows (Microsoft Paulina), syntezy mowy przeglądarki i Azure TTS dla publicznego pokazu i publikacji nagrań. Reakcje na wybory nagrywamy aktorsko (klipy `reaction`), syntezator tylko dla kwestii pisanych na żywo |
| Czcionki w napisach | **ZESPÓŁ** | Fonty z licencją pozwalającą na użycie w filmie (np. SIL Open Font License) |
| Oprogramowanie zewnętrzne | **OK** | Biblioteki i modele zostają na swoich licencjach (tabela niżej); żadna nie odbiera zespołowi praw do własnego kodu, scenariusza i filmu |
| Licencja repozytorium | **ZESPÓŁ** | Repozytorium nie ma pliku `LICENSE`. Zespół decyduje, na jakich zasadach udostępnia kod; bez pliku wszystkie prawa zostają przy autorach |

**Licencje komponentów** (sprawdzone w metadanych paczek):

| Komponent | Licencja | Rola |
|---|---|---|
| python-vlc / libVLC | LGPL-2.1+ | Odtwarzacz `--player vlc` (VLC instalowany osobno) |
| foundry-local-sdk, onnxruntime | MIT | Lokalne AI (Foundry Local, Windows ML) |
| onnxruntime-genai-core | MIT (repozytorium microsoft/onnxruntime-genai) | Silnik modeli Foundry Local |
| Phi-4-mini, Whisper | MIT (karty modeli) | Model językowy, rozpoznawanie mowy |
| winrt (pywinrt) | MIT | Syntezator mowy Windows |
| azure-cognitiveservices-speech | Licencja Microsoft (własnościowa) | Tylko tryb `azure` |
| openai | Apache-2.0 | Klient Azure OpenAI i serwera Foundry Local |
| PyYAML, sounddevice | MIT | Scenariusz, dźwięk |
| python-dotenv | BSD-3-Clause | Ustawienia |
| numpy | BSD-3-Clause (z komponentami MIT, Zlib, CC0) | Dźwięk |
| ffmpeg | LGPL/GPL (zależnie od kompilacji) | Narzędzie do zaślepek i wersji liniowej; nie jest częścią odcinka |

## Mikrofon w odtwarzaczu i drugi ekran — prywatność i bezpieczeństwo

Odpowiedź głosem nagrywa strona odtwarzacza w trakcie okna wyboru, a opcjonalnie telefon domownika
(drugi ekran, [README](../README.md#drugi-ekran-telefon-jako-pilot-z-mikrofonem)). Głos dziecka to dane osobowe,
a widzami są małe dzieci, dlatego:

| Kwestia | Rozwiązanie | Stan |
|---|---|---|
| Gdzie trafia nagranie | Odtwarzacz: tylko do aplikacji na tym samym komputerze (`127.0.0.1`). Telefon: do komputera z odcinkiem w sieci domowej, szyfrowane (HTTPS). Rozpoznawane lokalnie, na chwilę przez plik tymczasowy, usuwany zaraz po rozpoznaniu; bez chmury w trybie lokalnym | **OK** |
| Kiedy mikrofon nagrywa | Tylko w trakcie okna wyboru (na ekranie „Słucham…”), najwyżej kilka sekund; poza oknem nic nie jest wysyłane. Rodzic wyłącza mikrofon w ustawieniach (⚙) | **OK** |
| Informacja dla rodzica | Ekran startowy odtwarzacza, ekran dołączania telefonu i strona z kodem QR mówią, że nagranie służy tylko do rozpoznania odpowiedzi, trafia na chwilę do pliku tymczasowego, jest usuwane zaraz po rozpoznaniu i nie jest przechowywane | **OK** |
| Dzieci i rodzice | Zgodę na mikrofon daje rodzic w przeglądarce (ekran startowy, ustawienia). W produkcji: osobna zgoda rodzica w profilu dziecka i jasna informacja w opisie odcinka | **ZESPÓŁ** |
| Nadużycia | Limit rozmiaru nagrania, odpowiedzi tylko w otwartym oknie wyboru, odtwarzacz przyjmuje zapytania tylko z `localhost` i tylko typy danych wysyłane przez jego stronę; kwestie modelu filtrowane (`bajka/safety.py`) | **OK** |
| Odpowiedź bez mówienia | Pilot, dotyk, klawiatura — głos jest dodatkiem, nie warunkiem | **OK** |
| Tętno widza | W demo wyłącznie symulowane (`bajka/pulse.py`), bez danych prawdziwych osób. Prawdziwa wersja z zegarka to dane o zdrowiu (RODO art. 9): osobna, wyraźna zgoda rodzica, funkcja domyślnie wyłączona, przetwarzanie tylko na urządzeniu i w trakcie odcinka, bez zapisywania i bez wysyłania do serwisu | **OK** (demo) |

## Pitch wobec kryteriów jury (§4 ust. 5)

| Kryterium | Argument |
|---|---|
| **Innowacyjność** | Dziecko rozmawia z postacią bajki: w oknie wyboru może po prostu powiedzieć odpowiedź swoimi słowami, a postać reaguje. Rozpoznawanie mowy i zrozumienie odpowiedzi działają na urządzeniu (Copilot+ PC z NPU, Foundry Local), bez wysyłania głosu dziecka do chmury. Odcinek może też dopasowywać tempo do widza: przy pobudzeniu gra wersję spokojną sceny, przy znużeniu — żywą (w demo tętno jest symulowane, a panel pokazuje każdą decyzję) |
| **Adekwatność do zadania** | „Przyszłość odbioru dzieł audiowizualnych”: odbiór przenosi się do serwisów streamingowych, a widz przestaje być bierny. Uczymy się na błędach rynku: Netflix wycofał drogie filmy interaktywne, więc nasz format jest tani w produkcji (zagadki zbiegają się do tej samej sceny) i zawsze ma wersję liniową. W tradycji Kinoautomatu (Expo 67), gdzie widzowie głosowali przyciskami — u nas pilotem albo głosem |
| **Oryginalność** | Własny świat i postacie; interakcja projektowana dla dzieci 4–7 lat: obrazki zamiast tekstu, dłuższy czas na odpowiedź, brak kary za ciszę, odcinek z wyraźnym końcem |
| **Kreatywność** | Mechaniki w oknach wyboru: zagadki, wspólny oddech, liczenie; pomyłki stają się częścią nauki; cztery zakończenia zachęcają do obejrzenia jeszcze raz |

Technologia pasuje do partnerów hackathonu: nagrodą jest Copilot+ PC Lenovo, a odcinek z głosem działa lokalnie właśnie
na takim komputerze.

## Test z prawdziwą publicznością (§5 ust. 3)

Propozycja pierwszego testu po hackathonie:

1. 5–10 rodzin z dziećmi w wieku 4–7 lat, w domu albo w bibliotece, na laptopie lub tablecie; rodzic obok dziecka.
   Przed testem informacja dla rodziców: kiedy działa mikrofon i że nagrania są usuwane zaraz po rozpoznaniu.
2. Bez instruktażu: czy dziecko samo rozumie okno wyboru (pierwsza scena uczy zasad)?
3. Pomiary z logu aplikacji (bez nagrań): ile okien rozstrzygnięto pilotem, ile głosem (`Widz: wybór …, mowa …`),
   ile razy postać musiała dopytać albo wybrać sama, czasy odpowiedzi.
4. Krótka rozmowa z dzieckiem i rodzicem: czy chce obejrzeć jeszcze raz, co było trudne, czy mikrofon był w porządku.

## Lista kontrolna dla zespołu przed 18.10, 19:00

- [ ] Zgłoszenie przez formularz wysłane; nikt z zespołu nie podlega wykluczeniu z §3 ust. 7.
- [ ] Potwierdzenie z organizatorem, że odcinek do serwisów streamingowych mieści się w zadaniu (hasło „Kino szuka nowej formy”).
- [ ] Zespół przerobił scenariusz i zapisał autorstwo poszczególnych części.
- [ ] Wygląd postaci (zwłaszcza Bzyczki) zatwierdzony jako oryginalny.
- [ ] Muzyka i efekty własne; warunki generatorów obrazu i głosu sprawdzone.
- [ ] Napisy końcowe uzupełnione (nazwiska, informacja o AI).
- [ ] Decyzja o licencji repozytorium.
- [ ] Data prezentacji potwierdzona z organizatorem (literówka „18.10.2022” w §2 ust. 3).
- [ ] Na nagraniach z pokazu i testów nie ma dzieci bez zgody rodziców.
- [ ] Na pokazie: Edge albo Chrome, polski głos syntezatora, modele pobrane wcześniej, wersja liniowa wygenerowana.

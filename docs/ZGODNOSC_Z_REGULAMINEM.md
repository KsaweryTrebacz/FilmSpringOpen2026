# Zgodność z regulaminem hackathonu

Podstawa: Regulamin konkursu programistyczno-filmowego „KINO SZUKA NOWEJ FORMY. ZNAJDŹ JĄ. Hackathon o przyszłości
odbioru dzieł audiowizualnych” (Fundacja Film Spring Open, 21. Plenery Film Spring Open, Kraków, 16–18.10.2026).
Dotyczy filmu [„Bzyczka szuka domu”](../scenarios/klub_ciekawskich.md) i aplikacji `bajka`.

Oznaczenia: **OK** — spełnione · **POPRAWIONE** — naprawione w repozytorium · **ZESPÓŁ** — do zrobienia przez
zespół · **ZAPYTAĆ** — do wyjaśnienia z organizatorem.

## Przegląd

| Regulamin | Wymóg | Stan | Co zrobiliśmy / co zostaje |
|---|---|---|---|
| §2 ust. 2 | „Zarys filmów, aplikacji, gier… umożliwiających odbiór dzieł sztuki na nowej, interakcyjnej płaszczyźnie” | **OK** | Interaktywny film krótkometrażowy: widownia w kinie współdecyduje o przebiegu okrzykiem i odpowiedziami, a bohaterka reaguje na żywo. Do tego działający prototyp aplikacji |
| §2 ust. 3 i 5 | Prezentacja przed jury 18.10 o 19:00 | **POPRAWIONE** / **ZAPYTAĆ** | Scenariusz ma [plan na hackathon](../scenarios/klub_ciekawskich.md#plan-na-hackathon-prezentacja-18102026-1900) (zarys całego filmu + jedna scena w pełnej animacji). W §2 ust. 3 jest data „18.10.2022” — oczywista literówka, ale warto ją potwierdzić z organizatorem |
| §3 ust. 4, 6, 7 | Zgłoszenie przez formularz (nazwa zespołu, lider, e-mail); uczestnicy pełnoletni albo 13+ za zgodą opiekunów; wykluczenie pracowników organizatora i partnerów oraz ich rodzin | **ZESPÓŁ** | Sprawdzić, czy zgłoszenie jest wysłane i czy żaden członek zespołu nie podlega wykluczeniu |
| §3 ust. 8 | Bez treści obraźliwych, wulgarnych, propagujących przemoc, niemoralnych, nieprawdziwych lub wprowadzających w błąd | **POPRAWIONE** | Szczegóły niżej: filtr kwestii AI, zasady w prompcie, sprawdzone fakty, poprawione dwa fakty w scenariuszu, informacja o AI w napisach |
| §3 ust. 9 | Lider oświadcza, że zespołowi przysługują wyłączne prawa autorskie do pracy, która jest oryginalna i wolna od roszczeń osób trzecich | **POPRAWIONE** / **ZESPÓŁ** | Szczegóły niżej: oryginalne postacie, muzyka tylko własna, treści z AI jako szkic do opracowania przez zespół, licencje narzędzi |
| §3 ust. 10 | Praca może zostać opublikowana na stronie i w mediach społecznościowych organizatora | **ZESPÓŁ** | Wszystko, co pokażemy, musi nadawać się do publikacji: bez nagrań dzieci bez zgody opiekunów, bez cudzych utworów |
| §4 ust. 5 | Kryteria: innowacyjność, adekwatność do zadania, oryginalność, kreatywność | **OK** | Mapowanie na pitch niżej |
| §5 ust. 3 | Najlepszy projekt to pomysł wart dalszego rozwijania i testowania z prawdziwą publicznością | **OK** / **ZESPÓŁ** | Projekt jest od początku zbudowany do seansu z widownią; plan testu niżej |
| §6 | Ochrona danych (RODO) | **OK** / **ZESPÓŁ** | Aplikacja nie zapisuje głosu ani wypowiedzi; lokalne AI przetwarza mowę na komputerze, bez wysyłania nagrań do chmury. Wyjątek: w scenach rysowanych na żywo (`kind: open`) rozpoznany tekst odpowiedzi dziecka trafia do Azure OpenAI, a obraz rysuje Azure AI Foundry (nagranie głosu nigdy); informacja dla opiekunów powinna o tym wspomnieć. Głos dzieci z telefonów — szczegóły niżej |

## §3 ust. 8 — treści

Film słuchają małe dzieci, a część kwestii Lili pisze na żywo model językowy. Dlatego zabezpieczenia są w czterech
warstwach:

1. **Scenariusz** — wszystkie kwestie stałe są napisane i sprawdzone przez ludzi. Nie ma przemocy ani straszenia.
   Fakty edukacyjne są zebrane i sprawdzone w tabeli [„Sprawdzone fakty”](../scenarios/klub_ciekawskich.md#sprawdzone-fakty-regulamin-3-ust-8-bez-treści-nieprawdziwych).
2. **Prompt modelu** (`bajka/intent.py`, używany też lokalnie): mów tylko prawdę o świecie, nie zmyślaj faktów,
   nie powtarzaj brzydkich ani obraźliwych słów, nie mów o przemocy, poprawiaj pomyłki łagodnie. **POPRAWIONE**
3. **Filtr kwestii** (`bajka/safety.py`): kwestia z wulgaryzmem, słowami o przemocy, linkiem albo dłuższa niż ok.
   dwa zdania nie zostaje wypowiedziana — Lila mówi zamiast niej sprawdzoną kwestię ze scenariusza. **POPRAWIONE**
   W scenach decyzji z krzykomierzem model w ogóle nie pisze kwestii, a przy odpowiedziach z telefonów — tylko gdy
   odpowie jedna osoba; przy wielu Lila mówi teksty ze scenariusza.
4. **Ilustracje rysowane na żywo** (sceny `kind: open`, moduły Ksawerego): pomysł dziecka najpierw przepisuje
   model językowy na bezpieczny opis (`bajka/imagine.py`, te same zasady prawdy i kultury), podejrzana kwestia
   unieważnia cały pomysł (`SafeImaginer`), a model obrazu ma własny filtr treści (gpt-image; przy FLUX —
   Azure AI Content Safety). Przy każdym błędzie albo odrzuceniu pokazujemy przygotowany klip zapasowy.
   Ilustracje poprzednich seansów aplikacja usuwa przy starcie. **OK** w kodzie; **ZESPÓŁ**: filtr treści przy FLUX.

**Poprawione fakty w scenariuszu:**
- Sowa w dzień: sowy są aktywne głównie nocą, więc Lila mówi teraz „Sowy w dzień zwykle śpią, a my ją chyba budzimy!”.
- Ul: wcześniej „na wysokim drzewie”, co bardziej pasuje do dzikiego gniazda. Teraz ul stoi na końcu łąki pod lipą.

**Bez wprowadzania w błąd:** napisy końcowe informują, że reakcje Lili tworzy na żywo sztuczna inteligencja i że
głosów widowni nie zapisujemy. **POPRAWIONE**

## §3 ust. 9 — prawa autorskie

| Element | Stan | Uwagi |
|---|---|---|
| Postacie, imiona, świat, fabuła | **OK** | Oryginalne. Scenariusz zastrzega, że projektując postacie nie wzorujemy się na postaciach z innych filmów i seriali. W szczególności Bzyczka ma własny wygląd (miętowy sweterek w miodowe paski) i nie może przypominać znanych pszczółek z animacji. W materiałach i pitchu nie odwołujemy się do cudzych marek |
| Tekst scenariusza powstał z pomocą AI | **ZESPÓŁ** | Prawo autorskie chroni twórczość człowieka. Traktujcie tekst jako szkic: zespół go przerabia, wybiera i uzupełnia (dialogi, ujęcia, napisy) i zapisuje, kto co zrobił. Dopiero wtedy lider może z czystym sumieniem złożyć oświadczenie z §3 ust. 9 |
| Ilustracje i animacje z generatorów (Azure AI Foundry, ewentualnie Kling, Runway, Veo) | **ZESPÓŁ** | Zgodnie z [projektem flow filmu](superpowers/specs/2026-10-16-flow-filmu-design.md) przed prezentacją sprawdzamy warunki każdej usługi: czy zespół może korzystać z wyników i je publikować |
| Muzyka, piosenki, efekty dźwiękowe | **POPRAWIONE** / **ZESPÓŁ** | Scenariusz wymaga muzyki i melodii skomponowanych przez zespół. Bez znanych melodii, gotowych podkładów i efektów z sieci — nawet darmowe licencje nie dają *wyłącznych* praw. Muzyka generowana przez AI tylko po sprawdzeniu licencji |
| Głos syntezatora (Lila na żywo) | **ZESPÓŁ** | Sprawdzić warunki głosów Windows (Microsoft Paulina) i Azure TTS dla publicznego pokazu i publikacji nagrań. Alternatywa: głos aktorski w klipach, syntezator tylko na żywo |
| Czcionki w napisach | **ZESPÓŁ** | Fonty z licencją pozwalającą na użycie w filmie (np. SIL Open Font License) |
| Oprogramowanie zewnętrzne | **OK** | Biblioteki i modele zostają na swoich licencjach (tabela niżej); żadna nie odbiera zespołowi praw do własnego kodu, scenariusza i filmu |
| Licencja repozytorium | **ZESPÓŁ** | Repozytorium nie ma pliku `LICENSE`. Zespół decyduje, na jakich zasadach udostępnia kod; bez pliku wszystkie prawa zostają przy autorach |

**Licencje komponentów** (sprawdzone w metadanych paczek):

| Komponent | Licencja | Rola |
|---|---|---|
| python-vlc / libVLC | LGPL-2.1+ | Odtwarzacz (VLC instalowany osobno) |
| foundry-local-sdk, onnxruntime | MIT | Lokalne AI (Foundry Local, Windows ML) |
| onnxruntime-genai-core | MIT (repozytorium microsoft/onnxruntime-genai) | Silnik modeli Foundry Local |
| Phi-4-mini, Whisper | MIT (karty modeli) | Model językowy, rozpoznawanie mowy |
| winrt (pywinrt) | MIT | Syntezator mowy Windows |
| azure-cognitiveservices-speech | Licencja Microsoft (własnościowa) | Tylko tryb `azure` |
| openai | Apache-2.0 | Klient Azure OpenAI i serwera Foundry Local |
| PyYAML, sounddevice | MIT | Scenariusz, dźwięk |
| python-dotenv | BSD-3-Clause | Ustawienia |
| numpy | BSD-3-Clause (z komponentami MIT, Zlib, CC0) | Dźwięk |
| ffmpeg | LGPL/GPL (zależnie od kompilacji) | Narzędzie do zaślepek i ruchu kamery; nie jest częścią filmu |

## Aplikacja mobilna widowni — prywatność i bezpieczeństwo

Odpowiedzi publiczności zbiera aplikacja na telefony z dostępem do mikrofonu ([README](../README.md#aplikacja-mobilna-widowni)).
Głos dziecka to dane osobowe, a widzami są małe dzieci, dlatego:

| Kwestia | Rozwiązanie | Stan |
|---|---|---|
| Gdzie trafia nagranie | Tylko do komputera z filmem w sieci lokalnej, szyfrowane (HTTPS); rozpoznawane w pamięci i od razu usuwane; bez chmury w trybie lokalnym | **OK** |
| Kiedy telefon nagrywa | Tylko w trakcie rundy pytania (pulsuje lupka), najwyżej kilka sekund; poza rundami nic nie jest wysyłane | **OK** |
| Informacja dla widza | Przed dołączeniem aplikacja mówi, że nagranie służy tylko do rozpoznania odpowiedzi i nie jest zapisywane | **OK** |
| Dzieci i opiekunowie | Telefon należy zwykle do opiekuna, który dołącza i zezwala na mikrofon; przed seansem krótka informacja dla opiekunów (plansza przy wejściu albo słowo prowadzącego) | **ZESPÓŁ** |
| Nadużycia | Jedna odpowiedź na telefon w rundzie, limit rozmiaru nagrania, odpowiedzi tylko w otwartej rundzie; kwestie modelu filtrowane (`bajka/safety.py`) | **OK** |
| Odpowiedź bez mówienia | Dziecko, które nie chce albo nie może mówić, dotyka opcji | **OK** |
| Pomysł na przyszłość: tętno z zegarka | Dane o zdrowiu (RODO art. 9) — tylko za wyraźną zgodą opiekunów, dobrowolnie, uśrednione i bez zapisywania; na razie wyłącznie pomysł w README | — |

## Pitch wobec kryteriów jury (§4 ust. 5)

| Kryterium | Argument |
|---|---|
| **Innowacyjność** | Bohaterka filmu słucha widowni i odpowiada na żywo: każdy widz mówi do własnego telefonu, a komputer w kinie liczy głosy całej sali. Rozpoznawanie mowy, wybór ścieżki i głos działają lokalnie (Copilot+ PC z NPU, Foundry Local), bez nagrywania dzieci; w chmurze Azure powstają tylko ilustracje scen rysowanych na żywo, z samego tekstu, bez nagrania. Bez telefonów decyzje rozstrzyga krzykomierz |
| **Adekwatność do zadania** | „Przyszłość odbioru dzieł audiowizualnych”: widz przestaje być bierny — współdecyduje o filmie. Nawiązujemy do tradycji: w czechosłowackim Kinoautomacie (Expo 67) widzowie głosowali przyciskami; u nas głosują głosem, a postać reaguje na nich |
| **Oryginalność** | Własny świat i postacie, film dla najmłodszych z pierwszym w życiu doświadczeniem kina jako wspólnej zabawy |
| **Kreatywność** | Mechaniki zaprojektowane pod salę kinową: okrzyki, odpowiedzi chórem, wspólny oddech, liczenie; pomyłki widowni stają się częścią nauki |

Technologia pasuje do partnerów hackathonu: nagrodą jest Copilot+ PC Lenovo, a film działa lokalnie właśnie na takim
komputerze.

## Test z prawdziwą publicznością (§5 ust. 3)

Propozycja pierwszego seansu próbnego po hackathonie:

1. Grupa przedszkolna (10–25 dzieci) z opiekunami, sala z ekranem. Przed seansem informacja dla opiekunów:
   mikrofon słucha, nic nie jest nagrywane.
2. Kalibracja krzykomierza na pełnej sali: `python -m bajka.vote`.
3. Pomiary z logu aplikacji (bez nagrań): ile rund okrzyków rozstrzygnięto za pierwszym razem (`Okrzyki: …`),
   jak często odpowiedź chórem została rozpoznana (`Intencja: …`), ile razy Lila musiała wybrać sama, czasy odpowiedzi.
4. Obserwacja zaangażowania: czy dzieci krzyczą, oddychają i liczą razem z postaciami; krótka rozmowa z opiekunami.

## Lista kontrolna dla zespołu przed 18.10, 19:00

- [ ] Zgłoszenie przez formularz wysłane; nikt z zespołu nie podlega wykluczeniu z §3 ust. 7.
- [ ] Zespół przerobił scenariusz i zapisał autorstwo poszczególnych części.
- [ ] Wygląd postaci (zwłaszcza Bzyczki) zatwierdzony jako oryginalny.
- [ ] Muzyka i efekty własne; warunki generatorów obrazu i głosu sprawdzone.
- [ ] Napisy końcowe uzupełnione (nazwiska, informacja o AI).
- [ ] Decyzja o licencji repozytorium.
- [ ] Data prezentacji potwierdzona z organizatorem (literówka „18.10.2022” w §2 ust. 3).
- [ ] Na nagraniach z pokazu nie ma dzieci bez zgody opiekunów.
- [x] Ilustracje z poprzednich seansów usuwane przy starcie aplikacji (zadanie 6 planu „obraz na żywo”).
- [ ] Na pokazie: Wi-Fi dla telefonów (bez izolacji klientów), port aplikacji otwarty w zaporze, plansza z kodem QR,
      informacja dla opiekunów o mikrofonie.

# Klub Ciekawskich — bajka, która słucha

**Zgłoszenie na hackathon FilmSpring Open 2026 „Kino szuka nowej formy”** · 18.10.2026

**Zespół:** [imiona i role — do uzupełnienia] · **Lider:** [imię i nazwisko] · **Kontakt:** [e-mail]

| Do obejrzenia (bez instalowania czegokolwiek) | |
|---|---|
| Cały odcinek w prawdziwym odtwarzaczu, ok. 3 min, z dźwiękiem i napisami | [media/odcinek_przejscie.mp4](media/odcinek_przejscie.mp4) |
| Zwiastun z klipów odcinka, 32 s | [media/zwiastun.mp4](media/zwiastun.mp4) |
| Tętno a montaż: odtwarzacz i panel obok siebie, 47 s | [media/tetno_montaz.mp4](media/tetno_montaz.mp4) |
| Mapa odcinka: etapy, odpowiedzi i gałęzie | [media/mapa_odcinka.jpg](media/mapa_odcinka.jpg) |
| Slajdy (25) z notatkami | eksport PDF w załączniku · [link do slajdów](https://claude.ai/artifact/LhY5PzguvLUpW7VHhCCYtg) |
| Kod, scenariusz i cała dokumentacja | [github.com/KsaweryTrebacz/FilmSpringOpen2026](https://github.com/KsaweryTrebacz/FilmSpringOpen2026) |

> **English summary.** *Klub Ciekawskich* (The Curious Club) is an interactive animated series for children aged 4–7 designed for streaming platforms. At key story points, characters ask questions and a choice menu appears. The child can respond using a remote control, touchscreen, or voice in natural Polish. Each choice leads to an appropriate reaction or branch, with transitions (dissolves, wipes, cuts) selected based on narrative context and viewer engagement. A parent panel allows adjusting educational topics, puzzle difficulty, and screen time limits. Speech recognition and language processing run locally on device, keeping children's audio private. The playable prototype, episode scenario, and documentation were created during the FilmSpring Open 2026 hackathon.

![Okno wyboru w odtwarzaczu na klipie z odcinka](media/okno-glos.jpg)

## 1. Opis projektu

Animowany serial dla dzieci 4–7 lat do serwisów streamingowych, w którym **dziecko rozmawia z bohaterami**.
Odcinek pilotażowy: „Bzyczka szuka domu” — Lila Lupka i wiewiórek Fiku pomagają zagubionej pszczółce wrócić do ula.

1. Postać zadaje pytanie, klip przechodzi w cichą pętlę, a na dole ekranu pojawia się **okno wyboru**: 2–3 opcje
   z obrazkami, nazwami i paskiem odliczania.
2. Dziecko wybiera **pilotem, dotykiem albo głosem**. Głos rozpoznaje model Whisper, a sens odpowiedzi — mały model
   językowy Phi; oba działają na komputerze widza. Gdy model zawiedzie, wybór rozpoznają słowa kluczowe.
3. **Każda odpowiedź ma skutek**: nagrana reakcja postaci i często osobna scena. Zła deska w mostku nie kończy gry —
   mostek się chwieje i naprawiamy go razem. Wybory „kosmetyczne” (kwiatek dla mamy Bzyczki) mogą być przezroczystymi
   **warstwami** nakładanymi na jeden klip zamiast osobnych wersji scen — silnik i odtwarzacz je obsługują, a w odcinku
   wrócą z kwiatkiem wyciętym z ilustracji.
4. **Montażysta AI** wybiera przejście między klipami (przenikanie, przetarcie, zaciemnienie, rozjaśnienie, cięcie)
   i jego długość — według miejsca akcji, wyboru i słów dziecka oraz jego tętna (dziś z symulatora). Gdy nie zdąży,
   decydują reguły; odcinek nigdy nie staje.
5. Cisza nie karze: postać dopytuje, a potem wybiera sama. Na końcu ekran „Twoje wybory” i „Obejrzyj jeszcze raz”.
6. Telewizor bez mikrofonu? **Telefon** staje się pilotem z mikrofonem: wystarczy zeskanować kod QR.
7. Każdy odcinek ma też **wersję liniową** (zwykły film z napisami) i **manifest** dla odtwarzacza serwisu.
   Twórcy widzą w **panelu podglądu** drogę widza, tętno i uzasadnienie każdej decyzji montażysty.

**Kreator Rodzica** (koncepcja i makieta): rodzic wybiera, czego dziecko ma się dziś uczyć (liczenie, wzory, emocje,
przyroda), ile ma być zagadek, ile czasu dziecko ma na odpowiedź i czy odpowiada głosem, oraz ustawia limit ekranu.
Po odcinku dostaje krótki raport z pomysłami na rozmowę bez ekranu ([KREATOR_RODZICA.md](KREATOR_RODZICA.md)).

![Kreator Rodzica — makieta](media/kreator.png)

**Język filmowy.** Odcinek ma scenopis z przebiegiem barwnym (ciepły bursztyn dziupli, turkus strumyka, złota godzina
na łące, szafirowy zmierzch finału) i biblię wizualną postaci dla generatora wideo
([SCENARIUSZ_WIZUALNY_PROMPTY_AI.md](../SCENARIUSZ_WIZUALNY_PROMPTY_AI.md)). Montażysta stosuje zasady
montażowe: to samo miejsce — łagodne przenikanie, nowe miejsce — przetarcie, zakończenie — zaciemnienie albo
przejście wskazane przez autora (finał Bzyczki: rozjaśnienie). Gdy dziecko jest pobudzone, montaż zwalnia (dłuższe
przenikanie), gdy się nudzi — przyspiesza (krótkie przetarcie). Rozjaśnienie trwa co najmniej 0,8 s, żeby nie
powstawały błyski.

## 2. Problem i cel projektu

- **Tradycyjna bajka nie słucha dziecka:** W klasycznej formule pytanie z ekranu to tylko kilkusekundowa pauza, po której postać i tak mówi swoje bez względu na reakcję widza.
- **Brak wpływu rodzica na przebieg seansu:** Rodzic może wybrać tytuł bajki, ale nie ma wpływu na liczbę zadań, czas trwania czy poziom trudności.
- **Rekomendacje dotyczące czasu przed ekranem (WHO, AAP):** Dla dzieci w wieku 2–4 lat zaleca się do godziny dziennie wartościowych treści, najlepiej oglądanych z opiekunem. Brakuje narzędzi ułatwiających takie podejście.
- **Dotychczasowe kino interaktywne:** Netflix wycofał większość swoich produkcji interaktywnych w 2024 roku, ponieważ były kosztowne w produkcji, kierowane do dorosłych i oparte wyłącznie na pilotach. Format dla dzieci z obsługą głosu i tańszą modułową produkcją wypełnia tę lukę.

## 3. Odbiorcy i korzyści

| Odbiorca | Korzyść |
|---|---|
| **Dzieci w wieku 4–7 lat** | Aktywne uczestnictwo w historii, dialog z bohaterami, zadania z natychmiastową informacją zwrotną. |
| **Dzieci nieczytające lub z trudnościami mowy** | Symbole graficzne, obsługa pilotem i dotykiem bez konieczności mówienia, wydłużony czas odpowiedzi. |
| **Rodzice** | Kontrola nad czasem i treścią (Kreator rodzica), podsumowanie po seansie i tematy do rozmów z dzieckiem. |
| **Rodzeństwo i grupy** | Możliwość wspólnego oglądania i podejmowania decyzji przez telefony w trybie drugiego ekranu. |
| **Przedszkola i placówki edukacyjne** | Możliwość dopasowania tematyki odcinka do programu zajęć. |
| **Platformy VOD i nadawcy** | Lekki format gotowy do integracji (manifest JSON lub odtwarzacz webowy), brak konieczności utrzymywania kosztownej infrastruktury chmurowej AI. |

## 4. Główne wyzwania i rozwiązania techniczne

| Wyzwanie | Rozwiązanie |
|---|---|
| **Koszty produkcji rozgałęzień** | Krótkie gałęzie (15–25 s) powracające do osi głównej. Wybory rekwizytów realizowane za pomocą przezroczystych nakładek WebM, bez renderowania osobnych wariantów całych scen. |
| **Rozpoznawanie mowy dziecka** | Wielotorowe wejście: pilot, dotyk lub głos. Model Whisper z podpowiedzią słownika scenariusza, mały model językowy Phi do interpretacji intencji oraz fallback na reguły słów kluczowych. |
| **Prywatność i ochrona danych** | Przetwarzanie lokalne na urządzeniu, bez wysyłania dźwięku do chmury. Mikrofon aktywny tylko w trakcie okna wyboru, bufor audio kasowany z pamięci RAM zaraz po transkrypcji. |
| **Bezpieczeństwo treści** | Modele nie generują obrazu ani fabuły na żywo. Wszystkie klipy wideo są renderowane i sprawdzane przed emisją, a teksty przechodzą przez filtr bezpieczeństwa. |
| **Spójność wizualna materiałów** | Stała stylistyka promptów, wspólna paleta barwna (bursztyn, turkus, złoto, szafir) i generowanie ujęć z klatek referencyjnych. |
| **Płynność montażu** | Pętle oczekiwania z przygotowanym crossfade na szwie zapętlenia. Montażysta dobiera rodzaj cięcia zależnie od zmiany miejsca i tętna widza. |
| **Różnorodność urządzeń odtwarzających** | Gotowy odtwarzacz webowy, możliwość wygenerowania pliku liniowego MP4 lub manifestu JSON dla istniejących odtwarzaczy VOD. |

## 5. Wyniki testów i weryfikacja

### Badania zewnętrzne
- **Wpływ dialogu z postacią na przyswajanie wiedzy:** Badanie zespołu dr Ying Xu (CHI 2022) na serialu PBS KIDS *Elinor Wonders Why* wykazało wyższy poziom zapamiętywania treści u dzieci w wersji interaktywnej (63% poprawnych odpowiedzi w teście) w porównaniu z wersją pasywną (56%).
- **Reakcja społeczna w mediach dziecięcych:** Badania Troseth, Saylor i Archer (*Child Development* 2006) potwierdzają, że dzieci w wieku przedszkolnym znacznie lepiej uczą się z ekranu, gdy postać reaguje na ich komunikaty.

### Testy prototypu z 17–18.10.2026
| Test | Wynik |
|---|---|
| **Odtwarzanie pełnego odcinka w przeglądarce** | Prawidłowe przejście ścieżki od sceny startowej do finału (8 okien wyboru, 10 cięć montażowych, brak błędów w konsoli przeglądarki). |
| **Adaptacja montażu do tętna** | Symulacja niskiego tętna skutkuje dynamicznym cięciem (0,4 s wipe, tempo 1.08x), symulacja wysokiego tętna wydłuża przenikanie (1,2 s, tempo 0.92x). |
| **Rozpoznawanie wypowiedzi bez modelu (słowa kluczowe)** | Zestaw 100 prób tekstowych: 79 z 81 jasnych deklaracji rozpoznanych poprawnie, 0 błędnych wyborów, w 19 przypadkach niejednoznacznych wywołano dopytanie. |
| **Testy automatyczne (pytest)** | 444 testy jednostkowe i integracyjne silnika, montażu, scenariusza i serwerów HTTP przechodzą poprawnie. |
| **Struktura grafu scenariusza** | 17 scen, 8 decyzji na ścieżce, 32 układy narracyjne, 576 możliwych kombinacji wyborów. Silnik waliduje spójność każdego węzła. |
| **Materiały wideo** | 31 klipów wideo przygotowanych i zoptymalizowanych do płynnego odtwarzania. |

### Kwestie do weryfikacji w kolejnym etapie
- Testy z udziałem rodzin i dzieci w wieku 4–7 lat (obserwacja naturalnych reakcji, preferencji wyboru pilot vs głos).
- Testy wydajnościowe modelu Whisper i Phi na różnych konfiguracjach sprzętowych (NPU DirectML vs CPU).

## 6. Prace zrealizowane podczas hackathonu

Projekt powstał w całości w dniach 16–18 października 2026 r.:
- **Koncepcja i scenariusz:** Opracowanie świata Klubu Ciekawskich, postaci Lili i Fiku, grafu scenariusza i zagadek edukacyjnych.
- **Implementacja silnika:** Architektura portów i adapterów w Pythonie (`bajka/engine.py`), obsługa stanów, timeoutów i warstw przezroczystych.
- **Odtwarzacz webowy:** Dwudeckowy odtwarzacz wideo w JavaScript (`bajka/player_app/`), płynne przejścia CSS, obsługa Web Audio i Web Speech API.
- **System montażu:** Moduł doboru cięć na bazie kontekstu i tętna widza z deterministycznym fallbackiem regułowym (`bajka/montage.py`).
- **Narzędzia wspomagające:** Panel realizatora z podglądem telemetrii (`bajka/panel.py`), obsługa drugiego ekranu na smartfonach (`bajka/mobile.py`) oraz eksporter do wideo liniowego (`bajka/linear.py`).

**Komponenty zewnętrzne:** Do uruchamiania modeli lokalnych wykorzystano środowisko Foundry Local SDK, modele Whisper i Phi oraz narzędzie FFmpeg do obróbki wideo. Badania z sekcji 5 to prace innych zespołów.

## 7. Dalsze plany

| Kiedy | Co |
|---|---|
| do 25.10 (aktualizacja zgłoszenia) | Test z kilkoma rodzinami, 2 brakujące klipy i warstwy kwiatków, uzupełnione badania zespołu |
| 29.10 | Pokaz na żywo na sesji online: widzowie transmisji wybierają drogę na czacie |
| 1–3 miesiące | Pilotaż z 5–10 rodzinami, pełny odcinek z nagranymi głosami postaci, Kreator v0 |
| 3–6 miesięcy | Biblioteka modułów z oznaczonymi umiejętnościami, planista Kreatora, raport dla rodzica, trzy odcinki |
| 6–12 miesięcy | Pierwszy partner (serwis albo platforma edukacyjna); tętno w becie, tylko za zgodą rodzica |

Model biznesowy (hipotezy do sprawdzenia): subskrypcja dla rodzin, licencja dla serwisów i placówek edukacyjnych, licencja narzędzi dla studiów. Ceny ustalimy po pilotażu ([ONE_PAGER.md](ONE_PAGER.md)).

## Załączniki i dalsza lektura

[ONE_PAGER.md](ONE_PAGER.md) (jedna strona) · [PITCH.md](PITCH.md) (scenariusz wystąpienia) ·
[KREATOR_RODZICA.md](KREATOR_RODZICA.md) · [BADANIA.md](BADANIA.md) · [scenariusz odcinka](../../scenarios/klub_ciekawskich.md) ·
[realia rynku](../STREAMING.md) · [zgodność z regulaminem](../ZGODNOSC_Z_REGULAMINEM.md) ·
[uruchomienie prototypu](../URUCHOMIENIE.md) (Windows, Python, ffmpeg — nie jest potrzebne do oceny)

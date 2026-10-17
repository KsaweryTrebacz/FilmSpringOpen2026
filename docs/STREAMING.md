# Bajka interaktywna w serwisie streamingowym

Ten dokument tłumaczy, dlaczego projekt zmienił sposób odbioru z seansu w kinie na odcinek interaktywny
w serwisie streamingowym, jak wygląda rynek, jak odcinek trafia do serwisów i co proponujemy dalej.

## Co się zmieniło (17.10.2026)

| Było (seans w kinie) | Jest (odcinek w domu) |
|---|---|
| Sala dzieci odpowiada chórem albo okrzykiem; krzykomierz mierzy głośność | Jedno dziecko (czasem z rodzeństwem) wybiera w **oknie wyboru** pilotem, dotykiem albo głosem |
| Telefony widzów jako jedyny sposób zbierania głosów | Telefon to opcjonalny **drugi ekran** (pilot z mikrofonem dla telewizora bez mikrofonu) |
| Lila mówi do widowni w liczbie mnogiej | Postacie mówią do widza w liczbie pojedynczej, bez form zależnych od płci |
| Kwestie po wyborze zawsze z syntezatora | Najpierw **nagrane klipy reakcji**; syntezator tylko dla kwestii pisanych na żywo, zawsze z napisami |
| VLC na pełnym ekranie, mikrofon komputera | **Odtwarzacz w przeglądarce**, jak w serwisie: okno wyboru, odliczanie, napisy, ustawienia rodzica, „obejrzyj jeszcze raz” |
| Tętno całej sali | Tętno jednego widza z zegarka (dziś symulator) — wersja spokojna albo żywa sceny |
| Jeden plik do pokazu | Trzy drogi do serwisów: wersja interaktywna, **manifest JSON**, **wersja liniowa** |

## Realia rynku: dlaczego „urealnić”

Interaktywne filmy w serwisach to dziś nisza, a największy gracz się z nich wycofał:

- **Netflix wycofał prawie wszystkie „Interactive Specials”.** Pod koniec 2024 r. serwis zapowiedział usunięcie
  20 z 24 tytułów do 1 grudnia 2024 r., tłumacząc, że format „spełnił swoje zadanie, ale teraz ogranicza” rozwój
  technologii w innych obszarach ([VGC](https://videogameschronicle.com/news/netflix-is-removing-almost-all-of-its-interactive-specials-this-month)).
  Ostatnie dwa — *Black Mirror: Bandersnatch* i *Kimmy vs the Reverend* — zniknęły 12 maja 2025 r.
  ([VGC](https://www.videogameschronicle.com/news/netflix-is-removing-bandersnatch-its-interactive-video-game-episode-of-black-mirror),
  [Dark Horizons](https://www.darkhorizons.com/?p=184199),
  [Derbyshire Times](https://www.derbyshiretimes.co.uk/whats-on/black-mirror-bandersnatch-pulled-from-netflix-5123500));
  według doniesień interaktywności zabrakło w nowym interfejsie serwisu.
- **Tytuły przygodowe wróciły jako zwykłe filmy.** Programy z Bearem Gryllsem — najbliższe treściom dla dzieci —
  Netflix przywrócił w wersjach bez interakcji, z jedną fabułą (źródła jak wyżej).
- **Platformy do wideo z rozgałęzieniami istnieją, ale to nisza:** np. Adventr — klipy dla każdej gałęzi połączone
  punktami decyzji, a logiką zajmuje się odtwarzacz ([przegląd](https://creatoreconomytools.com/tool/adventr)).
- **Wyzwania techniczne są znane:** zgłoszenia patentowe opisują m.in. segment prowadzący do punktu wyboru, segment
  z opcjami i problem buforowania wszystkich gałęzi naraz ([przykład](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10771865)).
- **Badania nad dostępnością** pokazują sens wyboru głosem i dźwiękiem: w pracy z lipca 2025 r. rozgałęzione wideo 360°
  z prowadzeniem audio (Branch Explorer) zwiększyło poczucie sprawczości i zaangażowanie niewidomych i słabowidzących widzów
  (badanie na 12 osobach, [arXiv:2507.09959](https://arxiv.org/abs/2507.09959v1)).

**Wnioski dla projektu:**
1. Nie zakładamy, że duży serwis od razu przyjmie format interaktywny. Każdy odcinek ma **wersję liniową**
   z tych samych klipów (`python -m bajka.linear`) — tak jak Netflix zrobił z programami Bear Gryllsa.
2. Interaktywność musi być **tania w produkcji**: zagadki zbiegają się do tej samej sceny, a różni je tylko krótka
   reakcja. 10 scen + kilka reakcji zamiast drzewa kilkudziesięciu klipów.
3. Wartość, której linearny film nie da: dziecko **mówi do postaci swoimi słowami**, a postać odpowiada —
   z rozpoznawaniem mowy na urządzeniu, bez wysyłania głosu dziecka do chmury.
4. Najbardziej realne pierwsze kanały: aplikacja na tablet/PC (np. edukacyjna albo biblioteczna), serwisy dla dzieci
   z własnym odtwarzaczem (manifest JSON), a dopiero potem duże platformy.

## Trzy drogi do widza

| Droga | Co dostaje serwis | Interakcja | Głos | Tętno |
|---|---|---|---|---|
| **1. Nasz odtwarzacz** (`python -m bajka`) | Aplikację: strona + silnik + modele lokalne | Pełna: okna wyboru, reakcje, dopytywanie | Tak, na urządzeniu | Tak (dziś symulator) |
| **2. Manifest** (`python -m bajka.manifest`) | Klipy + `odcinek.json`: sceny, okna wyboru, obrazki, reakcje, wersje scen, opisy i słowa kluczowe do rozpoznawania głosu, `linear_path` | Odtwarzacz serwisu | Jeśli serwis doda rozpoznawanie (np. słowa kluczowe z manifestu) | Jeśli serwis zechce |
| **3. Wersja liniowa** (`python -m bajka.linear`) | Jeden plik MP4 + napisy `.srt` | Brak: postać pyta, czeka chwilę i wybiera sama | — | — |

Format plików: MP4 (H.264/AAC) z indeksem na początku pliku. W produkcji serwisy pakują klipy do HLS/DASH;
manifest wskazuje klipy po ścieżkach, więc wystarczy zamienić je na adresy segmentów.

## Okno wyboru: zasady projektowe

- **2–3 opcje**, każda z dużym obrazkiem i krótką nazwą (do 24 znaków). Dzieci 4–7 lat często jeszcze nie czytają.
- **Pytanie zawsze słychać i widać** (klip + napisy). Opcje można przeczytać na głos przy fokusie (audiodeskrypcja).
- **Czas: 12 s** domyślnie, dłużej przy ćwiczeniach: oddech 20 s, liczenie 15 s.
  Rodzic może wydłużyć czas (`BAJKA_CHOICE_SECONDS`).
- **Bez kary za ciszę**: dopytanie, potem postać wybiera sama i mówi to wprost („To ja wybiorę”).
- **Pilot przede wszystkim**: strzałki + OK działają na każdym telewizorze; głos jest dodatkiem, nie warunkiem.
- **Mikrofon tylko w oknie wyboru**, z widocznym wskaźnikiem „Słucham…” i informacją, co usłyszał („Słyszę: …”).

## Głos na urządzeniu

- Rozpoznawanie mowy: Whisper przez Foundry Local (NPU/GPU/CPU), zrozumienie intencji: Phi albo słowa kluczowe.
  Nagranie trafia tylko do urządzenia, na którym działa bajka, do pliku tymczasowego usuwanego zaraz po rozpoznaniu.
- Głos postaci w kwestiach na żywo: synteza mowy przeglądarki (na Windows lokalne głosy systemu, np. Paulina),
  zawsze z napisami. W produkcji większość kwestii to nagrania aktorskie (klipy reakcji).
- W przeglądarce mikrofon działa bez certyfikatu tylko pod `localhost`/`127.0.0.1`. Na telewizorze bez mikrofonu
  pomaga drugi ekran (telefon przez HTTPS w domowej sieci).

## Tętno i uwaga widza (przyszłość)

Pomysł: zegarek dziecka mierzy tętno, a odcinek wybiera wersję sceny — spokojną przy dużym pobudzeniu, żywą przy
znużeniu (`mood: zrownowazony`). Dziś działa symulator sterowany z panelu podglądu.

| Zasada | Dlaczego |
|---|---|
| Wyraźna, osobna zgoda rodzica; funkcja domyślnie wyłączona | Dane o zdrowiu to szczególna kategoria danych (RODO, art. 9); widz to dziecko |
| Przetwarzanie tylko na urządzeniu i tylko w trakcie odcinka | Serwis nie potrzebuje tętna — potrzebuje tylko decyzji „wersja spokojna/żywa” |
| Żadnego zapisu, profilowania ani wysyłania do serwisu | Minimalizacja danych; brak pokusy reklamowej |
| Tętno zmienia tylko tempo i montaż sceny, nigdy treść ani długość oglądania | Chronimy dziecko przed mechanizmami „przytrzymywania” przy ekranie |
| Odczyt: Health Connect (Android), HealthKit (iOS), Bluetooth „Heart Rate” | Standardowe, systemowe ścieżki z kontrolą uprawnień |

**Sygnały uwagi bez biometrii** (proponujemy jako pierwsze, bo nie wymagają zegarka ani danych o zdrowiu):
czas reakcji w oknie wyboru, liczba okien zakończonych ciszą z rzędu, pauzy i przewijanie. Seria cisz może
uruchamiać żywą wersję kolejnej sceny albo krótsze pytania — wszystko lokalnie i bez zapisu.

## Propozycje usprawnień

Uporządkowane od najtańszych. Odhaczone są już w repozytorium.

- [x] Okno wyboru z obrazkami, odliczaniem, pilotem, dotykiem i głosem (`bajka/web_player.py`).
- [x] Nagrane klipy reakcji zamiast syntezatora (`reaction`), napisy dla kwestii na żywo.
- [x] Wersja liniowa i manifest JSON dla serwisów.
- [x] Ekran końcowy z wyborami widza i „obejrzyj jeszcze raz” (cztery zakończenia), bez automatycznego kolejnego odcinka.
- [ ] **Sygnały uwagi bez biometrii** (czas reakcji, serie cisz) jako wejście dla wersji scen — przed zegarkiem.
- [ ] **Profil dziecka bez danych osobowych**: tylko ustawienia (czas okna, mikrofon, napisy) zapisane na urządzeniu.
- [ ] **Napisy WebVTT do klipów** (plik `.vtt` obok klipu) i audiodeskrypcja opcji przy fokusie.
- [ ] **Pamięć wyborów między odcinkami** (np. który pomocnik był ulubiony) — lokalnie, z wyłączeniem przez rodzica.
- [ ] **Raport dla rodzica po odcinku**: czego dotyczyły zagadki i jak poszło (bez nagrań, bez wysyłania).
- [ ] **Pakowanie HLS/DASH** i podgląd kolejnej gałęzi (wczytanie tylko klipów możliwych po bieżącym oknie wyboru).
- [ ] **Aplikacja na telewizor** (Tizen/webOS/Android TV) z tym samym `player_app` — strona już obsługuje strzałki i OK.
- [ ] **Sprawdzenie patentów** na odtwarzanie rozgałęzionych treści przed komercjalizacją (zob. zgłoszenia wyżej).
- [ ] **Test z rodzinami**: 5–10 dzieci w wieku 4–7 lat, w domu, z rodzicem; mierzymy, czy dzieci rozumieją okno
  wyboru bez pomocy, ile razy mówią, a ile wybierają pilotem, i czy chcą obejrzeć jeszcze raz.

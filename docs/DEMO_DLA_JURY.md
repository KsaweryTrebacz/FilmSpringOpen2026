# Pokaz dla jury: bajka interaktywna jak w serwisie streamingowym

Prezentacja: **18.10.2026, 19:00**. Pokaz trwa około 4 minut i działa na jednym laptopie, bez internetu.
Jury jest „dzieckiem przed telewizorem”: jeden juror trzyma pilota (klawiaturę albo pilota do prezentacji
ze strzałkami), wszyscy mogą odpowiadać na głos, a ktoś z zespołu steruje symulowanym tętnem na panelu podglądu.

## Przygotowanie (przed wejściem jury)

1. Klipy na miejscu: prawdziwe albo zastępcze z nazwą pliku na planszy
   (`python -m bajka.placeholders scenarios/klub_ciekawskich.yaml`). Polecenie tworzy tylko brakujące pliki,
   więc uzupełnia też klipy reakcji (`01_reakcja_*.mp4`) i wersje scen (`*_spokojna.mp4`, `*_zywa.mp4`).
   Bez nich bajka się nie uruchomi („Brak plików wideo”).
2. Przeglądarka Edge albo Chrome (Chromium bez kodeka H.264 nie odtworzy MP4). Polski głos syntezatora w Windows
   (Ustawienia → Czas i język → Mowa), inaczej postać „mówi” tylko napisami.
3. Pierwsze uruchomienie modeli (Whisper, Phi) **przed pokazem** — pobierają się raz, potem działają bez internetu.
4. Zamknijcie podglądy po próbach (`python -m bajka.panel`, poprzednie uruchomienie bajki): zajęty port 8080
   albo 8090 kończy start komunikatem „Nie udało się uruchomić serwera (port zajęty?)”. Sprawdzenie:
   `netstat -ano | findstr 8080`.
5. Ekrany: laptop i projektor jako rozszerzony ekran (Win+P, „Rozszerz”). Kartę z odcinkiem przeciągnijcie
   na projektor i naciśnijcie **F** (pełny ekran); panel podglądu zostaje na laptopie.
6. Wersja liniowa na zapas i do pokazania (kilka minut ffmpeg, więc wcześniej):
   `python -m bajka.linear scenarios/klub_ciekawskich.yaml` → `scenarios/klub_ciekawskich_liniowy.mp4` + `.srt`.
7. Komenda startowa:

   ```powershell
   python -m bajka scenarios/klub_ciekawskich.yaml --panel
   ```

   Bez modeli (słabszy laptop albo kłopot z Foundry Local): dodajcie `--no-llm --no-mic` — okna wyboru działają
   pilotem, a głos zastępuje wybór strzałkami. Telewizor bez mikrofonu: `--mobile` i telefon jurora jako drugi ekran.

## Start

Odcinek czeka na przycisk **▶ Oglądaj**, więc aplikację można uruchomić wcześniej. W ustawieniach na ekranie
startowym zostawcie zaznaczone „Odpowiedzi głosem”, „Postać czyta swoje kwestie” i „Napisy”. Przeglądarka zapyta
o mikrofon — zezwólcie. Panel podglądu: `http://127.0.0.1:8090/`.

## Przebieg (około 4 minut)

| Czas | Co się dzieje | Co mówimy |
|---|---|---|
| 0:00–0:30 | Ekran startowy, juror naciska **Oglądaj**. SC. 1, potem pierwsze okno wyboru („Hop-sa-sa!” / „Puk, puk!”) | „To odcinek z serwisu streamingowego. Netflix wycofał swoje filmy interaktywne — my pokazujemy, jak zrobić to prościej i dla dzieci.” |
| 0:30–1:00 | Juror wybiera **strzałką i OK**. Gra nagrany klip reakcji. Na panelu: decyzja „wybór pilotem albo dotykiem” i wpis „Punkt odniesienia tętna widza” | „Pilot działa na każdym telewizorze. Dzieci, które nie czytają, mają obrazki.” |
| 1:00–1:45 | SC. 2: okno „Tęczowy Mostek / Szumiący Las”. Juror **mówi** „przez las!”. Pod oknem: „Słyszę: …”. W trakcie tego okna klikamy na panelu **Pobudzenie** | „Głos rozpoznaje Whisper na tym laptopie. Nic nie idzie do chmury, nagranie znika zaraz po rozpoznaniu.” |
| 1:45–2:30 | Las (albo mostek) i Wiaterek grają **wersję spokojną**; dziennik panelu mówi dlaczego. Okno z oddechem trwa 20 s | „Dziecko jest bardzo pobudzone, więc odcinek zwalnia: dłuższe ujęcia, cichszy dźwięk. Tętno dziś symulujemy, docelowo z zegarka, za zgodą rodzica.” |
| 2:30–3:15 | Przy oknie „Mapa, latarka czy lornetka?” nikt nic nie robi: postać dopytuje, a po czasie wybiera sama. Klikamy **Znużenie** | „Cisza nie zatrzymuje bajki. A gdy dziecko się nudzi, kolejna scena będzie żywsza.” |
| 3:15–4:00 | Święto w **wersji żywej**, wybór zakończenia, finał. Ekran końcowy: „Twoje wybory” i „Obejrzyj jeszcze raz” | „Cztery zakończenia, każde inne. Ten sam odcinek jest też zwykłym filmem dla serwisów bez interakcji” — pokazujemy plik `_liniowy.mp4` |

Wiaterek jest zawsze na ścieżce, więc to najpewniejsze miejsce na wersję spokojną. Wersję żywą mają Las i Święto.

## Kiedy klikać na panelu

Wersję sceny odcinek wybiera w chwili, gdy scena się zaczyna, więc tętno trzeba zmienić wcześniej.

1. **Najpierw punkt odniesienia.** Tętno liczy się względem odczytu tuż po pierwszej scenie. Klikajcie dopiero, gdy
   w dzienniku jest wpis „Punkt odniesienia tętna widza: N”.
2. **Z zapasem przed sceną.** Pobudzenie to co najmniej 15% ponad odniesieniem, znużenie — 3% poniżej. Symulator
   dochodzi do celu w kilka sekund, więc klikajcie co najmniej 10 s przed startem sceny (najlepiej w oknie wyboru
   poprzedniej sceny).
3. **Spokój** wraca do tętna wyjściowego — wtedy sceny grają zwykłe wersje.
4. **„▶ Przebieg demo”** robi to samo automatycznie (stoi 20 s, rośnie, wraca), ale trudniej trafić w scenę.

## Gdy coś nie działa

- **Nie słychać postaci:** brak polskiego głosu syntezatora — są napisy, pokaz idzie dalej.
- **Głos nie działa** (mikrofon, model): wybieramy pilotem; w ostateczności uruchamiamy z `--no-llm --no-mic`.
- **Wideo się nie odtwarza:** przeglądarka bez H.264 — otwórzcie adres w Edge albo Chrome.
- **Zamknięta karta:** odcinek czeka; otwórzcie `http://127.0.0.1:8080/` ponownie i naciśnijcie Oglądaj — bieżąca scena
  zagra od początku.
- **Panel się nie odświeża:** odcinek leci dalej; błędy panelu nigdy go nie zatrzymują.
- **Koniec:** „Zakończ” na ekranie końcowym zamyka odcinek i aplikację. Panel zostaje wygaszony z napisem
  „brak połączenia z odcinkiem” — to normalne.

## Pytania jury

| Pytanie | Odpowiedź |
|---|---|
| Netflix się z tego wycofał. Czemu wam ma się udać? | Netflix robił drogie filmy dla dorosłych z wieloma gałęziami i wycofał je, bo format „ograniczał” rozwój serwisu. My robimy krótkie odcinki dla dzieci: zagadki zbiegają się do tej samej sceny, a każdy odcinek ma wersję liniową dla serwisów bez interakcji. Głos dziecka to wartość, której zwykły film nie da ([STREAMING.md](STREAMING.md)) |
| Czy zbieracie dane dzieci? | Nie. Mikrofon działa tylko w oknie wyboru, nagranie trafia na laptop, na chwilę do pliku tymczasowego, i jest usuwane zaraz po rozpoznaniu. Tętno w demo jest symulowane |
| Skąd weźmiecie tętno? | Z zegarka dziecka przez telefon rodzica: Health Connect, HealthKit albo Bluetooth „Heart Rate”. Tylko za zgodą rodzica, tylko na urządzeniu, bez zapisu. Wcześniej chcemy sygnałów bez biometrii: czas reakcji i serie cisz |
| A RODO? | Tętno to dane o zdrowiu (art. 9): osobna zgoda, funkcja domyślnie wyłączona, nic nie trafia do serwisu |
| Jak to trafi do serwisu? | Trzy drogi: nasz odtwarzacz (aplikacja), manifest JSON dla odtwarzacza serwisu albo wersja liniowa (zwykły MP4 z napisami) |
| Czy zadziała z innym odcinkiem? | Tak. Historia to plik ze scenariuszem: sceny, okna wyboru, reakcje i wersje scen. Silnik się nie zmienia |
| Ile to kosztuje? | Modele AI działają lokalnie, bez opłat za chmurę. Produkcja: 10 scen + kilka krótkich reakcji i wersji |

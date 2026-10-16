# Pokaz dla jury: film, który słucha i czuje salę

Prezentacja: **18.10.2026, 19:00**. Pokaz trwa około 3 minut i działa na jednym laptopie, bez internetu.
Jury jest widownią: mówi do swoich telefonów, a jedna osoba steruje tętnem sali na panelu.

## Przygotowanie (przed wejściem jury)

1. Klipy na miejscu: prawdziwe albo zastępcze z nazwą pliku na planszy
   (`python -m bajka.placeholders scenarios/klub_ciekawskich.yaml`). Polecenie tworzy tylko brakujące pliki,
   więc uzupełnia też spokojne wersje scen (`03b_las_spokojna.mp4`, `04_wiaterek_spokojna.mp4`,
   `07_swieto_spokojna.mp4`). Bez nich bajka się nie uruchomi („Brak plików wideo”).
   Zastępcze klipy trwają po 4 sekundy i na nich liczymy 3 minuty. Z prawdziwymi klipami pokaz trwa dłużej.
2. Laptop i telefony w tej samej sieci Wi-Fi, port aplikacji mobilnej (8443) otwarty w zaporze Windows.
3. Zamknijcie wszystkie podglądy, które mogły zostać po próbach (`python -m bajka.panel`,
   `python -m bajka.mobile`). Zapomniany podgląd trzyma port 8090 (panel) albo 8443 (telefony) i odbierałby
   zapytania zamiast filmu. Sprawdzenie: `netstat -ano | findstr 8090` (a potem `8443`) nie powinno przed
   startem pokazać żadnego nasłuchującego procesu, a po starcie filmu dokładnie jeden.
4. Ekrany: laptop i projektor jako rozszerzony ekran (Win+P, „Rozszerz”).
   - **Zalecane:** bajka z `--windowed`. Okno filmu przeciągnijcie na projektor i rozwińcie na cały ekran.
     Panel i stronę z kodem QR otwórzcie w przeglądarce na ekranie laptopa.
   - **Panel na tablecie jury:** `BAJKA_PANEL_HOST=0.0.0.0` w `.env`, w przeglądarce tabletu adres IP laptopa
     i port 8090 (`BAJKA_PANEL_PORT`). Port panelu też musi być otwarty w zaporze Windows, tak samo jak 8443.
   - **Zamiast przeciągania okna:** ustawcie projektor jako ekran główny (Ustawienia, System, Ekran) i uruchomcie
     bajkę bez `--windowed`. Film otworzy się od razu na całym ekranie projektora. Przeglądarkę przesuńcie na laptopa.
   - Wybrany układ przećwiczcie na próbie, bo okna układają się chwilę, a film rusza od razu po starcie.
5. Komenda startowa (**jeszcze jej nie uruchamiajcie**, patrz „Start”):

   ```powershell
   python -m bajka scenarios/klub_ciekawskich.yaml --mobile --panel --windowed
   ```

   Przy ekranie głównym na projektorze ta sama komenda bez `--windowed`.
   Próba bez mikrofonu i bez telefonów: `python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed --panel`.

## Start (gdy jury już siedzi)

Film rusza zaraz po uruchomieniu, bez przycisku start. Dlatego komendę uruchamiamy dopiero wtedy, gdy jury siedzi.

1. Uruchomcie komendę z punktu 4. W konsoli pojawią się adres panelu (domyślnie `http://127.0.0.1:8090/`)
   i adres kodu QR dla telefonów (`https://<adres laptopa>:8443/qr`, po słowach „Kod QR na ekran kina”).
2. Otwórzcie w przeglądarce stronę z kodem QR i pokażcie ją jury: obróćcie ekran laptopa albo na chwilę
   przesuńcie okno przeglądarki na projektor. Potem otwórzcie panel.
3. Pierwsze pytanie (`powitanie`) może rozstrzygnąć krzykomierz, zanim telefony zdążą dołączyć. To też część
   pokazu: sala woła na głos. Od sceny `kuferek` decydują telefony.

## Przebieg (około 3 minut)

| Czas | Co się dzieje | Co mówimy |
|---|---|---|
| 0:00–0:30 | Uruchamiamy bajkę, film rusza od razu. Jury skanuje kod QR i dołącza telefonami. Pierwsze pytanie (`powitanie`) rozstrzyga krzykomierz, jeśli telefony jeszcze się łączą | „To kino, które słucha widowni i czuje salę. Wy jesteście dziś widownią.” |
| 0:30–1:15 | Od sceny `kuferek` Lila pyta, a jury odpowiada do telefonów. Na panelu rosną słupki głosów, a w drzewie scen podświetla się wybrana ścieżka. W trakcie pytania w `kuferek`, po wpisie „Punkt odniesienia tętna sali”, ktoś z jury klika „Sala się ekscytuje”. Wykres tętna wychodzi ponad normę | „Każdy mówi do swojego telefonu, a komputer w kinie liczy głosy całej sali. Wygrywa większość.” |
| 1:15–2:15 | Sceny `most` albo `las`, potem `wiaterek`. Sala jest już pobudzona, więc `wiaterek` gra wersję spokojną, a dziennik pisze dlaczego | „Film jest spokojny, a sala się rozkręciła. Dlatego ta scena ma wolniejszy montaż i dłuższe ujęcia.” |
| 2:15–3:00 | Film się kończy, a panel zostaje na ekranie (wygaszony, z ostatnim stanem) | Wizja: zegarki widzów, tylko średnia sali, zgoda opiekunów, nic nie jest zapisywane. Twórcy filmu dostają mapę emocji widowni. Kinoautomat z 1967 roku dał widzom przyciski; my dajemy im głos i puls |

Scena `wiaterek` jest zawsze na ścieżce, więc to najpewniejsze miejsce na pokazanie wersji spokojnej.
Spokojne wersje mają też `las` (jeśli widownia go wybierze) i `swieto`.

## Kiedy klikać na panelu

Wersję sceny film wybiera w chwili, gdy scena się zaczyna. Sala musi więc być pobudzona wcześniej.

1. **Najpierw punkt odniesienia.** Tętno sali liczy się względem tętna zmierzonego tuż po pierwszej scenie
   (`powitanie`). Kliknijcie „Sala się ekscytuje” dopiero wtedy, gdy w dzienniku panelu jest wpis
   „Punkt odniesienia tętna sali: N” (pod wykresem pojawia się „Odniesienie N”). Kliknięcie wcześniej zrobi
   z wysokiego tętna normę i spokojnej wersji nie będzie.
2. **Z zapasem przed sceną.** Sala jest pobudzona, gdy tętno jest co najmniej 15% ponad odniesieniem (przy 90 to około
   104). Symulator dochodzi do tego w kilka sekund, więc klikajcie co najmniej 10 sekund przed startem sceny
   ze spokojną wersją. Dla `wiaterek` niezawodny moment to pytanie w `kuferek` albo scena `most` / `las`, czyli
   zanim panel pokaże `wiaterek`. Nie czekajcie do końca tych scen. `las` zagra wersję spokojną tylko wtedy,
   gdy sala jest pobudzona już w chwili jego startu.
3. **Powrót do normy.** „Spokojna sala” wraca do tętna wyjściowego. Kliknijcie ją przed sceną `swieto`
   (z zapasem co najmniej 10 sekund), jeśli chcecie pokazać, że wtedy gra zwykła wersja.
4. **„▶ Przebieg demo”.** Tętno stoi w miejscu przez 20 sekund, potem rośnie i wraca do normy. Sala jest
   pobudzona mniej więcej od 30. do 80. sekundy po kliknięciu. Scena ze spokojną wersją musi zacząć się w tym oknie,
   a to trudno trafić. Ręczny przycisk „Sala się ekscytuje” łatwiej wcisnąć na scenie w dobrym momencie.

## Gdy coś nie działa

- **Telefony się nie łączą:** sprawdźcie Wi-Fi, port 8443 i ostrzeżenie o certyfikacie w telefonie („Zaawansowane,
  Przejdź do strony”, potem zgoda na mikrofon). Bez telefonów sceny z głosowaniem (`powitanie`, `kuferek`,
  `wiaterek`, `pomocnik`, `swieto`) rozstrzyga krzykomierz, a pozostałe (`most`, `las`, `laka`) bajka rozpoznaje
  z mikrofonu laptopa. Telefon, który dołączy w trakcie pytania, jeszcze na nie odpowie, a późniejsze
  liczą się od następnej decyzji.
- **Scena zagrała wersję zwykłą:** kliknięcie było za późno albo przed punktem odniesienia. Film leci dalej.
  Jeśli punkt odniesienia był już zapisany, kliknijcie „Sala się ekscytuje” w trakcie sceny `pomocnik` albo `laka`,
  a `swieto` zagra wersję spokojną.
- **Panel się nie odświeża:** film leci dalej, błędy panelu nigdy go nie zatrzymują. Wystarczy odświeżyć stronę.
- **Brak internetu:** nic nie szkodzi, wszystko działa lokalnie na laptopie.
- **Koniec filmu:** po ostatniej scenie aplikacja sama się zamyka (`Esc` zamyka ją wcześniej). Panel w przeglądarce
  zostaje z ostatnim stanem, wygaszony, z napisem „brak połączenia z filmem”. To normalne. Nie odświeżajcie wtedy strony.

## Pytania jury

| Pytanie | Odpowiedź |
|---|---|
| Czy zbieracie dane dzieci? | Nie zapisujemy niczego. Telefon nagrywa głos tylko w trakcie pytania. Nagranie trafia do laptopa, na chwilę do pliku tymczasowego, i jest usuwane zaraz po rozpoznaniu. Na pokazie nic nie idzie do chmury (tryb `--backend azure` wysłałby nagranie do Azure, więc go nie używamy). Tętno w demo jest symulowane |
| Skąd naprawdę weźmiecie tętno? | Z zegarka sparowanego z telefonem: Health Connect (Android), HealthKit (iOS) albo standard Bluetooth „Heart Rate”. Do komputera trafia tylko średnia sali |
| A RODO? | Tętno to dane o zdrowiu (art. 9). Tylko za wyraźną zgodą opiekunów, dobrowolnie, w trakcie seansu i bez zapisywania |
| Ile to kosztuje kino? | Jeden laptop (na przykład Copilot+ PC) i Wi-Fi. Modele AI działają lokalnie, bez opłat za chmurę |
| Czy to zadziała z innym filmem? | Tak. Historia to plik ze scenariuszem: sceny, pytania, nastrój filmu i wersje scen. Silnik się nie zmienia |

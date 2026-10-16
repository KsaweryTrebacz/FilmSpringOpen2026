# Pokaz dla jury: film, który słucha i czuje salę

Prezentacja: **18.10.2026, 19:00**. Pokaz trwa około 3 minut i działa na jednym laptopie, bez internetu.
Jury jest widownią: mówi do swoich telefonów, a jedna osoba steruje tętnem sali na panelu.

## Przygotowanie (przed wejściem jury)

1. Klipy na miejscu: prawdziwe albo zastępcze z nazwą pliku na planszy
   (`python -m bajka.placeholders scenarios/klub_ciekawskich.yaml`).
2. Laptop i telefony w tej samej sieci Wi-Fi, port aplikacji mobilnej (8443) otwarty w zaporze Windows.
3. Start bajki z telefonami i panelem:

   ```powershell
   python -m bajka scenarios/klub_ciekawskich.yaml --mobile --panel
   ```

   Próba bez mikrofonu i bez telefonów: `python -m bajka scenarios/klub_ciekawskich.yaml --text --no-llm --windowed --panel`.
4. Panel otwarty w przeglądarce (adres w konsoli, domyślnie `http://127.0.0.1:8090/`) na ekranie laptopa albo
   na tablecie jury (`BAJKA_PANEL_HOST=0.0.0.0` w `.env`, adres IP laptopa i port 8090).
5. Na ekranie kina plansza z kodem QR (adres z konsoli z dopiskiem `qr`).

## Przebieg (około 3 minut)

| Czas | Co się dzieje | Co mówimy |
|---|---|---|
| 0:00–0:30 | Jury skanuje kod QR i dołącza telefonami | „To kino, które słucha widowni i czuje salę. Wy jesteście dziś widownią.” |
| 0:30–1:15 | Lila pyta, jury odpowiada do telefonów. Na panelu rosną słupki głosów, a w drzewie scen podświetla się wybrana ścieżka | „Każdy mówi do swojego telefonu, a komputer w kinie liczy głosy całej sali. Wygrywa większość.” |
| 1:15–2:15 | Przed sceną `wiaterek` ktoś z jury klika „Sala się ekscytuje” (albo wcześniej „Przebieg demo”). Wykres tętna wychodzi ponad normę, scena gra wersję spokojną, a dziennik pisze dlaczego | „Film jest spokojny, a sala się rozkręciła. Dlatego ta scena ma wolniejszy montaż i dłuższe ujęcia.” |
| 2:15–3:00 | Panel zostaje na ekranie | Wizja: zegarki widzów, tylko średnia sali, zgoda opiekunów, nic nie jest zapisywane. Twórcy filmu dostają mapę emocji widowni. Kinoautomat z 1967 roku dał widzom przyciski; my dajemy im głos i puls |

Scena `wiaterek` jest zawsze na ścieżce, więc to najpewniejsze miejsce na pokazanie wersji spokojnej.
Spokojne wersje mają też `las` (jeśli widownia go wybierze) i `swieto`.

## Gdy coś nie działa

- **Telefony się nie łączą:** bajka sama słucha sali; decyzje rozstrzyga krzykomierz („Krzyczymy: LAS!”).
- **Panel się nie odświeża:** film leci dalej, błędy panelu nigdy go nie zatrzymują. Wystarczy odświeżyć stronę.
- **Brak internetu:** nic nie szkodzi, wszystko działa lokalnie na laptopie.

## Pytania jury

| Pytanie | Odpowiedź |
|---|---|
| Czy zbieracie dane dzieci? | Nie. Nagrania z telefonów są rozpoznawane w pamięci i od razu znikają. Tętno w demo jest symulowane |
| Skąd naprawdę weźmiecie tętno? | Z zegarka sparowanego z telefonem: Health Connect (Android), HealthKit (iOS) albo standard Bluetooth „Heart Rate”. Do komputera trafia tylko średnia sali |
| A RODO? | Tętno to dane o zdrowiu (art. 9). Tylko za wyraźną zgodą opiekunów, dobrowolnie, w trakcie seansu i bez zapisywania |
| Ile to kosztuje kino? | Jeden laptop (na przykład Copilot+ PC) i Wi-Fi. Modele AI działają lokalnie, bez opłat za chmurę |
| Czy to zadziała z innym filmem? | Tak. Historia to plik ze scenariuszem: sceny, pytania, nastrój filmu i wersje scen. Silnik się nie zmienia |

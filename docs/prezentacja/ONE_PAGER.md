# Klub Ciekawskich — bajka, która słucha

**Interaktywna animacja dla dzieci 3–7 lat, w której dziecko rozmawia z bohaterami, a rodzic decyduje, czego się uczy.**
(nazwa robocza · FilmSpring Open 2026)

![Okno wyboru na klipie odcinka](media/okno-droga-glos.jpg)

## Problem
- Bajka w telewizji i w serwisach mówi do dziecka, ale nie słyszy odpowiedzi. 15 minut ekranu to 15 minut słuchania.
- Rodzic wybiera tytuł — i na tym kończy się jego wpływ na to, czego dziecko się uczy.
- WHO i pediatrzy: dzieci 2–4 lata do 1 godziny ekranu dziennie; liczy się jakość i oglądanie razem z dorosłym.

## Rozwiązanie
- **Rozmowa:** w oknie wyboru dziecko odpowiada pilotem, dotykiem albo głosem, swoimi słowami; postać reaguje.
- **Wybór zmienia historię:** każda odpowiedź ma swoją scenę, a wybory widza są nakładane na klipy jako warstwy.
  Montażysta AI łączy klipy płynnymi przejściami.
- **Rodzic ma ster:** Kreator Rodzica — cele nauki, liczba zagadek, czas na odpowiedź, głos lub pilot, limit ekranu;
  po odcinku raport i pomysły na rozmowę bez ekranu ([KREATOR_RODZICA.md](KREATOR_RODZICA.md)).

## Dlaczego to działa
W badaniu z 240 dziećmi (serial *Elinor Wonders Why*) dzieci, z którymi postać naprawdę rozmawiała, odpowiedziały
poprawnie na 63% pytań, wobec 56% po zwykłej wersji; dzieci z biedniejszej dzielnicy dorównały rówieśnikom z zamożnej.
Źródła: [BADANIA.md](BADANIA.md).

## Dlaczego teraz
- Rozpoznawanie mowy i małe modele językowe działają **na urządzeniu** (Copilot+ PC z NPU): bez chmury, bez kosztu
  na widza, bez wysyłania głosu dziecka.
- Generatory wideo obniżają koszt klipów i gałęzi.
- Netflix wycofał drogie filmy interaktywne dla dorosłych (2024–2025) — nisza dla dzieci jest pusta, a my wiemy,
  czego unikać: tanie gałęzie, warstwy, wersja liniowa każdego odcinka.

## Model biznesowy (hipotezy)
| Klient | Co dostaje | Jak płaci |
|---|---|---|
| Rodziny | Aplikacja z Kreatorem i biblioteką odcinków | subskrypcja [__ zł/mies.] |
| Serwisy i aplikacje dla dzieci | Odcinki + odtwarzacz albo manifest JSON i wersja liniowa | licencja [__] |
| Przedszkola, biblioteki | Odcinki pod temat tygodnia, tryb sali | licencja placówki [__] |
| Studia i właściciele postaci | Narzędzia do odcinków interaktywnych z własnych postaci | licencja narzędzi [__] |

## Stan
Działający prototyp: odcinek „Bzyczka szuka domu” (8 klipów z generatora + zaślepki), odtwarzacz w przeglądarce,
odpowiedzi głosem na urządzeniu, montaż AI, gałęzie i warstwy, wersja liniowa i manifest, panel podglądu,
ponad 400 testów automatycznych. Kreator Rodzica: makieta i koncepcja; większość parametrów działa w silniku.

## Szukamy
Rodzin do pilotażu · studia animacji lub wydawcy z postaciami dla dzieci · serwisu albo platformy edukacyjnej
na pierwsze wdrożenie. Kontakt: [__]

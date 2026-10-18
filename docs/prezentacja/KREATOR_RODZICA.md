# Kreator Rodzica: rodzic składa odcinek, dziecko w nim gra

Propozycja zastosowania mechaniki projektu: **rodzic tworzy dla dziecka edukacyjną animację** — wybiera, czego
dziecko ma się dziś uczyć, ile ma być zagadek i jak dziecko odpowiada — a dziecko ogląda odcinek, w którym rozmawia
z bohaterami i decyduje o drodze. Makiety: [mockupy/kreator.html](mockupy/kreator.html) (ustawienia)
i [mockupy/raport.html](mockupy/raport.html) (po odcinku); zrzuty w [media/](media/).

![Kreator Rodzica — makieta](media/kreator.png)

## Dla kogo i po co

- **Rodzic dziecka 4–7 lat**, który i tak włącza bajkę, ale chce, żeby te 15 minut było aktywne i czegoś uczyło,
  i żeby to on decydował, czego i jak długo.
- **Rodzeństwo**: odcinek dla dwójki dzieci w różnym wieku (profile, odpowiedzi na zmianę).
- **Przedszkole, biblioteka, świetlica**: nauczyciel ustawia odcinek pod temat tygodnia.

**Koedukacyjnie**: ta sama bajka dla dziewczynek i chłopców — postacie mówią do widza bez form zależnych od płci
(„pomożesz?”, „świetnie liczysz”), bohaterowie łamią stereotypy (Lila majsterkuje i prowadzi wyprawę, Fiku mówi,
że się boi), a tryb rodzeństwa i „Oglądamy razem” zaprasza do wspólnego oglądania.

## Co ustawia rodzic

Kolumna „Status” wskazuje, które elementy działają już w prototypie, a które są planowane na kolejnych etapach:

| Ustawienie | Działanie w odcinku | Status |
|---|---|---|
| **Tematyka edukacyjna** (liczenie, kolory i wzory, ćwiczenia oddechowe, przyroda) | Wybór modułów z biblioteki scen. Scena zawiera okno wyboru, gałęzie i reakcje przypisane do danej umiejętności. | Planowane; w pilocie zrealizowano moduły: wzór (deski), oddech (Wiaterek), liczenie (łąka), narzędzia (pomocnik) |
| **Liczba zagadek** (np. 3 lub 4 z 8) | W scenach niewybranych przez rodzica postać decyduje sama, skracając czas trwania odcinka. | Scenariusz z pominięciem zagadek działa w module liniowym (`python -m bajka.linear`) |
| **Czas na odpowiedź** | Długość odliczania w oknie wyboru (10–20 s). | Działa w prototypie (`timeout` sceny, zmienna `BAJKA_CHOICE_SECONDS`) |
| **Liczba podpowiedzi** | Ile razy postać dopytuje przed podjęciem samodzielnej decyzji. | Działa w prototypie (`BAJKA_MAX_REPROMPTS`) |
| **Poziom trudności** | Wybór między 2 a 3 opcjami, zakres liczenia, stopień złożoności wzorów logicznych. | Planowane (silnik obsługuje 2 lub 3 opcje) |
| **Tryb odpowiedzi (głos / pilot)** | Włączenie mikrofonu w oknie wyboru lub ograniczenie do pilota i dotyku. Dźwięk przetwarzany lokalnie, bufor czyszczony z pamięci RAM. | Działa w prototypie (opcja w odtwarzaczu lub flaga `--no-mic`) |
| **Napisy dla dzieci** | Wyświetlanie kwestii dialogowych i pytań na ekranie. | Działa w prototypie |
| **Tryb wspólnego oglądania** | Podgląd pytań na telefonie rodzica i propozycje rozmów w trakcie seansu. | Działa serwer mobilny (`--mobile`); dedykowana treść pytań w opracowaniu |
| **Limit czasu ekranowego** | Licznik czasu w profilu; po seansie aplikacja proponuje zabawę manualną bez autoodtwarzania kolejnego odcinka. | Planowane |
| **Adaptacja tempa do tętna** | Dobór wersji sceny (spokojna lub żywa) na podstawie odczytu tętna. | Silnik i symulator tętna działają (`--panel`); integracja z fizycznym smartwatchem w planach |
| **Podsumowanie po seansie** | Raport z wyborami dziecka, czasem reakcji i propozycjami rozmowy poza ekranem. | Zbieranie danych działa (`StoryEngine.decisions`); generowanie pytań w planach |

Kreator v0 to więc **ekran ustawień nad parametrami, które silnik już ma**; trudniejsza część to biblioteka modułów.

## Jak powstaje odcinek

```
Rodzic: cele, wiek, liczba zagadek, czas, głos ──► Planista (model językowy)
                                                    │ wybiera moduły z biblioteki i układa graf scen
                                                    ▼
                         Scenariusz odcinka (YAML) ──► walidacja silnika: każda ścieżka ma koniec,
                                                    │  każdy klip istnieje, każde okno ma wybór domyślny
                                                    ▼
Biblioteka zatwierdzonych modułów (klipy, reakcje, warstwy) ──► Odtwarzacz + montażysta AI na urządzeniu
```

1. **Planista** (model językowy, np. Phi na urządzeniu albo w chmurze) dostaje cele rodzica i katalog modułów,
   a oddaje scenariusz w tym samym formacie YAML co dziś `scenarios/klub_ciekawskich.yaml`. Nie pisze nowych
   scen ani dialogów — wybiera i łączy gotowe.
2. **Walidacja** silnika (`bajka.scenario`) odrzuca scenariusz, w którym coś nie gra: brak klipu, ścieżka bez końca,
   okno bez wyboru domyślnego. Dziecko nigdy nie zobaczy „zepsutego” odcinka.
3. **Biblioteka modułów** powstaje w studiu: klipy z generatora wideo według biblii wizualnej
   ([SCENARIUSZ_WIZUALNY_PROMPTY_AI.md](../SCENARIUSZ_WIZUALNY_PROMPTY_AI.md)), import narzędziem `bajka.clips`
   i **sprawdzenie przez człowieka** przed publikacją. Nie generujemy wideo na żywo dla dziecka.
4. **Montażysta AI** na urządzeniu łączy moduły płynnymi przejściami, a wybory dziecka nakłada jako warstwy.

Personalizacja na żywo ogranicza się do krótkich kwestii postaci w odpowiedzi na słowa dziecka, które przechodzą
przez filtr treści (`bajka/safety.py`) i są tylko w napisach.

## Zasady projektowe (z badań)

Szczegóły i źródła: [BADANIA.md](BADANIA.md).

- **Postać naprawdę reaguje** na odpowiedź (każda odpowiedź ma reakcję), a nie tylko „robi pauzę”.
- **Cisza nie karze**: postać dopytuje, potem wybiera sama; odcinek nigdy nie staje.
- **Pomyłka jest częścią przygody**: zła deska to osobna scena, w której naprawiamy mostek razem.
- **Wyraźny koniec**: ekran „Koniec odcinka”, bez automatycznego następnego odcinka, bez nagród za czas oglądania.
- **Limit i wspólne oglądanie** zgodne z WHO (do 1 h dziennie dla 2–4 lat) i AAP (oglądanie z rodzicem).
- **Prywatność domyślnie**: AI na urządzeniu, mikrofon tylko w oknie wyboru, nagrania usuwane od razu, tętno tylko
  za osobną zgodą rodzica (dane o zdrowiu, RODO art. 9), bez zapisu.

## Przykładowe zestawy

| Zestaw | Ustawienia |
|---|---|
| **Szybka zagadka przed obiadem** | 2 zagadki, 15 s na odpowiedź, ok. 7 min, pilot zamiast głosu |
| **Wieczorne wyciszenie** | moduły oddechu i liczenia, wersje spokojne scen, bez głośnych reakcji, napisy wyłączone |
| **Liczymy z rodzeństwem** | 6 zagadek, trudność „średnia”, odpowiedzi na zmianę, „Oglądamy razem” włączone |
| **Przedszkole: temat tygodnia „Pszczoły”** | rzutnik i pilot u nauczyciela albo głosowanie z kilku tabletów (`--mobile`), 5 zagadek, wersja liniowa na zapas |

## Po odcinku

![Raport po odcinku — makieta](media/raport.png)

Raport pokazuje drogę dziecka, sposób odpowiedzi (głos, pilot, wybór postaci), ćwiczone umiejętności i trzy pomysły
na rozmowę albo zabawę bez ekranu. Nie zawiera nagrań ani transkrypcji wypowiedzi dziecka.

# Badania: co wiemy o bajkach interaktywnych i co z tego bierzemy

Podstawa naukowa produktu i slajdów „Dlaczego to działa”. Każda liczba ma źródło; czego nie udało się sprawdzić
w źródle pierwotnym, oznaczamy. Nie podajemy danych rynkowych, których nie mamy — w modelu biznesowym są miejsca do
uzupełnienia po pilotażu.

## 1. Dziecko uczy się z ekranu, gdy ekran mu odpowiada

**Troseth, Saylor i Archer (2006), *Child Development* 77(3), 786–799.** Dwulatki zwykle nie korzystały z informacji
z nagrania wideo (np. gdzie ukryto zabawkę), ale gdy osoba na ekranie wchodziła z nimi w kontakt na żywo, „zależny”
od dziecka (rozmowa przez telewizję w czasie rzeczywistym), dzieci wykorzystywały informację z ekranu.
([opis w EdTech Hub](https://docs.edtechhub.org/lib/53A22D6L),
[komunikat Vanderbilt University](https://news.vanderbilt.edu/2006/05/18/video-wasted-on-toddlers-unless-its-interactive-58995/))

**Co bierzemy:** pytanie postaci ma sens tylko wtedy, gdy postać naprawdę reaguje na odpowiedź dziecka. Dlatego każda
odpowiedź ma własną reakcję i często własną scenę, a postać, która „nie usłyszała”, dopytuje zamiast iść dalej.

## 2. Rozmowa z postacią bajki poprawia naukę — i wyrównuje szanse

**Xu, Vigil, Bustamante, Warschauer — „Elinor's Talking to Me!” (CHI 2022) i dalsze badania zespołu Ying Xu.**
Do odcinków serialu PBS KIDS *Elinor Wonders Why* dodano rozmowę: postać zadaje pytanie, rozpoznawanie mowy zamienia
odpowiedź dziecka na tekst, a system wybiera najlepiej pasującą odpowiedź Elinor.
- W badaniu z udziałem 240 dzieci (trzy grupy po 80) dzieci oglądające wersję z prawdziwą rozmową odpowiedziały
  poprawnie na **63%** pytań sprawdzających, wersję „pozornie interaktywną” (pytanie, pauza, ogólna pochwała) — **61%**,
  a zwykłą wersję telewizyjną — **56%**.
- Dzieci z dzielnicy o niskich dochodach, które oglądały wersję z AI, osiągnęły wyniki z nauk przyrodniczych
  porównywalne z dziećmi z zamożnej dzielnicy oglądającymi zwykłą wersję.
- Autorzy opisują też większe zaangażowanie i bardziej pozytywny odbiór wersji z rozmową.

Źródła: [CHI 2022 (NSF PAR)](https://par.nsf.gov/biblio/10346104),
[artykuł autorki w The Conversation / The 74](https://www.the74million.org/article/kids-cartoon-characters-that-use-ai-to-customize-responses-help-children-learn/),
[EdSurge 2021](https://www.edsurge.com/news/2021-02-09-when-the-animated-bunny-in-the-tv-show-listens-for-kids-answers-and-answers-back),
[„Artificial Intelligence Enhances Children's Science Learning” (APA, 2025)](https://psycnet.apa.org/fulltext/2025-11376-001.pdf).

**Co bierzemy:** to najmocniejszy argument produktu. Nasza bajka robi to samo, co wersja „z prawdziwą rozmową”
(rozpoznaje słowa dziecka i dobiera reakcję), a nie to, co wersja pozorna znana z telewizji (pytanie i pauza).
Do tego wybór dziecka **zmienia dalszą scenę**, czego w badaniu Elinor nie było. Uczciwie: różnica 63% vs 56%
dotyczy tamtego serialu i tamtych pytań; nasz efekt trzeba zmierzyć w pilotażu (sekcja 5).

## 3. Ile ekranu i jakiego

**WHO (2019), wytyczne dla dzieci poniżej 5 lat.** Niemowlęta: ekran niezalecany; dzieci 2–4 lata: czas siedzący przed
ekranem nie dłużej niż 1 godzina dziennie, mniej znaczy lepiej; w czasie siedzącym zalecane jest wspólne czytanie
i opowiadanie z opiekunem.
([WHO](https://www.who.int/news/item/24-04-2019-to-grow-up-healthy-children-need-to-sit-less-and-play-more),
[PAHO](https://www.paho.org/en/news/24-4-2019-grow-healthy-children-need-sit-less-and-play-more))

**American Academy of Pediatrics (2016), „Media and Young Minds”.** Dla dzieci 2–5 lat ok. 1 godziny dziennie
programów dobrej jakości, najlepiej oglądanych razem z rodzicem, który pomaga dziecku zrozumieć, co widzi
(omówienie: [First Things First](https://www.firstthingsfirst.org/2016/12/screen-time-recommendations-from-pediatricians/)).

**Co bierzemy:**
- **Kreator Rodzica ma limit dzienny** i nie proponuje kolejnego odcinka automatycznie; po odcinku jest zabawa bez
  ekranu ([KREATOR_RODZICA.md](KREATOR_RODZICA.md)).
- **Tryb „Oglądamy razem”**: pytania dla rodzica w trakcie i rozmowa po odcinku — to, co zalecają WHO i AAP.
- Odcinki są krótkie (10–15 min) i mają wyraźny koniec.

## 4. Rynek: interaktywne filmy są trudne — wiemy dlaczego

Netflix wycofał prawie wszystkie „Interactive Specials” (20 z 24 do 1.12.2024, ostatnie w maju 2025), tłumacząc,
że format „ograniczał” rozwój serwisu; programy przygodowe wróciły jako zwykłe filmy. Źródła i omówienie:
[STREAMING.md](../STREAMING.md#realia-rynku-dlaczego-urealnić).

**Co bierzemy:** produkcja musi być tania (gałęzie wracają na wspólną drogę, wybory „kosmetyczne” to warstwy
na jednym klipie), a każdy odcinek ma wersję liniową. Interakcja musi dawać coś, czego film nie da: rozmowę.

## 5. Czego jeszcze nie wiemy (i jak sprawdzimy)

| Pytanie | Jak sprawdzimy |
|---|---|
| Czy dzieci 4–7 lat same rozumieją okno wyboru? | Pilotaż: 5–10 rodzin, bez instruktażu ([plan](../ZGODNOSC_Z_REGULAMINEM.md#test-z-prawdziwą-publicznością-5-ust-3)) |
| Jak dobrze Whisper rozumie polskie dzieci? | Log aplikacji: ile odpowiedzi głosem rozpoznano, ile razy postać dopytała |
| Czy dzieci uczą się więcej niż z wersji liniowej? | Ten sam odcinek interaktywnie i liniowo, krótkie pytania po obejrzeniu (jak w badaniu Elinor) |
| Czy rodzice chcą sterować liczbą zagadek? | Rozmowa z rodzicami po pilotażu, klikalna makieta Kreatora |

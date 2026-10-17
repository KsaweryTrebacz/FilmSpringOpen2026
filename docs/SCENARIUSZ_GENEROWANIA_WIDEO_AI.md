# Bzyczka szuka domu – Kompleksowy Scenariusz i Prompty do Generowania Scen Wideo AI

Dokumentacja realizacyjna do wygenerowania wszystkich **21 plików wideo (.mp4)** wymaganych przez silnik bajki (`scenarios/klub_ciekawskich.yaml`).
Ścieżka docelowa dla wygenerowanych klipów:  
`scenarios/clips/klub_ciekawskich/<nazwa_pliku>.mp4`

---

## 🎨 Globalny Styl Wizualny (Style Consistency Anchor)

Wszystkie sceny muszą zachować ten sam styl wizualny i paletę barw:
- **Styl:** Miękka akwarela dla dzieci, ilustracja książkowa 2D, ciepłe pastele, ręcznie malowane tła, subtelne kontury, delikatne animacje postaci w stylu klasycznych europejskich bajek (jak *Kubuś Puchatek*, *Gruffalo*, *Dzieci z Bullerbyn*).
- **Proporcje i format:** 16:9, rozdzielczość 1920×1080, 24 fps.
- **Master Style Prompt Prefix (dodawaj do każdego promptu w generatorze wideo AI):**
  > `Children's book illustration style, 2D animation, soft watercolor textures, warm pastel colors, storybook aesthetic, gentle cinematic lighting, high quality, 1920x1080 --no 3d, realistic, photorealistic, harsh shadows, dark grim tones`

---

## 👥 Stałe Postacie (Character Consistency Prompts)

1. **Lila Lupka (Hero):**
   - *Opis:* 7-letnia ciekawska dziewczynka, kasztanowe warkoczyki, dżinsowe ogrodniczki z kieszonkami na śrubki, jasny sweterek, jasnoczerwona apaszka, **żółte kalosze** oraz **duża lupa z mosiężną ramką na sznurku na szyi**.
   - *Prompt:* `7-year-old girl named Lila, braided brown hair, denim dungarees, bright yellow rubber rain boots, wearing a large magnifying glass necklace, warm cheerful expression`.
2. **Fiku Fikołek:**
   - *Opis:* Rudy, wesoły i ruchliwy wiewiórek, puszysty ogon zwinięty w kształt znaku zapytania, miękki zielony szalik wokół szyi, mały lniany fartuszek piekarza.
   - *Prompt:* `Adorable cute red squirrel named Fiku, bushy tail shaped like a question mark, wearing a cozy green scarf and a tiny baker apron, friendly expressive eyes`.
3. **Pszczółka Bzyczka:**
   - *Opis:* Malutka, puchata pszczółka z różowymi policzkami, ubrana w miętowy dzianinowy sweterek w żółto-miodowe paski, małe koszyczki na pyłek przy nóżkach.
   - *Prompt:* `Tiny fluffy cute honeybee named Bzyczka, wearing a mint-green knit sweater with honey-yellow stripes, blushing pink cheeks, sweet innocent expression, gentle fluttering translucent wings`.
4. **Wiaterek Fiufiu:**
   - *Opis:* Mały, puszysty biały obłoczek-wietrzyk z sympatyczną buzią i rumianymi policzkami, który unosi się w powietrzu, zawirowuje liście, gdy się cieszy rośnie, a po głębokim wydechu maleje.
   - *Prompt:* `Friendly living little white cloud creature named Fiufiu, blushing pink cheeks, swirls of gentle breeze, playful and whimsical`.
5. **Kuferek Hopsasa:**
   - *Opis:* Kolorowy, drewniany stary kufer podróżny, oklejony zabawnymi naklejkami ze stemplami podróżnymi, wieko rusza się jak usta podczas mówienia, w środku bije ciepłe tęczowe światło.
   - *Prompt:* `Whimsical magical wooden travel chest trunk named Hopsasa, covered in vintage colorful travel stickers, the lid opens like a talking mouth with gentle golden glow inside`.

---

## 🎬 Katalog Scen i Prompty Generatora

---

### SCENA 1: Dziupla Klubu Ciekawskich (`powitanie`)

#### 1. `01_powitanie.mp4` (Klip główny · ok. 60–70 s)
- **Akcja:** Kamera wjeżdża do przytulnej dziupli starego dębu. Wszędzie słoiki z guzikami, suszone liście, drewniane półki. Lila macha do widowni wesoło, Fiku robi fikołka i ląduje obok niej. Lila pokazuje świecącą lupkę. Do dziupli wpada zagubiona Pszczółka Bzyczka, płacze. Fiku otula ją ogonem. Lila zwraca się do ekranu: pyta dzieci, czy zawołają Kuferek okrzykiem „Hop-sa-sa!”.
- **Ruch kamery:** Powolny najazd do przodu (Slow push-in), następnie kadr z perspektywy widza na Lilę i Fiku.
- **AI Video Prompt:**
  > `Children's book illustration 2D animation, cozy oak tree hollow clubhouse, wooden shelves with button jars, warm amber sunlight. A cheerful 7yo girl Lila in yellow boots waves at the camera with her cute red squirrel friend doing a joyful somersault. A tiny bee in a mint sweater flies in tearfully. Lila points her glowing magnifying glass towards the camera. Whimsical, heartwarming, soft watercolor storybook style.`

#### 2. `01_powitanie_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Lila i Fiku trzymają dłonie przy uszach w geście nasłuchiwania w stronę widowni, uśmiechają się cierpliwie. Kuferek w tle cicho pochrapuje (delikatnie unosi się i opada). W prawym dolnym rogu ekranu pulsuje złota lupka (sygnał mówienia).
- **Audio:** Cisza (dźwięk wyciszony, mikrofon sali słucha).
- **AI Video Prompt:**
  > `Looping animation, cozy tree hollow, 7yo girl and cute red squirrel with hands cupped behind their ears patiently listening to the viewer, smiling, gentle breathing motion, magical glowing magnifying glass icon pulsing softly in bottom-right corner, seamless subtle loop, watercolor 2D animation.`

---

### SCENA 2: Kuferek i Wybór Drogi (`kuferek`)

#### 3. `02_kuferek.mp4` (Klip główny · ok. 45 s)
- **Akcja:** Kuferek ziewa szeroko, wieko się otwiera, z wnętrza wylatuje tęczowy blask. Wyskakują 3 przedmioty: Mapa Rozkładanka, Latarka Świetliczka i Lornetka Patrzałka. Lila rozkłada mapę i ogląda ją przez lupę. Na mapie widać dwie ścieżki: Tęczowy Mostek nad strumykiem oraz Szumiący Las. Lila pyta salę: „Przez Tęczowy Mostek czy przez Szumiący Las?”.
- **AI Video Prompt:**
  > `Magical talking travel chest pops open with golden sparkles and rainbow light. Three illustrated adventure tools hop out: a folded parchment map, a cute torchlight, and brass binoculars. Lila unrolls the map showing two illustrated paths: a vibrant rainbow wooden bridge and a whispering green forest. Lila turns to camera with an inviting smile. Soft watercolor illustration.`

#### 4. `02_kuferek_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Kadr na rozłożoną mapę z dwiema ścieżkami. Tęczowy Mostek i Szumiący Las na przemian delikatnie pulsują i lśnią gwiezdnym pyłem, zachęcając do wyboru. W rogu pulsująca lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless looping shot of an open vintage illustrated storybook map on a rustic wooden table. One path shows a rainbow wooden footbridge over a babbling stream, the other path shows emerald pine trees gently swaying. The two locations take turns softly glowing with pastel fairy dust. Soft storybook aesthetic.`

---

### SCENA 3a: Tęczowy Mostek (`most`)

#### 5. `03a_most.mp4` (Klip główny · ok. 40 s)
- **Akcja:** Bohaterowie docierają do strumyka z drewnianym mostkiem. Deski tworzą powtarzalny kolorowy wzór: czerwona, niebieska, czerwona, niebieska. W pewnym miejscu jest dziura – brakuje jednej deski! Fiku trochę się boi, Lila go pociesza. Kuferek wysuwa z wieka dwie deski: czerwoną i niebieską. Lila pyta dzieci: „Jaka deska pasuje do dziury, czerwona czy niebieska?”.
- **AI Video Prompt:**
  > `Sunny outdoor landscape, sparkling crystal stream crossed by a wooden bridge painted in alternating vibrant red and blue planks. In the middle of the bridge, one plank is missing. A cute red squirrel looks anxious, Lila gently places a hand on his shoulder reassuringly. The magical chest presents two wooden planks, one red and one blue. Lila asks the viewer for help. Warm watercolor children's book art.`

#### 6. `03a_most_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Czerwona i niebieska deska lewitują lekko nad mostkiem z miękką poświatą. Woda pod mostkiem szemrze, w prawym dolnym rogu pulsuje lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless looping animation of a colorful wooden footbridge over a clear stream. A red wooden board and a blue wooden board float gently in mid-air with a subtle sparkle next to the gap in the bridge planks. Gentle water ripple, tranquil sunny atmosphere, watercolor 2D animation.`

---

### SCENA 3b: Szumiący Las (`las`)

#### 7. `03b_las.mp4` (Klip główny · ok. 40 s)
- **Akcja:** Ścieżka wchodzi w gęsty, szmaragdowo-zielony las ze snopami słonecznego światła przeszywającymi korony drzew. Słychać szum liści, a z dziupli rozlega się tajemnicze „Hu-hu! Hu-hu!”. Fiku skacze i krzyczy: „To na pewno żaba!”, ale Bzyczka ma wątpliwości. Lila pyta widownię: „Kto tak woła hu-hu? Sowa czy żaba?”.
- **AI Video Prompt:**
  > `Enchanted lush green forest canopy, soft dappled sunlight filtering through swaying oak leaves. Lila, squirrel Fiku, and tiny bee Bzyczka walk along a mossy trail. In a high hollow tree branch, two sleepy golden owl eyes peek through the shadow. Squirrel enthusiastically mimics a frog jump, Lila smiles at the camera, raising an eyebrow quizzically. Watercolor fairytale art.`

#### 8. `03b_las_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Zbliżenie na dziuplę w starym drzewie – zaspana, puchata sówka powoli mruga wielkimi oczami, liście wokół łagodnie falują. W rogu pulsuje lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless loop of a fluffy, cute sleepy cartoon owl sitting inside a tree hollow, slowly blinking large amber eyes in the soft shaded woodland. Leaves rustle gently in the background. Calm, cozy, pastel picture-book illustration.`

#### 9. `03b_las_spokojna.mp4` (Wersja spokojna / wariant tętna · ok. 40 s)
- **Akcja:** Ta sama scena, ale z wolniejszym tempem montażu, dłuższymi, statycznymi ujęciami, ciepłym, kojącym światłem, redukującym przebodźcowanie sali.
- **AI Video Prompt:**
  > `Slow contemplative cinema pace, serene tranquil fairytale forest, gentle golden afternoon light, cute girl and woodland friends resting on a mossy log listening calmly. Extremely soft and relaxing atmosphere, smooth slow animation.`

---

### SCENA 4: Wiaterek Fiufiu (`wiaterek`)

#### 10. `04_wiaterek.mp4` (Klip główny · ok. 55 s – punkt kulminacyjny)
- **Akcja:** Na skraju lasu i łąki pojawia się mały obłoczek Fiufiu. Ekscytuje się za bardzo: „Fiu-fiu-fiuuu!”, nadyma się i rośnie, dmuchając wichurą! Bzyczka wiruje w powietrzu, mapa odlatuje, Fiku trzyma się trawy. Lila zatrzymuje sytuację: „Fiufiu, każdy czasem ma wielkie emocje! Znamy na to sposób: spokojny oddech!”. Lila prowadzi ćwiczenie oddechowe z widownią: „Głęboki wdech nosem... i wydech buzią fffuuu...”. Fiufiu z każdym oddechem uspokaja się i maleje.
- **AI Video Prompt:**
  > `A cute fluffy white cartoon cloud creature named Fiufiu swirls joyfully across an open grassy meadow, puffing big gusty winds with swirling flower petals. The little bee tumbles playfully, the squirrel hugs a daisy stem. Lila raises her hands in a soothing calming gesture, demonstrating deep mindful breathing. The little cloud gradually shrinks down to miniature size, blushing softly. Children's book watercolor style.`

#### 11. `04_wiaterek_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Fiufiu unosi się w miejscu, rytmicznie powiększając się i zmniejszając w spokojnym tempie oddechu (4 sekundy wdech, 4 sekundy wydech). Lila i Fiku oddychają razem z nim. W rogu pulsuje lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless loop of a peaceful miniature puffy white cloud breathing smoothly in a rhythmic cycle (expand on inhale, gently contract on exhale). The girl Lila and the squirrel breathe in sync beside him against a serene sky with soft drifting petals. Calming, mindfulness, 2D watercolor animation.`

#### 12. `04_wiaterek_spokojna.mp4` (Wersja spokojna · ok. 55 s)
- **Akcja:** Wersja z mniej gwałtownym wiatrem, stonowanym ruchem i wydłużonymi ujęciami relaksacyjnymi.
- **AI Video Prompt:**
  > `Extremely calm and slow paced pacing, gentle zephyr across a wildflower field, serene cloud smiling peacefully, pastel watercolor aesthetics, very relaxing visual tone.`

---

### SCENA 5: Wybór Pomocnika (`pomocnik`)

#### 13. `05_pomocnik.mp4` (Klip główny · ok. 40 s)
- **Akcja:** Brzeg Kwiatowej Łąki w złotym popołudniowym słońcu. Łąka ciągnie się hen po horyzont. Pod wielką lipą w oddali majaczy mały kształt. Bzyczka mówi, że to jej ul, ale jest za daleko i nic nie widzi. Kuferek otwiera się z radosnym hasłem i unosi trzy pomocniki: Mapę, Latarkę i Lornetkę. Lila pyta: „Który pomocnik pomoże zobaczyć ul daleko na końcu łąki? Mapa, latarka czy lornetka?”.
- **AI Video Prompt:**
  > `Golden hour sunlit panoramic field of colorful blooming wildflowers extending to the distant horizon under an ancient linden tree. Bzyczka the bee squints her eyes trying to spot her home far away. The magical chest pops open displaying three hovering glowing items: a rolled map, a glowing brass lantern, and twin binoculars. Lila addresses the screen cheerfully.`

#### 14. `05_pomocnik_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Trzy pomocniki (Mapa, Latarka, Lornetka) unoszą się w powietrzu nad kuferkiem, po kolei delikatnie rozbłyskując złotą aureolką. W rogu pulsuje lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless looping animation of three magical adventure gadgets (paper map, lantern, binoculars) hovering above a wooden trunk, sequentially glowing with soft golden halo light. Blooming meadow background, sunny pastel watercolor.`

---

### SCENA 6: Ul na Kwiatowej Łące i Liczenie (`laka`)

#### 15. `06_laka.mp4` (Klip główny · ok. 40 s)
- **Akcja:** Najpierw widok z perspektywy lornetki (okrągły kadr, przybliżenie) na kolorowy drewniany ul pod kwitnącą lipą. Następnie dynamiczny przelot nad kwiatami prosto pod ul! Z ula wylatują z radosnym brzęczeniem trzy pszczółki – dwie siostry i brat Bzyczki! Krążą wesoło. Fiku liczy na palcach i się gubi. Lila prosi widownię: „Ile pszczółek wyleciało z ula, żeby przywitać Bzyczkę?”.
- **AI Video Prompt:**
  > `Binocular circular vignette zoom-in showing a charming hand-painted wooden beehive covered in honeysuckle flowers. Transition to ground view as three cute baby bees fly out of the hive entrance one by one with joyful buzz trails and stay hovering in distinct visible spots. Fiku scratches his head counting fingers, Lila turns to audience with an encouraging smile.`

#### 16. `06_laka_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Trzy pszczółki latają powoli w stałych, wyraźnych punktach kadru, unosząc się lekko góra-dół (tak, aby dzieci mogły je łatwo policzyć na ekranie). Kwiaty kołyszą się na wietrze. W rogu pulsuje lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless looping shot of three distinct little cartoon bees hovering calmly in fixed triangular positions in front of a rustic beehive, gently flapping their wings in place. Easy to count for kids, vibrant sunny watercolor painting.`

---

### SCENA 7: Świętowanie (`swieto`)

#### 17. `07_swieto.mp4` (Klip główny · ok. 30 s)
- **Akcja:** Złota godzina przed zachodem słońca. Wszyscy zgromadzeni przed ulem: cała rodzina pszczółek, Lila, Fiku, Kuferek i Wiaterek Fiufiu. Bzyczka dziękuje z całego serca: „Bzz-dziękuję!”. Fiku proponuje świętowanie. Lila pyta salę kinową: „Jak świętujemy powrót Bzyczki? Pszczółkowym tańcem czy piosenką o kwiatkach?”.
- **AI Video Prompt:**
  > `Sunset golden meadow party in front of the cheerful beehive. All characters together: Lila, squirrel Fiku with baker apron, bee Bzyczka and her bee siblings, smiling cloud Fiufiu, and the dancing chest. Golden light rays, happy celebratory atmosphere. Lila happily asks the audience to decide between dance and song.`

#### 18. `07_swieto_idle.mp4` (Pętla oczekiwania · ok. 6–8 s zapętlona)
- **Akcja:** Wszyscy bohaterowie kołyszą się w rytmicznym radosnym oczekiwaniu na odpowiedź widowni, Kuferek tupie nóżkami w trawie. W rogu pulsuje lupka.
- **Audio:** Cisza.
- **AI Video Prompt:**
  > `Seamless looping animation of all fairytale friends standing together swaying side to side in cheerful anticipation, festive sunset meadow backdrop, soft watercolor cartoon animation.`

#### 19. `07_swieto_spokojna.mp4` (Wersja spokojna · ok. 30 s)
- **Akcja:** Wolniejsze kołysanie, stonowane kolory zachodzącego słońca, ujęcie oparte na ciepłej relacji bohaterów.
- **AI Video Prompt:**
  > `Serene peaceful sunset celebration, warm gentle hues of orange and lilac, characters hugging and smiling softly without fast movements, tranquil aesthetic.`

---

### SCENA 8a: Finał z Tańcem Pszczółek (`koniec_taniec`)

#### 20. `08a_koniec_taniec.mp4` (Klip finałowy · ok. 75 s)
- **Akcja:** Bzyczka i jej rodzeństwo prowadzą radosny taniec pszczółek! Wszyscy podnoszą ręce („skrzydełka w górę!”), opuszczają („skrzydełka w dół!”), kręcą się w kółko i podskakują („i hop na kwiatek!”). Lila, Fiku i Fiufiu tańczą razem z nimi. Kamera oddala się ku niebu, ukazując całą kwitnącą łąkę. Pojawiają się napisy końcowe i podziękowanie dla małych odkrywców z Klubu Ciekawskich.
- **AI Video Prompt:**
  > `Joyful lively cartoon bee dance sequence on a sunset meadow. All characters flap their arms like wings, spin in circles, and jump playfully on giant blooming flowers. High-angle crane shot slowly pulling back into the colorful twilight sky showing the whole flourishing countryside. Credit titles softly rolling, uplifting, magical and happy children's book finale.`

---

### SCENA 8b: Finał z Piosenką o Kwiatkach (`koniec_piosenka`)

#### 21. `08b_koniec_piosenka.mp4` (Klip finałowy · ok. 75 s)
- **Akcja:** Lila wyjmuje małe drewniane dzwoneczki, Fiku gra na łupince żołędzia, Kuferek rytmicznie postukuje wiekiem. Wszyscy śpiewają melodyjną, pogodną piosenkę o kwiatkach i przyjaźni. Kwiaty na łące otwierają kielichy i mienią się pyłkiem. Kamera unosi się ku gwiazdom, które układają się w kształt lupy Lili. Napisy końcowe.
- **AI Video Prompt:**
  > `Musical musical finale in a magical twilight meadow. Lila plays tiny wooden bells, the squirrel taps an acorn drum, bees flutter harmoniously in musical notes pattern. Luminescent pollen glows like starry fireflies as the camera rises into the starry night sky forming a constellation of a magnifying glass. Warm touching storybook conclusion with rolling end credits.`

---

## 🛠️ Podsumowanie checklisty plików MP4

| # | Nazwa pliku w `scenarios/clips/klub_ciekawskich/` | Typ | Długość | Dźwięk |
|---|---|---|---|---|
| 1 | `01_powitanie.mp4` | Klip sceny | ~70 s | Dialogi + muzyka |
| 2 | `01_powitanie_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 3 | `02_kuferek.mp4` | Klip sceny | ~45 s | Dialogi + muzyka |
| 4 | `02_kuferek_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 5 | `03a_most.mp4` | Klip sceny | ~40 s | Dialogi + muzyka |
| 6 | `03a_most_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 7 | `03b_las.mp4` | Klip sceny | ~40 s | Dialogi + efekty dźwiękowe |
| 8 | `03b_las_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 9 | `03b_las_spokojna.mp4` | Wariant tętna | ~40 s | Spokojna muzyka |
| 10 | `04_wiaterek.mp4` | Klip sceny | ~55 s | Dialogi + szum wiatru |
| 11 | `04_wiaterek_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 12 | `04_wiaterek_spokojna.mp4` | Wariant tętna | ~55 s | Kojący szum |
| 13 | `05_pomocnik.mp4` | Klip sceny | ~40 s | Dialogi + muzyka |
| 14 | `05_pomocnik_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 15 | `06_laka.mp4` | Klip sceny | ~40 s | Dialogi + brzęczenie pszczół |
| 16 | `06_laka_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 17 | `07_swieto.mp4` | Klip sceny | ~30 s | Dialogi + radosna muzyka |
| 18 | `07_swieto_idle.mp4` | Pętla idle | 6–8 s loop | **Cisza** |
| 19 | `07_swieto_spokojna.mp4` | Wariant tętna | ~30 s | Spokojna muzyka |
| 20 | `08a_koniec_taniec.mp4` | Finał | ~75 s | Piosenka taneczna + napisy |
| 21 | `08b_koniec_piosenka.mp4` | Finał | ~75 s | Piosenka finałowa + napisy |

# YouTrak

Lokalna aplikacja do zapisywania piosenek z YouTube jako plików MP3 na własny użytek.
Ciemny interfejs z turkusowym akcentem, własna ikona aplikacji (`assets/icon.ico`).

## Dlaczego to jest bezpieczne

- Cały kod źródłowy jest w `app.py` — możesz go przeczytać w całości.
- Jedyne biblioteki: `yt-dlp` (aktywnie rozwijany fork youtube-dl, standard branżowy)
  i `imageio-ffmpeg` (oficjalna, statyczna binarka ffmpeg dystrybuowana przez PyPI).
- Program nie łączy się z żadnym serwerem poza YouTube. Brak reklam, brak
  "instalatorów", brak telemetrii — w przeciwieństwie do gotowych "yt2mp3.exe"
  z losowych stron, które bywają nośnikiem malware/adware.
- `.exe` budujesz sam z tego kodu (patrz niżej), więc wiesz dokładnie co w nim jest.

## Użycie (z gotowym .exe)

1. Uruchom `dist\YouTrak.exe`.
2. Wklej link do YouTube.
3. Wybierz folder docelowy (domyślnie `Dokumenty\Music\YouTrak`) i jakość MP3.
4. Kliknij "Pobierz jako MP3". Plik pojawi się w wybranym folderze z osadzoną
   okładką i metadanymi (tytuł, wykonawca).
5. Zaznacz opcję playlisty, jeśli link prowadzi do całej playlisty/albumu.

## Budowanie .exe od nowa

```powershell
cd YouTrack
.\build.ps1
```

Plik wynikowy: `dist\YouTrak.exe` (samodzielny, nie wymaga instalacji Pythona
na docelowym komputerze).

## Aktualizacja yt-dlp

YouTube często zmienia swoje mechanizmy, więc `yt-dlp` wymaga okresowych
aktualizacji:

```powershell
.\venv\Scripts\python.exe -m pip install -U yt-dlp
.\build.ps1
```

## Zastrzeżenie prawne

**Ten kod jest bezpieczny do publikacji i udostępniania.** Narzędzie jest
GUI-nakładką na `yt-dlp` — analogiczne aplikacje istnieją publicznie na
GitHubie w dziesiątkach wariantów. Sam `yt-dlp` (i jego poprzednik,
`youtube-dl`) przetrwał próbę usunięcia przez RIAA na drodze DMCA w 2020 r. —
GitHub po analizie prawnej przywrócił repozytorium, uznając, że samo
narzędzie do pobierania nie hostuje ani nie rozpowszechnia treści chronionych
prawem autorskim, więc nie narusza go samo w sobie.

**Odpowiedzialność leży po stronie sposobu użycia, nie kodu:**

- Regulamin YouTube zabrania pobierania treści bez zgody właściciela praw
  (poza wyjątkami: własne materiały, licencja Creative Commons, oficjalny
  przycisk pobierania YouTube).
- W Polsce dozwolony użytek osobisty (art. 23 ustawy o prawie autorskim)
  pozwala na pewien zakres kopiowania na własny użytek, ale jego zastosowanie
  do pobierania z serwisów streamingowych jest prawnie niejednoznaczne —
  zwłaszcza gdy łamie to zabezpieczenia techniczne lub regulamin platformy.
- Pobieraj wyłącznie treści, do których masz prawo: własne nagrania, muzykę
  na licencji Creative Commons / royalty-free, lub materiały z wyraźną zgodą
  właściciela praw.

**Jeśli pokazujesz działanie aplikacji publicznie** (film na YouTube, demo,
prezentacja) — użyj do tego utworu na licencji Creative Commons lub
własnego nagrania, a nie popularnego, komercyjnego hitu. Publiczna
demonstracja pobierania chronionego utworu może skutkować usunięciem filmu
przez system Content ID/DMCA, niezależnie od tego, czy sam kod narzędzia jest
legalny.

**Nie publikuj i nie rozpowszechniaj już pobranych plików MP3** — to inna
kategoria ryzyka niż udostępnianie kodu: bezpośrednie rozpowszechnianie
treści chronionych prawem autorskim.

To nie jest formalna porada prawna — przepisy i ich interpretacja różnią się
w zależności od jurysdykcji.

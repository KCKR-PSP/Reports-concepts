# Koncepcje Reports

Klikalne koncepcje ekranów aplikacji Reports, do przejrzenia przez użytkowników przed wdrożeniem. To statyczna strona:
HTML, CSS i jeden plik JavaScript, bez serwera, bez kont i bez zapisywania danych. Każda zmiana wprowadzona na stronie
znika po odświeżeniu.

**Wszystkie dane na planszach są przykładowe** (jednostki, osoby, numery decyzji). Strona nie łączy się z Reports ani
z SWD-PSP.

## Zawartość

| Koncepcja | Strony |
|---|---|
| Karta jednostki OSP KSRG | `osp-ksrg/karta.html` (karta jednostki), `osp-ksrg/wnioski.html` (kreator i obieg wniosku KSRG) |
| Działania międzynarodowe | `dzialania-miedzynarodowe/index.html`: wybór poziomu (KG PSP, KW PSP Poznań, KP PSP Chodzież, członek modułu), dalej moduły GFFF, GFFFV, USAR, DSIM i HCP klikalne jak w aplikacji; poziom zmienia pasek „Widok”. Dokumenty wyjazdu (XLSX, PDF) w `dzialania-miedzynarodowe/dokumenty/`. Stary adres `grupy-miedzynarodowe/` przekierowuje |

Na górze każdej strony jest pasek koncepcji z przełącznikami:
- motyw (jasny, ciemny);
- na karcie: stan danych i stopień zagrożenia gminy;
- na wnioskach: widok KP, KW albo KG PSP, który odblokowuje czynności danego poziomu.

## Struktura

```text
index.html             lista koncepcji (generowana)
osp-ksrg/*.html        strony koncepcji (generowane)
assets/dc-runtime.js   mały silnik plansz: {{ }}, sc-for, sc-if, onClick/onChange, setState
src/<koncepcja>/       plansze źródłowe (.dc.html) wyeksportowane z kanwy
tools/build.py         generator stron
tools/concepts.json    lista koncepcji, plansz i przełączników
```

## Aktualizacja koncepcji

1. Podmień plansze w `src/<koncepcja>/` na aktualne pliki `.dc.html` z kanwy.
2. Zbuduj strony (wymaga tylko Pythona 3.9+):

   ```bash
   python3 tools/build.py
   ```

3. Otwórz stronę lokalnie, np. `python3 -m http.server 8000`, i przeklikaj zmienione plansze.
4. Zatwierdź źródła i wygenerowane strony w jednym commicie.

Nową koncepcję dodaje się w `tools/concepts.json`: `id` (katalog), tytuł, opis i lista plansz (`source`, `page`,
`title`, opcjonalnie `controls`, czyli przełączniki z `data-props` planszy).

## Publikacja (GitHub Pages)

Strona działa z dowolnej ścieżki, bo wszystkie odnośniki są względne. Do publikacji wystarczy włączyć GitHub Pages
z gałęzi `main` i katalogu głównego (`/`). Plik `.nojekyll` wyłącza przetwarzanie przez Jekyll.

- Adres `https://kgpsp.github.io/<repozytorium>/` wymaga publicznego repozytorium w organizacji **KGPSP**.
- To repozytorium (`KCKR-PSP/Reports-concepts`) jest prywatne. Na planie Free GitHub Pages działa tylko dla repozytoriów
  publicznych, a strona byłaby pod adresem `kckr-psp.github.io`.

Strona ma `noindex`, więc nie powinna trafiać do wyszukiwarek. Nie chroni to jednak dostępu: każdy, kto zna adres,
może ją otworzyć.

# 🚴‍♂️ Sporza Wielermanager AI - Project Context & Documentatie

## 📌 Project Overzicht
Dit project is een hybride AI-gedreven beslissingsondersteunend systeem voor de Sporza Wielermanager. Het combineert een menselijk gecureerde basis-dataset met live web-scraping, berekent verwachte punten op basis van historische data, en gebruikt lineaire programmering (PuLP) om de optimale transferstrategie (korte termijn en een seizoens-masterplan) te berekenen.

## 📂 Bestandsstructuur & Data Flow
1. **`Copy of De Sporza Wielermanager - Wielermatrix.csv`**: De brondata. Een extern bijgehouden lijst met voorlopige startlijsten per koers (1 = start, 0 of leeg = start niet).
2. **`pcs_scraper.py`**: Verrijkt de brondata door live ProCyclingStats (PCS) te scrapen op ontbrekende renners.
3. **`maak_matrix.py`**: De "Rekenmotor". Combineert de startlijsten met een historische database (`wielermanager.db`) om de verwachte punten per renner per koers te berekenen. Output: `Wielermanager_Matrix_Berekend.csv`.
4. **`app.py`**: De Streamlit web-applicatie. Leest beide CSV's in, past filterlogica toe en lost het wiskundige optimalisatieprobleem op.
5. **`controlepaneel.py`**: Een Tkinter GUI die dient als dashboard om de scripts (scraper, matrix, app) opeenvolgend te draaien zonder terminal-commando's.

---

## ⚙️ Gedetailleerde Script Logica

### 1. `pcs_scraper.py` (De Web Scraper)
**Doel:** Het automatisch ophalen van actuele startlijsten om de hybride brondata aan te vullen.
**Logica & Beveiligingen:**
* Gebruikt `cloudscraper` en `BeautifulSoup` om PCS te scrapen (omzeilt simpele bot-protectie).
* **Anti-Sidebar Bug:** Zoekt expliciet alléén in de `<div class='page-content'>` of `<div class='content'>` om te voorkomen dat renners uit de "Trending Riders" zijbalk (zoals Pogačar of Van Aert) onterecht als deelnemer worden gemarkeerd.
* **Naam-Normalisatie:** Verwijdert stopwoorden ('van', 'de', 'der') en leestekens om robuuste matches te maken tussen de CSV-namen en PCS-URL's. Vereist een overlap van minimaal 2 woorden.
* **Non-Destructief:** Overschrijft nooit een bestaande `1` in de CSV naar een `0`. Voegt enkel nieuwe waarden toe via `max(huidige_waarde, rijdt_mee)`.

### 2. `maak_matrix.py` (De Rekenmotor)
**Doel:** Genereren van de matrix met verwachte punten (`Wielermanager_Matrix_Berekend.csv`).
**Logica & Beveiligingen:**
* **Naam-Mapping Fix:** Verwijdert via regex (`re.sub(r'\d+', '', str(rid))`) nummers achter PCS-id's (bijv. `romain-gregoire1` wordt `romain-gregoire`) zodat renners met naamgenoten in het verleden feilloos aan de database worden gekoppeld.
* **De "3-Traps Raket" (Startkans Bepaling):**
    1. Staat er een `1` in de hybride CSV? -> Kans = `100%`.
    2. Heeft een koers >40 deelnemers in de CSV (definitieve lijst), maar staat de renner er niet op? -> Kans = `0%`.
    3. Heeft de koers <40 deelnemers (Blinde Vlek)? -> Kijk naar historische deelnamekans.
* **Fallback voor Talenten/Neo-profs:** Als een renner wel in de CSV staat als starter, maar geen historische data heeft (geen match in DB), krijgt deze niet 0 punten, maar een berekende 'rookie-score' op basis van het peloton-gemiddelde.

### 3. `app.py` (De Streamlit Optimizer)
**Doel:** De gebruikersinterface en de AI-solver (Masterplan).
**Logica & Beveiligingen:**
* **Blinde Vlek Detectie & Slider:** De app vergelijkt de berekende matrix met de ruwe data. Als een koers <40 bekende starters heeft, wordt de `historisch_vertrouwen` slider actief, waarmee de berekende punten vermenigvuldigd worden.
* **Anti-Opvulling (Knapsack Fodder):** Een slider (`min_verwachte_punten`) verbiedt het model om nutteloze renners van 3M die 0 punten pakken te kopen, puur om budget vrij te maken voor een topper.
* **Transfer-Efficiëntie Eis (Myopic Greed Preventie):** In Tab 2 trekt de solver virtueel strafpunten (bijv. 25pt) af per uitgevoerde transfer. Dit forceert de AI om langetermijninvesteringen te doen en voorkomt het zinloos roteren van eendagsvliegen.
* **Exponentiële Strafpunten (Linear Convex Hull):** In de Sporza manager lopen transferkosten op (1e = 1M, 2e = 2M, totaal = 3M). Omdat PuLP lineair is, is dit gemodelleerd via een *Piece-wise Linear Convex Hull* iteratie in de constraints: `prob += penalty[t] >= k * paid_transfers[t] - (k * (k - 1)) / 2`.
* **Gantt Chart UI:** Toont de seizoensplanning met duidelijke status per renner:
    * 👑: Actief als Kopman (x2 punten).
    * 🟢: Actief in team (normale punten).
    * ☕: Zit in team, fietst niet, maar wordt gehouden om transfers te besparen ("stashing").
* *UI Note:* Gebruikt `width='stretch'` bij `st.dataframe` i.p.v. het verouderde `use_container_width`.

### 4. `controlepaneel.py` (De UI Shell)
**Doel:** Een gebruiksvriendelijk dashboard om de command-line scripts te bypassen.
**Logica:**
* Geschreven in `tkinter`.
* Gebruikt `threading` zodat de UI responsief blijft tijdens het runnen van zware Python processen op de achtergrond.
* Stelt de environment variabele `PYTHONIOENCODING=utf-8` in via `os.environ.copy()` zodat de terminal-output emoji's (zoals 🚴‍♂️ en 👑) correct naar de Tkinter `ScrolledText` widget kan printen zonder `UnicodeEncodeError` crashes op Windows.

---

## 🧠 AI Prompting Guidelines (Voor gebruik binnen Antigravity/Cursor)
Als je wijzigingen aanbrengt in dit project, respecteer dan de volgende regels:
1. **Behoud het Hybride Data Model:** Vertrouw op de ruwe CSV als waarheid, gebruik de scraper enkel als toevoeging. Overschrijf nooit handmatige waarden naar 0.
2. **PuLP Constraints:** Wees extreem voorzichtig met het toevoegen van wiskundige constraints in `app.py`. Zorg dat ze lineair blijven. Gebruik de bestaande variabelen (`x` voor team, `c` voor kopman, `transfer_in` voor wijzigingen).
3. **Naamgeving:** Namen moeten consistent blijven tussen de CSV, PCS en de database. Behoud altijd de filter voor `stopwoorden` en regex voor nummers.
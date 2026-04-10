# 🚴‍♂️ Sporza Wielermanager — Claude Instructions

## 📌 Project Overview
This is a hybrid AI-driven decision-support system for the Sporza Wielermanager fantasy cycling game. It combines a human-curated base dataset with live web scraping, calculates expected points from historical data, and uses linear programming (PuLP) to compute the optimal transfer strategy (short-term and a season master plan).

## 📂 File Structure & Data Flow
1. **`Copy of De Sporza Wielermanager - Wielermatrix.csv`** — Source data. An externally maintained list of preliminary start lists per race (1 = starts, 0 or blank = does not start).
2. **`pcs_scraper.py`** — Enriches the source data by live-scraping ProCyclingStats (PCS) for missing riders.
3. **`maak_matrix.py`** — The "Calculation Engine". Combines start lists with a historical database (`wielermanager.db`) to compute expected points per rider per race. Output: `Wielermanager_Matrix_Berekend.csv`.
4. **`app.py`** — The Streamlit web app. Reads both CSVs, applies filter logic, and solves the mathematical optimization problem.
5. **`controlepaneel.py`** — A Tkinter GUI dashboard to run the scripts (scraper, matrix, app) sequentially without terminal commands.

---

## ⚙️ Key Script Logic & Guardrails

### `pcs_scraper.py`
- Uses `cloudscraper` + `BeautifulSoup` to scrape PCS (bypasses simple bot protection).
- **Anti-Sidebar Bug:** Only searches inside `<div class='page-content'>` or `<div class='content'>` to prevent sidebar riders (e.g. Pogačar, Van Aert) from being falsely marked as starters.
- **Name Normalization:** Strips stopwords (`van`, `de`, `der`) and punctuation; requires a minimum 2-word overlap between CSV names and PCS URLs.
- **Non-Destructive:** Never overwrites an existing `1` in the CSV with `0`. Only adds values via `max(current_value, riding)`.

### `maak_matrix.py`
- **Name-Mapping Fix:** Uses regex (`re.sub(r'\d+', '', str(rid))`) to strip trailing numbers from PCS IDs (e.g. `romain-gregoire1` → `romain-gregoire`).
- **"3-Stage Rocket" (Start Probability):**
  1. If the hybrid CSV has a `1` → probability = `100%`.
  2. If a race has >40 riders in the CSV (definitive list) but a rider isn't on it → probability = `0%`.
  3. If a race has <40 riders (Blind Spot) → use historical participation probability.
- **Rookie Fallback:** Riders with no historical data but confirmed as starters get a calculated rookie score based on the peloton average.
- **Bookie Odds Bonus (dominant signal):** Loads `bookie_odds_<KOERS>.json` files. Uses both **Winner** and **Top 3** markets to compute expected Sporza points from implied probabilities (`P(1st) * pts_1st + P(2nd|3rd) * avg(pts_2,pts_3)`). Applied with `BOOKIE_WEIGHT = 3.0` (tunable), designed to dominate historical data when available. Only affects races for which a JSON file exists.

### `app.py`
- **Blind Spot Detection & Slider:** Compares the computed matrix with raw data. If a race has <40 known starters, `historisch_vertrouwen` slider becomes active to scale expected points.
- **Anti-Padding (Knapsack Fodder):** `min_verwachte_punten` slider prevents the model from buying 3M zero-point riders just to free budget.
- **Transfer Efficiency (Myopic Greed Prevention):** Tab 2 deducts virtual penalty points (e.g. 25pt) per transfer, forcing long-term investments.
- **Exponential Transfer Costs (Piece-wise Linear Convex Hull):** Models Sporza's escalating transfer costs (1st = 1M, 2nd = 2M, total = 3M) via: `prob += penalty[t] >= k * paid_transfers[t] - (k * (k - 1)) / 2`.
- **Gantt Chart UI:** Season overview per rider — 👑 Kopman (×2 pts), 🟢 Active, ☕ Stashed.
- Use `width='stretch'` on `st.dataframe`, not the deprecated `use_container_width`.

### `controlepaneel.py`
- Written in `tkinter` with `threading` to keep the UI responsive.
- Sets `PYTHONIOENCODING=utf-8` via `os.environ.copy()` so emoji output (🚴‍♂️, 👑) prints correctly to the `ScrolledText` widget without `UnicodeEncodeError` on Windows.

---

## 🧠 AI Coding Rules (Always Respect These)
1. **Preserve the Hybrid Data Model:** Treat the raw CSV as ground truth. The scraper only adds data — never overwrite manual `1` values with `0`.
2. **PuLP Constraints:** Be extremely careful when adding mathematical constraints in `app.py`. Keep them linear. Use existing variables: `x` (team), `c` (kopman), `transfer_in` (changes).
3. **Name Consistency:** Names must stay consistent across CSV, PCS, and the database. Always keep the `stopwoorden` filter and the regex for trailing numbers.
4. **Bookie Odds:** One JSON file per race (`bookie_odds_<KOERS>.json`). Only use the `Winner` and `Top 3` markets. The bonus is additive to the historical score. Never modify `update_huidige_vorm.py` with odds data — odds are a prediction signal, not historical results.

---

## 🚫 Ignored Paths
Always **ignore** the `backups/` folder and any of its contents for all purposes:
- Do NOT read, index, or include files from `backups/` as context
- Do NOT suggest changes to files inside `backups/`
- Do NOT reference or surface files from `backups/` in responses
- Treat `backups/` as if it does not exist

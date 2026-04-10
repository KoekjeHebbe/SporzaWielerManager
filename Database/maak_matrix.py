import sqlite3
import pandas as pd
import unicodedata
import re
import json
import glob

print("Stap 1: Database inlezen en Sporza-koersen herkennen...")

connectie = sqlite3.connect('wielermanager.db')
df_uitslagen = pd.read_sql_query("SELECT * FROM historische_uitslagen", connectie)
try:
    df_top_comp = pd.read_sql_query("SELECT * FROM pcs_top_competitors WHERE year = 2026", connectie)
except Exception:
    df_top_comp = pd.DataFrame(columns=['rider_name', 'pcs_points', 'koers_code'])
connectie.close()

pts_monument = {1:125, 2:100, 3:80, 4:70, 5:60, 6:55, 7:50, 8:45, 9:40, 10:37, 
                11:34, 12:31, 13:28, 14:25, 15:22, 16:20, 17:18, 18:16, 19:14, 20:12,
                21:10, 22:9, 23:8, 24:7, 25:6, 26:5, 27:4, 28:3, 29:2, 30:1}

pts_wt = {1:100, 2:80, 3:65, 4:55, 5:48, 6:44, 7:40, 8:36, 9:32, 10:30, 
          11:27, 12:24, 13:22, 14:20, 15:18, 16:16, 17:14, 18:12, 19:10, 20:9,
          21:8, 22:7, 23:6, 24:5, 25:4, 26:3, 27:2, 28:2, 29:1, 30:1}

pts_pro = {1:80, 2:64, 3:52, 4:44, 5:38, 6:35, 7:32, 8:29, 9:26, 10:24, 
           11:22, 12:20, 13:18, 14:16, 15:14, 16:12, 17:11, 18:10, 19:9, 20:8,
           21:7, 22:6, 23:5, 24:4, 25:3, 26:3, 27:2, 28:2, 29:1, 30:1}

koers_mapping = {
    'OML': ('nieuwsblad', 100, pts_wt), 'KBK': ('kuurne', 80, pts_pro), 'SAM': ('samyn', 80, pts_pro),
    'STRADE': ('strade', 100, pts_wt), 'NK': ('nokere', 80, pts_pro), 'BKC': ('bredene', 80, pts_pro),
    'MSR': ('sanremo', 125, pts_monument), 'RVB': ('panne', 100, pts_wt), 'E3': ('e3', 100, pts_wt),
    'GW': ('wevelgem', 100, pts_wt), 'DDV': ('dwars door', 100, pts_wt), 'RVV': ('vlaanderen - tour', 125, pts_monument), 
    'SCHELD': ('scheldeprijs', 80, pts_pro), 'PR': ('roubaix', 125, pts_monument), 'RVL': ('frankfurt', 100, pts_wt), 
    'BP': ('brabantse', 80, pts_pro), 'AG': ('amstel', 100, pts_wt), 'WP': ('wallonne', 100, pts_wt), 'LBL': ('bastogne', 125, pts_monument)
}

def bepaal_race(race_naam):
    race_naam_lower = str(race_naam).lower()
    
    # --- FILTER 1: Negeert classificatie-rijen (GC, Youth, Points, KOM) ---
    # PCS scrape bevat rijen als "Youth classificationYouth classification" etc.
    classificatie_markers = ['classification', 'classement']
    if any(marker in race_naam_lower for marker in classificatie_markers):
        return None, 0, {}
    
    # --- FILTER 2: Negeert U23/Junior versies van koersen ---
    # "Liège-Bastogne-Liège MU (1.2U)" is NIET hetzelfde als LBL!
    junior_markers = ['junior', '(1.2u)', '(2.2u)', '(1.1u)', '(2.1u)', ' mu ', ' mu(', ' mj ', ' mj(', 'under 23', 'u23']
    if any(marker in race_naam_lower for marker in junior_markers):
        return None, 0, {}
    
    for code, (keyword, max_p, p_dict) in koers_mapping.items():
        if keyword in race_naam_lower:
            return code, max_p, p_dict
    return None, 0, {}

types, max_pts = [], []
for _, row in df_uitslagen.iterrows():
    k_code, mp, _ = bepaal_race(row['Race'])
    types.append(k_code)
    max_pts.append(mp)

df_uitslagen['koers_code'] = types
df_uitslagen['max_points'] = max_pts
df_sporza_all = df_uitslagen[df_uitslagen['koers_code'].notnull()].copy()

print("Stap 2: Historische DEELNAME-KANS berekenen...")

df_sporza_all['year'] = pd.to_numeric(df_sporza_all['year'], errors='coerce').fillna(2026).astype(int)
df_recent = df_sporza_all[df_sporza_all['year'] >= 2024].copy()
df_starts = df_recent[~df_recent['Result'].astype(str).str.contains('DNS', na=False, case=False)]
years_active = df_starts.groupby('rider_id')['year'].nunique().to_dict()
starts_per_race = df_starts.groupby(['rider_id', 'koers_code'])['year'].nunique()

prob_dict = {}
for (rid, koers), starts in starts_per_race.items():
    act_years = years_active.get(rid, 3)
    if act_years == 0: act_years = 1
    prob_dict[(rid, koers)] = min(1.0, starts / act_years)

print("Stap 3: Historische VORM (Punten) berekenen...")

df_sporza_punten = df_sporza_all.copy()
df_sporza_punten['Result'] = pd.to_numeric(df_sporza_punten['Result'], errors='coerce')
df_sporza_punten = df_sporza_punten.dropna(subset=['Result'])
df_sporza_punten['Result'] = df_sporza_punten['Result'].astype(int)

earned = []
for _, row in df_sporza_punten.iterrows():
    k_code, _, p_dict = bepaal_race(row['Race'])
    earned.append(p_dict.get(row['Result'], 0))
df_sporza_punten['earned_points'] = earned

gewichten = {2026: 4, 2025: 2, 2024: 1}
df_sporza_punten['weight'] = df_sporza_punten['year'].map(gewichten).fillna(0)
df_sporza_punten['weighted_earned'] = df_sporza_punten['earned_points'] * df_sporza_punten['weight']
df_sporza_punten['weighted_max'] = df_sporza_punten['max_points'] * df_sporza_punten['weight']

global_stats = df_sporza_punten.groupby('rider_id')[['weighted_earned', 'weighted_max']].sum()
avg_peloton_qual = df_sporza_punten['weighted_earned'].sum() / df_sporza_punten['weighted_max'].sum()
demping_global = 200
global_quality = ((global_stats['weighted_earned'] + avg_peloton_qual * demping_global) / 
                  (global_stats['weighted_max'] + demping_global)).to_dict()

# --- ERVARINGSKORTING (Experience Discount) ---
# Jonge renners met weinig historische data worden afgestraft.
# Een renner heeft ~2000 weighted_max nodig om als 'ervaren' te gelden 
# (bijv. 10 koersen/jaar x 2-3 jaar x gemiddeld 100 max_pts per koers).
# Onder die drempel wordt hun kwaliteit proportioneel verlaagd.
ERVARINGS_DREMPEL = 2000
global_weighted_max = global_stats['weighted_max'].to_dict()
for rid in global_quality:
    wmx = global_weighted_max.get(rid, 0)
    ervarings_factor = min(1.0, wmx / ERVARINGS_DREMPEL)
    global_quality[rid] *= ervarings_factor

race_stats = df_sporza_punten.groupby(['rider_id', 'koers_code'])[['weighted_earned', 'weight']].sum()
dict_specific_earned = race_stats['weighted_earned'].to_dict()
dict_specific_weight = race_stats['weight'].to_dict()

print("Stap 4: CSV inlezen en de '3-Traps Raket' toepassen...")

bestand_naam = "Copy of De Sporza Wielermanager - Wielermatrix.csv"
try:
    # Probeer het eerst als 'schoon' bestand (zonder de 11 lege rijen)
    df_csv = pd.read_csv(bestand_naam)
    
    # Als de kolom 'Naam' niet bestaat, staan de 11 lege rijen er nog wel in
    if 'Naam' not in df_csv.columns:
        df_csv = pd.read_csv(bestand_naam, skiprows=11)
        
    if 'Naam' not in df_csv.columns:
        print("\n❌ Fout: Kan de kolom 'Naam' écht niet vinden. Controleer je bestand!")
        exit()
        
except FileNotFoundError:
    print(f"\n❌ Kan '{bestand_naam}' niet vinden. Controleer de naam!")
    exit()

# --- DE FIX VOOR NAMEN (Stopwoorden filter) ---
stopwoorden = {'van', 'der', 'de', 'den', 'het', 'ten', 'ter', 'le', 'la', 'du', 'des', 'di', 'da', 'del', 'dos'}

def normaliseer_naam(naam):
    naam = ''.join(c for c in unicodedata.normalize('NFD', str(naam)) if unicodedata.category(c) != 'Mn')
    return set(re.sub(r'[^a-z\s]', '', naam.lower()).split()) - stopwoorden

# --- PCS TOP COMPETITORS VOORBEREIDEN ---
top_comp_norm_dict = {}
for _, row in df_top_comp.iterrows():
    if pd.isna(row['rider_name']): continue
    k_code = row['koers_code']
    pts = pd.to_numeric(row['pcs_points'], errors='coerce')
    if pd.isna(pts): pts = 0
    rn_parts = normaliseer_naam(row['rider_name'])
    
    if k_code not in top_comp_norm_dict:
        top_comp_norm_dict[k_code] = []
    top_comp_norm_dict[k_code].append({'parts': rn_parts, 'points': pts})

# NIEUW: Haal getallen weg uit de PCS IDs (bijv. 'romain-gregoire1' wordt 'romain-gregoire')
pcs_parts_dict = {}
for rid in global_quality.keys():
    schone_id = re.sub(r'\d+', '', str(rid)) 
    pcs_parts_dict[rid] = set(schone_id.split('-')) - stopwoorden
mapped_ids = []

for naam in df_csv['Naam']:
    if pd.isna(naam):
        mapped_ids.append(None)
        continue
    csv_parts = normaliseer_naam(naam)
    best_match, max_overlap = None, 0
    for rid, pcs_parts in pcs_parts_dict.items():
        overlap = len(csv_parts.intersection(pcs_parts))
        if overlap > max_overlap:
            max_overlap = overlap
            best_match = rid
            
    # Eis minimaal 2 matchende unieke woorden (voornaam + achternaam)
    mapped_ids.append(best_match if max_overlap >= min(2, len(csv_parts)) else None)

df_csv['rider_id'] = mapped_ids

koersen_lijst = list(koers_mapping.keys())
bestaande_koersen = [k for k in koersen_lijst if k in df_csv.columns]

# --- 1. ACTIEF FILTER ---
for k in bestaande_koersen:
    df_csv[k] = pd.to_numeric(df_csv[k], errors='coerce').fillna(0)
df_csv['Actief_Dit_Voorjaar'] = df_csv[bestaande_koersen].sum(axis=1) > 0
actief_array = df_csv['Actief_Dit_Voorjaar'].values

# --- 1b. BOOKIE ODDS LADEN ---
BOOKIE_WEIGHT = 3.0  # Hoe zwaar bookie odds meewegen vs. historische data (dominant)
bookie_data = {}  # { koers_code: { 'winner': {frozenset: implied_prob}, 'top3': {frozenset: implied_prob} } }

for pad in glob.glob("bookie_odds_*.json"):
    try:
        with open(pad, encoding='utf-8') as f:
            data = json.load(f)
        koers = data['koers_code']
        bookie_data[koers] = {'winner': {}, 'top3': {}}

        for entry in data['markets'].get('Winner', []):
            parts = frozenset(normaliseer_naam(entry['name']))
            bookie_data[koers]['winner'][parts] = 1.0 / entry['price']

        for entry in data['markets'].get('Top 3', []):
            parts = frozenset(normaliseer_naam(entry['name']))
            bookie_data[koers]['top3'][parts] = 1.0 / entry['price']

        print(f"  \U0001f4ca Bookie odds geladen voor {koers}: {len(bookie_data[koers]['winner'])} renners (Winner), {len(bookie_data[koers]['top3'])} renners (Top 3)")
    except Exception as e:
        print(f"  \u26a0\ufe0f Fout bij laden bookie odds uit {pad}: {e}")

if bookie_data:
    print(f"  Bookie weight ingesteld op {BOOKIE_WEIGHT}x (dominant over historische data)")
else:
    print("  Geen bookie odds bestanden gevonden (bookie_odds_*.json).")

# --- 2. DEFINITIEVE STARTLIJSTEN ---
# Pas als de externe CSV écht vol begint te lopen (>40 namen), beschouwen we de lijst als definitief.
definitieve_koersen = [k for k in bestaande_koersen if df_csv[k].sum() > 40]

demping_race = 2 

for koers, (_, max_p, p_dict_koers) in koers_mapping.items():
    if koers in df_csv.columns:
        deelnames_csv = df_csv[koers].values
        nieuwe_kolom = []
        
        for idx, row in df_csv.iterrows():
            rid = row['rider_id']
            if not rid:
                nieuwe_kolom.append(0)
                continue
                
            # Bereken zijn verwachte punten (indien hij zou starten)
            qual = global_quality.get(rid, avg_peloton_qual * 0.1)  # Onbekende renners: zeer lage verwachting
            fallback_earned = qual * max_p * demping_race
            actual_earned = dict_specific_earned.get((rid, koers), 0)
            actual_weight = dict_specific_weight.get((rid, koers), 0)
            verwachte_score_bij_start = (actual_earned + fallback_earned) / (actual_weight + demping_race)
            
            # --- BONUS PCS TOP COMPETITOR ---
            pcs_bonus_punten = 0
            if koers in top_comp_norm_dict and not pd.isna(row['Naam']):
                rij_csv_parts = normaliseer_naam(row['Naam'])
                for tc in top_comp_norm_dict[koers]:
                    overlap = len(rij_csv_parts.intersection(tc['parts']))
                    if overlap >= min(2, len(rij_csv_parts)):
                        pcs_bonus_punten = tc['points']
                        break
            
            # Voeg een procentuele bonus toe in plaats van een ruwe vermenigvuldiging.
            # Max score op PCS ligt rond de 5000 punten voor absolute goden. 
            # We creëren hier een factor (pcs / 5000) en vermenigvuldigen dat met de maximale race bonus (15% van totale race punten).
            if pcs_bonus_punten > 0:
                relatieve_sterkte = pcs_bonus_punten / 5000.0
                maximale_bonus = max_p * 0.25
                uiteindelijke_pcs_bonus = relatieve_sterkte * maximale_bonus
                verwachte_score_bij_start += uiteindelijke_pcs_bonus

            # --- BOOKIE ODDS BONUS ---
            bookie_bonus = 0
            if koers in bookie_data and not pd.isna(row['Naam']):
                csv_parts = frozenset(normaliseer_naam(row['Naam']))
                win_prob = 0
                top3_prob = 0
                for b_parts, prob in bookie_data[koers]['winner'].items():
                    if len(csv_parts & b_parts) >= min(2, len(csv_parts)):
                        win_prob = prob
                        break
                for b_parts, prob in bookie_data[koers]['top3'].items():
                    if len(csv_parts & b_parts) >= min(2, len(csv_parts)):
                        top3_prob = prob
                        break
                if win_prob > 0 or top3_prob > 0:
                    pts_1st = p_dict_koers.get(1, max_p)
                    pts_2nd = p_dict_koers.get(2, 0)
                    pts_3rd = p_dict_koers.get(3, 0)
                    p_2or3 = max(0, top3_prob - win_prob)
                    bookie_expected = win_prob * pts_1st + p_2or3 * ((pts_2nd + pts_3rd) / 2)
                    bookie_bonus = bookie_expected * BOOKIE_WEIGHT
            verwachte_score_bij_start += bookie_bonus

# --- DE 3-TRAPS RAKET (Hybride Model) ---
            if deelnames_csv[idx] > 0:
                kans = 1.0 # Staat in de externe CSV, of gevonden via de PCS bot. 100% zeker!
            elif koers in definitieve_koersen:
                kans = 0.0 # Lijst is al rijk gevuld (>40 man), maar hij staat er niet op. 0 punten!
            else:
                # Toekomstige koers (blinde vlek): we vullen de lege gaten in met het verleden
                kans = prob_dict.get((rid, koers), 0.0)
            
            finale_score = verwachte_score_bij_start * kans
            nieuwe_kolom.append(round(finale_score, 1))
            
        df_csv[koers] = nieuwe_kolom

print("Stap 5: Totalen berekenen en bestanden opmaken...")

df_csv['Totaal_Verwacht'] = df_csv[bestaande_koersen].sum(axis=1).round(1)
df_csv['Prijs (M)'] = pd.to_numeric(df_csv['Prijs (M)'], errors='coerce')
df_csv['Punten_per_Miljoen'] = (df_csv['Totaal_Verwacht'] / df_csv['Prijs (M)']).round(2)

df_eind = df_csv.sort_values(by='Totaal_Verwacht', ascending=False)
df_eind = df_eind.drop(columns=['rider_id', 'Unnamed: 0', 'Unnamed: 5', 'Actief_Dit_Voorjaar'], errors='ignore')
df_eind = df_eind.fillna(0)

df_eind.to_csv("Wielermanager_Matrix_Berekend.csv", index=False)

excel_bestand = "Wielermanager_Matrix_Berekend.xlsx"
writer = pd.ExcelWriter(excel_bestand, engine='xlsxwriter')
df_eind.to_excel(writer, sheet_name='Matrix', index=False)

workbook  = writer.book
worksheet = writer.sheets['Matrix']
aantal_rijen = len(df_eind)
aantal_kolommen = len(df_eind.columns)

kolom_settings = [{'header': col} for col in df_eind.columns]
worksheet.add_table(0, 0, aantal_rijen, aantal_kolommen - 1, {'columns': kolom_settings, 'style': 'Table Style Medium 9'})
worksheet.set_column(0, 0, 25) 
worksheet.set_column(1, 1, 30) 
worksheet.set_column(2, aantal_kolommen - 1, 9)
worksheet.freeze_panes(1, 1)

def get_col_index(col_name):
    return df_eind.columns.get_loc(col_name)

try:
    idx_totaal = get_col_index('Totaal_Verwacht')
    idx_ppm = get_col_index('Punten_per_Miljoen')
    idx_start_koersen = get_col_index(bestaande_koersen[0])
    idx_eind_koersen = get_col_index(bestaande_koersen[-1])

    worksheet.conditional_format(1, idx_totaal, aantal_rijen, idx_totaal, {'type': '3_color_scale', 'min_color': '#F8696B', 'mid_color': '#FFEB84', 'max_color': '#63BE7B'})
    worksheet.conditional_format(1, idx_ppm, aantal_rijen, idx_ppm, {'type': '3_color_scale', 'min_color': '#F8696B', 'mid_color': '#FFEB84', 'max_color': '#63BE7B'})
    worksheet.conditional_format(1, idx_start_koersen, aantal_rijen, idx_eind_koersen, {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': '#63BE7B'})
except Exception:
    pass

writer.close()

print(f"\nKLAAR! Bestand opgeslagen als '{excel_bestand}'!")
import streamlit as st
import pandas as pd
import pulp

# --- CONFIGURATIE ---
st.set_page_config(page_title="Sporza Transfer AI Pro", page_icon="🚴‍♂️", layout="wide")
st.title("🚴‍♂️ Sporza Wielermanager: De AI Masterplan Editie")

@st.cache_data
def laad_data():
    try:
        df_b = pd.read_csv("Wielermanager_Matrix_Berekend.csv")
        df_r = pd.read_csv("Copy of De Sporza Wielermanager - Wielermatrix.csv")
        if 'Naam' not in df_r.columns:
            df_r = pd.read_csv("Copy of De Sporza Wielermanager - Wielermatrix.csv", skiprows=11)
        return df_b, df_r
    except Exception:
        return None, None

df_berekend, df_raw = laad_data()
if df_berekend is None or df_raw is None:
    st.error("Kan de CSV bestanden niet vinden. Zorg dat de matrix en raw data aanwezig zijn.")
    st.stop()

df = df_berekend.copy()

alle_koersen = ['OML', 'KBK', 'SAM', 'STRADE', 'NK', 'BKC', 'MSR', 'RVB', 'E3', 'GW', 'DDV', 'RVV', 'SCHELD', 'PR', 'RVL', 'BP', 'AG', 'WP', 'LBL']
bestaande_koersen = [k for k in alle_koersen if k in df.columns]
alle_namen = df['Naam'].sort_values().tolist()

max_punten_per_koers = {
    'MSR': 125, 'RVV': 125, 'PR': 125, 'LBL': 125,
    'OML': 100, 'STRADE': 100, 'RVB': 100, 'E3': 100, 'GW': 100, 'DDV': 100, 'RVL': 100, 'AG': 100, 'WP': 100,
    'KBK': 80, 'SAM': 80, 'NK': 80, 'BKC': 80, 'SCHELD': 80, 'BP': 80
}

# JOUW NIEUWE TEAM!
mijn_hardcoded_team = [
    "Pogačar Tadej", "van der Poel Mathieu", "Philipsen Jasper", "Pidcock Thomas",
    "Merlier Tim", "Magnier Paul", "Brennan Matthew", "Vermeersch Gianni", "Meeus Jordi",
    "Laporte Christophe", "Grégoire Romain", "Kanter Max", "Moschetti Matteo",
    "Mohorič Matej", "Seixas Paul", "Lamperti Luke", "Alaphilippe Julian",
    "Fredheim Stian", "Teutenberg Tim Torn", "Renard Alexis"
]

if 'mijn_team' not in st.session_state:
    st.session_state.mijn_team = [naam for naam in mijn_hardcoded_team if naam in alle_namen]
if 'budget_bank' not in st.session_state:
    st.session_state.budget_bank = 0.0

st.sidebar.header("⚙️ Instellingen")
geselecteerd_team = st.sidebar.multiselect("Selecteer jouw 20 renners:", options=alle_namen, default=st.session_state.mijn_team, max_selections=20)
ingevuld_budget = st.sidebar.number_input("Miljoenen op de bank:", min_value=0.0, max_value=120.0, value=float(st.session_state.budget_bank), step=0.5)

st.session_state.mijn_team = geselecteerd_team
st.session_state.budget_bank = ingevuld_budget

volgende_koers = st.sidebar.selectbox("Wat is de VOLGENDE koers?", options=bestaande_koersen)
# Standaard op 0 gezet!
gratis_transfers = st.sidebar.number_input("Overgebleven GRATIS transfers:", min_value=0, max_value=3, value=0)
reeds_gedane_transfers = st.sidebar.number_input("Reeds BETAALDE transfers dit seizoen:", min_value=0, max_value=30, value=0, help="Aantal transfers dat je al hebt uitgevoerd boven je gratis transfers. De volgende betaalde transfer kost dan (reeds+1)M.")

st.sidebar.divider()
st.sidebar.header("🎯 AI Kaders (Geavanceerd)")
min_verwachte_punten = st.sidebar.slider("Minimale kwaliteit voor NIEUWE aankopen (pt):", 0, 150, 40)
historisch_vertrouwen = st.sidebar.slider("Vertrouwen in Historische kansen (%):", 0, 100, 75) / 100.0
transfer_rendement_eis = st.sidebar.slider("Eis voor Transfer-Efficiëntie (pt):", 0, 100, 25)

geblesseerde_renners = st.sidebar.multiselect("🏥 Geblesseerde uitvallers (0 pt):", options=alle_namen)
locked_renners = st.sidebar.multiselect("🔒 Grendel (Mag AI NIET verkopen):", options=st.session_state.mijn_team)
vorm_renners = st.sidebar.multiselect("🔥 Vorm van de Dag (Krijgt x1.5 pt):", options=alle_namen)

start_idx = bestaande_koersen.index(volgende_koers)
resterende_koersen = bestaande_koersen[start_idx:]

blinde_vlekken = []
for k in resterende_koersen:
    if k in df_raw.columns:
        if pd.to_numeric(df_raw[k], errors='coerce').fillna(0).sum() < 40: # Aangepaste drempel!
            blinde_vlekken.append(k)
            df[k] = df[k] * historisch_vertrouwen

df['Rest_Punten'] = df[resterende_koersen].sum(axis=1).round(1)

if geblesseerde_renners:
    df.loc[df['Naam'].isin(geblesseerde_renners), 'Rest_Punten'] = 0.0

if vorm_renners:
    for vr in vorm_renners:
        if vr in df['Naam'].values:
            df.loc[df['Naam'] == vr, 'Rest_Punten'] = (df.loc[df['Naam'] == vr, 'Rest_Punten'] * 1.5).round(1)

mijn_team_df = df[df['Naam'].isin(st.session_state.mijn_team)]
totaal_budget = mijn_team_df['Prijs (M)'].sum() + st.session_state.budget_bank
huidige_verwachte_punten = mijn_team_df['Rest_Punten'].sum()

toegestane_renners = df[(df['Naam'].isin(st.session_state.mijn_team)) | (df['Rest_Punten'] >= min_verwachte_punten)]['Naam'].tolist()

tab1, tab2 = st.tabs(["🚀 Korte Termijn (Volgende Koers)", "🗺️ Het Masterplan (Rest v/h Seizoen)"])

with tab1:
    st.subheader("Directe Transfers voor de volgende koers")
    max_transfers_direct = st.slider("Hoeveel transfers wil je direct doorvoeren?", 1, 5, 3)
    if st.button("Bereken Korte Termijn"):
        if len(st.session_state.mijn_team) != 20:
            st.error("Je hebt geen 20 renners geselecteerd!")
        else:
            with st.spinner("Opties afwegen..."):
                best_winst, best_team, best_straf = -9999, [], 0
                for t in range(0, max_transfers_direct + 1):
                    paid_t = max(0, t - gratis_transfers)
                    # EXPONENTIËLE STRAF BEREKENING met reeds betaalde transfers!
                    # Als je al N betaalde transfers deed, kost de volgende (N+1)M
                    # Totaal = sum(N+1 .. N+paid_t) = paid_t*N + paid_t*(paid_t+1)/2
                    penalty = paid_t * reeds_gedane_transfers + (paid_t * (paid_t + 1)) / 2 * 1.0
                    
                    beschikbaar_budget = totaal_budget - penalty
                    if beschikbaar_budget < 0: continue
                    
                    prob = pulp.LpProblem(f"Transfers_t{t}", pulp.LpMaximize)
                    renner_vars = pulp.LpVariable.dicts("Renner", toegestane_renners, cat='Binary')
                    
                    prob += pulp.lpSum([df.loc[df['Naam'] == naam, 'Rest_Punten'].values[0] * renner_vars[naam] for naam in toegestane_renners])
                    prob += pulp.lpSum([renner_vars[naam] for naam in toegestane_renners]) == 20
                    prob += pulp.lpSum([df.loc[df['Naam'] == naam, 'Prijs (M)'].values[0] * renner_vars[naam] for naam in toegestane_renners]) <= beschikbaar_budget
                    
                    for r in locked_renners:
                        if r in renner_vars:
                            prob += renner_vars[r] == 1
                    
                    nieuwe_renners = [renner_vars[naam] for naam in toegestane_renners if naam not in st.session_state.mijn_team]
                    prob += pulp.lpSum(nieuwe_renners) == t
                    prob.solve(pulp.PULP_CBC_CMD(msg=False))
                    
                    if pulp.LpStatus[prob.status] == 'Optimal':
                        if pulp.value(prob.objective) > best_winst:
                            best_winst = pulp.value(prob.objective)
                            best_team = [naam for naam in toegestane_renners if renner_vars[naam].varValue == 1.0]
                            best_straf = int(penalty)

                winst = best_winst - huidige_verwachte_punten
                if winst <= 0:
                    st.info("Blijf af! Jouw team is optimaal voor de komende weken.")
                else:
                    st.success(f"Winst: +{round(winst,1)} punten! (Budget ingeleverd: {best_straf}M)")
                    vertrekkers = [n for n in st.session_state.mijn_team if n not in best_team]
                    nieuwkomers = [n for n in best_team if n not in st.session_state.mijn_team]
                    
                    colA, colB = st.columns(2)
                    with colA:
                        for v in vertrekkers: 
                            prijs = df.loc[df['Naam'] == v, 'Prijs (M)'].values[0]
                            ptn = df.loc[df['Naam'] == v, 'Rest_Punten'].values[0]
                            st.error(f"📤 UIT: **{v}** (+{prijs}M) | *Mist {ptn} pt*")
                    with colB:
                        for n in nieuwkomers: 
                            prijs = df.loc[df['Naam'] == n, 'Prijs (M)'].values[0]
                            ptn = df.loc[df['Naam'] == n, 'Rest_Punten'].values[0]
                            st.success(f"📥 IN: **{n}** (-{prijs}M) | *Pakt {ptn} pt*")

with tab2:
    st.subheader("Het Ultieme Seizoensplan (Inclusief Exponentiële Boetes!)")
    
    col_x, col_y = st.columns(2)
    max_seizoen_transfers = col_x.slider("Max transfers voor de REST VAN HET SEIZOEN:", 0, 15, 6)
    max_per_koers = col_y.slider("Max transfers TEGELIJKERTIJD (per koers):", 1, 5, 3)

    if st.button("🗺️ Genereer Masterplan", type="primary"):
        if len(st.session_state.mijn_team) != 20:
            st.error("Selecteer exact 20 renners in de zijbalk.")
        else:
            with st.spinner("AI kraakt de oplopende transferkosten... dit is serieuze wiskunde (duurt ~20 sec)..."):
                
                df_active = df[df['Naam'].isin(toegestane_renners)]
                ploegen = df_active['Ploeg'].dropna().unique().tolist()
                
                prob = pulp.LpProblem("Masterplan_Pro", pulp.LpMaximize)
                
                x = pulp.LpVariable.dicts("team", ((r, t) for r in df_active['Naam'] for t in resterende_koersen), cat='Binary')
                c = pulp.LpVariable.dicts("kopman", ((r, t) for r in df_active['Naam'] for t in resterende_koersen), cat='Binary')
                transfer_in = pulp.LpVariable.dicts("in", ((r, t) for r in df_active['Naam'] for t in resterende_koersen), cat='Binary')
                
                # Exponentiële wiskunde variabelen
                paid_transfers = pulp.LpVariable.dicts("paid", resterende_koersen, lowBound=0, cat='Continuous')
                penalty = pulp.LpVariable.dicts("penalty", resterende_koersen, lowBound=0, cat='Continuous')
                transfers_cumul = pulp.LpVariable.dicts("transfers_cumul", resterende_koersen, lowBound=0, cat='Continuous')
                
                prob += pulp.lpSum([
                    (df_active.loc[df_active['Naam']==r, t].values[0] * x[(r, t)]) + 
                    ((df_active.loc[df_active['Naam']==r, t].values[0] / max_punten_per_koers.get(t, 100)) * 30.0 * c[(r, t)]) 
                    for r in df_active['Naam'] for t in resterende_koersen
                ]) - pulp.lpSum([
                    transfer_in[(r, t)] * transfer_rendement_eis 
                    for r in df_active['Naam'] for t in resterende_koersen
                ])
                
                for i, t in enumerate(resterende_koersen):
                    prob += pulp.lpSum([x[(r, t)] for r in df_active['Naam']]) == 20
                    prob += pulp.lpSum([df_active.loc[df_active['Naam']==r, 'Prijs (M)'].values[0] * x[(r, t)] for r in df_active['Naam']]) <= totaal_budget - penalty[t]
                    
                    for r in locked_renners:
                        if r in df_active['Naam'].values:
                            prob += x[(r, t)] == 1
                    
                    prob += pulp.lpSum([c[(r, t)] for r in df_active['Naam']]) == 1
                    for r in df_active['Naam']:
                        prob += c[(r, t)] <= x[(r, t)]
                    
                    for ploeg in ploegen:
                        ploeg_renners = df_active[df_active['Ploeg'] == ploeg]['Naam'].tolist()
                        if ploeg_renners:
                            prob += pulp.lpSum([x[(r, t)] for r in ploeg_renners]) <= 4
                    
                    if i == 0:
                        for r in df_active['Naam']:
                            in_huidig_team = 1 if r in st.session_state.mijn_team else 0
                            prob += transfer_in[(r, t)] >= x[(r, t)] - in_huidig_team
                        prob += pulp.lpSum([transfer_in[(r, t)] for r in df_active['Naam']]) <= max_per_koers
                        prob += transfers_cumul[t] == pulp.lpSum([transfer_in[(r, t)] for r in df_active['Naam']])
                    else:
                        prev_t = resterende_koersen[i-1]
                        for r in df_active['Naam']:
                            prob += transfer_in[(r, t)] >= x[(r, t)] - x[(r, prev_t)]
                        prob += pulp.lpSum([transfer_in[(r, t)] for r in df_active['Naam']]) <= max_per_koers
                        prob += transfers_cumul[t] == transfers_cumul[prev_t] + pulp.lpSum([transfer_in[(r, t)] for r in df_active['Naam']])
                        
                    # DE AI-TRUC: Lineaire formules die samen een oplopende (convex) boete vormen!
                    # Verschoven met reeds_gedane_transfers als startpunt
                    prob += paid_transfers[t] >= transfers_cumul[t] - gratis_transfers
                    for k in range(1, 21): 
                        prob += penalty[t] >= (k + reeds_gedane_transfers) * paid_transfers[t] - (k * (k - 1)) / 2
                
                prob += transfers_cumul[resterende_koersen[-1]] <= max_seizoen_transfers
                
                prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=60, gapRel=0.02)) 
                
                if pulp.LpStatus[prob.status] in ['Optimal', 'Not Solved']:
                    totale_wissels = int(pulp.value(transfers_cumul[resterende_koersen[-1]]))
                    totaal_betaald = max(0, totale_wissels - gratis_transfers)
                    totaal_straf = int((totaal_betaald * (totaal_betaald + 1)) / 2)
                    
                    echte_verwachte_score = round(pulp.value(prob.objective) + (totale_wissels * transfer_rendement_eis), 1)
                    
                    st.success(f"✅ Masterplan berekend! Verwachte Punten: **{echte_verwachte_score}** (Totale bankboete voor deze {totale_wissels} transfers: -{totaal_straf}M)")
                    
                    st.subheader("📅 Jouw Opstelling per koers (Verwachte Punten)")
                    timeline_data = []
                    for r in df_active['Naam']:
                        in_team = False
                        row = {'Renner': r}
                        for t in resterende_koersen:
                            is_in = pulp.value(x[(r, t)]) == 1.0
                            is_cap = pulp.value(c[(r, t)]) == 1.0
                            
                            verwachte_punten_in_koers = round(df_active.loc[df_active['Naam']==r, t].values[0], 1)
                            
                            if is_in: 
                                in_team = True
                                if is_cap:
                                    kopman_bonus = (verwachte_punten_in_koers / max_punten_per_koers.get(t, 100)) * 30.0
                                    row[t] = f"👑 {round(verwachte_punten_in_koers + kopman_bonus, 1)}"
                                elif verwachte_punten_in_koers > 0:
                                    row[t] = f"🟢 {verwachte_punten_in_koers}"
                                else:
                                    row[t] = "☕ 0" 
                            else:
                                row[t] = ""
                        if in_team: timeline_data.append(row)
                    
                    df_timeline = pd.DataFrame(timeline_data)
                    st.dataframe(df_timeline, width='stretch')
                    st.divider()

                    huidig_sim_team = set(st.session_state.mijn_team)
                    aantal_wissels_gedaan = 0
                    virtueel_bank_budget = st.session_state.budget_bank
                    
                    for i, t in enumerate(resterende_koersen):
                        nieuw_sim_team = set([r for r in df_active['Naam'] if pulp.value(x[(r, t)]) == 1.0])
                        gekocht = nieuw_sim_team - huidig_sim_team
                        verkocht = huidig_sim_team - nieuw_sim_team
                        kopman = [r for r in nieuw_sim_team if pulp.value(c[(r, t)]) == 1.0]
                        
                        if gekocht or verkocht or kopman:
                            if i > 0 and (gekocht or verkocht):
                                st.write(f"### 🗓️ Voor de start van **{t}**:")
                            elif i == 0:
                                st.write(f"### 🗓️ Huidige Koers: **{t}**")

                            if kopman:
                                st.info(f"👑 **Ideale Kopman voor deze koers:** {kopman[0]} (Krijgt dubbele punten!)")
                            
                            if gekocht or verkocht:
                                huidige_ronde_wissels = len(gekocht)
                                kosten_in_ronde = 0
                                
                                # DE OPLOPENDE BUDGET SIMULATIE!
                                for k in range(huidige_ronde_wissels):
                                    aantal_wissels_gedaan += 1
                                    if aantal_wissels_gedaan > gratis_transfers:
                                        betaalde_transfer_index = (aantal_wissels_gedaan - gratis_transfers) + reeds_gedane_transfers
                                        kosten_in_ronde += betaalde_transfer_index # verschoven door al eerder betaalde transfers
                                
                                colA, colB = st.columns(2)
                                with colA:
                                    if verkocht: st.markdown("##### 📤 VERKOPEN")
                                    for v in verkocht: 
                                        prijs = df.loc[df['Naam'] == v, 'Prijs (M)'].values[0]
                                        rest_ptn_vanaf_nu = round(df.loc[df['Naam'] == v, resterende_koersen[i:]].sum(axis=1).values[0], 1)
                                        virtueel_bank_budget += prijs
                                        st.error(f"**{v}** (+{prijs}M) | *Mist {rest_ptn_vanaf_nu} pt*")
                                with colB:
                                    if gekocht: st.markdown("##### 📥 KOPEN")
                                    for k in gekocht: 
                                        prijs = df.loc[df['Naam'] == k, 'Prijs (M)'].values[0]
                                        virtueel_bank_budget -= prijs
                                        
                                        netto_punten = 0
                                        for future_t in resterende_koersen[i:]:
                                            if pulp.value(x[(k, future_t)]) == 1.0:
                                                netto_punten += df.loc[df['Naam'] == k, future_t].values[0]
                                        st.success(f"**{k}** (-{prijs}M) | *Netto rendement in je team: {round(netto_punten,1)} pt*")
                                
                                virtueel_bank_budget -= kosten_in_ronde
                                if kosten_in_ronde > 0:
                                    st.warning(f"⚠️ Deze ronde kostte -{kosten_in_ronde}M cumulatieve boete van de bank.")
                                st.write(f"💰 **Virtueel restbudget na deze koers:** {round(virtueel_bank_budget, 1)}M")
                                st.write("---")
                            
                        huidig_sim_team = nieuw_sim_team
                else:
                    st.error("Kon geen masterplan berekenen. De oplopende kosten maakten het wiskundig onmogelijk met dit budget. Probeer je kaders wat te versoepelen!")
                    st.error("Kon geen masterplan berekenen. De oplopende kosten maakten het wiskundig onmogelijk met dit budget. Probeer je kaders wat te versoepelen!")
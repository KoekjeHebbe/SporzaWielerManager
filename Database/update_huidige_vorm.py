import time
import sqlite3
import pandas as pd
import cloudscraper
import io

print("🚴‍♂️ Huidige Vorm (2026) Scraper gestart...\n")

# Maak verbinding met de base data
try:
    connectie = sqlite3.connect('wielermanager.db')
    df_bestaand = pd.read_sql_query("SELECT DISTINCT rider_id FROM historische_uitslagen", connectie)
    renners_lijst = df_bestaand['rider_id'].tolist()
    connectie.close()
except Exception as e:
    print(f"❌ Kan bestaande renners niet ophalen: {e}")
    exit()

print(f"Lijst van {len(renners_lijst)} renners opgehaald uit de database.")

jaar = 2026
alle_uitslagen = []
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

print(f"Start met het ophalen van data voor het lopende jaar {jaar}...\n")

aantal_succes = 0

for i, renner_id in enumerate(renners_lijst):
    url = f"https://www.procyclingstats.com/rider/{renner_id}/{jaar}"
    
    try:
        response = scraper.get(url)
        
        if response.status_code != 200:
            print(f"[{i+1}/{len(renners_lijst)}] ❌ {renner_id}: Geen data (Status: {response.status_code}).")
            continue

        tabellen = pd.read_html(io.StringIO(response.text))
        
        df_jaar = None
        for tabel in tabellen:
            if 'Race' in tabel.columns and 'Date' in tabel.columns:
                df_jaar = tabel
                # Hernoem de uitslag (positie) kolom
                df_jaar = df_jaar.rename(columns={df_jaar.columns[1]: 'Result'})
                break
        
        if df_jaar is not None and not df_jaar.empty:
            df_jaar['rider_id'] = renner_id
            df_jaar['year'] = jaar
            alle_uitslagen.append(df_jaar)
            aantal_succes += 1
            print(f"[{i+1}/{len(renners_lijst)}] ✅ {renner_id}: {len(df_jaar)} actuele koersen gevonden.")
        else:
            print(f"[{i+1}/{len(renners_lijst)}] ⚠️ {renner_id}: Nog geen uitslagen gereden in {jaar}.")
            
    except Exception as e:
        print(f"[{i+1}/{len(renners_lijst)}] ❌ {renner_id}: Fout bij ophalen. Error: {e}")
        
    time.sleep(1) # Korte pauze tegen IP bans (iets sneller dan archief, gezien het er maar 1 per renner is)

print("\nHuidige Vorm data ophalen succesvol! Nu de database updaten...")

if alle_uitslagen:
    df_compleet = pd.concat(alle_uitslagen, ignore_index=True)
    
    kolommen_om_te_bewaren = ['rider_id', 'year', 'Date', 'Result', 'Race']
    bestaande_kolommen = [col for col in kolommen_om_te_bewaren if col in df_compleet.columns]
    df_compleet = df_compleet[bestaande_kolommen]

    connectie = sqlite3.connect('wielermanager.db')
    cursor = connectie.cursor()
    
    # Verwijder oude 2026 data zodat we geen dubbele rijen krijgen bij herhaaldelijke runs
    cursor.execute(f"DELETE FROM historische_uitslagen WHERE year = {jaar}")
    connectie.commit()
    
    # Voeg de nieuwe 2026 data toe
    df_compleet.to_sql('historische_uitslagen', connectie, if_exists='append', index=False)
    connectie.close()
    
    print(f"\n🎉 SUCCES! {aantal_succes} renners hebben nieuwe {jaar} uitslagen gekregen in de database.")
    print("Vergeet hierna niet om 'Herbereken Matrix' te doen, zodat de algoritmes deze punten meenemen!")
else:
    print("\n🤷 Geen enkele renner heeft momenteel bruikbare uitslagen voor 2026 gevonden.")

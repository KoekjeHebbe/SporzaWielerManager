import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import re
import time
import io

print("🚴‍♂️ PCS Top Competitors Scraper gestart...\n")

pcs_urls = {
    'OML': 'omloop-het-nieuwsblad',
    'KBK': 'kuurne-brussel-kuurne',
    'SAM': 'le-samyn',
    'STRADE': 'strade-bianche', 
    'NK': 'nokere-koerse',
    'BKC': 'bredene-koksijde-classic',
    'MSR': 'milano-sanremo',
    'RVB': 'classic-brugge-de-panne',
    'E3': 'e3-harelbeke',
    'GW': 'gent-wevelgem',
    'DDV': 'dwars-door-vlaanderen',
    'RVV': 'ronde-van-vlaanderen',
    'SCHELD': 'scheldeprijs',
    'PR': 'paris-roubaix',
    'RVL': 'eschborn-frankfurt',
    'BP': 'brabantse-pijl',
    'AG': 'amstel-gold-race',
    'WP': 'la-fleche-wallonne',
    'LBL': 'liege-bastogne-liege'
}

JAAR = 2026
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
alle_competitors = []

for koers_code, basis_naam in pcs_urls.items():
    print(f"Internet afspeuren voor Top Competitors: {koers_code} ({basis_naam})...")
    basis_naam = basis_naam.replace('-me', '')
    url = f"https://www.procyclingstats.com/race/{basis_naam}/{JAAR}/startlist/top-competitors"
    
    try:
        response = scraper.get(url, timeout=10)
        if response.status_code == 200:
            # We zoeken naar de tabellen
            tabellen = pd.read_html(io.StringIO(response.text))
            
            df_race = None
            for df in tabellen:
                if 'Rider' in df.columns and 'Points' in df.columns:
                    df_race = df.copy()
                    break
                    
            if df_race is not None and not df_race.empty:
                df_opslag = df_race[['Rider', 'Points']].copy()
                df_opslag = df_opslag.rename(columns={'Rider': 'rider_name', 'Points': 'pcs_points'})
                df_opslag['koers_code'] = koers_code
                df_opslag['year'] = JAAR
                
                alle_competitors.append(df_opslag)
                print(f"  ✅ {len(df_opslag)} top competitors gevonden!")
            else:
                print(f"  ❌ Geen tabel met 'Points' gevonden voor {koers_code}.")
        else:
            print(f"  ❌ Fout {response.status_code} bij {koers_code}.")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        
    time.sleep(1.5)

if alle_competitors:
    df_compleet = pd.concat(alle_competitors, ignore_index=True)
    
    connectie = sqlite3.connect('wielermanager.db')
    cursor = connectie.cursor()
    
    # Maak tabel als hij nog niet bestaat
    cursor.execute('''CREATE TABLE IF NOT EXISTS pcs_top_competitors (
                        rider_name TEXT, pcs_points REAL, koers_code TEXT, year INTEGER)''')
                        
    # Verwijder oude data van dit jaar om duplicaten te voorkomen
    cursor.execute(f"DELETE FROM pcs_top_competitors WHERE year = {JAAR}")
    connectie.commit()
    
    # Opslaan
    df_compleet.to_sql('pcs_top_competitors', connectie, if_exists='append', index=False)
    connectie.close()
    print("\n🎉 SUCCES! Alle Top Competitor data is opgeslagen in de database.")
else:
    print("\n🤷 Geen data gevonden of opgeslagen.")

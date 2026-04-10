import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import unicodedata

print("🚴‍♂️ ProCyclingStats Live Startlijst Scraper gestart...\n")

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

live_startlijsten = {}

for koers_code, basis_naam in pcs_urls.items():
    print(f"Internet afspeuren voor {koers_code} ({basis_naam})...")
    basis_naam = basis_naam.replace('-me', '')
    
    url_varianten = [
        f"https://www.procyclingstats.com/race/{basis_naam}-me/{JAAR}/startlist",
        f"https://www.procyclingstats.com/race/{basis_naam}/{JAAR}/startlist",
        f"https://www.procyclingstats.com/race/{basis_naam}-me/{JAAR}/result",
        f"https://www.procyclingstats.com/race/{basis_naam}/{JAAR}/result"
    ]
    
    succes = False
    for url in url_varianten:
        try:
            response = scraper.get(url, timeout=10)
        except Exception:
            continue
            
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- DE FIX: NEGEER DE ZIJBALKEN! ---
            # PCS zet de trending renners in een sidebar. We pakken alleen het hoofdmenu.
            hoofd_content = soup.find('div', class_='page-content')
            if not hoofd_content:
                hoofd_content = soup.find('div', class_='content')
            if not hoofd_content:
                hoofd_content = soup # Nood-fallback
            
            # Zoek uitsluitend in het hoofdscherm naar links
            a_tags = hoofd_content.find_all('a', href=True)
            
            renners_gevonden = []
            for tag in a_tags:
                href = tag['href']
                if href.startswith('rider/'):
                    renner_id = href.replace('rider/', '')
                    renners_gevonden.append(renner_id)
                    
            unieke_renners = set(renners_gevonden)
            
            if len(unieke_renners) > 0:
                bron = "STARTLIJST" if "startlist" in url else "UITSLAG"
                print(f"  ✅ {len(unieke_renners)} renners gevonden via {bron}!")
                live_startlijsten[koers_code] = unieke_renners
                succes = True
                break 
                
        time.sleep(0.5)
        
    if not succes:
        print(f"  ❌ Kon geen lijst vinden voor {koers_code}.")
        live_startlijsten[koers_code] = set()

# --- CSV INLEZEN EN UPDATEN ---
bestand_naam = "Copy of De Sporza Wielermanager - Wielermatrix.csv"
try:
    df_csv = pd.read_csv(bestand_naam)
    if 'Naam' not in df_csv.columns:
        df_csv = pd.read_csv(bestand_naam, skiprows=11)
        
    if 'Naam' not in df_csv.columns:
        print("\n❌ Fout: Kan de kolom 'Naam' niet vinden in je Excel-bestand.")
        exit()
except FileNotFoundError:
    print(f"\n❌ Kan '{bestand_naam}' niet vinden.")
    exit()

stopwoorden = {'van', 'der', 'de', 'den', 'het', 'ten', 'ter', 'le', 'la', 'du', 'des', 'di', 'da', 'del', 'dos'}

def normaliseer_naam(naam):
    naam = ''.join(c for c in unicodedata.normalize('NFD', str(naam)) if unicodedata.category(c) != 'Mn')
    return set(re.sub(r'[^a-z\s]', '', naam.lower()).split()) - stopwoorden

print("\n⚙️ Startlijsten koppelen aan jouw matrix...")

aantal_updates = 0
for idx, row in df_csv.iterrows():
    naam = row['Naam']
    if pd.isna(naam): continue
    
    csv_parts = normaliseer_naam(naam)
    
    for koers_code in pcs_urls.keys():
        if koers_code in df_csv.columns:
            startlijst_pcs = live_startlijsten.get(koers_code, set())
            rijdt_mee = 0
            
            for pcs_id in startlijst_pcs:
                pcs_parts = set(pcs_id.split('-')) - stopwoorden
                if len(csv_parts.intersection(pcs_parts)) >= min(2, len(csv_parts)):
                    rijdt_mee = 1
                    aantal_updates += 1
                    break
                    
            huidige_waarde = pd.to_numeric(df_csv.at[idx, koers_code], errors='coerce')
            if pd.isna(huidige_waarde): huidige_waarde = 0
            df_csv.at[idx, koers_code] = max(huidige_waarde, rijdt_mee)

df_csv.to_csv(bestand_naam, index=False)
print(f"\n🎉 SUCCES! Er zijn dit keer {aantal_updates} start-matches gelegd.")
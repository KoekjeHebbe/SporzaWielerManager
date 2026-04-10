import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import os

# --- CONFIGURATIE ---
SCRIPTS = {
    "🌟 0a. Update Actuele Vorm (2026)": "python update_huidige_vorm.py",
    "🌟 0b. Update PCS Top Competitors": "python update_top_competitors.py",
    "📡 1. Update Startlijsten (Scraper)": "python pcs_scraper.py",
    "🧮 2. Herbereken Matrix": "python maak_matrix.py",
    "🚀 3. Start Sporza AI App": "streamlit run app.py"
}

def voer_script_uit(commando, knop_naam):
    # We runnen dit in een aparte "thread" (achtergrond) zodat de UI niet vastloopt
    def taak():
        console.insert(tk.END, f"\n▶ Starten: {knop_naam}...\n", "info")
        console.see(tk.END)
        
        try:
            # Forceer Python om UTF-8 (emojis) te gebruiken!
            mijn_env = os.environ.copy()
            mijn_env["PYTHONIOENCODING"] = "utf-8"
            
            # Voer het commando uit en lees de output live uit
            proces = subprocess.Popen(
                commando, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                shell=True,
                env=mijn_env,
                encoding="utf-8"
            )
            
            for lijn in proces.stdout:
                console.insert(tk.END, lijn)
                console.see(tk.END)
                
            proces.wait()
            console.insert(tk.END, f"✅ Klaar met {knop_naam}.\n{'-'*50}\n", "succes")
            console.see(tk.END)
            
        except Exception as e:
            console.insert(tk.END, f"❌ Fout bij uitvoeren: {e}\n", "fout")
            console.see(tk.END)

    threading.Thread(target=taak, daemon=True).start()

# --- UI OPBOUWEN ---
root = tk.Tk()
root.title("🚴‍♂️ Sporza AI - Control Center")
root.geometry("700x500")
root.configure(bg="#f4f4f9")

# Titel
titel_label = tk.Label(root, text="Wielermanager Control Center", font=("Helvetica", 18, "bold"), bg="#f4f4f9", fg="#333")
titel_label.pack(pady=15)

# Knoppen Frame
knoppen_frame = tk.Frame(root, bg="#f4f4f9")
knoppen_frame.pack(pady=10)

# Genereer de knoppen automatisch
for naam, commando in SCRIPTS.items():
    actie = lambda c=commando, n=naam: voer_script_uit(c, n)
    knop = tk.Button(knoppen_frame, text=naam, font=("Helvetica", 12), bg="#4CAF50", fg="white", 
                     activebackground="#45a049", activeforeground="white", width=35, pady=8, cursor="hand2", command=actie)
    knop.pack(pady=5)

# Console / Logboek (Zwart scherm met tekst)
console_label = tk.Label(root, text="Terminal Output:", font=("Helvetica", 10, "bold"), bg="#f4f4f9")
console_label.pack(anchor="w", padx=20)

console = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=15, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
console.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)

# Kleuren voor specifieke teksten in de console
console.tag_config("info", foreground="#00bfff")
console.tag_config("succes", foreground="#32cd32", font=("Consolas", 10, "bold"))
console.tag_config("fout", foreground="#ff4500", font=("Consolas", 10, "bold"))

console.insert(tk.END, "Welkom bij de AI Manager! Klaar voor instructies...\n")

# Start de UI
root.mainloop()
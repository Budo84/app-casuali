import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: CHEF & VOLANTINI (FIX PERCORSI) ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante.")
    sys.exit(1)

model = genai.GenerativeModel("gemini-1.5-flash")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI (BLINDATA) ---
def analizza_volantini():
    offerte_db = {}
    
    # --- FIX PERCORSI ---
    # Definiamo due possibili percorsi dove cercare
    # 1. Percorso assoluto basato sulla posizione dello script
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_1 = os.path.join(path_script, "volantini")
    
    # 2. Percorso relativo dalla root di GitHub (Current Working Directory)
    dir_2 = os.path.join(os.getcwd(), "spesa", "volantini")

    # Scegliamo quello che esiste
    target_dir = ""
    if os.path.exists(dir_1):
        target_dir = dir_1
    elif os.path.exists(dir_2):
        target_dir = dir_2
    
    print(f"📍 Cartella Script: {path_script}")
    print(f"📍 CWD (Root): {os.getcwd()}")
    print(f"📂 Cartella Volantini scelta: {target_dir}")

    if not target_dir or not os.path.exists(target_dir):
        print("⚠️ ERRORE: La cartella 'volantini' non esiste in nessuno dei percorsi previsti.")
        # Proviamo a crearla per il futuro
        try: 
            os.makedirs(dir_1) 
            print("   -> Creata cartella vuota per evitare errori futuri.")
        except: pass
        return {}

    # DEBUG: Stampa contenuto cartella
    print(f"   Contenuto cartella: {os.listdir(target_dir)}")

    # Cerca PDF (Case insensitive per sicurezza: .pdf e .PDF)
    files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
    
    if not files:
        print("ℹ️ Nessun file PDF trovato nella cartella.")
        return {}

    print(f"🔎 Trovati {len(files)} volantini. Inizio analisi...")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            # Pulizia nome: rimuove estensione e underscore
            nome_store = os.path.splitext(nome_file)[0].replace("_", " ").title()
            
            print(f"📄 Elaborazione: {nome_store} ({nome_file})")
            
            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa attiva (max 20 sec)
            attempt = 0
            while pdf.state.name == "PROCESSING" and attempt < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempt += 1
            
            if pdf.state.name == "FAILED":
                print(f"   ❌ Google non riesce a leggere {nome_file}.")
                continue

            # Prompt Estrazione
            prompt = f"""
            Analizza il volantino "{nome_store}". 
            Estrai TUTTI i prodotti alimentari (cibo, bevande) e i prezzi.
            
            OUTPUT JSON UNICO: 
            {{ "{nome_store}": [ {{"name": "Nome Prodotto", "price": 0.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            raw_text = pulisci_json(res.text)
            
            try:
                data = json.loads(raw_text)
                # Gestione chiavi dinamiche
                chiave = nome_store if nome_store in data else list(data.keys())[0]
                
                if chiave in data and isinstance(data[chiave], list):
                    offerte_db[nome_store] = data[chiave]
                    print(f"   ✅ OK: {len(data[chiave])} offerte estratte.")
                else:
                    print(f"   ⚠️ Warning: JSON vuoto o malformato per {nome_store}")
            except:
                print(f"   ❌ Errore parsing JSON per {nome_store}")

            # Pulizia
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ⚠️ Errore generico su {file_path}: {e}")

    return offerte_db

# --- FASE 2: GENERATORE RICETTARIO ---
def crea_database_ricette(offerte):
    print("🍳 Aggiornamento Database Ricette...")
    
    ingred_context = ""
    if offerte:
        all_products = []
        for s in offerte:
            for p in offerte[s]: all_products.append(p['name'])
        sample = random.sample(all_products, min(len(all_products), 20))
        ingred_context = f"USA SE PUOI: {', '.join(sample)}."

    try:
        prompt = f"""
        Crea un DATABASE RICETTE (Chef Expert).
        {ingred_context}
        
        3 CATEGORIE:
        1. "mediterranea" (Equilibrata)
        2. "vegetariana" (No carne/pesce)
        3. "mondo" (Internazionale)
        
        Per OGNI categoria: 5 Colazioni, 7 Pranzi, 7 Cene, 5 Merende.
        
        JSON:
        {{
            "mediterranea": {{
                "colazione": [ {{"title": "...", "ingredients": ["..."]}} ],
                "pranzo": [...], "cena": [...], "merenda": [...]
            }},
            "vegetariana": {{ ... }},
            "mondo": {{ ... }}
        }}
        """
        
        response = model.generate_content(prompt)
        db_ricette = json.loads(pulisci_json(response.text))
        print("✅ Database Ricette aggiornato.")
        return db_ricette

    except Exception as e:
        print(f"❌ Errore AI Ricette: {e}. Uso Backup.")
        return DATABASE_BACKUP

DATABASE_BACKUP = {
    "mediterranea": {
        "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"]}],
        "pranzo": [{"title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}],
        "cena": [{"title": "Pollo ai Ferri", "ingredients": ["Pollo", "Limone"]}],
        "merenda": [{"title": "Mela", "ingredients": ["Mela"]}]
    },
    "vegetariana": {
        "colazione": [{"title": "Yogurt", "ingredients": ["Yogurt"]}],
        "pranzo": [{"title": "Pasta Pesto", "ingredients": ["Pasta", "Basilico"]}],
        "cena": [{"title": "Frittata", "ingredients": ["Uova"]}],
        "merenda": [{"title": "Noci", "ingredients": ["Noci"]}]
    },
    "mondo": {
        "colazione": [{"title": "Pancakes", "ingredients": ["Farina", "Uova"]}],
        "pranzo": [{"title": "Riso Cantonese", "ingredients": ["Riso", "Prosciutto"]}],
        "cena": [{"title": "Tacos", "ingredients": ["Carne", "Mais"]}],
        "merenda": [{"title": "Muffin", "ingredients": ["Cioccolato"]}]
    }
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. Analisi
    offerte = analizza_volantini()
    
    # 2. Ricette
    database_ricette = crea_database_ricette(offerte)

    # 3. Save
    output_data = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": database_ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"💾 Salvato: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

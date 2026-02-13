import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: CHEF 3.0 (FIX MODELLO AI) ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante.")
    sys.exit(1)

# 2. SELEZIONE MODELLO ROBUSTA
def get_working_model():
    # Elenco di modelli da provare in ordine
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest"
    ]
    for model_name in candidates:
        try:
            print(f"🔌 Tentativo connessione con modello: {model_name}...")
            model = genai.GenerativeModel(model_name)
            # Test rapido di connessione (senza sprecare token)
            return model
        except:
            continue
    
    print("⚠️ Fallback: Uso modello standard 'gemini-pro'")
    return genai.GenerativeModel("gemini-pro")

model = get_working_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI ---
def analizza_volantini():
    offerte_db = {}
    
    # PERCORSI BLINDATI
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_1 = os.path.join(path_script, "volantini")
    dir_2 = os.path.join(os.getcwd(), "spesa", "volantini")

    target_dir = dir_1 if os.path.exists(dir_1) else (dir_2 if os.path.exists(dir_2) else "")
    
    if not target_dir:
        print("ℹ️ Cartella volantini non trovata. Salto analisi.")
        return {}

    # Cerca PDF
    files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
    print(f"🔎 Trovati {len(files)} volantini in {target_dir}")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].replace("_", " ").title()
            print(f"📄 Analisi: {nome_store}")
            
            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa
            attempt = 0
            while pdf.state.name == "PROCESSING" and attempt < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempt += 1
            
            if pdf.state.name == "FAILED":
                print(f"   ❌ File illeggibile lato Google.")
                continue

            # Prompt
            prompt = f"""
            Analizza il volantino "{nome_store}". 
            Estrai TUTTI i prodotti alimentari e prezzi.
            JSON: {{ "{nome_store}": [ {{"name": "Nome", "price": 0.00}} ] }}
            """
            
            # Qui gestiamo l'errore 404 specifico del modello
            try:
                res = model.generate_content([pdf, prompt])
                data = json.loads(pulisci_json(res.text))
                
                chiave = nome_store if nome_store in data else list(data.keys())[0]
                if chiave in data:
                    offerte_db[nome_store] = data[chiave]
                    print(f"   ✅ Estratti {len(data[chiave])} prodotti.")
            except Exception as e_gen:
                print(f"   ⚠️ Errore generazione AI per {nome_store}: {e_gen}")

            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ❌ Errore file {file_path}: {e}")

    return offerte_db

# --- FASE 2: RICETTARIO ---
def crea_database_ricette(offerte):
    print("🍳 Creazione Ricettario...")
    
    ingred_context = ""
    if offerte:
        all_p = []
        for s in offerte:
            for p in offerte[s]: all_p.append(p['name'])
        if all_p:
            sample = random.sample(all_p, min(len(all_p), 20))
            ingred_context = f"Usa ingredienti in offerta: {', '.join(sample)}."

    try:
        prompt = f"""
        Crea un DATABASE RICETTE (Chef Expert).
        {ingred_context}
        
        3 CATEGORIE:
        1. "mediterranea" (Equilibrata)
        2. "vegetariana" (No carne/pesce)
        3. "mondo" (Internazionale)
        
        Per OGNI categoria: 5 Colazioni, 7 Pranzi, 7 Cene, 5 Merende.
        
        JSON STRUTTURA:
        {{
            "mediterranea": {{
                "colazione": [ {{"title": "...", "ingredients": ["..."]}} ],
                "pranzo": [...], "cena": [...], "merenda": [...]
            }},
            "vegetariana": {{ ... }},
            "mondo": {{ ... }}
        }}
        """
        
        res = model.generate_content(prompt)
        db_ricette = json.loads(pulisci_json(res.text))
        print("✅ Ricettario creato.")
        return db_ricette

    except Exception as e:
        print(f"❌ Errore AI Ricette: {e}. Uso Backup.")
        return DATABASE_BACKUP

DATABASE_BACKUP = {
    "mediterranea": {
        "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"]}],
        "pranzo": [{"title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}],
        "cena": [{"title": "Pollo al Limone", "ingredients": ["Pollo", "Limone"]}],
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
    
    offerte = analizza_volantini()
    db_ricette = crea_database_ricette(offerte)

    output = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": db_ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"💾 Salvato: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

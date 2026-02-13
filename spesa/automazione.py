import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: GESTORE CLOUD ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante.")
    sys.exit(1)

model = genai.GenerativeModel("gemini-pro")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI ---
def analizza_volantini():
    offerte_db = {}
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_1 = os.path.join(path_script, "volantini")
    dir_2 = os.path.join(os.getcwd(), "spesa", "volantini")
    target_dir = dir_1 if os.path.exists(dir_1) else (dir_2 if os.path.exists(dir_2) else "")

    if not target_dir: return {}

    files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
    print(f"🔎 Analisi {len(files)} volantini...")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].replace("_", " ").title()
            
            pdf = genai.upload_file(file_path, display_name=nome_store)
            attempt = 0
            while pdf.state.name == "PROCESSING" and attempt < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempt += 1
            
            if pdf.state.name == "FAILED": continue

            prompt = f"""Estrai prodotti e prezzi da "{nome_store}". JSON: {{ "{nome_store}": [ {{"name": "...", "price": 0.00}} ] }}"""
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            chiave = nome_store if nome_store in data else list(data.keys())[0]
            if chiave in data: offerte_db[nome_store] = data[chiave]
            try: genai.delete_file(pdf.name)
            except: pass
        except: pass
    return offerte_db

# --- FASE 2: GESTIONE DATABASE ---
def carica_vecchio_db():
    path_script = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(path_script, "dati_settimanali.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("database_ricette", DATABASE_BACKUP)
        except: pass
    return DATABASE_BACKUP

def importa_ricette_utenti(db_esistente):
    # Cerca file JSON caricati dagli utenti
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_utente = os.path.join(path_script, "ricette_utenti")
    # Supporto anche per CWD
    if not os.path.exists(dir_utente):
        dir_utente = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
    
    if not os.path.exists(dir_utente): return db_esistente

    files = glob.glob(os.path.join(dir_utente, "*.json"))
    if not files: return db_esistente

    print(f"📥 Trovate {len(files)} nuove ricette utente da importare...")
    
    count = 0
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file_obj:
                nuova = json.load(file_obj)
                # Struttura attesa: {"category": "mediterranea", "type": "pranzo", "recipe": {...}}
                cat = nuova.get('category', 'mediterranea')
                tipo = nuova.get('type', 'pranzo')
                ricetta = nuova.get('recipe')

                if cat in db_esistente and tipo in db_esistente[cat] and ricetta:
                    # Evita duplicati
                    titoli = [r['title'].lower() for r in db_esistente[cat][tipo]]
                    if ricetta['title'].lower() not in titoli:
                        db_esistente[cat][tipo].append(ricetta)
                        count += 1
                        print(f"   + Aggiunta: {ricetta['title']}")
            
            # Cancelliamo il file dopo l'import (ci pensa git rm nel workflow, ma qui lo segniamo come fatto)
        except Exception as e:
            print(f"   ❌ Errore import file {f}: {e}")

    print(f"✅ Importate {count} ricette nel Database Principale.")
    return db_esistente

def crea_nuove_ricette(offerte):
    print("🍳 Chef AI al lavoro...")
    context = ""
    if offerte:
        items = [p['name'] for s in offerte for p in offerte[s]]
        if items:
            sample = random.sample(items, min(len(items), 15))
            context = f"Usa ingredienti: {', '.join(sample)}."

    try:
        prompt = f"""
        Crea 3-4 ricette NUOVE per categoria.
        {context}
        Categorie: mediterranea, vegetariana, mondo.
        Pasti: colazione, pranzo, cena, merenda.
        JSON: {{ "mediterranea": {{ "colazione": [...], ... }}, ... }}
        """
        res = model.generate_content(prompt)
        return json.loads(pulisci_json(res.text))
    except: return {}

def unisci_db(main_db, new_db):
    if not new_db: return main_db
    for cat in new_db:
        if cat in main_db:
            for pasto in new_db[cat]:
                if pasto in main_db[cat]:
                    titoli = [r['title'] for r in main_db[cat][pasto]]
                    for r in new_db[cat][pasto]:
                        if r['title'] not in titoli: main_db[cat][pasto].append(r)
    return main_db

DATABASE_BACKUP = {
    "mediterranea": {
        "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"]}],
        "pranzo": [{"title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}],
        "cena": [{"title": "Pollo al Limone", "ingredients": ["Pollo", "Limone"]}],
        "merenda": [{"title": "Mela", "ingredients": ["Mela"]}]
    },
    "vegetariana": {"colazione":[], "pranzo":[], "cena":[], "merenda":[]},
    "mondo": {"colazione":[], "pranzo":[], "cena":[], "merenda":[]}
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    offerte = analizza_volantini()
    
    # 1. Carica DB esistente
    db_principale = carica_vecchio_db()
    
    # 2. Importa Ricette Utente (Cloud)
    db_principale = importa_ricette_utenti(db_principale)
    
    # 3. Genera Nuove Ricette AI
    nuove_ai = crea_nuove_ricette(offerte)
    db_principale = unisci_db(db_principale, nuove_ai)

    output = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": db_principale
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"💾 Salvato: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

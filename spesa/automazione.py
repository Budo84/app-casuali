import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: CHEF GLUTEN-FREE & SAFETY ---")

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

# --- 1. OFFERTE ---
def analizza_volantini():
    offerte_db = {}
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_1 = os.path.join(path_script, "volantini")
    dir_2 = os.path.join(os.getcwd(), "spesa", "volantini")
    target_dir = dir_1 if os.path.exists(dir_1) else (dir_2 if os.path.exists(dir_2) else "")

    if not target_dir: return {}
    files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
    
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

# --- 2. DB MANAGEMENT ---
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
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_utente = os.path.join(path_script, "ricette_utenti")
    if not os.path.exists(dir_utente): dir_utente = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
    if not os.path.exists(dir_utente): return db_esistente

    files = glob.glob(os.path.join(dir_utente, "*.json"))
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file_obj:
                nuova = json.load(file_obj)
                cats = nuova.get('categories', [nuova.get('category')])
                types = nuova.get('types', [nuova.get('type')])
                ricetta = nuova.get('recipe')
                
                if ricetta:
                    for cat in cats:
                        if cat not in db_esistente: db_esistente[cat] = {"colazione":[], "pranzo":[], "cena":[], "merenda":[]}
                        for tipo in types:
                            if tipo not in db_esistente[cat]: db_esistente[cat][tipo] = []
                            titoli = [r['title'].lower() for r in db_esistente[cat][tipo]]
                            if ricetta['title'].lower() not in titoli:
                                db_esistente[cat][tipo].append(ricetta)
        except: pass
    return db_esistente

def crea_nuove_ricette(offerte):
    context = ""
    if offerte:
        items = [p['name'] for s in offerte for p in offerte[s]]
        if items:
            sample = random.sample(items, min(len(items), 15))
            context = f"Usa ingredienti in offerta: {', '.join(sample)}."
    try:
        # AGGIUNTA CATEGORIA SENZA GLUTINE
        prompt = f"""
        Crea 3 ricette nuove per categoria.
        {context}
        
        4 CATEGORIE: 
        1. "mediterranea" (Tradizionale)
        2. "vegetariana" (No carne/pesce)
        3. "mondo" (Etnica)
        4. "senza_glutine" (TASSATIVO: Riso, Mais, Grano Saraceno, Patate, Legumi. VIETATO: Grano, Orzo, Farro, Pasta normale, Pane normale).
        
        Pasti: colazione, pranzo, cena, merenda.
        JSON: {{ "mediterranea": {{ ... }}, "senza_glutine": {{ ... }} }}
        """
        res = model.generate_content(prompt)
        return json.loads(pulisci_json(res.text))
    except: return {}

def unisci_db(main_db, new_db):
    if not new_db: return main_db
    for cat in new_db:
        if cat not in main_db: main_db[cat] = {"colazione":[], "pranzo":[], "cena":[], "merenda":[]}
        for pasto in new_db[cat]:
            if pasto not in main_db[cat]: main_db[cat][pasto] = []
            
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
    "mondo": {"colazione":[], "pranzo":[], "cena":[], "merenda":[]},
    "senza_glutine": {
        "colazione": [{"title": "Yogurt e Frutta", "ingredients": ["Yogurt", "Banana"]}],
        "pranzo": [{"title": "Risotto allo Zafferano", "ingredients": ["Riso", "Zafferano", "Parmigiano"]}],
        "cena": [{"title": "Petto di Pollo e Patate", "ingredients": ["Pollo", "Patate", "Rosmarino"]}],
        "merenda": [{"title": "Gallette di Mais", "ingredients": ["Gallette mais", "Marmellata"]}]
    }
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    offerte = analizza_volantini()
    db_prin = carica_vecchio_db()
    db_prin = importa_ricette_utenti(db_prin)
    nuove = crea_nuove_ricette(offerte)
    db_prin = unisci_db(db_prin, nuove)

    out = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": db_prin
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
    print(f"💾 Salvato: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

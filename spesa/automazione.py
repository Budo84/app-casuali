import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: SISTEMA DOPPIO FILE ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante.")
    sys.exit(1)

# SELETTORE MODELLO (Usa Pro per i PDF che è più affidabile)
def get_model():
    try:
        return genai.GenerativeModel("gemini-1.5-pro")
    except:
        return genai.GenerativeModel("gemini-pro")

model = get_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI -> offerte.json ---
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
            print(f"📄 Leggo: {nome_store}")
            
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa attiva
            for _ in range(10):
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                if pdf.state.name == "ACTIVE": break
            
            if pdf.state.name != "ACTIVE": 
                print("❌ PDF non pronto")
                continue

            prompt = f"""
            Analizza il volantino "{nome_store}".
            Estrai TUTTI i prodotti alimentari e i prezzi.
            
            RISPONDI SOLO JSON:
            {{
                "{nome_store}": [
                    {{"name": "Pasta Barilla 500g", "price": 0.89}},
                    {{"name": "Latte 1L", "price": 1.20}}
                ]
            }}
            """
            
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            chiave = nome_store if nome_store in data else list(data.keys())[0]
            if chiave in data:
                offerte_db[nome_store] = data[chiave]
                print(f"   ✅ Trovati {len(data[chiave])} prodotti.")
            
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ⚠️ Errore file {file_path}: {e}")

    return offerte_db

# --- FASE 2: GESTIONE RICETTE -> dati_settimanali.json ---
def carica_vecchio_db():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati_settimanali.json")
        with open(path, "r") as f:
            return json.load(f).get("database_ricette", DATABASE_BACKUP)
    except: return DATABASE_BACKUP

def importa_ricette_utenti(db_esistente):
    try:
        path = os.path.dirname(os.path.abspath(__file__))
        d_user = os.path.join(path, "ricette_utenti")
        if not os.path.exists(d_user): d_user = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
        
        if os.path.exists(d_user):
            files = glob.glob(os.path.join(d_user, "*.json"))
            for f in files:
                try:
                    with open(f, "r") as fo:
                        j = json.load(fo)
                        r = j.get('recipe')
                        cats = j.get('categories', [j.get('category')])
                        types = j.get('types', [j.get('type')])
                        if r:
                            for c in cats:
                                if c not in db_esistente: db_esistente[c] = {}
                                for t in types:
                                    if t not in db_esistente[c]: db_esistente[c][t] = []
                                    if not any(x['title'] == r['title'] for x in db_esistente[c][t]):
                                        db_esistente[c][t].append(r)
                except: pass
    except: pass
    return db_esistente

def crea_nuove_ricette(offerte_data):
    # Usa le offerte appena lette per ispirare le ricette
    context = ""
    if offerte_data:
        items = []
        for s in offerte_data:
            for p in offerte_data[s]: items.append(p['name'])
        if items:
            sample = random.sample(items, min(len(items), 10))
            context = f"Usa ingredienti in offerta: {', '.join(sample)}."
            
    try:
        prompt = f"""
        Crea 2 ricette NUOVE per categoria.
        {context}
        Categorie: mediterranea, vegetariana, mondo, senza_glutine.
        Pasti: colazione, pranzo, cena, merenda.
        JSON: {{ "mediterranea": {{ "pranzo": [...] }} }}
        """
        res = model.generate_content(prompt)
        return json.loads(pulisci_json(res.text))
    except: return {}

def unisci_db(old, new):
    if not new: return old
    for cat in new:
        if cat not in old: old[cat] = {}
        for pasto in new[cat]:
            if pasto not in old[cat]: old[cat][pasto] = []
            for r in new[cat][pasto]:
                if not any(x['title'] == r['title'] for x in old[cat][pasto]):
                    old[cat][pasto].append(r)
    return old

DATABASE_BACKUP = {
    "mediterranea": {
        "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"]}],
        "pranzo": [{"title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}],
        "cena": [{"title": "Pollo al Limone", "ingredients": ["Pollo", "Limone"]}],
        "merenda": [{"title": "Mela", "ingredients": ["Mela"]}]
    },
    "senza_glutine": {
        "pranzo": [{"title": "Risotto Zafferano", "ingredients": ["Riso", "Zafferano"]}],
        "cena": [{"title": "Frittata", "ingredients": ["Uova", "Verdure"]}]
    }
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. ANALISI OFFERTE -> FILE SEPARATO
    offerte = analizza_volantini()
    file_offerte = os.path.join(base_dir, "offerte.json")
    with open(file_offerte, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print(f"💾 Offerte salvate in: {file_offerte}")

    # 2. GESTIONE RICETTE -> FILE PRINCIPALE
    db = carica_vecchio_db()
    db = importa_ricette_utenti(db)
    nuove = crea_nuove_ricette(offerte)
    db = unisci_db(db, nuove)

    file_ricette = os.path.join(base_dir, "dati_settimanali.json")
    out = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "database_ricette": db
    }

    with open(file_ricette, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
    print(f"💾 Ricette salvate in: {file_ricette}")

if __name__ == "__main__":
    esegui_tutto()

import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: ANALISI VOLANTINI & MENU ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante.")
    sys.exit(1)

# 2. SELEZIONE MODELLO ROBUSTA (Evita errore 404)
def get_model():
    # Proviamo prima Flash (ottimo per i PDF)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        print("✅ Uso modello: Flash (Veloce)")
        return model
    except:
        pass
    
    # Fallback su Pro (Stabile)
    print("⚠️ Flash non disponibile, passo a Pro.")
    return genai.GenerativeModel("gemini-1.5-pro")

model = get_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI ---
def analizza_volantini():
    offerte_db = {}
    
    # Percorsi flessibili per GitHub Actions
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_1 = os.path.join(path_script, "volantini")
    dir_2 = os.path.join(os.getcwd(), "spesa", "volantini")
    
    target_dir = dir_1 if os.path.exists(dir_1) else (dir_2 if os.path.exists(dir_2) else "")

    if not target_dir:
        print("ℹ️ Nessuna cartella volantini trovata.")
        return {}

    # Cerca PDF (Case insensitive)
    files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
    print(f"🔎 Trovati {len(files)} volantini in: {target_dir}")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].replace("_", " ").title()
            print(f"📄 Elaborazione: {nome_store}...")
            
            # Upload del file su Google AI
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa attiva elaborazione
            attempt = 0
            while pdf.state.name == "PROCESSING" and attempt < 20:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempt += 1
            
            if pdf.state.name == "FAILED":
                print(f"   ❌ Errore lettura PDF {nome_store}")
                continue

            # Prompt specifico per estrazione prezzi
            prompt = f"""
            Analizza questo volantino di "{nome_store}".
            Estrai una lista di prodotti alimentari e i relativi prezzi.
            Ignora prodotti non alimentari (es. detersivi) se possibile, ma includi tutto ciò che è cibo.
            
            RISPONDI SOLO CON QUESTO JSON:
            {{
                "{nome_store}": [
                    {{"name": "Pasta Garofalo 500g", "price": 0.89}},
                    {{"name": "Latte Intero 1L", "price": 1.20}}
                ]
            }}
            """
            
            res = model.generate_content([pdf, prompt])
            raw_json = pulisci_json(res.text)
            data = json.loads(raw_json)
            
            # Salvataggio dati
            chiave = nome_store if nome_store in data else list(data.keys())[0]
            if chiave in data:
                offerte_db[nome_store] = data[chiave]
                print(f"   ✅ Estratti {len(data[chiave])} prodotti da {nome_store}")
            
            # Pulizia file remoto
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ⚠️ Errore durante l'analisi di {file_path}: {e}")

    return offerte_db

# --- FASE 2: GESTIONE DATABASE RICETTE (ACCUMULATIVO) ---
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
    # Fallback path
    if not os.path.exists(dir_utente):
        dir_utente = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
    
    if not os.path.exists(dir_utente): return db_esistente

    files = glob.glob(os.path.join(dir_utente, "*.json"))
    if not files: return db_esistente

    print(f"📥 Importazione {len(files)} ricette utente...")
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file_obj:
                nuova = json.load(file_obj)
                # Gestione array categorie/tipi
                cats = nuova.get('categories', [nuova.get('category')])
                types = nuova.get('types', [nuova.get('type')])
                ricetta = nuova.get('recipe')
                
                if ricetta:
                    for cat in cats:
                        if not cat: continue
                        if cat not in db_esistente: db_esistente[cat] = {"colazione":[], "pranzo":[], "cena":[], "merenda":[]}
                        for tipo in types:
                            if not tipo: continue
                            if tipo not in db_esistente[cat]: db_esistente[cat][tipo] = []
                            
                            # Controllo duplicati
                            titoli = [r['title'].lower() for r in db_esistente[cat][tipo]]
                            if ricetta['title'].lower() not in titoli:
                                db_esistente[cat][tipo].append(ricetta)
                                print(f"   + Aggiunta: {ricetta['title']}")
        except: pass
    return db_esistente

def crea_nuove_ricette(offerte):
    print("🍳 Lo Chef sta creando nuove ricette...")
    context = ""
    if offerte:
        items = []
        for s in offerte:
            for p in offerte[s]: items.append(p['name'])
        if items:
            sample = random.sample(items, min(len(items), 20))
            context = f"Usa preferibilmente questi ingredienti in offerta: {', '.join(sample)}."

    try:
        prompt = f"""
        Agisci come Chef. Crea 3 NUOVE ricette per ogni categoria e pasto.
        {context}
        
        Categorie Obbligatorie: 
        1. "mediterranea"
        2. "vegetariana"
        3. "mondo"
        4. "senza_glutine" (Usa SOLO: Riso, Mais, Grano Saraceno, Patate, Legumi. NO pasta di grano).
        
        Pasti: colazione, pranzo, cena, merenda.
        
        JSON STRUTTURA: 
        {{ 
            "mediterranea": {{ "colazione": [{{...}}], ... }},
            "senza_glutine": {{ "pranzo": [{{ "title": "...", "ingredients": [...] }}], ... }}
        }}
        """
        res = model.generate_content(prompt)
        return json.loads(pulisci_json(res.text))
    except Exception as e:
        print(f"⚠️ Errore generazione AI: {e}")
        return {}

def unisci_db(main_db, new_db):
    if not new_db: return main_db
    for cat in new_db:
        if cat not in main_db: main_db[cat] = {"colazione":[], "pranzo":[], "cena":[], "merenda":[]}
        for pasto in new_db[cat]:
            if pasto not in main_db[cat]: main_db[cat][pasto] = []
            
            titoli = [r['title'] for r in main_db[cat][pasto]]
            for r in new_db[cat][pasto]:
                if r['title'] not in titoli:
                    main_db[cat][pasto].append(r)
    return main_db

# DB DI BASE MINIMO
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
        "pranzo": [{"title": "Risotto allo Zafferano", "ingredients": ["Riso", "Zafferano"]}],
        "cena": [{"title": "Frittata di Patate", "ingredients": ["Uova", "Patate"]}],
        "merenda": [{"title": "Gallette di Mais", "ingredients": ["Gallette"]}]
    }
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. Analisi Volantini
    offerte = analizza_volantini()
    
    # 2. Carica e Unisci Ricette
    db_prin = carica_vecchio_db()
    db_prin = importa_ricette_utenti(db_prin)
    nuove = crea_nuove_ricette(offerte)
    db_prin = unisci_db(db_prin, nuove)

    # 3. Output Finale
    output = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": db_prin
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"💾 Dati salvati con successo in: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

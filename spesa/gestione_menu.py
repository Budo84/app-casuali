import os
import json
import google as genai
from datetime import datetime
import sys
import glob
import random

print("--- 👨‍🍳 AVVIO GESTORE MENU E RICETTE ---")

if "GEMINI_KEY" in os.environ:
    # Nuova inizializzazione Client
    client = genai.Client(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

# Usa il modello TEXT standard (funziona sempre, non dà errore 404)
model = genai.GenerativeModel("gemini-pro")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- LEGGE LE OFFERTE (SOLO PER ISPIRAZIONE) ---
def get_ingredienti_offerte():
    try:
        # Cerca il file delle offerte generato dall'altro script
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offerte.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = []
            for store in data:
                for prod in data[store]:
                    items.append(prod['name'])
            return items
    except:
        return []

# --- GESTIONE DATABASE RICETTE (LOGICA AUTOMAZIONE 1.PY) ---
def carica_db_esistente():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati_settimanali.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("database_ricette", DATABASE_BACKUP)
    except:
        return DATABASE_BACKUP

def importa_ricette_utenti(db):
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "ricette_utenti")
        if not os.path.exists(path): path = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
        
        if os.path.exists(path):
            files = glob.glob(os.path.join(path, "*.json"))
            print(f"📥 Trovate {len(files)} ricette utente da importare.")
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as fo:
                        j = json.load(fo)
                        # Supporto sia per formato singolo che lista
                        ric = j.get('recipe')
                        cats = j.get('categories', [j.get('category')])
                        types = j.get('types', [j.get('type')])
                        
                        if ric:
                            for c in cats:
                                if c and c not in db: db[c] = {}
                                for t in types:
                                    if t:
                                        if t not in db[c]: db[c][t] = []
                                        # Evita duplicati
                                        if not any(x['title'] == ric['title'] for x in db[c][t]):
                                            db[c][t].append(ric)
                except: pass
    except Exception as e:
        print(f"⚠️ Errore import utenti: {e}")
    return db

def genera_nuove_ricette(ingredienti):
    print("🍳 Chef AI al lavoro...")
    context = ""
    if ingredienti:
        sample = random.sample(ingredienti, min(len(ingredienti), 15))
        context = f"Usa questi ingredienti in offerta: {', '.join(sample)}."
        
    try:
        prompt = f"""
        Crea 3 ricette per categoria.
        {context}
        Categorie: mediterranea, vegetariana, mondo, senza_glutine (solo riso/mais/patate).
        Pasti: colazione, pranzo, cena, merenda.
        JSON: {{ "mediterranea": {{ "pranzo": [{{ "title": "...", "ingredients": [...] }}] }} }}
        """
        res = model.generate_content(prompt)
        return json.loads(pulisci_json(res.text))
    except Exception as e:
        print(f"⚠️ Errore AI: {e}")
        return {}

def unisci(old, new):
    if not new: return old
    for c in new:
        if c not in old: old[c] = {}
        for t in new[c]:
            if t not in old[c]: old[c][t] = []
            for r in new[c][t]:
                if not any(x['title'] == r['title'] for x in old[c][t]):
                    old[c][t].append(r)
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

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Carica ingredienti (se ci sono offerte)
    ingr = get_ingredienti_offerte()
    
    # 2. Gestione DB
    db = carica_db_esistente()
    db = importa_ricette_utenti(db)
    nuove = genera_nuove_ricette(ingr)
    db = unisci(db, nuove)
    
    # 3. Salva
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    # Manteniamo la struttura che l'HTML si aspetta
    out = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "database_ricette": db
    }
    
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
    print(f"✅ Menu salvato in {file_out}")

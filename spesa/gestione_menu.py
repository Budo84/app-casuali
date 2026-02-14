import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import random

print("--- 👨‍🍳 AVVIO GESTORE MENU (LIBRERIA CLASSICA) ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

# Usa Gemini Pro standard (testuale, affidabile al 100%)
model = genai.GenerativeModel("gemini-pro")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def get_ingredienti_offerte():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offerte.json")
        with open(path, "r") as f:
            data = json.load(f)
            items = []
            for store in data:
                for prod in data[store]: items.append(prod['name'])
            return items
    except: return []

def carica_db():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati_settimanali.json")
        with open(path, "r") as f: return json.load(f).get("database_ricette", DB_BACKUP)
    except: return DB_BACKUP

def importa_ricette_utenti(db):
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "ricette_utenti")
        if not os.path.exists(path): path = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
        if os.path.exists(path):
            files = glob.glob(os.path.join(path, "*.json"))
            for f in files:
                try:
                    with open(f, "r") as fo:
                        j = json.load(fo)
                        r = j.get('recipe')
                        cats = j.get('categories', [j.get('category')])
                        types = j.get('types', [j.get('type')])
                        if r:
                            for c in cats:
                                if c and c not in db: db[c] = {}
                                for t in types:
                                    if t and t not in db[c]: db[c][t] = []
                                    if t and not any(x['title'] == r['title'] for x in db[c][t]): 
                                        db[c][t].append(r)
                except: pass
    except: pass
    return db

def genera_nuove(ingr):
    print("🍳 Chef AI al lavoro...")
    context = ""
    if ingr:
        sample = random.sample(ingr, min(len(ingr), 15))
        context = f"Usa ingredienti: {', '.join(sample)}."
    try:
        prompt = f"""
        Crea 3 ricette per categoria. {context}
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
                if not any(x['title'] == r['title'] for x in old[c][t]): old[c][t].append(r)
    return old

DB_BACKUP = {
    "mediterranea": {"pranzo": [{"title": "Pasta Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}]},
    "senza_glutine": {"pranzo": [{"title": "Risotto", "ingredients": ["Riso"]}]}
}

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    ingr = get_ingredienti_offerte()
    db = carica_db()
    db = importa_ricette_utenti(db)
    nuove = genera_nuove(ingr)
    db = unisci(db, nuove)
    
    out = { "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"), "database_ricette": db }
    with open(os.path.join(base, "dati_settimanali.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
    print("✅ Menu salvato.")

import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import random

print("--- 👨‍🍳 AVVIO GESTORE MENU (CREATIVO) ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

# Temperatura alta = Più varietà
generation_config = {"temperature": 0.9, "top_p": 1, "top_k": 32, "max_output_tokens": 4096}
model = genai.GenerativeModel("gemini-pro", generation_config=generation_config)

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
                                    if not any(x['title'] == r['title'] for x in db[c][t]): 
                                        db[c][t].append(r)
                except: pass
    except: pass
    return db

def genera_nuove(ingr):
    print("🍳 Chef AI al lavoro per nuove idee...")
    
    # TEMA CASUALE PER VARIARE
    temi = ["Tradizione Rustica", "Cucina Veloce", "Sapori Esotici", "Comfort Food", "Gourmet Casalingo", "Leggero e Fresco"]
    tema_scelto = random.choice(temi)
    print(f"   ✨ Tema di oggi: {tema_scelto}")

    context = ""
    if ingr:
        sample = random.sample(ingr, min(len(ingr), 10))
        context = f"Ingredienti bonus da usare se possibile: {', '.join(sample)}."
        
    try:
        prompt = f"""
        Sei uno chef creativo. Inventa 3 ricette NUOVE e ORIGINALI per ogni categoria.
        Stile cucina di oggi: {tema_scelto}.
        {context}
        
        REGOLE:
        1. Non ripetere ricette banali (es. pasta al pomodoro semplice).
        2. Categorie: mediterranea, vegetariana, mondo, senza_glutine (USA SOLO: Riso, Mais, Grano Saraceno, Patate, Quinoa. VIETATO: Grano, Orzo, Farro).
        3. Pasti: colazione, pranzo, cena, merenda.
        
        RISPONDI SOLO JSON: {{ "mediterranea": {{ "pranzo": [{{ "title": "Nome Creativo", "ingredients": ["Ing1", "Ing2"] }}] }} }}
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
    print("✅ Menu aggiornato.")

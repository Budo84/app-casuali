import os
import json
import glob
import random
import time
from datetime import datetime
import requests
import sys

print("--- 👨‍🍳 AVVIO GESTORE MENU (METODO DIRETTO REST API) ---")

API_KEY = os.environ.get("GEMINI_KEY")
if not API_KEY:
    print("❌ Chiave mancante. Controlla che la secret 'GEMINI_KEY' sia impostata su GitHub (Settings > Secrets and variables > Actions).")
    sys.exit(1)  # prima era sys.exit(0): il job risultava "verde" anche senza chiave

# gemini-1.5-flash è stato ritirato da Google: proviamo più modelli in ordine.
MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
]
MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 5


def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1:
        return text[s:e]
    return text


def estrai_testo_risposta(res_json):
    """Concatena TUTTE le parti di testo della risposta, non solo la prima."""
    try:
        parts = res_json["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p)
    except (KeyError, IndexError, TypeError):
        return ""


def get_ingredienti_offerte():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offerte.json")
        with open(path, "r") as f:
            data = json.load(f)
            items = []
            for store in data:
                for prod in data[store]:
                    items.append(prod['name'])
            return items
    except Exception:
        return []


def carica_db():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati_settimanali.json")
        with open(path, "r") as f:
            return json.load(f).get("database_ricette", DB_BACKUP)
    except Exception:
        return DB_BACKUP


def importa_ricette_utenti(db):
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "ricette_utenti")
        if not os.path.exists(path):
            path = os.path.join(os.getcwd(), "spesa", "ricette_utenti")
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
                                if c and c not in db:
                                    db[c] = {}
                                for t in types:
                                    if t and t not in db[c]:
                                        db[c][t] = []
                                    if t and not any(x['title'] == r['title'] for x in db[c][t]):
                                        db[c][t].append(r)
                except Exception:
                    pass
    except Exception:
        pass
    return db


def chiama_gemini(model_name, prompt_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.9},
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }

    for tentativo in range(1, MAX_RETRIES_PER_MODEL + 1):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Errore di rete con {model_name} (tentativo {tentativo}): {e}")
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        if res.status_code == 200:
            return res.json()
        elif res.status_code == 404:
            print(f"   ⚠️ Modello '{model_name}' non disponibile (404). Passo al prossimo.")
            return None
        elif res.status_code == 429:
            print(f"   ⏳ Rate limit (429) su {model_name}, riprovo tra {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)
            continue
        else:
            print(f"   ⚠️ Errore HTTP {res.status_code} con {model_name}: {res.text[:300]}")
            return None

    return None


def genera_nuove(ingr):
    print("🍳 Chef AI genera nuove idee...")
    context = ""
    if ingr:
        sample = random.sample(ingr, min(len(ingr), 10))
        context = f"Cerca di usare alcuni di questi ingredienti: {', '.join(sample)}."

    prompt = f"""
    Sei uno Chef molto creativo. Inventa 3 ricette nuove per categoria. {context}
    Categorie: mediterranea, vegetariana, mondo, senza_glutine (USA SOLO: Riso, Mais, Grano Saraceno, Patate. VIETATO Grano/Pasta).
    Pasti: colazione, pranzo, cena, merenda.
    RISPONDI TASSATIVAMENTE SOLO CON QUESTO JSON, SENZA TESTO PRIMA O DOPO:
    {{ "mediterranea": {{ "pranzo": [{{ "title": "...", "ingredients": [...] }}] }} }}
    """

    for model in MODELS:
        res_json = chiama_gemini(model, prompt)
        if not res_json:
            continue
        ai_text = estrai_testo_risposta(res_json)
        if not ai_text:
            print(f"   ⚠️ Risposta vuota dal modello '{model}'.")
            continue
        try:
            data = json.loads(pulisci_json(ai_text))
            print(f"   ✅ Nuove ricette generate con '{model}'.")
            return data
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON non valido dal modello '{model}': {e}")
            print(f"   --- Risposta grezza (primi 500 char) ---\n{ai_text[:500]}")
            continue

    print("❌ Nessun modello ha prodotto ricette valide. Il menu esistente resta invariato.")
    return {}


def unisci(old, new):
    if not new:
        return old
    for c in new:
        if c not in old:
            old[c] = {}
        for t in new[c]:
            if t not in old[c]:
                old[c][t] = []
            for r in new[c][t]:
                if not any(x['title'] == r['title'] for x in old[c][t]):
                    old[c][t].append(r)
    return old


DB_BACKUP = {
    "mediterranea": {"pranzo": [{"title": "Pasta Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}]},
    "senza_glutine": {"pranzo": [{"title": "Risotto Zafferano", "ingredients": ["Riso", "Zafferano"]}]}
}

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    ingr = get_ingredienti_offerte()
    db = carica_db()
    db = importa_ricette_utenti(db)
    nuove = genera_nuove(ingr)
    db = unisci(db, nuove)

    out = {"data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"), "database_ricette": db}
    with open(os.path.join(base, "dati_settimanali.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
    print("✅ Menu aggiornato.")

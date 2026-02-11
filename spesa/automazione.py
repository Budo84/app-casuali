import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

# --- CONFIGURAZIONE ---
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

def trova_modello():
    try:
        mods = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best = next((m for m in mods if "flash" in m), next((m for m in mods if "pro" in m), mods[0]))
        return genai.GenerativeModel(best)
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

model = trova_modello()

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    # Cerchiamo l'inizio e la fine dell'oggetto JSON
    start = testo.find('{')
    end = testo.rfind('}') + 1
    if start != -1 and end != -1:
        return testo[start:end]
    return testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    # 1. OFFERTE PER SUPERMERCATO
    print(f"🤖 Uso modello: {model.model_name}")
    supermercati = ["Conad", "Coop", "Esselunga", "Lidl", "Eurospin"]
    
    prompt_offerte = f"""
    Genera un database JSON di offerte alimentari realistiche per questi supermercati italiani: {', '.join(supermercati)}.
    Per ogni supermercato includi 8 prodotti diversi con prezzi realistici in Euro.
    
    RISPONDI ESATTAMENTE IN QUESTO FORMATO JSON (SOLO IL JSON):
    {{
      "Conad": [{{"name": "Pasta", "price": 0.85}}],
      "Coop": [{{"name": "Pasta", "price": 0.80}}],
      ...
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
        print("✅ Offerte generate con successo per tutti gli store.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}. Uso fallback.")
        offerte_db = {s: [{"name": "Pasta", "price": 0.90}] for s in supermercati}

    # Estraiamo i prodotti per le ricette
    ingredienti_base = []
    for s in offerte_db:
        for p in offerte_db[s]:
            ingredienti_base.append(p['name'])
    
    # 2. RICETTE
    prompt_ricette = f"""
    Crea 21 ricette italiane varie usando questi ingredienti: {', '.join(list(set(ingredienti_base))[:15])}.
    Usa SOLO questi tag per 'contains': "glutine", "lattosio", "uova", "pesce", "frutta_guscio".
    RISPONDI SOLO COL JSON (Array di oggetti).
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        # Pulizia specifica per array
        testo_ric = resp_ric.text.replace("```json", "").replace("```", "").strip()
        start, end = testo_ric.find('['), testo_ric.rfind(']') + 1
        ricette = json.loads(testo_ric[start:end])
    except:
        ricette = []

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte_per_supermercato": offerte_db,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Dati salvati.")

if __name__ == "__main__":
    genera_tutto()

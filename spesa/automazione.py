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
    start = testo.find('{')
    end = testo.rfind('}') + 1
    if start != -1 and end != -1:
        return testo[start:end]
    return testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    # 1. OFFERTE PER SUPERMERCATO (LISTA AGGIORNATA)
    print(f"🤖 Uso modello: {model.model_name}")
    
    # AGGIUNTI I NUOVI SUPERMERCATI QUI SOTTO
    supermercati = [
        "Conad", "Coop", "Esselunga", "Lidl", "Eurospin", 
        "Pewex", "MA Supermercati", "Ipercarni", "Todis"
    ]
    
    prompt_offerte = f"""
    Genera un database JSON di offerte alimentari realistiche per questi supermercati: {', '.join(supermercati)}.
    Per ogni supermercato includi 6 prodotti diversi (pasta, carne, verdura, scatolame) con prezzi realistici.
    
    RISPONDI ESATTAMENTE IN QUESTO FORMATO JSON:
    {{
      "Conad": [{{"name": "Pasta", "price": 0.85}}, {{"name": "Tonno", "price": 2.50}}],
      "Pewex": [{{"name": "Bistecca", "price": 4.50}}],
      "Todis": [{{"name": "Latte", "price": 0.79}}],
      ... (fai così per tutti i {len(supermercati)} supermercati)
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
        print("✅ Offerte generate con successo.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}. Uso fallback.")
        offerte_db = {s: [{"name": "Pasta", "price": 0.90}] for s in supermercati}

    # 2. RICETTE
    # Raccogliamo ingredienti da tutti i negozi per avere varietà
    ingredienti_base = []
    for s in offerte_db:
        for p in offerte_db[s]:
            ingredienti_base.append(p['name'])
            
    prompt_ricette = f"""
    Crea 21 ricette per una famiglia italiana usando questi ingredienti in offerta: {', '.join(list(set(ingredienti_base))[:20])}.
    
    Regole JSON:
    1. Usa "title" per il nome della ricetta.
    2. "type" deve essere solo: "colazione", "pranzo", "cena".
    3. "ingredients" deve essere una LISTA DI OGGETTI con "item" e "quantity".
    4. "contains" deve segnalare SOLO se presenti: "glutine", "lattosio", "uova", "pesce", "frutta_guscio".
    
    FORMATO RISPOSTA:
    [
      {{
        "title": "Pasta al Sugo",
        "type": "pranzo",
        "ingredients": [ {{"item": "Pasta", "quantity": "100g"}}, {{"item": "Pomodoro", "quantity": "50g"}} ],
        "contains": ["glutine"],
        "description": "Piatto semplice..."
      }}
    ]
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        testo_ric = resp_ric.text.replace("```json", "").replace("```", "").strip()
        start, end = testo_ric.find('['), testo_ric.rfind(']') + 1
        ricette = json.loads(testo_ric[start:end])
        print(f"✅ {len(ricette)} ricette generate.")
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
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

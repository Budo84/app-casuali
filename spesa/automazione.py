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
    if start == -1: # Fallback per array
        start = testo.find('[')
        end = testo.rfind(']') + 1
    if start != -1 and end != -1:
        return testo[start:end]
    return testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    print(f"🤖 Modello: {model.model_name}")
    
    # 1. OFFERTE (MARCHE SPECIFICHE)
    supermercati = [
        "Conad", "Coop", "Esselunga", "Lidl", "Eurospin", 
        "Pewex", "MA Supermercati", "Ipercarni", "Todis"
    ]
    
    prompt_offerte = f"""
    Genera un database JSON di offerte per: {', '.join(supermercati)}.
    
    IMPORTANTE: Usa NOMI REALI E MARCHE (es. "Pasta Barilla", "Nutella", "Tonno Rio Mare", "Latte Granarolo", "Biscotti Mulino Bianco").
    Per ogni supermercato inserisci 6 prodotti vari con prezzi realistici.
    
    RISPONDI SOLO JSON:
    {{
      "Conad": [{{"name": "Pasta Barilla", "price": 0.79}}, {{"name": "Passata Mutti", "price": 0.99}}],
      ...
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
        print("✅ Offerte (con marche) generate.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}")
        offerte_db = {s: [{"name": "Pasta Barilla", "price": 0.90}] for s in supermercati}

    # 2. RICETTE (INGREDIENTI GENERICI)
    # Estraiamo i nomi per dare un contesto, ma chiediamo ricette generiche
    ingredienti_raw = []
    for s in offerte_db:
        for p in offerte_db[s]:
            ingredienti_raw.append(p['name'])
            
    prompt_ricette = f"""
    Crea 28 ricette italiane (colazione, pranzo, merenda, cena) ispirate a questi prodotti in offerta: {', '.join(list(set(ingredienti_raw))[:30])}.
    
    REGOLA FONDAMENTALE: 
    Nei campi "title" e "ingredients", usa SOLO TERMINI GENERICI. 
    Esempio: Se l'offerta è "Pasta Barilla", tu scrivi solo "Pasta". Se è "Nutella", scrivi "Crema di nocciole".
    
    FORMATO JSON:
    [
      {{
        "title": "Pasta al Pomodoro",
        "type": "pranzo",
        "ingredients": [ {{"item": "Pasta", "quantity": "100g"}}, {{"item": "Passata di pomodoro", "quantity": "100g"}} ],
        "contains": ["glutine"],
        "description": "..."
      }}
    ]
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        ricette = json.loads(pulisci_json(resp.text))
        print(f"✅ {len(ricette)} ricette generiche generate.")
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

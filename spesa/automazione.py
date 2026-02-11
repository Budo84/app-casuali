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

    # 1. OFFERTE
    print(f"🤖 Uso modello: {model.model_name}")
    supermercati = [
        "Conad", "Coop", "Esselunga", "Lidl", "Eurospin", 
        "Pewex", "MA Supermercati", "Ipercarni", "Todis"
    ]
    
    prompt_offerte = f"""
    Genera un database JSON di offerte alimentari realistiche per: {', '.join(supermercati)}.
    Per ogni supermercato includi 6 prodotti (pasta, carne, verdura, frutta, snack).
    
    RISPONDI SOLO JSON:
    {{
      "Conad": [{{"name": "Pasta", "price": 0.85}}, {{"name": "Mele", "price": 1.50}}],
      ...
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
        print("✅ Offerte generate.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}")
        offerte_db = {s: [{"name": "Pasta", "price": 0.90}] for s in supermercati}

    # 2. RICETTE (Include MERENDA)
    ingredienti_base = []
    for s in offerte_db:
        for p in offerte_db[s]:
            ingredienti_base.append(p['name'])
            
    prompt_ricette = f"""
    Crea 28 ricette italiane per una famiglia (colazione, pranzo, merenda, cena) usando: {', '.join(list(set(ingredienti_base))[:25])}.
    
    REGOLE JSON:
    1. Usa "title" per il nome.
    2. "type" deve essere SOLO: "colazione", "pranzo", "merenda", "cena".
    3. "ingredients": lista di oggetti {{"item": "Nome", "quantity": "..."}}.
    4. "contains": lista allergeni ("glutine", "lattosio", "uova", "pesce", "frutta_guscio").
    
    FORMATO:
    [
      {{
        "title": "Yogurt e Frutta",
        "type": "merenda",
        "ingredients": [ {{"item": "Yogurt", "quantity": "1 vasetto"}} ],
        "contains": ["lattosio"],
        "description": "Snack sano..."
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

import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import random

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
    # Cerca parentesi quadre per array (ricette) o graffe per oggetti (offerte)
    if testo.startswith("{"):
        start = testo.find('{')
        end = testo.rfind('}') + 1
    else:
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
    Genera un database JSON di offerte reali per: {', '.join(supermercati)}.
    Usa NOMI DI MARCA (es. "Pasta Barilla", "Tonno Rio Mare", "Biscotti Mulino Bianco").
    Per ogni supermercato inserisci 6 prodotti vari con prezzi realistici.
    
    RISPONDI SOLO JSON:
    {{
      "Conad": [{{"name": "Pasta Barilla 500g", "price": 0.79}}],
      ...
    }}
    """
    
    try:
        print("1. Genero Offerte...")
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}")
        offerte_db = {s: [{"name": "Pasta Barilla", "price": 0.90}] for s in supermercati}

    # 2. RICETTE (INGREDIENTI GENERICI)
    # Estraiamo i nomi grezzi
    ingredienti_raw = []
    for s in offerte_db:
        for p in offerte_db[s]:
            # Pulizia grezza del nome per dare spunto (es. "Pasta Barilla" -> "Pasta")
            nome = p['name'].split()[0] 
            if len(nome) > 3: ingredienti_raw.append(nome)
    
    ingredienti_input = ', '.join(list(set(ingredienti_raw))[:40])
    
    prompt_ricette = f"""
    Sei uno Chef. Crea un menu settimanale (28 ricette: colazione, pranzo, merenda, cena).
    
    INGREDIENTI DA USARE:
    Usa come ispirazione questi ingredienti in offerta: {ingredienti_input}.
    IMPORTANTE: Puoi usare anche ingredienti comuni da dispensa (farina, uova, olio, verdure base) per completare le ricette.
    
    REGOLE FONDAMENTALI:
    1. Usa SOLO nomi GENERICI per gli ingredienti (es. scrivi "Pasta", NON "Pasta Barilla").
    2. NON inserire prezzi nelle ricette.
    3. Il formato deve essere una LISTA DI OGGETTI.
    
    RISPONDI SOLO CON QUESTO JSON:
    [
      {{
        "title": "Pasta al Pomodoro",
        "type": "pranzo",
        "ingredients": ["Pasta", "Passata di pomodoro", "Basilico"],
        "contains": ["glutine"],
        "description": "Piatto semplice..."
      }},
      {{
        "title": "Yogurt e Cereali",
        "type": "colazione",
        "ingredients": ["Yogurt", "Cereali"],
        "contains": ["lattosio"],
        "description": "..."
      }}
    ]
    """
    
    print("2. Genero Ricette...")
    try:
        resp_ric = model.generate_content(prompt_ricette)
        ricette = json.loads(pulisci_json(resp.text))
        
        # Controllo di sicurezza: se ricette è un dizionario (errore AI), lo forziamo a lista
        if isinstance(ricette, dict):
            print("⚠️ AI ha sbagliato formato (dict invece di list). Tento fix.")
            nuova_lista = []
            for k in ricette: # Se ha raggruppato per chiavi strane
                if isinstance(ricette[k], list):
                    nuova_lista.extend(ricette[k])
            ricette = nuova_lista

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
    print("💾 Salvato.")

if __name__ == "__main__":
    genera_tutto()

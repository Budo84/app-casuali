import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import time

# --- 1. CONFIGURAZIONE ---
if "GEMINI_KEY" not in os.environ:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=os.environ["GEMINI_KEY"])

# --- 2. SELEZIONE MODELLO ROBUSTA ---
def get_working_model():
    print("🔍 Cerco un modello funzionante...")
    
    # Lista di modelli da provare in ordine di preferenza
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-pro",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro",
        "models/gemini-pro"
    ]
    
    for model_name in candidates:
        try:
            print(f"   Provo modello: {model_name}...")
            model = genai.GenerativeModel(model_name)
            # Test rapido per vedere se risponde
            response = model.generate_content("Test", generation_config={"max_output_tokens": 5})
            if response and response.text:
                print(f"   ✅ Modello OK: {model_name}")
                return model
        except Exception as e:
            # Ignora l'errore e prova il prossimo
            continue
            
    print("❌ NESSUN MODELLO FUNZIONANTE TROVATO.")
    sys.exit(1)

model = get_working_model()

# --- 3. PULIZIA JSON ---
def pulisci_json(testo):
    # Rimuove markdown JSON se presente
    testo = testo.replace("```json", "").replace("```", "").strip()
    
    # Cerca l'inizio e la fine del JSON (oggetto o array)
    start_obj = testo.find('{')
    start_arr = testo.find('[')
    
    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        start = start_obj
        end = testo.rfind('}') + 1
    elif start_arr != -1:
        start = start_arr
        end = testo.rfind(']') + 1
    else:
        return testo # Nessun JSON trovato
        
    if start != -1 and end != -1:
        return testo[start:end]
    return testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    supermercati = [
        "Conad", "Coop", "Esselunga", "Lidl", "Eurospin", 
        "Pewex", "MA Supermercati", "Ipercarni", "Todis"
    ]

    # --- FASE 1: OFFERTE ---
    print("1. Genero OFFERTE...")
    prompt_offerte = f"""
    Genera un JSON con offerte per questi supermercati: {', '.join(supermercati)}.
    Usa MARCHE REALI ITALIANE (es. Barilla, Mutti, Granarolo).
    Per ogni supermercato inserisci 6 prodotti con prezzi realistici.
    
    RISPONDI SOLO CON IL JSON, SENZA ALTRO TESTO.
    Struttura:
    {{
      "Conad": [ {{"name": "Pasta Barilla 500g", "price": 0.89}}, ... ],
      "Coop": [ ... ]
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        text = pulisci_json(resp.text)
        offerte_db = json.loads(text)
        print("✅ Offerte generate.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}")
        # Non usiamo fallback, lasciamo vuoto se fallisce per vedere l'errore
        offerte_db = {} 

    # --- FASE 2: RICETTE (DIETA MEDITERRANEA) ---
    print("2. Genero MENU MEDITERRANEO...")
    
    prompt_ricette = """
    Crea un menu settimanale DIETA MEDITERRANEA.
    Usa ingredienti GENERICI (es. "Pasta", non "Pasta Barilla").
    
    Devi restituire un JSON con queste 4 liste:
    1. "colazione": 7 ricette dolci (Latte, Caffè, Biscotti).
    2. "pranzo": 7 ricette carboidrati (Pasta, Riso).
    3. "merenda": 7 ricette leggere (Frutta, Yogurt).
    4. "cena": 7 ricette proteine (Carne, Pesce, Uova) + verdure.

    RISPONDI SOLO CON IL JSON.
    Struttura:
    {
      "colazione": [ {"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"], "contains": ["lattosio", "glutine"]} ],
      "pranzo": [ ... ],
      "merenda": [ ... ],
      "cena": [ ... ]
    }
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        text_ric = pulisci_json(resp_ric.text)
        ricette_raw = json.loads(text_ric)
        
        lista_ricette = []
        for categoria in ["colazione", "pranzo", "merenda", "cena"]:
            for piatto in ricette_raw.get(categoria, []):
                piatto['type'] = categoria
                lista_ricette.append(piatto)
                
        print(f"✅ Menu generato: {len(lista_ricette)} ricette.")
        
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        lista_ricette = []

    # --- SALVATAGGIO ---
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_db,
        "ricette": lista_ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 File salvato.")

if __name__ == "__main__":
    genera_tutto()

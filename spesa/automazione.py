import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

# --- CONFIGURAZIONE ---
print("--- INIZIO DIAGNOSTICA ---")

# 1. VERIFICA CHIAVE API
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
    print(f"✅ Chiave API trovata (lunghezza: {len(API_KEY)})")
else:
    print("❌ ERRORE FATALE: La variabile 'GEMINI_KEY' non esiste nei Secrets di GitHub.")
    print("Vai su Settings > Secrets and variables > Actions e aggiungi GEMINI_KEY.")
    sys.exit(1) # Blocca tutto e dai errore rosso

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def pulisci_json(testo):
    # Rimuove i backticks di markdown che spesso rompono tutto
    testo = testo.replace("```json", "").replace("```", "").strip()
    return testo

def genera_tutto():
    cartella_script = os.path.dirname(os.path.abspath(__file__))
    file_output = os.path.join(cartella_script, "dati_settimanali.json")

    # --- GENERAZIONE OFFERTE ---
    print("\n1. Richiedo OFFERTE a Gemini...")
    try:
        prompt_offerte = """
        Rispondi SOLO con un array JSON valido. Non scrivere altro testo.
        Genera 5 prodotti da supermercato in offerta.
        Esempio: [{"name": "Pasta Barilla", "price": 0.89}]
        """
        response = model.generate_content(prompt_offerte)
        print(f"   Risposta Grezza Gemini: {response.text[:100]}...") # Stampa i primi 100 caratteri per controllo
        
        json_pulito = pulisci_json(response.text)
        offerte = json.loads(json_pulito)
        print(f"✅ Offerte Parsate correttamente: {len(offerte)} elementi.")
        nomi_prodotti = [o['name'] for o in offerte]
        
    except Exception as e:
        print(f"❌ ERRORE OFFERTE: {e}")
        print("   Dettaglio risposta che ha causato errore:", response.text if 'response' in locals() else "Nessuna risposta")
        sys.exit(1) # Blocca tutto per farti vedere l'errore

    # --- GENERAZIONE RICETTE ---
    print("\n2. Richiedo RICETTE a Gemini...")
    try:
        prompt_ricette = f"""
        Rispondi SOLO con un array JSON valido.
        Crea 10 ricette usando: {', '.join(nomi_prodotti)}.
        Usa ESATTAMENTE questi tag per 'contains': "glutine", "lattosio", "uova", "pesce", "frutta_guscio".
        Format: [{{"name": "Pasta", "type": "pranzo", "contains": ["glutine"], "ingredients": ["pasta"], "desc": "..."}}]
        """
        response = model.generate_content(prompt_ricette)
        
        json_pulito = pulisci_json(response.text)
        ricette = json.loads(json_pulito)
        print(f"✅ Ricette Parsate correttamente: {len(ricette)} elementi.")
        
    except Exception as e:
        print(f"❌ ERRORE RICETTE: {e}")
        print("   Dettaglio risposta:", response.text if 'response' in locals() else "Nessuna risposta")
        sys.exit(1)

    # --- SALVATAGGIO ---
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte": offerte,
        "ricette": ricette
    }

    if not os.path.exists(os.path.dirname(file_output)):
        os.makedirs(os.path.dirname(file_output))

    with open(file_output, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
        
    print(f"\n💾 FILE SCRITTO CORRETTAMENTE: {file_output}")
    print("--- FINE DIAGNOSTICA ---")

if __name__ == "__main__":
    genera_tutto()

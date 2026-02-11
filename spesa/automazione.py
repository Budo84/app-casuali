import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

# --- CONFIGURAZIONE ---
print("--- INIZIO DIAGNOSTICA ---")

if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
    print(f"✅ Chiave API trovata (lunghezza: {len(API_KEY)})")
else:
    print("❌ ERRORE FATALE: La variabile 'GEMINI_KEY' non esiste nei Secrets di GitHub.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# USO IL MODELLO STANDARD 'GEMINI-PRO' PER EVITARE ERRORI DI VERSIONE
model = genai.GenerativeModel('gemini-pro')

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    # A volte gemini mette testo prima o dopo, cerchiamo le parentesi
    start = testo.find('[')
    end = testo.rfind(']') + 1
    if start != -1 and end != -1:
        return testo[start:end]
    return testo

def genera_tutto():
    cartella_script = os.path.dirname(os.path.abspath(__file__))
    file_output = os.path.join(cartella_script, "dati_settimanali.json")

    # --- GENERAZIONE OFFERTE ---
    print("\n1. Richiedo OFFERTE a Gemini...")
    try:
        prompt_offerte = """
        Agisci come un database JSON. 
        Genera una lista di 15 prodotti alimentari tipici italiani da supermercato.
        Assegna un prezzo realistico.
        Rispondi SOLO con il JSON: [{"name": "Pasta Barilla", "price": 0.89}, ...]
        """
        response = model.generate_content(prompt_offerte)
        print("   Ricevuto dati offerte...")
        
        offerte = json.loads(pulisci_json(response.text))
        print(f"✅ Offerte Parsate: {len(offerte)}")
        nomi_prodotti = [o['name'] for o in offerte]
        
    except Exception as e:
        print(f"❌ ERRORE OFFERTE: {e}")
        # Fallback per non bloccare tutto
        offerte = [{"name": "Pasta", "price": 1.00}, {"name": "Pollo", "price": 5.00}]
        nomi_prodotti = ["Pasta", "Pollo"]

    # --- GENERAZIONE RICETTE ---
    print("\n2. Richiedo RICETTE a Gemini...")
    try:
        prompt_ricette = f"""
        Agisci come un database JSON.
        Crea 21 ricette (colazione, pranzo, cena) usando: {', '.join(nomi_prodotti)}.
        
        Usa ESATTAMENTE questi tag in 'contains': "glutine", "lattosio", "uova", "pesce", "frutta_guscio".
        
        Rispondi SOLO con il JSON: 
        [{{"name": "Nome", "type": "pranzo", "contains": ["glutine"], "ingredients": ["pasta"], "desc": "..."}}]
        """
        response = model.generate_content(prompt_ricette)
        
        ricette = json.loads(pulisci_json(response.text))
        print(f"✅ Ricette Parsate: {len(ricette)}")
        
    except Exception as e:
        print(f"❌ ERRORE RICETTE: {e}")
        print("Testo ricevuto:", response.text if 'response' in locals() else "Nulla")
        sys.exit(1)

    # --- SALVATAGGIO ---
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
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

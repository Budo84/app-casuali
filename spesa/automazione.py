import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

# 1. VERIFICA CHIAVE
if "GEMINI_KEY" not in os.environ:
    print("❌ ERRORE: Manca la GEMINI_KEY nei Secrets!")
    sys.exit(1)

genai.configure(api_key=os.environ["GEMINI_KEY"])

# 2. CONFIGURAZIONE MODELLO
# Usiamo il modello base 'gemini-pro' che è il più stabile
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel("gemini-1.5-flash", generation_config=generation_config)

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    print("🚀 Inizio generazione...")

    # TEST OFFERTE
    try:
        print("1. Richiedo OFFERTE...")
        prompt = """
        Genera un JSON con offerte per: Conad, Coop, Esselunga, Lidl.
        Struttura: { "Conad": [{"name": "Pasta Barilla", "price": 0.90}] }
        """
        response = model.generate_content(prompt)
        print(f"   Risposta ricevuta! Lunghezza: {len(response.text)}")
        offerte = json.loads(response.text)
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO OFFERTE: {e}")
        # Se c'è un errore qui, STAMPA TUTTO per capire
        if 'response' in locals() and hasattr(response, 'prompt_feedback'):
            print(f"   Feedback Sicurezza: {response.prompt_feedback}")
        sys.exit(1) # Blocca tutto così vediamo l'errore nel log rosso

    # TEST RICETTE
    try:
        print("2. Richiedo RICETTE...")
        prompt_ricette = """
        Genera un JSON con 4 liste di ricette (colazione, pranzo, merenda, cena).
        Struttura: { "colazione": [{"title": "Caffè", "ingredients": ["Caffè"], "contains": []}] }
        """
        response = model.generate_content(prompt_ricette)
        ricette_raw = json.loads(response.text)
        
        # Trasformazione
        ricette_finali = []
        for k, v in ricette_raw.items():
            for r in v:
                r['type'] = k
                ricette_finali.append(r)
                
        print(f"   Ricette generate: {len(ricette_finali)}")

    except Exception as e:
        print(f"\n❌ ERRORE CRITICO RICETTE: {e}")
        sys.exit(1)

    # SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette_finali
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)
    print("✅ FILE SALVATO CORRETTAMENTE!")

if __name__ == "__main__":
    genera_tutto()

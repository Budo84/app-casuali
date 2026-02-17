import os
import json
import glob
import base64
import requests

# --- CONFIGURAZIONE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_FILE = os.path.join(BASE_DIR, 'output', 'offerte.json')
API_KEY = os.environ.get("GEMINI_API_KEY")

# LISTA DI RISERVA: Se il primo non va, prova gli altri
MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-1.0-pro-vision-latest" # Vecchio ma solido per le immagini
]

if not API_KEY:
    print("❌ ERRORE: Manca la GEMINI_API_KEY!")
    exit(1)

def encode_pdf_to_base64(pdf_path):
    """Converte il PDF in una stringa Base64 per inviarlo via web"""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def call_gemini_vision(model_name, base64_data):
    """Chiama l'API REST direttamente (senza libreria Google)"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": """
                    Sei un assistente AI specializzato in data entry.
                    Analizza le immagini di questo PDF (volantino offerte).
                    Estrai un array JSON con i prodotti.
                    
                    Struttura JSON richiesta:
                    [
                      {"prodotto": "Nome Marca", "prezzo": 1.99, "dettagli": "kg/pz"}
                    ]

                    Regole:
                    1. Cerca i prezzi grandi e associali al testo vicino.
                    2. Unisci nome e marca.
                    3. Ignora indirizzi e orari.
                    4. Rispondi SOLO con il JSON valido.
                    """
                },
                {
                    "inline_data": {
                        "mime_type": "application/pdf",
                        "data": base64_data
                    }
                }
            ]
        }]
    }

    print(f"📡 Tentativo connessione a: {model_name}...")
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"⚠️ Modello {model_name} non trovato (404).")
            return None
        else:
            print(f"⚠️ Errore HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Errore di connessione: {e}")
        return None

def main():
    # 1. Cerca PDF
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdf_files:
        print("⚠️ Nessun PDF trovato.")
        return

    pdf_path = pdf_files[0]
    print(f"📄 File trovato: {os.path.basename(pdf_path)}")

    # 2. Prepara il file (Base64)
    try:
        base64_data = encode_pdf_to_base64(pdf_path)
        print(f"📦 PDF codificato ({len(base64_data)} bytes).")
    except Exception as e:
        print(f"❌ Errore lettura file: {e}")
        exit(1)

    final_result = None

    # 3. Loop tentativi modelli
    for model in MODELS:
        result = call_gemini_vision(model, base64_data)
        if result and 'candidates' in result:
            final_result = result
            print(f"✅ SUCCESSO con il modello: {model}!")
            break # Usciamo dal loop appena uno funziona
        else:
            print("🔄 Passo al prossimo modello...")

    # 4. Gestione Risultato
    if not final_result:
        print("❌ TUTTI I MODELLI HANNO FALLITO.")
        exit(1)

    try:
        content_text = final_result['candidates'][0]['content']['parts'][0]['text']
        clean_json = content_text.replace("```json", "").replace("```", "").strip()
        
        # Validazione
        parsed = json.loads(clean_json)
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
            
        print("💾 File offerte.json salvato correttamente.")

    except Exception as e:
        print(f"❌ Errore salvataggio JSON: {e}")
        # Stampa raw per debug
        print(content_text)
        exit(1)

if __name__ == "__main__":
    main()

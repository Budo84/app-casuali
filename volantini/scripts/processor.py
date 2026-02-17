import os
import json
import glob
import time
import google.generativeai as genai
from google.api_core import exceptions

# CONFIGURAZIONE PERCORSI
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_FILE = os.path.join(BASE_DIR, 'output', 'offerte.json')

# Lista di modelli da provare in ordine di priorità
MODELS_TO_TRY = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro-latest"
]

# CONFIGURAZIONE API
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ ERRORE: Manca la GEMINI_API_KEY nei Secrets di GitHub!")
    exit(1)

genai.configure(api_key=api_key)

def main():
    # 1. Cerca il file PDF
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    
    if not pdf_files:
        print("⚠️ Nessun PDF trovato nella cartella input.")
        return

    pdf_path = pdf_files[0]
    print(f"📄 Elaborazione file: {os.path.basename(pdf_path)}")

    # 2. Carica il file su Gemini
    print("☁️ Caricamento file su Google AI...")
    try:
        sample_file = genai.upload_file(path=pdf_path, display_name="Volantino")
        print(f"✅ File caricato: {sample_file.uri}")
        
        # Attendi che il file sia processato (Active)
        while sample_file.state.name == "PROCESSING":
            print("⏳ Elaborazione file lato Google...")
            time.sleep(2)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED":
            raise ValueError("Stato file: FAILED")
            
    except Exception as e:
        print(f"❌ Errore upload: {e}")
        exit(1)

    # 3. Tentativi con diversi modelli
    json_result = None
    
    prompt = """
    Sei un estrattore dati per supermercati. Analizza questo file PDF.
    Estrai un elenco JSON con: prodotto, prezzo (numero), unita.
    Regole:
    - Ignora indirizzi, orari e numeri di telefono.
    - Se trovi prodotti vicini ai prezzi, uniscili (es. "Pasta" + "Barilla" -> "Pasta Barilla").
    - Rispondi SOLO JSON valido, senza markdown.
    """

    for model_name in MODELS_TO_TRY:
        print(f"🔄 Tento con il modello: {model_name}...")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([sample_file, prompt])
            
            # Se siamo qui, ha funzionato
            json_result = response.text
            print(f"✅ Successo con {model_name}!")
            break 
            
        except exceptions.NotFound:
            print(f"⚠️ Modello {model_name} non trovato (404). Provo il prossimo...")
        except Exception as e:
            print(f"⚠️ Errore con {model_name}: {str(e)}")

    # 4. Gestione Risultato
    if not json_result:
        print("❌ TUTTI I MODELLI HANNO FALLITO.")
        # Pulizia
        try:
            genai.delete_file(sample_file.name)
        except:
            pass
        exit(1)

    try:
        # Pulizia stringa JSON
        clean_json = json_result.replace("```json", "").replace("```", "").strip()
        
        # Verifica validità
        json.loads(clean_json)

        # Salvataggio
        output_dir = os.path.dirname(OUTPUT_FILE)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(clean_json)
            
        print("💾 File offerte.json salvato correttamente.")

    except Exception as e:
        print(f"❌ Errore nel salvataggio JSON: {e}")
        print(f"Raw output: {json_result}")
        exit(1)
    finally:
        # Pulizia file remoto
        try:
            genai.delete_file(sample_file.name)
            print("🧹 File remoto eliminato.")
        except:
            pass

if __name__ == "__main__":
    main()

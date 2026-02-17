import os
import json
import glob
import google.generativeai as genai

# CONFIGURAZIONE PERCORSI
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_FILE = os.path.join(BASE_DIR, 'output', 'offerte.json')

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

    # 2. Carica il file su Gemini (Python SDK gestisce l'upload temporaneo)
    print("☁️ Caricamento file su Google AI...")
    try:
        sample_file = genai.upload_file(path=pdf_path, display_name="Volantino")
        print(f"✅ File caricato: {sample_file.uri}")
    except Exception as e:
        print(f"❌ Errore upload: {e}")
        exit(1)

    # 3. Configura il modello
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = """
    Analizza questo volantino supermercato.
    Estrai un elenco JSON con: prodotto, prezzo, unita.
    Regole:
    - Unisci nome prodotto e marca (es: "Acqua" + "Santagata" -> "Acqua Santagata").
    - Il prezzo deve essere un numero (es. 1.99).
    - Ignora orari, indirizzi e numeri di telefono.
    - Rispondi SOLO con il JSON valido, senza markdown ```json.
    """

    print("🤖 Analisi in corso...")
    
    try:
        response = model.generate_content([sample_file, prompt])
        
        # Pulizia risposta
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        
        # Verifica validità JSON
        json.loads(json_text) 

        # 4. Salva il risultato
        output_dir = os.path.dirname(OUTPUT_FILE)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(json_text)
            
        print("💾 Successo! File offerte.json salvato.")

        # Pulizia file remoto (opzionale ma consigliata)
        genai.delete_file(sample_file.name)

    except Exception as e:
        print(f"❌ Errore durante l'analisi: {e}")
        exit(1)

if __name__ == "__main__":
    main()

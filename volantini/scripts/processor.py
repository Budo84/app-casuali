import os
import time
import json
import glob
import google.generativeai as genai

# --- CONFIGURAZIONE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_FILE = os.path.join(BASE_DIR, 'output', 'offerte.json')

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ ERRORE: Manca la GEMINI_API_KEY!")
    exit(1)

genai.configure(api_key=api_key)

def main():
    # 1. TROVA IL PDF
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdf_files:
        print("⚠️ Nessun PDF trovato.")
        return

    pdf_path = pdf_files[0]
    print(f"📄 Trovato file: {os.path.basename(pdf_path)}")

    # 2. CARICA IL FILE SU GOOGLE (Visione AI)
    print("☁️ Caricamento file su Google AI...")
    try:
        myfile = genai.upload_file(pdf_path)
        print(f"✅ Upload completato: {myfile.name}")
    except Exception as e:
        print(f"❌ Errore upload: {e}")
        exit(1)

    # 3. ATTENDI L'ELABORAZIONE (Cruciale per i PDF!)
    print("⏳ Attesa elaborazione file...")
    while myfile.state.name == "PROCESSING":
        time.sleep(2)
        myfile = genai.get_file(myfile.name)

    if myfile.state.name == "FAILED":
        print("❌ L'elaborazione del file da parte di Google è fallita.")
        exit(1)
    
    print("✅ File pronto per l'analisi.")

    # 4. CHIEDI A GEMINI (Il Prompt Esatto)
    # Usiamo il modello Flash perché è veloce ed economico, ma vede bene come il Pro
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
    Analizza questo volantino come un esperto di dati.
    Estrai un array JSON contenente le offerte presenti.
    
    Struttura richiesta per ogni offerta:
    {
        "prodotto": "Nome completo marca e prodotto",
        "dettagli": "Grammatura o descrizione (es. 500g, 1.5L)",
        "prezzo": 0.00,
        "offerta_speciale": "Eventuale testo come '1+1 gratis' o 'Sconto 30%'"
    }

    Regole:
    - Ignora indirizzi dei negozi e orari di apertura.
    - Se il prezzo è "1,49", convertilo in numero 1.49.
    - Se ci sono offerte "1+1", scrivilo nel campo "offerta_speciale".
    - Rispondi SOLO con il JSON puro.
    """

    print("🤖 Generazione JSON in corso...")
    try:
        result = model.generate_content([myfile, prompt])
        
        # Pulizia testo (toglie eventuali ```json)
        json_text = result.text.replace("```json", "").replace("```", "").strip()
        
        # Validazione
        parsed_json = json.loads(json_text)
        
        # Salvataggio
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
            
        print("💾 OTTIMO! File offerte.json salvato con successo.")

    except Exception as e:
        print(f"❌ Errore durante l'analisi: {e}")
        # Stampa l'output grezzo per debug se fallisce il parsing
        if 'result' in locals():
            print("Output grezzo:", result.text)
        exit(1)
    finally:
        # Pulizia: cancella il file dai server Google per privacy
        genai.delete_file(myfile.name)
        print("🧹 File temporaneo remoto eliminato.")

if __name__ == "__main__":
    main()

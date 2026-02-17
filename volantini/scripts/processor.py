import os
import json
import glob
import requests
from pypdf import PdfReader

# --- CONFIGURAZIONE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_FILE = os.path.join(BASE_DIR, 'output', 'offerte.json')
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    print("❌ ERRORE: Manca la GEMINI_API_KEY!")
    exit(1)

def extract_text_from_pdf(pdf_path):
    """Estrae il testo puro dal PDF usando pypdf"""
    print("📖 Estrazione testo dal PDF in locale...")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"❌ Errore lettura PDF: {e}")
        return None

def call_gemini_text(text_content):
    """Chiama Gemini passando SOLO il testo (niente file upload)"""
    
    # URL diretto API v1beta (più stabile per il testo)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    # Costruiamo il JSON a mano per avere controllo totale
    payload = {
        "contents": [{
            "parts": [{
                "text": f"""
                Analizza il seguente testo estratto da un volantino supermercato.
                Estrai un array JSON con le offerte.
                Struttura: {{"prodotto": "Nome e Marca", "prezzo": 1.99, "dettagli": "peso/info"}}
                
                Regole:
                1. Cerca di ripulire i nomi dei prodotti (es. togli codici strani).
                2. Unisci il prezzo al prodotto corretto.
                3. Rispondi SOLO JSON.
                
                TESTO VOLANTINO:
                {text_content[:30000]} 
                """ 
                # Limitiamo a 30k caratteri per sicurezza, bastano per un volantino
            }]
        }]
    }

    print("📡 Invio testo a Google Gemini...")
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    
    if response.status_code != 200:
        print(f"⚠️ Errore API ({response.status_code}): {response.text}")
        # Tenta fallback su modello Pro se Flash fallisce
        if response.status_code == 404:
             return call_gemini_fallback(text_content)
        return None
        
    return response.json()

def call_gemini_fallback(text_content):
    """Tentativo di riserva con Gemini Pro"""
    print("🔄 Provo con il modello gemini-1.0-pro (Fallback)...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.0-pro:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": f"Estrai JSON offerte da questo testo: {text_content[:15000]}"}]}]
    }
    
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Anche il fallback ha fallito: {response.text}")
        return None

def main():
    # 1. Cerca PDF
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdf_files:
        print("⚠️ Nessun PDF trovato.")
        return

    pdf_path = pdf_files[0]
    print(f"📄 File trovato: {os.path.basename(pdf_path)}")

    # 2. Estrai Testo Locale (Nessun upload a Google)
    raw_text = extract_text_from_pdf(pdf_path)
    
    if not raw_text or len(raw_text.strip()) < 50:
        print("❌ Il PDF sembra non contenere testo leggibile (forse è solo immagini?).")
        print("   Questa strategia richiede PDF con testo selezionabile.")
        exit(1)
        
    print(f"✅ Testo estratto: {len(raw_text)} caratteri.")

    # 3. Chiama AI
    result = call_gemini_text(raw_text)

    if not result or 'candidates' not in result:
        print("❌ Nessun dato ricevuto dall'AI.")
        exit(1)

    # 4. Salva JSON
    try:
        content_text = result['candidates'][0]['content']['parts'][0]['text']
        clean_json = content_text.replace("```json", "").replace("```", "").strip()
        
        # Validazione
        parsed = json.loads(clean_json)
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
            
        print("💾 OTTIMO! File offerte.json salvato.")

    except Exception as e:
        print(f"❌ Errore parsing/salvataggio: {e}")
        exit(1)

if __name__ == "__main__":
    main()

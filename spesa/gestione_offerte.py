import os
import json
import google.generativeai as genai
import glob
import time
import sys
from pypdf import PdfReader  # Libreria per leggere il testo locale

print("--- 🛒 AVVIO ANALISI OFFERTE (ESTRAZIONE TESTO) ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

# Usa il modello STANDARD (Testuale) che non fallisce mai
model = genai.GenerativeModel("gemini-pro")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def analizza():
    base = os.path.dirname(os.path.abspath(__file__))
    paths = [os.path.join(base, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target = next((p for p in paths if os.path.exists(p)), None)
    
    offerte = {}
    
    if target:
        files = glob.glob(os.path.join(target, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(files)} PDF.")
        
        for fp in files:
            try:
                nome = os.path.splitext(os.path.basename(fp))[0].replace("_", " ").title()
                print(f"📄 Leggo testo di: {nome}")
                
                # 1. ESTRAZIONE TESTO LOCALE (Senza inviare file a Google)
                full_text = ""
                try:
                    reader = PdfReader(fp)
                    for page in reader.pages:
                        full_text += page.extract_text() + "\n"
                except Exception as e:
                    print(f"   ❌ Errore lettura PDF locale: {e}")
                    continue

                if len(full_text) < 50:
                    print("   ⚠️ PDF sembra vuoto o è un'immagine.")
                    continue

                # Limitiamo i caratteri per non intasare l'IA
                testo_ridotto = full_text[:30000] 

                # 2. INVIO TESTO A GEMINI
                prompt = f"""
                Sei un assistente per la spesa. Analizza il seguente testo estratto da un volantino del supermercato "{nome}".
                Estrai una lista di prodotti alimentari e i loro prezzi.
                Ignora codici, date o indirizzi.
                
                TESTO:
                {testo_ridotto}
                
                RISPONDI SOLO JSON:
                {{
                    "{nome}": [
                        {{"name": "Esempio Prodotto", "price": 1.99}}
                    ]
                }}
                """
                
                print("   🤖 Invio testo all'IA...")
                res = model.generate_content(prompt)
                
                # 3. SALVATAGGIO
                data = json.loads(pulisci_json(res.text))
                if data:
                    k = list(data.keys())[0]
                    offerte[nome] = data[k]
                    print(f"   ✅ Estratti {len(data[k])} prodotti.")
                
            except Exception as e:
                print(f"   ⚠️ Errore su {nome}: {e}")

    # SALVATAGGIO FILE JSON
    if not offerte:
        offerte = {"Info": [{"name": "Nessuna offerta trovata", "price": 0.00}]}
    
    file_out = os.path.join(base, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print("💾 Offerte salvate.")

if __name__ == "__main__":
    analizza()

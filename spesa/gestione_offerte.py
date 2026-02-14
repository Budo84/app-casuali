import os
import json
from google import genai
from google.genai import types
import glob
import time
import sys

print("--- 🛒 AVVIO ANALISI OFFERTE (NUOVA LIBRERIA) ---")

if "GEMINI_KEY" in os.environ:
    # Nuova inizializzazione Client
    client = genai.Client(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

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
                print(f"📄 Analisi: {nome}")
                
                # CARICAMENTO FILE (Nuovo Metodo)
                try:
                    file_ref = client.files.upload(file=fp)
                    print(f"   Upload OK: {file_ref.name}")
                except Exception as e:
                    print(f"   ❌ Errore Upload: {e}")
                    continue
                
                # ATTESA ATTIVA (Il file deve essere 'ACTIVE')
                for _ in range(30):
                    file_info = client.files.get(name=file_ref.name)
                    if file_info.state == "ACTIVE":
                        break
                    time.sleep(2)
                
                # PROMPT
                prompt = f"""
                Analizza questo volantino di "{nome}".
                Estrai una lista di prodotti alimentari e prezzi.
                RISPONDI SOLO JSON: {{ "{nome}": [ {{"name": "...", "price": 0.00}} ] }}
                """
                
                # GENERAZIONE (Nuovo Metodo)
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[file_ref, prompt]
                )
                
                if response.text:
                    data = json.loads(pulisci_json(response.text))
                    if data:
                        k = list(data.keys())[0]
                        offerte[nome] = data[k]
                        print(f"   ✅ Trovati {len(data[k])} prodotti.")
                
            except Exception as e:
                print(f"   ⚠️ Errore AI su {nome}: {e}")

    # SALVATAGGIO
    if not offerte:
        offerte = {"Nessuna Offerta": [{"name": "Riprova Analisi", "price": 0.00}]}
    
    file_out = os.path.join(base, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print("💾 Offerte salvate.")

if __name__ == "__main__":
    analizza()

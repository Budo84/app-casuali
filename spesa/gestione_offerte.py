import os
import json
import google.generativeai as genai
import glob
import time
import sys
from pypdf import PdfReader  # Libreria per leggere il testo

print("--- 🛒 AVVIO ANALISI OFFERTE (TEXT EXTRACTION) ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

# Usa Gemini Pro Standard (solo testo, affidabilissimo)
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
                print(f"📄 Elaborazione: {nome}")
                
                # 1. ESTRAZIONE TESTO (Locale)
                print("   📖 Estraggo testo dal PDF...")
                testo_pdf = ""
                try:
                    reader = PdfReader(fp)
                    for page in reader.pages:
                        testo_pdf += page.extract_text() + "\n"
                except Exception as e:
                    print(f"   ❌ Errore lettura PDF: {e}")
                    continue
                
                # Tagliamo il testo se troppo lungo (Gemini Pro accetta molto, ma stiamo sicuri)
                if len(testo_pdf) > 30000: 
                    testo_pdf = testo_pdf[:30000]
                    print("   ⚠️ Testo troncato a 30k caratteri.")

                # 2. INVIO A GEMINI
                print("   🤖 Invio testo all'AI...")
                prompt = f"""
                Sei un assistente per la spesa. Ecco il testo estratto da un volantino di "{nome}".
                Estrai una lista dei prodotti alimentari in offerta e i loro prezzi.
                Ignora codici, date o frasi pubblicitarie.
                
                TESTO VOLANTINO:
                {testo_pdf}
                
                RISPONDI SOLO CON QUESTO JSON:
                {{
                    "{nome}": [
                        {{"name": "Nome Prodotto", "price": 0.00}},
                        {{"name": "Altro Prodotto", "price": 0.00}}
                    ]
                }}
                """
                
                res = model.generate_content(prompt)
                
                # 3. SALVATAGGIO DATI
                try:
                    data = json.loads(pulisci_json(res.text))
                    if data:
                        k = list(data.keys())[0]
                        offerte[nome] = data[k]
                        print(f"   ✅ Estratti {len(data[k])} prodotti.")
                except:
                    print("   ⚠️ L'AI non ha restituito un JSON valido.")
                
            except Exception as e:
                print(f"   ⚠️ Errore generico su {nome}: {e}")

    # SALVATAGGIO FILE
    if not offerte:
        offerte = {"Info": [{"name": "Nessuna offerta trovata", "price": 0.00}]}
    
    file_out = os.path.join(base, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print("💾 Offerte salvate.")

if __name__ == "__main__":
    analizza()

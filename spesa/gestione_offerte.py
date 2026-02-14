import os
import json
import google.generativeai as genai
import glob
import time
import sys

print("--- 🛒 AVVIO ANALISI OFFERTE ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

def get_model():
    try: return genai.GenerativeModel("gemini-1.5-flash")
    except: 
        try: return genai.GenerativeModel("gemini-1.5-pro")
        except: return genai.GenerativeModel("gemini-pro")

model = get_model()

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
                pdf = genai.upload_file(fp, display_name=nome)
                
                for _ in range(15):
                    time.sleep(2)
                    pdf = genai.get_file(pdf.name)
                    if pdf.state.name == "ACTIVE": break
                
                if pdf.state.name != "ACTIVE": continue
                
                prompt = f"""Analizza "{nome}". Estrai prodotti e prezzi. JSON: {{ "{nome}": [ {{"name": "...", "price": 0.00}} ] }}"""
                res = model.generate_content([pdf, prompt])
                data = json.loads(pulisci_json(res.text))
                if data: offerte[nome] = data[list(data.keys())[0]]
                try: genai.delete_file(pdf.name)
                except: pass
            except Exception as e: print(f"⚠️ Errore {nome}: {e}")

    if not offerte: offerte = {"Info": [{"name": "Nessuna offerta trovata", "price": 0.00}]}
    
    with open(os.path.join(base, "offerte.json"), "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print("💾 Offerte salvate.")

if __name__ == "__main__":
    analizza()

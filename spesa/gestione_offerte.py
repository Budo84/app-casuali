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

# Tenta di prendere il modello migliore per PDF
def get_model():
    try:
        return genai.GenerativeModel("gemini-1.5-flash")
    except:
        try:
            return genai.GenerativeModel("gemini-1.5-pro")
        except:
            return None

model = get_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def analizza():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Cerca la cartella in vari posti
    paths = [os.path.join(base_dir, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target_dir = next((p for p in paths if os.path.exists(p)), None)
    
    offerte = {}
    
    if target_dir and model:
        files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(files)} PDF in {target_dir}")
        
        for file_path in files:
            try:
                nome = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
                print(f"📄 Analisi: {nome}")
                
                pdf = genai.upload_file(file_path, display_name=nome)
                
                # Attesa attiva
                for _ in range(15):
                    time.sleep(2)
                    pdf = genai.get_file(pdf.name)
                    if pdf.state.name == "ACTIVE": break
                
                if pdf.state.name != "ACTIVE":
                    print("❌ PDF non pronto.")
                    continue
                    
                prompt = f"""Estrai prodotti e prezzi da "{nome}". JSON: {{ "{nome}": [ {{"name": "...", "price": 0.00}} ] }}"""
                res = model.generate_content([pdf, prompt])
                data = json.loads(pulisci_json(res.text))
                
                if data:
                    k = list(data.keys())[0]
                    offerte[nome] = data[k]
                    print(f"✅ Trovati {len(data[k])} prodotti.")
                
                try: genai.delete_file(pdf.name)
                except: pass
                
            except Exception as e:
                print(f"⚠️ Errore su {nome}: {e}")
    else:
        print("⚠️ Nessun modello valido o cartella non trovata.")

    # SALVATAGGIO
    # Se vuoto, mettiamo un dato placeholder
    if not offerte:
        offerte = {"Nessuna Offerta": [{"name": "Carica un volantino e riprova", "price": 0.00}]}
        
    file_out = os.path.join(base_dir, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print(f"💾 Offerte salvate in {file_out}")

if __name__ == "__main__":
    analizza()

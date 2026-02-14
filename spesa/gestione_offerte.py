import os
import json
import google.generativeai as genai
import glob
import time
import sys

print("--- 🛒 AVVIO ANALISI OFFERTE (PDF) ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

# --- CERCA IL MODELLO MIGLIORE (AUTO-FIX 404) ---
def get_best_model():
    print("📡 Scansione modelli disponibili...")
    try:
        available = [m.name for m in genai.list_models()]
        print(f"   Modelli: {available}")
        
        # Priorità: 1. Flash (Veloce) 2. Pro 1.5 (Potente) 3. Pro (Standard)
        for m in available:
            if 'flash' in m and '1.5' in m: return genai.GenerativeModel(m.replace('models/', ''))
        for m in available:
            if 'pro' in m and '1.5' in m: return genai.GenerativeModel(m.replace('models/', ''))
            
        return genai.GenerativeModel("gemini-pro") # Fallback
    except:
        return genai.GenerativeModel("gemini-pro")

model = get_best_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def analizza():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    paths = [os.path.join(base_dir, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target_dir = next((p for p in paths if os.path.exists(p)), None)
    
    offerte = {}
    
    if target_dir:
        files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(files)} PDF in {target_dir}")
        
        for file_path in files:
            try:
                nome = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
                print(f"📄 Analisi: {nome}")
                
                pdf = genai.upload_file(file_path, display_name=nome)
                
                # Attesa attiva
                ready = False
                for _ in range(15):
                    time.sleep(2)
                    pdf = genai.get_file(pdf.name)
                    if pdf.state.name == "ACTIVE": 
                        ready = True
                        break
                
                if not ready:
                    print("❌ PDF non pronto (Timeout).")
                    continue
                    
                prompt = f"""
                Analizza il volantino "{nome}".
                Estrai TUTTI i prodotti alimentari e i prezzi.
                RISPONDI SOLO JSON: {{ "{nome}": [ {{"name": "...", "price": 0.00}} ] }}
                """
                
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

    # SALVATAGGIO (Se vuoto, evita errore nell'app)
    if not offerte:
        offerte = {"Nessun Dato": [{"name": "Riprova Analisi", "price": 0.00}]}
        
    file_out = os.path.join(base_dir, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print(f"💾 Offerte salvate in {file_out}")

if __name__ == "__main__":
    analizza()

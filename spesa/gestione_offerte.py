import os
import json
import google.generativeai as genai
import glob
import time
import sys

print("--- 🛒 AVVIO ANALISI OFFERTE (AUTO-DETECT) ---")

if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave mancante.")
    sys.exit(0)

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FUNZIONE CRUCIALE: TROVA IL MODELLO GIUSTO ---
def get_best_model_name():
    print("📡 Interrogo Google per i modelli disponibili...")
    try:
        candidates = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                candidates.append(m.name)
        
        print(f"📋 Modelli trovati: {candidates}")

        # Priorità: Flash (Veloce) -> Pro 1.5 -> Pro 1.0
        for m in candidates:
            if 'flash' in m and '1.5' in m: return m
        for m in candidates:
            if 'pro' in m and '1.5' in m: return m
        
        # Fallback estremo
        return 'models/gemini-1.5-flash'
    except Exception as e:
        print(f"⚠️ Errore lista modelli: {e}. Uso default.")
        return 'models/gemini-1.5-flash'

def analizza():
    base = os.path.dirname(os.path.abspath(__file__))
    paths = [os.path.join(base, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target = next((p for p in paths if os.path.exists(p)), None)
    
    offerte = {}
    
    # 1. SCEGLI IL MODELLO
    model_name = get_best_model_name()
    print(f"✅ Uso modello: {model_name}")
    model = genai.GenerativeModel(model_name)

    if target:
        files = glob.glob(os.path.join(target, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(files)} PDF.")
        
        for fp in files:
            try:
                nome = os.path.splitext(os.path.basename(fp))[0].replace("_", " ").title()
                print(f"📄 Elaborazione: {nome}...")
                
                # 2. CARICA IL FILE SU GOOGLE (Metodo File API)
                print("   ☁️ Upload su Google...")
                myfile = genai.upload_file(fp, display_name=nome)
                
                # 3. ATTENDI ELABORAZIONE
                print("   ⏳ Attendo elaborazione...")
                while myfile.state.name == "PROCESSING":
                    time.sleep(2)
                    myfile = genai.get_file(myfile.name)
                
                if myfile.state.name == "FAILED":
                    print("   ❌ Errore elaborazione Google.")
                    continue

                # 4. CHIEDI ALL'AI
                prompt = f"""
                Analizza questo volantino di "{nome}".
                Estrai TUTTI i prodotti alimentari (cibo, bevande) e i relativi prezzi.
                Ignora tutto ciò che non è cibo.
                
                RISPONDI TASSATIVAMENTE SOLO CON QUESTO JSON:
                {{
                    "{nome}": [
                        {{"name": "Nome Prodotto", "price": 0.00}},
                        {{"name": "Altro Prodotto", "price": 0.00}}
                    ]
                }}
                """
                
                print("   🤖 Analisi AI in corso...")
                res = model.generate_content([myfile, prompt])
                
                # 5. PULIZIA
                try: genai.delete_file(myfile.name)
                except: pass

                # 6. PARSING DATI
                raw_text = pulisci_json(res.text)
                data = json.loads(raw_text)
                
                if data:
                    k = list(data.keys())[0]
                    offerte[nome] = data[k]
                    print(f"   ✅ Successo! Estratti {len(data[k])} prodotti.")
                
            except Exception as e:
                print(f"   ⚠️ Errore critico su {nome}: {e}")

    # SALVATAGGIO (Sempre, per non rompere l'app)
    if not offerte:
        offerte = {"Info": [{"name": "Nessuna offerta trovata. Controlla i log.", "price": 0.00}]}
    
    file_out = os.path.join(base, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print(f"💾 Offerte salvate in {file_out}")

if __name__ == "__main__":
    analizza()

import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- 🚀 AVVIO ROBOT SPESA ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante. Lo script si ferma.")
    sys.exit(1)

# 2. MODELLO
model = genai.GenerativeModel("gemini-1.5-flash")

# Funzione per pulire il JSON sporco che a volte Gemini genera
def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def analizza_volantini():
    offerte_db = {}
    
    # --- PERCORSO ASSOLUTO ---
    # Trova la cartella dove sta questo file 'automazione.py' (cioè la cartella 'spesa')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Cerca dentro 'spesa/volantini'
    path_volantini = os.path.join(base_dir, "volantini", "*.pdf")
    
    print(f"📂 Cerco PDF in: {path_volantini}")
    files = glob.glob(path_volantini)
    
    if not files:
        print("⚠️ Nessun PDF trovato. Genererò solo un menu base.")
        return {}

    print(f"✅ Trovati {len(files)} volantini.")

    for file_path in files:
        try:
            # Nome file = Nome Supermercato (es. conad.pdf -> Conad)
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].title() # Conad
            
            print(f"📄 Analizzo: {nome_file} -> {nome_store}")

            # 1. Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            while pdf.state.name == "PROCESSING":
                time.sleep(1)
                pdf = genai.get_file(pdf.name)
            
            if pdf.state.name == "FAILED":
                print("   ❌ Errore Google: File illeggibile.")
                continue

            # 2. Estrazione
            prompt = f"""
            Analizza il volantino di "{nome_store}".
            Estrai TUTTI i prodotti alimentari e i prezzi.
            RISPONDI SOLO JSON: {{ "{nome_store}": [ {{"name": "...", "price": 1.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            if nome_store in data:
                offerte_db[nome_store] = data[nome_store]
                print(f"   ✅ Estratti {len(data[nome_store])} prodotti.")
            
            genai.delete_file(pdf.name)

        except Exception as e:
            print(f"   ❌ Errore file {nome_file}: {e}")

    return offerte_db

def genera_tutto():
    # Percorso output assoluto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. Analisi
    offerte = analizza_volantini()
    
    # 2. Generazione Menu
    print("🍳 Generazione Menu...")
    ricette = []
    
    # Se abbiamo offerte, usiamo quegli ingredienti
    context = "Usa ingredienti generici."
    if offerte:
        ingred = []
        for s in offerte:
            for p in offerte[s]: ingred.append(p['name'])
        context = "Usa questi ingredienti in offerta: " + ", ".join(ingred[:50])

    try:
        prompt_menu = f"""
        Crea un menu settimanale DIETA MEDITERRANEA.
        {context}
        Usa nomi generici (es. "Pasta", non "Pasta Barilla").
        
        JSON:
        {{
          "colazione": [ {{"title": "...", "ingredients": ["..."], "contains": []}} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }}
        """
        res = model.generate_content(prompt_menu)
        raw = json.loads(pulisci_json(res.text))
        
        for k in ["colazione", "pranzo", "merenda", "cena"]:
            for r in raw.get(k, []):
                r['type'] = k
                ricette.append(r)
        print(f"✅ Menu generato: {len(ricette)} ricette.")

    except Exception as e:
        print(f"❌ Errore Menu: {e}. Uso menu di emergenza.")
        ricette = [
            {"title": "Pasta Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Pomodoro"], "contains": []},
            {"title": "Pollo e Insalata", "type": "cena", "ingredients": ["Pollo", "Insalata"], "contains": []}
        ]

    # 3. Salvataggio
    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)
    print(f"💾 FILE SALVATO: {file_out}")

if __name__ == "__main__":
    genera_tutto()

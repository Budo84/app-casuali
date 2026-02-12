import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- AVVIO ROBOT LETTORE PDF ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Manca GEMINI_KEY")
    sys.exit(1)

# 2. SETUP MODELLO
def get_model():
    # Proviamo diversi modelli in ordine
    for m in ["gemini-1.5-flash", "gemini-1.5-pro"]:
        try:
            return genai.GenerativeModel(m)
        except: continue
    return genai.GenerativeModel("gemini-1.5-flash")

model = get_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    return text[s:e] if s != -1 and e != -1 else text

# 3. ANALISI VOLANTINI (Percorso Blindato)
def analizza_volantini():
    offerte_db = {}
    
    # TRUCCO: Costruiamo il percorso assoluto partendo da dove si trova QUESTO file script
    base_dir = os.path.dirname(os.path.abspath(__file__)) # Cartella 'spesa'
    path_volantini = os.path.join(base_dir, "volantini", "*.pdf")
    
    print(f"🔍 Cerco PDF in: {path_volantini}")
    files = glob.glob(path_volantini)
    
    # DEBUG: Stampa cosa ha trovato
    if not files:
        print("❌ NESSUN PDF TROVATO! Verifica che il file sia in spesa/volantini/")
        # Stampa contenuto cartella per debug
        try:
            print(f"Contenuto di {os.path.join(base_dir, 'volantini')}:")
            print(os.listdir(os.path.join(base_dir, "volantini")))
        except:
            print("Cartella volantini non leggibile.")
        return {}

    print(f"✅ Trovati {len(files)} volantini.")

    for file_path in files:
        nome_file = os.path.basename(file_path)
        nome_store = os.path.splitext(nome_file)[0].capitalize()
        if "ma" == nome_store.lower(): nome_store = "MA Supermercati"
        
        print(f"📄 Leggo: {nome_file} -> Store: {nome_store}")

        try:
            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            while pdf.state.name == "PROCESSING":
                time.sleep(1)
                pdf = genai.get_file(pdf.name)

            if pdf.state.name == "FAILED":
                print("   ❌ Google non riesce a leggere questo PDF.")
                continue

            # Prompt
            prompt = f"""
            Estrai dal volantino {nome_store} TUTTI i cibi e prezzi.
            JSON FORMAT: {{ "{nome_store}": [ {{"name": "...", "price": 0.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            if nome_store in data:
                offerte_db[nome_store] = data[nome_store]
                print(f"   ✅ Estratti {len(data[nome_store])} prodotti!")
            
            genai.delete_file(pdf.name)

        except Exception as e:
            print(f"   ❌ Errore critico: {e}")

    return offerte_db

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    # 1. Estrai Offerte
    offerte = analizza_volantini()
    
    # 2. Genera Menu (se ci sono offerte)
    ricette = []
    if offerte:
        ingred = []
        for s in offerte:
            for p in offerte[s]: ingred.append(p['name'])
        
        txt_ing = ", ".join(ingred[:50])
        print("🍳 Genero menu basato su:", txt_ing[:50], "...")
        
        try:
            prompt = f"""
            Crea menu settimanale DIETA MEDITERRANEA usando: {txt_ing}.
            JSON: {{ "colazione": [], "pranzo": [], "merenda": [], "cena": [] }}
            Ogni ricetta: {{"title": "...", "ingredients": ["..."], "type": "..."}}
            """
            res = model.generate_content(prompt)
            raw = json.loads(pulisci_json(res.text))
            for k in ["colazione","pranzo","merenda","cena"]:
                for r in raw.get(k, []):
                    r['type'] = k
                    ricette.append(r)
        except Exception as e:
            print(f"❌ Errore Menu: {e}")

    # 3. Salva
    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }
    
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)
    print("💾 SALVATO.")

if __name__ == "__main__":
    genera_tutto()

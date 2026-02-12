import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

# --- CONFIGURAZIONE ---
print("--- START: SOLO VOLANTINI REALI ---")

if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# --- CONFIGURAZIONE MODELLO ---
def get_model():
    # Per i PDF serve il modello Flash o Pro
    candidates = ["gemini-1.5-flash", "gemini-1.5-pro"]
    for m in candidates:
        try:
            model = genai.GenerativeModel(m)
            return model
        except: continue
    return genai.GenerativeModel("gemini-1.5-flash") # Fallback

model = get_model()

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    if testo.startswith("{"): start, end = testo.find('{'), testo.rfind('}') + 1
    else: start, end = testo.find('['), testo.rfind(']') + 1
    return testo[start:end] if start != -1 and end != -1 else testo

def analizza_volantini():
    offerte_db = {} # Si parte VUOTI. Niente invenzioni.
    
    # Percorso cartella volantini
    path_volantini = os.path.join(os.path.dirname(__file__), "..", "volantini", "*.pdf")
    files = glob.glob(path_volantini)
    
    if not files:
        print("📂 Nessun PDF trovato. Nessuna offerta verrà generata.")
        return {}

    print(f"📂 Trovati {len(files)} volantini reali.")

    for file_path in files:
        try:
            # Nome file = Nome Store (es. "lidl.pdf" -> "Lidl")
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].capitalize()
            if nome_store.lower() == "ma": nome_store = "MA Supermercati"
            
            print(f"   📄 Analizzo {nome_file}...")
            
            # Upload su Gemini
            sample_file = genai.upload_file(path=file_path, display_name=nome_store)
            
            # Attesa elaborazione
            while sample_file.state.name == "PROCESSING":
                time.sleep(2)
                sample_file = genai.get_file(sample_file.name)

            if sample_file.state.name == "FAILED":
                print("      ❌ Fallito.")
                continue

            # Prompt Estrazione
            prompt = f"""
            Estrai TUTTI i prodotti alimentari e prezzi da questo volantino di {nome_store}.
            Ignora non-food.
            RISPONDI SOLO JSON:
            {{
                "{nome_store}": [
                    {{"name": "Nome Marca", "price": 1.99}},
                    ...
                ]
            }}
            """
            resp = model.generate_content([sample_file, prompt])
            dati = json.loads(pulisci_json(resp.text))
            
            if nome_store in dati:
                offerte_db[nome_store] = dati[nome_store]
                print(f"      ✅ Estratti {len(dati[nome_store])} prodotti.")
            
            # Cleanup privacy
            genai.delete_file(sample_file.name)
            
        except Exception as e:
            print(f"      ❌ Errore su {nome_file}: {e}")

    return offerte_db

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    # 1. ANALISI REALE
    offerte_finali = analizza_volantini()

    # 2. MENU (Basato su quello che c'è)
    print("2. Genero Menu...")
    
    # Raccogliamo ingredienti disponibili
    ingredienti_disponibili = []
    for s in offerte_finali:
        for p in offerte_finali[s]:
            ingredienti_disponibili.append(p['name'])
    
    context_str = "Ingredienti in offerta: " + ", ".join(ingredienti_disponibili[:50])
    if not ingredienti_disponibili:
        context_str = "Nessuna offerta disponibile. Usa ingredienti base economici (Pasta, Uova, Verdure stagione)."

    try:
        prompt_ric = f"""
        Crea menu settimanale DIETA MEDITERRANEA.
        {context_str}
        Usa ingredienti GENERICI.
        
        Format JSON:
        {{
          "colazione": [ {{"title": "...", "ingredients": ["..."], "contains": []}} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }}
        """
        resp_ric = model.generate_content(prompt_ric)
        ricette_raw = json.loads(pulisci_json(resp_ric.text))
        
        ricette_finali = []
        for t in ["colazione", "pranzo", "merenda", "cena"]:
            for p in ricette_raw.get(t, []):
                p['type'] = t
                ricette_finali.append(p)
                
    except Exception as e:
        print(f"❌ Errore Menu: {e}")
        ricette_finali = []

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_finali,
        "ricette": ricette_finali
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Dati salvati.")

if __name__ == "__main__":
    genera_tutto()

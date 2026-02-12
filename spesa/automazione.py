import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

# --- CONFIGURAZIONE ---
print("--- START: SISTEMA VOLANTINI REALI ---")

if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# --- 1. SELEZIONE MODELLO ---
def get_model():
    # Per leggere i PDF serve il modello Flash o Pro
    candidates = ["gemini-1.5-flash", "gemini-1.5-pro"]
    for m in candidates:
        try:
            model = genai.GenerativeModel(m)
            return model
        except: continue
    print("⚠️ Fallback su Flash standard")
    return genai.GenerativeModel("gemini-1.5-flash")

model = get_model()

# --- 2. PULIZIA OUTPUT ---
def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    if testo.startswith("{"): start, end = testo.find('{'), testo.rfind('}') + 1
    else: start, end = testo.find('['), testo.rfind(']') + 1
    return testo[start:end] if start != -1 and end != -1 else testo

# --- 3. ANALISI PDF ---
def analizza_volantini():
    offerte_db = {} 
    
    # Percorso: cartella corrente (spesa) + volantini
    cartella_script = os.path.dirname(os.path.abspath(__file__))
    path_volantini = os.path.join(cartella_script, "volantini", "*.pdf")
    files = glob.glob(path_volantini)
    
    if not files:
        print(f"📂 Nessun PDF trovato in: {path_volantini}")
        print("ℹ️ Nessuna offerta verrà generata (Modalità: No Invenzioni).")
        return {}

    print(f"📂 Trovati {len(files)} volantini.")

    for file_path in files:
        try:
            # Nome file = Nome Store (es. "conad.pdf" -> "Conad")
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].capitalize()
            # Correzioni nomi comuni
            if nome_store.lower() == "ma": nome_store = "MA Supermercati"
            
            print(f"   📄 Analizzo {nome_file}...")
            
            # Upload su Gemini
            sample_file = genai.upload_file(path=file_path, display_name=nome_store)
            
            # Attesa elaborazione
            while sample_file.state.name == "PROCESSING":
                time.sleep(2)
                sample_file = genai.get_file(sample_file.name)

            if sample_file.state.name == "FAILED":
                print("      ❌ Lettura fallita da parte di Google.")
                continue

            # Prompt Estrazione
            prompt = f"""
            Sei un assistente per la spesa. Analizza questo volantino di {nome_store}.
            Estrai TUTTI i prodotti alimentari e i prezzi.
            
            Regole:
            1. Ignora prodotti non alimentari (Tv, Vestiti, ecc).
            2. Se il prezzo è al kg, scrivilo nel nome (es. "Mele al kg").
            3. Rispondi ESCLUSIVAMENTE con un JSON valido.
            
            Format:
            {{
                "{nome_store}": [
                    {{"name": "Pasta Barilla 500g", "price": 0.79}},
                    {{"name": "Passata Mutti", "price": 0.99}}
                ]
            }}
            """
            resp = model.generate_content([sample_file, prompt])
            dati = json.loads(pulisci_json(resp.text))
            
            if nome_store in dati:
                offerte_db[nome_store] = dati[nome_store]
                print(f"      ✅ Estratti {len(dati[nome_store])} prodotti.")
            
            # Cleanup file remoto
            genai.delete_file(sample_file.name)
            
        except Exception as e:
            print(f"      ❌ Errore analisi {nome_file}: {e}")

    return offerte_db

# --- 4. GENERAZIONE MENU ---
def genera_menu(offerte_db):
    print("2. Genero Menu...")
    
    # Creiamo un contesto con gli ingredienti trovati nei volantini
    ingredienti_disponibili = []
    for s in offerte_db:
        for p in offerte_db[s]:
            ingredienti_disponibili.append(p['name'])
    
    txt_ing = ", ".join(ingredienti_disponibili[:60]) # Limitiamo per non intasare il prompt
    if not txt_ing:
        txt_ing = "Nessuna offerta specifica. Usa ingredienti base economici."

    try:
        prompt_ric = f"""
        Crea un menu settimanale DIETA MEDITERRANEA.
        Cerca di usare questi ingredienti in offerta: {txt_ing}.
        Usa nomi GENERICI per gli ingredienti nelle ricette (es. "Pasta", non "Pasta Barilla").
        
        Struttura JSON richiesta (4 pasti al giorno):
        {{
          "colazione": [ {{"title": "...", "ingredients": ["..."], "contains": []}} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }}
        """
        resp_ric = model.generate_content(prompt_ric)
        ricette_raw = json.loads(pulisci_json(resp_ric.text))
        
        lista_ricette = []
        for t in ["colazione", "pranzo", "merenda", "cena"]:
            for p in ricette_raw.get(t, []):
                p['type'] = t
                lista_ricette.append(p)
        return lista_ricette
                
    except Exception as e:
        print(f"❌ Errore Menu: {e}")
        # Fallback minimo se l'IA fallisce la generazione del menu
        return [
            {"title": "Pasta al Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Pomodoro"], "contains": []},
            {"title": "Pollo e Insalata", "type": "cena", "ingredients": ["Pollo", "Insalata"], "contains": []}
        ]

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    # 1. Analisi Volantini
    offerte_finali = analizza_volantini()

    # 2. Menu
    ricette_finali = genera_menu(offerte_finali)

    # 3. Salvataggio
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

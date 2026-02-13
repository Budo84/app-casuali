import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- 🚀 AVVIO ROBOT SPESA: VERSIONE MEDITERRANEA ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante. Lo script si ferma.")
    sys.exit(1)

# 2. MODELLO
model = genai.GenerativeModel("gemini-1.5-flash")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def analizza_volantini():
    offerte_db = {}
    
    # --- RICERCA FILE ROBUSTA ---
    # 1. Cerca partendo dalla cartella dello script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    volantini_dir = os.path.join(base_dir, "volantini")
    
    # Se non esiste, prova a crearla
    if not os.path.exists(volantini_dir):
        try:
            os.makedirs(volantini_dir)
        except: pass

    # Cerca i PDF
    path_volantini = os.path.join(volantini_dir, "*.pdf")
    files = glob.glob(path_volantini)
    
    # Debug nei log
    print(f"📂 Cartella analizzata: {volantini_dir}")
    print(f"🔎 File trovati: {files}")
    
    if not files:
        print("⚠️ Nessun PDF trovato. Salto analisi prezzi.")
        return {}

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].title()
            
            print(f"📄 Elaborazione: {nome_file} -> {nome_store}")

            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa
            attempts = 0
            while pdf.state.name == "PROCESSING" and attempts < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempts += 1
            
            if pdf.state.name == "FAILED":
                print("   ❌ Errore Google: File illeggibile.")
                continue

            # Estrazione Prezzi
            prompt = f"""
            Analizza il volantino di "{nome_store}".
            Estrai TUTTI i prodotti alimentari e i prezzi visibili.
            RISPONDI SOLO JSON: {{ "{nome_store}": [ {{"name": "...", "price": 1.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            if nome_store in data:
                offerte_db[nome_store] = data[nome_store]
                print(f"   ✅ Offerte estratte: {len(data[nome_store])}")
            
            genai.delete_file(pdf.name)

        except Exception as e:
            print(f"   ❌ Errore critico su {nome_file}: {e}")

    return offerte_db

def genera_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. ANALISI PREZZI (Solo se ci sono PDF)
    offerte = analizza_volantini()
    
    # 2. GENERAZIONE MENU (Indipendente dai volantini)
    print("🍳 Generazione Menu Dieta Mediterranea...")
    ricette = []
    
    try:
        # Prompt modificato come richiesto: SOLO dieta equilibrata, niente volantini
        prompt_menu = """
        Crea un menu settimanale basato rigorosamente sulla DIETA MEDITERRANEA EQUILIBRATA.
        
        REGOLE:
        1. Non guardare offerte o volantini. Crea il menu ideale per la salute.
        2. Bilancia carboidrati, proteine e verdure.
        3. Usa ingredienti generici (es. "Pasta integrale", "Pesce azzurro", "Legumi").
        4. Struttura: Colazione, Pranzo, Merenda, Cena per 7 giorni.
        
        FORMATO JSON OBBLIGATORIO:
        {
          "colazione": [ {"title": "...", "ingredients": ["..."], "contains": []} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }
        """
        res = model.generate_content(prompt_menu)
        raw = json.loads(pulisci_json(res.text))
        
        for k in ["colazione", "pranzo", "merenda", "cena"]:
            for r in raw.get(k, []):
                r['type'] = k
                ricette.append(r)
        print(f"✅ Menu creato: {len(ricette)} pasti.")

    except Exception as e:
        print(f"❌ Errore Menu: {e}")
        # Fallback
        ricette = [{"title": "Pasto Equilibrato", "type": "pranzo", "ingredients": ["Cereali", "Verdure", "Proteine"], "contains": []}]

    # 3. SALVATAGGIO
    # Se non ci sono offerte nuove, manteniamo quelle vecchie se esistono? 
    # Per ora sovrascriviamo per pulizia, come da logica "nuova settimana".
    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)
    print(f"💾 Dati salvati in: {file_out}")

if __name__ == "__main__":
    genera_tutto()

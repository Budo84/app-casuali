import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- 🚀 AVVIO ROBOT SPESA: TUTTI I SUPERMERCATI ---")

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
    
    # PERCORSO ASSOLUTO
    base_dir = os.path.dirname(os.path.abspath(__file__))
    volantini_dir = os.path.join(base_dir, "volantini")
    
    # Crea cartella se non esiste
    if not os.path.exists(volantini_dir):
        try: os.makedirs(volantini_dir)
        except: pass

    # Cerca TUTTI i PDF
    path_volantini = os.path.join(volantini_dir, "*.pdf")
    files = glob.glob(path_volantini)
    
    print(f"📂 Cartella: {volantini_dir}")
    print(f"🔎 File trovati: {len(files)}")
    
    if not files:
        print("⚠️ Nessun PDF trovato. Nessuna offerta verrà caricata.")
        return {}

    for file_path in files:
        try:
            # Ricava il nome del supermercato dal nome del file
            # es. "spesa/volantini/ipercarni.pdf" -> "Ipercarni"
            nome_file = os.path.basename(file_path)
            nome_store_raw = os.path.splitext(nome_file)[0]
            
            # Formattazione Nome (es. "ma supermercati", "pewex")
            nome_store = nome_store_raw.replace("_", " ").title()
            
            # Correzioni specifiche per i tuoi store
            if "ma" in nome_store_raw.lower() and len(nome_store_raw) < 4: 
                nome_store = "MA Supermercati"
            
            print(f"📄 Analizzo Volantino: {nome_store} ({nome_file})")

            # Upload su Google
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa elaborazione
            attempts = 0
            while pdf.state.name == "PROCESSING" and attempts < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempts += 1
            
            if pdf.state.name == "FAILED":
                print(f"   ❌ Errore Google: Il file {nome_file} è illeggibile.")
                continue

            # Prompt specifico per estrarre PREZZI
            prompt = f"""
            Sei un assistente per la spesa. Analizza il volantino di "{nome_store}".
            Estrai TUTTI i prodotti alimentari e i loro prezzi.
            
            REGOLE:
            1. Cerca carne, pesce, pasta, verdure, frutta, dispensa.
            2. Ignora prodotti non alimentari (detersivi, tv, vestiti) se possibile.
            3. Se un prezzo non è chiaro, ignoralo.
            
            RISPONDI SOLO ED ESCLUSIVAMENTE CON QUESTO JSON:
            {{
                "{nome_store}": [
                    {{"name": "Nome Prodotto precsio", "price": 1.99}},
                    {{"name": "Altro prodotto", "price": 0.50}}
                ]
            }}
            """
            res = model.generate_content([pdf, prompt])
            cleaned_text = pulisci_json(res.text)
            
            try:
                data = json.loads(cleaned_text)
                # Verifica che la chiave esista, altrimenti cerchiamo la prima chiave disponibile
                chiave_dati = list(data.keys())[0] 
                prodotti = data[chiave_dati]
                
                # Salviamo usando il nome corretto del file come chiave (es. "Pewex")
                offerte_db[nome_store] = prodotti
                print(f"   ✅ Successo! Estratte {len(prodotti)} offerte per {nome_store}.")
                
            except Exception as e_json:
                print(f"   ⚠️ Errore lettura dati per {nome_store}: {e_json}")
                print(f"   Debug Risposta IA: {cleaned_text[:100]}...")
            
            # Pulizia file remoto
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ❌ Errore critico su file {file_path}: {e}")

    return offerte_db

def genera_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. ANALISI OFFERTE (Dai volantini reali)
    offerte = analizza_volantini()
    
    # 2. GENERAZIONE MENU (Dieta Mediterranea Equilibrata - INDIPENDENTE)
    print("🍳 Generazione Menu Dieta Mediterranea (Generale)...")
    ricette = []
    
    try:
        # Prompt per dieta equilibrata pura
        prompt_menu = """
        Crea un menu settimanale basato rigorosamente sulla DIETA MEDITERRANEA EQUILIBRATA.
        
        OBIETTIVO: Salute e Benessere.
        Non guardare offerte o volantini per questa parte.
        
        REGOLE:
        1. Bilancia carboidrati (pasta/pane/riso), proteine (pesce/legumi/carne bianca) e verdure.
        2. Varia gli ingredienti durante la settimana.
        3. Usa nomi generici (es. "Pasta integrale al pomodoro", "Pesce al forno", "Minestrone di verdure").
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
        print(f"✅ Menu creato: {len(ricette)} pasti equilibrati.")

    except Exception as e:
        print(f"❌ Errore Generazione Menu: {e}")
        # Fallback di sicurezza
        ricette = [
            {"title": "Pasta e Ceci", "type": "pranzo", "ingredients": ["Pasta", "Ceci", "Rosmarino"], "contains": []},
            {"title": "Pesce e Insalata", "type": "cena", "ingredients": ["Pesce", "Insalata"], "contains": []}
        ]

    # 3. SALVATAGGIO FINALE
    if not offerte and not ricette:
        print("⚠️ Nessun dato generato. Evito di sovrascrivere il file con vuoto.")
        return

    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
    print(f"💾 Dati salvati correttamente in: {file_out}")

if __name__ == "__main__":
    genera_tutto()

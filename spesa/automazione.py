import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- AVVIO ROBOT ANALISI UNIVERSALE ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Manca GEMINI_KEY")
    sys.exit(1)

# 2. SETUP MODELLO (Flash è il migliore per i documenti)
model = genai.GenerativeModel("gemini-1.5-flash")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    return text[s:e] if s != -1 and e != -1 else text

def analizza_volantini():
    offerte_db = {}
    
    # PERCORSO ASSOLUTO (Indistruttibile)
    # Trova la cartella dove si trova questo script (spesa)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Cerca nella sottocartella 'volantini'
    path_volantini = os.path.join(base_dir, "volantini", "*.pdf")
    
    print(f"🔍 Cerco PDF in: {path_volantini}")
    files = glob.glob(path_volantini)
    
    if not files:
        print("⚠️ NESSUN PDF TROVATO. Carica i file tramite l'app.")
        # Debug: stampiamo cosa c'è nella cartella per capire
        try:
            print(f"Contenuto cartella: {os.listdir(os.path.join(base_dir, 'volantini'))}")
        except:
            print("Cartella volantini vuota o inesistente.")
        return {}

    print(f"✅ Trovati {len(files)} file da analizzare.")

    for file_path in files:
        try:
            # USIAMO IL NOME DEL FILE COME NOME SUPERMERCATO
            # es. "spesa/volantini/conad.pdf" -> "Conad"
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0]
            
            # Formattazione bella (prima lettera maiuscola)
            nome_store = nome_store.replace("_", " ").title()
            
            # Eccezione estetica per "MA" se vuoi (opzionale)
            if nome_store.lower() == "ma": nome_store = "MA Supermercati"

            print(f"📄 Analisi: {nome_file} -> Supermercato: {nome_store}")

            # Upload su Google
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa attiva
            while pdf.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(1)
                pdf = genai.get_file(pdf.name)
            print(" Fatto.")

            if pdf.state.name == "FAILED":
                print(f"❌ Errore Google: Impossibile leggere {nome_file}")
                continue

            # Prompt
            prompt = f"""
            Sei un esperto di spesa. Analizza questo volantino di "{nome_store}".
            Estrai TUTTI i prodotti alimentari (Cibo, Bevande) e i prezzi.
            Ignora detersivi e vestiti se possibile.
            
            RISPONDI SOLO JSON in questo formato esatto:
            {{
                "{nome_store}": [
                    {{"name": "Nome Prodotto preciso", "price": 1.99}},
                    {{"name": "Altro prodotto", "price": 0.50}}
                ]
            }}
            """
            
            res = model.generate_content([pdf, prompt])
            
            try:
                data = json.loads(pulisci_json(res.text))
                if nome_store in data:
                    prodotti = data[nome_store]
                    offerte_db[nome_store] = prodotti
                    print(f"   ✅ Estratti {len(prodotti)} prodotti!")
                else:
                    print(f"   ⚠️ Il JSON non conteneva la chiave '{nome_store}'")
            except Exception as e_json:
                print(f"   ❌ Errore lettura JSON per {nome_store}: {res.text[:100]}...")

            # Pulizia
            genai.delete_file(pdf.name)

        except Exception as e:
            print(f"   ❌ Errore critico su {file_path}: {e}")

    return offerte_db

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    # 1. ANALISI
    offerte_finali = analizza_volantini()
    
    # 2. MENU
    print("\n🍳 Generazione Menu...")
    
    # Raccogliamo ingredienti per ispirare il menu
    ingredienti_input = []
    if offerte_finali:
        for store in offerte_finali:
            for p in offerte_finali[store]:
                ingredienti_input.append(p['name'])
        context = "Usa questi ingredienti in offerta: " + ", ".join(ingredienti_input[:50])
    else:
        print("⚠️ Nessuna offerta trovata. Genero menu con ingredienti base.")
        context = "Usa ingredienti economici e di stagione (Pasta, Riso, Uova, Pollo, Verdure)."

    ricette_finali = []
    try:
        prompt_menu = f"""
        Crea un menu settimanale DIETA MEDITERRANEA (4 pasti al giorno).
        {context}
        Usa nomi GENERICI per gli ingredienti (es. "Pasta", non "Pasta Barilla").
        
        RISPONDI SOLO JSON:
        {{
          "colazione": [ {{"title": "...", "ingredients": ["..."], "contains": []}} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }}
        """
        res = model.generate_content(prompt_menu)
        menu_raw = json.loads(pulisci_json(res.text))
        
        for k in ["colazione", "pranzo", "merenda", "cena"]:
            for r in menu_raw.get(k, []):
                r['type'] = k
                ricette_finali.append(r)
        
        print(f"✅ Menu generato: {len(ricette_finali)} ricette.")

    except Exception as e:
        print(f"❌ Errore generazione menu: {e}")
        # Fallback minimo per non rompere l'app
        ricette_finali = [
            {"title": "Pasta al Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Pomodoro"], "contains": []},
            {"title": "Cena Leggera", "type": "cena", "ingredients": ["Verdure", "Pane"], "contains": []}
        ]

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_finali,
        "ricette": ricette_finali
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 FILE SALVATO CORRETTAMENTE.")

if __name__ == "__main__":
    genera_tutto()

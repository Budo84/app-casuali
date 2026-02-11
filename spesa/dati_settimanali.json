import os
import json
import google.generativeai as genai
from datetime import datetime

# Configurazione API
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("⚠️ Chiave GEMINI_KEY non trovata.")
    exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def genera_tutto():
    print("🤖 IL ROBOT È SVEGLIO...")
    
    # 1. OFFERTE
    mese = datetime.now().strftime("%B")
    prompt_offerte = f"""
    Genera JSON puro di 15 prodotti alimentari in offerta a {mese} nei supermercati italiani.
    Format: [{{"name": "prodotto", "price": 1.99}}]
    """
    try:
        resp = model.generate_content(prompt_offerte)
        text_off = resp.text.replace("```json", "").replace("```", "").strip()
        offerte = json.loads(text_off)
        nomi = [o['name'] for o in offerte]
        print(f"✅ Offerte trovate: {len(offerte)}")
    except Exception as e:
        print(f"❌ Errore Offerte: {e}")
        return

    # 2. RICETTE
    prompt_ricette = f"""
    Usa questi ingredienti: {', '.join(nomi)}.
    Crea 21 ricette (colazione, pranzo, cena).
    Format JSON:
    [{{ "name": "Nome", "type": "pranzo", "contains": ["glutine"], "ingredients": ["pasta"], "desc": "..." }}]
    """
    try:
        resp = model.generate_content(prompt_ricette)
        text_ric = resp.text.replace("```json", "").replace("```", "").strip()
        ricette = json.loads(text_ric)
        print(f"✅ Ricette create: {len(ricette)}")
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        return

    # 3. SALVATAGGIO (PERCORSO CORRETTO: SPESA)
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte": offerte,
        "ricette": ricette
    }
    
    # Percorso relativo alla radice del repository
    cartella_target = "spesa"
    path_file = "spesa/dati_settimanali.json"
    
    # Crea la cartella se non esiste (sicurezza)
    if not os.path.exists(cartella_target):
        os.makedirs(cartella_target)
        print(f"📁 Cartella '{cartella_target}' creata.")

    with open(path_file, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
        
    print(f"💾 FILE SALVATO IN: {path_file}")

if __name__ == "__main__":
    genera_tutto()

import os
import json
import google.generativeai as genai
from datetime import datetime

# 1. SETUP API KEY
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE GRAVE: Chiave GEMINI_KEY non trovata nei Secrets!")
    exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def genera_tutto():
    print("🤖 START: Inizio generazione...")
    
    # 2. CALCOLO PERCORSO ASSOLUTO (Così non sbaglia mai cartella)
    # Trova la cartella dove si trova QUESTO file python (cioè 'spesa')
    cartella_script = os.path.dirname(os.path.abspath(__file__))
    file_output = os.path.join(cartella_script, "dati_settimanali.json")
    
    print(f"📂 Il file verrà salvato qui: {file_output}")

    # 3. OFFERTE
    try:
        print("🔍 Cerco offerte...")
        mese = datetime.now().strftime("%B")
        prompt = f"""Genera JSON puro di 15 prodotti alimentari in offerta a {mese}. Format: [{{"name": "pasta", "price": 0.99}}]"""
        resp = model.generate_content(prompt)
        offerte = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
        nomi = [o['name'] for o in offerte]
    except Exception as e:
        print(f"❌ ERRORE IA (Offerte): {e}")
        # Creiamo dati finti per non rompere l'app se l'IA fallisce
        offerte = [{"name": "Errore Generazione", "price": 0.00}]
        nomi = ["Pane"]

    # 4. RICETTE
    try:
        print("👨‍🍳 Creo ricette...")
        prompt = f"""Crea 21 ricette con: {', '.join(nomi)}. Format JSON: [{{ "name": "Nome", "type": "pranzo", "contains": [], "ingredients": [], "desc": "" }}]"""
        resp = model.generate_content(prompt)
        ricette = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        print(f"❌ ERRORE IA (Ricette): {e}")
        ricette = []

    # 5. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte": offerte,
        "ricette": ricette
    }

    try:
        with open(file_output, "w", encoding="utf-8") as f:
            json.dump(database, f, indent=4, ensure_ascii=False)
        print("✅ SALVATAGGIO RIUSCITO!")
    except Exception as e:
        print(f"❌ ERRORE SCRITTURA FILE: {e}")
        exit(1)

if __name__ == "__main__":
    genera_tutto()

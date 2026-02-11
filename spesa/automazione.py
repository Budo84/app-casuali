import os
import json
import google.generativeai as genai
from datetime import datetime

# CONFIGURAZIONE
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ Chiave GEMINI_KEY mancante.")
    exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def genera_tutto():
    print("🤖 START...")
    
    # PERCORSO
    path_script = os.path.dirname(os.path.abspath(__file__))
    path_file = os.path.join(path_script, "dati_settimanali.json")

    # 1. OFFERTE
    try:
        mese = datetime.now().strftime("%B")
        prompt = f"""Genera JSON di 15 cibi in offerta a {mese} (supermercato ita). Format: [{{"name":"pasta","price":0.99}}]"""
        resp = model.generate_content(prompt)
        offerte = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
        nomi = [o['name'] for o in offerte]
    except:
        offerte = []
        nomi = ["Pasta", "Riso", "Pollo", "Uova", "Zucchine"]

    # 2. RICETTE (IL PUNTO CRUCIALE: LE PAROLE CHIAVE)
    try:
        print("👨‍🍳 Genero ricette...")
        prompt = f"""
        Crea 25 ricette usando: {', '.join(nomi)}.
        
        REGOLE FONDAMENTALI PER 'contains':
        Devi segnalare gli allergeni usando ESATTAMENTE queste parole chiave (e nessun'altra):
        - "glutine" (per pane, pasta, farina, orzo)
        - "lattosio" (per latte, burro, formaggio, panna)
        - "uova"
        - "pesce"
        - "frutta_guscio" (per noci, mandorle, pistacchi, nocciole)
        
        Se non c'è allergene, lascia la lista vuota: [].
        
        Format JSON:
        [
            {{ 
                "name": "Pasta al pesto", 
                "type": "pranzo", 
                "contains": ["glutine", "lattosio", "frutta_guscio"], 
                "ingredients": ["pasta", "basilico", "pinoli", "parmigiano"], 
                "desc": "Piatto classico" 
            }}
        ]
        """
        resp = model.generate_content(prompt)
        ricette = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        ricette = []

    # 3. SALVATAGGIO
    database = { "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"), "offerte": offerte, "ricette": ricette }
    
    if not os.path.exists(path_script): os.makedirs(path_script)
    with open(path_file, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("✅ Salvato.")

if __name__ == "__main__":
    genera_tutto()

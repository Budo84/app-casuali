import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

# --- CONFIGURAZIONE ---
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# Trova modello (Auto-Configurante)
def trova_modello():
    try:
        mods = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Cerca Flash > Pro > Altro
        best = next((m for m in mods if "flash" in m), next((m for m in mods if "pro" in m), mods[0]))
        return genai.GenerativeModel(best)
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

model = trova_modello()

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    start, end = testo.find('['), testo.rfind(']') + 1
    if start == -1: start, end = testo.find('{'), testo.rfind('}') + 1
    if start != -1 and end != -1: return testo[start:end]
    return testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    # 1. OFFERTE PER SUPERMERCATO
    print("1. Genero OFFERTE MULTI-STORE...")
    supermercati = ["Conad", "Coop", "Esselunga", "Lidl", "Eurospin"]
    offerte_db = {}
    tutti_prodotti = set()

    try:
        prompt = f"""
        Agisci come un database di prezzi italiano.
        Genera offerte realistiche per questi supermercati: {', '.join(supermercati)}.
        Per OGNI supermercato, elenca 8 prodotti in offerta (pasta, carne, verdura, scatolame).
        
        Rispondi SOLO con questo JSON esatto:
        {{
            "Conad": [{{"name": "Pasta Barilla", "price": 0.79}}, {{"name": "Passata", "price": 0.89}}],
            "Lidl": [{{"name": "Pasta Combino", "price": 0.65}}, {{"name": "Pollo", "price": 3.99}}],
            ... (fai così per tutti)
        }}
        """
        resp = model.generate_content(prompt)
        offerte_db = json.loads(pulisci_json(resp.text))
        
        # Raccogliamo tutti i nomi dei prodotti per creare le ricette
        for store in offerte_db:
            for item in offerte_db[store]:
                tutti_prodotti.add(item['name'])
        
        print(f"✅ Offerte generate per: {list(offerte_db.keys())}")
        
    except Exception as e:
        print(f"❌ Errore Offerte: {e}")
        offerte_db = {"Genarico": [{"name": "Pasta", "price": 1.00}]}
        tutti_prodotti = ["Pasta", "Pomodoro", "Uova"]

    # 2. RICETTE
    print("2. Genero RICETTE...")
    lista_ing = list(tutti_prodotti)[:20] # Prendiamo i primi 20 per non confondere l'AI
    try:
        prompt = f"""
        Crea 21 ricette italiane usando: {', '.join(lista_ing)}.
        Usa ESATTAMENTE questi tag 'contains': "glutine", "lattosio", "uova", "pesce", "frutta_guscio".
        Format JSON:
        [{{ "name": "Nome", "type": "pranzo", "contains": ["glutine"], "ingredients": ["pasta", "pomodoro"], "desc": "..." }}]
        """
        resp = model.generate_content(prompt)
        ricette = json.loads(pulisci_json(resp.text))
        print(f"✅ {len(ricette)} ricette generate.")
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        ricette = []

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte_per_supermercato": offerte_db, # Nuova struttura
        "ricette": ricette
    }

    if not os.path.exists(os.path.dirname(file_out)): os.makedirs(os.path.dirname(file_out))
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Salvato.")

if __name__ == "__main__":
    genera_tutto()

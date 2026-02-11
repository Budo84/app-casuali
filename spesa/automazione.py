import os
import json
import google.generativeai as genai
from datetime import datetime

# Configurazione API (Prende la chiave dai Segreti di GitHub)
if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    # Fallback solo per test locale sul tuo PC (se non usi GitHub Actions)
    print("⚠️ Chiave GEMINI_KEY non trovata nelle variabili d'ambiente.")
    exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def genera_tutto():
    print("🤖 IL ROBOT È SVEGLIO...")
    
    # --- 1. IDENTIFICAZIONE OFFERTE (SIMULAZIONE SMART) ---
    mese_corrente = datetime.now().strftime("%B")
    
    prompt_offerte = f"""
    Sei un esperto di supermercati italiani. Siamo a {mese_corrente}.
    Genera una lista JSON realistica di 15 prodotti alimentari che si trovano tipicamente in offerta nei volantini (es. Conad, Coop, Esselunga) in questo periodo dell'anno.
    Includi verdure di stagione, carne, pasta e scatolame.
    Assegna un prezzo realistico in offerta (es. 0.99, 1.50).
    
    Format JSON: 
    [
        {{"name": "nome prodotto", "price": 0.99}},
        ...
    ]
    Rispondi SOLO con il JSON puro, niente markdown.
    """
    
    print("🔍 Cerco offerte stagionali...")
    try:
        resp_off = model.generate_content(prompt_offerte)
        text_off = resp_off.text.replace("```json", "").replace("```", "").strip()
        offerte = json.loads(text_off)
    except Exception as e:
        print(f"❌ Errore generazione offerte: {e}")
        return

    nomi_offerte = [o['name'] for o in offerte]
    print(f"✅ Trovate {len(offerte)} offerte: {nomi_offerte[:3]}...")

    # --- 2. GENERAZIONE MENU E RICETTE ---
    print("👨‍🍳 Lo Chef IA sta cucinando i dati...")
    
    prompt_ricette = f"""
    Ho questi ingredienti in offerta: {', '.join(nomi_offerte)}.
    Crea un database JSON con 21 ricette (per una settimana: colazione, pranzo, cena).
    
    REGOLE:
    1. Usa il più possibile gli ingredienti in offerta.
    2. Varia le ricette (carne, pesce, vegetariane).
    3. Indica chiaramente gli allergeni nel campo 'contains' (es. glutine, lattosio, uova, pesce).
    
    FORMATO JSON OBBLIGATORIO:
    [
        {{
            "name": "Nome Ricetta",
            "type": "pranzo", 
            "contains": ["glutine", "lattosio"], 
            "ingredients": ["ingrediente1", "ingrediente2"],
            "desc": "Breve descrizione"
        }}
    ]
    Rispondi SOLO con il JSON puro.
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        text_ric = resp_ric.text.replace("```json", "").replace("```", "").strip()
        ricette = json.loads(text_ric)
    except Exception as e:
        print(f"❌ Errore generazione ricette: {e}")
        return
    
    # --- 3. SALVATAGGIO ---
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte": offerte,
        "ricette": ricette
    }
    
    # Determina il percorso della cartella dove si trova QUESTO script
    cartella_corrente = os.path.dirname(os.path.abspath(__file__))
    percorso_file = os.path.join(cartella_corrente, "dati_settimanali.json")
    
    with open(percorso_file, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
        
    print(f"💾 Dati salvati correttamente in: {percorso_file}")

if __name__ == "__main__":
    genera_tutto()

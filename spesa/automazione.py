import os
import json
import google.generativeai as genai
from datetime import datetime

# Configurazione
API_KEY = os.environ["GEMINI_KEY"] # Prende la chiave dai segreti di GitHub
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def genera_tutto():
    print("🤖 IL ROBOT È SVEGLIO...")
    
    # 1. IDENTIFICAZIONE OFFERTE (SIMULAZIONE SMART)
    # Chiediamo a Gemini di agire come un esperto di spesa che conosce le offerte attuali
    # (Per uno scraping reale di PDF servirebbero librerie pesanti che rallentano le Action, 
    # questo metodo è più stabile per una demo e dà risultati realistici basati sulla stagione)
    mese_corrente = datetime.now().strftime("%B")
    
    prompt_offerte = f"""
    Sei un esperto di supermercati italiani. Siamo a {mese_corrente}.
    Genera una lista JSON realistica di 15 prodotti alimentari che si trovano tipicamente in offerta nei volantini (es. Conad, Coop, Esselunga) in questo periodo dell'anno.
    Includi verdure di stagione, carne, pasta e scatolame.
    Assegna un prezzo realistico in offerta.
    
    Format: [{"name": "nome prodotto", "price": 0.99}, ...]
    Solo JSON puro.
    """
    
    print("🔍 Cerco offerte stagionali...")
    resp_off = model.generate_content(prompt_offerte)
    offerte = json.loads(resp_off.text.replace("```json", "").replace("```", "").strip())
    
    nomi_offerte = [o['name'] for o in offerte]
    print(f"✅ Trovate {len(offerte)} offerte: {nomi_offerte[:3]}...")

    # 2. GENERAZIONE MENU E RICETTE
    print("👨‍🍳 Lo Chef IA sta cucinando i dati...")
    
    prompt_ricette = f"""
    Ho questi ingredienti in offerta: {', '.join(nomi_offerte)}.
    Crea un database JSON con 21 ricette (per una settimana: colazione, pranzo, cena).
    
    REGOLE:
    1. Usa il più possibile gli ingredienti in offerta.
    2. Varia le ricette (carne, pesce, vegetariane).
    3. Indica chiaramente gli allergeni nel campo 'contains'.
    
    FORMATO JSON OBBLIGATORIO:
    [
        {{
            "name": "Nome Ricetta",
            "type": "pranzo" (o cena o colazione),
            "contains": ["glutine", "lattosio"], (array vuoto se nessuno)
            "ingredients": ["ingrediente1", "ingrediente2"],
            "desc": "Breve descrizione"
        }}
    ]
    Solo JSON puro.
    """
    
    resp_ric = model.generate_content(prompt_ricette)
    ricette = json.loads(resp_ric.text.replace("```json", "").replace("```", "").strip())
    
    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte": offerte,
        "ricette": ricette
    }
    
    # Salviamo nella cartella 'menu' così l'app lo trova
    os.makedirs("menu", exist_ok=True)
    with open("menu/dati_settimanali.json", "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
        
    print("💾 Dati salvati in menu/dati_settimanali.json")

if __name__ == "__main__":
    genera_tutto()

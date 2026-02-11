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

# Configurazione per forzare l'output JSON puro (Niente testo inutile)
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    # 1. OFFERTE (MARCHE REALI)
    print("1. Richiedo OFFERTE (JSON Mode)...")
    supermercati = ["Conad", "Coop", "Esselunga", "Lidl", "Eurospin", "Pewex", "MA Supermercati", "Ipercarni", "Todis"]
    
    prompt_offerte = f"""
    Genera un oggetto JSON con le offerte per questi supermercati: {', '.join(supermercati)}.
    Usa MARCHE REALI ITALIANE (es. Barilla, Mutti, Granarolo, Rana).
    Per ogni supermercato inserisci esattamente 8 prodotti vari (Pasta, Latte, Colazione, Freschi).
    
    Struttura richiesta:
    {{
      "Conad": [ {{"name": "Pasta Barilla 500g", "price": 0.89}}, ... ],
      "Coop": [ ... ]
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(resp.text)
        print("✅ Offerte scaricate correttamente.")
    except Exception as e:
        print(f"❌ Errore Offerte: {e}")
        # Dati minimi di fallback per non rompere l'app
        offerte_db = {s: [{"name": "Offerte in aggiornamento", "price": 0.00}] for s in supermercati}

    # 2. RICETTE (DIETA MEDITERRANEA)
    print("2. Richiedo MENU MEDITERRANEO (JSON Mode)...")
    
    # Prendiamo spunto dalle offerte, ma chiediamo ricette generiche
    prompt_ricette = """
    Sei un nutrizionista italiano. Crea un database di ricette per una settimana seguendo la DIETA MEDITERRANEA.
    Usa ingredienti generici (es. "Pasta", non "Pasta Barilla").
    
    Devi restituire un oggetto JSON con esattamente queste 4 categorie:
    
    1. "colazione": 7 ricette dolci/sane (Latte, Caffè, Yogurt, Fette biscottate, Marmellata, Biscotti). NO PELATI, NO SUGO.
    2. "pranzo": 7 ricette carboidrati (Pasta, Riso, Farro, Legumi, Gnocchi).
    3. "merenda": 7 ricette leggere (Frutta fresca, Yogurt, Tè, Pane e olio).
    4. "cena": 7 ricette proteine + verdure (Carne, Pesce, Uova, Formaggi, Minestrone). NO PASTA PESANTE.

    Struttura richiesta:
    {
      "colazione": [ {"title": "Latte e Biscotti", "ingredients": ["Latte parzialmente scremato", "Biscotti integrali"], "contains": ["lattosio", "glutine"]} ],
      "pranzo": [ ... ],
      "merenda": [ ... ],
      "cena": [ ... ]
    }
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        ricette_db = json.loads(resp.text)
        
        # Trasformiamo in lista unica aggiungendo il campo 'type'
        lista_ricette = []
        for categoria, piatti in ricette_db.items():
            for piatto in piatti:
                piatto['type'] = categoria # Fondamentale per l'app
                lista_ricette.append(piatto)
                
        print(f"✅ Menu generato: {len(lista_ricette)} ricette.")
        
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        # Fallback Ricette per evitare schermo bianco
        lista_ricette = [
            {"title": "Latte e Caffè", "type": "colazione", "ingredients": ["Latte", "Caffè"], "contains": ["lattosio"]},
            {"title": "Pasta al Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Passata di pomodoro"], "contains": ["glutine"]},
            {"title": "Mela", "type": "merenda", "ingredients": ["Mela"], "contains": []},
            {"title": "Petto di Pollo e Insalata", "type": "cena", "ingredients": ["Petto di pollo", "Insalata"], "contains": []}
        ]

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_db,
        "ricette": lista_ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 File salvato con successo.")

if __name__ == "__main__":
    genera_tutto()

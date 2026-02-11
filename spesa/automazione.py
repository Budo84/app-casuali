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
model = genai.GenerativeModel('gemini-1.5-flash')

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    if testo.startswith("{"):
        start, end = testo.find('{'), testo.rfind('}') + 1
    else:
        start, end = testo.find('['), testo.rfind(']') + 1
    return testo[start:end] if start != -1 and end != -1 else testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    # 1. OFFERTE (MARCHE REALI)
    supermercati = ["Conad", "Coop", "Esselunga", "Lidl", "Eurospin", "Pewex", "MA Supermercati", "Ipercarni", "Todis"]
    
    prompt_offerte = f"""
    Genera JSON offerte per: {', '.join(supermercati)}.
    Usa MARCHE REALI ITALIANE.
    Per ogni supermercato inserisci:
    - 2 Prodotti Colazione (es. Biscotti Mulino Bianco, Caffè Lavazza, Latte Granarolo)
    - 3 Prodotti Dispensa (es. Pasta Barilla, Riso Gallo, Passata Mutti)
    - 3 Freschi (es. Pollo Amadori, Uova, Mozzarella Santa Lucia, Mele, Zucchine)
    
    FORMATO: {{ "Conad": [{{"name": "Pasta Barilla 500g", "price": 0.79}}], ... }}
    """
    
    try:
        print("1. Genero Offerte...")
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
    except:
        offerte_db = {s: [{"name": "Pasta Barilla", "price": 0.90}] for s in supermercati}

    # 2. RICETTE (DIETA MEDITERRANEA RIGIDA)
    # Estraiamo ingredienti per ispirazione
    ing_list = []
    for s in offerte_db:
        for p in offerte_db[s]:
            ing_list.append(p['name'])
    ing_str = ', '.join(list(set(ing_list))[:30])

    prompt_ricette = f"""
    Crea un database di ricette per una DIETA MEDITERRANEA.
    Usa ingredienti generici (es. "Pasta", non "Pasta Barilla").
    Ispirati a queste offerte: {ing_str}.

    DEVI GENERARE 4 LISTE DISTINTE NEL JSON:
    1. "colazione": 7 ricette DOLCI (Biscotti, Latte, Caffè, Yogurt, Frutta, Fette biscottate). VIETATO: Salato, Sugo, Carne.
    2. "pranzo": 7 ricette PRIMI PIATTI (Pasta, Riso, Farro, Legumi).
    3. "merenda": 7 ricette LEGGERE (Frutta, Yogurt, Snack).
    4. "cena": 7 ricette SECONDI PIATTI + CONTORNO (Carne, Pesce, Uova, Formaggi + Verdure). VIETATO: Pasta, Riso.

    FORMATO OBBLIGATORIO:
    {{
        "colazione": [ {{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"], "contains": ["lattosio", "glutine"]}} ],
        "pranzo": [ ... ],
        "merenda": [ ... ],
        "cena": [ ... ]
    }}
    """
    
    print("2. Genero Menu Mediterraneo...")
    try:
        resp_ric = model.generate_content(prompt_ricette)
        ricette_raw = json.loads(pulisci_json(resp.text))
        
        # Appiattiamo il dizionario in una lista unica con il campo 'type' corretto
        ricette_finali = []
        for tipo in ["colazione", "pranzo", "merenda", "cena"]:
            for r in ricette_raw.get(tipo, []):
                r["type"] = tipo # Assegna il tipo corretto
                ricette_finali.append(r)
                
        print(f"✅ {len(ricette_finali)} ricette generate.")

    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        ricette_finali = []

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte_per_supermercato": offerte_db,
        "ricette": ricette_finali
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Salvato.")

if __name__ == "__main__":
    genera_tutto()

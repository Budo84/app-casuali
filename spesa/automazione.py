import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import re

# --- 1. CONFIGURAZIONE BASE ---
if "GEMINI_KEY" not in os.environ:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=os.environ["GEMINI_KEY"])

# --- 2. SELEZIONE AUTOMATICA DEL MODELLO ---
def get_best_model():
    print("🔍 Cerco modelli disponibili...")
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        
        print(f"   Modelli trovati: {available}")
        
        # Cerca il migliore in ordine di preferenza
        # 1.5 Flash è veloce e supporta JSON nativo
        for m in available:
            if "gemini-1.5-flash" in m: return m, True  # True = Supporta JSON Mode
        for m in available:
            if "gemini-1.5-pro" in m: return m, True
        
        # Fallback sui vecchi (non supportano JSON nativo, usiamo pulizia manuale)
        for m in available:
            if "gemini-pro" in m: return m, False
            
        return available[0], False
    except Exception as e:
        print(f"⚠️ Errore ricerca modelli: {e}. Provo default.")
        return "models/gemini-pro", False

model_name, supports_json_mode = get_best_model()
print(f"🤖 MODELLO SCELTO: {model_name} (JSON Mode: {supports_json_mode})")

# Configurazione dinamica
config = {"temperature": 0.7, "max_output_tokens": 8192}
if supports_json_mode:
    config["response_mime_type"] = "application/json"

model = genai.GenerativeModel(model_name, generation_config=config)

# --- 3. FUNZIONI DI PULIZIA ---
def pulisci_json(testo):
    # Se il modello non supporta JSON mode, puliamo il markdown
    testo = testo.replace("```json", "").replace("```", "").strip()
    # Trova la prima parentesi aperta e l'ultima chiusa
    if testo.startswith("{") or "{" in testo:
        start = testo.find('{')
        end = testo.rfind('}') + 1
        return testo[start:end]
    elif testo.startswith("[") or "[" in testo:
        start = testo.find('[')
        end = testo.rfind(']') + 1
        return testo[start:end]
    return testo

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")

    supermercati = [
        "Conad", "Coop", "Esselunga", "Lidl", "Eurospin", 
        "Pewex", "MA Supermercati", "Ipercarni", "Todis"
    ]

    # --- FASE 1: OFFERTE (MARCHE SPECIFICHE) ---
    print("1. Genero OFFERTE...")
    prompt_offerte = f"""
    Genera un JSON con offerte per questi supermercati: {', '.join(supermercati)}.
    Usa MARCHE REALI ITALIANE (es. Barilla, Mutti, Granarolo).
    Per ogni supermercato inserisci 6 prodotti con prezzi realistici (Pasta, Latte, Biscotti, Freschi).
    
    Struttura JSON richiesta:
    {{
      "Conad": [ {{"name": "Pasta Barilla 500g", "price": 0.89}}, ... ],
      "Coop": [ ... ]
    }}
    """
    
    try:
        resp = model.generate_content(prompt_offerte)
        text = resp.text
        if not supports_json_mode: text = pulisci_json(text)
        offerte_db = json.loads(text)
        print("✅ Offerte OK.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}")
        offerte_db = {s: [{"name": "Offerte in arrivo", "price": 0.00}] for s in supermercati}

    # --- FASE 2: RICETTE (DIETA MEDITERRANEA) ---
    print("2. Genero MENU MEDITERRANEO...")
    
    # Istruzioni diverse in base al supporto JSON
    format_instr = "Rispondi SOLO con il JSON."
    if not supports_json_mode:
        format_instr = "NON usare markdown. Inizia con { e finisci con }."

    prompt_ricette = f"""
    Agisci come un nutrizionista. Crea un menu settimanale DIETA MEDITERRANEA.
    Usa ingredienti GENERICI (es. "Pasta", non "Pasta Barilla").
    
    Devi restituire un oggetto JSON con queste 4 chiavi esatte:
    1. "colazione": 7 ricette dolci (Latte, Caffè, Fette biscottate).
    2. "pranzo": 7 ricette carboidrati (Pasta, Riso, Legumi).
    3. "merenda": 7 ricette leggere (Frutta, Yogurt).
    4. "cena": 7 ricette proteine (Carne, Pesce, Uova) + verdure.

    {format_instr}
    
    Esempio Struttura:
    {{
      "colazione": [ {{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"], "contains": ["lattosio", "glutine"]}} ],
      "pranzo": [ ... ],
      "merenda": [ ... ],
      "cena": [ ... ]
    }}
    """
    
    try:
        resp_ric = model.generate_content(prompt_ricette)
        text_ric = resp_ric.text
        if not supports_json_mode: text_ric = pulisci_json(text_ric)
        ricette_raw = json.loads(text_ric)
        
        # Trasformazione in lista unica per l'app
        lista_ricette = []
        for categoria in ["colazione", "pranzo", "merenda", "cena"]:
            for piatto in ricette_raw.get(categoria, []):
                piatto['type'] = categoria
                lista_ricette.append(piatto)
                
        print(f"✅ Menu OK: {len(lista_ricette)} ricette.")
        
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        # Fallback minimo
        lista_ricette = [
            {"title": "Caffè", "type": "colazione", "ingredients": ["Caffè"], "contains": []},
            {"title": "Pasta al Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Pomodoro"], "contains": ["glutine"]},
            {"title": "Mela", "type": "merenda", "ingredients": ["Mela"], "contains": []},
            {"title": "Pollo e Insalata", "type": "cena", "ingredients": ["Pollo", "Insalata"], "contains": []}
        ]

    # --- SALVATAGGIO ---
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_db,
        "ricette": lista_ricette
    }

    if not os.path.exists(os.path.dirname(file_out)):
        os.makedirs(os.path.dirname(file_out))

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Salvato.")

if __name__ == "__main__":
    genera_tutto()

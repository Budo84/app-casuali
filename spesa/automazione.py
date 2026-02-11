import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

# --- CONFIGURAZIONE ---
print("--- INIZIO AUTOMAZIONE INTELLIGENTE ---")

if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# --- FUNZIONE MAGICA: TROVA IL MODELLO GIUSTO ---
def trova_modello_funzionante():
    print("🔍 Cerco un modello AI disponibile per la tua chiave...")
    try:
        # Chiede a Google la lista dei modelli
        modelli_disponibili = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelli_disponibili.append(m.name)
        
        print(f"   Modelli trovati: {modelli_disponibili}")
        
        # Cerca il migliore (priorità: Flash > Pro > Altri)
        modello_scelto = None
        
        # 1. Cerca qualcosa con "flash" (più veloce)
        for m in modelli_disponibili:
            if "flash" in m and "legacy" not in m:
                modello_scelto = m
                break
        
        # 2. Se non c'è, cerca "pro"
        if not modello_scelto:
            for m in modelli_disponibili:
                if "pro" in m and "legacy" not in m:
                    modello_scelto = m
                    break
                    
        # 3. Altrimenti prendi il primo della lista
        if not modello_scelto and modelli_disponibili:
            modello_scelto = modelli_disponibili[0]
            
        if modello_scelto:
            print(f"✅ MODELLO SELEZIONATO: {modello_scelto}")
            return genai.GenerativeModel(modello_scelto)
        else:
            print("❌ NESSUN MODELLO COMPATIBILE TROVATO.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Errore durante la ricerca modelli: {e}")
        # TENTATIVO DISPERATO CON QUELLO STANDARD
        print("⚠️ Provo forzatamente 'gemini-1.5-flash'...")
        return genai.GenerativeModel('gemini-1.5-flash')

# INIZIALIZZA IL MODELLO TROVATO
model = trova_modello_funzionante()

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    start = testo.find('[')
    end = testo.rfind(']') + 1
    if start != -1 and end != -1:
        return testo[start:end]
    return testo

def genera_tutto():
    cartella_script = os.path.dirname(os.path.abspath(__file__))
    file_output = os.path.join(cartella_script, "dati_settimanali.json")

    # 1. OFFERTE
    print("\n1. Genero OFFERTE...")
    try:
        prompt = """
        Rispondi SOLO JSON. Lista di 15 prodotti alimentari italiani in offerta.
        Format: [{"name": "Pasta", "price": 0.89}]
        """
        resp = model.generate_content(prompt)
        offerte = json.loads(pulisci_json(resp.text))
        nomi = [o['name'] for o in offerte]
        print(f"✅ {len(offerte)} offerte generate.")
    except Exception as e:
        print(f"⚠️ Errore Offerte: {e}. Uso dati backup.")
        offerte = [{"name": "Pasta", "price": 1.00}, {"name": "Pollo", "price": 5.00}]
        nomi = ["Pasta", "Pollo"]

    # 2. RICETTE
    print("\n2. Genero RICETTE...")
    try:
        prompt = f"""
        Rispondi SOLO JSON. Crea 21 ricette con: {', '.join(nomi)}.
        Usa ESATTAMENTE questi tag per 'contains': "glutine", "lattosio", "uova", "pesce", "frutta_guscio".
        Format: [{{"name": "Nome", "type": "pranzo", "contains": ["glutine"], "ingredients": ["pasta"], "desc": "..."}}]
        """
        resp = model.generate_content(prompt)
        ricette = json.loads(pulisci_json(resp.text))
        print(f"✅ {len(ricette)} ricette generate.")
    except Exception as e:
        print(f"❌ Errore Ricette: {e}")
        ricette = []

    # 3. SALVA
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y"),
        "offerte": offerte,
        "ricette": ricette
    }

    if not os.path.exists(os.path.dirname(file_output)):
        os.makedirs(os.path.dirname(file_output))

    with open(file_output, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print(f"\n💾 SALVATO: {file_output}")

if __name__ == "__main__":
    genera_tutto()

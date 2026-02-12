import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import random

# --- CONFIGURAZIONE ---
print("--- START: AUTOMAZIONE IBRIDA ---")

if "GEMINI_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_KEY"]
else:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# --- DATI DI BACKUP (SALVAVITA) ---
# Se l'IA fallisce, usiamo questi dati per non lasciare l'app vuota
BACKUP_OFFERTE = {
    "Conad": [{"name": "Pasta Barilla 500g", "price": 0.79}, {"name": "Passata Mutti", "price": 0.99}],
    "Lidl": [{"name": "Pasta Combino", "price": 0.65}, {"name": "Yogurt Greco Milbona", "price": 0.89}],
    "Pewex": [{"name": "Bistecca Manzo", "price": 12.90}, {"name": "Pane Casareccio", "price": 1.90}],
    "Todis": [{"name": "Latte UHT", "price": 0.79}, {"name": "Biscotti", "price": 1.50}],
    "Coop": [{"name": "Riso Gallo", "price": 2.10}],
    "Esselunga": [{"name": "Uova Bio", "price": 2.20}],
    "Eurospin": [{"name": "Olio EVO", "price": 5.50}],
    "MA Supermercati": [{"name": "Mozzarella", "price": 1.00}],
    "Ipercarni": [{"name": "Petto di Pollo", "price": 6.90}]
}

BACKUP_RICETTE = [
    {"title": "Latte e Biscotti", "type": "colazione", "ingredients": ["Latte", "Biscotti"], "contains": ["lattosio", "glutine"]},
    {"title": "Pasta al Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Passata di pomodoro", "Olio EVO"], "contains": ["glutine"]},
    {"title": "Mela", "type": "merenda", "ingredients": ["Mela"], "contains": []},
    {"title": "Petto di Pollo e Insalata", "type": "cena", "ingredients": ["Petto di pollo", "Insalata"], "contains": []}
]

# --- 1. SELEZIONE MODELLO (LA TUA FUNZIONE) ---
def trova_modello_funzionante():
    print("🔍 Cerco modello AI...")
    try:
        modelli = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priorità: Flash > Pro > Altri
        scelto = next((m for m in modelli if "flash" in m), next((m for m in modelli if "pro" in m), modelli[0]))
        
        print(f"✅ Modello trovato: {scelto}")
        return genai.GenerativeModel(scelto)
    except Exception as e:
        print(f"⚠️ Errore ricerca: {e}. Uso fallback 'gemini-pro'")
        return genai.GenerativeModel('gemini-pro')

model = trova_modello_funzionante()

# --- 2. PULIZIA OUTPUT ---
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
    
    # Inizializziamo con i backup (così se fallisce, salva questi)
    offerte_finali = BACKUP_OFFERTE
    ricette_finali = BACKUP_RICETTE

    try:
        # --- FASE A: OFFERTE (MARCHE REALI) ---
        print("1. Genero Offerte...")
        supermercati = ["Conad", "Coop", "Esselunga", "Lidl", "Eurospin", "Pewex", "MA Supermercati", "Ipercarni", "Todis"]
        
        prompt_off = f"""
        Genera JSON offerte per: {', '.join(supermercati)}.
        Usa MARCHE REALI (es. Pasta Barilla, Latte Granarolo).
        6 prodotti per negozio.
        RISPONDI SOLO JSON: {{ "Conad": [{{"name": "Pasta Barilla", "price": 0.89}}] }}
        """
        resp = model.generate_content(prompt_off)
        offerte_finali = json.loads(pulisci_json(resp.text))
        print("✅ Offerte OK.")

        # --- FASE B: RICETTE (GENERICHE & MEDITERRANEE) ---
        print("2. Genero Menu...")
        prompt_ric = """
        Crea un menu settimanale DIETA MEDITERRANEA.
        Usa ingredienti GENERICI (es. "Pasta", NON "Pasta Barilla").
        
        Devi restituire un JSON con 4 liste:
        1. "colazione": 7 ricette dolci.
        2. "pranzo": 7 ricette primi piatti.
        3. "merenda": 7 ricette leggere.
        4. "cena": 7 ricette secondi + contorno.

        RISPONDI SOLO JSON:
        {
          "colazione": [ {"title": "Caffè", "ingredients": ["Caffè"], "contains": []} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }
        """
        resp_ric = model.generate_content(prompt_ric)
        ricette_raw = json.loads(pulisci_json(resp_ric.text))
        
        # Appiattiamo il dizionario in una lista unica per l'app
        temp_list = []
        for tipo in ["colazione", "pranzo", "merenda", "cena"]:
            for piatto in ricette_raw.get(tipo, []):
                piatto['type'] = tipo
                temp_list.append(piatto)
        
        if len(temp_list) > 5:
            ricette_finali = temp_list
            print("✅ Menu OK.")

    except Exception as e:
        print(f"❌ ERRORE IA: {e}")
        print("⚠️ Uso dati di Backup.")

    # --- SALVATAGGIO ---
    # Verifica che tutti i supermercati esistano nel JSON finale
    for s in ["Pewex", "Todis", "Ipercarni", "MA Supermercati"]:
        if s not in offerte_finali:
            offerte_finali[s] = BACKUP_OFFERTE.get(s, [])

    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_finali,
        "ricette": ricette_finali
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Salvato.")

if __name__ == "__main__":
    genera_tutto()

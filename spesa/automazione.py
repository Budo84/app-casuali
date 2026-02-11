import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import traceback

print("--- DIAGNOSTICA INIZIATA ---")
print(f"Versione Libreria Google: {genai.__version__}")

# 1. CONTROLLO CHIAVE
if "GEMINI_KEY" not in os.environ:
    print("❌ ERRORE CRITICO: La variabile 'GEMINI_KEY' non esiste nei Secrets.")
    sys.exit(1)

API_KEY = os.environ["GEMINI_KEY"]
print(f"Chiave trovata: {API_KEY[:5]}... (lunghezza: {len(API_KEY)})")
genai.configure(api_key=API_KEY)

def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    if testo.startswith("{"):
        start, end = testo.find('{'), testo.rfind('}') + 1
    else:
        start, end = testo.find('['), testo.rfind(']') + 1
    return testo[start:end] if start != -1 and end != -1 else testo

# DATI DI BACKUP (Se l'IA fallisce, usiamo questi così l'app funziona)
BACKUP_OFFERTE = {
    "Conad": [{"name": "Pasta Integrale Barilla", "price": 0.95}, {"name": "Passata Mutti", "price": 0.89}],
    "Coop": [{"name": "Riso Gallo", "price": 1.99}, {"name": "Latte Granarolo", "price": 1.15}],
    "Esselunga": [{"name": "Uova Bio", "price": 2.10}, {"name": "Parmigiano", "price": 4.50}],
    "Lidl": [{"name": "Yogurt Greco", "price": 0.99}, {"name": "Pollo", "price": 3.50}]
}

BACKUP_RICETTE = [
    {"title": "Latte e Biscotti Integrali", "type": "colazione", "ingredients": ["Latte", "Biscotti integrali"], "contains": ["lattosio", "glutine"]},
    {"title": "Pasta al Pomodoro e Basilico", "type": "pranzo", "ingredients": ["Pasta", "Passata di pomodoro", "Basilico"], "contains": ["glutine"]},
    {"title": "Mela e Noci", "type": "merenda", "ingredients": ["Mela", "Noci"], "contains": ["frutta_guscio"]},
    {"title": "Petto di Pollo alla Piastra con Insalata", "type": "cena", "ingredients": ["Petto di pollo", "Insalata mista", "Olio EVO"], "contains": []},
    {"title": "Yogurt con Miele", "type": "colazione", "ingredients": ["Yogurt bianco", "Miele"], "contains": ["lattosio"]},
    {"title": "Risotto allo Zafferano", "type": "pranzo", "ingredients": ["Riso", "Zafferano", "Brodo vegetale"], "contains": []},
    {"title": "Frittata di Zucchine", "type": "cena", "ingredients": ["Uova", "Zucchine", "Parmigiano"], "contains": ["uova", "lattosio"]}
]

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    offerte_db = BACKUP_OFFERTE
    ricette_db = BACKUP_RICETTE
    errore_rilevato = False

    # TENTATIVO CONNESSIONE IA
    try:
        print("📡 Test connessione a Google Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Test rapido
        response = model.generate_content("Scrivi la parola OK")
        print(f"✅ Connessione riuscita! Risposta: {response.text.strip()}")
        
        # 1. OFFERTE
        print("🛒 Genero Offerte Reali...")
        prompt_offerte = """
        Genera JSON offerte per: Conad, Coop, Esselunga, Lidl, Eurospin, Todis.
        Usa MARCHE ITALIANE REALI. 6 prodotti per store.
        Format: {"Conad": [{"name": "Pasta Barilla", "price": 0.89}]}
        """
        resp_off = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp_off.text))
        
        # 2. RICETTE
        print("👨‍🍳 Genero Menu Mediterraneo...")
        prompt_ricette = """
        Crea 28 ricette DIETA MEDITERRANEA (Colazione, Pranzo, Merenda, Cena) per 7 giorni.
        Usa ingredienti GENERICI.
        Format Array: [{"title": "Nome", "type": "pranzo", "ingredients": ["Pasta"], "contains": ["glutine"]}]
        """
        resp_ric = model.generate_content(prompt_ricette)
        ricette_db = json.loads(pulisci_json(resp_ric.text))

    except Exception as e:
        print("\n\n❌❌ ERRORE GENERAZIONE AI ❌❌")
        print(traceback.format_exc())
        print("⚠️ UTILIZZO DATI DI BACKUP PER NON BLOCCARE L'APP.")
        errore_rilevato = True

    # SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M") + (" (Backup)" if errore_rilevato else ""),
        "offerte_per_supermercato": offerte_db,
        "ricette": ricette_db
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    
    print(f"💾 File salvato in: {file_out}")
    if errore_rilevato:
        # Forziamo errore uscita per farti vedere il log rosso, ma il file è salvato
        sys.exit(1) 

if __name__ == "__main__":
    genera_tutto()

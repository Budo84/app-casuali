import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import time

# --- CONFIGURAZIONE ---
if "GEMINI_KEY" not in os.environ:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=os.environ["GEMINI_KEY"])

# --- FUNZIONE PULIZIA JSON ---
def pulisci_json(testo):
    testo = testo.replace("```json", "").replace("```", "").strip()
    if testo.startswith("{"):
        start, end = testo.find('{'), testo.rfind('}') + 1
    else:
        start, end = testo.find('['), testo.rfind(']') + 1
    return testo[start:end] if start != -1 and end != -1 else testo

# --- DATI DI BACKUP (DIETA MEDITERRANEA) ---
# Se l'IA fallisce, usiamo questi dati sensati
BACKUP_OFFERTE = {
    "Conad": [{"name": "Pasta Integrale Barilla 500g", "price": 0.95}, {"name": "Passata Mutti", "price": 0.89}, {"name": "Mele Melinda", "price": 1.50}],
    "Coop": [{"name": "Riso Gallo", "price": 1.99}, {"name": "Latte Granarolo", "price": 1.15}, {"name": "Pollo Amadori", "price": 4.50}],
    "Esselunga": [{"name": "Uova Bio", "price": 2.10}, {"name": "Parmigiano Reggiano", "price": 4.50}, {"name": "Zucchine", "price": 1.20}],
    "Lidl": [{"name": "Yogurt Greco", "price": 0.99}, {"name": "Biscotti Cereali", "price": 1.50}, {"name": "Salmone", "price": 3.99}]
}

BACKUP_RICETTE = [
    {"title": "Latte e Biscotti", "type": "colazione", "ingredients": ["Latte Parzialmente Scremato", "Biscotti Integrali"], "contains": ["lattosio", "glutine"]},
    {"title": "Yogurt e Frutta", "type": "colazione", "ingredients": ["Yogurt Bianco", "Frutta Fresca"], "contains": ["lattosio"]},
    {"title": "Fette Biscottate e Marmellata", "type": "colazione", "ingredients": ["Fette biscottate", "Marmellata di ciliegie"], "contains": ["glutine"]},
    
    {"title": "Pasta al Pomodoro e Basilico", "type": "pranzo", "ingredients": ["Pasta", "Passata di pomodoro", "Basilico", "Olio EVO"], "contains": ["glutine"]},
    {"title": "Risotto allo Zafferano", "type": "pranzo", "ingredients": ["Riso", "Zafferano", "Brodo vegetale"], "contains": []},
    {"title": "Pasta e Ceci", "type": "pranzo", "ingredients": ["Pasta", "Ceci", "Rosmarino"], "contains": ["glutine"]},
    
    {"title": "Mela e Noci", "type": "merenda", "ingredients": ["Mela", "Noci"], "contains": ["frutta_guscio"]},
    {"title": "Yogurt", "type": "merenda", "ingredients": ["Yogurt"], "contains": ["lattosio"]},
    
    {"title": "Petto di Pollo e Insalata", "type": "cena", "ingredients": ["Petto di pollo", "Insalata mista", "Olio EVO"], "contains": []},
    {"title": "Frittata di Zucchine", "type": "cena", "ingredients": ["Uova", "Zucchine", "Parmigiano"], "contains": ["uova", "lattosio"]},
    {"title": "Pesce al Forno e Patate", "type": "cena", "ingredients": ["Orata", "Patate", "Rosmarino"], "contains": ["pesce"]}
]

def get_model():
    print("🔍 Cerco un modello disponibile...")
    try:
        # Chiede a Google cosa c'è disponibile
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Se troviamo gemini-pro, usiamo quello che è il più sicuro
                if 'gemini-pro' in m.name:
                    print(f"✅ Trovato modello stabile: {m.name}")
                    return genai.GenerativeModel(m.name)
        
        # Se non trova gemini-pro specifico, prende il primo disponibile
        first_model = list(genai.list_models())[0]
        print(f"⚠️ Uso primo modello disponibile: {first_model.name}")
        return genai.GenerativeModel(first_model.name)
    except:
        print("⚠️ Errore lista modelli. Provo forzatura 'gemini-pro'")
        return genai.GenerativeModel('gemini-pro')

def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    # Inizializza con backup (così se tutto fallisce, abbiamo i dati sani)
    offerte_db = BACKUP_OFFERTE
    lista_ricette = BACKUP_RICETTE
    
    try:
        model = get_model()
        
        # 1. OFFERTE
        print("1. Genero OFFERTE...")
        prompt_offerte = """
        Genera JSON offerte per: Conad, Coop, Esselunga, Lidl, Eurospin, Todis, Pewex, Ipercarni.
        Usa MARCHE REALI ITALIANE (es. Barilla, Mutti). 6 prodotti per store.
        RISPONDI SOLO JSON PURO: {"Conad": [{"name": "Pasta Barilla", "price": 0.89}]}
        """
        resp = model.generate_content(prompt_offerte)
        offerte_db = json.loads(pulisci_json(resp.text))
        print("✅ Offerte scaricate.")

        # 2. RICETTE
        print("2. Genero MENU MEDITERRANEO...")
        prompt_ricette = """
        Crea un menu settimanale DIETA MEDITERRANEA.
        Usa ingredienti GENERICI (es. "Pasta", non "Pasta Barilla").
        
        Struttura JSON OBBLIGATORIA con 4 chiavi:
        1. "colazione": 7 ricette dolci (Latte, Caffè, Biscotti, Yogurt).
        2. "pranzo": 7 ricette carboidrati (Pasta, Riso, Legumi).
        3. "merenda": 7 ricette leggere (Frutta, Yogurt).
        4. "cena": 7 ricette proteine (Carne, Pesce, Uova) + verdure. NO PASTA A CENA.

        RISPONDI SOLO JSON PURO:
        {
          "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"], "contains": ["lattosio"]}],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }
        """
        resp_ric = model.generate_content(prompt_ricette)
        raw_ricette = json.loads(pulisci_json(resp_ric.text))
        
        # Convertiamo nel formato lista per l'app
        lista_ricette = []
        for tipo in ["colazione", "pranzo", "merenda", "cena"]:
            for piatto in raw_ricette.get(tipo, []):
                piatto['type'] = tipo
                lista_ricette.append(piatto)
        print(f"✅ Ricette scaricate: {len(lista_ricette)}")

    except Exception as e:
        print(f"\n❌ ERRORE IA: {e}")
        print("⚠️ USATI DATI DI BACKUP (Dieta Mediterranea)")

    # 3. SALVATAGGIO
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_db,
        "ricette": lista_ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 Salvataggio completato.")

if __name__ == "__main__":
    genera_tutto()

import os
import json
import google.generativeai as genai
from datetime import datetime
import sys

print("--- 🚀 AVVIO PRIORITÀ MENU ---")

# 1. SETUP
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave Mancante. Stop.")
    sys.exit(1)

model = genai.GenerativeModel("gemini-1.5-flash")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FUNZIONE 1: GENERA MENU (PRIORITÀ MASSIMA) ---
def crea_menu_mediterraneo():
    print("🍳 Sto creando il Menu Settimanale Equilibrato...")
    try:
        prompt = """
        Agisci come un nutrizionista esperto.
        Crea un menu settimanale basato sulla DIETA MEDITERRANEA per una famiglia.
        
        REGOLE FONDAMENTALI:
        1. Bilancia Carboidrati, Proteine, Grassi e Fibre.
        2. Varia gli alimenti (es. Pesce 2 volte, Legumi 3 volte, Carne bianca, Uova).
        3. Usa descrizioni semplici (es. "Pasta al pomodoro e basilico", "Pollo al limone").
        4. Struttura: Colazione, Pranzo, Merenda, Cena x 7 giorni.
        
        RISPONDI SOLO CON QUESTO JSON:
        {
          "colazione": [ {"title": "Nome Piatto", "ingredients": ["ingrediente1", "ingrediente2"], "contains": []} ],
          "pranzo": [...], 
          "merenda": [...], 
          "cena": [...]
        }
        """
        response = model.generate_content(prompt)
        menu_data = json.loads(pulisci_json(response.text))
        
        # Aggiungiamo il tag "type" per l'app
        lista_piatti = []
        for pasto in ["colazione", "pranzo", "merenda", "cena"]:
            items = menu_data.get(pasto, [])
            for item in items:
                item['type'] = pasto
                lista_piatti.append(item)
        
        print(f"✅ Menu generato con successo: {len(lista_piatti)} piatti.")
        return lista_piatti

    except Exception as e:
        print(f"❌ Errore generazione menu: {e}")
        # Fallback di emergenza per non lasciare l'app vuota
        return [
            {"title": "Latte e Cereali", "type": "colazione", "ingredients": ["Latte", "Cereali"], "contains": []},
            {"title": "Pasta al Sugo", "type": "pranzo", "ingredients": ["Pasta", "Pomodoro"], "contains": []},
            {"title": "Frutto", "type": "merenda", "ingredients": ["Mela"], "contains": []},
            {"title": "Frittata e Verdure", "type": "cena", "ingredients": ["Uova", "Zucchine"], "contains": []}
        ]

# --- FUNZIONE 2: ANALISI VOLANTINI (OPZIONALE PER ORA) ---
def prova_analisi_volantini():
    # Per ora restituiamo vuoto per non bloccare il menu.
    # Quando il menu funziona, riattiveremo questa parte.
    print("ℹ️ Analisi volantini saltata temporaneamente per testare il menu.")
    return {}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. PRIMA FACCIAMO IL MENU (Così siamo sicuri che esista)
    ricette = crea_menu_mediterraneo()
    
    # 2. Poi (facoltativo) i volantini
    offerte = prova_analisi_volantini()

    # 3. Salvataggio
    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print(f"💾 File JSON salvato correttamente in: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

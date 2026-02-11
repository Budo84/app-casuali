import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import random

# --- 1. CONFIGURAZIONE ---
if "GEMINI_KEY" not in os.environ:
    print("❌ ERRORE: Chiave GEMINI_KEY mancante.")
    sys.exit(1)

genai.configure(api_key=os.environ["GEMINI_KEY"])

# --- 2. LISTA SUPERMERCATI COMPLETA ---
SUPERMERCATI = [
    "Conad", "Coop", "Esselunga", "Lidl", "Eurospin", 
    "Pewex", "MA Supermercati", "Ipercarni", "Todis"
]

# --- 3. DATI DI BACKUP (Se l'IA fallisce, usa questi) ---
# Nota: Ho aggiunto manualmente Pewex, Todis, ecc. così li vedi SEMPRE.
BACKUP_OFFERTE = {
    "Conad": [{"name": "Pasta Barilla", "price": 0.79}, {"name": "Passata Mutti", "price": 0.89}],
    "Coop": [{"name": "Riso Gallo", "price": 1.99}, {"name": "Latte Granarolo", "price": 1.15}],
    "Esselunga": [{"name": "Uova Bio", "price": 2.10}, {"name": "Parmigiano", "price": 4.50}],
    "Lidl": [{"name": "Yogurt Greco", "price": 0.99}, {"name": "Pollo", "price": 3.50}],
    "Eurospin": [{"name": "Biscotti", "price": 1.20}, {"name": "Olio EVO", "price": 5.50}],
    "Pewex": [{"name": "Bistecca di Manzo", "price": 12.90}, {"name": "Pane Casereccio", "price": 1.90}, {"name": "Salsicce", "price": 6.90}],
    "MA Supermercati": [{"name": "Mozzarella", "price": 0.99}, {"name": "Prosciutto Cotto", "price": 1.50}],
    "Ipercarni": [{"name": "Macinato Scelto", "price": 7.90}, {"name": "Petto di Pollo", "price": 6.50}],
    "Todis": [{"name": "Latte UHT", "price": 0.79}, {"name": "Pasta Fresca", "price": 1.10}]
}

BACKUP_RICETTE = [
    {"title": "Latte e Biscotti", "type": "colazione", "ingredients": ["Latte", "Biscotti"], "contains": ["lattosio", "glutine"]},
    {"title": "Yogurt e Miele", "type": "colazione", "ingredients": ["Yogurt", "Miele"], "contains": ["lattosio"]},
    {"title": "Pasta al Pomodoro", "type": "pranzo", "ingredients": ["Pasta", "Passata di pomodoro"], "contains": ["glutine"]},
    {"title": "Risotto allo Zafferano", "type": "pranzo", "ingredients": ["Riso", "Zafferano", "Burro"], "contains": ["lattosio"]},
    {"title": "Mela", "type": "merenda", "ingredients": ["Mela"], "contains": []},
    {"title": "Petto di Pollo e Insalata", "type": "cena", "ingredients": ["Petto di pollo", "Insalata"], "contains": []},
    {"title": "Frittata di Zucchine", "type": "cena", "ingredients": ["Uova", "Zucchine"], "contains": ["uova"]}
]

# --- 4. RICERCA MODELLO ---
def get_model():
    print("🔍 Cerco modello...")
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Preferisci Flash > Pro > Altro
        best = next((m for m in models if "flash" in m), next((m for m in models if "pro" in m), models[0]))
        print(f"✅ Modello trovato: {best}")
        return genai.GenerativeModel(best)
    except:
        return genai.GenerativeModel('gemini-1.5-flash') # Tentativo disperato

# --- 5. GENERAZIONE ---
def genera_tutto():
    cartella = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(cartella, "dati_settimanali.json")
    
    # Variabili finali (iniziano col backup)
    offerte_finali = BACKUP_OFFERTE
    ricette_finali = BACKUP_RICETTE
    
    try:
        model = get_model()
        
        # --- OFFERTE ---
        print("1. Genero Offerte IA...")
        prompt_offerte = f"""
        Genera JSON offerte per: {', '.join(SUPERMERCATI)}.
        Usa MARCHE REALI (es. Barilla, Mutti).
        Format: {{ "Pewex": [{{"name": "Pasta Barilla", "price": 0.89}}] }}
        """
        resp_off = model.generate_content(prompt_offerte)
        clean_off = resp_off.text.replace("```json", "").replace("```", "").strip()
        start = clean_off.find('{')
        end = clean_off.rfind('}') + 1
        offerte_finali = json.loads(clean_off[start:end])
        print("✅ Offerte IA Riuscite.")

        # --- RICETTE ---
        print("2. Genero Menu IA...")
        # Aggiungiamo un numero casuale al prompt per variare il menu ogni volta
        seed = random.randint(1, 1000)
        prompt_ricette = f"""
        Crea un menu settimanale DIETA MEDITERRANEA (Seed variazione: {seed}).
        Usa ingredienti GENERICI (es. Pasta, non Pasta Barilla).
        
        Devi restituire un JSON con 4 liste: "colazione", "pranzo", "merenda", "cena".
        Totale 7 ricette per tipo.
        
        Format:
        {{
          "colazione": [ {{"title": "Caffè", "ingredients": ["Caffè"], "contains": []}} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }}
        """
        resp_ric = model.generate_content(prompt_ricette)
        clean_ric = resp_ric.text.replace("```json", "").replace("```", "").strip()
        start = clean_ric.find('{')
        end = clean_ric.rfind('}') + 1
        ricette_raw = json.loads(clean_ric[start:end])
        
        # Converti per l'app
        temp_list = []
        for k in ["colazione", "pranzo", "merenda", "cena"]:
            for p in ricette_raw.get(k, []):
                p['type'] = k
                temp_list.append(p)
        
        if len(temp_list) > 10: # Controllo validità
            ricette_finali = temp_list
            print("✅ Menu IA Riuscito.")
            
    except Exception as e:
        print(f"❌ Errore IA: {e}")
        print("⚠️ Uso dati di backup (che ora includono Pewex, Todis, ecc).")

    # --- SALVATAGGIO ---
    # Uniamo i backup se mancano chiavi (es. se l'IA scorda Pewex, lo aggiungiamo dal backup)
    for store in SUPERMERCATI:
        if store not in offerte_finali:
            offerte_finali[store] = BACKUP_OFFERTE.get(store, [])

    database = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte_finali,
        "ricette": ricette_finali
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("💾 File salvato.")

if __name__ == "__main__":
    genera_tutto()

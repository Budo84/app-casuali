import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- 🚀 AVVIO ROBOT: RICETTARIO GLOBALE ---")

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

# --- FASE 1: ANALISI VOLANTINI ---
def analizza_volantini():
    offerte_db = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    volantini_dir = os.path.join(base_dir, "volantini")
    
    if not os.path.exists(volantini_dir):
        try: os.makedirs(volantini_dir)
        except: pass

    files = glob.glob(os.path.join(volantini_dir, "*.pdf"))
    
    if not files:
        print("ℹ️ Nessun volantino trovato.")
        return {}

    print(f"🔎 Analisi {len(files)} volantini...")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].title()
            print(f"📄 Leggo: {nome_store}")
            
            pdf = genai.upload_file(file_path, display_name=nome_store)
            attempt = 0
            while pdf.state.name == "PROCESSING" and attempt < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempt += 1
            
            if pdf.state.name == "FAILED":
                print("   ❌ File illeggibile.")
                continue

            prompt = f"""
            Estrai dal volantino di "{nome_store}" i prodotti alimentari e i prezzi.
            JSON: {{ "{nome_store}": [ {{"name": "Prodotto", "price": 1.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            chiave = nome_store if nome_store in data else list(data.keys())[0]
            if chiave in data:
                offerte_db[nome_store] = data[chiave]
                print(f"   ✅ Estratti {len(data[chiave])} prodotti.")
            
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ⚠️ Errore su {nome_store}: {e}")

    return offerte_db

# --- FASE 2: GENERAZIONE RICETTARIO ---
def crea_ricettario(offerte):
    print("🍳 Generazione Database Ricette (Mediterraneo, Veg, Mondo)...")
    
    ingred_extra = ""
    if offerte:
        lista = []
        for s in offerte:
            for p in offerte[s]: lista.append(p['name'])
        ingred_extra = f"Cerca di includere anche questi ingredienti in offerta: {', '.join(lista[:25])}."

    try:
        # CHIEDIAMO UN DATABASE, NON UN MENU SETTIMANALE
        prompt = f"""
        Agisci come uno Chef esperto. Crea un DATABASE DI RICETTE per un'app di pianificazione pasti.
        
        Devi generare 3 CATEGORIE DI CUCINA:
        1. "mediterranea": Dieta equilibrata classica (pesce, carne bianca, pasta, legumi).
        2. "vegetariana": Esclusivamente piatti senza carne/pesce.
        3. "mondo": Piatti internazionali famosi (es. Sushi, Curry, Tacos, Couscous).
        
        Per OGNI categoria, genera:
        - 5 Colazioni
        - 10 Pranzi
        - 10 Cene
        - 5 Merende
        
        {ingred_extra}
        
        RISPONDI SOLO JSON in questo formato:
        {{
            "mediterranea": {{
                "colazione": [ {{"title": "...", "ingredients": ["..."]}} ],
                "pranzo": [...], "cena": [...], "merenda": [...]
            }},
            "vegetariana": {{ ...stessa struttura... }},
            "mondo": {{ ...stessa struttura... }}
        }}
        """
        response = model.generate_content(prompt)
        dataset = json.loads(pulisci_json(response.text))
        
        # Validazione base
        count = 0
        for cat in dataset:
            for pasto in dataset[cat]:
                count += len(dataset[cat][pasto])
        
        print(f"✅ Ricettario Generato: {count} ricette totali pronte all'uso.")
        return dataset

    except Exception as e:
        print(f"❌ Errore AI ({e}). Uso DB backup.")
        return get_backup_db()

def get_backup_db():
    # Un piccolo DB locale di sicurezza
    return {
        "mediterranea": {
            "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"]}],
            "pranzo": [{"title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}],
            "cena": [{"title": "Pollo al Limone", "ingredients": ["Pollo", "Limone"]}],
            "merenda": [{"title": "Mela", "ingredients": ["Mela"]}]
        },
        "vegetariana": {
            "colazione": [{"title": "Yogurt e Frutta", "ingredients": ["Yogurt", "Frutta"]}],
            "pranzo": [{"title": "Pasta al Pesto", "ingredients": ["Pasta", "Basilico"]}],
            "cena": [{"title": "Frittata di Verdure", "ingredients": ["Uova", "Zucchine"]}],
            "merenda": [{"title": "Noci", "ingredients": ["Noci"]}]
        },
        "mondo": {
            "colazione": [{"title": "Pancakes", "ingredients": ["Farina", "Latte", "Uova"]}],
            "pranzo": [{"title": "Riso Cantonese", "ingredients": ["Riso", "Prosciutto", "Uova"]}],
            "cena": [{"title": "Tacos", "ingredients": ["Tortilla", "Fagioli", "Carne"]}],
            "merenda": [{"title": "Muffin", "ingredients": ["Farina", "Cioccolato"]}]
        }
    }

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    offerte = analizza_volantini()
    ricettario = crea_ricettario(offerte)

    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": ricettario # NOTA: La chiave è cambiata da 'ricette' a 'database_ricette'
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
    print(f"💾 Dati salvati: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

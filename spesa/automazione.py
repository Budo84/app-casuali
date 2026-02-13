import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- 🚀 AVVIO ROBOT: MENU BLINDATO ---")

# 1. SETUP
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ Chiave Mancante. Stop.")
    sys.exit(1)

model = genai.GenerativeModel("gemini-1.5-flash")

# --- PARACADUTE: MENU DI RISERVA (Se l'IA fallisce) ---
MENU_BACKUP = [
    {"type": "colazione", "title": "Latte e Fette Biscottate", "ingredients": ["Latte", "Fette biscottate", "Marmellata"], "contains": []},
    {"type": "colazione", "title": "Yogurt e Cereali", "ingredients": ["Yogurt", "Cereali integrali", "Frutta"], "contains": []},
    {"type": "colazione", "title": "Caffè e Biscotti", "ingredients": ["Caffè", "Biscotti secchi"], "contains": []},
    {"type": "colazione", "title": "Tè e Pane Tostato", "ingredients": ["Tè", "Pane", "Miele"], "contains": []},
    {"type": "colazione", "title": "Latte Macchiato e Frutta", "ingredients": ["Latte", "Caffè", "Mela"], "contains": []},
    {"type": "colazione", "title": "Spremuta e Toast", "ingredients": ["Arance", "Pane", "Prosciutto"], "contains": []},
    {"type": "colazione", "title": "Cappuccino e Cornetto", "ingredients": ["Latte", "Caffè", "Cornetto"], "contains": []},
    
    {"type": "pranzo", "title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Passata di pomodoro", "Parmigiano"], "contains": []},
    {"type": "pranzo", "title": "Riso e Piselli", "ingredients": ["Riso", "Piselli", "Cipolla"], "contains": []},
    {"type": "pranzo", "title": "Pasta e Lenticchie", "ingredients": ["Pasta", "Lenticchie", "Carote"], "contains": []},
    {"type": "pranzo", "title": "Insalata di Riso", "ingredients": ["Riso", "Tonno", "Olive", "Pomodorini"], "contains": []},
    {"type": "pranzo", "title": "Farro con Verdure", "ingredients": ["Farro", "Zucchine", "Melanzane"], "contains": []},
    {"type": "pranzo", "title": "Gnocchi al Pesto", "ingredients": ["Gnocchi", "Pesto alla genovese"], "contains": []},
    {"type": "pranzo", "title": "Pasta Tonno e Olive", "ingredients": ["Pasta", "Tonno", "Olive nere"], "contains": []},

    {"type": "merenda", "title": "Mela", "ingredients": ["Mela"], "contains": []},
    {"type": "merenda", "title": "Yogurt", "ingredients": ["Yogurt bianco"], "contains": []},
    {"type": "merenda", "title": "Banana", "ingredients": ["Banana"], "contains": []},
    {"type": "merenda", "title": "Tè e Biscotto", "ingredients": ["Tè", "Biscotto"], "contains": []},
    {"type": "merenda", "title": "Frutta Secca", "ingredients": ["Noci", "Mandorle"], "contains": []},
    {"type": "merenda", "title": "Pane e Olio", "ingredients": ["Pane", "Olio EVO"], "contains": []},
    {"type": "merenda", "title": "Cioccolato Fondente", "ingredients": ["Cioccolato"], "contains": []},

    {"type": "cena", "title": "Petto di Pollo e Insalata", "ingredients": ["Petto di pollo", "Insalata mista"], "contains": []},
    {"type": "cena", "title": "Frittata di Zucchine", "ingredients": ["Uova", "Zucchine", "Parmigiano"], "contains": []},
    {"type": "cena", "title": "Pesce al Forno", "ingredients": ["Merluzzo", "Patate", "Pomodorini"], "contains": []},
    {"type": "cena", "title": "Mozzarella e Pomodori", "ingredients": ["Mozzarella", "Pomodori", "Basilico"], "contains": []},
    {"type": "cena", "title": "Burger Vegetale", "ingredients": ["Burger soia", "Spinaci"], "contains": []},
    {"type": "cena", "title": "Scaloppine al Limone", "ingredients": ["Arista", "Farina", "Limone"], "contains": []},
    {"type": "cena", "title": "Uova Sode e Fagiolini", "ingredients": ["Uova", "Fagiolini"], "contains": []}
]

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
            
            # Supporto per chiavi dinamiche
            chiave = nome_store if nome_store in data else list(data.keys())[0]
            
            if chiave in data:
                offerte_db[nome_store] = data[chiave]
                print(f"   ✅ Estratti {len(data[chiave])} prodotti.")
            
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ⚠️ Errore su {nome_store}: {e}")

    return offerte_db

# --- FASE 2: MENU GENERATIVO ---
def crea_menu_ai(offerte):
    print("🍳 Generazione Menu AI...")
    
    ingred_extra = ""
    if offerte:
        lista = []
        for s in offerte:
            for p in offerte[s]: lista.append(p['name'])
        ingred_extra = f"Usa anche: {', '.join(lista[:20])}."

    try:
        prompt = f"""
        Crea menu settimanale DIETA MEDITERRANEA.
        7 Colazioni, 7 Pranzi, 7 Merende, 7 Cene.
        PIATTI DIVERSI OGNI GIORNO.
        {ingred_extra}
        
        JSON:
        {{
          "colazione": [ {{"title": "...", "ingredients": ["..."], "contains": []}} ],
          "pranzo": [...], "merenda": [...], "cena": [...]
        }}
        """
        response = model.generate_content(prompt)
        raw_data = json.loads(pulisci_json(response.text))
        
        lista_finale = []
        for tipo in ["colazione", "pranzo", "merenda", "cena"]:
            piatti = raw_data.get(tipo, [])
            for p in piatti:
                p['type'] = tipo
                lista_finale.append(p)
        
        # CONTROLLO QUALITÀ
        if len(lista_finale) < 20:
            raise Exception("Menu generato troppo corto")
            
        print(f"✅ Menu AI Generato: {len(lista_finale)} ricette.")
        return lista_finale

    except Exception as e:
        print(f"❌ Errore AI ({e}). USO IL MENU DI BACKUP.")
        return MENU_BACKUP

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. Analisi (Non bloccante)
    offerte = analizza_volantini()
    
    # 2. Menu (Garantito)
    ricette = crea_menu_ai(offerte)

    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
    print(f"💾 Dati salvati: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

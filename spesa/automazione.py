import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time

print("--- 🚀 AVVIO ROBOT: MENU EQUILIBRATO & VOLANTINI ---")

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

# --- FASE 1: ANALISI VOLANTINI (Robustissima) ---
def analizza_volantini():
    offerte_db = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    volantini_dir = os.path.join(base_dir, "volantini")
    
    # Crea cartella se manca
    if not os.path.exists(volantini_dir):
        try: os.makedirs(volantini_dir)
        except: pass

    files = glob.glob(os.path.join(volantini_dir, "*.pdf"))
    
    if not files:
        print("ℹ️ Nessun volantino trovato. Procedo solo con il menu.")
        return {}

    print(f"🔎 Trovati {len(files)} volantini. Inizio analisi...")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].title()
            
            print(f"📄 Leggo: {nome_store}")
            
            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            while pdf.state.name == "PROCESSING":
                time.sleep(1)
                pdf = genai.get_file(pdf.name)
            
            if pdf.state.name == "FAILED":
                print("   ❌ File illeggibile.")
                continue

            # Estrazione
            prompt = f"""
            Estrai dal volantino di "{nome_store}" i prodotti alimentari e i prezzi.
            JSON: {{ "{nome_store}": [ {{"name": "Prodotto", "price": 1.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            if nome_store in data:
                offerte_db[nome_store] = data[nome_store]
                print(f"   ✅ Estratti {len(data[nome_store])} prodotti.")
            
            genai.delete_file(pdf.name)

        except Exception as e:
            print(f"   ⚠️ Errore su {nome_store}: {e}")

    return offerte_db

# --- FASE 2: MENU MEDITERRANEO (Varietà Garantita) ---
def crea_menu_vario(offerte):
    print("🍳 Generazione Menu Settimanale Vario...")
    
    # Creiamo un contesto leggero sugli ingredienti in offerta, ma senza forzare troppo
    ingred_extra = ""
    if offerte:
        lista = []
        for s in offerte:
            for p in offerte[s]: lista.append(p['name'])
        ingred_extra = f"Se possibile, includi questi ingredienti in offerta: {', '.join(lista[:30])}."

    try:
        prompt = f"""
        Agisci come un nutrizionista. Crea un menu settimanale DIETA MEDITERRANEA per 7 giorni.
        
        REGOLE FERREE PER LA VARIETÀ:
        1. Devi generare ESATTAMENTE 7 Colazioni, 7 Pranzi, 7 Merende, 7 Cene.
        2. I piatti DEVONO ESSERE DIVERSI ogni giorno (es. Lunedì Pesce, Martedì Legumi, Mercoledì Uova...).
        3. Bilancia carboidrati e proteine. Non mettere pasta sia a pranzo che a cena.
        {ingred_extra}
        
        RISPONDI SOLO JSON:
        {{
          "colazione": [ 
             {{"title": "Lun: Latte e Caffè", "ingredients": ["Latte", "Caffè"], "contains": []}},
             {{"title": "Mar: Yogurt e Frutta", "ingredients": ["Yogurt", "Frutta"], "contains": []}},
             ... (altri 5 diversi) ...
          ],
          "pranzo": [ ... 7 ricette diverse ... ],
          "merenda": [ ... 7 ricette diverse ... ],
          "cena": [ ... 7 ricette diverse ... ]
        }}
        """
        response = model.generate_content(prompt)
        raw_data = json.loads(pulisci_json(response.text))
        
        # Appiattiamo il JSON in una lista unica per l'app
        lista_finale = []
        for tipo in ["colazione", "pranzo", "merenda", "cena"]:
            piatti = raw_data.get(tipo, [])
            # Se ne ha generati meno di 7, duplichiamo gli ultimi per arrivare a 7
            while len(piatti) < 7:
                piatti.append(piatti[-1] if piatti else {"title": "Pasto Vario", "ingredients": ["Misto"], "contains": []})
            
            for p in piatti:
                p['type'] = tipo
                lista_finale.append(p)
        
        print(f"✅ Menu Generato: {len(lista_finale)} ricette totali.")
        return lista_finale

    except Exception as e:
        print(f"❌ Errore Menu: {e}")
        return []

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. Analisi Volantini (Se fallisce torna vuoto, non blocca)
    offerte = analizza_volantini()
    
    # 2. Generazione Menu (Usa le offerte se ci sono)
    ricette = crea_menu_vario(offerte)
    
    # Se il menu è vuoto (errore AI), usiamo un backup statico per non rompere l'app
    if not ricette:
        ricette = [
            {"title": "Backup Pasta", "type": "pranzo", "ingredients": ["Pasta"], "contains": []}
        ]

    db = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "ricette": ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
    print(f"💾 Salvato in: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

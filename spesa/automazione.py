import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: CHEF AUTO-CONFIGURANTE ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE CRITICO: Chiave API Mancante.")
    sys.exit(1)

# 2. SELEZIONE MODELLO INTELLIGENTE
def get_best_model():
    print("📡 Interrogo Google per i modelli disponibili...")
    try:
        available_models = []
        # Chiede a Google la lista dei modelli
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Pulisce il nome (toglie 'models/')
                name = m.name.replace('models/', '')
                available_models.append(name)
        
        print(f"   Modelli trovati: {available_models}")

        # CERCA IL MIGLIORE IN ORDINE DI PRIORITÀ
        # 1. Prova Flash 1.5 (Veloce ed economico)
        for m in available_models:
            if 'flash' in m and '1.5' in m:
                print(f"✅ Scelto modello RAPIDO: {m}")
                return genai.GenerativeModel(m)
        
        # 2. Prova Pro 1.5 (Potente)
        for m in available_models:
            if 'pro' in m and '1.5' in m:
                print(f"✅ Scelto modello POTENTE: {m}")
                return genai.GenerativeModel(m)

        # 3. Fallback su Gemini Pro Standard (Compatibilità massima)
        if 'gemini-pro' in available_models:
            print("⚠️ Uso modello STANDARD (Gemini Pro)")
            return genai.GenerativeModel('gemini-pro')
            
        # 4. Se proprio non trova nulla, prova il primo della lista
        if available_models:
            print(f"⚠️ Uso il primo modello disponibile: {available_models[0]}")
            return genai.GenerativeModel(available_models[0])

    except Exception as e:
        print(f"❌ Errore nella ricerca modelli: {e}")
    
    # ULTIMO TENTATIVO ALLA CIECA
    print("⚠️ Fallback Estremo: provo 'gemini-pro' alla cieca.")
    return genai.GenerativeModel("gemini-pro")

# Inizializza il modello scelto
model = get_best_model()

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI ---
def analizza_volantini():
    offerte_db = {}
    
    # Percorsi sicuri
    path_script = os.path.dirname(os.path.abspath(__file__))
    dir_1 = os.path.join(path_script, "volantini")
    dir_2 = os.path.join(os.getcwd(), "spesa", "volantini")
    target_dir = dir_1 if os.path.exists(dir_1) else (dir_2 if os.path.exists(dir_2) else "")

    if not target_dir:
        print("ℹ️ Cartella volantini non trovata. Salto.")
        return {}

    files = glob.glob(os.path.join(target_dir, "*.[pP][dD][fF]"))
    print(f"🔎 Analisi {len(files)} file in: {target_dir}")

    for file_path in files:
        try:
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].replace("_", " ").title()
            print(f"📄 Elaborazione: {nome_store}")
            
            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            
            # Attesa
            attempts = 0
            while pdf.state.name == "PROCESSING" and attempts < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempts += 1
            
            if pdf.state.name == "FAILED":
                print(f"   ❌ File non valido.")
                continue

            # Prompt
            prompt = f"""
            Analizza "{nome_store}". Estrai TUTTI i cibi e prezzi.
            JSON: {{ "{nome_store}": [ {{"name": "...", "price": 0.00}} ] }}
            """
            
            try:
                res = model.generate_content([pdf, prompt])
                data = json.loads(pulisci_json(res.text))
                
                # Gestione chiavi dinamiche
                chiave = nome_store if nome_store in data else list(data.keys())[0]
                if chiave in data:
                    offerte_db[nome_store] = data[chiave]
                    print(f"   ✅ OK: {len(data[chiave])} prodotti.")
            except Exception as e:
                print(f"   ⚠️ Errore AI su file: {e}")

            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ❌ Errore critico file: {e}")

    return offerte_db

# --- FASE 2: RICETTARIO ---
def crea_database_ricette(offerte):
    print("🍳 Creazione Ricettario...")
    
    context = ""
    if offerte:
        items = []
        for s in offerte:
            for p in offerte[s]: items.append(p['name'])
        if items:
            sample = random.sample(items, min(len(items), 15))
            context = f"Usa ingredienti: {', '.join(sample)}."

    try:
        prompt = f"""
        Crea DATABASE RICETTE (Chef).
        {context}
        
        3 CATEGORIE:
        1. "mediterranea" (Equilibrata)
        2. "vegetariana" (No carne)
        3. "mondo" (Internazionale)
        
        Per OGNI categoria: 5 Colazioni, 7 Pranzi, 7 Cene, 5 Merende.
        
        JSON:
        {{
            "mediterranea": {{ "colazione": [...], "pranzo": [...], "cena": [...], "merenda": [...] }},
            "vegetariana": {{ ... }},
            "mondo": {{ ... }}
        }}
        """
        
        res = model.generate_content(prompt)
        db = json.loads(pulisci_json(res.text))
        print("✅ Ricettario OK.")
        return db

    except Exception as e:
        print(f"❌ Errore Generazione Ricette: {e}. Uso Backup.")
        return DATABASE_BACKUP

DATABASE_BACKUP = {
    "mediterranea": {
        "colazione": [{"title": "Latte e Biscotti", "ingredients": ["Latte", "Biscotti"]}],
        "pranzo": [{"title": "Pasta al Pomodoro", "ingredients": ["Pasta", "Pomodoro"]}],
        "cena": [{"title": "Pollo al Limone", "ingredients": ["Pollo", "Limone"]}],
        "merenda": [{"title": "Mela", "ingredients": ["Mela"]}]
    },
    "vegetariana": {
        "colazione": [{"title": "Yogurt", "ingredients": ["Yogurt"]}],
        "pranzo": [{"title": "Pasta Pesto", "ingredients": ["Pasta", "Basilico"]}],
        "cena": [{"title": "Frittata", "ingredients": ["Uova"]}],
        "merenda": [{"title": "Noci", "ingredients": ["Noci"]}]
    },
    "mondo": {
        "colazione": [{"title": "Pancakes", "ingredients": ["Farina", "Uova"]}],
        "pranzo": [{"title": "Riso Cantonese", "ingredients": ["Riso", "Prosciutto"]}],
        "cena": [{"title": "Tacos", "ingredients": ["Carne", "Mais"]}],
        "merenda": [{"title": "Muffin", "ingredients": ["Cioccolato"]}]
    }
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    offerte = analizza_volantini()
    db_ricette = crea_database_ricette(offerte)

    out = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": db_ricette
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
    print(f"💾 Salvato: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

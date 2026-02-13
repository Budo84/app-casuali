import os
import json
import google.generativeai as genai
from datetime import datetime
import sys
import glob
import time
import random

print("--- 🚀 AVVIO ROBOT: CHEF NUTRIZIONISTA 2.0 ---")

# 1. SETUP CHIAVE
if "GEMINI_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_KEY"])
else:
    print("❌ ERRORE: Chiave Mancante. Lo script si ferma.")
    # Non usiamo exit(1) per permettere al workflow di tentare comunque il commit se serve
    # Ma senza chiave non possiamo fare nulla di intelligente.
    sys.exit(1)

model = genai.GenerativeModel("gemini-1.5-flash")

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

# --- FASE 1: ANALISI VOLANTINI (UNIVERSALE) ---
def analizza_volantini():
    offerte_db = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    volantini_dir = os.path.join(base_dir, "volantini")
    
    # Crea cartella se non esiste (sicurezza)
    if not os.path.exists(volantini_dir):
        try: os.makedirs(volantini_dir)
        except: pass

    # Cerca PDF
    files = glob.glob(os.path.join(volantini_dir, "*.pdf"))
    
    if not files:
        print("ℹ️ Nessun volantino trovato. Procedo senza offerte.")
        return {}

    print(f"🔎 Analisi di {len(files)} volantini...")

    for file_path in files:
        try:
            # Ricava nome store dal file (es. "iper_carni.pdf" -> "Iper Carni")
            nome_file = os.path.basename(file_path)
            nome_store = os.path.splitext(nome_file)[0].replace("_", " ").title()
            
            print(f"📄 Leggo: {nome_store}")
            
            # Upload
            pdf = genai.upload_file(file_path, display_name=nome_store)
            attempt = 0
            while pdf.state.name == "PROCESSING" and attempt < 10:
                time.sleep(2)
                pdf = genai.get_file(pdf.name)
                attempt += 1
            
            if pdf.state.name == "FAILED":
                print(f"   ❌ File {nome_file} illeggibile.")
                continue

            # Prompt Estrazione
            prompt = f"""
            Analizza il volantino "{nome_store}". 
            Estrai TUTTI i prodotti alimentari (cibo, bevande) e i prezzi.
            Ignora tutto il resto.
            
            OUTPUT JSON: {{ "{nome_store}": [ {{"name": "Nome Prodotto", "price": 0.00}} ] }}
            """
            res = model.generate_content([pdf, prompt])
            data = json.loads(pulisci_json(res.text))
            
            # Recupera la lista prodotti (gestione chiavi dinamiche)
            chiave = nome_store if nome_store in data else list(data.keys())[0]
            
            if chiave in data and isinstance(data[chiave], list):
                offerte_db[nome_store] = data[chiave]
                print(f"   ✅ Estratti {len(data[chiave])} prodotti da {nome_store}.")
            
            try: genai.delete_file(pdf.name)
            except: pass

        except Exception as e:
            print(f"   ⚠️ Errore su {file_path}: {e}")

    return offerte_db

# --- FASE 2: GENERATORE RICETTARIO (CHEF) ---
def crea_database_ricette(offerte):
    print("🍳 Lo Chef sta creando il database ricette...")
    
    # Creiamo contesto ingredienti dai volantini
    ingred_context = ""
    if offerte:
        all_products = []
        for s in offerte:
            for p in offerte[s]: all_products.append(p['name'])
        # Prendiamo 30 prodotti a caso per ispirare lo chef
        sample = random.sample(all_products, min(len(all_products), 30))
        ingred_context = f"INGREDIENTI IN OFFERTA DA USARE SE POSSIBILE: {', '.join(sample)}."

    try:
        prompt = f"""
        Agisci come un Masterchef e Nutrizionista.
        Crea un DATABASE DI RICETTE strutturato per un'app.
        
        {ingred_context}
        
        Devi generare 3 CATEGORIE DI DIETA:
        1. "mediterranea": Equilibrata, pasta, pesce, carne bianca, legumi, verdure.
        2. "vegetariana": Niente carne o pesce. Uova e latticini ok.
        3. "mondo": Ricette internazionali (Sushi, Curry, Tacos, Paella, Chili, ecc).
        
        Per OGNI categoria devi generare:
        - 5 Colazioni
        - 7 Pranzi (Variare ingredienti!)
        - 7 Cene (Leggere e proteiche)
        - 5 Merende
        
        IMPORTANTE: 
        - Usa nomi di piatti reali e appetitosi.
        - Elenca gli ingredienti principali (senza quantità).
        
        STRUTTURA JSON OBBLIGATORIA:
        {{
            "mediterranea": {{
                "colazione": [ {{"title": "...", "ingredients": ["..."]}}, ... ],
                "pranzo": [...], "cena": [...], "merenda": [...]
            }},
            "vegetariana": {{ ...come sopra... }},
            "mondo": {{ ...come sopra... }}
        }}
        """
        
        response = model.generate_content(prompt)
        db_ricette = json.loads(pulisci_json(response.text))
        
        # Validazione minima
        if "mediterranea" not in db_ricette: raise Exception("JSON incompleto")
        
        print("✅ Database Ricette generato con successo!")
        return db_ricette

    except Exception as e:
        print(f"❌ Errore Chef AI ({e}). Uso il Ricettario di Backup.")
        return DATABASE_BACKUP

# --- DATABASE DI BACKUP (PARACADUTE) ---
DATABASE_BACKUP = {
    "mediterranea": {
        "colazione": [
            {"title": "Latte e Fette Biscottate", "ingredients": ["Latte", "Fette biscottate", "Marmellata"]},
            {"title": "Yogurt Greco e Noci", "ingredients": ["Yogurt greco", "Noci", "Miele"]},
            {"title": "Cappuccino e Brioche", "ingredients": ["Latte", "Caffè", "Brioche"]},
            {"title": "Pane Ricotta e Miele", "ingredients": ["Pane integrale", "Ricotta", "Miele"]},
            {"title": "Spremuta e Toast", "ingredients": ["Arance", "Pane", "Prosciutto cotto"]}
        ],
        "pranzo": [
            {"title": "Pasta al Pomodoro e Basilico", "ingredients": ["Pasta", "Pomodoro", "Basilico"]},
            {"title": "Riso con Zucchine e Gamberetti", "ingredients": ["Riso", "Zucchine", "Gamberetti"]},
            {"title": "Pasta e Ceci", "ingredients": ["Pasta", "Ceci", "Rosmarino"]},
            {"title": "Insalata di Riso", "ingredients": ["Riso", "Tonno", "Uova", "Sottaceti"]},
            {"title": "Orecchiette alle Cime di Rapa", "ingredients": ["Orecchiette", "Cime di rapa", "Acciughe"]},
            {"title": "Spaghetti alle Vongole", "ingredients": ["Spaghetti", "Vongole", "Prezzemolo"]},
            {"title": "Farro con Verdure", "ingredients": ["Farro", "Peperoni", "Melanzane"]}
        ],
        "cena": [
            {"title": "Petto di Pollo alla Piastra", "ingredients": ["Pollo", "Insalata", "Limone"]},
            {"title": "Pesce Spada al Forno", "ingredients": ["Pesce spada", "Pomodorini", "Olive"]},
            {"title": "Frittata di Spinaci", "ingredients": ["Uova", "Spinaci", "Parmigiano"]},
            {"title": "Bresaola Rucola e Grana", "ingredients": ["Bresaola", "Rucola", "Grana"]},
            {"title": "Minestrone di Verdure", "ingredients": ["Patate", "Carote", "Zucchine", "Fagioli"]},
            {"title": "Mozzarella e Pomodoro (Caprese)", "ingredients": ["Mozzarella", "Pomodoro", "Origano"]},
            {"title": "Polpette al Sugo", "ingredients": ["Carne macinata", "Uova", "Pomodoro"]}
        ],
        "merenda": [
            {"title": "Mela", "ingredients": ["Mela"]},
            {"title": "Banana", "ingredients": ["Banana"]},
            {"title": "Yogurt", "ingredients": ["Yogurt"]},
            {"title": "Mandorle", "ingredients": ["Mandorle"]},
            {"title": "Pane e Olio", "ingredients": ["Pane", "Olio EVO"]}
        ]
    },
    "vegetariana": {
        "colazione": [
            {"title": "Porridge d'Avena", "ingredients": ["Avena", "Latte di soia", "Banana"]},
            {"title": "Smoothie Verde", "ingredients": ["Spinaci", "Mela", "Kiwi"]},
            {"title": "Yogurt e Frutti di Bosco", "ingredients": ["Yogurt", "Mirtilli", "Lamponi"]},
            {"title": "Pane Burro e Marmellata", "ingredients": ["Pane", "Burro", "Marmellata"]},
            {"title": "Tè e Biscotti Veg", "ingredients": ["Tè", "Biscotti senza uova"]}
        ],
        "pranzo": [
            {"title": "Pasta al Pesto Genovese", "ingredients": ["Pasta", "Basilico", "Pinoli", "Parmigiano"]},
            {"title": "Risotto ai Funghi", "ingredients": ["Riso", "Funghi porcini", "Burro"]},
            {"title": "Pasta alla Norma", "ingredients": ["Pasta", "Melanzane", "Ricotta salata"]},
            {"title": "Couscous alle Verdure", "ingredients": ["Couscous", "Zucchine", "Peperoni", "Ceci"]},
            {"title": "Gnocchi al Pomodoro", "ingredients": ["Gnocchi", "Pomodoro", "Mozzarella"]},
            {"title": "Zuppa di Legumi", "ingredients": ["Lenticchie", "Fagioli", "Farro"]},
            {"title": "Insalata di Quinoa", "ingredients": ["Quinoa", "Avocado", "Mais", "Pomodori"]}
        ],
        "cena": [
            {"title": "Burger di Soia", "ingredients": ["Burger vegetale", "Insalata", "Pomodoro"]},
            {"title": "Parmigiana di Melanzane", "ingredients": ["Melanzane", "Mozzarella", "Pomodoro"]},
            {"title": "Uova al Tegamino con Asparagi", "ingredients": ["Uova", "Asparagi"]},
            {"title": "Hummus e Verdure Crude", "ingredients": ["Ceci", "Tahina", "Carote", "Sedano"]},
            {"title": "Torta Salata Ricotta e Spinaci", "ingredients": ["Pasta sfoglia", "Ricotta", "Spinaci"]},
            {"title": "Vellutata di Zucca", "ingredients": ["Zucca", "Patate", "Porri"]},
            {"title": "Formaggi Misti e Pere", "ingredients": ["Pecorino", "Gorgonzola", "Pere"]}
        ],
        "merenda": [
            {"title": "Cioccolato Fondente", "ingredients": ["Cioccolato"]},
            {"title": "Frutta Secca", "ingredients": ["Noci", "Nocciole"]},
            {"title": "Centrifugato", "ingredients": ["Carota", "Arancia"]},
            {"title": "Barretta ai Cereali", "ingredients": ["Cereali", "Miele"]},
            {"title": "Pera", "ingredients": ["Pera"]}
        ]
    },
    "mondo": {
        "colazione": [
            {"title": "Pancakes allo Sciroppo d'Acero", "ingredients": ["Farina", "Uova", "Latte", "Sciroppo d'acero"]},
            {"title": "Colazione Inglese (Beans & Toast)", "ingredients": ["Fagioli", "Pane tostato", "Uova"]},
            {"title": "Churros", "ingredients": ["Farina", "Zucchero", "Cannella"]},
            {"title": "French Toast", "ingredients": ["Pane", "Uova", "Latte", "Cannella"]},
            {"title": "Miso Soup (Giappone)", "ingredients": ["Brodo dashi", "Miso", "Tofu"]}
        ],
        "pranzo": [
            {"title": "Sushi Misto", "ingredients": ["Riso", "Salmone", "Alga Nori", "Avocado"]},
            {"title": "Pollo al Curry con Riso Basmati", "ingredients": ["Pollo", "Curry", "Latte di cocco", "Riso"]},
            {"title": "Paella Valenciana", "ingredients": ["Riso", "Zafferano", "Frutti di mare", "Pollo"]},
            {"title": "Riso alla Cantonese", "ingredients": ["Riso", "Prosciutto", "Piselli", "Uova"]},
            {"title": "Couscous Marocchino", "ingredients": ["Couscous", "Agnello", "Verdure", "Ceci"]},
            {"title": "Pad Thai", "ingredients": ["Tagliatelle di riso", "Gamberi", "Arachidi", "Germogli di soia"]},
            {"title": "Greek Salad", "ingredients": ["Feta", "Olive nere", "Cetrioli", "Pomodori", "Cipolla"]}
        ],
        "cena": [
            {"title": "Tacos Messicani", "ingredients": ["Tortillas", "Carne macinata", "Fagioli neri", "Mais"]},
            {"title": "Ramen", "ingredients": ["Noodles", "Brodo", "Uova", "Maiale"]},
            {"title": "Chili con Carne", "ingredients": ["Carne macinata", "Fagioli rossi", "Peperoncino", "Pomodoro"]},
            {"title": "Falafel con Hummus", "ingredients": ["Ceci", "Prezzemolo", "Tahina", "Pita"]},
            {"title": "Pollo Tandoori", "ingredients": ["Pollo", "Yogurt", "Spezie tandoori"]},
            {"title": "Goulash Ungherese", "ingredients": ["Manzo", "Paprika", "Patate", "Cipolla"]},
            {"title": "Fish and Chips", "ingredients": ["Merluzzo", "Pastella", "Patate fritte"]}
        ],
        "merenda": [
            {"title": "Muffin ai Mirtilli", "ingredients": ["Farina", "Mirtilli", "Zucchero"]},
            {"title": "Brownies", "ingredients": ["Cioccolato", "Burro", "Noci"]},
            {"title": "Apple Pie (Fetta)", "ingredients": ["Mela", "Pasta brisè"]},
            {"title": "Crepes alla Nutella", "ingredients": ["Uova", "Latte", "Farina", "Nutella"]},
            {"title": "Cookie Americano", "ingredients": ["Cioccolato", "Farina", "Burro"]}
        ]
    }
}

def esegui_tutto():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_out = os.path.join(base_dir, "dati_settimanali.json")
    
    # 1. Analisi Offerte
    offerte = analizza_volantini()
    
    # 2. Generazione Ricettario (Database)
    database_ricette = crea_database_ricette(offerte)

    # 3. Struttura Finale JSON
    output_data = {
        "data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "offerte_per_supermercato": offerte,
        "database_ricette": database_ricette 
        # Nota: Non salviamo più "ricette" (menu fisso), ma il "database_ricette"
        # L'app JS sceglierà cosa mostrare.
    }

    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"💾 Dati salvati in: {file_out}")

if __name__ == "__main__":
    esegui_tutto()

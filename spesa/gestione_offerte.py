import os
import json
import glob
import base64
import requests
import fitz  # Libreria PyMuPDF
import sys

print("--- 🛒 AVVIO ANALISI OFFERTE (METODO DIRETTO REST API) ---")

API_KEY = os.environ.get("GEMINI_KEY")
if not API_KEY:
    print("❌ Chiave mancante.")
    sys.exit(0)

def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1: return text[s:e]
    return text

def analizza():
    base = os.path.dirname(os.path.abspath(__file__))
    paths = [os.path.join(base, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target = next((p for p in paths if os.path.exists(p)), None)

    offerte = {}

    if target:
        files = glob.glob(os.path.join(target, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(files)} PDF.")

        for fp in files:
            try:
                nome = os.path.splitext(os.path.basename(fp))[0].replace("_", " ").title()
                print(f"📄 Elaborazione: {nome}")

                # 1. Converti PDF in immagini (Risolve il problema dei file "Pewex" fotocopiati)
                print("   📖 Scatto foto alle pagine del PDF...")
                doc = fitz.open(fp)
                image_parts = []
                
                # Elaboriamo massimo 20 pagine per non superare i limiti di grandezza
                max_pages = min(len(doc), 20) 
                for i in range(max_pages):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    img_bytes = pix.tobytes("jpeg")
                    b64_img = base64.b64encode(img_bytes).decode("utf-8")
                    image_parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_img
                        }
                    })
                
                doc.close()

                # 2. Invia tutto direttamente al server Google tramite HTTP
                print("   🤖 Inoltro immagini all'Intelligenza Artificiale...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
                
                prompt_text = f"""
                Analizza le immagini di questo volantino di "{nome}". 
                Estrai TUTTI i prodotti alimentari e i relativi prezzi. Ignora detersivi e prodotti per la casa.
                RISPONDI TASSATIVAMENTE SOLO CON QUESTO JSON ESATTO:
                {{
                    "{nome}": [
                        {{"name": "Nome Prodotto", "price": 0.00}}
                    ]
                }}
                """

                payload = {
                    "contents": [{
                        "parts": [{"text": prompt_text}] + image_parts
                    }]
                }

                response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
                
                # 3. Leggi la risposta
                if response.status_code == 200:
                    res_json = response.json()
                    ai_text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    data = json.loads(pulisci_json(ai_text))
                    if data:
                        k = list(data.keys())[0]
                        offerte[nome] = data[k]
                        print(f"   ✅ Successo! Estratti {len(data[k])} prodotti.")
                else:
                    print(f"   ❌ Errore Google API: {response.status_code} - {response.text}")

            except Exception as e:
                print(f"   ⚠️ Errore critico su {nome}: {e}")

    # SALVATAGGIO
    if not offerte:
        offerte = {"Info": [{"name": "Nessuna offerta trovata. Controlla il PDF.", "price": 0.00}]}

    file_out = os.path.join(base, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print("💾 Offerte salvate.")

if __name__ == "__main__":
    analizza()

import os
import json
import glob
import base64
import time
import requests
import fitz  # Libreria PyMuPDF
import sys

print("--- 🛒 AVVIO ANALISI OFFERTE (METODO DIRETTO REST API) ---")

API_KEY = os.environ.get("GEMINI_KEY")
if not API_KEY:
    print("❌ Chiave mancante. Controlla che la secret 'GEMINI_KEY' sia impostata su GitHub (Settings > Secrets and variables > Actions).")
    sys.exit(1)  # prima era sys.exit(0): il job risultava "verde" anche senza chiave

# Lista di modelli da provare in ordine. gemini-1.5-flash è stato ritirato da Google:
# usiamo l'alias "-latest" (si aggiorna da solo nel tempo) e alcuni nomi concreti come riserva.
MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
]

MAX_PAGES = 30          # prima 20: alcuni volantini (es. Conad) hanno più pagine
IMG_SCALE = 1.5
MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 5


def pulisci_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e != -1:
        return text[s:e]
    return text


def estrai_testo_risposta(res_json):
    """Concatena TUTTE le parti di testo della risposta, non solo la prima."""
    try:
        parts = res_json["candidates"][0]["content"]["parts"]
        testo = "".join(p.get("text", "") for p in parts if "text" in p)
        return testo
    except (KeyError, IndexError, TypeError):
        return ""


def chiama_gemini(model_name, prompt_text, image_parts):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt_text}] + image_parts}]}
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,  # più sicuro che mettere la chiave nell'URL
    }

    for tentativo in range(1, MAX_RETRIES_PER_MODEL + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Errore di rete con {model_name} (tentativo {tentativo}): {e}")
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"   ⚠️ Modello '{model_name}' non disponibile (404). Passo al prossimo.")
            return None  # niente retry, il modello proprio non esiste: prova il prossimo
        elif response.status_code == 429:
            print(f"   ⏳ Rate limit (429) su {model_name}, riprovo tra {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)
            continue
        else:
            print(f"   ⚠️ Errore HTTP {response.status_code} con {model_name}: {response.text[:300]}")
            return None

    return None


def analizza():
    base = os.path.dirname(os.path.abspath(__file__))
    paths = [os.path.join(base, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target = next((p for p in paths if os.path.exists(p)), None)

    offerte = {}
    errori = []

    if target:
        files = glob.glob(os.path.join(target, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(files)} PDF.")

        for fp in files:
            nome = os.path.splitext(os.path.basename(fp))[0].replace("_", " ").title()
            try:
                print(f"📄 Elaborazione: {nome}")

                print("   📖 Scatto foto alle pagine del PDF...")
                doc = fitz.open(fp)
                image_parts = []

                max_pages = min(len(doc), MAX_PAGES)
                if len(doc) > MAX_PAGES:
                    print(f"   ℹ️ Il PDF ha {len(doc)} pagine, ne analizzo solo {MAX_PAGES}.")
                for i in range(max_pages):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=fitz.Matrix(IMG_SCALE, IMG_SCALE))
                    img_bytes = pix.tobytes("jpeg")
                    b64_img = base64.b64encode(img_bytes).decode("utf-8")
                    image_parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_img,
                        }
                    })
                doc.close()

                prompt_text = f"""
                Analizza le immagini di questo volantino di "{nome}".
                Estrai TUTTI i prodotti alimentari e i relativi prezzi. Ignora detersivi e prodotti per la casa.
                RISPONDI TASSATIVAMENTE SOLO CON QUESTO JSON ESATTO, SENZA TESTO PRIMA O DOPO:
                {{
                    "{nome}": [
                        {{"name": "Nome Prodotto", "price": 0.00}}
                    ]
                }}
                """

                print("   🤖 Inoltro immagini all'Intelligenza Artificiale...")
                risultato = None
                modello_usato = None
                for model in MODELS:
                    res_json = chiama_gemini(model, prompt_text, image_parts)
                    if res_json:
                        risultato = res_json
                        modello_usato = model
                        break

                if not risultato:
                    msg = f"Tutti i modelli hanno fallito per '{nome}'."
                    print(f"   ❌ {msg}")
                    errori.append(msg)
                    continue

                ai_text = estrai_testo_risposta(risultato)
                if not ai_text:
                    msg = f"Risposta vuota dall'AI per '{nome}' (modello: {modello_usato})."
                    print(f"   ❌ {msg}")
                    errori.append(msg)
                    continue

                try:
                    data = json.loads(pulisci_json(ai_text))
                except json.JSONDecodeError as e:
                    msg = f"JSON non valido per '{nome}': {e}"
                    print(f"   ❌ {msg}")
                    print(f"   --- Risposta grezza (primi 500 char) ---\n{ai_text[:500]}")
                    errori.append(msg)
                    continue

                if data:
                    k = list(data.keys())[0]
                    offerte[nome] = data[k]
                    print(f"   ✅ Successo con '{modello_usato}'! Estratti {len(data[k])} prodotti.")

            except Exception as e:
                msg = f"Errore critico su {nome}: {e}"
                print(f"   ⚠️ {msg}")
                errori.append(msg)
    else:
        print("❌ Cartella 'volantini' non trovata.")
        errori.append("Cartella 'volantini' non trovata.")

    # SALVATAGGIO
    if not offerte:
        offerte = {"Info": [{"name": "Nessuna offerta trovata. Controlla il PDF.", "price": 0.00}]}

    file_out = os.path.join(base, "offerte.json")
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)
    print("💾 Offerte salvate.")

    # Se nessun volantino è stato analizzato con successo, fai fallire il job:
    # così su GitHub Actions vedi rosso invece di un falso "successo".
    if errori and "Info" in offerte:
        print(f"❌ Analisi fallita per tutti i volantini ({len(errori)} errori). Vedi log sopra.")
        sys.exit(1)


if __name__ == "__main__":
    analizza()

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
    sys.exit(1)

# Lista di modelli da provare in ordine. gemini-1.5-flash è stato ritirato da Google:
# usiamo l'alias "-latest" (si aggiorna da solo nel tempo) e alcuni nomi concreti come riserva.
MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
]

MAX_PAGES = 30           # limite di sicurezza sul totale pagine per PDF
PAGES_PER_BATCH = 6       # poche pagine per richiesta = molta piu' precisione, meno "invenzioni"
IMG_SCALE = 2.3           # ~166 dpi, molto piu' leggibile di prima (era 1.5 ~ 108 dpi)
MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 5


def pulisci_array_json(text):
    """Estrae un array JSON [...] dal testo, ripulendo eventuali markdown fences."""
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("[")
    e = text.rfind("]") + 1
    if s != -1 and e != -1:
        return text[s:e]
    return text


def estrai_testo_risposta(res_json):
    """Concatena TUTTE le parti di testo della risposta, non solo la prima."""
    try:
        parts = res_json["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p)
    except (KeyError, IndexError, TypeError):
        return ""


def chiama_gemini(model_name, prompt_text, image_parts):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt_text}] + image_parts}]}
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }

    for tentativo in range(1, MAX_RETRIES_PER_MODEL + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.RequestException as e:
            print(f"      ⚠️ Errore di rete con {model_name} (tentativo {tentativo}): {e}")
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"      ⚠️ Modello '{model_name}' non disponibile (404). Passo al prossimo.")
            return None
        elif response.status_code == 429:
            print(f"      ⏳ Rate limit (429) su {model_name}, riprovo tra {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)
            continue
        else:
            print(f"      ⚠️ Errore HTTP {response.status_code} con {model_name}: {response.text[:300]}")
            return None

    return None


def analizza_lotto(nome, image_parts, num_batch):
    """Analizza un piccolo gruppo di pagine e restituisce una lista di prodotti (puo' essere vuota)."""
    prompt_text = f"""
    Stai guardando {len(image_parts)} pagine (foto) di un volantino di supermercato ("{nome}").

    Il tuo compito è fare OCR/trascrizione, NON inventare.
    Regole obbligatorie:
    1. Trascrivi SOLO i prodotti alimentari con un prezzo chiaramente visibile e leggibile nell'immagine.
    2. Ignora completamente detersivi, prodotti per la casa, elettronica, abbigliamento.
    3. Se il testo di un prezzo o di un nome prodotto è sfocato, tagliato, troppo piccolo o non sei sicuro al 100%, OMETTI quel prodotto: NON indovinare e NON inventare valori plausibili.
    4. Se in queste pagine non c'è nessun prodotto alimentare leggibile, restituisci un array vuoto [].
    5. Il prezzo deve essere un numero (es. 1.99), mai una stringa, mai con la virgola.

    RISPONDI SOLO con un array JSON in questo formato esatto, senza testo prima o dopo:
    [
        {{"name": "Nome esatto del prodotto", "price": 0.00}}
    ]
    """

    for model in MODELS:
        res_json = chiama_gemini(model, prompt_text, image_parts)
        if not res_json:
            continue
        ai_text = estrai_testo_risposta(res_json)
        if not ai_text:
            print(f"      ⚠️ Risposta vuota dal modello '{model}' (lotto {num_batch}).")
            continue
        try:
            data = json.loads(pulisci_array_json(ai_text))
            if not isinstance(data, list):
                raise ValueError("La risposta non è un array JSON")
            print(f"      ✅ Lotto {num_batch}: {len(data)} prodotti con '{model}'.")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"      ❌ JSON non valido dal modello '{model}' (lotto {num_batch}): {e}")
            print(f"      --- Risposta grezza (primi 300 char) ---\n{ai_text[:300]}")
            continue

    print(f"      ❌ Tutti i modelli hanno fallito per il lotto {num_batch}.")
    return None  # None = fallimento vero e proprio, diverso da [] = "nessun prodotto in queste pagine"


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
                doc = fitz.open(fp)
                max_pages = min(len(doc), MAX_PAGES)
                if len(doc) > MAX_PAGES:
                    print(f"   ℹ️ Il PDF ha {len(doc)} pagine, ne analizzo solo {MAX_PAGES}.")

                prodotti_totali = []
                nomi_visti = set()  # per evitare duplicati tra un lotto e l'altro
                num_batch = 0
                lotti_falliti = 0
                lotti_totali = 0

                for start in range(0, max_pages, PAGES_PER_BATCH):
                    num_batch += 1
                    lotti_totali += 1
                    end = min(start + PAGES_PER_BATCH, max_pages)
                    print(f"   📖 Lotto {num_batch}: pagine {start + 1}-{end}...")

                    image_parts = []
                    for i in range(start, end):
                        page = doc.load_page(i)
                        pix = page.get_pixmap(matrix=fitz.Matrix(IMG_SCALE, IMG_SCALE))
                        img_bytes = pix.tobytes("jpeg")
                        b64_img = base64.b64encode(img_bytes).decode("utf-8")
                        image_parts.append({
                            "inline_data": {"mime_type": "image/jpeg", "data": b64_img}
                        })

                    risultato = analizza_lotto(nome, image_parts, num_batch)
                    if risultato is None:
                        lotti_falliti += 1
                        continue

                    for prodotto in risultato:
                        try:
                            key = (str(prodotto.get("name", "")).strip().lower(), round(float(prodotto.get("price", 0)), 2))
                        except (TypeError, ValueError):
                            continue
                        if key[0] and key not in nomi_visti:
                            nomi_visti.add(key)
                            prodotto["price"] = key[1]
                            prodotti_totali.append(prodotto)

                doc.close()

                if lotti_falliti == lotti_totali and lotti_totali > 0:
                    msg = f"Tutti i {lotti_totali} lotti sono falliti per '{nome}'."
                    print(f"   ❌ {msg}")
                    errori.append(msg)
                    continue

                offerte[nome] = prodotti_totali
                print(f"   ✅ Totale per '{nome}': {len(prodotti_totali)} prodotti "
                      f"({lotti_falliti}/{lotti_totali} lotti falliti).")

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

    if errori and "Info" in offerte:
        print(f"❌ Analisi fallita per tutti i volantini ({len(errori)} errori). Vedi log sopra.")
        sys.exit(1)


if __name__ == "__main__":
    analizza()

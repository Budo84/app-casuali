import os
import json
import glob
import base64
import time
import requests
import fitz  # Libreria PyMuPDF
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

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

MAX_PAGES = 30            # limite di sicurezza sul totale pagine per PDF
PAGES_PER_BATCH = 8        # meno lotti = meno chiamate = piu' veloce (ma leggermente meno "attenzione" per pagina)
IMG_SCALE = 2.0            # leggermente ridotta da 2.3: ancora molto piu' nitida dell'originale (1.5), ma piu' leggera/veloce da inviare
MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 4
MAX_WORKERS = 4            # quanti lotti analizzare IN PARALLELO


def pulisci_array_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("[")
    e = text.rfind("]") + 1
    if s != -1 and e != -1:
        return text[s:e]
    return text


def estrai_testo_risposta(res_json):
    try:
        parts = res_json["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p)
    except (KeyError, IndexError, TypeError):
        return ""


def chiama_gemini(model_name, prompt_text, image_parts, etichetta):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt_text}] + image_parts}]}
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}

    for tentativo in range(1, MAX_RETRIES_PER_MODEL + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
        except requests.exceptions.RequestException as e:
            print(f"   [{etichetta}] ⚠️ Errore di rete con {model_name} (tentativo {tentativo}): {e}")
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"   [{etichetta}] ⚠️ Modello '{model_name}' non disponibile (404).")
            return None
        elif response.status_code == 429:
            print(f"   [{etichetta}] ⏳ Rate limit (429) su {model_name}, riprovo tra {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)
            continue
        else:
            print(f"   [{etichetta}] ⚠️ Errore HTTP {response.status_code} con {model_name}: {response.text[:200]}")
            return None

    return None


def analizza_lotto(nome, image_parts, etichetta):
    """Analizza un gruppo di pagine. Ritorna una lista (anche vuota) o None se fallito del tutto."""
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
        res_json = chiama_gemini(model, prompt_text, image_parts, etichetta)
        if not res_json:
            continue
        ai_text = estrai_testo_risposta(res_json)
        if not ai_text:
            print(f"   [{etichetta}] ⚠️ Risposta vuota dal modello '{model}'.")
            continue
        try:
            data = json.loads(pulisci_array_json(ai_text))
            if not isinstance(data, list):
                raise ValueError("La risposta non è un array JSON")
            print(f"   [{etichetta}] ✅ {len(data)} prodotti con '{model}'.")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"   [{etichetta}] ❌ JSON non valido dal modello '{model}': {e}")
            continue

    print(f"   [{etichetta}] ❌ Tutti i modelli hanno fallito.")
    return None


def prepara_lotti(fp, nome):
    """Apre il PDF e prepara la lista di lotti (etichetta, image_parts) senza ancora chiamare l'AI."""
    doc = fitz.open(fp)
    max_pages = min(len(doc), MAX_PAGES)
    if len(doc) > MAX_PAGES:
        print(f"   ℹ️ {nome}: il PDF ha {len(doc)} pagine, ne analizzo solo {MAX_PAGES}.")

    lotti = []
    num_batch = 0
    for start in range(0, max_pages, PAGES_PER_BATCH):
        num_batch += 1
        end = min(start + PAGES_PER_BATCH, max_pages)
        image_parts = []
        for i in range(start, end):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(IMG_SCALE, IMG_SCALE))
            img_bytes = pix.tobytes("jpeg")
            b64_img = base64.b64encode(img_bytes).decode("utf-8")
            image_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_img}})
        etichetta = f"{nome} p.{start + 1}-{end}"
        lotti.append((etichetta, image_parts))
    doc.close()
    return lotti


import subprocess


def trova_radice_repo():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def ultimo_commit_timestamp(filepath, repo_root):
    """Restituisce l'orario (unix timestamp) dell'ultimo commit che ha toccato questo file. 0 se sconosciuto."""
    if not repo_root:
        return 0
    try:
        rel = os.path.relpath(filepath, repo_root)
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", rel],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        ts = out.stdout.strip()
        return int(ts) if out.returncode == 0 and ts else 0
    except Exception:
        return 0


def analizza():
    t0 = time.time()
    base = os.path.dirname(os.path.abspath(__file__))
    paths = [os.path.join(base, "volantini"), os.path.join(os.getcwd(), "spesa", "volantini")]
    target = next((p for p in paths if os.path.exists(p)), None)

    # Carica le offerte gia' salvate in precedenza: le manteniamo per i supermercati
    # che NON stiamo rianalizzando in questa esecuzione.
    file_out_path = os.path.join(base, "offerte.json")
    offerte = {}
    try:
        with open(file_out_path, "r", encoding="utf-8") as f:
            offerte = json.load(f)
        offerte.pop("Info", None)  # rimuovi l'eventuale placeholder di errore
    except Exception:
        offerte = {}

    errori = []

    if target:
        tutti_i_pdf = glob.glob(os.path.join(target, "*.[pP][dD][fF]"))
        print(f"🔎 Trovati {len(tutti_i_pdf)} PDF in totale nella cartella.")

        # Analizza SOLO il/i PDF caricati con l'ultimo commit (di norma un upload = un commit = un PDF),
        # cosi' non si rianalizzano ogni volta anche i volantini gia' letti in precedenza.
        repo_root = trova_radice_repo()
        file_times = [(fp, ultimo_commit_timestamp(fp, repo_root)) for fp in tutti_i_pdf]
        file_times = [(fp, t) for fp, t in file_times if t > 0]

        if file_times:
            newest_ts = max(t for _, t in file_times)
            files = [fp for fp, t in file_times if t == newest_ts]
            print(f"🆕 Volantino/i più recente/i (ultimo commit): {[os.path.basename(f) for f in files]}")
            saltati = [os.path.basename(fp) for fp in tutti_i_pdf if fp not in files]
            if saltati:
                print(f"⏭️ Non rianalizzo (già fatto in precedenza): {saltati}")
        else:
            files = tutti_i_pdf
            print("⚠️ Impossibile leggere la cronologia git (repo non trovato?): analizzo tutti i PDF per sicurezza.")

        # 1. Prepara TUTTI i lotti dei PDF selezionati prima di chiamare l'AI
        job_per_store = {}   # nome -> lista di (etichetta, image_parts)
        for fp in files:
            nome = os.path.splitext(os.path.basename(fp))[0].replace("_", " ").title()
            print(f"📄 Preparazione immagini: {nome}")
            job_per_store[nome] = prepara_lotti(fp, nome)

        # 2. Metti in coda TUTTI i lotti di TUTTI i PDF insieme e falli girare in parallelo
        tutti_i_lotti = []  # (nome, etichetta, image_parts)
        for nome, lotti in job_per_store.items():
            for etichetta, image_parts in lotti:
                tutti_i_lotti.append((nome, etichetta, image_parts))

        print(f"🤖 Analisi di {len(tutti_i_lotti)} lotti in parallelo (max {MAX_WORKERS} alla volta)...")
        risultati_per_store = {nome: [] for nome in job_per_store}
        falliti_per_store = {nome: 0 for nome in job_per_store}
        nomi_visti_per_store = {nome: set() for nome in job_per_store}

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {
                executor.submit(analizza_lotto, nome, image_parts, etichetta): nome
                for nome, etichetta, image_parts in tutti_i_lotti
            }
            for future in as_completed(future_map):
                nome = future_map[future]
                try:
                    risultato = future.result()
                except Exception as e:
                    print(f"   ⚠️ Errore imprevisto per '{nome}': {e}")
                    risultato = None

                if risultato is None:
                    falliti_per_store[nome] += 1
                    continue

                for prodotto in risultato:
                    try:
                        key = (str(prodotto.get("name", "")).strip().lower(), round(float(prodotto.get("price", 0)), 2))
                    except (TypeError, ValueError):
                        continue
                    if key[0] and key not in nomi_visti_per_store[nome]:
                        nomi_visti_per_store[nome].add(key)
                        prodotto["price"] = key[1]
                        risultati_per_store[nome].append(prodotto)

        # 3. Assembla i risultati finali
        for nome, lotti in job_per_store.items():
            totale_lotti = len(lotti)
            falliti = falliti_per_store[nome]
            if totale_lotti > 0 and falliti == totale_lotti:
                msg = f"Tutti i {totale_lotti} lotti sono falliti per '{nome}'."
                print(f"❌ {msg}")
                errori.append(msg)
                continue
            offerte[nome] = risultati_per_store[nome]
            print(f"✅ Totale per '{nome}': {len(risultati_per_store[nome])} prodotti ({falliti}/{totale_lotti} lotti falliti).")
    else:
        print("❌ Cartella 'volantini' non trovata.")
        errori.append("Cartella 'volantini' non trovata.")

    # SALVATAGGIO
    if not offerte:
        offerte = {"Info": [{"name": "Nessuna offerta trovata. Controlla il PDF.", "price": 0.00}]}

    with open(file_out_path, "w", encoding="utf-8") as f:
        json.dump(offerte, f, indent=4, ensure_ascii=False)

    print(f"💾 Offerte salvate. Tempo totale: {time.time() - t0:.1f}s")

    if errori and "Info" in offerte:
        print(f"❌ Analisi fallita per tutti i volantini ({len(errori)} errori). Vedi log sopra.")
        sys.exit(1)


if __name__ == "__main__":
    analizza()

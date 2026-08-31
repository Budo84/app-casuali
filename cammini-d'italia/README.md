# Cammini d'Italia (e non solo) — Pianificatore offline

Web app statica (HTML/CSS/JS puro, nessun backend) per esplorare cammini e trail italiani ed europei, pianificare le tappe, importare tracce GPX, cercare strutture ricettive vicino a ogni tappa e usare tutto anche senza connessione. Pensata per essere ospitata gratis su **GitHub Pages**.

## Funzionalità

- **Esplora**: elenco di cammini con tappe, km, dislivelli, difficoltà (cammini italiani più il Cammino di Santiago).
- **Pianifica**: genera un itinerario giorno per giorno in base al tuo ritmo di marcia, con data di partenza; salva i piani sul dispositivo.
- **Traccia GPX**: carica un file `.gpx` (scaricato ad es. da Wikiloc, dal sito ufficiale del cammino o dal CAI) e visualizzalo su mappa con statistiche di distanza e dislivello. Da ogni traccia caricata puoi creare un **cammino personalizzato**, che compare tra le tile in Esplora esattamente come i cammini ufficiali (con ricerca strutture inclusa), oppure aggiungerla come nuova tappa a un cammino personalizzato già creato in precedenza.
- **Strutture ricettive**: per ogni tappa con coordinate, un pulsante "Cerca strutture vicino all'arrivo" interroga OpenStreetMap (Overpass API) e mostra hotel, ostelli, B&B, agriturismi, campeggi e rifugi nel raggio di 3 km, con indirizzo, telefono e sito quando disponibili. I risultati vengono salvati sul dispositivo per essere consultati anche offline.
- **Consigli**: zaino, sicurezza in montagna, organizzazione delle tappe, link a fonti ufficiali (CAI, Vie Francigene, Wikiloc).
- **Dati**: esporta/importa il database dei cammini e i tuoi dati personali in JSON; funziona come PWA installabile e offline.

## Come funziona l'offline

Un *service worker* (`service-worker.js`) mette in cache l'intera app (HTML, CSS, JS, il database `data/db.json`) al primo caricamento. Da quel momento l'app si apre e resta utilizzabile anche senza rete. Le tile della mappa (OpenStreetMap) e la ricerca strutture (Overpass API) richiedono connessione al momento della richiesta; le tile già visitate e le strutture già cercate restano disponibili offline.

I tuoi itinerari pianificati, le tracce GPX caricate, le strutture ricettive trovate e i cammini personalizzati creati dalle tue tracce sono salvati in `localStorage`, quindi restano sul dispositivo anche offline e sopravvivono agli aggiornamenti futuri del database ufficiale.

## Fonte dei dati

Il file `data/db.json` contiene un database curato a mano con informazioni pubbliche generali su alcuni cammini italiani noti (Via Francigena, Cammino di Francesco, Via degli Dei, Alta Via 1 delle Dolomiti, Cammino Materano, un tratto d'esempio del Sentiero Italia CAI) e sul Cammino di Santiago (Camino Francés, Francia-Spagna), incluso su richiesta pur non essendo un cammino italiano.

Le strutture ricettive mostrate nel dettaglio di ogni tappa provengono da **OpenStreetMap**, tramite la **Overpass API** pubblica (`https://overpass-api.de`), gratuita e senza chiave di accesso. Sono dati contribuiti dalla comunità OSM: possono essere incompleti, specialmente in zone remote di montagna, e vanno sempre verificati contattando direttamente la struttura o consultando altri portali di prenotazione prima di partire.

**Importante**: le distanze, i dislivelli e i tempi sono indicativi. Prima di partire, verifica sempre:
- il sito ufficiale del cammino (link presente in ogni scheda),
- una traccia GPX aggiornata (da Wikiloc, dal sito ufficiale o dal CAI),
- le condizioni meteo e del sentiero.

Puoi ampliare o correggere il database in due modi:
1. Modifica direttamente `data/db.json` (segui la struttura esistente) e ripubblica su GitHub Pages.
2. Dalla scheda **Dati** dell'app, esporta il database attuale, modificalo offline, poi reimportalo: l'app salva la tua versione personalizzata in locale senza serve modificare il codice.

## Pubblicare su GitHub Pages

1. Crea un nuovo repository su GitHub (es. `cammini-italia`).
2. Carica tutti i file di questa cartella nella root del repository (mantenendo la struttura `css/`, `js/`, `data/`, `icons/`).
3. Vai su **Settings → Pages** del repository.
4. In "Build and deployment", scegli **Deploy from a branch**, branch `main`, cartella `/ (root)`.
5. Dopo qualche minuto l'app sarà online su `https://<tuo-utente>.github.io/cammini-italia/`.

Nota: i service worker richiedono HTTPS (o `localhost`) per funzionare — GitHub Pages serve tutto in HTTPS di default, quindi l'offline funzionerà automaticamente una volta pubblicata.

## Sviluppo locale

Non serve alcuna build. Basta servire la cartella con un server statico qualsiasi, ad esempio:

```bash
cd cammini-italia
python3 -m http.server 8080
```

Poi apri `http://localhost:8080` nel browser. (Aprire direttamente `index.html` con `file://` funziona per l'interfaccia, ma il service worker e il `fetch` del database richiedono un server, anche locale.)

## Struttura del progetto

```
cammini-italia/
├── index.html
├── manifest.json
├── service-worker.js
├── css/
│   └── style.css
├── js/
│   ├── app.js        # logica interfaccia
│   ├── db.js         # caricamento/salvataggio database e dati utente
│   ├── gpx.js        # parsing dei file GPX
│   └── strutture.js  # ricerca strutture ricettive via Overpass API (OpenStreetMap)
├── data/
│   └── db.json      # database dei cammini
└── icons/
    ├── icon-192.png
    └── icon-512.png
```

## Aggiungere un nuovo cammino al database

Ogni voce di `data/db.json` segue questa struttura:

```json
{
  "id": "slug-univoco",
  "nome": "Nome del cammino",
  "tipo": "religioso-storico | trekking-storico | trekking-montagna | facile-media",
  "regioni": ["Regione1", "Regione2"],
  "difficoltaGenerale": "facile | media | impegnativa",
  "descrizione": "Breve descrizione originale.",
  "sitoUfficiale": "https://...",
  "wikilocRicerca": "https://www.wikiloc.com/wikiloc/find.do?q=...",
  "segnaletica": "Descrizione del segnavia",
  "tappe": [
    {"n": 1, "da": "...", "a": "...", "km": 20, "dislivelloSalita": 300, "dislivelloDiscesa": 200, "difficolta": "media", "note": "..."}
  ]
}
```

## Licenza dei contenuti

I testi descrittivi sono originali. Le tracce GPX che l'utente importa restano di proprietà di chi le ha create/condivise (es. community Wikiloc): l'app le salva solo in locale sul dispositivo dell'utente e non le ridistribuisce.

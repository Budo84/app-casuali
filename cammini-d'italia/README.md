# Cammini d'Italia (e non solo) — Pianificatore offline

Web app statica (HTML/CSS/JS puro, nessun backend) per esplorare cammini e trail italiani ed europei, pianificare le tappe, importare tracce GPX, cercare strutture ricettive vicino a ogni tappa e usare tutto anche senza connessione. Pensata per essere ospitata gratis su **GitHub Pages**.

## Funzionalità

- **Esplora**: elenco di cammini con tappe, km, dislivelli, difficoltà (cammini italiani più il Cammino di Santiago), mostrati come tile visive. Puoi ordinarle per distanza dalla tua posizione con "📍 Cammini vicino a me".
- **Dettaglio cammino con mappa sempre visibile**: aprendo un cammino vedi subito una mappa con il percorso. Se non è disponibile un tracciato reale, la mappa mostra un percorso approssimativo (linea tratteggiata tra le tappe); puoi cercare e importare il **tracciato reale da OpenStreetMap** con un clic, quando il cammino è lì mappato per intero (è il caso di molti cammini storici). Sono presenti anche link di ricerca su più piattaforme esterne (Wikiloc, Outdooractive, AllTrails, Komoot, Waymarked Trails), non solo Wikiloc.
- **Tempo di percorrenza stimato**: calcolato per ogni tappa e per l'intero cammino in base al tuo passo di marcia personale (regola di Naismith: velocità in piano + tempo aggiuntivo per il dislivello), impostabile nella scheda Dati.
- **Meteo per tappa**: previsioni a 5 giorni (Open-Meteo, gratuito) per il punto di arrivo di ogni tappa.
- **Diario di viaggio**: aggiungi note e, opzionalmente, una foto per ogni tappa; tutto resta salvato sul dispositivo.
- **Tappe completate e statistiche personali**: spunta le tappe che hai davvero percorso; nella scheda Dati trovi km totali percorsi, dislivello totale, tappe e cammini completati.
- **Checklist zaino interattiva**: nella scheda Consigli, lista predefinita di attrezzatura spuntabile e personalizzabile.
- **Profilo altimetrico**: grafico nel dettaglio di ogni cammino, reale se creato da una traccia GPS oppure stimato dai dislivelli complessivi di ogni tappa.
- **Tema chiaro/scuro**: pulsante 🌙/☀️ in alto, preferenza salvata sul dispositivo.
- **Registrazione GPS**: nella scheda Registra puoi tracciare davvero il percorso mentre cammini (avvia, metti in pausa, ferma) e salvarlo come traccia GPX, da cui puoi anche creare un cammino personalizzato.
- **Punti acqua**: pulsante "💧 Punti acqua" per tappa, stesso motore di ricerca (Overpass API) usato per le strutture ricettive.
- **Preferiti**: stella su ogni tile, con filtro "Solo preferiti".
- **Confronto cammini**: seleziona fino a 3 cammini per confrontarli fianco a fianco (km, dislivello, difficoltà, tempo stimato, regioni).
- **Traguardi**: piccoli obiettivi sbloccabili in base alle tue statistiche (km percorsi, tappe completate, dislivello, cammini creati), visibili nella scheda Dati.
- **Giochi per bambini**: nel dettaglio di ogni cammino, sezione "🎮 Giochi di questo cammino" con quattro mini-giochi generati sui dati reali di quel cammino:
  - **Quiz** — 5 domande su tappe, km, regione, difficoltà
  - **Memory** — abbina partenza e arrivo di ogni tappa
  - **Caccia al tesoro** — cose da scoprire camminando, con i punti di interesse reali quando disponibili
  - **Salto del Pellegrino** — un vero mini-gioco platform (canvas 2D), con **un livello per ogni tappa** generato dalla sua difficoltà/dislivello reale, **4 personaggi sbloccabili** man mano che si accumulano punti o si completa un cammino, controlli touch a schermo, e fino a 3 stelle per livello in base ai tesori raccolti
- **Sistema di medaglie "da bambini"**: traguardi mostrati come un album di adesivi (sbloccati dorati, ancora da sbloccare tratteggiati), con un'animazione di festa (confetti) alla prima sblocco di ognuno, un **forziere a sorpresa** che si apre ogni 50 punti gioco, e un **diploma stampabile** per ogni medaglia (con il nome di chi l'ha vinta).
- **Pianifica**: genera un itinerario giorno per giorno in base al tuo ritmo di marcia, con data di partenza e tempo stimato; salva i piani sul dispositivo o esportali come **PDF stampabile**.
- **Traccia GPX**: carica un file `.gpx` (scaricato ad es. da Wikiloc, dal sito ufficiale del cammino o dal CAI) e visualizzalo su mappa con statistiche di distanza e dislivello. I punti di interesse (waypoint) presenti nel file — rifugi, fontane, chiese, panorami — vengono riconosciuti e mostrati con nome e descrizione, e il link alla pagina originale (es. su Wikiloc) viene conservato. Da ogni traccia caricata puoi creare un **cammino personalizzato**: nome dei luoghi di partenza/arrivo, tipologia e difficoltà vengono **rilevati automaticamente** (geocodifica inversa via OpenStreetMap Nominatim per i nomi dei luoghi, parole chiave per tipologia/difficoltà), ma **restano tutti modificabili** prima di salvare e anche in seguito, dal dettaglio del cammino ("Modifica"). Il cammino compare tra le tile in Esplora esattamente come i cammini ufficiali (con ricerca strutture, punti di interesse e link alla traccia originale inclusi), oppure puoi aggiungere la traccia come nuova tappa a un cammino personalizzato già creato in precedenza. Puoi anche **condividere** un tuo cammino personalizzato come file, da mandare a un amico che potrà importarlo nella sua app.
- **Strutture ricettive**: per ogni tappa con coordinate, un pulsante "Cerca strutture vicino all'arrivo" interroga OpenStreetMap (Overpass API) e mostra hotel, ostelli, B&B, agriturismi, campeggi e rifugi nel raggio di 3 km, con indirizzo, telefono e sito quando disponibili. I risultati vengono salvati sul dispositivo per essere consultati anche offline.
- **Consigli**: zaino, sicurezza in montagna, organizzazione delle tappe, link a fonti ufficiali (CAI, Vie Francigene, Wikiloc).
- **Dati**: esporta/importa il database dei cammini e i tuoi dati personali (itinerari, diario, checklist, statistiche) in JSON; funziona come PWA installabile e offline.

## Come funziona l'offline

Un *service worker* (`service-worker.js`) mette in cache l'intera app (HTML, CSS, JS, il database `data/db.json`) al primo caricamento. Da quel momento l'app si apre e resta utilizzabile anche senza rete. Le tile della mappa (OpenStreetMap) e la ricerca strutture (Overpass API) richiedono connessione al momento della richiesta; le tile già visitate e le strutture già cercate restano disponibili offline.

I tuoi itinerari pianificati, le tracce GPX caricate, le strutture ricettive trovate e i cammini personalizzati creati dalle tue tracce sono salvati in `localStorage`, quindi restano sul dispositivo anche offline e sopravvivono agli aggiornamenti futuri del database ufficiale.

## Fonte dei dati

Il file `data/db.json` contiene un database curato a mano con informazioni pubbliche generali su alcuni cammini italiani noti (Via Francigena, Cammino di Francesco, Via degli Dei, Alta Via 1 delle Dolomiti, Cammino Materano, un tratto d'esempio del Sentiero Italia CAI) e sul Cammino di Santiago (Camino Francés, Francia-Spagna), incluso su richiesta pur non essendo un cammino italiano.

Le strutture ricettive mostrate nel dettaglio di ogni tappa provengono da **OpenStreetMap**, tramite la **Overpass API** pubblica (`https://overpass-api.de`), gratuita e senza chiave di accesso. Sono dati contribuiti dalla comunità OSM: possono essere incompleti, specialmente in zone remote di montagna, e vanno sempre verificati contattando direttamente la struttura o consultando altri portali di prenotazione prima di partire.

Il riconoscimento automatico dei nomi di partenza/arrivo quando crei un cammino da una traccia GPX usa la **Nominatim API** di OpenStreetMap (`https://nominatim.openstreetmap.org`), anch'essa gratuita e senza chiave. Tipologia e difficoltà proposte automaticamente sono invece stimate con semplici parole chiave e statistiche della traccia (km, dislivello): sono solo un punto di partenza, sempre correggibile a mano nel form o in seguito dal pulsante "Modifica" nel dettaglio del cammino.

Il tracciato reale che puoi importare per un cammino dal suo dettaglio proviene anch'esso da **OpenStreetMap** (relazioni `route=hiking`/`route=foot`, sempre via Overpass API): è un'importazione "a miglior sforzo", che ricompone i singoli tratti mappati in un unico percorso continuo per vicinanza geografica — non è quindi garantita al 100% come un vero file GPX ufficiale, ma è un dato reale e verificabile, non inventato. Se un cammino non risulta ancora mappato per intero su OpenStreetMap, puoi comunque cercarlo manualmente sulle altre piattaforme collegate dal dettaglio (Wikiloc, Outdooractive, AllTrails, Komoot) e importarlo come file GPX dalla scheda "Traccia GPX": non è possibile automatizzare il download da queste piattaforme, perché richiederebbe accordi commerciali o tecniche di scraping che l'app non usa.

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
│   ├── strutture.js  # ricerca strutture ricettive via Overpass API (OpenStreetMap)
│   ├── geocode.js    # geocodifica inversa (Nominatim) e classificazione automatica tipo/difficoltà
│   ├── osmtracce.js  # ricerca e importazione di tracciati reali da OpenStreetMap (Overpass API)
│   ├── meteo.js      # previsioni meteo per tappa (Open-Meteo)
│   ├── giochi.js     # generazione di quiz, memory e caccia al tesoro su misura per ogni cammino
│   └── platform.js   # motore del gioco platform "Salto del Pellegrino" (canvas 2D, livelli, personaggi)
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

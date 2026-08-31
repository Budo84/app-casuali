/* Ricerca strutture ricettive (alberghi, ostelli, B&B, agriturismi, campeggi, rifugi)
   vicino alle tappe di un cammino, tramite Overpass API di OpenStreetMap.
   Nessuna chiave richiesta. Serve connessione internet al momento della ricerca;
   i risultati vengono poi salvati in localStorage per la consultazione offline. */

const STRUTTURE = {
  KEY_CACHE: 'cammini_strutture_v1',
  ENDPOINT: 'https://overpass-api.de/api/interpreter',

  // Raggio di ricerca in metri attorno al punto di arrivo della tappa
  RAGGIO_DEFAULT: 3000,

  // Tag OSM considerati "struttura ricettiva"
  TAG_QUERY: [
    ['tourism', 'hotel'],
    ['tourism', 'hostel'],
    ['tourism', 'guest_house'],
    ['tourism', 'apartment'],
    ['tourism', 'chalet'],
    ['tourism', 'camp_site'],
    ['tourism', 'alpine_hut'],
    ['tourism', 'wilderness_hut'],
  ],

  _cache() {
    try { return JSON.parse(localStorage.getItem(this.KEY_CACHE)) || {}; }
    catch (e) { return {}; }
  },
  _saveCache(cache) {
    localStorage.setItem(this.KEY_CACHE, JSON.stringify(cache));
  },

  // Chiave univoca per identificare la tappa cercata (cammino + numero tappa)
  _chiave(camminoId, tappaN) {
    return `${camminoId}__tappa${tappaN}`;
  },

  // Restituisce i risultati già salvati per una tappa, se presenti (funziona offline)
  getSalvate(camminoId, tappaN) {
    const cache = this._cache();
    return cache[this._chiave(camminoId, tappaN)] || null;
  },

  // Costruisce la query Overpass QL per uno o più punti (lat, lon)
  _costruisciQuery(punti, raggio) {
    const filtri = this.TAG_QUERY.map(([k, v]) => `["${k}"="${v}"]`);
    let corpo = '[out:json][timeout:25];(';
    for (const [lat, lon] of punti) {
      for (const f of filtri) {
        corpo += `node${f}(around:${raggio},${lat},${lon});`;
        corpo += `way${f}(around:${raggio},${lat},${lon});`;
      }
    }
    corpo += ');out center tags;';
    return corpo;
  },

  // Esegue la ricerca online via Overpass API attorno alle coordinate di arrivo (e opzionalmente partenza) di una tappa
  async cerca(camminoId, tappa, opzioni = {}) {
    const raggio = opzioni.raggio || this.RAGGIO_DEFAULT;
    const punti = [];
    if (tappa.coordA) punti.push(tappa.coordA);
    if (opzioni.includiPartenza && tappa.coordDa) punti.push(tappa.coordDa);
    if (punti.length === 0) {
      throw new Error('Questa tappa non ha coordinate geografiche: impossibile cercare strutture.');
    }

    const query = this._costruisciQuery(punti, raggio);
    const res = await fetch(this.ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: query
    });

    if (!res.ok) {
      throw new Error(`Overpass API ha risposto con errore ${res.status}. Riprova tra qualche istante (il servizio pubblico è a volte sovraccarico).`);
    }

    const data = await res.json();
    const risultati = (data.elements || []).map(el => this._normalizza(el)).filter(Boolean);

    // rimuove duplicati (stesso nome + coordinate arrotondate)
    const viste = new Set();
    const uniche = risultati.filter(r => {
      const k = `${r.nome}_${r.lat.toFixed(4)}_${r.lon.toFixed(4)}`;
      if (viste.has(k)) return false;
      viste.add(k);
      return true;
    });

    // Salva in cache locale per consultazione offline
    const cache = this._cache();
    cache[this._chiave(camminoId, tappa.n)] = {
      cercatoIl: new Date().toISOString(),
      raggio,
      strutture: uniche
    };
    this._saveCache(cache);

    return uniche;
  },

  _normalizza(el) {
    const tags = el.tags || {};
    const lat = el.type === 'node' ? el.lat : (el.center ? el.center.lat : null);
    const lon = el.type === 'node' ? el.lon : (el.center ? el.center.lon : null);
    if (lat == null || lon == null) return null;

    const tipoMap = {
      hotel: 'Hotel',
      hostel: 'Ostello',
      guest_house: 'B&B / Guest house',
      apartment: 'Appartamento turistico',
      chalet: 'Chalet',
      camp_site: 'Campeggio',
      alpine_hut: 'Rifugio alpino',
      wilderness_hut: 'Rifugio non custodito'
    };

    return {
      nome: tags.name || tags['name:it'] || '(struttura senza nome su OSM)',
      tipo: tipoMap[tags.tourism] || tags.tourism || 'Struttura',
      lat, lon,
      indirizzo: [tags['addr:street'], tags['addr:housenumber'], tags['addr:city']]
        .filter(Boolean).join(' '),
      telefono: tags.phone || tags['contact:phone'] || null,
      sito: tags.website || tags['contact:website'] || null,
      email: tags.email || tags['contact:email'] || null,
      openingHours: tags.opening_hours || null,
      osmId: `${el.type}/${el.id}`
    };
  },

  // Elimina tutte le strutture salvate (reset dati utente)
  reset() {
    localStorage.removeItem(this.KEY_CACHE);
  }
};

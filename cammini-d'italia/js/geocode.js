/* Geocodifica inversa (coordinate -> nome del luogo) tramite Nominatim di OpenStreetMap,
   gratuita e senza chiave. Usata per riconoscere automaticamente partenza/arrivo di una
   traccia GPX. Va rispettato il limite di 1 richiesta al secondo del servizio pubblico. */

const GEOCODE = {
  ENDPOINT: 'https://nominatim.openstreetmap.org/reverse',
  _ultimaChiamata: 0,

  async _attendiRateLimit() {
    const attesa = 1100 - (Date.now() - this._ultimaChiamata);
    if (attesa > 0) await new Promise(r => setTimeout(r, attesa));
    this._ultimaChiamata = Date.now();
  },

  // Restituisce { nome, regione } oppure null se non disponibile (offline o servizio irraggiungibile)
  async nomeLuogo(lat, lon) {
    try {
      await this._attendiRateLimit();
      const url = `${this.ENDPOINT}?format=jsonv2&lat=${lat}&lon=${lon}&zoom=14&addressdetails=1&accept-language=it`;
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!res.ok) return null;
      const data = await res.json();
      const a = data.address || {};
      const nome = a.village || a.town || a.city || a.hamlet || a.suburb || a.municipality
        || (data.display_name ? data.display_name.split(',')[0].trim() : null);
      const regione = a.state || a.county || null;
      if (!nome) return null;
      return { nome, regione };
    } catch (e) {
      return null; // offline o servizio non raggiungibile: chi chiama userà un valore di riserva
    }
  }
};

/* Classificazione automatica di tipo e difficoltà di un cammino, a partire da testo
   (nome traccia + punti di interesse) e dati statistici (km, dislivello). Sono euristiche
   semplici basate su parole chiave: l'utente può sempre correggerle a mano. */

const CLASSIFICA = {
  PAROLE_RELIGIOSO: ['chiesa', 'cattedrale', 'santuario', 'abbazia', 'pellegrin', 'via crucis',
    'monastero', 'cammino di', 'francigena', 'certosa', 'basilica', 'convento', 'eremo', 'via degli dei', 'santiago'],
  PAROLE_STORICO: ['storico', 'medievale', 'borgo', 'castello', 'antica via', 'via storica', 'archeologic', 'romano', 'etrusco'],

  tipo(testoCompleto) {
    const t = (testoCompleto || '').toLowerCase();
    if (this.PAROLE_RELIGIOSO.some(k => t.includes(k))) return 'religioso-storico';
    if (this.PAROLE_STORICO.some(k => t.includes(k))) return 'trekking-storico';
    return 'trekking-montagna';
  },

  difficolta(km, dislivelloSalita) {
    if (dislivelloSalita > 1000 || km > 30) return 'molto impegnativa';
    if (dislivelloSalita > 600 || km > 24) return 'impegnativa';
    if (dislivelloSalita > 250 || km > 15) return 'media';
    return 'facile';
  }
};

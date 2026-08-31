/* Ricerca e importazione di tracciati reali di cammini/sentieri già mappati su OpenStreetMap
   (relazioni "route=hiking"), tramite Overpass API. Molti cammini storici italiani ed europei
   sono mappati come percorso continuo su OSM: quando è così, possiamo scaricarne davvero la
   geometria, senza bisogno di scraping di altre piattaforme (Wikiloc, Komoot, ecc. non lo
   permettono). È un tracciato "migliore sforzo": la sequenza dei tratti viene ricostruita con
   un algoritmo di concatenazione per prossimità, quindi non è garantita al 100% come un vero GPX. */

const OSMTRACCE = {
  ENDPOINT: 'https://overpass-api.de/api/interpreter',

  // Cerca relazioni "route=hiking" (o "route=foot") il cui nome assomiglia al cammino cercato.
  // Restituisce un elenco di candidati (id, nome, rete, distretto/paese se noto).
  async cercaRelazioni(nomeCammino) {
    const nomeEscaped = nomeCammino.replace(/["\\]/g, '').trim();
    if (!nomeEscaped) return [];
    const query = `[out:json][timeout:25];
      (
        relation["route"~"hiking|foot"]["name"~"${nomeEscaped}",i];
      );
      out tags;`;
    const res = await fetch(this.ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: query
    });
    if (!res.ok) throw new Error(`OpenStreetMap (Overpass) ha risposto con errore ${res.status}.`);
    const data = await res.json();
    return (data.elements || [])
      .filter(el => el.tags && el.tags.name)
      .map(el => ({
        id: el.id,
        nome: el.tags.name,
        rete: el.tags.network || null,
        operatore: el.tags.operator || null
      }));
  },

  // Scarica la geometria completa di una relazione (tutti i suoi "way" membri con le coordinate)
  // e la ricompone in un'unica sequenza di punti concatenando i tratti per vicinanza.
  async importaRelazione(relId) {
    const query = `[out:json][timeout:50];
      relation(${relId});
      way(r)->.tratti;
      .tratti out geom;`;
    const res = await fetch(this.ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: query
    });
    if (!res.ok) throw new Error(`OpenStreetMap (Overpass) ha risposto con errore ${res.status}.`);
    const data = await res.json();

    const tratti = (data.elements || [])
      .filter(el => el.type === 'way' && el.geometry && el.geometry.length > 1)
      .map(el => el.geometry.map(g => ({ lat: g.lat, lon: g.lon })));

    if (tratti.length === 0) throw new Error('Nessuna geometria trovata per questa relazione OpenStreetMap.');

    const points = this._ricomponi(tratti);
    const stats = GPX.computeStats(points);
    return { points, stats };
  },

  // Concatena i tratti (ognuno una sequenza di punti) scegliendo ogni volta il tratto
  // rimanente più vicino all'estremità corrente, invertendolo se necessario.
  _ricomponi(tratti) {
    const rimanenti = tratti.slice();
    let catena = rimanenti.shift();
    while (rimanenti.length) {
      const fine = catena[catena.length - 1];
      let miglioreIdx = 0, miglioreInverti = false, miglioreDist = Infinity;
      rimanenti.forEach((t, i) => {
        const dInizio = GPX.haversine(fine, t[0]);
        const dFine = GPX.haversine(fine, t[t.length - 1]);
        if (dInizio < miglioreDist) { miglioreDist = dInizio; miglioreIdx = i; miglioreInverti = false; }
        if (dFine < miglioreDist) { miglioreDist = dFine; miglioreIdx = i; miglioreInverti = true; }
      });
      let prossimo = rimanenti.splice(miglioreIdx, 1)[0];
      if (miglioreInverti) prossimo = prossimo.slice().reverse();
      catena = catena.concat(prossimo);
    }
    return catena;
  },

  // Riduce il numero di punti per non appesantire troppo il salvataggio locale
  decima(points, max = 500) {
    if (points.length <= max) return points;
    const passo = points.length / max;
    const out = [];
    for (let i = 0; i < max; i++) out.push(points[Math.floor(i * passo)]);
    return out;
  }
};

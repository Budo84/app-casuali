/* Parsing di file GPX nel browser, senza dipendenze esterne */

const GPX = {
  parse(text) {
    const xml = new DOMParser().parseFromString(text, 'application/xml');
    const err = xml.querySelector('parsererror');
    if (err) throw new Error('File GPX non valido o corrotto.');

    // Preferisci il nome della traccia (trk > name); altrimenti quello dei metadati del file
    const trkNameEl = xml.querySelector('trk > name');
    const metaNameEl = xml.querySelector('metadata > name');
    const nameEl = trkNameEl || metaNameEl;
    let name = nameEl ? nameEl.textContent.trim() : 'Traccia senza nome';
    // Wikiloc antepone "Wikiloc - " al nome nei metadati: lo rimuoviamo per un titolo più pulito
    name = name.replace(/^Wikiloc\s*-\s*/i, '').trim() || 'Traccia senza nome';

    // Link alla pagina di origine (es. la pagina del percorso su Wikiloc), se presente
    const linkEl = xml.querySelector('metadata > link[href], trk > link[href]');
    const sourceUrl = linkEl ? linkEl.getAttribute('href') : null;

    const points = [];
    const trkpts = xml.querySelectorAll('trkpt, rtept');
    trkpts.forEach(pt => {
      const lat = parseFloat(pt.getAttribute('lat'));
      const lon = parseFloat(pt.getAttribute('lon'));
      const eleEl = pt.querySelector('ele');
      const ele = eleEl ? parseFloat(eleEl.textContent) : null;
      if (!isNaN(lat) && !isNaN(lon)) points.push({ lat, lon, ele });
    });

    if (points.length === 0) throw new Error('Nessun punto traccia trovato nel file GPX.');

    // Punti di interesse (waypoint): tappe intermedie, rifugi, fontane, chiese ecc.
    // segnalati da chi ha registrato la traccia (molto comuni nei GPX scaricati da Wikiloc)
    const waypoints = [];
    xml.querySelectorAll('wpt').forEach(wp => {
      const lat = parseFloat(wp.getAttribute('lat'));
      const lon = parseFloat(wp.getAttribute('lon'));
      if (isNaN(lat) || isNaN(lon)) return;
      const nomeEl = wp.querySelector('name');
      const descEl = wp.querySelector('desc');
      const cmtEl = wp.querySelector('cmt');
      waypoints.push({
        nome: nomeEl && nomeEl.textContent.trim() ? nomeEl.textContent.trim() : 'Punto di interesse',
        descrizione: (descEl && descEl.textContent.trim()) || (cmtEl && cmtEl.textContent.trim()) || '',
        lat, lon
      });
    });

    const stats = this.computeStats(points);
    return { name, points, stats, waypoints, sourceUrl };
  },

  computeStats(points) {
    let distanceKm = 0;
    let ascent = 0;
    let descent = 0;
    for (let i = 1; i < points.length; i++) {
      distanceKm += this.haversine(points[i - 1], points[i]);
      if (points[i].ele != null && points[i - 1].ele != null) {
        const diff = points[i].ele - points[i - 1].ele;
        if (diff > 0) ascent += diff; else descent += -diff;
      }
    }
    const elevations = points.filter(p => p.ele != null).map(p => p.ele);
    return {
      distanceKm: Math.round(distanceKm * 10) / 10,
      ascent: Math.round(ascent),
      descent: Math.round(descent),
      minEle: elevations.length ? Math.round(Math.min(...elevations)) : null,
      maxEle: elevations.length ? Math.round(Math.max(...elevations)) : null,
      numPoints: points.length
    };
  },

  haversine(a, b) {
    const R = 6371; // km
    const toRad = deg => deg * Math.PI / 180;
    const dLat = toRad(b.lat - a.lat);
    const dLon = toRad(b.lon - a.lon);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
};

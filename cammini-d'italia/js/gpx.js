/* Parsing di file GPX nel browser, senza dipendenze esterne */

const GPX = {
  parse(text) {
    const xml = new DOMParser().parseFromString(text, 'application/xml');
    const err = xml.querySelector('parsererror');
    if (err) throw new Error('File GPX non valido o corrotto.');

    const nameEl = xml.querySelector('trk > name, metadata > name');
    const name = nameEl ? nameEl.textContent.trim() : 'Traccia senza nome';

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

    const stats = this.computeStats(points);
    return { name, points, stats };
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

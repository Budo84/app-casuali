/* Gestione del database dei cammini: caricamento, cache locale, import/export */

const DB = {
  KEY_DB: 'cammini_db_v1',
  KEY_PLANS: 'cammini_plans_v1',
  KEY_GPX: 'cammini_gpx_v1',

  async load() {
    // 1. prova la copia salvata localmente (funziona offline e con import personalizzati)
    const local = localStorage.getItem(this.KEY_DB);
    if (local) {
      try { return JSON.parse(local); } catch (e) { /* copia corrotta, ricarica */ }
    }
    // 2. altrimenti scarica il file incluso nell'app
    const res = await fetch('data/db.json');
    const data = await res.json();
    localStorage.setItem(this.KEY_DB, JSON.stringify(data));
    return data;
  },

  async refreshFromFile() {
    // forza il ricaricamento dal file dell'app (utile dopo un aggiornamento dell'app)
    const res = await fetch('data/db.json', { cache: 'no-store' });
    const data = await res.json();
    localStorage.setItem(this.KEY_DB, JSON.stringify(data));
    return data;
  },

  importDb(jsonObj) {
    localStorage.setItem(this.KEY_DB, JSON.stringify(jsonObj));
  },

  getPlans() {
    try { return JSON.parse(localStorage.getItem(this.KEY_PLANS)) || []; }
    catch (e) { return []; }
  },
  savePlans(plans) {
    localStorage.setItem(this.KEY_PLANS, JSON.stringify(plans));
  },

  getGpxTracks() {
    try { return JSON.parse(localStorage.getItem(this.KEY_GPX)) || []; }
    catch (e) { return []; }
  },
  saveGpxTracks(tracks) {
    localStorage.setItem(this.KEY_GPX, JSON.stringify(tracks));
  },

  exportUserData() {
    return {
      esportato: new Date().toISOString(),
      itinerari: this.getPlans(),
      tracceGpx: this.getGpxTracks()
    };
  },
  importUserData(obj) {
    if (obj.itinerari) this.savePlans(obj.itinerari);
    if (obj.tracceGpx) this.saveGpxTracks(obj.tracceGpx);
  },
  resetUserData() {
    localStorage.removeItem(this.KEY_PLANS);
    localStorage.removeItem(this.KEY_GPX);
  }
};

/* Gestione del database dei cammini: caricamento, cache locale, import/export */

const DB = {
  KEY_DB: 'cammini_db_v1',
  KEY_CUSTOM: 'cammini_db_custom_v1', // impostato a '1' solo se l'utente importa un database personalizzato
  KEY_PLANS: 'cammini_plans_v1',
  KEY_GPX: 'cammini_gpx_v1',

  async load() {
    const isCustom = localStorage.getItem(this.KEY_CUSTOM) === '1';
    let local = null;
    try { local = JSON.parse(localStorage.getItem(this.KEY_DB)); } catch (e) { local = null; }

    // Se l'utente ha importato un database personalizzato, rispettalo sempre e non sovrascriverlo
    if (isCustom && local) return local;

    // Altrimenti confronta la versione del file incluso nell'app con quella salvata:
    // così chi ha già usato l'app riceve automaticamente nuovi cammini aggiunti negli aggiornamenti.
    try {
      const res = await fetch('data/db.json', { cache: 'no-store' });
      const fresh = await res.json();
      if (!local || (fresh.versione || 0) > (local.versione || 0)) {
        localStorage.setItem(this.KEY_DB, JSON.stringify(fresh));
        return fresh;
      }
      return local;
    } catch (e) {
      // offline al primo avvio o rete assente: usa la copia salvata se c'è
      if (local) return local;
      throw e;
    }
  },

  async refreshFromFile() {
    // forza il ricaricamento dal file dell'app, ignorando eventuale database personalizzato importato
    const res = await fetch('data/db.json', { cache: 'no-store' });
    const data = await res.json();
    localStorage.setItem(this.KEY_DB, JSON.stringify(data));
    localStorage.removeItem(this.KEY_CUSTOM);
    return data;
  },

  importDb(jsonObj) {
    localStorage.setItem(this.KEY_DB, JSON.stringify(jsonObj));
    localStorage.setItem(this.KEY_CUSTOM, '1');
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

  /* ---- Cammini personalizzati creati dall'utente a partire da tracce GPX ----
     Salvati separatamente dal database ufficiale, così sopravvivono agli
     aggiornamenti del database (vedi load()) e possono essere esportati/importati
     insieme agli altri dati personali. */
  KEY_CUSTOM_CAMMINI: 'cammini_custom_v1',

  getCustomCammini() {
    try { return JSON.parse(localStorage.getItem(this.KEY_CUSTOM_CAMMINI)) || []; }
    catch (e) { return []; }
  },
  saveCustomCammini(list) {
    localStorage.setItem(this.KEY_CUSTOM_CAMMINI, JSON.stringify(list));
  },
  addCustomCammino(cammino) {
    const list = this.getCustomCammini();
    list.push(cammino);
    this.saveCustomCammini(list);
    return list;
  },
  aggiungiTappaACustomCammino(camminoId, tappa) {
    const list = this.getCustomCammini();
    const c = list.find(x => x.id === camminoId);
    if (!c) return list;
    tappa.n = c.tappe.length + 1;
    c.tappe.push(tappa);
    this.saveCustomCammini(list);
    return list;
  },
  eliminaCustomCammino(camminoId) {
    const list = this.getCustomCammini().filter(c => c.id !== camminoId);
    this.saveCustomCammini(list);
    return list;
  },

  exportUserData() {
    return {
      esportato: new Date().toISOString(),
      itinerari: this.getPlans(),
      tracceGpx: this.getGpxTracks(),
      camminiPersonalizzati: this.getCustomCammini()
    };
  },
  importUserData(obj) {
    if (obj.itinerari) this.savePlans(obj.itinerari);
    if (obj.tracceGpx) this.saveGpxTracks(obj.tracceGpx);
    if (obj.camminiPersonalizzati) this.saveCustomCammini(obj.camminiPersonalizzati);
  },
  resetUserData() {
    localStorage.removeItem(this.KEY_PLANS);
    localStorage.removeItem(this.KEY_GPX);
    localStorage.removeItem(this.KEY_CUSTOM_CAMMINI);
  }
};

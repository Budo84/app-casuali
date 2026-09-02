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

  /* ---- Tracciati reali importati da OpenStreetMap per un cammino (ufficiale o personalizzato) ----
     Salvati a parte, associati all'id del cammino, così sopravvivono agli aggiornamenti del database. */
  KEY_TRACCIATI_OSM: 'cammini_tracciati_osm_v1',

  getTracciatiOsm() {
    try { return JSON.parse(localStorage.getItem(this.KEY_TRACCIATI_OSM)) || {}; }
    catch (e) { return {}; }
  },
  getTracciatoOsm(camminoId) {
    return this.getTracciatiOsm()[camminoId] || null;
  },
  saveTracciatoOsm(camminoId, dati) {
    const tutti = this.getTracciatiOsm();
    tutti[camminoId] = dati;
    localStorage.setItem(this.KEY_TRACCIATI_OSM, JSON.stringify(tutti));
  },
  eliminaTracciatoOsm(camminoId) {
    const tutti = this.getTracciatiOsm();
    delete tutti[camminoId];
    localStorage.setItem(this.KEY_TRACCIATI_OSM, JSON.stringify(tutti));
  },

  /* ---- Impostazioni personali (passo di marcia, per il calcolo del tempo di percorrenza) ---- */
  KEY_IMPOSTAZIONI: 'cammini_impostazioni_v1',
  DEFAULT_IMPOSTAZIONI: { velocitaKmH: 4, minutiPer100mSalita: 12 },

  getImpostazioni() {
    try { return { ...this.DEFAULT_IMPOSTAZIONI, ...(JSON.parse(localStorage.getItem(this.KEY_IMPOSTAZIONI)) || {}) }; }
    catch (e) { return { ...this.DEFAULT_IMPOSTAZIONI }; }
  },
  saveImpostazioni(imp) {
    localStorage.setItem(this.KEY_IMPOSTAZIONI, JSON.stringify(imp));
  },

  /* ---- Diario di viaggio: note (ed eventuale foto) per singola tappa ---- */
  KEY_DIARIO: 'cammini_diario_v1',

  getDiario() {
    try { return JSON.parse(localStorage.getItem(this.KEY_DIARIO)) || {}; }
    catch (e) { return {}; }
  },
  getVociDiario(camminoId, tappaN) {
    const tutto = this.getDiario();
    return tutto[`${camminoId}__${tappaN}`] || [];
  },
  aggiungiVoceDiario(camminoId, tappaN, voce) {
    const tutto = this.getDiario();
    const chiave = `${camminoId}__${tappaN}`;
    tutto[chiave] = tutto[chiave] || [];
    tutto[chiave].push(voce);
    localStorage.setItem(this.KEY_DIARIO, JSON.stringify(tutto));
  },
  eliminaVoceDiario(camminoId, tappaN, indice) {
    const tutto = this.getDiario();
    const chiave = `${camminoId}__${tappaN}`;
    if (!tutto[chiave]) return;
    tutto[chiave].splice(indice, 1);
    localStorage.setItem(this.KEY_DIARIO, JSON.stringify(tutto));
  },

  /* ---- Checklist zaino (voci con stato spuntato/non spuntato) ---- */
  KEY_CHECKLIST: 'cammini_checklist_v1',
  CHECKLIST_DEFAULT: [
    'Scarpe da trekking rodate', 'Zaino con copertura antipioggia', 'Bastoncini da trekking',
    'Borraccia o sacca idrica', 'Kit primo soccorso', 'Crema solare e cappello',
    'Giacca antipioggia', 'Ricambio calzini', 'Power bank e cavo di ricarica',
    'Documenti e credenziale del pellegrino (se richiesta)', 'Torcia frontale', 'Coltellino multiuso'
  ],

  getChecklist() {
    try {
      const salvata = JSON.parse(localStorage.getItem(this.KEY_CHECKLIST));
      if (salvata) return salvata;
    } catch (e) { /* usa quella di default */ }
    return this.CHECKLIST_DEFAULT.map(testo => ({ testo, fatto: false }));
  },
  saveChecklist(lista) {
    localStorage.setItem(this.KEY_CHECKLIST, JSON.stringify(lista));
  },

  /* ---- Tappe completate (per le statistiche personali) ---- */
  KEY_COMPLETATE: 'cammini_completate_v1',

  getTappeCompletate() {
    try { return JSON.parse(localStorage.getItem(this.KEY_COMPLETATE)) || {}; }
    catch (e) { return {}; }
  },
  isTappaCompletata(camminoId, tappaN) {
    return !!this.getTappeCompletate()[`${camminoId}__${tappaN}`];
  },
  toggleTappaCompletata(camminoId, tappaN, valore) {
    const tutte = this.getTappeCompletate();
    const chiave = `${camminoId}__${tappaN}`;
    if (valore) tutte[chiave] = { data: new Date().toISOString() };
    else delete tutte[chiave];
    localStorage.setItem(this.KEY_COMPLETATE, JSON.stringify(tutte));
  },

  /* ---- Tema chiaro/scuro (preferenza di visualizzazione, non inclusa nel reset dati) ---- */
  KEY_TEMA: 'cammini_tema_v1',
  getTema() { return localStorage.getItem(this.KEY_TEMA) || 'light'; },
  saveTema(tema) { localStorage.setItem(this.KEY_TEMA, tema); },

  /* ---- Cammini preferiti (lista dei desideri) ---- */
  KEY_PREFERITI: 'cammini_preferiti_v1',
  getPreferiti() {
    try { return JSON.parse(localStorage.getItem(this.KEY_PREFERITI)) || []; }
    catch (e) { return []; }
  },
  isPreferito(camminoId) { return this.getPreferiti().includes(camminoId); },
  togglePreferito(camminoId) {
    let lista = this.getPreferiti();
    if (lista.includes(camminoId)) lista = lista.filter(id => id !== camminoId);
    else lista.push(camminoId);
    localStorage.setItem(this.KEY_PREFERITI, JSON.stringify(lista));
    return lista.includes(camminoId);
  },

  /* ---- Giochi per cammino (quiz, memory, caccia al tesoro) e punti/medaglie collegate ---- */
  KEY_GIOCHI: 'cammini_giochi_v1',
  getGiochi() {
    try { return JSON.parse(localStorage.getItem(this.KEY_GIOCHI)) || {}; }
    catch (e) { return {}; }
  },
  getGiocoCammino(camminoId) {
    const tutti = this.getGiochi();
    return tutti[camminoId] || { punti: 0, quiz: false, memory: false, caccia: false, cacciaSpuntati: [] };
  },
  aggiornaGiocoCammino(camminoId, patchFn) {
    const tutti = this.getGiochi();
    const attuale = tutti[camminoId] || { punti: 0, quiz: false, memory: false, caccia: false, cacciaSpuntati: [] };
    tutti[camminoId] = patchFn({ ...attuale });
    localStorage.setItem(this.KEY_GIOCHI, JSON.stringify(tutti));
    return tutti[camminoId];
  },
  puntiGiocoTotali() {
    const tutti = this.getGiochi();
    return Object.values(tutti).reduce((s, g) => s + (g.punti || 0), 0);
  },

  /* ---- Gioco platform: personaggio scelto, livelli completati, forzieri aperti, medaglie già mostrate ---- */
  KEY_PLATFORM: 'cammini_platform_v1',
  getPlatformState() {
    try { return JSON.parse(localStorage.getItem(this.KEY_PLATFORM)) || { personaggio: 0, livelli: {} }; }
    catch (e) { return { personaggio: 0, livelli: {} }; }
  },
  savePlatformState(stato) { localStorage.setItem(this.KEY_PLATFORM, JSON.stringify(stato)); },
  segnaLivelloCompletato(camminoId, tappaN, stelle) {
    const stato = this.getPlatformState();
    const chiave = `${camminoId}__${tappaN}`;
    const precedente = stato.livelli[chiave];
    if (!precedente || stelle > precedente.stelle) {
      stato.livelli[chiave] = { stelle, data: new Date().toISOString() };
    }
    this.savePlatformState(stato);
  },
  getStelleLivello(camminoId, tappaN) {
    const stato = this.getPlatformState();
    const v = stato.livelli[`${camminoId}__${tappaN}`];
    return v ? v.stelle : 0;
  },
  sceglierPersonaggio(indice) {
    const stato = this.getPlatformState();
    stato.personaggio = indice;
    this.savePlatformState(stato);
  },

  KEY_FORZIERI: 'cammini_forzieri_v1',
  getForzieriAperti() {
    try { return JSON.parse(localStorage.getItem(this.KEY_FORZIERI)) || []; }
    catch (e) { return []; }
  },
  apriForziere(soglia) {
    const aperti = this.getForzieriAperti();
    if (!aperti.includes(soglia)) { aperti.push(soglia); localStorage.setItem(this.KEY_FORZIERI, JSON.stringify(aperti)); }
  },

  KEY_BADGE_VISTI: 'cammini_badge_visti_v1',
  getBadgeVisti() {
    try { return JSON.parse(localStorage.getItem(this.KEY_BADGE_VISTI)) || []; }
    catch (e) { return []; }
  },
  segnaBadgeVisto(id) {
    const visti = this.getBadgeVisti();
    if (!visti.includes(id)) { visti.push(id); localStorage.setItem(this.KEY_BADGE_VISTI, JSON.stringify(visti)); }
  },

  exportUserData() {
    return {
      esportato: new Date().toISOString(),
      itinerari: this.getPlans(),
      tracceGpx: this.getGpxTracks(),
      camminiPersonalizzati: this.getCustomCammini(),
      tracciatiOsm: this.getTracciatiOsm(),
      impostazioni: this.getImpostazioni(),
      diario: this.getDiario(),
      checklist: this.getChecklist(),
      tappeCompletate: this.getTappeCompletate(),
      preferiti: this.getPreferiti(),
      giochi: this.getGiochi(),
      platform: this.getPlatformState(),
      forzieri: this.getForzieriAperti(),
      badgeVisti: this.getBadgeVisti()
    };
  },
  importUserData(obj) {
    if (obj.itinerari) this.savePlans(obj.itinerari);
    if (obj.tracceGpx) this.saveGpxTracks(obj.tracceGpx);
    if (obj.camminiPersonalizzati) this.saveCustomCammini(obj.camminiPersonalizzati);
    if (obj.tracciatiOsm) localStorage.setItem(this.KEY_TRACCIATI_OSM, JSON.stringify(obj.tracciatiOsm));
    if (obj.impostazioni) this.saveImpostazioni(obj.impostazioni);
    if (obj.diario) localStorage.setItem(this.KEY_DIARIO, JSON.stringify(obj.diario));
    if (obj.checklist) this.saveChecklist(obj.checklist);
    if (obj.tappeCompletate) localStorage.setItem(this.KEY_COMPLETATE, JSON.stringify(obj.tappeCompletate));
    if (obj.preferiti) localStorage.setItem(this.KEY_PREFERITI, JSON.stringify(obj.preferiti));
    if (obj.giochi) localStorage.setItem(this.KEY_GIOCHI, JSON.stringify(obj.giochi));
    if (obj.platform) this.savePlatformState(obj.platform);
    if (obj.forzieri) localStorage.setItem(this.KEY_FORZIERI, JSON.stringify(obj.forzieri));
    if (obj.badgeVisti) localStorage.setItem(this.KEY_BADGE_VISTI, JSON.stringify(obj.badgeVisti));
  },
  resetUserData() {
    localStorage.removeItem(this.KEY_PLANS);
    localStorage.removeItem(this.KEY_GPX);
    localStorage.removeItem(this.KEY_CUSTOM_CAMMINI);
    localStorage.removeItem(this.KEY_TRACCIATI_OSM);
    localStorage.removeItem(this.KEY_IMPOSTAZIONI);
    localStorage.removeItem(this.KEY_DIARIO);
    localStorage.removeItem(this.KEY_CHECKLIST);
    localStorage.removeItem(this.KEY_COMPLETATE);
    localStorage.removeItem(this.KEY_PREFERITI);
    localStorage.removeItem(this.KEY_GIOCHI);
    localStorage.removeItem(this.KEY_PLATFORM);
    localStorage.removeItem(this.KEY_FORZIERI);
    localStorage.removeItem(this.KEY_BADGE_VISTI);
    localStorage.removeItem('cammini_strutture_v1');
    localStorage.removeItem('cammini_acqua_v1');
  }
};

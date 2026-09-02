/* Giochi generati "ad hoc" per ogni cammino, usando i dati reali del cammino stesso
   (tappe, km, regioni, difficoltà, punti di interesse): non sono contenuti statici uguali
   per tutti, ma cambiano cammino per cammino. Pensati per rendere l'app più coinvolgente
   anche per i bambini che partecipano al cammino. */

const GIOCHI = {
  PUNTI_RISPOSTA_QUIZ: 10,
  PUNTI_MEMORY: 20,
  PUNTI_OGGETTO_CACCIA: 5,

  _mescola(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  },

  /* ---------- Quiz del cammino: 5 domande costruite sui dati reali del cammino ---------- */
  generaQuiz(c) {
    const domande = [];
    const tappe = c.tappe;

    // 1. Numero di tappe
    const nTappe = tappe.length;
    domande.push(this._domandaNumerica(
      `Quante tappe ha "${c.nome}"?`, nTappe, [1, -1, 2]
    ));

    // 2. Km totali (arrotondati)
    const kmTot = Math.round(tappe.reduce((s, t) => s + (t.km || 0), 0));
    domande.push(this._domandaNumerica(
      `Quanti km sono in totale (circa)?`, kmTot, [10, -10, 20], ' km'
    ));

    // 3. Tappa più lunga
    let idxMax = 0;
    tappe.forEach((t, i) => { if (t.km > tappe[idxMax].km) idxMax = i; });
    const tappaPiuLunga = tappe[idxMax];
    const altreTappeOpz = this._mescola(tappe.filter((t, i) => i !== idxMax)).slice(0, 3);
    if (altreTappeOpz.length >= 2) {
      const opzioni = this._mescola([
        `${tappaPiuLunga.da} → ${tappaPiuLunga.a}`,
        ...altreTappeOpz.map(t => `${t.da} → ${t.a}`)
      ]);
      domande.push({
        domanda: 'Qual è la tappa più lunga di questo cammino?',
        opzioni,
        corretta: opzioni.indexOf(`${tappaPiuLunga.da} → ${tappaPiuLunga.a}`)
      });
    }

    // 4. Regione
    const regioneCorretta = c.regioni[0];
    const altreRegioni = this._mescola(
      ['Toscana', 'Umbria', 'Lazio', 'Puglia', 'Veneto', 'Liguria', 'Emilia-Romagna', 'Piemonte']
        .filter(r => !c.regioni.includes(r))
    ).slice(0, 3);
    const opzioniRegione = this._mescola([regioneCorretta, ...altreRegioni]);
    domande.push({
      domanda: `In quale regione (tra queste) passa "${c.nome}"?`,
      opzioni: opzioniRegione,
      corretta: opzioniRegione.indexOf(regioneCorretta)
    });

    // 5. Difficoltà generale
    const diffCorretta = c.difficoltaGenerale;
    const opzioniDiff = this._mescola(
      Array.from(new Set([diffCorretta, 'facile', 'media', 'impegnativa', 'molto impegnativa'])).slice(0, 4)
    );
    domande.push({
      domanda: `Qual è la difficoltà generale di questo cammino?`,
      opzioni: opzioniDiff,
      corretta: opzioniDiff.indexOf(diffCorretta)
    });

    // 6. Punto di interesse (se disponibile per qualche tappa) — domanda bonus
    const tappaConPoi = tappe.find(t => t.puntiInteresse && t.puntiInteresse.length);
    if (tappaConPoi) {
      const poiCorretto = tappaConPoi.puntiInteresse[0].nome;
      const altriPoi = this._mescola(
        tappe.flatMap(t => (t.puntiInteresse || []).map(p => p.nome)).filter(n => n !== poiCorretto)
      ).slice(0, 3);
      if (altriPoi.length >= 2) {
        const opzioniPoi = this._mescola([poiCorretto, ...altriPoi]);
        domande.push({
          domanda: `Cosa si trova lungo la tappa "${tappaConPoi.da} → ${tappaConPoi.a}"?`,
          opzioni: opzioniPoi,
          corretta: opzioniPoi.indexOf(poiCorretto)
        });
      }
    }

    return this._mescola(domande).slice(0, 5);
  },

  _domandaNumerica(testo, corretto, scarti, suffisso = '') {
    let candidati = [corretto, ...scarti.map(s => corretto + s)].map(n => Math.max(1, n));
    const uniche = Array.from(new Set(candidati));
    while (uniche.length < 4) uniche.push(uniche[uniche.length - 1] + 3 + uniche.length);
    const scelte = uniche.slice(0, 4);
    const opzioni = this._mescola(scelte.map(n => n + suffisso));
    return { domanda: testo, opzioni, corretta: opzioni.indexOf(corretto + suffisso) };
  },

  /* ---------- Memory delle tappe: abbina partenza e arrivo di ogni tappa ---------- */
  generaMemory(c) {
    const tappeUsabili = c.tappe.slice(0, 6); // massimo 6 coppie per tenere il gioco gestibile
    const carte = [];
    tappeUsabili.forEach(t => {
      carte.push({ coppia: t.n, testo: t.da, tipo: 'da' });
      carte.push({ coppia: t.n, testo: t.a, tipo: 'a' });
    });
    return this._mescola(carte);
  },

  /* ---------- Caccia al tesoro: cose da individuare lungo il cammino ---------- */
  generaCaccia(c) {
    const oggetti = [];
    // Usa i punti di interesse reali, se presenti
    c.tappe.forEach(t => {
      (t.puntiInteresse || []).forEach(p => oggetti.push(`📍 ${p.nome}`));
    });
    // Aggiunge voci generiche legate al tipo di cammino, per completare la lista
    const generiche = c.tipo === 'religioso-storico' || c.tipo === 'cammino-storico-religioso'
      ? ['⛪ Una chiesa o cappella', '🕊️ Una statua religiosa', '🔔 Una campana', '🌳 Un albero secolare']
      : ['🏔️ Un panorama con più valli', '🐐 Un animale al pascolo', '💧 Una fontana o sorgente', '🪨 Una roccia curiosa'];
    generiche.forEach(g => { if (oggetti.length < 8) oggetti.push(g); });
    return this._mescola(oggetti).slice(0, 6);
  }
};

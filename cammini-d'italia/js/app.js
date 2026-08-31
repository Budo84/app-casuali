let CAMMINI = null;
let currentDettaglioId = null;
let leafletMap = null;
let leafletLayer = null;

const $ = sel => document.querySelector(sel);
const $$ = sel => Array.from(document.querySelectorAll(sel));

/* ---------- Navigazione tab ---------- */
function switchTab(name) {
  $$('.tab').forEach(t => {
    const active = t.dataset.tab === name;
    t.classList.toggle('active', active);
    t.setAttribute('aria-selected', active);
  });
  $$('.panel').forEach(p => p.classList.remove('active'));
  $('#panel-' + name).classList.add('active');
}
$$('.tab').forEach(t => t.addEventListener('click', () => switchTab(t.dataset.tab)));

/* ---------- Stato connessione ---------- */
function updateConnStatus() {
  const online = navigator.onLine;
  $('#connDot').classList.toggle('offline', !online);
  $('#connText').textContent = online ? 'Online' : 'Offline (dati locali)';
}
window.addEventListener('online', updateConnStatus);
window.addEventListener('offline', updateConnStatus);

/* ---------- Rendering elenco cammini ---------- */
function difficoltaBadge(diff) {
  const cls = diff && diff.includes('facile') ? 'diff-facile' : diff && diff.includes('impegnativa') ? 'diff-impegnativa' : 'diff-media';
  return `<span class="badge ${cls}">${diff || 'media'}</span>`;
}

function totaleKm(cammino) {
  return cammino.tappe.reduce((s, t) => s + (t.km || 0), 0);
}

// Icona SVG semplice associata al tipo di cammino (nessuna immagine esterna: tutto inline, funziona offline)
const OPZIONI_TIPO_CAMMINO = [
  ['trekking-montagna', 'Trekking di montagna'],
  ['religioso-storico', 'Cammino storico-religioso'],
  ['trekking-storico', 'Trekking storico-culturale'],
  ['personalizzato', 'Altro / personalizzato']
];
const OPZIONI_DIFFICOLTA = ['facile', 'media', 'impegnativa', 'molto impegnativa'];

const ICONE_TIPO = {
  'trekking-montagna': '<svg viewBox="0 0 24 24"><path d="M3 20L9 8l4 6 2-3 6 9H3z"/><circle cx="18" cy="6" r="2"/></svg>',
  'cammino-storico-religioso': '<svg viewBox="0 0 24 24"><path d="M12 2v20M6 7h12M8 12h8"/></svg>',
  'religioso-storico': '<svg viewBox="0 0 24 24"><path d="M12 2v20M6 7h12M8 12h8"/></svg>',
  'trekking-storico': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 6v6l4 2"/></svg>',
  'personalizzato': '<svg viewBox="0 0 24 24"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  'default': '<svg viewBox="0 0 24 24"><path d="M4 18l6-12 4 7 2-4 4 9H4z"/></svg>'
};
function iconaTipo(tipo) {
  return ICONE_TIPO[tipo] || ICONE_TIPO.default;
}
function classeTipo(tipo) {
  return ICONE_TIPO[tipo] ? `tipo-${tipo}` : 'tipo-default';
}

function renderLista() {
  const q = ($('#searchInput').value || '').toLowerCase();
  const tipoFiltro = $('#filterTipo').value;
  const list = $('#camminiList');
  list.innerHTML = '';

  if (!CAMMINI || !CAMMINI.cammini) {
    list.innerHTML = '<p class="empty-note">Database non disponibile: prova a ricaricare la pagina.</p>';
    return;
  }

  const filtrati = CAMMINI.cammini.filter(c => {
    const testo = (c.nome + ' ' + c.regioni.join(' ') + ' ' + c.descrizione).toLowerCase();
    const okTesto = !q || testo.includes(q);
    const okTipo = !tipoFiltro || c.tipo === tipoFiltro || c.difficoltaGenerale === tipoFiltro;
    return okTesto && okTipo;
  });

  if (filtrati.length === 0) {
    list.innerHTML = '<p class="empty-note">Nessun cammino trovato con questi filtri.</p>';
    return;
  }

  filtrati.forEach(c => {
    const tile = document.createElement('div');
    tile.className = 'cammino-tile';
    tile.innerHTML = `
      <div class="tile-visual ${classeTipo(c.tipo)}">
        ${iconaTipo(c.tipo)}
        <span class="tile-badge">${difficoltaBadge(c.difficoltaGenerale)}</span>
        ${c.personalizzato ? '<span class="tile-mine">tuo</span>' : ''}
      </div>
      <div class="tile-body">
        <div class="tile-name">${c.nome}</div>
        <div class="tile-region">${c.regioni.join(' · ')}</div>
        <div class="tile-stats">
          <span>${totaleKm(c)} km</span>
          <span>${c.tappe.length} tappe</span>
        </div>
      </div>
    `;
    tile.addEventListener('click', () => apriDettaglio(c.id));
    list.appendChild(tile);
  });
}

/* ---------- Dettaglio cammino ---------- */
function apriDettaglio(id) {
  currentDettaglioId = id;
  const c = CAMMINI.cammini.find(x => x.id === id);
  if (!c) return;
  const cont = $('#dettaglioContent');
  cont.innerHTML = `
    <div class="dett-header">
      <div class="cc-region">${c.regioni.join(' · ')} — ${difficoltaBadge(c.difficoltaGenerale)} ${c.personalizzato ? '<span class="badge">tuo cammino</span>' : ''}</div>
      <h2 class="hero-title" style="color:var(--pine)">${c.nome}</h2>
      <p class="section-sub">${c.descrizione}</p>
      <p class="section-sub"><strong>Segnaletica:</strong> ${c.segnaletica || 'verificare sul sito ufficiale'}</p>
    </div>
    <div class="dett-links">
      ${c.sitoUfficiale ? `<a href="${c.sitoUfficiale}" target="_blank" rel="noopener">Sito ufficiale ↗</a>` : ''}
      ${c.wikilocRicerca ? `<a href="${c.wikilocRicerca}" target="_blank" rel="noopener">${c.personalizzato ? 'Vedi la traccia originale ↗' : 'Cerca tracce su Wikiloc ↗'}</a>` : ''}
    </div>
    <div class="cc-stats" style="margin-bottom:1rem">
      <span>${totaleKm(c)} km totali</span>
      <span>${c.tappe.length} tappe</span>
    </div>
    <div class="stage-list">
      ${c.tappe.map(t => `
        <div class="stage-row">
          <div class="stage-n">${t.n}</div>
          <div class="stage-body">
            <div class="stage-route">${t.da} → ${t.a}</div>
            <div class="stage-meta">${t.km} km · ↑${t.dislivelloSalita}m ↓${t.dislivelloDiscesa}m · ${t.difficolta}</div>
            <div class="stage-note">${t.note || ''}</div>
            ${t.puntiInteresse && t.puntiInteresse.length ? `
              <div class="poi-list poi-list-compact">
                ${t.puntiInteresse.map(w => `<div class="poi-item"><span class="poi-nome">📍 ${w.nome}</span>${w.descrizione ? `<span class="poi-desc">${w.descrizione}</span>` : ''}</div>`).join('')}
              </div>
            ` : ''}
            ${t.coordA ? `
              <div class="stage-strutture">
                <button class="btn-strutture" data-cammino="${c.id}" data-tappa="${t.n}">🏠 Cerca strutture vicino all'arrivo</button>
                <div class="strutture-risultati" id="strutture-${c.id}-${t.n}"></div>
              </div>
            ` : ''}
          </div>
        </div>
      `).join('')}
    </div>
    ${c.personalizzato ? `
      <div class="dett-azioni-custom">
        <button class="btn-secondary" id="btnModificaCammino">✏️ Modifica</button>
        <button class="btn-danger" id="btnEliminaCammino">Elimina questo cammino personalizzato</button>
      </div>
    ` : ''}
    <div id="modificaCamminoWrap"></div>
  `;
  $$('.panel').forEach(p => p.classList.remove('active'));
  $('#panel-dettaglio').classList.add('active');

  // Mostra eventuali risultati già salvati in precedenza (offline-friendly)
  c.tappe.forEach(t => {
    const salvate = STRUTTURE.getSalvate(c.id, t.n);
    if (salvate) renderStrutture(c.id, t.n, salvate.strutture, salvate.cercatoIl, salvate.raggio);
  });

  cont.querySelectorAll('.btn-strutture').forEach(btn => {
    btn.addEventListener('click', () => cercaStruttureTappa(btn.dataset.cammino, parseInt(btn.dataset.tappa, 10)));
  });

  if (c.personalizzato) {
    $('#btnEliminaCammino').addEventListener('click', () => {
      if (confirm(`Eliminare "${c.nome}" dalle tue tile? L'azione non è reversibile.`)) {
        DB.eliminaCustomCammino(c.id);
        integraCamminiPersonalizzati();
        switchTab('esplora');
        renderLista();
      }
    });
    $('#btnModificaCammino').addEventListener('click', () => renderModificaCammino(c));
  }
}
$('#backFromDettaglio').addEventListener('click', () => switchTab('esplora'));

/* ---------- Modifica di un cammino personalizzato (tutti i campi sono modificabili) ---------- */
function renderModificaCammino(c) {
  const wrap = $('#modificaCamminoWrap');
  wrap.innerHTML = `
    <div class="edit-box">
      <h3 class="section-title small">Modifica cammino</h3>
      <div class="planner-form">
        <label>Nome del cammino
          <input type="text" id="editNome" value="${c.nome.replace(/"/g, '&quot;')}">
        </label>
        <label>Tipologia
          <select id="editTipo">
            ${OPZIONI_TIPO_CAMMINO.map(([v, l]) => `<option value="${v}" ${v === c.tipo ? 'selected' : ''}>${l}</option>`).join('')}
          </select>
        </label>
        <label>Zona / regione
          <input type="text" id="editRegione" value="${(c.regioni || []).join(', ').replace(/"/g, '&quot;')}">
        </label>
        <label>Difficoltà generale
          <select id="editDifficolta">
            ${OPZIONI_DIFFICOLTA.map(v => `<option value="${v}" ${v === c.difficoltaGenerale ? 'selected' : ''}>${v}</option>`).join('')}
          </select>
        </label>
        <label>Descrizione
          <input type="text" id="editDescrizione" value="${(c.descrizione || '').replace(/"/g, '&quot;')}">
        </label>
      </div>

      <h4 class="section-title small" style="margin-top:1rem">Tappe</h4>
      ${c.tappe.map((t, i) => `
        <div class="edit-tappa">
          <div class="edit-tappa-n">${t.n}</div>
          <div class="edit-tappa-fields">
            <input type="text" class="edit-t-da" data-i="${i}" value="${t.da.replace(/"/g, '&quot;')}" placeholder="Partenza">
            <span>→</span>
            <input type="text" class="edit-t-a" data-i="${i}" value="${t.a.replace(/"/g, '&quot;')}" placeholder="Arrivo">
            <input type="number" class="edit-t-km" data-i="${i}" value="${t.km}" step="0.1" min="0" title="km">
            <select class="edit-t-diff" data-i="${i}">
              ${OPZIONI_DIFFICOLTA.map(v => `<option value="${v}" ${v === t.difficolta ? 'selected' : ''}>${v}</option>`).join('')}
            </select>
          </div>
        </div>
      `).join('')}

      <div class="edit-azioni">
        <button class="btn-primary" id="btnSalvaModifiche">Salva modifiche</button>
        <button class="btn-secondary" id="btnAnnullaModifiche">Annulla</button>
      </div>
    </div>
  `;

  $('#btnAnnullaModifiche').addEventListener('click', () => { wrap.innerHTML = ''; });

  $('#btnSalvaModifiche').addEventListener('click', () => {
    const list = DB.getCustomCammini();
    const target = list.find(x => x.id === c.id);
    if (!target) return;

    target.nome = ($('#editNome').value || target.nome).trim();
    target.tipo = $('#editTipo').value;
    target.regioni = ($('#editRegione').value || 'Personalizzato').split(',').map(s => s.trim()).filter(Boolean);
    target.difficoltaGenerale = $('#editDifficolta').value;
    target.descrizione = $('#editDescrizione').value.trim();

    target.tappe.forEach((t, i) => {
      const da = wrap.querySelector(`.edit-t-da[data-i="${i}"]`);
      const a = wrap.querySelector(`.edit-t-a[data-i="${i}"]`);
      const km = wrap.querySelector(`.edit-t-km[data-i="${i}"]`);
      const diff = wrap.querySelector(`.edit-t-diff[data-i="${i}"]`);
      if (da) t.da = da.value.trim() || t.da;
      if (a) t.a = a.value.trim() || t.a;
      if (km) t.km = parseFloat(km.value) || t.km;
      if (diff) t.difficolta = diff.value;
    });

    DB.saveCustomCammini(list);
    integraCamminiPersonalizzati();
    renderLista();
    apriDettaglio(c.id);
  });
}

/* ---------- Ricerca strutture ricettive per tappa ---------- */
async function cercaStruttureTappa(camminoId, tappaN) {
  const c = CAMMINI.cammini.find(x => x.id === camminoId);
  const t = c.tappe.find(x => x.n === tappaN);
  const contDiv = $(`#strutture-${camminoId}-${tappaN}`);
  const btn = document.querySelector(`.btn-strutture[data-cammino="${camminoId}"][data-tappa="${tappaN}"]`);

  if (!navigator.onLine) {
    contDiv.innerHTML = '<p class="empty-note">Sei offline: mostro solo eventuali risultati già salvati in precedenza.</p>';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Ricerca in corso…';
  contDiv.innerHTML = '<p class="empty-note">Interrogo OpenStreetMap (Overpass API)…</p>';

  try {
    const risultati = await STRUTTURE.cerca(camminoId, t);
    renderStrutture(camminoId, tappaN, risultati, new Date().toISOString(), STRUTTURE.RAGGIO_DEFAULT);
  } catch (err) {
    contDiv.innerHTML = `<p class="empty-note">Errore nella ricerca: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🏠 Cerca strutture vicino all\'arrivo';
  }
}

function renderStrutture(camminoId, tappaN, strutture, cercatoIl, raggio) {
  const contDiv = $(`#strutture-${camminoId}-${tappaN}`);
  if (!contDiv) return;
  const dataStr = cercatoIl ? new Date(cercatoIl).toLocaleDateString('it-IT') : '';
  if (!strutture || strutture.length === 0) {
    contDiv.innerHTML = `<p class="empty-note">Nessuna struttura trovata entro ${raggio || STRUTTURE.RAGGIO_DEFAULT}m su OpenStreetMap (dati incompleti in zone remote: verificare anche altre fonti). Ricerca del ${dataStr}.</p>`;
    return;
  }
  contDiv.innerHTML = `
    <p class="empty-note">${strutture.length} strutture trovate entro ${raggio}m (fonte: OpenStreetMap, ricerca del ${dataStr})</p>
    <div class="strutture-list">
      ${strutture.map(s => `
        <div class="struttura-card">
          <div class="struttura-top">
            <span class="struttura-nome">${s.nome}</span>
            <span class="badge diff-media">${s.tipo}</span>
          </div>
          ${s.indirizzo ? `<div class="struttura-riga">📍 ${s.indirizzo}</div>` : ''}
          ${s.telefono ? `<div class="struttura-riga">📞 ${s.telefono}</div>` : ''}
          ${s.sito ? `<div class="struttura-riga">🔗 <a href="${s.sito.startsWith('http') ? s.sito : 'https://' + s.sito}" target="_blank" rel="noopener">${s.sito}</a></div>` : ''}
          <div class="struttura-riga struttura-coord">${s.lat.toFixed(5)}, ${s.lon.toFixed(5)} · <a href="https://www.openstreetmap.org/${s.osmId}" target="_blank" rel="noopener">vedi su OSM ↗</a></div>
        </div>
      `).join('')}
    </div>
  `;
}

/* ---------- Pianificatore ---------- */
function popolaSelectPianificatore() {
  const sel = $('#plannerCammino');
  sel.innerHTML = CAMMINI.cammini.map(c => `<option value="${c.id}">${c.nome}</option>`).join('');
}

function generaItinerario() {
  const id = $('#plannerCammino').value;
  const dataInizio = $('#plannerData').value;
  const ritmo = parseFloat($('#plannerRitmo').value) || 20;
  const c = CAMMINI.cammini.find(x => x.id === id);
  if (!c) return;

  // Raggruppa le tappe ufficiali in giorni in base al ritmo desiderato
  const giorni = [];
  let giornoCorrente = { tappe: [], km: 0 };
  c.tappe.forEach(t => {
    if (giornoCorrente.km > 0 && giornoCorrente.km + t.km > ritmo * 1.35) {
      giorni.push(giornoCorrente);
      giornoCorrente = { tappe: [], km: 0 };
    }
    giornoCorrente.tappe.push(t);
    giornoCorrente.km += t.km;
  });
  if (giornoCorrente.tappe.length) giorni.push(giornoCorrente);

  const start = dataInizio ? new Date(dataInizio + 'T00:00:00') : null;

  const risultatoHtml = giorni.map((g, i) => {
    const da = g.tappe[0].da;
    const a = g.tappe[g.tappe.length - 1].a;
    let dataLabel = `Giorno ${i + 1}`;
    if (start) {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      dataLabel = d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' });
    }
    const salita = g.tappe.reduce((s, t) => s + t.dislivelloSalita, 0);
    const discesa = g.tappe.reduce((s, t) => s + t.dislivelloDiscesa, 0);
    return `
      <div class="day-card">
        <div class="day-head"><span>${dataLabel}</span><span>${Math.round(g.km * 10) / 10} km · ↑${salita}m ↓${discesa}m</span></div>
        <div class="day-route">${da} → ${a}</div>
      </div>
    `;
  }).join('');

  $('#plannerRisultato').innerHTML = `
    <h3 class="section-title small">Itinerario proposto (${giorni.length} giorni)</h3>
    ${risultatoHtml}
    <button class="btn-primary" id="btnSalvaPiano" style="margin-top:.6rem">Salva questo itinerario</button>
  `;

  $('#btnSalvaPiano').addEventListener('click', () => {
    const plans = DB.getPlans();
    plans.push({
      id: 'plan_' + Date.now(),
      camminoId: c.id,
      camminoNome: c.nome,
      dataInizio,
      ritmo,
      giorni: giorni.length,
      creato: new Date().toISOString()
    });
    DB.savePlans(plans);
    renderPianiSalvati();
  });
}
$('#plannerGenera').addEventListener('click', generaItinerario);

function renderPianiSalvati() {
  const plans = DB.getPlans();
  const cont = $('#plannerSalvati');
  if (!plans.length) {
    cont.innerHTML = '<p class="empty-note">Nessun itinerario salvato ancora.</p>';
    return;
  }
  cont.innerHTML = plans.map(p => `
    <div class="saved-item">
      <span>${p.camminoNome} — ${p.giorni} giorni${p.dataInizio ? ' dal ' + new Date(p.dataInizio).toLocaleDateString('it-IT') : ''}</span>
      <button data-id="${p.id}" class="del-plan">Elimina</button>
    </div>
  `).join('');
  $$('.del-plan').forEach(btn => btn.addEventListener('click', () => {
    const plans2 = DB.getPlans().filter(p => p.id !== btn.dataset.id);
    DB.savePlans(plans2);
    renderPianiSalvati();
  }));
}

/* ---------- GPX ---------- */
function initMap() {
  if (leafletMap) return;
  leafletMap = L.map('gpxMap');
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18
  }).addTo(leafletMap);
  leafletMap.setView([42.5, 12.5], 6); // centro Italia
}

function mostraTraccia(parsed) {
  // Info e form di conversione in cammino: sempre mostrati, indipendentemente dalla mappa
  $('#gpxInfo').innerHTML = `
    <h3 class="section-title small" style="margin-top:.4rem">${parsed.name}</h3>
    <div class="gpx-stats">
      <span>${parsed.stats.distanceKm} km</span>
      <span>↑ ${parsed.stats.ascent} m</span>
      <span>↓ ${parsed.stats.descent} m</span>
      ${parsed.stats.minEle != null ? `<span>${parsed.stats.minEle}–${parsed.stats.maxEle} m slm</span>` : ''}
    </div>
    ${parsed.sourceUrl ? `<p class="section-sub" style="margin-top:.4rem"><a href="${parsed.sourceUrl}" target="_blank" rel="noopener">Apri la pagina originale della traccia ↗</a></p>` : ''}
    ${parsed.waypoints && parsed.waypoints.length ? `
      <h4 class="section-title small" style="margin-top:.9rem;font-size:.92rem">Punti di interesse rilevati (${parsed.waypoints.length})</h4>
      <div class="poi-list">
        ${parsed.waypoints.map(w => `
          <div class="poi-item">
            <span class="poi-nome">📍 ${w.nome}</span>
            ${w.descrizione ? `<span class="poi-desc">${w.descrizione}</span>` : ''}
          </div>
        `).join('')}
      </div>
    ` : '<p class="empty-note" style="margin-top:.6rem">Nessun punto di interesse (waypoint) nel file GPX: solo il tracciato.</p>'}
    <button class="btn-secondary" id="btnSalvaGpx" style="margin-top:.9rem">Salva traccia sul dispositivo</button>
  `;

  $('#btnSalvaGpx').addEventListener('click', () => {
    const tracks = DB.getGpxTracks();
    tracks.push({
      id: 'gpx_' + Date.now(),
      nome: parsed.name,
      stats: parsed.stats,
      points: parsed.points,
      waypoints: parsed.waypoints || [],
      sourceUrl: parsed.sourceUrl || null,
      salvato: new Date().toISOString()
    });
    DB.saveGpxTracks(tracks);
    renderGpxSalvati();
  });

  renderFormNuovoCammino(parsed);

  // La mappa (Leaflet, richiede la libreria da CDN) è un arricchimento visivo:
  // se non si carica (rete assente o CDN irraggiungibile) il resto della funzione resta comunque utilizzabile.
  try {
    initMap();
    if (leafletLayer) leafletMap.removeLayer(leafletLayer);
    const latlngs = parsed.points.map(p => [p.lat, p.lon]);
    leafletLayer = L.polyline(latlngs, { color: '#B23A2E', weight: 4 }).addTo(leafletMap);
    leafletMap.fitBounds(leafletLayer.getBounds(), { padding: [20, 20] });
    (parsed.waypoints || []).forEach(w => {
      L.marker([w.lat, w.lon]).addTo(leafletMap).bindPopup(`<strong>${w.nome}</strong>${w.descrizione ? '<br>' + w.descrizione : ''}`);
    });
  } catch (e) {
    console.warn('Mappa non disponibile:', e.message);
  }
}

function renderFormNuovoCammino(parsed) {
  const primoPunto = parsed.points[0];
  const ultimoPunto = parsed.points[parsed.points.length - 1];
  const camminiPersonalizzatiEsistenti = DB.getCustomCammini();

  // Rilevamento automatico di tipo e difficoltà da nome traccia + punti di interesse + statistiche.
  // Restano comunque tutti modificabili nel form qui sotto.
  const testoPerClassificazione = [parsed.name, ...(parsed.waypoints || []).map(w => w.nome + ' ' + w.descrizione)].join(' ');
  const tipoRilevato = CLASSIFICA.tipo(testoPerClassificazione);
  const difficoltaRilevata = CLASSIFICA.difficolta(parsed.stats.distanceKm, parsed.stats.ascent);

  const OPZIONI_TIPO = OPZIONI_TIPO_CAMMINO;
  const OPZIONI_DIFF = OPZIONI_DIFFICOLTA;

  const cont = $('#gpxToCammino');
  cont.innerHTML = `
    <h3 class="section-title small">Trasforma in un cammino</h3>
    <p class="section-sub">Nome dei luoghi, tipologia e difficoltà vengono rilevati automaticamente dalla traccia: controlla e correggi pure tutto prima di salvare.</p>
    <div class="planner-form">
      <label>Aggiungi a
        <select id="cammSelTarget">
          <option value="__nuovo__">➕ Crea un nuovo cammino</option>
          ${camminiPersonalizzatiEsistenti.map(c => `<option value="${c.id}">${c.nome}</option>`).join('')}
        </select>
      </label>
      <div id="cammNuovoWrap">
        <label>Nome del cammino
          <input type="text" id="cammNomeInput" placeholder="Es. Il mio giro delle colline" value="${parsed.name || ''}">
        </label>
        <label>Tipologia
          <select id="cammTipoInput">
            ${OPZIONI_TIPO.map(([v, l]) => `<option value="${v}" ${v === tipoRilevato ? 'selected' : ''}>${l}</option>`).join('')}
          </select>
        </label>
        <label>Zona / regione
          <input type="text" id="cammRegioneInput" placeholder="Rilevamento in corso…" value="">
        </label>
      </div>
      <label>Difficoltà
        <select id="cammDiffInput">
          ${OPZIONI_DIFF.map(v => `<option value="${v}" ${v === difficoltaRilevata ? 'selected' : ''}>${v}</option>`).join('')}
        </select>
      </label>
      <label>Nome tappa — Partenza
        <input type="text" id="cammTappaDa" placeholder="Rilevamento in corso…" value="">
      </label>
      <label>Nome tappa — Arrivo
        <input type="text" id="cammTappaA" placeholder="Rilevamento in corso…" value="">
      </label>
      <button class="btn-primary" id="btnCreaCammino">Aggiungi alle tue tile</button>
      <p class="empty-note" id="cammFeedback"></p>
    </div>
  `;

  const selTarget = $('#cammSelTarget');
  const nuovoWrap = $('#cammNuovoWrap');
  selTarget.addEventListener('change', () => {
    nuovoWrap.style.display = selTarget.value === '__nuovo__' ? 'block' : 'none';
  });

  // Rilevamento automatico dei nomi di partenza/arrivo (e della regione) tramite geocodifica inversa.
  // Richiede connessione: se non disponibile, restano da compilare a mano.
  const inputDa = $('#cammTappaDa');
  const inputA = $('#cammTappaA');
  const inputRegione = $('#cammRegioneInput');
  if (navigator.onLine) {
    GEOCODE.nomeLuogo(primoPunto.lat, primoPunto.lon).then(res => {
      inputDa.value = res ? res.nome : '';
      inputDa.placeholder = 'Partenza';
      if (res && res.regione) inputRegione.value = res.regione;
      else inputRegione.placeholder = 'Es. Veneto';
    });
    GEOCODE.nomeLuogo(ultimoPunto.lat, ultimoPunto.lon).then(res => {
      inputA.value = res ? res.nome : '';
      inputA.placeholder = 'Arrivo';
    });
  } else {
    inputDa.placeholder = 'Partenza'; inputDa.value = '';
    inputA.placeholder = 'Arrivo'; inputA.value = '';
    inputRegione.placeholder = 'Es. Veneto';
  }

  $('#btnCreaCammino').addEventListener('click', () => {
    const target = selTarget.value;
    const da = ($('#cammTappaDa').value || 'Partenza').trim();
    const a = ($('#cammTappaA').value || 'Arrivo').trim();
    const difficoltaScelta = $('#cammDiffInput').value;
    const tappa = {
      da, a,
      km: parsed.stats.distanceKm,
      dislivelloSalita: parsed.stats.ascent,
      dislivelloDiscesa: parsed.stats.descent,
      difficolta: difficoltaScelta,
      note: `Tappa creata da traccia GPX "${parsed.name}".`,
      coordDa: [primoPunto.lat, primoPunto.lon],
      coordA: [ultimoPunto.lat, ultimoPunto.lon],
      puntiInteresse: parsed.waypoints || []
    };

    let messaggio;
    if (target === '__nuovo__') {
      const nome = ($('#cammNomeInput').value || parsed.name || 'Nuovo cammino').trim();
      const tipoScelto = $('#cammTipoInput').value;
      const regioneScelta = ($('#cammRegioneInput').value || 'Personalizzato').trim();
      const nuovo = {
        id: 'personalizzato_' + Date.now(),
        nome,
        tipo: tipoScelto,
        regioni: [regioneScelta],
        difficoltaGenerale: difficoltaScelta,
        descrizione: 'Cammino creato da una traccia GPX personale, non fa parte del database ufficiale.',
        sitoUfficiale: '',
        wikilocRicerca: parsed.sourceUrl || '',
        segnaletica: '',
        personalizzato: true,
        tappe: [{ n: 1, ...tappa }]
      };
      DB.addCustomCammino(nuovo);
      messaggio = `Fatto! "${nome}" è stato aggiunto alle tue tile in Esplora.`;
    } else {
      DB.aggiungiTappaACustomCammino(target, tappa);
      // Se il cammino non aveva ancora un link alla traccia originale, lo aggiunge ora
      if (parsed.sourceUrl) {
        const list = DB.getCustomCammini();
        const c2 = list.find(x => x.id === target);
        if (c2 && !c2.wikilocRicerca) {
          c2.wikilocRicerca = parsed.sourceUrl;
          DB.saveCustomCammini(list);
        }
      }
      messaggio = 'Fatto! Nuova tappa aggiunta al cammino personalizzato.';
    }

    integraCamminiPersonalizzati();
    renderLista();
    popolaSelectPianificatore();
    renderFormNuovoCammino(parsed); // ricostruisce il form con l'elenco aggiornato dei cammini personalizzati
    $('#cammFeedback').textContent = messaggio;
  });
}

$('#gpxFile').addEventListener('change', async e => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = GPX.parse(text);
    mostraTraccia(parsed);
  } catch (err) {
    $('#gpxInfo').innerHTML = `<p class="empty-note">${err.message}</p>`;
  }
});

function renderGpxSalvati() {
  const tracks = DB.getGpxTracks();
  const cont = $('#gpxSalvati');
  if (!tracks.length) {
    cont.innerHTML = '<p class="empty-note">Nessuna traccia salvata ancora.</p>';
    return;
  }
  cont.innerHTML = tracks.map(t => `
    <div class="saved-item">
      <span>${t.nome} — ${t.stats.distanceKm} km</span>
      <span>
        <button data-id="${t.id}" class="load-gpx">Apri</button>
        <button data-id="${t.id}" class="del-gpx">Elimina</button>
      </span>
    </div>
  `).join('');
  $$('.load-gpx').forEach(btn => btn.addEventListener('click', () => {
    const t = DB.getGpxTracks().find(x => x.id === btn.dataset.id);
    if (t) mostraTraccia({ name: t.nome, points: t.points, stats: t.stats, waypoints: t.waypoints || [], sourceUrl: t.sourceUrl || null });
  }));
  $$('.del-gpx').forEach(btn => btn.addEventListener('click', () => {
    DB.saveGpxTracks(DB.getGpxTracks().filter(x => x.id !== btn.dataset.id));
    renderGpxSalvati();
  }));
}

/* ---------- Sezione dati / import-export ---------- */
function downloadJson(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

$('#btnExportDb').addEventListener('click', () => downloadJson(CAMMINI, 'cammini-italia-database.json'));
$('#btnExportUser').addEventListener('click', () => downloadJson(DB.exportUserData(), 'cammini-italia-miei-dati.json'));

$('#importDbFile').addEventListener('change', async e => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const obj = JSON.parse(await file.text());
    if (!obj.cammini) throw new Error('Il file non contiene un database valido.');
    DB.importDb(obj);
    CAMMINI = obj;
    integraCamminiPersonalizzati();
    renderLista(); popolaSelectPianificatore(); renderInfoDb();
  } catch (err) { alert('Errore importazione: ' + err.message); }
});

$('#importUserFile').addEventListener('change', async e => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const obj = JSON.parse(await file.text());
    DB.importUserData(obj);
    integraCamminiPersonalizzati();
    renderPianiSalvati(); renderGpxSalvati(); renderLista();
  } catch (err) { alert('Errore importazione: ' + err.message); }
});

$('#btnResetUser').addEventListener('click', () => {
  if (confirm('Cancellare tutti gli itinerari, le tracce e i cammini personalizzati salvati su questo dispositivo? L\'azione non è reversibile.')) {
    DB.resetUserData();
    integraCamminiPersonalizzati();
    renderPianiSalvati(); renderGpxSalvati(); renderLista();
  }
});

function renderInfoDb() {
  $('#dbVersion').textContent = CAMMINI.versione || '—';
  $('#dbUpdated').textContent = CAMMINI.aggiornato || '—';
}

/* ---------- Ricerca / filtro ---------- */
$('#searchInput').addEventListener('input', renderLista);
$('#filterTipo').addEventListener('change', renderLista);

/* ---------- Avvio ---------- */
function integraCamminiPersonalizzati() {
  // Riparte sempre dai cammini ufficiali del database caricato, poi aggiunge
  // in coda i cammini creati dall'utente da tracce GPX (salvati a parte).
  const ufficiali = CAMMINI.cammini.filter(c => !c.personalizzato);
  CAMMINI.cammini = [...ufficiali, ...DB.getCustomCammini()];
}

async function init() {
  updateConnStatus();
  CAMMINI = await DB.load();
  integraCamminiPersonalizzati();
  renderLista();
  popolaSelectPianificatore();
  renderPianiSalvati();
  renderGpxSalvati();
  renderInfoDb();

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('service-worker.js').catch(() => {});
  }
}
init();

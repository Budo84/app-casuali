let CAMMINI = null;
let currentDettaglioId = null;
let leafletMap = null;
let leafletLayer = null;
let dettMap = null; // mappa Leaflet indipendente per il dettaglio di ogni cammino

const $ = sel => document.querySelector(sel);
const $$ = sel => Array.from(document.querySelectorAll(sel));

/* ---------- Navigazione tab ---------- */
function switchTab(name) {
  if (typeof PLATFORM !== 'undefined') PLATFORM.ferma();
  $$('.tab').forEach(t => {
    const active = t.dataset.tab === name;
    t.classList.toggle('active', active);
    t.setAttribute('aria-selected', active);
  });
  $$('.panel').forEach(p => p.classList.remove('active'));
  $('#panel-' + name).classList.add('active');
  if (name === 'dati' && CAMMINI) renderStatistiche();
}
$$('.tab').forEach(t => t.addEventListener('click', () => switchTab(t.dataset.tab)));

/* ---------- Tema chiaro/scuro ---------- */
function applicaTema(tema) {
  document.documentElement.setAttribute('data-theme', tema);
  $('#btnTema').textContent = tema === 'dark' ? '☀️' : '🌙';
}
$('#btnTema').addEventListener('click', () => {
  const nuovo = DB.getTema() === 'dark' ? 'light' : 'dark';
  DB.saveTema(nuovo);
  applicaTema(nuovo);
});

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

/* ---------- Tempo di percorrenza stimato (regola di Naismith: velocità in piano + dislivello) ---------- */
function tempoStimatoMinuti(km, dislivelloSalita) {
  const imp = DB.getImpostazioni();
  const minutiPiano = (km / imp.velocitaKmH) * 60;
  const minutiSalita = (dislivelloSalita / 100) * imp.minutiPer100mSalita;
  return Math.round(minutiPiano + minutiSalita);
}
function tempoStimatoTesto(km, dislivelloSalita) {
  const min = tempoStimatoMinuti(km, dislivelloSalita);
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h > 0 ? `${h}h ${m}min` : `${m}min`;
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

let modoConfronta = false;
let selezionatiConfronto = new Set();
let soloPreferiti = false;

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
    const okPreferito = !soloPreferiti || DB.isPreferito(c.id);
    return okTesto && okTipo && okPreferito;
  });

  if (filtrati.length === 0) {
    list.innerHTML = `<p class="empty-note">${soloPreferiti ? 'Nessun cammino tra i preferiti ancora: tocca la stella su una tile per aggiungerlo.' : 'Nessun cammino trovato con questi filtri.'}</p>`;
    return;
  }

  filtrati.forEach(c => {
    const tile = document.createElement('div');
    tile.className = 'cammino-tile';
    tile.innerHTML = `
      <div class="tile-visual ${classeTipo(c.tipo)}">
        <button class="tile-preferito" data-id="${c.id}" title="Preferito">${DB.isPreferito(c.id) ? '★' : '☆'}</button>
        ${iconaTipo(c.tipo)}
        <span class="tile-badge">${difficoltaBadge(c.difficoltaGenerale)}</span>
        ${c.personalizzato ? '<span class="tile-mine">tuo</span>' : ''}
        ${modoConfronta ? `<input type="checkbox" class="confronta-check" data-id="${c.id}" ${selezionatiConfronto.has(c.id) ? 'checked' : ''}>` : ''}
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

    tile.querySelector('.tile-preferito').addEventListener('click', e => {
      e.stopPropagation();
      const attivo = DB.togglePreferito(c.id);
      e.target.textContent = attivo ? '★' : '☆';
    });

    const chk = tile.querySelector('.confronta-check');
    if (chk) {
      chk.addEventListener('click', e => e.stopPropagation());
      chk.addEventListener('change', () => {
        if (chk.checked) {
          if (selezionatiConfronto.size >= 3) { chk.checked = false; alert('Puoi confrontare al massimo 3 cammini alla volta.'); return; }
          selezionatiConfronto.add(c.id);
        } else {
          selezionatiConfronto.delete(c.id);
        }
        renderBarraConfronta();
      });
    }

    list.appendChild(tile);
  });
}

function renderBarraConfronta() {
  const cont = $('#barraConfronta');
  if (!modoConfronta || selezionatiConfronto.size === 0) { cont.innerHTML = ''; return; }
  cont.innerHTML = `
    <div class="barra-confronta">
      <span>${selezionatiConfronto.size} selezionat${selezionatiConfronto.size === 1 ? 'o' : 'i'} (max 3)</span>
      <button id="btnVediConfronto">Confronta ora</button>
    </div>
  `;
  $('#btnVediConfronto').addEventListener('click', mostraConfronto);
}

function mostraConfronto() {
  const ids = [...selezionatiConfronto];
  const cammini = ids.map(id => CAMMINI.cammini.find(c => c.id === id)).filter(Boolean);
  if (cammini.length < 2) { alert('Seleziona almeno due cammini da confrontare.'); return; }

  const righe = [
    ['Km totali', c => `${totaleKm(c)} km`],
    ['Tappe', c => c.tappe.length],
    ['Difficoltà', c => c.difficoltaGenerale],
    ['Dislivello in salita', c => `${c.tappe.reduce((s, t) => s + t.dislivelloSalita, 0)} m`],
    ['Tempo stimato', c => tempoStimatoTesto(totaleKm(c), c.tappe.reduce((s, t) => s + t.dislivelloSalita, 0))],
    ['Regioni', c => c.regioni.join(', ')]
  ];

  $('#dettaglioContent').innerHTML = `
    <h2 class="section-title">Confronto cammini</h2>
    <div style="overflow-x:auto">
      <table class="confronto-tabella">
        <thead><tr><th></th>${cammini.map(c => `<th>${c.nome}</th>`).join('')}</tr></thead>
        <tbody>
          ${righe.map(([label, fn]) => `<tr><td><strong>${label}</strong></td>${cammini.map(c => `<td>${fn(c)}</td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
  $$('.panel').forEach(p => p.classList.remove('active'));
  $('#panel-dettaglio').classList.add('active');

  // Esce dalla modalità confronto, così tornando a Esplora le tile sono di nuovo normali
  modoConfronta = false;
  selezionatiConfronto = new Set();
  $('#btnModoConfronta').textContent = '⚖️ Confronta';
  $('#barraConfronta').innerHTML = '';
}

$('#btnSoloPreferiti').addEventListener('click', () => {
  soloPreferiti = !soloPreferiti;
  $('#btnSoloPreferiti').classList.toggle('btn-primary', soloPreferiti);
  renderLista();
});

$('#btnModoConfronta').addEventListener('click', () => {
  modoConfronta = !modoConfronta;
  selezionatiConfronto = new Set();
  $('#btnModoConfronta').textContent = modoConfronta ? '✕ Annulla confronto' : '⚖️ Confronta';
  renderLista();
  renderBarraConfronta();
});

/* ---------- Dettaglio cammino ---------- */
function linkRicercaEsterni(c) {
  const q = encodeURIComponent(c.nome.replace(/\(.*?\)/g, '').trim());
  return [
    { nome: 'Outdooractive', url: `https://www.outdooractive.com/en/search/?q=${q}` },
    { nome: 'AllTrails', url: `https://www.alltrails.com/search?q=${q}` },
    { nome: 'Komoot', url: `https://www.komoot.com/search?query=${q}` },
    { nome: 'Waymarked Trails (OSM)', url: 'https://hiking.waymarkedtrails.org/' }
  ];
}

function apriDettaglio(id) {
  if (typeof PLATFORM !== 'undefined') PLATFORM.ferma(); // ferma un'eventuale partita rimasta in corso
  currentDettaglioId = id;
  const c = CAMMINI.cammini.find(x => x.id === id);
  if (!c) return;
  const cont = $('#dettaglioContent');
  const tracciatoOsm = DB.getTracciatoOsm(c.id);

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
      ${linkRicercaEsterni(c).map(l => `<a href="${l.url}" target="_blank" rel="noopener">${l.nome} ↗</a>`).join('')}
    </div>
    <div id="dettMappaWrap">
      <div id="dettMappa" class="map-box"></div>
      <p class="empty-note" id="dettMappaNota"></p>
    </div>
    <div id="osmTracciaPanel"></div>
    <div class="cc-stats" style="margin:1rem 0">
      <span>${totaleKm(c)} km totali</span>
      <span>${c.tappe.length} tappe</span>
      <span>${tempoStimatoTesto(totaleKm(c), c.tappe.reduce((s, t) => s + t.dislivelloSalita, 0))} stimate</span>
    </div>
    <div id="profiloAltimetrico"></div>
    <div id="giochiCammino"></div>
    <div class="stage-list">
      ${c.tappe.map(t => `
        <div class="stage-row">
          <div class="stage-n ${DB.isTappaCompletata(c.id, t.n) ? 'completata' : ''}">${DB.isTappaCompletata(c.id, t.n) ? '✓' : t.n}</div>
          <div class="stage-body">
            <div class="stage-route">${t.da} → ${t.a}</div>
            <div class="stage-meta">${t.km} km · ↑${t.dislivelloSalita}m ↓${t.dislivelloDiscesa}m · ${t.difficolta} · ⏱ ${tempoStimatoTesto(t.km, t.dislivelloSalita)}</div>
            <div class="stage-note">${t.note || ''}</div>
            <label class="stage-completa-label">
              <input type="checkbox" class="stage-check" data-cammino="${c.id}" data-tappa="${t.n}" ${DB.isTappaCompletata(c.id, t.n) ? 'checked' : ''}>
              Segna come completata
            </label>
            ${t.puntiInteresse && t.puntiInteresse.length ? `
              <div class="poi-list poi-list-compact">
                ${t.puntiInteresse.map(w => `<div class="poi-item"><span class="poi-nome">📍 ${w.nome}</span>${w.descrizione ? `<span class="poi-desc">${w.descrizione}</span>` : ''}</div>`).join('')}
              </div>
            ` : ''}
            <div class="stage-azioni-riga">
              ${t.coordA ? `<button class="btn-strutture" data-cammino="${c.id}" data-tappa="${t.n}">🏠 Strutture</button>` : ''}
              ${t.coordA ? `<button class="btn-acqua" data-cammino="${c.id}" data-tappa="${t.n}">💧 Punti acqua</button>` : ''}
              ${t.coordA ? `<button class="btn-meteo" data-cammino="${c.id}" data-tappa="${t.n}" data-lat="${t.coordA[0]}" data-lon="${t.coordA[1]}">🌦️ Meteo</button>` : ''}
              <button class="btn-diario" data-cammino="${c.id}" data-tappa="${t.n}">📓 Diario</button>
            </div>
            <div class="strutture-risultati" id="strutture-${c.id}-${t.n}"></div>
            <div class="acqua-risultati" id="acqua-${c.id}-${t.n}"></div>
            <div class="meteo-risultati" id="meteo-${c.id}-${t.n}"></div>
            <div class="diario-box" id="diario-${c.id}-${t.n}"></div>
          </div>
        </div>
      `).join('')}
    </div>
    ${c.personalizzato ? `
      <div class="dett-azioni-custom">
        <button class="btn-secondary" id="btnModificaCammino">✏️ Modifica</button>
        <button class="btn-secondary" id="btnCondividiCammino">📤 Condividi</button>
        <button class="btn-danger" id="btnEliminaCammino">Elimina questo cammino personalizzato</button>
      </div>
    ` : ''}
    <div id="modificaCamminoWrap"></div>
  `;
  $$('.panel').forEach(p => p.classList.remove('active'));
  $('#panel-dettaglio').classList.add('active');

  renderDettMappa(c, tracciatoOsm);
  renderPannelloOsm(c, tracciatoOsm);
  renderProfiloAltimetrico(c);
  renderGiochiCammino(c);

  // Mostra eventuali risultati già salvati in precedenza (offline-friendly)
  c.tappe.forEach(t => {
    const salvate = STRUTTURE.getSalvate(c.id, t.n);
    if (salvate) renderStrutture(c.id, t.n, salvate.strutture, salvate.cercatoIl, salvate.raggio);
    const acquaSalvata = ACQUA.getSalvate(c.id, t.n);
    if (acquaSalvata) renderAcqua(c.id, t.n, acquaSalvata.punti, acquaSalvata.cercatoIl, acquaSalvata.raggio);
    renderDiario(c.id, t.n);
  });

  cont.querySelectorAll('.btn-strutture').forEach(btn => {
    btn.addEventListener('click', () => cercaStruttureTappa(btn.dataset.cammino, parseInt(btn.dataset.tappa, 10)));
  });
  cont.querySelectorAll('.btn-acqua').forEach(btn => {
    btn.addEventListener('click', () => cercaAcquaTappa(btn.dataset.cammino, parseInt(btn.dataset.tappa, 10)));
  });
  cont.querySelectorAll('.btn-meteo').forEach(btn => {
    btn.addEventListener('click', () => mostraMeteoTappa(btn));
  });
  cont.querySelectorAll('.btn-diario').forEach(btn => {
    btn.addEventListener('click', () => toggleDiarioForm(btn.dataset.cammino, parseInt(btn.dataset.tappa, 10)));
  });
  cont.querySelectorAll('.stage-check').forEach(chk => {
    chk.addEventListener('change', () => {
      const cId = chk.dataset.cammino, tN = parseInt(chk.dataset.tappa, 10);
      DB.toggleTappaCompletata(cId, tN, chk.checked);
      const badge = chk.closest('.stage-row').querySelector('.stage-n');
      badge.classList.toggle('completata', chk.checked);
      badge.textContent = chk.checked ? '✓' : tN;
      renderStatistiche();
    });
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
    $('#btnCondividiCammino').addEventListener('click', () => {
      downloadJson({ tipo: 'cammino-condiviso-v1', cammino: c }, `${c.nome.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.json`);
    });
  }
}
$('#backFromDettaglio').addEventListener('click', () => switchTab('esplora'));

/* ---------- Meteo per tappa (Open-Meteo, richiede connessione) ---------- */
async function mostraMeteoTappa(btn) {
  const div = $(`#meteo-${btn.dataset.cammino}-${btn.dataset.tappa}`);
  if (!navigator.onLine) {
    div.innerHTML = '<p class="empty-note">Sei offline: il meteo richiede connessione.</p>';
    return;
  }
  btn.disabled = true;
  div.innerHTML = '<p class="empty-note">Carico le previsioni…</p>';
  try {
    const giorni = await METEO.previsioni(parseFloat(btn.dataset.lat), parseFloat(btn.dataset.lon));
    div.innerHTML = `
      <div class="meteo-giorni">
        ${giorni.map(g => {
          const [emoji, testo] = METEO.descrizione(g.codice);
          const dataLabel = new Date(g.data).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' });
          return `
            <div class="meteo-giorno">
              <span class="meteo-data">${dataLabel}</span>
              <span class="meteo-emoji">${emoji}</span>
              <span class="meteo-temp">${g.tempMin}°/${g.tempMax}°</span>
              <span class="meteo-pioggia">💧${g.precipitazione}%</span>
            </div>
          `;
        }).join('')}
      </div>
      <p class="empty-note" style="margin-top:.3rem">Previsioni Open-Meteo per il punto di arrivo della tappa.</p>
    `;
  } catch (err) {
    div.innerHTML = `<p class="empty-note">Errore nel recupero meteo: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
  }
}

/* ---------- Diario di viaggio per tappa ---------- */
function renderDiario(camminoId, tappaN) {
  const div = $(`#diario-${camminoId}-${tappaN}`);
  if (!div) return;
  const voci = DB.getVociDiario(camminoId, tappaN);
  const listaHtml = voci.length ? `
    <div class="diario-lista">
      ${voci.map((v, i) => `
        <div class="diario-voce">
          <div class="diario-voce-head">
            <span>${new Date(v.data).toLocaleDateString('it-IT')}</span>
            <button class="diario-elimina" data-cammino="${camminoId}" data-tappa="${tappaN}" data-i="${i}" title="Elimina">✕</button>
          </div>
          ${v.foto ? `<img src="${v.foto}" class="diario-foto" alt="Foto del diario">` : ''}
          <p>${v.testo}</p>
        </div>
      `).join('')}
    </div>
  ` : '';
  div.innerHTML = listaHtml;
  div.querySelectorAll('.diario-elimina').forEach(b => {
    b.addEventListener('click', () => {
      DB.eliminaVoceDiario(b.dataset.cammino, parseInt(b.dataset.tappa, 10), parseInt(b.dataset.i, 10));
      renderDiario(b.dataset.cammino, parseInt(b.dataset.tappa, 10));
    });
  });
}

function toggleDiarioForm(camminoId, tappaN) {
  const div = $(`#diario-${camminoId}-${tappaN}`);
  const esistente = div.querySelector('.diario-form');
  if (esistente) { esistente.remove(); return; }

  const form = document.createElement('div');
  form.className = 'diario-form';
  form.innerHTML = `
    <textarea placeholder="Com'è andata questa tappa?" rows="3"></textarea>
    <label class="btn-secondary file-btn" style="margin-top:.4rem">Aggiungi una foto (opzionale)
      <input type="file" accept="image/*" hidden class="diario-foto-input">
    </label>
    <span class="empty-note diario-foto-nome"></span>
    <div class="btn-row" style="margin-top:.5rem">
      <button class="btn-primary diario-salva">Salva nel diario</button>
    </div>
  `;
  div.prepend(form);

  const textarea = form.querySelector('textarea');
  const fotoInput = form.querySelector('.diario-foto-input');
  const fotoNome = form.querySelector('.diario-foto-nome');
  let fotoDataUrl = null;

  fotoInput.addEventListener('change', () => {
    const file = fotoInput.files[0];
    if (!file) return;
    comprimiImmagine(file, 640, 0.65).then(dataUrl => {
      fotoDataUrl = dataUrl;
      fotoNome.textContent = `Foto pronta (${file.name})`;
    }).catch(() => {
      fotoNome.textContent = 'Impossibile elaborare questa immagine.';
    });
  });

  form.querySelector('.diario-salva').addEventListener('click', () => {
    const testo = textarea.value.trim();
    if (!testo && !fotoDataUrl) return;
    DB.aggiungiVoceDiario(camminoId, tappaN, {
      testo: testo || '(solo foto)',
      foto: fotoDataUrl,
      data: new Date().toISOString()
    });
    form.remove();
    renderDiario(camminoId, tappaN);
  });
}

// Ridimensiona e comprime un'immagine caricata dall'utente, per non appesantire troppo
// il salvataggio locale (localStorage ha uno spazio limitato).
function comprimiImmagine(file, maxLato, qualita) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        let { width, height } = img;
        if (width > height && width > maxLato) { height *= maxLato / width; width = maxLato; }
        else if (height > maxLato) { width *= maxLato / height; height = maxLato; }
        const canvas = document.createElement('canvas');
        canvas.width = width; canvas.height = height;
        canvas.getContext('2d').drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL('image/jpeg', qualita));
      };
      img.onerror = reject;
      img.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/* ---------- Sezione Giochi del cammino (quiz, memory, caccia al tesoro) ---------- */
function renderGiochiCammino(c) {
  const cont = $('#giochiCammino');
  if (!cont) return;
  const stato = DB.getGiocoCammino(c.id);
  const tutteFatte = stato.quiz && stato.memory && stato.caccia;

  cont.innerHTML = `
    <div class="giochi-box">
      <div class="giochi-head">
        <h3 class="section-title small">🎮 Giochi di questo cammino</h3>
        <span class="giochi-punti">⭐ ${stato.punti} punti</span>
      </div>
      <p class="section-sub">Pensati apposta per questo cammino: utili per intrattenere i più piccoli lungo il percorso.</p>
      <div class="griglia-giochi">
        <button class="gioco-tile ${stato.quiz ? 'fatto' : ''}" id="btnGiocoQuiz">
          <span class="em">❓</span>
          <span class="nm">Quiz del cammino</span>
          <span class="ds">5 domande su questo percorso</span>
          ${stato.quiz ? '<span class="gioco-ok">✓ fatto</span>' : ''}
        </button>
        <button class="gioco-tile ${stato.memory ? 'fatto' : ''}" id="btnGiocoMemory">
          <span class="em">🧠</span>
          <span class="nm">Memory delle tappe</span>
          <span class="ds">Abbina partenza e arrivo</span>
          ${stato.memory ? '<span class="gioco-ok">✓ fatto</span>' : ''}
        </button>
        <button class="gioco-tile ${stato.caccia ? 'fatto' : ''}" id="btnGiocoCaccia">
          <span class="em">🔎</span>
          <span class="nm">Caccia al tesoro</span>
          <span class="ds">Cose da scoprire camminando</span>
          ${stato.caccia ? '<span class="gioco-ok">✓ fatto</span>' : ''}
        </button>
        <button class="gioco-tile avventura" id="btnGiocoPlatform">
          <span class="em">🕹️</span>
          <span class="nm">Salto del Pellegrino</span>
          <span class="ds">Un livello per ogni tappa</span>
        </button>
      </div>
      ${tutteFatte ? '<p class="giochi-medaglia">🏅 Medaglia sbloccata: Esploratore di questo cammino!</p>' : ''}
      <div id="giocoAttivo"></div>
    </div>
  `;

  $('#btnGiocoQuiz').addEventListener('click', () => avviaQuiz(c));
  $('#btnGiocoMemory').addEventListener('click', () => avviaMemory(c));
  $('#btnGiocoCaccia').addEventListener('click', () => avviaCaccia(c));
  $('#btnGiocoPlatform').addEventListener('click', () => renderSelezionePersonaggio(c));
}

function avviaQuiz(c) {
  const box = $('#giocoAttivo');
  const domande = GIOCHI.generaQuiz(c);
  let indice = 0, corrette = 0;

  function mostraDomanda() {
    if (indice >= domande.length) {
      const punti = corrette * GIOCHI.PUNTI_RISPOSTA_QUIZ;
      DB.aggiornaGiocoCammino(c.id, g => { g.quiz = true; g.punti += punti; return g; });
      box.innerHTML = `
        <div class="mini-gioco">
          <p class="giochi-esito">Hai risposto bene a ${corrette} domande su ${domande.length}!<br>+${punti} punti ⭐</p>
          <button class="btn-secondary" id="btnChiudiGioco">Chiudi</button>
        </div>
      `;
      $('#btnChiudiGioco').addEventListener('click', () => { box.innerHTML = ''; renderGiochiCammino(c); renderStatistiche(); });
      return;
    }
    const d = domande[indice];
    box.innerHTML = `
      <div class="mini-gioco">
        <p class="quiz-progress">Domanda ${indice + 1} di ${domande.length}</p>
        <p class="quiz-domanda">${d.domanda}</p>
        <div class="quiz-opzioni">
          ${d.opzioni.map((o, i) => `<button class="quiz-opzione" data-i="${i}">${o}</button>`).join('')}
        </div>
      </div>
    `;
    box.querySelectorAll('.quiz-opzione').forEach(btn => {
      btn.addEventListener('click', () => {
        const scelto = parseInt(btn.dataset.i, 10);
        box.querySelectorAll('.quiz-opzione').forEach(b => b.disabled = true);
        if (scelto === d.corretta) {
          btn.classList.add('giusta');
          corrette++;
        } else {
          btn.classList.add('sbagliata');
          box.querySelectorAll('.quiz-opzione')[d.corretta].classList.add('giusta');
        }
        setTimeout(() => { indice++; mostraDomanda(); }, 900);
      });
    });
  }
  mostraDomanda();
}

function avviaMemory(c) {
  const box = $('#giocoAttivo');
  const carte = GIOCHI.generaMemory(c);
  if (carte.length < 4) {
    box.innerHTML = '<p class="empty-note">Questo cammino ha troppe poche tappe per il memory.</p>';
    return;
  }
  let apertaIdx = null;
  let bloccato = false;
  let coppieTrovate = 0;

  box.innerHTML = `
    <div class="mini-gioco">
      <p class="quiz-progress">Trova tutte le coppie partenza/arrivo</p>
      <div class="memory-grid">
        ${carte.map((_, i) => `<button class="carta-memory" data-i="${i}">?</button>`).join('')}
      </div>
    </div>
  `;

  const bottoni = box.querySelectorAll('.carta-memory');
  bottoni.forEach(btn => {
    btn.addEventListener('click', () => {
      const i = parseInt(btn.dataset.i, 10);
      if (bloccato || btn.classList.contains('presa') || btn.classList.contains('aperta')) return;
      btn.classList.add('aperta');
      btn.textContent = carte[i].testo;

      if (apertaIdx === null) {
        apertaIdx = i;
        return;
      }
      bloccato = true;
      const primaBtn = bottoni[apertaIdx];
      if (carte[apertaIdx].coppia === carte[i].coppia && apertaIdx !== i) {
        setTimeout(() => {
          primaBtn.classList.add('presa'); btn.classList.add('presa');
          apertaIdx = null; bloccato = false; coppieTrovate++;
          if (coppieTrovate === carte.length / 2) {
            const punti = GIOCHI.PUNTI_MEMORY;
            DB.aggiornaGiocoCammino(c.id, g => { g.memory = true; g.punti += punti; return g; });
            setTimeout(() => {
              box.innerHTML = `<div class="mini-gioco"><p class="giochi-esito">Complimenti! Tutte le coppie trovate!<br>+${punti} punti ⭐</p><button class="btn-secondary" id="btnChiudiGioco">Chiudi</button></div>`;
              $('#btnChiudiGioco').addEventListener('click', () => { box.innerHTML = ''; renderGiochiCammino(c); renderStatistiche(); });
            }, 400);
          }
        }, 500);
      } else {
        setTimeout(() => {
          primaBtn.classList.remove('aperta'); primaBtn.textContent = '?';
          btn.classList.remove('aperta'); btn.textContent = '?';
          apertaIdx = null; bloccato = false;
        }, 750);
      }
    });
  });
}

function avviaCaccia(c) {
  const box = $('#giocoAttivo');
  const oggetti = GIOCHI.generaCaccia(c);
  const stato = DB.getGiocoCammino(c.id);
  const spuntati = new Set(stato.cacciaSpuntati || []);

  box.innerHTML = `
    <div class="mini-gioco">
      <p class="quiz-progress">Spunta quello che riconosci lungo il cammino</p>
      <div class="checklist" id="cacciaLista">
        ${oggetti.map((o, i) => `
          <label class="checklist-item">
            <input type="checkbox" data-i="${i}" ${spuntati.has(i) ? 'checked' : ''}>
            <span class="${spuntati.has(i) ? 'checklist-fatto' : ''}">${o}</span>
          </label>
        `).join('')}
      </div>
      <button class="btn-secondary" id="btnChiudiCaccia" style="margin-top:.6rem">Chiudi</button>
    </div>
  `;

  box.querySelectorAll('#cacciaLista input').forEach(chk => {
    chk.addEventListener('change', () => {
      const i = parseInt(chk.dataset.i, 10);
      const giaSpuntato = spuntati.has(i);
      if (chk.checked && !giaSpuntato) {
        spuntati.add(i);
        DB.aggiornaGiocoCammino(c.id, g => {
          g.cacciaSpuntati = Array.from(spuntati);
          g.punti += GIOCHI.PUNTI_OGGETTO_CACCIA;
          if (spuntati.size === oggetti.length) g.caccia = true;
          return g;
        });
      } else if (!chk.checked && giaSpuntato) {
        spuntati.delete(i);
        DB.aggiornaGiocoCammino(c.id, g => {
          g.cacciaSpuntati = Array.from(spuntati);
          g.punti = Math.max(0, g.punti - GIOCHI.PUNTI_OGGETTO_CACCIA);
          g.caccia = spuntati.size === oggetti.length;
          return g;
        });
      }
      chk.nextElementSibling.classList.toggle('checklist-fatto', chk.checked);
      renderStatistiche();
    });
  });

  $('#btnChiudiCaccia').addEventListener('click', () => { box.innerHTML = ''; renderGiochiCammino(c); });
}

/* ---------- Salto del Pellegrino: selezione personaggio, livelli, partita ---------- */
function calcolaStelle(raccolte, totali) {
  if (totali === 0) return 3;
  const perc = raccolte / totali;
  if (perc >= 0.99) return 3;
  if (perc >= 0.5) return 2;
  return 1;
}
function disegnaStelle(n) {
  return '⭐'.repeat(n) + '☆'.repeat(3 - n);
}

function renderSelezionePersonaggio(c) {
  const box = $('#giocoAttivo');
  const statoPlatform = DB.getPlatformState();

  box.innerHTML = `
    <div class="mini-gioco">
      <p class="quiz-progress">Scegli il tuo pellegrino</p>
      <div class="personaggi-grid">
        ${PERSONAGGI.map((p, i) => {
          const sbloccato = p.sblocco();
          return `
            <button class="personaggio-tile ${!sbloccato ? 'bloccato' : ''} ${statoPlatform.personaggio === i ? 'scelto' : ''}" data-i="${i}" ${!sbloccato ? 'disabled' : ''}>
              <canvas class="personaggio-anteprima" width="60" height="60" data-i="${i}"></canvas>
              <span class="personaggio-nome">${p.nome}</span>
              <span class="personaggio-desc">${sbloccato ? (statoPlatform.personaggio === i ? 'In uso' : '') : '🔒 ' + p.descrizione}</span>
            </button>
          `;
        }).join('')}
      </div>
      <button class="btn-secondary" id="btnChiudiSelezione" style="margin-top:.6rem">Chiudi</button>
    </div>
  `;

  // Piccola anteprima disegnata di ogni personaggio
  box.querySelectorAll('.personaggio-anteprima').forEach(canvas => {
    const idx = parseInt(canvas.dataset.i, 10);
    const pers = PERSONAGGI[idx];
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = pers.vestito; ctx.fillRect(20, 26, 20, 26);
    ctx.fillStyle = pers.pelle; ctx.beginPath(); ctx.arc(30, 20, 10, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = pers.accessorio; ctx.fillRect(20, 12, 20, 5);
  });

  box.querySelectorAll('.personaggio-tile').forEach(btn => {
    if (btn.disabled) return;
    btn.addEventListener('click', () => {
      DB.sceglierPersonaggio(parseInt(btn.dataset.i, 10));
      renderSelezioneLivelli(c);
    });
  });
  $('#btnChiudiSelezione').addEventListener('click', () => { box.innerHTML = ''; });
}

function renderSelezioneLivelli(c) {
  const box = $('#giocoAttivo');
  box.innerHTML = `
    <div class="mini-gioco">
      <p class="quiz-progress">Un livello per ogni tappa — scegline uno</p>
      <div class="livelli-lista">
        ${c.tappe.map((t, i) => {
          const stelle = DB.getStelleLivello(c.id, t.n);
          const fattaDavvero = DB.isTappaCompletata(c.id, t.n);
          return `
            <button class="livello-item" data-i="${i}">
              <span class="livello-n">${t.n}</span>
              <span class="livello-nome">${t.da} → ${t.a}${fattaDavvero ? ' <span class="livello-fatta">✓ tappa fatta</span>' : ''}</span>
              <span class="livello-stelle">${disegnaStelle(stelle)}</span>
            </button>
          `;
        }).join('')}
      </div>
      <button class="btn-secondary" id="btnCambiaPersonaggio" style="margin-top:.6rem">Cambia personaggio</button>
    </div>
  `;
  box.querySelectorAll('.livello-item').forEach(btn => {
    btn.addEventListener('click', () => avviaLivelloGioco(c, parseInt(btn.dataset.i, 10)));
  });
  $('#btnCambiaPersonaggio').addEventListener('click', () => renderSelezionePersonaggio(c));
}

function avviaLivelloGioco(c, indiceTappa) {
  const box = $('#giocoAttivo');
  const t = c.tappe[indiceTappa];
  const livello = PLATFORM.generaLivello(t, indiceTappa);
  const statoPlatform = DB.getPlatformState();

  box.innerHTML = `
    <div class="mini-gioco">
      <p class="quiz-progress">${livello.nome}</p>
      <canvas id="canvasPlatform" width="${PLATFORM.W}" height="${PLATFORM.H}"></canvas>
      <div class="comandi-platform">
        <button class="tasto-platform" id="btnSinistra">◀️</button>
        <button class="tasto-platform" id="btnDestra">▶️</button>
        <button class="tasto-platform salta" id="btnSalta">⤴️</button>
      </div>
      <button class="btn-secondary" id="btnEsciLivello" style="margin-top:.5rem">Esci dal livello</button>
    </div>
  `;

  $('#btnEsciLivello').addEventListener('click', () => { PLATFORM.ferma(); renderSelezioneLivelli(c); });

  const canvas = $('#canvasPlatform');
  const collega = (id, tasto) => {
    const el = $(id);
    const giu = ev => { ev.preventDefault(); PLATFORM.premi(tasto, true); };
    const su = ev => { ev.preventDefault(); PLATFORM.premi(tasto, false); };
    el.addEventListener('pointerdown', giu);
    el.addEventListener('pointerup', su);
    el.addEventListener('pointerleave', su);
    el.addEventListener('pointercancel', su);
  };
  collega('#btnSinistra', 'sinistra');
  collega('#btnDestra', 'destra');
  collega('#btnSalta', 'salto');

  PLATFORM.avvia(canvas, livello, statoPlatform.personaggio || 0, (raccolte, totali) => {
    const stelle = calcolaStelle(raccolte, totali);
    const puntiPrima = DB.getStelleLivello(c.id, t.n);
    DB.segnaLivelloCompletato(c.id, t.n, stelle);
    const puntiGuadagnati = 15 + raccolte * 5;
    DB.aggiornaGiocoCammino(c.id, g => { g.punti += puntiGuadagnati; return g; });

    box.innerHTML = `
      <div class="mini-gioco esito-platform">
        <div class="confetti-emoji">🎉 🌟 🎉</div>
        <p class="giochi-esito">Livello completato!<br>${disegnaStelle(stelle)}<br>Hai raccolto ${raccolte} di ${totali} tesori.<br>+${puntiGuadagnati} punti ⭐</p>
        <div class="btn-row">
          <button class="btn-primary" id="btnRigioca">Rigioca</button>
          <button class="btn-secondary" id="btnAltroLivello">Altri livelli</button>
        </div>
      </div>
    `;
    $('#btnRigioca').addEventListener('click', () => avviaLivelloGioco(c, indiceTappa));
    $('#btnAltroLivello').addEventListener('click', () => { renderSelezioneLivelli(c); renderStatistiche(); });
    renderStatistiche();
  });
}

/* ---------- Profilo altimetrico (reale se disponibile dalla traccia, altrimenti stimato dai dislivelli) ---------- */
function costruisciProfilo(c) {
  const haTracciatiReali = c.tappe.length > 0 && c.tappe.every(t => t.tracciato && t.tracciato.length && t.tracciato[0][2] != null);
  const punti = [];
  let distanzaCum = 0;

  if (haTracciatiReali) {
    c.tappe.forEach(t => {
      let prev = null;
      t.tracciato.forEach(([lat, lon, ele]) => {
        if (prev) distanzaCum += GPX.haversine({ lat: prev[0], lon: prev[1] }, { lat, lon });
        punti.push({ distKm: distanzaCum, ele: ele || 0 });
        prev = [lat, lon];
      });
    });
    return { punti, reale: true };
  }

  // Nessun dato di quota punto-per-punto: stima un profilo "a triangoli" dai dislivelli complessivi di ogni tappa
  let eleCorrente = 0;
  c.tappe.forEach(t => {
    const kmMeta = (t.km || 0) / 2;
    punti.push({ distKm: distanzaCum, ele: eleCorrente });
    distanzaCum += kmMeta;
    eleCorrente += t.dislivelloSalita || 0;
    punti.push({ distKm: distanzaCum, ele: eleCorrente });
    distanzaCum += kmMeta;
    eleCorrente -= t.dislivelloDiscesa || 0;
    punti.push({ distKm: distanzaCum, ele: eleCorrente });
  });
  return { punti, reale: false };
}

function svgProfilo(punti, w = 600, h = 110) {
  if (punti.length < 2) return '';
  const pad = 8;
  const distMax = punti[punti.length - 1].distKm || 1;
  const eleMin = Math.min(...punti.map(p => p.ele));
  const eleMax = Math.max(...punti.map(p => p.ele));
  const eleRange = (eleMax - eleMin) || 1;

  const coords = punti.map(p => {
    const x = pad + (p.distKm / distMax) * (w - 2 * pad);
    const y = h - pad - ((p.ele - eleMin) / eleRange) * (h - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const areaPath = `M${pad},${h - pad} L${coords.join(' L')} L${w - pad},${h - pad} Z`;

  return `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
    <path class="profilo-area" d="${areaPath}"/>
    <polyline class="profilo-linea" points="${coords.join(' ')}"/>
  </svg>`;
}

function renderProfiloAltimetrico(c) {
  const cont = $('#profiloAltimetrico');
  if (!cont) return;
  const { punti, reale } = costruisciProfilo(c);
  if (punti.length < 2) { cont.innerHTML = ''; return; }
  cont.innerHTML = `
    <h3 class="section-title small">Profilo altimetrico</h3>
    <div class="profilo-altimetrico">${svgProfilo(punti)}</div>
    <p class="profilo-nota">${reale ? 'Ricostruito dalla traccia GPS reale.' : 'Stima approssimativa basata sui dislivelli complessivi di ogni tappa, non su dati GPS punto per punto.'}</p>
  `;
}

/* ---------- Mappa sempre visibile nel dettaglio di un cammino ---------- */
function renderDettMappa(c, tracciatoOsm) {
  const nota = $('#dettMappaNota');
  try {
    if (dettMap) { dettMap.remove(); dettMap = null; }
    dettMap = L.map('dettMappa');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18
    }).addTo(dettMap);

    const bounds = [];

    if (tracciatoOsm && tracciatoOsm.points && tracciatoOsm.points.length) {
      // Tracciato reale importato da OpenStreetMap: un'unica traccia continua
      const latlngs = tracciatoOsm.points.map(p => [p.lat, p.lon]);
      L.polyline(latlngs, { color: '#B23A2E', weight: 4 }).addTo(dettMap);
      latlngs.forEach(ll => bounds.push(ll));
      nota.textContent = `Tracciato reale importato da OpenStreetMap (relazione ${tracciatoOsm.relId || ''}) il ${tracciatoOsm.importatoIl ? new Date(tracciatoOsm.importatoIl).toLocaleDateString('it-IT') : ''}.`;
    } else {
      // Nessun tracciato completo: per ogni tappa disegna il tracciato salvato (se creata da GPX)
      // oppure una linea approssimativa tra i punti di partenza e arrivo della tappa
      let haTracciatiTappa = false;
      c.tappe.forEach(t => {
        if (t.tracciato && t.tracciato.length) {
          haTracciatiTappa = true;
          L.polyline(t.tracciato, { color: '#B23A2E', weight: 4 }).addTo(dettMap);
          t.tracciato.forEach(ll => bounds.push(ll));
        } else if (t.coordDa && t.coordA) {
          L.polyline([t.coordDa, t.coordA], { color: '#B23A2E', weight: 3, dashArray: '6 6' }).addTo(dettMap);
          bounds.push(t.coordDa, t.coordA);
        }
        (t.puntiInteresse || []).forEach(w => {
          L.marker([w.lat, w.lon]).addTo(dettMap).bindPopup(`<strong>${w.nome}</strong>${w.descrizione ? '<br>' + w.descrizione : ''}`);
        });
      });
      // Marker di partenza/arrivo per ogni tappa (utile con la linea approssimativa tratteggiata)
      c.tappe.forEach(t => {
        if (t.coordDa) L.circleMarker(t.coordDa, { radius: 5, color: '#1F3A2E', fillColor: '#1F3A2E', fillOpacity: 1 }).addTo(dettMap).bindPopup(t.da);
        if (t.coordA) L.circleMarker(t.coordA, { radius: 5, color: '#1F3A2E', fillColor: '#1F3A2E', fillOpacity: 1 }).addTo(dettMap).bindPopup(t.a);
      });
      nota.textContent = haTracciatiTappa
        ? 'Traccia ricostruita dalle tracce GPX di ogni tappa.'
        : 'Percorso approssimativo tra le tappe (linea tratteggiata): non è il tracciato reale sul terreno. Cerca il tracciato vero qui sotto.';
    }

    if (bounds.length) {
      dettMap.fitBounds(bounds, { padding: [20, 20] });
    } else {
      dettMap.setView([42.5, 12.5], 6);
    }
  } catch (e) {
    console.warn('Mappa dettaglio non disponibile:', e.message);
    nota.textContent = 'Mappa non disponibile (verifica la connessione).';
  }
}

/* ---------- Ricerca e importazione di un tracciato reale da OpenStreetMap ---------- */
function renderPannelloOsm(c, tracciatoOsm) {
  const panel = $('#osmTracciaPanel');

  if (tracciatoOsm) {
    panel.innerHTML = `
      <p class="empty-note">
        Stai usando un tracciato reale importato da OpenStreetMap.
        <button class="btn-secondary" id="btnRimuoviOsm" style="margin-left:.5rem">Rimuovi e torna al percorso approssimativo</button>
      </p>
    `;
    $('#btnRimuoviOsm').addEventListener('click', () => {
      DB.eliminaTracciatoOsm(c.id);
      apriDettaglio(c.id);
    });
    return;
  }

  panel.innerHTML = `
    <div class="osm-cerca-box">
      <button class="btn-secondary" id="btnCercaOsm">🔎 Cerca il tracciato reale su OpenStreetMap</button>
      <p class="empty-note" style="margin-top:.4rem">Molti cammini storici sono mappati per intero su OpenStreetMap: se trovato, il tracciato reale sostituirà la linea approssimativa sulla mappa qui sopra.</p>
      <div id="osmRisultati"></div>
    </div>
  `;

  $('#btnCercaOsm').addEventListener('click', async () => {
    const btn = $('#btnCercaOsm');
    const risDiv = $('#osmRisultati');
    if (!navigator.onLine) {
      risDiv.innerHTML = '<p class="empty-note">Sei offline: la ricerca su OpenStreetMap richiede connessione.</p>';
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Ricerca in corso…';
    risDiv.innerHTML = '';
    try {
      const nomeBase = c.nome.replace(/\(.*?\)/g, '').trim();
      const candidati = await OSMTRACCE.cercaRelazioni(nomeBase);
      if (candidati.length === 0) {
        risDiv.innerHTML = '<p class="empty-note">Nessun percorso corrispondente trovato su OpenStreetMap. Prova i link di ricerca qui sopra su altre piattaforme.</p>';
      } else {
        risDiv.innerHTML = `
          <p class="empty-note">${candidati.length} percorso/i trovato/i. Scegli quello giusto:</p>
          ${candidati.map(cand => `
            <div class="osm-candidato">
              <span>${cand.nome}${cand.rete ? ` <span class="badge">${cand.rete}</span>` : ''}</span>
              <button class="btn-secondary btn-importa-osm" data-id="${cand.id}">Importa</button>
            </div>
          `).join('')}
        `;
        risDiv.querySelectorAll('.btn-importa-osm').forEach(b => {
          b.addEventListener('click', async () => {
            b.disabled = true;
            b.textContent = 'Importazione…';
            try {
              const { points, stats } = await OSMTRACCE.importaRelazione(b.dataset.id);
              DB.saveTracciatoOsm(c.id, {
                points: OSMTRACCE.decima(points, 500),
                stats,
                relId: b.dataset.id,
                importatoIl: new Date().toISOString()
              });
              apriDettaglio(c.id);
            } catch (err) {
              risDiv.innerHTML = `<p class="empty-note">Errore nell'importazione: ${err.message}</p>`;
            }
          });
        });
      }
    } catch (err) {
      risDiv.innerHTML = `<p class="empty-note">Errore nella ricerca: ${err.message}</p>`;
    } finally {
      btn.disabled = false;
      btn.textContent = '🔎 Cerca il tracciato reale su OpenStreetMap';
    }
  });
}

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
    btn.textContent = '🏠 Strutture';
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

/* ---------- Punti acqua per tappa ---------- */
async function cercaAcquaTappa(camminoId, tappaN) {
  const c = CAMMINI.cammini.find(x => x.id === camminoId);
  const t = c.tappe.find(x => x.n === tappaN);
  const contDiv = $(`#acqua-${camminoId}-${tappaN}`);
  const btn = document.querySelector(`.btn-acqua[data-cammino="${camminoId}"][data-tappa="${tappaN}"]`);

  if (!navigator.onLine) {
    contDiv.innerHTML = '<p class="empty-note">Sei offline: mostro solo eventuali risultati già salvati in precedenza.</p>';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Ricerca in corso…';
  contDiv.innerHTML = '<p class="empty-note">Interrogo OpenStreetMap (Overpass API)…</p>';

  try {
    const punti = await ACQUA.cerca(camminoId, t);
    renderAcqua(camminoId, tappaN, punti, new Date().toISOString(), ACQUA.RAGGIO_DEFAULT);
  } catch (err) {
    contDiv.innerHTML = `<p class="empty-note">Errore nella ricerca: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '💧 Punti acqua';
  }
}

function renderAcqua(camminoId, tappaN, punti, cercatoIl, raggio) {
  const contDiv = $(`#acqua-${camminoId}-${tappaN}`);
  if (!contDiv) return;
  const dataStr = cercatoIl ? new Date(cercatoIl).toLocaleDateString('it-IT') : '';
  if (!punti || punti.length === 0) {
    contDiv.innerHTML = `<p class="empty-note">Nessun punto acqua mappato entro ${raggio || ACQUA.RAGGIO_DEFAULT}m su OpenStreetMap. Ricerca del ${dataStr}.</p>`;
    return;
  }
  contDiv.innerHTML = `
    <p class="empty-note">${punti.length} punti acqua trovati entro ${raggio}m (fonte: OpenStreetMap, ricerca del ${dataStr})</p>
    <div class="strutture-list">
      ${punti.map(p => `
        <div class="struttura-card">
          <div class="struttura-top"><span class="struttura-nome">💧 ${p.nome}</span></div>
          <div class="struttura-riga struttura-coord">${p.lat.toFixed(5)}, ${p.lon.toFixed(5)} · <a href="https://www.openstreetmap.org/${p.osmId}" target="_blank" rel="noopener">vedi su OSM ↗</a></div>
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
    <div class="btn-row" style="margin-top:.6rem">
      <button class="btn-primary" id="btnSalvaPiano">Salva questo itinerario</button>
      <button class="btn-secondary" id="btnEsportaPdf">📄 Esporta come PDF</button>
    </div>
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

  $('#btnEsportaPdf').addEventListener('click', () => esportaItinerarioPdf(c, giorni, start));
}
$('#plannerGenera').addEventListener('click', generaItinerario);

/* ---------- Esportazione itinerario come PDF (via stampa del browser, nessuna libreria esterna) ---------- */
function esportaItinerarioPdf(c, giorni, start) {
  const righeGiorni = giorni.map((g, i) => {
    const da = g.tappe[0].da;
    const a = g.tappe[g.tappe.length - 1].a;
    let dataLabel = `Giorno ${i + 1}`;
    if (start) {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      dataLabel = d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' });
    }
    const salita = g.tappe.reduce((s, t) => s + t.dislivelloSalita, 0);
    const discesa = g.tappe.reduce((s, t) => s + t.dislivelloDiscesa, 0);
    const km = Math.round(g.km * 10) / 10;
    return `
      <tr>
        <td>${dataLabel}</td>
        <td>${da} → ${a}</td>
        <td>${km} km</td>
        <td>↑${salita}m ↓${discesa}m</td>
        <td>${tempoStimatoTesto(km, salita)}</td>
      </tr>
    `;
  }).join('');

  const finestra = window.open('', '_blank');
  if (!finestra) { alert('Il browser ha bloccato l\'apertura della finestra di stampa: consenti i popup per questo sito.'); return; }
  finestra.document.write(`
    <!doctype html><html lang="it"><head><meta charset="UTF-8">
    <title>${c.nome} — Itinerario</title>
    <style>
      body{font-family:Georgia,serif;color:#332B22;padding:2rem;max-width:800px;margin:0 auto;}
      h1{font-size:1.5rem;border-bottom:2px solid #B23A2E;padding-bottom:.5rem;}
      table{width:100%;border-collapse:collapse;margin-top:1rem;}
      th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid #ddd;font-size:.92rem;}
      th{background:#EDE7D6;}
      .meta{color:#6B6152;font-size:.9rem;margin-bottom:1rem;}
      @media print{ button{display:none;} }
    </style>
    </head><body>
    <h1>${c.nome}</h1>
    <p class="meta">${c.regioni.join(' · ')} — ${giorni.length} giorni, ${totaleKm(c)} km totali. Generato il ${new Date().toLocaleDateString('it-IT')}.</p>
    <table>
      <thead><tr><th>Giorno</th><th>Percorso</th><th>Km</th><th>Dislivello</th><th>Tempo stimato</th></tr></thead>
      <tbody>${righeGiorni}</tbody>
    </table>
    <p class="meta">Tempo stimato calcolato con il tuo passo impostato nell'app (velocità in piano + tempo aggiuntivo per il dislivello). Verifica sempre le condizioni reali del percorso prima di partire.</p>
    <button onclick="window.print()" style="margin-top:1rem;padding:.6rem 1.2rem;">Stampa / Salva come PDF</button>
    </body></html>
  `);
  finestra.document.close();
}

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
      puntiInteresse: parsed.waypoints || [],
      tracciato: OSMTRACCE.decima(parsed.points, 400).map(p => [p.lat, p.lon, p.ele || null])
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

/* ---------- Registrazione GPS in tempo reale ---------- */
let recWatchId = null;
let recTimerId = null;
let recPunti = [];
let recDistanzaKm = 0;
let recInizio = null;
let recInPausa = false;
let recMap = null;
let recLayer = null;

function initRecMap() {
  if (recMap) { recMap.remove(); recMap = null; recLayer = null; }
  try {
    recMap = L.map('recMappa').setView([42.5, 12.5], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 18
    }).addTo(recMap);
  } catch (e) {
    console.warn('Mappa registrazione non disponibile:', e.message);
  }
}

function recAggiornaUI() {
  $('#recDistanza').textContent = recDistanzaKm.toFixed(1);
  $('#recPunti').textContent = recPunti.length;
}
function recAggiornaTempo() {
  const secondi = Math.floor((Date.now() - recInizio) / 1000);
  const m = String(Math.floor(secondi / 60)).padStart(2, '0');
  const s = String(secondi % 60).padStart(2, '0');
  $('#recTempo').textContent = `${m}:${s}`;
}

// Elabora una nuova posizione ricevuta dal GPS (esposta come funzione a sé per poterla testare
// anche senza un vero segnale GPS, passandole una posizione simulata)
function recPosizioneRicevuta(pos) {
  const punto = {
    lat: pos.coords.latitude,
    lon: pos.coords.longitude,
    ele: (pos.coords.altitude != null) ? pos.coords.altitude : null,
    t: Date.now()
  };
  if (recPunti.length > 0) {
    const prev = recPunti[recPunti.length - 1];
    recDistanzaKm += GPX.haversine(prev, punto);
  }
  recPunti.push(punto);
  recAggiornaUI();
  if (recMap) {
    const ll = [punto.lat, punto.lon];
    if (!recLayer) { recLayer = L.polyline([ll], { color: '#B23A2E', weight: 4 }).addTo(recMap); recMap.setView(ll, 16); }
    else { recLayer.addLatLng(ll); recMap.panTo(ll); }
  }
}
function recErrore(err) {
  $('#recStato').textContent = 'Errore GPS: ' + (err.message || 'posizione non disponibile.');
}

function recAvvia() {
  if (!navigator.geolocation) {
    $('#recStato').textContent = 'Il tuo browser non supporta la geolocalizzazione.';
    return;
  }
  recPunti = []; recDistanzaKm = 0; recInizio = Date.now(); recInPausa = false;
  recAggiornaUI(); $('#recTempo').textContent = '00:00';
  $('#btnRecAvvia').disabled = true; $('#btnRecPausa').disabled = false; $('#btnRecStop').disabled = false;
  $('#recStato').textContent = 'Registrazione in corso… tieni l\'app aperta.';
  initRecMap();
  recWatchId = navigator.geolocation.watchPosition(recPosizioneRicevuta, recErrore, { enableHighAccuracy: true, maximumAge: 1000 });
  recTimerId = setInterval(recAggiornaTempo, 1000);
}

function recPausaToggle() {
  if (!recInPausa) {
    if (recWatchId != null) navigator.geolocation.clearWatch(recWatchId);
    clearInterval(recTimerId);
    recInPausa = true;
    $('#btnRecPausa').textContent = '▶️ Riprendi';
    $('#recStato').textContent = 'In pausa.';
  } else {
    recWatchId = navigator.geolocation.watchPosition(recPosizioneRicevuta, recErrore, { enableHighAccuracy: true, maximumAge: 1000 });
    recTimerId = setInterval(recAggiornaTempo, 1000);
    recInPausa = false;
    $('#btnRecPausa').textContent = '⏸️ Pausa';
    $('#recStato').textContent = 'Registrazione in corso…';
  }
}

function recFerma() {
  if (recWatchId != null) navigator.geolocation.clearWatch(recWatchId);
  clearInterval(recTimerId);
  $('#btnRecAvvia').disabled = false; $('#btnRecPausa').disabled = true; $('#btnRecStop').disabled = true;
  $('#btnRecPausa').textContent = '⏸️ Pausa';

  if (recPunti.length < 2) {
    $('#recStato').textContent = 'Registrazione troppo breve: non è stato salvato nulla.';
    return;
  }

  const nome = prompt('Come vuoi chiamare questa traccia?', 'Traccia registrata ' + new Date().toLocaleDateString('it-IT'));
  if (!nome) { $('#recStato').textContent = 'Registrazione non salvata.'; return; }

  const points = recPunti.map(p => ({ lat: p.lat, lon: p.lon, ele: p.ele }));
  const stats = GPX.computeStats(points);
  const tracks = DB.getGpxTracks();
  tracks.push({ id: 'gpx_' + Date.now(), nome, stats, points, waypoints: [], sourceUrl: null, salvato: new Date().toISOString() });
  DB.saveGpxTracks(tracks);
  renderGpxSalvati();
  $('#recStato').textContent = `Salvata come "${nome}". La trovi nella scheda Traccia GPX: da lì puoi anche trasformarla in un cammino.`;
}

$('#btnRecAvvia').addEventListener('click', recAvvia);
$('#btnRecPausa').addEventListener('click', recPausaToggle);
$('#btnRecStop').addEventListener('click', recFerma);

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
    renderChecklist(); caricaImpostazioniForm(); renderStatistiche();
  } catch (err) { alert('Errore importazione: ' + err.message); }
});

$('#btnResetUser').addEventListener('click', () => {
  if (confirm('Cancellare tutti gli itinerari, le tracce e i cammini personalizzati salvati su questo dispositivo? L\'azione non è reversibile.')) {
    DB.resetUserData();
    integraCamminiPersonalizzati();
    renderPianiSalvati(); renderGpxSalvati(); renderLista();
    renderChecklist(); caricaImpostazioniForm(); renderStatistiche();
  }
});

$('#importCamminoCondiviso').addEventListener('change', async e => {
  const file = e.target.files[0];
  if (!file) return;
  const feedback = $('#importCondivisoFeedback');
  try {
    const obj = JSON.parse(await file.text());
    const cammino = obj.cammino || obj; // accetta sia il formato "condiviso" sia il cammino nudo
    if (!cammino.tappe) throw new Error('Il file non contiene un cammino valido.');
    cammino.id = 'personalizzato_' + Date.now(); // nuovo id per evitare conflitti
    cammino.personalizzato = true;
    DB.addCustomCammino(cammino);
    integraCamminiPersonalizzati();
    renderLista();
    feedback.textContent = `Fatto! "${cammino.nome}" è stato aggiunto alle tue tile.`;
  } catch (err) {
    feedback.textContent = 'Errore importazione: ' + err.message;
  }
});

function renderInfoDb() {
  $('#dbVersion').textContent = CAMMINI.versione || '—';
  $('#dbUpdated').textContent = CAMMINI.aggiornato || '—';
}

/* ---------- Ricerca / filtro ---------- */
$('#searchInput').addEventListener('input', renderLista);
$('#filterTipo').addEventListener('change', renderLista);

/* ---------- Checklist zaino ---------- */
function renderChecklist() {
  const cont = $('#checklistZaino');
  const lista = DB.getChecklist();
  cont.innerHTML = lista.map((voce, i) => `
    <label class="checklist-item">
      <input type="checkbox" data-i="${i}" ${voce.fatto ? 'checked' : ''}>
      <span class="${voce.fatto ? 'checklist-fatto' : ''}">${voce.testo}</span>
      <button class="checklist-rimuovi" data-i="${i}" title="Rimuovi">✕</button>
    </label>
  `).join('');

  cont.querySelectorAll('input[type=checkbox]').forEach(chk => {
    chk.addEventListener('change', () => {
      const l = DB.getChecklist();
      l[parseInt(chk.dataset.i, 10)].fatto = chk.checked;
      DB.saveChecklist(l);
      renderChecklist();
    });
  });
  cont.querySelectorAll('.checklist-rimuovi').forEach(btn => {
    btn.addEventListener('click', () => {
      const l = DB.getChecklist();
      l.splice(parseInt(btn.dataset.i, 10), 1);
      DB.saveChecklist(l);
      renderChecklist();
    });
  });
}
$('#btnChecklistAggiungi').addEventListener('click', () => {
  const input = $('#checklistNuovaVoce');
  const testo = input.value.trim();
  if (!testo) return;
  const l = DB.getChecklist();
  l.push({ testo, fatto: false });
  DB.saveChecklist(l);
  input.value = '';
  renderChecklist();
});
$('#btnChecklistReset').addEventListener('click', () => {
  if (confirm('Ripristinare la lista predefinita? Le voci aggiunte a mano e lo stato delle spunte andranno persi.')) {
    localStorage.removeItem(DB.KEY_CHECKLIST);
    renderChecklist();
  }
});

/* ---------- Impostazioni di marcia ---------- */
function caricaImpostazioniForm() {
  const imp = DB.getImpostazioni();
  $('#impVelocita').value = imp.velocitaKmH;
  $('#impSalita').value = imp.minutiPer100mSalita;
}
$('#btnSalvaImpostazioni').addEventListener('click', () => {
  DB.saveImpostazioni({
    velocitaKmH: parseFloat($('#impVelocita').value) || DB.DEFAULT_IMPOSTAZIONI.velocitaKmH,
    minutiPer100mSalita: parseFloat($('#impSalita').value) || DB.DEFAULT_IMPOSTAZIONI.minutiPer100mSalita
  });
  if (currentDettaglioId) apriDettaglio(currentDettaglioId); // ricalcola i tempi mostrati, se sei nel dettaglio
});

/* ---------- Statistiche personali e traguardi ---------- */
const DEFINIZIONI_BADGE = [
  { id: 'prima_tappa', icona: '✅', label: 'Prima tappa completata', cond: s => s.tappeCompletateCount >= 1 },
  { id: 'primi_10km', icona: '👣', label: 'Primi 10 km', cond: s => s.kmTotali >= 10 },
  { id: 'primi_50km', icona: '🥾', label: 'Primi 50 km', cond: s => s.kmTotali >= 50 },
  { id: 'primi_100km', icona: '🏅', label: '100 km percorsi', cond: s => s.kmTotali >= 100 },
  { id: 'dieci_tappe', icona: '🔟', label: '10 tappe completate', cond: s => s.tappeCompletateCount >= 10 },
  { id: 'dislivello_1000', icona: '⛰️', label: '1000 m di dislivello', cond: s => s.dislivelloTotale >= 1000 },
  { id: 'primo_cammino', icona: '🏆', label: 'Primo cammino completato', cond: s => s.camminiCompletatiCount >= 1 },
  { id: 'esploratore', icona: '🗺️', label: 'Hai creato un tuo cammino', cond: s => DB.getCustomCammini().length >= 1 },
  { id: 'primo_quiz', icona: '❓', label: 'Primo quiz completato', cond: () => Object.values(DB.getGiochi()).some(g => g.quiz) },
  { id: 'giocatore_completo', icona: '🎮', label: 'Tutti i giochi di un cammino', cond: () => Object.values(DB.getGiochi()).some(g => g.quiz && g.memory && g.caccia) },
  { id: 'giochi_100', icona: '⭐', label: '100 punti gioco', cond: () => DB.puntiGiocoTotali() >= 100 },
  { id: 'livello_perfetto', icona: '🌟', label: 'Un livello a 3 stelle', cond: () => Object.values(DB.getPlatformState().livelli || {}).some(l => l.stelle === 3) }
];

function renderStatistiche() {
  const completate = DB.getTappeCompletate();
  let kmTotali = 0, dislivelloTotale = 0, tappeCompletateCount = 0;
  let camminiCompletatiCount = 0;

  (CAMMINI ? CAMMINI.cammini : []).forEach(c => {
    let tutteFatte = c.tappe.length > 0;
    c.tappe.forEach(t => {
      if (completate[`${c.id}__${t.n}`]) {
        kmTotali += t.km || 0;
        dislivelloTotale += t.dislivelloSalita || 0;
        tappeCompletateCount++;
      } else {
        tutteFatte = false;
      }
    });
    if (tutteFatte) camminiCompletatiCount++;
  });

  const stats = { kmTotali, dislivelloTotale, tappeCompletateCount, camminiCompletatiCount };

  $('#statsPersonali').innerHTML = `
    <div class="stat-box"><span class="stat-num">${Math.round(kmTotali)}</span><span class="stat-label">km percorsi</span></div>
    <div class="stat-box"><span class="stat-num">${Math.round(dislivelloTotale)}</span><span class="stat-label">m di dislivello</span></div>
    <div class="stat-box"><span class="stat-num">${tappeCompletateCount}</span><span class="stat-label">tappe completate</span></div>
    <div class="stat-box"><span class="stat-num">${camminiCompletatiCount}</span><span class="stat-label">cammini completati</span></div>
    <div class="stat-box"><span class="stat-num">${DB.puntiGiocoTotali()}</span><span class="stat-label">punti gioco ⭐</span></div>
  `;

  const badgeGrid = $('#badgeGrid');
  if (badgeGrid) {
    const giaVisti = DB.getBadgeVisti();
    const nuoviSbloccati = [];
    badgeGrid.innerHTML = DEFINIZIONI_BADGE.map((b, i) => {
      const sbloccato = b.cond(stats);
      if (sbloccato && !giaVisti.includes(b.id)) nuoviSbloccati.push(b);
      return `
        <div class="badge-item ${sbloccato ? 'sbloccato' : ''}" style="--rot:${(i % 5 - 2) * 2.5}deg" title="${sbloccato ? 'Sbloccato!' : 'Ancora da sbloccare'}">
          <span class="badge-icona">${b.icona}</span>
          <span>${b.label}</span>
          ${sbloccato ? `<button class="badge-diploma" data-id="${b.id}" data-icona="${b.icona}" data-label="${b.label}">🖨️ Diploma</button>` : ''}
        </div>
      `;
    }).join('');

    badgeGrid.querySelectorAll('.badge-diploma').forEach(btn => {
      btn.addEventListener('click', () => stampaDiploma(btn.dataset.label, btn.dataset.icona));
    });

    // Festeggia (una sola volta) le medaglie appena sbloccate da quando non si guardava la scheda Dati
    if (nuoviSbloccati.length) {
      nuoviSbloccati.forEach(b => DB.segnaBadgeVisto(b.id));
      festeggiaMedaglia(nuoviSbloccati[0]);
    }
  }

  renderForziere();
}

/* ---------- Festa alla sblocco di una nuova medaglia ---------- */
function festeggiaMedaglia(b) {
  document.querySelectorAll('.festa-overlay').forEach(el => el.remove()); // evita sovrapposizioni se scattano più feste in rapida successione
  const pop = document.createElement('div');
  pop.className = 'festa-overlay';
  pop.innerHTML = `
    <div class="festa-box">
      <div class="festa-confetti">🎉✨🎊✨🎉</div>
      <div class="festa-icona">${b.icona}</div>
      <h3>Nuova medaglia!</h3>
      <p>${b.label}</p>
      <button class="btn-primary" id="btnChiudiFesta">Evviva!</button>
    </div>
  `;
  document.body.appendChild(pop);
  $('#btnChiudiFesta').addEventListener('click', () => pop.remove());
}

/* ---------- Diploma stampabile per una medaglia ---------- */
function stampaDiploma(nomeMedaglia, icona) {
  const nomeBambino = prompt('Come si chiama chi ha vinto questa medaglia?', '') || '';
  const finestra = window.open('', '_blank');
  if (!finestra) { alert('Il browser ha bloccato la finestra di stampa: consenti i popup per questo sito.'); return; }
  finestra.document.write(`
    <!doctype html><html lang="it"><head><meta charset="UTF-8"><title>Diploma</title>
    <style>
      body{font-family:Georgia,serif;text-align:center;padding:3rem 2rem;color:#332B22;}
      .cornice{border:6px double #C98A2B;padding:3rem 2rem;border-radius:16px;max-width:520px;margin:0 auto;}
      .icona{font-size:4rem;}
      h1{font-size:1rem;letter-spacing:.2em;text-transform:uppercase;color:#B23A2E;margin:1rem 0 .3rem;}
      h2{font-size:1.6rem;margin:.3rem 0 1.2rem;}
      .nome{font-size:1.8rem;color:#1F3A2E;margin:1rem 0;border-bottom:2px solid #C98A2B;display:inline-block;padding:0 1rem .3rem;}
      .data{margin-top:2rem;font-size:.85rem;color:#6B6152;}
      @media print{ button{display:none;} }
    </style></head><body>
    <div class="cornice">
      <div class="icona">${icona}</div>
      <h1>Diploma del Cammino</h1>
      <h2>${nomeMedaglia}</h2>
      <p>assegnato con merito a</p>
      <div class="nome">${nomeBambino || '________________'}</div>
      <p class="data">${new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
    </div>
    <p style="text-align:center;margin-top:1.5rem"><button onclick="window.print()" style="padding:.6rem 1.2rem;">Stampa</button></p>
    </body></html>
  `);
  finestra.document.close();
}

/* ---------- Forziere a sorpresa: si apre ogni 50 punti gioco ---------- */
function renderForziere() {
  const cont = $('#forziereBox');
  if (!cont) return;
  const punti = DB.puntiGiocoTotali();
  const sogliaProssima = Math.floor(punti / 50) * 50;
  const aperti = DB.getForzieriAperti();
  const daAprire = sogliaProssima >= 50 && !aperti.includes(sogliaProssima);

  cont.innerHTML = daAprire ? `
    <button class="forziere-btn" id="btnApriForziere">📦 Hai un forziere da aprire! (${sogliaProssima} punti)</button>
  ` : `<p class="empty-note">Prossimo forziere a ${sogliaProssima + 50} punti gioco (ne hai ${punti}).</p>`;

  if (daAprire) {
    $('#btnApriForziere').addEventListener('click', () => {
      DB.apriForziere(sogliaProssima);
      const premi = ['Un applauso speciale! 👏', 'Sei un vero esploratore! 🧭', 'Continua così, pellegrino! 🥾', 'Hai stupito tutti! 🌟'];
      const premio = premi[Math.floor(Math.random() * premi.length)];
      festeggiaMedaglia({ icona: '📦', label: premio });
      renderForziere();
    });
  }
}

/* ---------- Cammini vicino a me (geolocalizzazione del dispositivo) ---------- */
$('#btnVicinoAMe').addEventListener('click', () => {
  const nota = $('#vicinoAMeNota');
  if (!navigator.geolocation) {
    nota.textContent = 'Il tuo browser non supporta la geolocalizzazione.';
    return;
  }
  nota.textContent = 'Rilevamento posizione in corso…';
  navigator.geolocation.getCurrentPosition(
    pos => {
      const qui = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      const conDistanza = CAMMINI.cammini
        .filter(c => c.tappe[0] && c.tappe[0].coordDa)
        .map(c => ({ c, distKm: Math.round(GPX.haversine(qui, { lat: c.tappe[0].coordDa[0], lon: c.tappe[0].coordDa[1] })) }))
        .sort((a, b) => a.distKm - b.distKm);
      const list = $('#camminiList');
      list.innerHTML = '';
      conDistanza.forEach(({ c, distKm }) => {
        const tile = document.createElement('div');
        tile.className = 'cammino-tile';
        tile.innerHTML = `
          <div class="tile-visual ${classeTipo(c.tipo)}">
            ${iconaTipo(c.tipo)}
            <span class="tile-badge">${difficoltaBadge(c.difficoltaGenerale)}</span>
          </div>
          <div class="tile-body">
            <div class="tile-name">${c.nome}</div>
            <div class="tile-region">${c.regioni.join(' · ')}</div>
            <div class="tile-stats"><span>📍 ${distKm} km da te</span></div>
          </div>
        `;
        tile.addEventListener('click', () => apriDettaglio(c.id));
        list.appendChild(tile);
      });
      nota.textContent = `Cammini ordinati per distanza dalla tua posizione attuale (partenza della prima tappa).`;
    },
    err => {
      nota.textContent = 'Impossibile ottenere la posizione: ' + (err.message || 'permesso negato.');
    }
  );
});

/* ---------- Avvio ---------- */
function integraCamminiPersonalizzati() {
  // Riparte sempre dai cammini ufficiali del database caricato, poi aggiunge
  // in coda i cammini creati dall'utente da tracce GPX (salvati a parte).
  const ufficiali = CAMMINI.cammini.filter(c => !c.personalizzato);
  CAMMINI.cammini = [...ufficiali, ...DB.getCustomCammini()];
}

async function init() {
  updateConnStatus();
  applicaTema(DB.getTema());
  CAMMINI = await DB.load();
  integraCamminiPersonalizzati();
  renderLista();
  popolaSelectPianificatore();
  renderPianiSalvati();
  renderGpxSalvati();
  renderInfoDb();
  renderChecklist();
  caricaImpostazioniForm();
  renderStatistiche();

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('service-worker.js').catch(() => {});
  }
}
init();

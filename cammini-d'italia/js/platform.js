/* Gioco platform "Salto del Pellegrino": un livello per ogni tappa di un cammino,
   generato dai dati reali della tappa (difficoltà, km, punti di interesse).
   Canvas 2D puro, nessuna libreria esterna: funziona offline come il resto dell'app. */

const PERSONAGGI = [
  { nome: 'Pellegrino Blu', pelle: '#E8B88A', vestito: '#345542', accessorio: '#B23A2E',
    sblocco: () => true, descrizione: 'Sempre pronto a partire.' },
  { nome: 'Pellegrina Rossa', pelle: '#E8B88A', vestito: '#B23A2E', accessorio: '#C98A2B',
    sblocco: () => DB.puntiGiocoTotali() >= 20, descrizione: 'Sbloccata a 20 punti gioco.' },
  { nome: 'Esploratore Verde', pelle: '#8A5A3C', vestito: '#5F8F76', accessorio: '#D9A03F',
    sblocco: () => DB.puntiGiocoTotali() >= 100, descrizione: 'Sbloccato a 100 punti gioco.' },
  { nome: 'Capo Cammino Oro', pelle: '#E8B88A', vestito: '#C98A2B', accessorio: '#1F3A2E',
    sblocco: () => PLATFORM.camminiCompletatiCount() >= 1, descrizione: 'Sbloccato completando un intero cammino.' }
];

const PLATFORM = {
  W: 320, H: 180,
  GRAVITY: 0.55,
  JUMP_V: -11.5,
  MOVE_SPEED: 2.3,

  _raf: null,
  _canvas: null, _ctx: null,
  _livello: null, _player: null, _camera: 0,
  _input: { sinistra: false, destra: false, salto: false },
  _tempo: 0,
  _onFine: null,
  _personaggioIdx: 0,
  _finito: false,

  camminiCompletatiCount() {
    if (!window.CAMMINI || !CAMMINI.cammini) return 0;
    const completate = DB.getTappeCompletate();
    let count = 0;
    CAMMINI.cammini.forEach(c => {
      if (c.tappe.length && c.tappe.every(t => completate[`${c.id}__${t.n}`])) count++;
    });
    return count;
  },

  /* ---------- Generazione del livello dai dati reali della tappa ---------- */
  generaLivello(t, indiceTappa) {
    let seed = (indiceTappa + 1) * 137 + Math.round((t.km || 1) * 10) + Math.round(t.dislivelloSalita || 0);
    const rand = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };

    const difficoltaNum = { facile: 0, media: 1, impegnativa: 2, 'molto impegnativa': 3 }[t.difficolta] ?? 1;
    const numPiattaforme = 9 + difficoltaNum * 3;
    const numOstacoli = 1 + difficoltaNum;

    const piattaforme = [{ x: 0, y: 160, w: 90, h: 20 }];
    let x = 90, y = 140;
    for (let i = 0; i < numPiattaforme; i++) {
      const gap = 20 + rand() * 26 + difficoltaNum * 3;
      const w = 46 + rand() * 38;
      y = Math.max(65, Math.min(158, y + (rand() - 0.5) * 24));
      x += gap;
      piattaforme.push({ x, y, w, h: 16 });
      x += w;
    }
    const xFinale = x + 50;
    piattaforme.push({ x: xFinale, y: 160, w: 110, h: 20 });

    const nomiPoi = (t.puntiInteresse && t.puntiInteresse.length) ? t.puntiInteresse.map(p => p.nome) : [];
    const collezionabili = [];
    piattaforme.slice(1, -1).forEach((p, i) => {
      if (rand() < 0.55) {
        collezionabili.push({ x: p.x + p.w / 2, y: p.y - 20, preso: false, nome: nomiPoi[i % Math.max(1, nomiPoi.length)] || 'Stella' });
      }
    });

    const ostacoli = [];
    for (let i = 0; i < numOstacoli; i++) {
      const idx = Math.max(1, Math.min(piattaforme.length - 2, Math.floor(rand() * (piattaforme.length - 2)) + 1));
      const p = piattaforme[idx];
      ostacoli.push({ x: p.x + p.w / 2, y: p.y - 45, w: 24, h: 16 });
    }

    return {
      nome: `${t.da} → ${t.a}`,
      larghezza: xFinale + 160,
      piattaforme, collezionabili, ostacoli,
      partenza: { x: 20, y: 120 },
      goal: { x: xFinale + 55, y: 100 }
    };
  },

  /* ---------- Avvio di una partita ---------- */
  avvia(canvas, livello, personaggioIdx, onFine) {
    this._canvas = canvas;
    this._ctx = canvas.getContext('2d');
    this._livello = livello;
    this._personaggioIdx = personaggioIdx;
    this._onFine = onFine;
    this._finito = false;
    this._camera = 0;
    this._tempo = 0;
    this._player = { x: livello.partenza.x, y: livello.partenza.y, vx: 0, vy: 0, w: 13, h: 20, grounded: false, direzione: 1 };
    this._ultimoCheckpoint = { x: livello.partenza.x, y: livello.partenza.y };
    this._coyote = 0;
    this._suOstacolo = false;
    this._stelleRaccolte = 0;
    this._attaccaInput();
    this._loop();
  },
  ferma() {
    if (this._raf) cancelAnimationFrame(this._raf);
    this._staccaInput();
  },

  _attaccaInput() {
    this._keydown = e => {
      if (e.key === 'ArrowLeft') this._input.sinistra = true;
      if (e.key === 'ArrowRight') this._input.destra = true;
      if (e.key === ' ' || e.key === 'ArrowUp') this._input.salto = true;
    };
    this._keyup = e => {
      if (e.key === 'ArrowLeft') this._input.sinistra = false;
      if (e.key === 'ArrowRight') this._input.destra = false;
      if (e.key === ' ' || e.key === 'ArrowUp') this._input.salto = false;
    };
    window.addEventListener('keydown', this._keydown);
    window.addEventListener('keyup', this._keyup);
  },
  _staccaInput() {
    if (this._keydown) window.removeEventListener('keydown', this._keydown);
    if (this._keyup) window.removeEventListener('keyup', this._keyup);
  },
  premi(tasto, valore) { this._input[tasto] = valore; },

  _rettangoliSiToccano(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  },

  _passo() {
    const p = this._player, liv = this._livello;
    // Un ostacolo toccato nel frame precedente rallenta il passo di questo frame (mai una spinta indietro:
    // per un gioco pensato per bambini, un ostacolo deve rendere le cose più lente, non far perdere progressi)
    const velocita = this._suOstacolo ? this.MOVE_SPEED * 0.4 : this.MOVE_SPEED;
    this._suOstacolo = false;
    p.vx = 0;
    if (this._input.sinistra) { p.vx = -velocita; p.direzione = -1; }
    if (this._input.destra) { p.vx = velocita; p.direzione = 1; }

    // "coyote time": qualche istante di tolleranza per saltare anche appena dopo aver lasciato una piattaforma,
    // così un salto un po' in ritardo (normalissimo per un bambino) non fa comunque fallire il livello
    this._coyote = p.grounded ? 8 : Math.max(0, this._coyote - 1);
    if (this._input.salto && (p.grounded || this._coyote > 0)) {
      p.vy = this.JUMP_V; p.grounded = false; this._coyote = 0;
    }

    p.vy += this.GRAVITY;

    p.x += p.vx;
    liv.piattaforme.forEach(pl => {
      if (this._rettangoliSiToccano(p, pl)) {
        if (p.vx > 0) p.x = pl.x - p.w;
        else if (p.vx < 0) p.x = pl.x + pl.w;
      }
    });
    p.x = Math.max(0, p.x);

    p.y += p.vy;
    p.grounded = false;
    liv.piattaforme.forEach(pl => {
      if (this._rettangoliSiToccano(p, pl)) {
        if (p.vy > 0) { p.y = pl.y - p.h; p.vy = 0; p.grounded = true; this._ultimoCheckpoint = { x: pl.x + 5, y: pl.y - p.h }; }
        else if (p.vy < 0) { p.y = pl.y + pl.h; p.vy = 0; }
      }
    });

    if (p.y > this.H + 60) { // caduto: si riparte dall'ultima piattaforma raggiunta (checkpoint), non da capo
      p.x = this._ultimoCheckpoint.x; p.y = this._ultimoCheckpoint.y; p.vx = 0; p.vy = 0;
    }

    liv.ostacoli.forEach(o => {
      if (this._rettangoliSiToccano(p, o)) { this._suOstacolo = true; }
    });

    liv.collezionabili.forEach(col => {
      if (!col.preso && Math.abs((p.x + p.w / 2) - col.x) < 14 && Math.abs((p.y + p.h / 2) - col.y) < 16) {
        col.preso = true; this._stelleRaccolte++;
      }
    });

    if (!this._finito && p.x + p.w >= liv.goal.x) {
      this._finito = true;
      this.ferma();
      if (this._onFine) this._onFine(this._stelleRaccolte, liv.collezionabili.length);
    }

    this._camera = Math.max(0, Math.min(p.x - this.W / 3, liv.larghezza - this.W));
    this._tempo++;
  },

  _disegna() {
    const ctx = this._ctx, liv = this._livello, p = this._player, cam = this._camera;
    ctx.clearRect(0, 0, this.W, this.H);

    const cielo = ctx.createLinearGradient(0, 0, 0, this.H);
    cielo.addColorStop(0, '#BFE0EE'); cielo.addColorStop(1, '#EAF6EE');
    ctx.fillStyle = cielo; ctx.fillRect(0, 0, this.W, this.H);

    ctx.fillStyle = '#1F3A2E';
    liv.piattaforme.forEach(pl => {
      const sx = pl.x - cam;
      if (sx + pl.w < 0 || sx > this.W) return;
      ctx.fillStyle = '#8A5A3C';
      ctx.fillRect(sx, pl.y + 6, pl.w, pl.h - 6);
      ctx.fillStyle = '#5F8F76';
      ctx.fillRect(sx, pl.y, pl.w, 7);
    });

    ctx.font = '16px sans-serif'; ctx.textAlign = 'center';
    liv.collezionabili.forEach(col => {
      if (col.preso) return;
      const sx = col.x - cam;
      if (sx < -20 || sx > this.W + 20) return;
      ctx.fillText('⭐', sx, col.y + 6);
    });
    liv.ostacoli.forEach(o => {
      const sx = o.x - cam;
      if (sx < -30 || sx > this.W + 30) return;
      ctx.font = '20px sans-serif';
      ctx.fillText('☁️', sx, o.y + 14);
    });

    const gsx = liv.goal.x - cam;
    if (gsx > -30 && gsx < this.W + 30) { ctx.font = '22px sans-serif'; ctx.fillText('🚩', gsx, liv.goal.y); }

    const pers = PERSONAGGI[this._personaggioIdx] || PERSONAGGI[0];
    const px = p.x - cam, py = p.y;
    ctx.fillStyle = pers.vestito;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(px, py + 7, p.w, p.h - 7, 3) : ctx.rect(px, py + 7, p.w, p.h - 7);
    ctx.fill();
    ctx.fillStyle = pers.pelle;
    ctx.beginPath();
    ctx.arc(px + p.w / 2, py + 4, 5.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = pers.accessorio;
    ctx.fillRect(px + p.w / 2 - 6, py, 12, 3);

    ctx.fillStyle = '#1F3A2E';
    ctx.font = '11px monospace'; ctx.textAlign = 'left';
    ctx.fillText(`⭐ ${this._stelleRaccolte}/${liv.collezionabili.length}`, 6, 14);
  },

  _loop() {
    this._passo();
    this._disegna();
    if (!this._finito) this._raf = requestAnimationFrame(() => this._loop());
  }
};

import createHobbit from './hobbit.js';
import { SOLUTION, EXPECTED_VICTORY } from './solution.js';

const $ = (s) => document.querySelector(s);
const enc = new TextEncoder();
const dec = new TextDecoder();

// --- i18n (EN/FR) : chaînes statiques via [data-i18n], dynamiques via L().
// Le choix est mémorisé dans le cookie "hobbit.lang". ---
const STR = {
  cmd_placeholder: ['Type a command…', 'Tapez une commande…'],
  objs_title: ['Objects & characters', 'Objets & personnages'],
  map_title: ['Map', 'Carte'],
  room_label: ['Room', 'Lieu'],
  vec_empty: ['(no illustration here)', "(pas d'illustration ici)"],
  th_hash: ['#', '#'],
  th_name: ['Name', 'Nom'],
  th_room: ['Room', 'Lieu'],
  th_carrier: ['Container', 'Contenant'],
  th_hp: ['HP', 'PV'],
  th_f0: ['Lock.', 'Verr.'],
  th_f0t: ['Locked (bit0)', 'Verrouillé (bit0)'],
  th_f1: ['Liquid', 'Liquide'],
  th_f1t: ['Liquid / consumable substance (bit1)', 'Liquide / substance (bit1)'],
  th_f2: ['Full', 'Plein'],
  th_f2t: ['Full container (bit2)', 'Contenant plein (bit2)'],
  th_f3: ['Down', 'À terre'],
  th_f3t: ['Downed / dead / broken (bit3)', 'À terre / mort / cassé (bit3)'],
  th_f4: ['Glow', 'Lum.'],
  th_f4t: ['Light source (bit4)', 'Source de lumière (bit4)'],
  th_f5: ['Open', 'Ouvert'],
  th_f5t: ['Open / lit (bit5)', 'Ouvert / allumé (bit5)'],
  th_f6: ['Creat.', 'Créat.'],
  th_f6t: ['Creature vs object (bit6)', 'Créature vs objet (bit6)'],
  th_f7: ['Present', 'Présent'],
  th_f7t: ['Present / visible in game (bit7)', 'Présent / visible en jeu (bit7)'],
  btn_load: ['LOAD', 'CHARGER'],
  btn_save: ['SAVE', 'SAUVER'],
  btn_about: ['ABOUT', 'À PROPOS'],
  btn_auto: ['AUTO PLAY', 'AUTO PLAY'],
  btn_auto_title: ['Replay the solution (spoilers)', 'Rejouer la solution (spoilers)'],
  auto_cancel: ['Cancel', 'Annuler'],
  auto_confirm: ['Start AUTO PLAY', 'Lancer AUTO PLAY'],
  btn_load_title: ['Reload local save', 'Recharger la sauvegarde locale'],
  btn_save_title: ['Save game (localStorage + file)',
                   'Enregistrer la partie (localStorage + fichier)'],
  btn_about_title: ['About / credits', 'À propos / crédits'],
  btn_copy: ['COPY', 'COPIER'],
  btn_copy_title: ['Copy game text to clipboard',
                   'Copier le texte du jeu dans le presse-papiers'],
  btn_mem: ['MEM', 'MEM'],
  btn_mem_title: ['Download memory trace (debug)',
                  'Télécharger la trace mémoire (debug)'],
};

const getCookie = (k) => {
  const m = document.cookie.match('(^|;)\\s*' + k + '\\s*=\\s*([^;]*)');
  return m ? decodeURIComponent(m[2]) : null;
};
const setCookie = (k, v) => {
  document.cookie = `${k}=${encodeURIComponent(v)}; max-age=31536000; path=/; SameSite=Lax`;
};

let LANG = getCookie('hobbit.lang')
  || ((navigator.language || '').toLowerCase().startsWith('fr') ? 'fr' : 'en');
const t = (k) => STR[k][LANG === 'fr' ? 1 : 0];
const L = (en, fr) => (LANG === 'fr' ? fr : en);

let statusEn = 'loading…', statusFr = 'chargement…';
function setStatus(en, fr) {
  statusEn = en; statusFr = fr;
  $('#status').textContent = L(en, fr);
}

function applyI18n() {
  document.documentElement.lang = LANG;
  for (const el of document.querySelectorAll('[data-i18n]'))
    el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll('[data-i18n-ph]'))
    el.placeholder = t(el.dataset.i18nPh);
  for (const el of document.querySelectorAll('[data-i18n-title]'))
    el.title = t(el.dataset.i18nTitle);
  for (const el of document.querySelectorAll('[data-lang-block]'))
    el.hidden = el.dataset.langBlock !== LANG;
  for (const b of document.querySelectorAll('.lang-flag'))
    b.classList.toggle('active', b.dataset.lang === LANG);
  $('#btn-auto').textContent = autoPlaying ? 'STOP' : t('btn_auto');
  $('#status').textContent = L(statusEn, statusFr);
}

const SLOT = { IMG: 0, ROM: 1, SHIM: 2, SNAP: 3, BLOB: 4 };
const SAVE_KEY = 'hobbit.oric.save';
const PAL = [[0,0,0],[255,0,0],[0,255,0],[255,255,0],
             [0,0,255],[255,0,255],[0,255,255],[255,255,255]];

let M = null;
let textLen = 0;
let busy = false;

// Autoplay (rejoue la solution). autoTimer : setTimeout courant.
let autoPlaying = false;
let autoTimer = null;
let autoIdx = 0;
const AUTO_DELAY = 800;
let memFrames = null;   /* trace @@M/@@D de l'autoplay en cours (debug) */

// Historique des commandes (fleches HAUT/BAS dans le champ de saisie).
const cmdHistory = [];
let histPos = 0;     // == cmdHistory.length => ligne en cours d'edition
let histDraft = '';  // texte non envoye, memorise a la premiere remontee

async function fetchInto(url, slot) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  const bytes = new Uint8Array(await r.arrayBuffer());
  const cap = M._hob_slot_cap(slot);
  if (bytes.length > cap) throw new Error(`${url}: ${bytes.length} > cap ${cap}`);
  M.HEAPU8.set(bytes, M._hob_slot(slot));
  M._hob_slot_len(slot, bytes.length);
  return bytes.length;
}

function drainText() {
  const len = M._hob_text_len();
  if (len > textLen) {
    const ptr = M._hob_text_ptr();
    const chunk = dec.decode(M.HEAPU8.subarray(ptr + textLen, ptr + len));
    const el = $('#screen');
    el.textContent += chunk;
    el.scrollTop = el.scrollHeight;
    textLen = len;
  }
}

const persistSave = () => {
  if (!M._hob_save_ready()) return false;
  const len = M._hob_save_len();
  const ptr = M._hob_save_ptr();
  const bytes = M.HEAPU8.slice(ptr, ptr + len);
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  localStorage.setItem(SAVE_KEY, btoa(s));
  M._hob_save_clear();
  return true;
};

function afterTurn() {
  drainText();
  if (persistSave())
    setStatus('save written (localStorage)', 'sauvegarde enregistree (localStorage)');
  refreshLive();
}

function sendCommand(text) {
  if (busy) return;
  busy = true;
  M._hob_key_flush();
  for (const b of enc.encode(text)) M._hob_key(b);
  M._hob_key(0x0d);
  M._hob_run(0);
  afterTurn();
  busy = false;
  $('#cmd').focus();
}

function refreshLive() {
  const room = M._hob_player_room();
  $('#room').textContent = room >= 0
    ? `$${hex(room)} ${M.UTF8ToString(M._hob_room_name(room))}` : '?';
  drawObjs();
  drawVector(room);
  drawMap(room);
}

const hex = (v) => v.toString(16).toUpperCase().padStart(2, '0');

function drawObjs() {
  const n = M._hob_obj_count();
  const byKey = new Map();
  for (let i = 0; i < n; i++) byKey.set(M._hob_obj_key(i), i);
  const oname = (i) => M.UTF8ToString(M._hob_obj_name(i));
  // poupée russe : remonte les contenants (+1) jusqu'à $FF
  const chain = (key) => {
    const parts = [];
    let k = key, guard = 0;
    while (guard++ < 70) {
      const i = byKey.get(k);
      if (i === undefined) { parts.push('$' + hex(k)); break; }
      parts.push(oname(i));
      k = M._hob_obj_field(i, 1);   // +1 brut ($FF = personne)
      if (k === 0xFF) break;
    }
    return parts.join(L(' in ', ' dans '));
  };
  const rows = [];
  for (let i = 0; i < n; i++) {
    const key = M._hob_obj_key(i);
    const flags = M._hob_obj_field(i, 6);
    const alive = M._hob_obj_alive(i);
    const eloc = M._hob_obj_field(i, 7);
    const carrier = M._hob_obj_carrier(i);
    let bits = '';
    for (let b = 0; b < 8; b++)
      bits += `<td class="f">${(flags & (1 << b)) ? '✓' : ''}</td>`;
    const cls = key === 0x00 ? 'player' : (alive ? '' : 'dead');
    const tip = esc(chain(key) + (eloc < 0 ? '' : ` @ $${hex(eloc)} ${roomName(eloc)}`))
      .replace(/"/g, '&quot;');
    rows.push(`<tr class="${cls}" title="${tip}"><td>$${hex(key)}</td>` +
      `<td>${esc(M.UTF8ToString(M._hob_obj_name(i)))}</td>` +
      `<td>${eloc < 0 ? '—' : '$' + hex(eloc)}</td>` +
      `<td>${carrier < 0 ? '—' : '$' + hex(carrier)}</td>` +
      `<td>${alive ? M._hob_obj_field(i, 4) : '✝'}</td>` + bits + `</tr>`);
  }
  $('#objs tbody').innerHTML = rows.join('');
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function renderVecInto(cv, room) {
  const ptr = M._hob_vec_ptr();
  if (room < 0 || M._hob_vec_key(room) < 0 || !M._hob_vec_render(room, ptr)) return false;
  const ctx = cv.getContext('2d');
  const img = ctx.createImageData(240, 128);
  for (let i = 0; i < 240 * 128; i++) {
    const c = PAL[M.HEAPU8[ptr + i] & 7];
    img.data[i * 4] = c[0];
    img.data[i * 4 + 1] = c[1];
    img.data[i * 4 + 2] = c[2];
    img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return true;
}

function drawVector(room) {
  const cv = $('#vec');
  const empty = $('#vec-empty');
  if (!renderVecInto(cv, room)) {
    cv.style.display = 'none';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  cv.style.display = 'block';
}

// --- carte : placement directionnel par BFS (directions des sorties) ---
let LAYOUT = null, LAYOUT_N = -1;

function computeLayout() {
  const n = M._hob_room_count();
  if (LAYOUT && LAYOUT_N === n) return LAYOUT;
  const ids = [];
  for (let i = 0; i < n; i++) ids.push(M._hob_room_id(i));
  const inSet = new Set(ids);
  const delta = { 1: [0, -1], 2: [0, 1], 3: [1, 0], 4: [-1, 0],
                  5: [1, -1], 6: [-1, -1], 7: [1, 1], 8: [-1, 1],
                  9: [0, -1], 10: [0, 1] };
  const pos = new Map();
  const occ = new Set();
  const free = (x, y) => !occ.has(x + ',' + y);
  const place = (id, x, y) => {
    let k = 0;
    while (!free(x + k, y) && !free(x, y + k) && k < 60) k++;
    if (free(x + k, y)) { x += k; } else if (free(x, y + k)) { y += k; }
    pos.set(id, [x, y]);
    occ.add(x + ',' + y);
  };
  const start = inSet.has(1) ? 1 : ids[0];
  place(start, 0, 0);
  const q = [start];
  while (q.length) {
    const id = q.shift();
    const [x, y] = pos.get(id);
    const ne = M._hob_room_exit_count(id);
    for (let j = 0; j < ne; j++) {
      const d = M._hob_room_exit_dir(id, j);
      const t = M._hob_room_exit_dst(id, j);
      if (!inSet.has(t) || pos.has(t)) continue;
      const [dx, dy] = delta[d] || [0, 0];
      place(t, x + dx, y + dy);
      q.push(t);
    }
  }
  for (const id of ids) if (!pos.has(id)) place(id, 0, 0);
  LAYOUT = { ids, pos };
  LAYOUT_N = n;
  return LAYOUT;
}

function buildMapSvg(playerRoom, focus) {
  const n = M._hob_room_count();
  if (!n) return null;
  const { ids, pos } = computeLayout();
  const xs = ids.map((i) => pos.get(i)[0]);
  const ys = ids.map((i) => pos.get(i)[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const step = 92, pad = 40;
  const W = pad * 2 + (maxX - minX) * step;
  const H = pad * 2 + (maxY - minY) * step;
  const at = (id) => {
    const [x, y] = pos.get(id);
    return [pad + (x - minX) * step, pad + (y - minY) * step];
  };

  let edges = '';
  const drawn = new Set();
  for (const id of ids) {
    const ne = M._hob_room_exit_count(id);
    for (let j = 0; j < ne; j++) {
      const t = M._hob_room_exit_dst(id, j);
      if (!pos.has(t)) continue;
      const k = id < t ? id + '-' + t : t + '-' + id;
      if (drawn.has(k)) continue;
      drawn.add(k);
      const [x1, y1] = at(id), [x2, y2] = at(t);
      edges += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#2f3944" stroke-width="1.5"/>`;
    }
  }

  // NPC : creature (cle >= $3C) vivante placee dans un lieu
  const npc = new Map();
  for (let i = 0; i < M._hob_obj_count(); i++) {
    const key = M._hob_obj_key(i);
    if (key < 0x3c || !M._hob_obj_alive(i)) continue;
    const loc = M._hob_obj_field(i, 7);
    if (loc < 0 || loc > 0x4f || !pos.has(loc)) continue;
    if (!npc.has(loc)) npc.set(loc, []);
    npc.get(loc).push(M.UTF8ToString(M._hob_obj_name(i)));
  }

  let nodes = '';
  for (const id of ids) {
    const [x, y] = at(id);
    const here = id === playerRoom;
    const nm = roomName(id);
    const full = nm && nm !== '?' ? `$${hex(id)} ${nm}` : `$${hex(id)}`;
    nodes += `<g><title>${esc(full)}</title>`;
    if (id === focus) {
      nodes += `<circle cx="${x}" cy="${y}" r="12" fill="none" class="focus"/>`;
    }
    nodes += `<circle cx="${x}" cy="${y}" r="${here ? 7 : 4}" fill="${here ? '#ff5a5a' : '#5f86a8'}" data-room="${id}"${here ? ' class="here"' : ''}/>`;
    nodes += `<text x="${x + 8}" y="${y + 3}" fill="#7d8794" font-size="10">$${hex(id)}</text>`;
    if (nm && nm !== '?') {
      const short = nm.length > 16 ? nm.slice(0, 15) + '…' : nm;
      nodes += `<text x="${x + 8}" y="${y + 14}" fill="#aab4bf" font-size="9">${esc(short)}</text>`;
    }
    const who = npc.get(id);
    if (who && who.length) {
      nodes += `<text x="${x + 8}" y="${y + 25}" fill="#c9b46a" font-size="9">${esc(who.join(', '))}</text>`;
    }
    nodes += `</g>`;
  }
  const svg = `<svg viewBox="0 0 ${W} ${H}" width="100%">${edges}${nodes}</svg>`;
  return { svg, W, H, at };
}

const MINI_ZOOM = 4;   // zoom par defaut de la mini-carte, centree joueur

function drawMap(playerRoom) {
  const m = buildMapSvg(playerRoom, -1);
  if (!m) { $('#map-svg').innerHTML = '(carte indisponible)'; return; }
  $('#map-svg').innerHTML = m.svg;
  const c = playerRoom >= 0 ? m.at(playerRoom) : [m.W / 2, m.H / 2];
  if (miniView.W !== m.W || miniView.H !== m.H) {
    resetView(miniView, m.W, m.H, c[0], c[1], MINI_ZOOM);
  } else if (playerRoom >= 0
    && (c[0] < miniView.x || c[0] > miniView.x + miniView.w
      || c[1] < miniView.y || c[1] > miniView.y + miniView.h)) {
    // joueur sorti du champ : recentre sur lui, garde son zoom
    const z = miniView.W / miniView.w;
    resetView(miniView, m.W, m.H, c[0], c[1], z);
  }
  applyView($('#map-svg'), miniView);
}

// --- modale : carte des lieux en grand (clic sur la carte) ---
function roomName(id) {
  return id >= 0 && M._hob_room_name(id)
    ? M.UTF8ToString(M._hob_room_name(id)) : '?';
}

// --- zoom molette/pinch + pan glisser, partage modale + mini-carte ---
const MAX_ZOOM = 8;   // zoom max : largeur vue = W/8 ; zoom min = carte entiere

const clampv = (v, a, b) => Math.max(a, Math.min(b, v));

function applyView(box, v) {
  const svg = box.querySelector('svg');
  if (!svg || !v.W) return;
  svg.setAttribute('viewBox', `${v.x} ${v.y} ${v.w} ${v.h}`);
}

function resetView(v, W, H, cx, cy, zoom) {
  v.W = W; v.H = H;
  v.w = W / zoom;
  v.h = H / zoom;
  v.x = clampv(cx - v.w / 2, 0, W - v.w);
  v.y = clampv(cy - v.h / 2, 0, H - v.h);
}

function zoomView(box, v, mx, my, factor) {
  const w0 = v.w;
  const w1 = clampv(w0 * factor, v.W / MAX_ZOOM, v.W);
  const h1 = w1 * (v.H / v.W);
  const k = w1 / w0;
  v.x = clampv(mx - (mx - v.x) * k, 0, v.W - w1);
  v.y = clampv(my - (my - v.y) * k, 0, v.H - h1);
  v.w = w1;
  v.h = h1;
  applyView(box, v);
}

// molette + glisser + pinch sur un conteneur de carte ; getView rend son etat
function attachPanZoom(box, getView) {
  const pts = new Map();
  let pinch = null;
  box.addEventListener('wheel', (e) => {
    const v = getView();
    const svg = box.querySelector('svg');
    if (!svg || !v.W) return;
    e.preventDefault();
    const r = svg.getBoundingClientRect();
    const mx = v.x + ((e.clientX - r.left) / r.width) * v.w;
    const my = v.y + ((e.clientY - r.top) / r.height) * v.h;
    // zoom proportionnel a l'amplitude du scroll (doux au touchpad)
    const unit = e.deltaMode === 1 ? 16 : 1;
    zoomView(box, v, mx, my, Math.pow(1.004, -e.deltaY * unit));
  }, { passive: false });
  box.addEventListener('pointerdown', (e) => {
    const v = getView();
    const svg = box.querySelector('svg');
    if (!svg || !v.W) return;
    svg.setPointerCapture(e.pointerId);
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]) };
    }
    box._dragMoved = 0;
    svg.classList.add('dragging');
  });
  box.addEventListener('pointermove', (e) => {
    const v = getView();
    const svg = box.querySelector('svg');
    if (!svg || !pts.has(e.pointerId)) return;
    const prev = pts.get(e.pointerId);
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    box._dragMoved = (box._dragMoved || 0)
      + Math.abs(e.clientX - prev[0]) + Math.abs(e.clientY - prev[1]);
    const r = svg.getBoundingClientRect();
    if (pts.size === 2 && pinch) {
      const [a, b] = [...pts.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (d > 0 && pinch.d > 0) {
        const mx = v.x + (((a[0] + b[0]) / 2 - r.left) / r.width) * v.w;
        const my = v.y + (((a[1] + b[1]) / 2 - r.top) / r.height) * v.h;
        zoomView(box, v, mx, my, pinch.d / d); // doigts ecartes = zoom avant
      }
      return;
    }
    const k = v.w / r.width;
    v.x = clampv(v.x - (e.clientX - prev[0]) * k, 0, v.W - v.w);
    v.y = clampv(v.y - (e.clientY - prev[1]) * k, 0, v.H - v.h);
    applyView(box, v);
  });
  for (const ev of ['pointerup', 'pointercancel']) {
    box.addEventListener(ev, (e) => {
      pts.delete(e.pointerId);
      if (pts.size < 2) pinch = null;
      if (!pts.size) box.querySelector('svg')?.classList.remove('dragging');
    });
  }
}

const modalView = { W: 0, H: 0, x: 0, y: 0, w: 0, h: 0 };
const miniView = { W: 0, H: 0, x: 0, y: 0, w: 0, h: 0 };
attachPanZoom($('#modal-map'), () => modalView);
attachPanZoom($('#map-svg'), () => miniView);

let mapFocus = -1;

function updateModalTitle() {
  if (!$('#modal-about').hidden) {
    $('#modal-title').textContent = L('About', 'À propos');
  } else if (!$('#modal-disclaimer').hidden) {
    $('#modal-title').textContent = L('Warning', 'Avertissement');
  } else {
    $('#modal-title').textContent = mapFocus >= 0
      ? L(`Map — $${hex(mapFocus)} ${roomName(mapFocus)}`,
          `Carte — $${hex(mapFocus)} ${roomName(mapFocus)}`)
      : t('map_title');
  }
}

function openMapModal(focus) {
  const player = M._hob_player_room();
  const m = buildMapSvg(player, focus);
  if (!m) return;
  mapFocus = focus;
  $('#modal-map').innerHTML = m.svg;
  const c = focus >= 0 ? m.at(focus)
    : player >= 0 ? m.at(player) : [m.W / 2, m.H / 2];
  resetView(modalView, m.W, m.H, c[0], c[1], 3);
  applyView($('#modal-map'), modalView);
  $('#modal-map').hidden = false;
  $('#modal-about').hidden = true;
  $('#modal-disclaimer').hidden = true;
  $('#modal').classList.remove('hidden');
  updateModalTitle();
}

function openAboutModal() {
  $('#modal-about').hidden = false;
  $('#modal-map').hidden = true;
  $('#modal-disclaimer').hidden = true;
  $('#modal').classList.remove('hidden');
  updateModalTitle();
}

function openDisclaimerModal() {
  $('#modal-disclaimer').hidden = false;
  $('#modal-about').hidden = true;
  $('#modal-map').hidden = true;
  $('#modal').classList.remove('hidden');
  updateModalTitle();
}

function closeModal() { $('#modal').classList.add('hidden'); }

// --- autoplay : rejoue la solution (docs/game_solution.md, Annexe 2) ---
function sawVictory() { return $('#screen').textContent.includes(EXPECTED_VICTORY); }

function startAutoplay() {
  closeModal();
  M._hob_slot_len(SLOT.BLOB, 0);   /* cold boot garanti : ignore toute
                                      sauvegarde locale (polluerait $E800) */
  M._hob_init();
  textLen = 0;
  $('#screen').textContent = '';
  M._hob_boot();
  drainText();
  refreshLive();
  /* Trace memoire (debug mem_diff.py) : sync post-boot + 1 delta/tour. */
  M._hob_mem_trace(1);
  memFrames = [new TextEncoder().encode('@@M\n'),
               M.HEAPU8.slice(M._hob_mem(), M._hob_mem() + M._hob_mem_len())];
  autoIdx = 0;
  autoPlaying = true;
  $('#btn-auto').textContent = 'STOP';
  $('#cmd').disabled = true;
  autoStep();
}

function autoStep() {
  if (!autoPlaying) return;
  if (autoIdx >= SOLUTION.length) { stopAutoplay(); return; }
  const i = autoIdx;
  autoIdx++;
  setStatus(`AUTO PLAY ${autoIdx}/${SOLUTION.length}`,
            `AUTO PLAY ${autoIdx}/${SOLUTION.length}`);
  sendCommand(SOLUTION[i]);
  if (memFrames) {
    const p = M._hob_memdiff_ptr(), n = M._hob_memdiff_len();
    memFrames.push(M.HEAPU8.slice(p, p + n));
  }
  autoTimer = setTimeout(autoStep, AUTO_DELAY);
}

function stopAutoplay() {
  autoPlaying = false;
  if (autoTimer) { clearTimeout(autoTimer); autoTimer = null; }
  $('#btn-auto').textContent = t('btn_auto');
  $('#cmd').disabled = false;
  $('#cmd').focus();
  const won = sawVictory();
  const done = autoIdx >= SOLUTION.length;
  setStatus(won ? 'AUTO PLAY — victory!'
                : done ? 'AUTO PLAY — finished' : 'AUTO PLAY — stopped',
            won ? 'AUTO PLAY — victoire !'
                : done ? 'AUTO PLAY — terminé' : 'AUTO PLAY — arrêté');
}

function setLang(lang) {
  LANG = lang === 'fr' ? 'fr' : 'en';
  setCookie('hobbit.lang', LANG);
  applyI18n();
  if (!$('#modal').classList.contains('hidden')) updateModalTitle();
  if (M) refreshLive();
}

for (const b of document.querySelectorAll('.lang-flag'))
  b.addEventListener('click', () => setLang(b.dataset.lang));

$('#map-svg').addEventListener('click', (e) => {
  if ($('#map-svg')._dragMoved > 4) { $('#map-svg')._dragMoved = 0; return; }
  const c = e.target.closest('circle[data-room]');
  openMapModal(c ? +c.dataset.room : -1);
});
$('#btn-about').addEventListener('click', openAboutModal);
$('#btn-copy').addEventListener('click', async () => {
  const txt = $('#screen').textContent;
  try {
    await navigator.clipboard.writeText(txt);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = txt;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
  setStatus('game text copied', 'texte du jeu copié');
  $('#cmd').focus();
});
$('#btn-mem').addEventListener('click', () => {
  if (!memFrames || !memFrames.length) {
    setStatus('no memory trace (run AUTO PLAY first)',
              'pas de trace mémoire (lance AUTO PLAY d\'abord)');
    return;
  }
  const blob = new Blob(memFrames, { type: 'application/octet-stream' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'mem_browser.bin';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  setStatus('memory trace downloaded', 'trace mémoire téléchargée');
  $('#cmd').focus();
});
$('#btn-auto').addEventListener('click', () => {
  if (autoPlaying) stopAutoplay(); else openDisclaimerModal();
});
$('#auto-confirm').addEventListener('click', startAutoplay);
$('#auto-cancel').addEventListener('click', closeModal);
$('#modal-close').addEventListener('click', closeModal);
$('#modal').addEventListener('click', (e) => { if (e.target.id === 'modal') closeModal(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

// --- intro FR/EN : overlay a chaque chargement, sauf ?skip_intro.
// Les deux colonnes s'affichent ensemble (independant du toggle EN/FR) ;
// marked (MIT) est vendore sous src/web/vendor/, charge seulement si affiche. ---
const SKIP_INTRO = new URLSearchParams(location.search).has('skip_intro');
if (SKIP_INTRO) $('#intro').classList.add('hidden');

async function loadIntro() {
  if (SKIP_INTRO) return;
  const { marked } = await import('./vendor/marked.esm.js');
  const [fr, en] = await Promise.all([
    fetch('intro.fr.md').then((r) => { if (!r.ok) throw new Error(`intro.fr.md: ${r.status}`); return r.text(); }),
    fetch('intro.en.md').then((r) => { if (!r.ok) throw new Error(`intro.en.md: ${r.status}`); return r.text(); }),
  ]);
  $('#intro-fr').innerHTML = marked.parse(fr);
  $('#intro-en').innerHTML = marked.parse(en);
}

$('#intro-play').addEventListener('click', () => {
  $('#intro').classList.add('hidden');
  $('#cmd').focus();
});
loadIntro();

applyI18n();

async function loadBlobFromStorage() {
  const saved = localStorage.getItem(SAVE_KEY);
  if (!saved) { M._hob_slot_len(SLOT.BLOB, 0); return false; }
  const bytes = Uint8Array.from(atob(saved), (c) => c.charCodeAt(0));
  M.HEAPU8.set(bytes, M._hob_slot(SLOT.BLOB));
  M._hob_slot_len(SLOT.BLOB, bytes.length);
  return true;
}

async function boot() {
  setStatus('compiling wasm…', 'compilation wasm…');
  M = await createHobbit({ locateFile: (f) => f });
  setStatus('loading files…', 'chargement des fichiers…');
  await fetchInto('hobbit.bin', SLOT.IMG);
  await fetchInto('basic10.rom', SLOT.ROM);
  await fetchInto('shim.bin', SLOT.SHIM);
  await fetchInto('snap.bin', SLOT.SNAP);
  const isSave = await loadBlobFromStorage();

  const rc = M._hob_init();
  if (rc !== 0) { setStatus(`init: error ${rc}`, `init: erreur ${rc}`); return; }
  setStatus('boot…', 'boot…');
  M._hob_boot();
  textLen = 0;
  drainText();
  if (isSave) {
    sendCommand('LOAD');   // restaure la sauvegarde locale
    sendCommand('');       // touches sacrifiees des invites cassette
    sendCommand('');
  }
  refreshLive();
  setStatus(isSave ? 'local save restored' : '',
            isSave ? 'sauvegarde locale restauree' : '');
  $('#cmd').focus();
}

$('#cmdline').addEventListener('submit', (e) => {
  e.preventDefault();
  memFrames = null;   /* commande manuelle : la trace autoplay n'est plus valide */
  const v = $('#cmd').value;
  $('#cmd').value = '';
  if (v.trim() && v !== cmdHistory[cmdHistory.length - 1]) cmdHistory.push(v);
  histPos = cmdHistory.length;
  histDraft = '';
  sendCommand(v);
});

$('#cmd').addEventListener('keydown', (e) => {
  if ((e.key !== 'ArrowUp' && e.key !== 'ArrowDown') || !cmdHistory.length) return;
  e.preventDefault();
  const el = $('#cmd');
  if (e.key === 'ArrowUp') {
    if (histPos === cmdHistory.length) histDraft = el.value;
    if (histPos > 0) histPos--;
  } else if (histPos < cmdHistory.length) {
    histPos++;
  }
  el.value = histPos === cmdHistory.length ? histDraft : cmdHistory[histPos];
  el.setSelectionRange(el.value.length, el.value.length);
});

$('#btn-save').addEventListener('click', () => {
  if (persistSave()) setStatus('saved (localStorage)', 'sauvegarde (localStorage)');
  else setStatus('nothing to save — type SAVE in the game',
                 'rien a sauver — tapez SAVE en jeu');
});

$('#btn-load').addEventListener('click', async () => {
  if (!(await loadBlobFromStorage())) {
    setStatus('no save', 'pas de sauvegarde'); return;
  }
  M._hob_init();
  textLen = 0;
  $('#screen').textContent = '';
  M._hob_boot();
  drainText();
  sendCommand('LOAD');
  sendCommand('');
  sendCommand('');
  refreshLive();
  setStatus('save reloaded', 'sauvegarde rechargee');
  $('#cmd').focus();
});

boot().catch((e) => {
  setStatus('error: ' + e.message, 'erreur: ' + e.message);
  console.error(e);
});

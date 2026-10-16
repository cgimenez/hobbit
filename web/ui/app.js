import createHobbit from './hobbit.js';

const $ = (s) => document.querySelector(s);
const enc = new TextEncoder();
const dec = new TextDecoder();

const SLOT = { IMG: 0, ROM: 1, SHIM: 2, SNAP: 3, BLOB: 4 };
const SAVE_KEY = 'hobbit.oric.save';
const ATTR = ['l', 'F', 'f', 'b', '*', 'o', 'A', 'v']; // bit0..7
const PAL = [[0,0,0],[255,0,0],[0,255,0],[255,255,0],
             [0,0,255],[255,0,255],[0,255,255],[255,255,255]];

let M = null;
let textLen = 0;
let busy = false;

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
  if (persistSave()) $('#status').textContent = 'sauvegarde enregistree (localStorage)';
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
  const rows = [];
  for (let i = 0; i < n; i++) {
    const key = M._hob_obj_key(i);
    const flags = M._hob_obj_field(i, 6);
    const alive = M._hob_obj_alive(i);
    const eloc = M._hob_obj_field(i, 7);
    const carrier = M._hob_obj_carrier(i);
    let attrs = '';
    for (let b = 0; b < 8; b++) attrs += (flags & (1 << b)) ? ATTR[b] : '.';
    const cls = key === 0x00 ? 'player' : (alive ? '' : 'dead');
    rows.push(`<tr class="${cls}"><td>$${hex(key)}</td>` +
      `<td>${esc(M.UTF8ToString(M._hob_obj_name(i)))}</td>` +
      `<td>${eloc < 0 ? '—' : '$' + hex(eloc)}</td>` +
      `<td>${carrier < 0 ? '—' : '$' + hex(carrier)}</td>` +
      `<td>${alive ? M._hob_obj_field(i, 4) : '✝'}</td>` +
      `<td class="attrs">${attrs}</td></tr>`);
  }
  $('#objs tbody').innerHTML = rows.join('');
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function drawVector(room) {
  const cv = $('#vec');
  const empty = $('#vec-empty');
  const ptr = M._hob_vec_ptr();
  if (room < 0 || M._hob_vec_key(room) < 0 || !M._hob_vec_render(room, ptr)) {
    cv.style.display = 'none';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  cv.style.display = 'block';
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

function drawMap(playerRoom) {
  const n = M._hob_room_count();
  if (!n) { $('#map-svg').textContent = '(carte indisponible)'; return; }
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
    nodes += `<circle cx="${x}" cy="${y}" r="${here ? 7 : 4}" fill="${here ? '#ff5a5a' : '#5f86a8'}"${here ? ' class="here"' : ''}/>`;
    nodes += `<text x="${x + 8}" y="${y + 3}" fill="#7d8794" font-size="10">$${hex(id)}</text>`;
    const who = npc.get(id);
    if (who && who.length) {
      nodes += `<text x="${x + 8}" y="${y + 14}" fill="#c9b46a" font-size="9">${esc(who.join(', '))}</text>`;
    }
  }
  $('#map-svg').innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%">${edges}${nodes}</svg>`;
}

async function loadBlobFromStorage() {
  const saved = localStorage.getItem(SAVE_KEY);
  if (!saved) { M._hob_slot_len(SLOT.BLOB, 0); return false; }
  const bytes = Uint8Array.from(atob(saved), (c) => c.charCodeAt(0));
  M.HEAPU8.set(bytes, M._hob_slot(SLOT.BLOB));
  M._hob_slot_len(SLOT.BLOB, bytes.length);
  return true;
}

async function boot() {
  $('#status').textContent = 'compilation wasm…';
  M = await createHobbit({ locateFile: (f) => f });
  $('#status').textContent = 'chargement des fichiers…';
  await fetchInto('hobbit.bin', SLOT.IMG);
  await fetchInto('basic10.rom', SLOT.ROM);
  await fetchInto('shim.bin', SLOT.SHIM);
  await fetchInto('snap.bin', SLOT.SNAP);
  const isSave = await loadBlobFromStorage();

  const rc = M._hob_init();
  if (rc !== 0) { $('#status').textContent = `init: erreur ${rc}`; return; }
  $('#status').textContent = 'boot…';
  M._hob_boot();
  textLen = 0;
  drainText();
  if (isSave) {
    sendCommand('LOAD');   // restaure la sauvegarde locale
    sendCommand('');       // touches sacrifiees des invites cassette
    sendCommand('');
  }
  refreshLive();
  $('#status').textContent = isSave ? 'sauvegarde locale restauree'
                                    : 'pret — tapez une commande';
  $('#cmd').focus();
}

$('#cmdline').addEventListener('submit', (e) => {
  e.preventDefault();
  const v = $('#cmd').value;
  $('#cmd').value = '';
  sendCommand(v);
});

$('#btn-save').addEventListener('click', () => {
  if (persistSave()) $('#status').textContent = 'sauvegarde (localStorage)';
  else $('#status').textContent = 'rien a sauver — tapez SAVE en jeu';
});

$('#btn-load').addEventListener('click', async () => {
  if (!(await loadBlobFromStorage())) { $('#status').textContent = 'pas de sauvegarde'; return; }
  M._hob_init();
  textLen = 0;
  $('#screen').textContent = '';
  M._hob_boot();
  drainText();
  sendCommand('LOAD');
  sendCommand('');
  sendCommand('');
  refreshLive();
  $('#status').textContent = 'sauvegarde rechargee';
  $('#cmd').focus();
});

boot().catch((e) => {
  $('#status').textContent = 'erreur: ' + e.message;
  console.error(e);
});

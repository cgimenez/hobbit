/* Smoke test Node : charge le wasm, boot jusqu'au prompt, joue une commande.
 * Usage : node dev/smoke.mjs [--serve [--memfd N]] [cmdfile]
 * Lit les fichiers depuis build/wasm/ (meme repertoire que l'image servie).
 *   --serve : mode serveur lockstep (cf. scripts/mem_diff.py) : trace
 *     memoire activee apres boot ; chaque ligne de stdin (meme vide) = 1
 *     hob_run ; snapshot post-boot "@@M" puis delta "@@D" par tour
 *     (protocol.md §4.3) ecrits sur le fd --memfd (defaut 3).
 */
import createHobbit from '../build/wasm/hobbit.js';
import { readFileSync, readSync, writeSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const build = join(here, '..', 'build', 'wasm');

let serve = false, memfd = 3, cmdfile = null;
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a === '--serve') serve = true;
  else if (a === '--memfd' && i + 1 < process.argv.length) memfd = +process.argv[++i];
  else if (!cmdfile) cmdfile = a;
}

const M = await createHobbit();

function load(file, slot) {
  const b = readFileSync(join(build, file));
  M.HEAPU8.set(b, M._hob_slot(slot));
  M._hob_slot_len(slot, b.length);
}

load('hobbit.bin', 0);
load('basic10.rom', 1);
load('shim.bin', 2);
load('snap.bin', 3);
M._hob_slot_len(4, 0);

const rc = M._hob_init();
if (rc !== 0) { console.error('hob_init =', rc); process.exit(1); }

/* Ecriture bouclee (pipes : writeSync peut etre partiel). */
function writeAll(fd, u8) {
  let off = 0;
  const buf = Buffer.from(u8.buffer, u8.byteOffset, u8.byteLength);
  while (off < buf.length) off += writeSync(fd, buf, off);
}
function memWrite(ptr, len) {
  writeAll(memfd, M.HEAPU8.subarray(ptr, ptr + len));
}

/* Lignes de stdin, lecture synchrone (\r internes preserves, \n retire). */
function* stdinLines() {
  const chunk = Buffer.alloc(65536);
  let acc = Buffer.alloc(0), n;
  for (;;) {
    try { n = readSync(0, chunk, 0, chunk.length, null); }
    catch { return; }
    if (n <= 0) return;
    acc = Buffer.concat([acc, chunk.subarray(0, n)]);
    let i;
    while ((i = acc.indexOf(0x0a)) >= 0) {
      let line = acc.subarray(0, i).toString('latin1');
      if (line.endsWith('\r')) line = line.slice(0, -1);
      yield line;
      acc = acc.subarray(i + 1);
    }
  }
}

let textLen = 0;
function drain() {
  const len = M._hob_text_len();
  if (len > textLen) {
    process.stdout.write(new TextDecoder().decode(
      M.HEAPU8.subarray(M._hob_text_ptr() + textLen, M._hob_text_ptr() + len)));
    textLen = len;
  }
}

function playOne(line) {
  M._hob_key_flush();
  for (const b of new TextEncoder().encode(line)) M._hob_key(b);
  M._hob_key(0x0d);
  return M._hob_run(0);
}

let rc1 = M._hob_boot();
drain();
console.error(`\n[boot rc=${rc1} texte=${M._hob_text_len()} lieu=$${M._hob_player_room().toString(16)}]`);

if (serve) {
  M._hob_mem_trace(1);
  writeAll(memfd, Buffer.from('@@M\n', 'latin1'));
  memWrite(M._hob_mem(), M._hob_mem_len());
  for (const line of stdinLines()) {
    const r = playOne(line);
    if (r === 1) console.error('  STALL pc=$' + M._hob_last_pc().toString(16) + ' autokey=' + M._hob_autokey_count() + ' shim=' + M._hob_shim_count() + ' kb7353=' + M._hob_kb7353_count());
    memWrite(M._hob_memdiff_ptr(), M._hob_memdiff_len());
    drain();
    console.error(`[${line} rc=${r} lieu=$${M._hob_player_room().toString(16)} objs=${M._hob_obj_count()} rooms=${M._hob_room_count()}]`);
  }
  process.exit(0);
}

const cmd = cmdfile ? readFileSync(cmdfile, 'utf8')
  .split('\n')
  .map((s) => s.replace(/\s+$/, ''))
  .filter((s) => s.length && !s.startsWith('#')) : ['OPEN DOOR', 'EAST', 'LOOK'];

for (const line of cmd) {
  const r = playOne(line);
  if (r===1) console.error('  STALL pc=$'+M._hob_last_pc().toString(16)+' autokey='+M._hob_autokey_count()+' shim='+M._hob_shim_count()+' kb7353='+M._hob_kb7353_count());
  drain();
  console.error(`[${line} rc=${r} lieu=$${M._hob_player_room().toString(16)} objs=${M._hob_obj_count()} rooms=${M._hob_room_count()}]`);
}
process.exit(0);

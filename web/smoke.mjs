/* Smoke test Node : charge le wasm, boot jusqu'au prompt, joue une commande.
 * Usage : node web/smoke.mjs [cmdfile]
 * Lit les fichiers depuis web/build/ (meme repertoire que l'image servie).
 */
import createHobbit from './build/hobbit.js';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const build = join(here, 'build');

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

let textLen = 0;
function drain() {
  const len = M._hob_text_len();
  if (len > textLen) {
    process.stdout.write(new TextDecoder().decode(
      M.HEAPU8.subarray(M._hob_text_ptr() + textLen, M._hob_text_ptr() + len)));
    textLen = len;
  }
}

const cmd = process.argv[2] ? readFileSync(process.argv[2], 'utf8')
  .split('\n')
  .map((s) => s.replace(/\s+$/, ''))
  .filter((s) => s.length && !s.startsWith('#')) : ['OPEN DOOR', 'EAST', 'LOOK'];

let rc1 = M._hob_boot();
drain();
console.error(`\n[boot rc=${rc1} texte=${M._hob_text_len()} lieu=$${M._hob_player_room().toString(16)}]`);

for (const line of cmd) {
  M._hob_key_flush();
  for (const b of new TextEncoder().encode(line)) M._hob_key(b);
  M._hob_key(0x0d);
  const r = M._hob_run(0);
  if (r===1) console.error('  STALL pc=$'+M._hob_last_pc().toString(16)+' autokey='+M._hob_autokey_count()+' shim='+M._hob_shim_count()+' kb7353='+M._hob_kb7353_count());
  drain();
  console.error(`[${line} rc=${r} lieu=$${M._hob_player_room().toString(16)} objs=${M._hob_obj_count()} rooms=${M._hob_room_count()}]`);
}
process.exit(0);

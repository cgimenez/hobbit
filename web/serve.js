/* Serveur statique dev (build/wasm) + HMR (hot reload).
 *
 * Zero dependance. Usage : node serve.js <dir> [port] [--no-hmr]
 *
 * HMR : surveille les sources (web/ui, src/core/,
 * src/6502/shim.s, src/6502/snap.s, Makefile racine) ; a chaque changement,
 * lance `make -C <racine> wasm assets` puis pousse un evenement SSE "reload" aux pages
 * connectees (le client HMR est injecte dans le HTML servi, index.html reste
 * propre). En cas d'echec de build, pousse "error" (pas de rechargement).
 */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const here = __dirname;            // web/
const root = path.resolve(here, '..');
const dir = path.resolve(process.argv[2] || path.join(root, 'build', 'wasm'));
const port = parseInt(process.argv[3] || '8000', 10);
const hmr = !process.argv.includes('--no-hmr');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.wasm': 'application/wasm',
  '.bin': 'application/octet-stream',
  '.rom': 'application/octet-stream',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
};

// ---- HMR ----
const clients = new Set();

function broadcast(obj) {
  const msg = `data: ${JSON.stringify(obj)}\n\n`;
  for (const c of clients) {
    try { c.write(msg); } catch { /* client parti */ }
  }
}

const HMR_CLIENT = `
<script>
(function () {
  var es = new EventSource('/__hmr');
  es.onmessage = function (e) {
    var d = JSON.parse(e.data);
    if (d.type === 'reload') location.reload();
    if (d.type === 'error') console.error('[hmr] build en echec:', d.msg);
  };
  es.onerror = function () { /* EventSource reconnecte tout seul */ };
})();
</script>
`;

let timer = null, building = false, pending = false, suppressUntil = 0;

function onChange(label) {
  return (event, filename) => {
    // macOS kqueue emet souvent 2 evenements par sauvegarde (rename+change) :
    // on ignore ceux qui arrivent juste apres un build.
    if (Date.now() < suppressUntil) return;
    clearTimeout(timer);
    timer = setTimeout(runBuild, 150);
  };
}

function runBuild() {
  if (building) { pending = true; return; }
  building = true;
  process.stderr.write('[hmr] make wasm assets...\n');
  const env = { ...process.env };
  if (!env.EMSDK_PYTHON) env.EMSDK_PYTHON = '/opt/local/bin/python3.14';
  const child = spawn('make', ['-C', root, 'wasm', 'assets'], {
    stdio: ['ignore', 'ignore', 'inherit'], env,
  });
  child.on('exit', (code) => {
    building = false;
    suppressUntil = Date.now() + 300;
    if (code === 0) {
      process.stderr.write('[hmr] reload\n');
      broadcast({ type: 'reload' });
    } else {
      broadcast({ type: 'error', msg: `make a echoue (code ${code})` });
    }
    if (pending) { pending = false; runBuild(); }
  });
}

function watch(target, opts) {
  try { fs.watch(target, opts, onChange(path.basename(target))); }
  catch (e) { process.stderr.write(`[hmr] watch ${target}: ${e.message}\n`); }
}

if (hmr) {
  for (const d of ['ui']) {
    watch(path.join(here, d), { recursive: true });
  }
  watch(path.join(root, 'src', 'core'), { recursive: true });
  // src/native (hote natif) exclu : ne participe pas au build wasm.
  // src/6502 (shim.s/snap.s) : recursif ; Makefile racine : le fichier seul
  // (pas le dossier racine, pour ne pas boucler sur build/wasm dont les
  // octets changent a chaque build).
  watch(path.join(root, 'src', '6502'), { recursive: true });
  watch(path.join(root, 'Makefile'), {});
  process.stderr.write('[hmr] surveillance des sources active\n');
}

// ---- HTTP ----
http.createServer((req, res) => {
  const url = req.url.split('?')[0];

  if (url === '/__hmr') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Cross-Origin-Resource-Policy': 'same-origin',
    });
    res.write(': hmr\n\n');
    clients.add(res);
    const ka = setInterval(() => { try { res.write(': ping\n\n'); } catch {} }, 15000);
    req.on('close', () => { clearInterval(ka); clients.delete(res); });
    return;
  }

  let rel = decodeURIComponent(url);
  if (rel === '/') rel = '/index.html';
  const file = path.join(dir, path.normalize(rel).replace(/^(\.\.[\\/])+/, ''));
  if (!file.startsWith(dir)) {
    res.writeHead(403); res.end('forbidden'); return;
  }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    const ext = path.extname(file);
    const headers = {
      'Content-Type': TYPES[ext] || 'application/octet-stream',
      'Cache-Control': 'no-store',   // dev : jamais de cache
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    };
    if (hmr && ext === '.html') {
      const html = data.toString('utf8').replace('</body>', `${HMR_CLIENT}</body>`);
      headers['Content-Length'] = Buffer.byteLength(html);
      res.writeHead(200, headers);
      res.end(html);
      return;
    }
    res.writeHead(200, headers);
    res.end(data);
  });
}).listen(port, () => console.log(`serve ${dir} -> http://localhost:${port}${hmr ? ' (hmr)' : ''}`));

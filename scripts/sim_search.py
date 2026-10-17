#!/usr/bin/env python3
"""Recherche parallele a froid sur sim65 (moteur unique, pas d'emu.cpp).

Chaque tache = un run froid COMPLET (reset $2C00, RNG continu, sans
LOAD/SAVE) : prefixe + suffixe, keystream pipe sur stdin, capture stdout
-> fichier, decodage ASCII (sim_play), juge texte. Fichiers par worker :
aucun partage. Image froide solveur (build/sim/hobbit_solver.sim, cf.
sim_pack.py --solver) : memes octets que le WASM (hors glue).

Usage :
  .venv/bin/python scripts/sim_search.py --prefix prefix.txt \
      --candidates cands.txt [--workers 11] [--image IMG] [--timeout S]
  prefix.txt : 1 commande/ligne (rejouees depuis le boot froid).
  cands.txt  : 1 suffixe/ligne, commandes separees par '|'.
Sortie : VERDICT <tab> suffixe <tab> wall <tab> extrait.
Verdicts : WIN/HALLS/DRAGON/GATE/LOC/DEAD/STALL/SAME/ERR.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SIM65 = ROOT / "tools" / "cc65" / "bin" / "sim65"
DEF_IMAGE = ROOT / "build" / "sim" / "hobbit_solver.sim"
SIM_PLAY = HERE / "sim_play.py"
TMP = Path("/tmp/simsearch")
TMP.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(HERE))
from solver_run import Capture, clean_line  # noqa: E402

RX_WIN = re.compile(r"cheering crowd of dwarves", re.I)
RX_DRAGON = re.compile(r"dragon is dead", re.I)
RX_HALLS = re.compile(r"dragon sleeps|halls where the dragon", re.I)
RX_GATE = re.compile(r"forest gate", re.I)
RX_DEAD = re.compile(
    r"you (are|have been) (killed|dead)|swept forcefully|drops from above"
    r"|stings|starved|fallen|drowned|burnt|eaten", re.I)


def judge(text: str, ok: bool) -> str:
    """Verdict sur le texte complet (priorite decroissante)."""
    if not ok:
        return "STALL"
    if RX_WIN.search(text):
        return "WIN"
    if RX_DRAGON.search(text):
        return "DRAGON"
    if RX_DEAD.search(text):
        return "DEAD"
    if RX_HALLS.search(text):
        return "HALLS"
    if RX_GATE.search(text):
        return "GATE"
    return "LOC"


def _decoded_lines(raw: bytes) -> list[str]:
    """Decode le flux ASCII brut en lignes nettoyees (sans attendre EOF)."""
    cap = Capture()
    cap.feed(raw)
    raws = [bytes(l) for l in cap.alines]
    if cap.cur:
        raws.append(bytes(cap.cur))
    return [clean_line(l) for l in raws if clean_line(l).strip()]


def cold_run(cmds: list[str], worker: int, image: str, cycles: str,
             timeout: float, stall_after: float = 180.0) -> dict:
    """Run froid : keystream pipe, kill des que le suffixe a repondu.

    Envoie prefixe+suffixe d'un coup ; scrute la capture jusqu'a voir
    l'echo du DERNIER suffixe suivi d'un prompt, puis tue sim65 (aucun
    WAIT idle, verdicts propres). Juge le texte complet.
    """
    keys = TMP / f"keys_{worker}.bin"
    rawp = TMP / f"out_{worker}.bin"
    suffix = cmds[-1] if cmds else ""
    stream = b"".join(c.encode("ascii") + b"\r" for c in cmds) + b"\r" * 3
    keys.write_bytes(stream)  # copie de secours/debug (stdin effectif = pipe)
    t0 = time.time()
    proc = None
    try:
        with open(rawp, "wb") as fout:
            fout.truncate(0)
            # stdin = PIPE tenu OUVERT : apres les octets envoyes, le jeu
            # BLOQUE en lecture (pas d'EOF -> pas de WAIT idle authentique).
            # Sans ca (fichier/EOF), le poll serre declenche l'auto-WAIT.
            proc = subprocess.Popen(
                [str(SIM65), "-x", str(cycles), str(image)],
                stdin=subprocess.PIPE, stdout=fout, stderr=subprocess.DEVNULL)
            proc.stdin.write(stream)
            proc.stdin.flush()
            needle = "> " + suffix + "."
            t1 = time.time()
            last_size = -1
            last_grow = t1
            while time.time() - t1 < timeout:
                if proc.poll() is not None:
                    break
                try:
                    sz = rawp.stat().st_size
                except OSError:
                    sz = 0
                now = time.time()
                if sz != last_size:
                    last_size = sz
                    last_grow = now
                elif now - last_grow > stall_after:
                    break  # silence prolonge : stall probable (pas de prints)
                with open(rawp, "rb") as fr:
                    lines = _decoded_lines(fr.read())
                for i, ln in enumerate(lines):
                    if ln.startswith(needle):
                        # Echo vu ; reponse complete si prompt suivant present.
                        if any(m.startswith(">") for m in lines[i + 1:]):
                            raise _Done
                        break
                time.sleep(0.3)
    except _Done:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            if proc is not None:
                proc.kill()
        except Exception:
            pass
        return {"verdict": "ERR", "text": "", "wall": time.time() - t0,
                "reason": f"{type(e).__name__}: {e}"}
    try:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        dec = subprocess.run(
            [sys.executable, str(SIM_PLAY)], input=rawp.read_bytes(),
            capture_output=True, timeout=60)
        text = dec.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return {"verdict": "ERR", "text": "", "wall": time.time() - t0,
                "reason": f"{type(e).__name__}: {e}"}
    # Timeout (= pas de reponse complete) sans marqueur fort = STALL.
    v = judge(text, True)
    if v == "LOC":
        # Distingue LOC (progres) de STALL (suffixe non consomme) : echo absent ?
        if suffix and ("> " + suffix + ".") not in text:
            v = "STALL"
    return {"verdict": v, "text": text, "wall": time.time() - t0, "reason": ""}


class _Done(Exception):
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--image", default=str(DEF_IMAGE))
    ap.add_argument("--cycles", default="1000000000")
    ap.add_argument("--timeout", type=float, default=600.0)
    a = ap.parse_args()

    prefix: list[str] = []
    if a.prefix:
        prefix = [l.rstrip("\n") for l in open(a.prefix, encoding="utf-8")
                  if l.strip() and not l.startswith("#")]
    cands: list[list[str]] = []
    for l in open(a.candidates, encoding="utf-8"):
        l = l.rstrip("\n")
        if not l.strip() or l.startswith("#"):
            continue
        cands.append([c.strip() for c in l.split("|") if c.strip()])
    if not cands:
        print("aucun candidat", file=sys.stderr)
        return 1

    print(f"# {len(prefix)} prefixe + {len(cands)} candidats, "
          f"{a.workers} workers, image {a.image}", file=sys.stderr, flush=True)
    results = []
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(cold_run, prefix + cmds, i % a.workers,
                          a.image, a.cycles, a.timeout): cmds
                for i, cmds in enumerate(cands)}
        for f in cf.as_completed(futs):
            cmds = futs[f]
            try:
                r = f.result(timeout=a.timeout + 120)
            except Exception as e:  # noqa: BLE001
                r = {"verdict": "ERR", "text": "", "wall": 0.0,
                     "reason": f"{type(e).__name__}: {e}"}
            results.append((cmds, r))
            tag = "|".join(cmds)
            snip = r["text"].replace("\n", " / ")[-200:]
            print(f"{r['verdict']}\t{tag}\twall={r['wall']:.0f}\t...{snip}",
                  flush=True)
    nwin = sum(1 for _, r in results if r["verdict"] == "WIN")
    print(f"# {nwin}/{len(results)} WIN", file=sys.stderr)
    return 0 if nwin else 2


if __name__ == "__main__":
    raise SystemExit(main())

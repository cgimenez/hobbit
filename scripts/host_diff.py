#!/usr/bin/env python3
"""Test differentiel natif vs WASM (option 1) : meme image, memes entrees,
memes octets en sortie. Les deux cotes partagent src/core/*.c + sim65 ;
seuls compilateur et backend I/O changent (cc/buffers vs emcc/JS).

Usage : .venv/bin/python scripts/host_diff.py [cmdfile]
  cmdfile : 1 commande/ligne (#... ignore, vides ignorees).
  Compare stdout (texte jeu) de :
    node dev/smoke.mjs <cmdfile>      (WASM, emcc)
    build/native/hobplay <cmdfile>      (natif, cc)
  Sortie exit 0 si byte-identique, 1 sinon (avec premier offset divergent).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CMDS = ["OPEN CHEST", "EAST", "NORTH\rSW", "WAIT", "WAIT",
                "NORTH", "GET KEY", "SW", "NORTHEAST", "UNLOCK DOOR",
                "OPEN DOOR", "NORTH", "GET SWORD", "GET ROPE"]


def run(argv, **kw):
    p = subprocess.run(argv, capture_output=True, cwd=ROOT, **kw)
    return p


def main() -> int:
    if len(sys.argv) > 1:
        cmdfile = sys.argv[1]
    else:
        cmdfile = str(ROOT / "build" / "host" / "diff_cmds.txt")
        Path(cmdfile).parent.mkdir(parents=True, exist_ok=True)
        Path(cmdfile).write_text("\n".join(DEFAULT_CMDS) + "\n",
                                 encoding="utf-8")

    w = run(["node", "dev/smoke.mjs", cmdfile])
    n = run(["build/native/hobplay", cmdfile])
    if w.returncode != 0:
        print(f"WASM rc={w.returncode}\n{w.stderr.decode()[-2000:]}")
        return 1
    if n.returncode != 0:
        print(f"natif rc={n.returncode}\n{n.stderr.decode()[-2000:]}")
        return 1
    if w.stdout == n.stdout:
        print(f"DIFF VIDE : {len(w.stdout)} o de texte jeu identiques "
              f"(natif cc == WASM emcc)")
        return 0
    for i, (a, b) in enumerate(zip(w.stdout, n.stdout)):
        if a != b:
            print(f"DIVERGENCE offset {i} : WASM={w.stdout[max(0,i-40):i+40]!r} "
                  f"natif={n.stdout[max(0,i-40):i+40]!r}")
            break
    else:
        print(f"prefixe commun, longueurs WASM={len(w.stdout)} "
              f"natif={len(n.stdout)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

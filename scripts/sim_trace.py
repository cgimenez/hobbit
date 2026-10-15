#!/usr/bin/env python3
"""Trace instruction ciblee du harnais sim65.

Lance `sim65 --trace` sur une image du harnais, lit le flux instruction par
instruction et ne garde que les executions dont le PC tombe dans une ou
plusieurs plages d'adresses (et, en option, N lignes de contexte apres chaque
hit). Sert a suivre le deroulement intra-commande des routines de resolution
de sortie / revision d'action ($358F-$3B74, $5A60-$5A6F) sans se noyer dans
le boot ni le rendu.

Le flux de trace (stdout+stderr) est filtrage en continu : les dumps binaires
du shim (@@FRAME/@@MEM) ne matchent pas le format de trace et sont ignores.

Usage :
  .venv/bin/python scripts/sim_trace.py --input cmdfile.txt \\
      [--image build/sim/hobbit_fast.sim] [--cycles N] \\
      [--range LO HI]... [--watch ADDR,...] [--context N] \\
      [--out /tmp/sim_trace.txt] [--max N]

Sortie : fichier de trace filtre + resume (compte par plage, sequence des
entrees de routine touchees).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM65 = ROOT / "tools/cc65/bin/sim65"

# Plages par defaut : moteur sortie/revision (bloc 4) + epilogue d'action.
DEFAULT_RANGES = [(0x358F, 0x3B74), (0x5A60, 0x5A6F)]

# Entrees de routine suivies par defaut (cibles JSR/JMP de la zone).
DEFAULT_WATCH = [
    0x358F, 0x359B, 0x35AE, 0x35E4, 0x35FD, 0x361C, 0x3622, 0x363E,
    0x3674, 0x3679, 0x3690, 0x36A5, 0x36BB, 0x36D5, 0x36DB,
    0x3790, 0x3804, 0x380A, 0x38A0, 0x38C9, 0x38E2, 0x38E5, 0x3928,
    0x3948, 0x3993, 0x39B1, 0x39B7, 0x39BE, 0x39CF, 0x39D3, 0x39EE,
    0x3A0B, 0x3A2D, 0x3A36, 0x3A6B, 0x3AB5, 0x3ADF, 0x3B21, 0x3B26,
    0x5A62,
]

RE_TRACE = re.compile(r"^\s*\d+\s+\d+\s+([0-9A-Fa-f]{4})\s")


def parse_args() -> dict:
    opt: dict = {
        "image": str(ROOT / "build/sim/hobbit_fast.sim"),
        "input": None,
        "cycles": 60_000_000,
        "ranges": list(DEFAULT_RANGES),
        "watch": list(DEFAULT_WATCH),
        "context": 0,
        "out": "/tmp/sim_trace.txt",
        "max": 500_000,
    }
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--image":
            opt["image"] = args[i + 1]; i += 2
        elif a == "--input":
            opt["input"] = args[i + 1]; i += 2
        elif a == "--cycles":
            opt["cycles"] = int(args[i + 1], 0); i += 2
        elif a == "--range":
            lo, hi = args[i + 1], args[i + 2]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                opt["ranges"].append((int(lo, 16), int(hi, 16))); i += 3
            else:
                i += 2
        elif a == "--watch":
            opt["watch"] = [int(x, 16) for x in args[i + 1].split(",") if x]; i += 2
        elif a == "--context":
            opt["context"] = int(args[i + 1]); i += 2
        elif a == "--out":
            opt["out"] = args[i + 1]; i += 2
        elif a == "--max":
            opt["max"] = int(args[i + 1]); i += 2
        else:
            print(f"option inconnue: {a}", file=sys.stderr)
            return {}
    if not opt["input"]:
        print("usage: sim_trace.py --input cmdfile.txt [...]; voir docstring",
              file=sys.stderr)
        return {}
    return opt


def in_ranges(pc: int, ranges: list[tuple[int, int]]) -> bool:
    return any(lo <= pc <= hi for lo, hi in ranges)


def main() -> int:
    opt = parse_args()
    if not opt:
        return 2
    if not SIM65.exists():
        print(f"sim65 introuvable: {SIM65}", file=sys.stderr)
        return 2
    img = Path(opt["image"])
    if not img.exists():
        print(f"image introuvable: {img}", file=sys.stderr)
        return 2

    cmd = [str(SIM65), "--trace", "-x", str(opt["cycles"]), str(img)]
    with open(opt["input"], "rb") as fin:
        proc = subprocess.Popen(cmd, stdin=fin, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    watch = set(opt["watch"])
    seq: list[int] = []
    per_range = [0] * len(opt["ranges"])
    kept = 0
    context_left = 0
    out_path = Path(opt["out"])
    with out_path.open("w") as fout:
        assert proc.stdout is not None
        for raw in proc.stdout:
            try:
                line = raw.decode("ascii", errors="replace")
            except Exception:
                line = ""
            m = RE_TRACE.match(line)
            if not m:
                if context_left > 0:
                    context_left -= 1
                    fout.write(line)
                    kept += 1
                continue
            pc = int(m.group(1), 16)
            hit = False
            for idx, (lo, hi) in enumerate(opt["ranges"]):
                if lo <= pc <= hi:
                    per_range[idx] += 1
                    hit = True
            if hit:
                fout.write(line)
                kept += 1
                context_left = opt["context"]
                if pc in watch:
                    seq.append(pc)
            elif context_left > 0:
                context_left -= 1
                fout.write(line)
                kept += 1
            if kept >= opt["max"]:
                break
    try:
        proc.terminate()
    except Exception:
        pass
    proc.wait()

    print(f"image     : {img}")
    print(f"cycles    : -x {opt['cycles']}")
    print(f"trace     : {kept} lignes -> {out_path}")
    for (lo, hi), n in zip(opt["ranges"], per_range):
        print(f"  plage ${lo:04X}-${hi:04X} : {n} instructions")
    print(f"entrees   : {len(seq)} hits")
    if seq:
        # compresse les repetitions consecutives de la meme entree
        short = [f"{seq[0]:04X}"]
        for a, b in zip(seq, seq[1:]):
            if b != a:
                short.append(f"{b:04X}")
        print("  sequence : " + " ".join(short))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Génère un listing assembleur annoté du bloc 4 de The Hobbit (Oric).

Le découpage code/données est déduit automatiquement par radare2 (`aaaa`),
puis da65 (cc65) produit le listing à partir d'un fichier d'information
(`disasm/hobbit.info`) et de `data/hobbit.bin`.

Prérequis : radare2 (`r2`) et da65 (paquet `cc65`).

Usage : .venv/bin/python scripts/disasm.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "data" / "hobbit.bin"
DISASM = ROOT / "disasm"
INFO = DISASM / "hobbit.info"
LISTING = DISASM / "block4.asm"

BASE = 0x0400
BLOCK1 = (0x0400, 0x0500)
BLOCK2 = (0x0500, 0x2BBD)
BLOCK3 = (0x7AC0, 0x91B1)
BLOCK4 = (0x2C00, 0x7A80)
ENTRY = 0x2C35

# Petites zones forcées en code (l'en-tête JMP $2C35 avant la table).
FORCED_CODE = [(0x2C00, 0x2C02), (0x2C35, 0x2C35)]

# Points d'entrée de la table de vecteurs en $2C05 (16 entrées JMP).
VECTORS = {
    0x2C00: "autorun",
    0x2C03: "ptr_block3",
    0x2C05: "vec_init",
    0x2C08: "vec_01",
    0x2C0B: "vec_02",
    0x2C0E: "vec_03",
    0x2C11: "vec_04",
    0x2C14: "vec_05",
    0x2C17: "vec_06",
    0x2C1A: "vec_07",
    0x2C1D: "vec_08",
    0x2C20: "vec_09",
    0x2C23: "vec_10",
    0x2C26: "vec_11",
    0x2C29: "keyin",
    0x2C2C: "print_cr",
    0x2C2F: "putchar",
    0x2C32: "main",
    0x2C35: "start",
}

# Routines ROM (issues du désassemblage 1.0 et 1.1, cf. docs/).
ROM_LABELS = {
    0xE5C6: "PUTBYTE_10",
    0xE630: "READBYTE_10",
    0xE696: "TAPESYNC_10",
    0xE6BA: "WRITELEADER_10",
    0xE6CA: "SETUPTAPE_10",
    0xF73C: "CHAR2SCR_10",
    0xF960: "RESETSTAT_10",
    0xE65E: "PUTBYTE_11",
    0xE6C9: "READBYTE_11",
    0xE735: "SYNCTAPE_11",
    0xE75A: "WRITELEADER_11",
    0xE76A: "SETUPTAPE_11",
    0xF77C: "CHAR2SCR_11",
    0xF9AA: "RESETSTAT_11",
}


def r2_functions() -> list[tuple[int, int]]:
    """Renvoie la liste (adresse, taille) des fonctions trouvées par r2.

    Le résultat de `afl` est mis en cache dans disasm/.r2_afl.txt.
    """
    cache = DISASM / ".r2_afl.txt"
    if cache.exists() and cache.stat().st_mtime >= BIN.stat().st_mtime:
        out = cache.read_text()
    else:
        cmd = [
            "r2", "-a", "6502", "-b", "8", "-m", f"0x{BASE:x}", "-q",
            "-e", "scr.color=0", "-e", "anal.timeout=300", "-e", "anal.hasnext=true",
            "-c", f"s 0x{ENTRY:x}; af; aaaa; afl",
            str(BIN),
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        cache.write_text(out)
    funcs: list[tuple[int, int]] = []
    for line in out.splitlines():
        m = re.match(r"0x([0-9a-f]+)\s+\d+\s+(\d+)\s", line)
        if m:
            funcs.append((int(m.group(1), 16), int(m.group(2))))
    return funcs


def merged_ranges(funcs: list[tuple[int, int]], lo: int, hi: int) -> list[list[int]]:
    ranges = sorted((a, a + sz - 1) for a, sz in funcs if lo <= a <= hi)
    merged: list[list[int]] = []
    for a, b in ranges:
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def merge(ranges: list[list[int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for a, b in sorted(ranges):
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def complement(ranges: list[list[int]], lo: int, hi: int) -> list[list[int]]:
    out: list[list[int]] = []
    cur = lo
    for a, b in ranges:
        if a > cur:
            out.append([cur, a - 1])
        cur = max(cur, b + 1)
    if cur <= hi:
        out.append([cur, hi])
    return out


def printable_ratio(data: bytes, a: int, b: int) -> float:
    chunk = data[a - BASE:b - BASE + 1]
    if not chunk:
        return 0.0
    ok = sum(1 for c in chunk if 0x20 <= c < 0x7F or c in (0x00, 0x0D))
    return ok / len(chunk)


def build_info(data: bytes, code_ranges: list[list[int]],
               data_ranges: list[list[int]]) -> str:
    named = {**VECTORS, **ROM_LABELS}
    lines = ['GLOBAL { CPU "6502"; PAGELENGTH 0; };']
    used: set[int] = set()
    # Zones de code détectées par radare2.
    for a, b in code_ranges:
        if a in named:
            name = named[a]
            used.add(a)
        else:
            name = f"code_{a:04X}"
        lines.append(
            f'RANGE {{ START ${a:04X}; END ${b:04X}; TYPE CODE; NAME "{name}"; }};'
        )
    # Trous : texte si très imprimable, sinon table d'octets.
    for a, b in data_ranges:
        kind = "TEXTTABLE" if printable_ratio(data, a, b) >= 0.6 else "BYTETABLE"
        lines.append(f"RANGE {{ START ${a:04X}; END ${b:04X}; TYPE {kind}; }};")
    for addr, name in named.items():
        if addr not in used:
            lines.append(f'LABEL {{ NAME "{name}"; ADDR ${addr:04X}; }};')
    return "\n".join(lines) + "\n"


def main() -> int:
    if not BIN.exists():
        print(f"{BIN} manquant : lancez scripts/extract.py", file=sys.stderr)
        return 1
    DISASM.mkdir(exist_ok=True)

    raw = BIN.read_bytes()
    funcs = r2_functions()
    lo, hi = BLOCK4

    # Cibles de la table de vecteurs ($2C05 : 16 x JMP absolu) : forcées en code.
    vec_targets = []
    for ea in range(0x2C05, 0x2C35, 3):
        vec_targets.append(raw[ea + 1 - BASE] | (raw[ea + 2 - BASE] << 8))
    extra = [list(r) for r in FORCED_CODE]
    extra += [[t, t + 47] for t in vec_targets]

    code = merge(merged_ranges(funcs, lo, hi) + extra)
    data = complement(code, lo, hi)

    INFO.write_text(build_info(raw, code, data))

    slice_path = Path("/tmp/hobbit_block4.bin")
    slice_path.write_bytes(raw[lo - BASE:hi - BASE + 1])

    covered = sum(b - a + 1 for a, b in code)
    print(f"bloc4 ${lo:04X}-${hi:04X} : {len(code)} zones code "
          f"({covered}/{hi - lo + 1} octets), {len(data)} zones données")

    cmd = [
        "da65", "-i", str(INFO), "-S", f"0x{lo:x}",
        "-o", str(LISTING), str(slice_path),
    ]
    subprocess.run(cmd, check=True)

    header = (
        "; ============================================================\n"
        "; The Hobbit (Oric, 1982) - bloc 4 ($2C00-$7A80)\n"
        "; Listing généré par scripts/disasm.py (radare2 + da65)\n"
        "; Charge en mémoire à $2C00, entrée autorun $2C00 -> $2C35.\n"
        "; ATTENTION : découpage code/données heuristique, à réviser.\n"
        "; ============================================================\n\n"
    )
    LISTING.write_text(header + LISTING.read_text())
    print(f"Listing écrit : {LISTING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

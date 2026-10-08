#!/usr/bin/env python3
"""Round-trip : réassemble disasm/block4.asm (ca65+ld65) et prouve le
byte-identique avec la tranche $2C00-$7A80 de data/hobbit.bin.

Sortie 0 si identique, 1 sinon (premier octet divergent affiché).

Usage : .venv/bin/python scripts/rebuild.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import BASE, BIN, BLOCK4, CA65, LD65, LISTING, ROOT  # noqa: E402

CFG = ROOT / "build" / "block4.cfg"
BUILD = ROOT / "build" / "sim"
OBJ = BUILD / "hobbit_block4.o"
OUT = BUILD / "hobbit_block4_rebuilt.bin"


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    for tool in (CA65, LD65):
        if not Path(tool).is_file():
            print(f"{tool} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
            return 1
    if not LISTING.is_file():
        print(f"{LISTING} manquant : lancez scripts/disasm.py")
        return 1
    lo, hi = BLOCK4
    subprocess.run([str(CA65), "-o", str(OBJ), str(LISTING)], check=True)
    subprocess.run([str(LD65), "-C", str(CFG), "-o", str(OUT), str(OBJ)], check=True)
    ref = BIN.read_bytes()[lo - BASE:hi - BASE + 1]
    got = OUT.read_bytes()
    if got == ref:
        print(f"Round-trip OK : {len(got)} octets byte-identiques (${lo:04X}-${hi:04X})")
        return 0
    n = min(len(got), len(ref))
    diff = next((i for i in range(n) if got[i] != ref[i]), n)
    print(f"Round-trip ÉCHEC : tailles rebuild={len(got)} ref={len(ref)}, "
          f"1er diff à +${diff:04X} (addr ${lo + diff:04X}) : "
          f"got ${got[diff]:02X} != ref ${ref[diff]:02X}" if diff < n
          else "même préfixe, tailles différentes")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Round-trip : réassemble disasm/<bloc>.asm (ca65+ld65) et prouve le
byte-identique avec la tranche correspondante de data/hobbit.bin.

Sortie 0 si identique, 1 sinon (premier octet divergent affiché).

Usage : .venv/bin/python scripts/disasm_rebuild.py [--block block1|block4]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import BASE, BIN, BLOCKS, CA65, LD65, ROOT  # noqa: E402

BUILD = ROOT / "build" / "sim"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block", default="block4", choices=sorted(BLOCKS))
    args = ap.parse_args()
    block = BLOCKS[args.block]

    BUILD.mkdir(parents=True, exist_ok=True)
    for tool in (CA65, LD65):
        if not Path(tool).is_file():
            print(f"{tool} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
            return 1
    if not block.listing.is_file():
        print(f"{block.listing} manquant : lancez scripts/disasm.py --block {block.key}")
        return 1
    lo, hi = block.lo, block.hi
    obj = BUILD / f"hobbit_{block.key}.o"
    out = BUILD / f"hobbit_{block.key}_rebuilt.bin"
    subprocess.run([str(CA65), "-o", str(obj), str(block.listing)], check=True)
    subprocess.run([str(LD65), "-C", str(block.cfg), "-o", str(out), str(obj)], check=True)
    ref = BIN.read_bytes()[lo - BASE:hi - BASE + 1]
    got = out.read_bytes()
    if got == ref:
        print(f"{block.key} : round-trip OK, {len(got)} octets byte-identiques "
              f"(${lo:04X}-${hi:04X})")
        return 0
    n = min(len(got), len(ref))
    diff = next((i for i in range(n) if got[i] != ref[i]), n)
    print(f"{block.key} : round-trip ÉCHEC, tailles rebuild={len(got)} ref={len(ref)}, "
          f"1er diff à +${diff:04X} (addr ${lo + diff:04X}) : "
          f"got ${got[diff]:02X} != ref ${ref[diff]:02X}" if diff < n
          else "même préfixe, tailles différentes")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

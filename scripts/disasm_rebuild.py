#!/usr/bin/env python3
"""Round-trip : réassemble disasm/<bloc>.asm (ca65+ld65) et prouve le
byte-identique avec la tranche correspondante de data/hobbit.bin.

Mode --all : réassemble les 4 blocs, les recolle à leurs adresses de
chargement (trous comblés de $00) et compare l'image complète $0400-$91B1
à data/hobbit.bin.

Sortie 0 si identique, 1 sinon (premier octet divergent affiché).

Usage : .venv/bin/python scripts/disasm_rebuild.py [--block block1|block2|block3|block4]
        .venv/bin/python scripts/disasm_rebuild.py --all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import BASE, BIN, BLOCKS, CA65, LD65, ROOT  # noqa: E402

BUILD = ROOT / "build" / "sim"


def assemble(block) -> bytes:
    """ca65 + ld65 le listing d'un bloc -> octets (taille = plage)."""
    BUILD.mkdir(parents=True, exist_ok=True)
    obj = BUILD / f"hobbit_{block.key}.o"
    out = BUILD / f"hobbit_{block.key}_rebuilt.bin"
    subprocess.run([str(CA65), "-o", str(obj), str(block.listing)], check=True)
    subprocess.run([str(LD65), "-C", str(block.cfg), "-o", str(out), str(obj)],
                   check=True)
    return out.read_bytes()


def check_tools() -> int:
    for tool in (CA65, LD65):
        if not Path(tool).is_file():
            print(f"{tool} manquant : toolchain attendue dans tools/cc65/bin "
                  f"(cf. AGENTS.md)")
            return 1
    return 0


def rebuild_block(block) -> int:
    if not block.listing.is_file():
        print(f"{block.listing} manquant : lancez scripts/disasm.py "
              f"--block {block.key}")
        return 1
    lo, hi = block.lo, block.hi
    got = assemble(block)
    ref = BIN.read_bytes()[lo - BASE:hi - BASE + 1]
    if got == ref:
        print(f"{block.key} : round-trip OK, {len(got)} octets byte-identiques "
              f"(${lo:04X}-${hi:04X})")
        return 0
    report_diff(block.key, lo, got, ref)
    return 1


def report_diff(key: str, lo: int, got: bytes, ref: bytes) -> None:
    n = min(len(got), len(ref))
    diff = next((i for i in range(n) if got[i] != ref[i]), n)
    if diff < n:
        print(f"{key} : round-trip ÉCHEC, tailles rebuild={len(got)} "
              f"ref={len(ref)}, 1er diff à +${diff:04X} "
              f"(addr ${lo + diff:04X}) : got ${got[diff]:02X} != "
              f"ref ${ref[diff]:02X}")
    else:
        print(f"{key} : round-trip ÉCHEC, même préfixe, tailles différentes "
              f"(rebuild={len(got)} ref={len(ref)})")


def rebuild_all() -> int:
    blocks = sorted(BLOCKS.values(), key=lambda b: b.lo)
    for b in blocks:
        if not b.listing.is_file():
            print(f"{b.listing} manquant : lancez scripts/disasm.py "
                  f"--block {b.key}")
            return 1
    base = min(b.lo for b in blocks)
    top = max(b.hi for b in blocks)
    image = bytearray(top - base + 1)  # trous = $00
    for b in blocks:
        got = assemble(b)
        exp = b.hi - b.lo + 1
        if len(got) != exp:
            print(f"{b.key} : taille rebuild={len(got)} != attendu {exp}")
            return 1
        image[b.lo - base:b.hi - base + 1] = got
        print(f"  {b.key} : ${b.lo:04X}-${b.hi:04X} ({exp} o) assemblé")
    ref = BIN.read_bytes()
    if base != BASE or len(ref) != len(image):
        print(f"image : base=${base:04X} taille={len(image)} vs "
              f"hobbit.bin base=${BASE:04X} taille={len(ref)} : incohérent")
        return 1
    holes = sum(1 for a in range(base, top + 1)
                if not any(b.lo <= a <= b.hi for b in blocks))
    if bytes(image) == ref:
        print(f"image complète ${base:04X}-${top:04X} : {len(image)} octets "
              f"byte-identiques ({len(blocks)} blocs + {holes} o de "
              f"remplissage $00)")
        return 0
    report_diff("image", base, bytes(image), ref)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block", default="block4", choices=sorted(BLOCKS))
    ap.add_argument("--all", action="store_true",
                    help="réassemble les 4 blocs et compare l'image complète")
    args = ap.parse_args()

    if check_tools():
        return 1
    if args.all:
        return rebuild_all()
    return rebuild_block(BLOCKS[args.block])


if __name__ == "__main__":
    raise SystemExit(main())

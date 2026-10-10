#!/usr/bin/env python3
"""Compare deux .tape (scripts/tape_save.py) bloc a bloc.

Usage : .venv/bin/python scripts/tape_diff.py sav/avant.tape sav/apres.tape
Sortie 0 si donnees identiques (headers dest/len compares separement),
1 sinon. Affiche par bloc : dest/len, nb d'octets differents, positions
et valeurs des premiers ecarts. Sert a valider LOAD (SAVE#2 vs SAVE#1 :
ecarts attendus = derive de ticks entre les deux saves) et a sonder la
mutation de l'etat en phase B.
"""

from __future__ import annotations

import sys
from pathlib import Path


def parse(path: Path) -> list[tuple[int, int, bytes]]:
    data = path.read_bytes()
    blocks: list[tuple[int, int, bytes]] = []
    p = 0
    while p < len(data):
        assert data[p] == 0x24, f"sync en offset {p} ({path})"
        hdr = data[p + 1:p + 10]
        end = (hdr[4] << 8) | hdr[5]
        dest = (hdr[6] << 8) | hdr[7]
        ln = (end - dest) & 0xFFFF
        assert data[p + 10] == 0x00, f"separateur ({path})"
        blocks.append((dest, ln, data[p + 11:p + 11 + ln]))
        p += 12 + ln
    return blocks


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: tape_diff.py avant.tape apres.tape")
        return 1
    a = parse(Path(sys.argv[1]))
    b = parse(Path(sys.argv[2]))
    fails = 0
    for i, ((da, la, ba), (db, lb, bb)) in enumerate(zip(a, b)):
        tag = f"bloc {i} (${da:04X}+${la:04X})"
        if (da, la) != (db, lb):
            print(f"{tag} : HEADERS DIFFERENTS (${db:04X}+${lb:04X}) -> ECHEC")
            fails += 1
            continue
        nd = sum(1 for x, y in zip(ba, bb) if x != y)
        if nd == 0 and len(ba) == len(bb):
            print(f"{tag} : identique ({la} o) OK")
        else:
            print(f"{tag} : {nd}/{la} octets differents")
            shown = 0
            for j, (x, y) in enumerate(zip(ba, bb)):
                if x != y and shown < 12:
                    print(f"    +${j:04X} : avant ${x:02X} vs apres ${y:02X}")
                    shown += 1
            fails += 1
    if len(a) != len(b):
        print(f"nb blocs : {len(a)} vs {len(b)} -> ECHEC")
        fails += 1
    print("RESULTAT :", "IDENTIQUE" if fails == 0 else f"{fails} BLOC(S) EN ECART")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verifie un LOAD : l'etat memoire restaure == le contenu du .tape.

Prend le .tape (scripts/save_tape.py) comme reference : chaque bloc
[dest len] donne l'image attendue en basse memoire. Prend le dernier
dump @@MEM par region dans frames.bin (les stubs $0417 dumpent apres
chaque bloc ; les dumps shim eventuels posterieurs ne couvrent que
$0000/$2B00) et compare. Seuls $00BE-$00D5 sont compares dans la page 0
(le reste bouge avec l'echo clavier).

Usage : .venv/bin/python scripts/tape_check.py sav/game.tape frames.bin
Sortie 0 si identique, 1 sinon (diffs affiches).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RE_MEM = re.compile(rb"@@MEM ([0-9A-F]{4}) ([0-9A-F]{4})\n")


def tape_image(path: Path) -> dict[int, bytes]:
    data = path.read_bytes()
    p = 0
    out: dict[int, bytes] = {}
    while p < len(data):
        assert data[p] == 0x24, f"sync en offset {p}"
        hdr = data[p + 1:p + 11]
        end = (hdr[4] << 8) | hdr[5]
        dest = (hdr[6] << 8) | hdr[7]
        ln = (end - dest) & 0xFFFF
        assert data[p + 11] == 0x00, f"separateur bloc dest=${dest:04X}"
        out[dest] = data[p + 12:p + 12 + ln]
        p += 13 + ln
    return out


def last_mems(frames: bytes) -> dict[int, bytes]:
    out: dict[int, bytes] = {}
    for m in RE_MEM.finditer(frames):
        addr, ln = int(m.group(1), 16), int(m.group(2), 16)
        payload = frames[m.end():m.end() + ln]
        if len(payload) == ln:
            out[addr] = payload
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: tape_check.py sav/game.tape frames.bin")
        return 1
    expected = tape_image(Path(sys.argv[1]))
    print("tape :", " ".join(f"${a:04X}+${len(d):04X}" for a, d in expected.items()))
    mems = last_mems(Path(sys.argv[2]).read_bytes())
    print("dumps :", " ".join(f"${a:04X}+${len(d):04X}" for a, d in sorted(mems.items())))
    fails = 0
    for dest, data in expected.items():
        if dest == 0x00BE:
            # page 0 : comparer $00BE-$00D5 via le dump $0000 (si present)
            page = mems.get(0x0000)
            if page is None or len(page) < 0xD6:
                print(f"  ${dest:04X} : PAS DE DUMP page 0 -> ECHEC")
                fails += 1
                continue
            got = page[dest:dest + len(data)]
        else:
            got = mems.get(dest)
            if got is None:
                print(f"  ${dest:04X} : PAS DE DUMP -> ECHEC")
                fails += 1
                continue
            got = got[:len(data)]
        if got != data:
            ndiff = sum(1 for a, b in zip(got, data) if a != b)
            print(f"  ${dest:04X} : {ndiff}/{len(data)} octets different -> ECHEC")
            for i, (a, b) in enumerate(zip(got, data)):
                if a != b and ndiff < 20:
                    print(f"    +${i:04X} : tape ${b:02X} vs mem ${a:02X}")
            fails += 1
        else:
            print(f"  ${dest:04X} : identique ({len(data)} o) OK")
    print("RESULTAT :", "OK" if fails == 0 else f"{fails} REGION(S) EN ECART")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extrait le flux cassette @@TAPE du harnais sim65 vers un fichier .tape.

Le stub $040E (harness/tape.s) emet "@@TAPE-BLOCK\\n" (leader $040B, un
par bloc SAVE) puis "@@TAPE-BYTE\\n" + 1 octet brut par octet ecrit.
Ce script reassemble les octets, decoupe en blocs ($24 + 10 o header +
$00 + donnees + checksum EOR), verifie et sauve.

Usage : sim65 ... > run.bin ; .venv/bin/python scripts/save_tape.py
            run.bin sav/game.tape
Sortie 0 si 4 blocs valides (dest/len/cksum OK), sinon 1 (fichier quand
meme ecrit pour diagnostic).
"""

from __future__ import annotations

import sys
from pathlib import Path

MARK_B = b"@@TAPE-BLOCK\n"
MARK_1 = b"@@TAPE-BYTE\n"


def parse_blocks(data: bytes) -> tuple[list[bytes], int]:
    """Decoupe le flux en blocs [sync $24 + 10 header + $00 + data + cksum].
    Rend (blocs, nb_octets_emis). Lève ValueError si incoherent."""
    out = bytearray()
    pos = 0
    while True:
        i = data.find(MARK_1, pos)
        if i < 0:
            break
        if i + len(MARK_1) >= len(data):
            break  # capture tronquee : ignore la queue
        out.append(data[i + len(MARK_1)])
        pos = i + len(MARK_1) + 1
    stream = bytes(out)
    blocks: list[bytes] = []
    p = 0
    while p < len(stream):
        if stream[p] != 0x24:
            raise ValueError(f"sync $24 attendu en offset {p}, vu ${stream[p]:02X}")
        if p + 12 > len(stream):
            raise ValueError("bloc tronque (header)")
        hdr = stream[p + 1:p + 11]
        if not (hdr[0] == 0xFF and hdr[1] == 0xFF and hdr[2] == 0x50
                and hdr[3] == 0x50 and hdr[8] == 0xFF):
            raise ValueError(f"header inattendu en bloc {len(blocks)} : {hdr.hex()}")
        end = (hdr[4] << 8) | hdr[5]
        dest = (hdr[6] << 8) | hdr[7]
        ln = (end - dest) & 0xFFFF
        if stream[p + 11] != 0x00:
            raise ValueError(f"separateur $00 attendu bloc {len(blocks)}")
        data = stream[p + 12:p + 12 + ln]
        if len(data) < ln:
            raise ValueError(f"donnees tronquees bloc {len(blocks)}")
        cksum = stream[p + 12 + ln]
        eor = 0
        for b in data:
            eor ^= b
        if cksum != eor:
            raise ValueError(f"checksum bloc {len(blocks)} : vu ${cksum:02X}, "
                             f"calcule ${eor:02X}")
        print(f"bloc {len(blocks)} : dest=${dest:04X} len=${ln:04X} ({ln}) cksum OK")
        blocks.append(stream[p:p + 13 + ln])
        p += 13 + ln
    return blocks, len(stream)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: save_tape.py run.bin sav/game.tape")
        return 1
    data = Path(sys.argv[1]).read_bytes()
    nblk = data.count(MARK_B)
    print(f"marqueurs : {nblk} BLOCK, {data.count(MARK_1)} BYTE")
    try:
        blocks, n = parse_blocks(data)
    except ValueError as e:
        print(f"ERREUR : {e}")
        return 1
    if len(blocks) != 4:
        print(f"ERREUR : {len(blocks)} blocs (attendu 4 : ZP/etats/scripts/records)")
        return 1
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"".join(blocks))
    print(f"tape : {out} ({sum(len(b) for b in blocks)} o, {n} octets emis)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

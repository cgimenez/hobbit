#!/usr/bin/env python3
"""Extrait le code binaire d'une archive Oric .tap en une image mémoire.

Format Oric TAP (voir docs/tape-format.md) :

    synchronisation : N x $16 (N >= 1) suivi de $24
    en-tête         : 9 octets
        [0:2]  réservés (inutilisés)
        [2]    type    : $00 = BASIC, $80 = code machine / bloc mémoire
        [3]    autorun : $00 = OFF, autre = ON
        [4:6]  adresse de fin    (big-endian)
        [6:8]  adresse de début  (big-endian)
        [8]    inutilisé
    nom             : ASCII terminé par $00, 15 caractères max
    données         : end - start + 1 octets

Les blocs sont placés à leur adresse de chargement dans une image mémoire
unique ; les zones non couvertes sont remplies d'octets $00.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

SYNC_BYTE = 0x16
SYNC_END = 0x24
HEADER_SIZE = 9
MAX_NAME = 15

TYPE_NAMES = {0x00: "BASIC", 0x80: "code machine / bloc mémoire"}


@dataclass
class Block:
    offset: int
    sync_len: int
    type: int
    autorun: int
    start: int
    end: int
    name: str
    payload: bytes

    @property
    def size(self) -> int:
        return len(self.payload)

    @property
    def autorun_on(self) -> bool:
        return self.autorun != 0x00


def parse_tap(data: bytes) -> list[Block]:
    blocks: list[Block] = []
    n = len(data)
    off = 0
    while off < n:
        start = off

        while off < n and data[off] == SYNC_BYTE:
            off += 1
        sync_len = off - start
        if sync_len == 0 or off >= n or data[off] != SYNC_END:
            raise ValueError(
                f"pas de synchronisation à l'offset {start} "
                f"({data[start:start + 16].hex(' ')})"
            )
        off += 1

        if off + HEADER_SIZE > n:
            raise ValueError("en-tête tronqué")
        header = data[off:off + HEADER_SIZE]
        off += HEADER_SIZE

        name_bytes = bytearray()
        while off < n and len(name_bytes) < MAX_NAME:
            c = data[off]
            off += 1
            if c == 0x00:
                break
            name_bytes.append(c)
        name = name_bytes.decode("ascii", errors="replace")

        block_type = header[2]
        autorun = header[3]
        end = header[4] * 256 + header[5]
        start_addr = header[6] * 256 + header[7]
        size = end - start_addr + 1
        if size <= 0:
            raise ValueError(f"taille invalide au bloc @{start}: {size}")

        payload = data[off:off + size]
        if len(payload) != size:
            raise ValueError(f"données tronquées au bloc @{start}")
        off += size

        blocks.append(
            Block(
                offset=start,
                sync_len=sync_len,
                type=block_type,
                autorun=autorun,
                start=start_addr,
                end=end,
                name=name,
                payload=payload,
            )
        )
    return blocks


def build_image(blocks: list[Block], fill: int = 0x00) -> tuple[int, bytes]:
    """Assemble les blocs dans une image mémoire unique.

    Retourne (adresse_de_base, image).
    """
    base = min(b.start for b in blocks)
    top = max(b.end for b in blocks)
    image = bytearray([fill] * (top - base + 1))
    for b in blocks:
        pos = b.start - base
        image[pos:pos + b.size] = b.payload
    return base, bytes(image)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tap",
        nargs="?",
        type=Path,
        default=root / "data" / "hobbit-1982.tap",
        help="archive .tap à extraire",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=root / "data" / "hobbit.bin",
        help="fichier binaire de sortie",
    )
    args = parser.parse_args()

    data = args.tap.read_bytes()
    blocks = parse_tap(data)

    print(f"Archive : {args.tap} ({len(data)} octets)")
    for i, b in enumerate(blocks, 1):
        print(
            f"  bloc {i}: @{b.offset:6d} sync={b.sync_len} "
            f"type=${b.type:02X} ({TYPE_NAMES.get(b.type, 'inconnu')}) "
            f"auto={'ON' if b.autorun_on else 'OFF'} "
            f"${b.start:04X}-${b.end:04X} ({b.size} octets) "
            f"nom={b.name!r}"
        )

    base, image = build_image(blocks)
    args.output.write_bytes(image)
    print(
        f"\nImage : ${base:04X}-${base + len(image) - 1:04X} "
        f"({len(image)} octets) -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

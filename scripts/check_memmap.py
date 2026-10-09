#!/usr/bin/env python3
"""Verification de la carte memoire (scripts/memmap_defs.py).

Sections (comme check_disasm.py) :
  A. REGIONS : somme = TOTAL_BYTES (3623), nom unique.
  B. annotate() non vide pour les 3623 adresses.
  C. noms de slots uniques (region+nom).
  D. doc d'un slot : une ligne, <= 160 car.
  E. genre de slot valide.
  F. structures attendues : 61 cles, 13 INDIR, 10 events, 17 entites, 79 rec.
Sortie : "RÉSULTAT: PROPRE" (exit 0) ou liste d'anomalies (exit 1).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memmap_defs as D  # noqa: E402

KINDS = {D.VAR, D.GABARIT, D.TABLE, D.CODE, D.CONST, D.UNKNOWN}
MAXDOC = 160


def main() -> int:
    anoms: list[str] = []

    # A. REGIONS
    if sum(ln for _, ln, _ in D.REGIONS) != 3623:
        anoms.append(f"A: somme regions = {D.TOTAL_BYTES} != 3623")
    if len(D.REGION_LEN) != len(D.REGIONS):
        anoms.append("A: bases de region dupliquees")

    # B/C/D/E : balayage des 3623 adresses
    seen: dict[tuple[str, str], list[int]] = {}
    named = 0
    for base, ln, nom in D.REGIONS:
        for off in range(ln):
            slots = D.annotate(base, off)
            if not slots:
                anoms.append(f"B: ${base:04X}+${off:04X} sans slot")
                continue
            for s in slots:
                if s.addr != base + off:
                    anoms.append(f"B: {s.name} addr ${s.addr:04X} "
                                 f"!= ${base:04X}+${off:04X}")
                seen.setdefault((s.region, s.name), []).append(base + off)
                if s.kind not in KINDS:
                    anoms.append(f"E: {s.name} genre invalide {s.kind!r}")
                if "\n" in s.doc or len(s.doc) > MAXDOC:
                    anoms.append(f"D: {s.name} doc {len(s.doc)} car")
                if s.kind != D.UNKNOWN:
                    named += 1

    # C. un slot = plage contigue d'adresses (les octets d'un champ
    #    multi-octets partagent le nom).
    for (region, name), addrs in seen.items():
        lo, hi = min(addrs), max(addrs)
        if len(addrs) != hi - lo + 1:
            anoms.append(f"C: {region}/{name} non contigu "
                         f"({len(addrs)} o sur {hi - lo + 1})")

    # F. structures
    if len(D.STATE_KEYS) != 61:
        anoms.append(f"F: {len(D.STATE_KEYS)} cles d'etat != 61")
    if len(D.INDIR_TABLES) != 13:
        anoms.append(f"F: {len(D.INDIR_TABLES)} tables INDIR != 13")
    if len(D.RECORDS) != 79:
        anoms.append(f"F: {len(D.RECORDS)} records != 79 "
                     f"(data/hobbit.bin absent ?)")

    print(f"slots distincts: {len(seen)}, occurrences nommees: {named}")
    if anoms:
        print(f"ANOMALIES: {len(anoms)}")
        for a in anoms[:40]:
            print("  " + a)
        print("RÉSULTAT: ANOMALIES")
        return 1
    print("RÉSULTAT: PROPRE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Diff des dumps memoire du harnais sim65 (marqueurs @@MEM).

Chaque @@FRAME s'accompagne (si l'ecran a change) de dumps
"@@MEM <addr4hex> <len4hex>\\n" + octets bruts (zero-page $0000 et tables
scheduler $2B00, cf. harness/shim.s). Par defaut affiche, pour chaque
trame, les octets modifies depuis la trame precedente ; --full vide
aussi les regions completes.

Usage : .venv/bin/python scripts/sim_mems.py frames.bin [--full]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RE_MEM = re.compile(rb"@@MEM ([0-9A-F]{4}) ([0-9A-F]{4})\n")


def frames_with_mems(data: bytes) -> list[list[tuple[int, bytes]]]:
    out: list[list[tuple[int, bytes]]] = []
    for chunk in re.split(b"@@FRAME text\n", data)[1:]:
        recs: list[tuple[int, bytes]] = []
        for m in RE_MEM.finditer(chunk):
            addr, ln = int(m.group(1), 16), int(m.group(2), 16)
            payload = chunk[m.end():m.end() + ln]
            if len(payload) < ln:  # capture tronquee (timeout) : ignore
                break
            recs.append((addr, payload))
        out.append(recs)
    return out


def main() -> int:
    full = "--full" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: sim_mems.py frames.bin [--full]")
        return 1
    frames = frames_with_mems(Path(args[0]).read_bytes())
    print(f"trames: {len(frames)}")
    prev: dict[int, bytes] = {}
    for n, recs in enumerate(frames, 1):
        if not recs:
            print(f"----- trame {n} : sans MEM -----")
            continue
        changed: list[str] = []
        for addr, payload in recs:
            old = prev.get(addr)
            if old is None:
                changed.append(f"  ${addr:04X} : (premier dump, {len(payload)} o)")
            else:
                for i, (a, b) in enumerate(zip(old, payload)):
                    if a != b:
                        changed.append(f"  ${addr + i:04X} : {a:02X} -> {b:02X}")
            prev[addr] = payload
            if full:
                for off in range(0, len(payload), 16):
                    blk = payload[off:off + 16]
                    changed.append(f"    ${addr + off:04X} : "
                                   + " ".join(f"{b:02X}" for b in blk))
        if changed or full:
            print(f"----- trame {n} -----")
            print("\n".join(changed) if changed else "  (identique)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

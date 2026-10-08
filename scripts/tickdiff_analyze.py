#!/usr/bin/env python3
"""Interprete un ticks.log de tickdiff : mappe chaque delta vers la
structure connue (docs/savegame-memory-map.md).

Usage : .venv/bin/python scripts/tickdiff_analyze.py build/sim/ticks_r4 [N]
  N = nb de ticks a detailler (defaut 5 premiers non-vides).
Sortie : resume global (net TICK0->FIN par region, series scheduler)
+ extrait interprete des N premiers ticks avec deltas.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Table des 61 cles (cle -> base bloc), cf. savegame-memory-map.md §2.
KEYS = [
    (0x00, 0x1B1A), (0x01, 0x1B63), (0x02, 0x1B96), (0x03, 0x1BBA),
    (0x04, 0x1BA8), (0x05, 0x1B42), (0x06, 0x1BCE), (0x07, 0x1BE9),
    (0x08, 0x1C05), (0x09, 0x1C25), (0x0A, 0x1C55), (0x0B, 0x1C74),
    (0x0C, 0x1C93), (0x0D, 0x1D1F), (0x0E, 0x1CB0), (0x0F, 0x1CDA),
    (0x10, 0x1CC4), (0x11, 0x1CEC), (0x12, 0x1D07), (0x13, 0x1D84),
    (0x14, 0x1DA8), (0x15, 0x1DE2), (0x16, 0x1DF6), (0x17, 0x1E0A),
    (0x18, 0x1E25), (0x19, 0x1E5F), (0x1A, 0x1E73), (0x1B, 0x1E87),
    (0x1C, 0x1EA4), (0x1D, 0x1EB7), (0x1E, 0x1ECB), (0x1F, 0x1EE3),
    (0x20, 0x1EF5), (0x21, 0x1F0B), (0x22, 0x1F23), (0x23, 0x1F37),
    (0x24, 0x1F49), (0x25, 0x1F5B), (0x26, 0x1FB1), (0x27, 0x1FC5),
    (0x28, 0x1FDA), (0x29, 0x1F75), (0x2A, 0x1C3D), (0x2B, 0x1B84),
    (0x3C, 0x1B30), (0x3D, 0x1FEC), (0x3E, 0x1D38), (0x3F, 0x1D4A),
    (0x40, 0x1D60), (0x41, 0x1D72), (0x42, 0x1DBE), (0x43, 0x1DD0),
    (0x44, 0x1E3B), (0x45, 0x2002), (0x46, 0x1E4D), (0x47, 0x1F8D),
    (0x48, 0x1F9F), (0x49, 0x2018), (0x4A, 0x202E), (0x4B, 0x2044),
    (0x4C, 0x205A),
]
KEYBASE = {k: b for k, b in KEYS}

ZP_NAMES = {
    0xBE: "exploc", 0xC5: "obj", 0xC6: "crec", 0xC7: "crec_hi",
    0xC8: "ploc", 0xC9: "eloc", 0xCE: "once",
}

FIELD = {0: "+0 type", 1: "+1 porteur", 8: "+8 tpl", 0x10: "+$10 eloc"}


def locate_states(off):
    """Rend les (cle, champ) possibles pour un offset global $1B1A+off."""
    addr = 0x1B1A + off
    out = []
    for k, b in KEYS:
        d = addr - b
        if 0 <= d <= 0x40:
            tag = FIELD.get(d, f"+${d:02X}")
            out.append(f"key${k:02X}{tag}")
    return out


def interp(base, off, a, b):
    addr = base + off
    if base == 0x00BE:
        nm = ZP_NAMES.get(addr, "?")
        return f"ZP ${addr:02X} {nm}: ${a:02X}->${b:02X}"
    if base == 0x1B1A:
        loc = locate_states(off)
        return f"ETAT +${off:04X} [${';'.join(loc)}]: ${a:02X}->${b:02X}"
    if base == 0x28CC:
        if 0x246 <= off <= 0x244 + 50:
            e = (off - 0x246) // 5
            f = ["id", "cpt", "actA", "cond", "actB"][(off - 0x246) % 5]
            return f"EVT e{e} {f}: ${a:02X}->${b:02X}"
        if 0x279 <= off <= 0x279 + 17 * 7:
            e = (off - 0x279) // 7
            f = ["id", "n", "PClo", "PChi", "balo", "bahi", "s6"][(off - 0x279) % 7]
            return f"ENT e{e} {f}: ${a:02X}->${b:02X}"
        return f"SCR +${off:04X}: ${a:02X}->${b:02X}"
    if base == 0x211A:
        return f"REC +${off:04X}: ${a:02X}->${b:02X}"
    return f"${base:04X}+${off:04X}: ${a:02X}->${b:02X}"


def load_ticks(d):
    ticks = []
    cur = None
    for l in (d / "ticks.log").read_text().splitlines():
        m = re.match(r'TICK (\d+) cmd="(.*)"', l)
        if m:
            cur = {"n": int(m.group(1)), "cmd": m.group(2), "diffs": []}
            ticks.append(cur)
            continue
        m = re.match(r"\s+\$(....) \+\$(....): \$(..)->\$(..)", l)
        if m and cur is not None:
            cur["diffs"].append(tuple(int(g, 16) for g in m.groups()))
    return ticks


def main():
    d = Path(sys.argv[1])
    n_show = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    ticks = load_ticks(d)
    print(f"{len(ticks)} ticks, {sum(len(t['diffs']) for t in ticks)} deltas")
    # Net par region : union des offsets touches + valeurs 1re/derniere
    first, last = {}, {}
    for t in ticks:
        for base, off, a, b in t["diffs"]:
            first.setdefault((base, off), a)
            last[(base, off)] = b
    byreg = {}
    for (base, off), b in last.items():
        byreg.setdefault(base, []).append((off, first[(base, off)], b))
    for base in sorted(byreg):
        chg = [x for x in byreg[base] if x[1] != x[2]]
        print(f"region ${base:04X} : {len(byreg[base])} offsets touches, "
              f"{len(chg)} nets differents au final")
    # Series scheduler : transitions (premier tick de chaque valeur)
    print("--- trajectoires scheduler (EVT/ENT) : nb valeurs distinctes ---")
    series = {}
    for t in ticks:
        for base, off, a, b in t["diffs"]:
            if base == 0x28CC and off >= 0x246:
                series.setdefault((base, off), []).append((t["n"], b))
    for k in sorted(series):
        vals = [v for _, v in series[k]]
        print(f"  ${k[0]:04X}+${k[1]:04X} : {len(set(vals))} valeurs, "
              f"1re=${vals[0]:02X} derniere=${vals[-1]:02X}")
    # Extrait interprete
    shown = 0
    for t in ticks:
        if not t["diffs"] or shown >= n_show:
            continue
        print(f"--- TICK {t['n']} cmd=\"{t['cmd']}\" ({len(t['diffs'])} deltas) ---")
        for base, off, a, b in t["diffs"]:
            print("   " + interp(base, off, a, b))
        shown += 1


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Registre de couverture de la memoire SAVE/LOAD (The Hobbit, Oric).

Fusionne les preuves dynamiques des deux bases :
  build/sim/hobbit.db  (tickdiff, table deltas)
  build/sim/solver.db  (BFS,     table edge_deltas)
et les rattache aux slots de scripts/memmap_defs.py.

Usage :
  memmap.py report               # couverture par region + % nommes
  memmap.py slots [--virgin]     # slots (--virgin : var jamais mutes)
  memmap.py unnamed              # offsets couverts sans slot nomme
  memmap.py addr <base_hex> <off_hex>   # annotation + preuves
  memmap.py sources              # apport par famille de source
  memmap.py xref [base [off]]    # refs litterales de block4.asm
  memmap.py gen [--write]        # annexe de couverture (doc)

Env : SOLVER_DB=... remplace build/sim/solver.db (runs de couverture).
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memmap_defs as D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOBBIT_DB = ROOT / "build" / "sim" / "hobbit.db"
SOLVER_DB = Path(os.environ.get("SOLVER_DB",
                                ROOT / "build" / "sim" / "solver.db"))
ASM = ROOT / "disasm" / "block4.asm"
DOC = ROOT / "docs" / "savegame-memory-map.md"
MARK_BEGIN = "<!-- BEGIN AUTO-COUVERTURE -->"
MARK_END = "<!-- END AUTO-COUVERTURE -->"


class Evidence:
    __slots__ = ("sources", "count", "vals", "cmds")

    def __init__(self) -> None:
        self.sources: set[str] = set()
        self.count = 0
        self.vals: set[int] = set()
        self.cmds: set[str] = set()


def load_deltas() -> dict[tuple[int, int], Evidence]:
    """{(base,off): Evidence} depuis les deux DB (silencieux si absentes)."""
    ev: dict[tuple[int, int], Evidence] = {}

    def add(base: int, off: int, av: int, ap: int, src: str,
            cmd: str | None) -> None:
        e = ev.setdefault((base, off), Evidence())
        e.sources.add(src)
        e.count += 1
        e.vals.add(av)
        e.vals.add(ap)
        if cmd:
            e.cmds.add(cmd)

    if HOBBIT_DB.is_file():
        cx = sqlite3.connect(f"file:{HOBBIT_DB}?mode=ro", uri=True)
        for base, off, av, ap, name, cmd in cx.execute(
                "SELECT d.base, d.off, d.avant, d.apres, r.name, t.cmd "
                "FROM deltas d JOIN runs r ON r.run_id=d.run_id "
                "LEFT JOIN ticks t ON t.run_id=d.run_id AND t.n=d.n"):
            add(base, off, av, ap, f"tick:{name}", cmd)
        cx.close()
    if SOLVER_DB.is_file():
        cx = sqlite3.connect(f"file:{SOLVER_DB}?mode=ro", uri=True)
        for base, off, av, ap, cmd in cx.execute(
                "SELECT d.base, d.off, d.avant, d.apres, n.cmd "
                "FROM edge_deltas d JOIN nodes n ON n.id=d.child"):
            add(base, off, av, ap, "bfs", cmd)
        cx.close()
    return ev


def address_slots() -> dict[tuple[int, int], list[D.Slot]]:
    """{(base,off): [Slots candidats]} pour les 3623 octets."""
    out = {}
    for base, ln, _nom in D.REGIONS:
        for off in range(ln):
            out[(base, off)] = D.annotate(base, off)
    return out


def _is_named(slot: D.Slot) -> bool:
    return slot.kind != D.UNKNOWN and not slot.name.startswith(("zp$", "rec?",
                                                               "code$"))


def cmd_report(ev: dict) -> int:
    addrs = address_slots()
    print(f"couverture : {len(ev)}/{D.TOTAL_BYTES} octets "
          f"({100 * len(ev) / D.TOTAL_BYTES:.1f}%)")
    print(f"{'region':8} {'octets':>7} {'couv':>6} {'%':>5}  "
          f"{'var couv/tot':>13}  {'slots nommes':>12}")
    for base, ln, nom in D.REGIONS:
        cov = sum(1 for off in range(ln) if (base, off) in ev)
        var_names, var_cov = set(), set()
        named, named_cov = set(), set()
        for off in range(ln):
            for s in addrs[(base, off)]:
                key = s.name
                if _is_named(s):
                    named.add(key)
                    if (base, off) in ev:
                        named_cov.add(key)
                if s.kind == D.VAR:
                    var_names.add(key)
                    if (base, off) in ev:
                        var_cov.add(key)
        print(f"${base:04X} {nom:8} {ln:7d} {cov:6d} "
              f"{100 * cov / ln:5.1f}  "
              f"{len(var_cov):5d}/{len(var_names):<5d}       "
              f"{len(named_cov):4d}/{len(named):<4d}")
    return 0


def cmd_slots(ev: dict, virgin: bool) -> int:
    addrs = address_slots()
    rows = []
    for (base, off), slots in addrs.items():
        for s in slots:
            if s.kind != D.VAR:
                continue
            cov = (base, off) in ev
            if virgin and cov:
                continue
            rows.append((base, off, s, cov))
    rows.sort(key=lambda r: (r[0], r[1], r[2].name))
    if not rows:
        print("(aucun slot variable)")
        return 0
    nvirg = sum(1 for *_, cov in rows if not cov)
    print(f"{len(rows)} slots variables ({nvirg} vierges) :")
    for base, off, s, cov in rows:
        tag = "ok " if cov else "VIERGE"
        print(f"  {tag} ${base:04X}+${off:04X} {s.name:26s} {s.doc}")
    return 0


def cmd_unnamed(ev: dict) -> int:
    """Offsets couverts mais sans aucun slot nomme (cibles du nommage)."""
    addrs = address_slots()
    total = 0
    for base, ln, nom in D.REGIONS:
        rows = []
        for off in range(ln):
            slots = addrs[(base, off)]
            if (base, off) in ev and not any(_is_named(s) for s in slots):
                rows.append((off, slots, ev[(base, off)]))
        total += len(rows)
        print(f"== ${base:04X} {nom}: {len(rows)} offsets couverts non nommes ==")
        for off, slots, e in rows:
            vals = " ".join(f"${v:02X}" for v in sorted(e.vals)[:8])
            cmds = sorted(c for c in e.cmds if c)[:5]
            names = ",".join(s.name for s in slots)
            print(f"  +${off:04X} [{names}] vals[{vals}] cmds{cmds}")
    print(f"total: {total} offsets a nommer")
    return 0


def cmd_addr(ev: dict, base: int, off: int) -> int:
    slots = D.annotate(base, off)
    print(f"${base:04X}+${off:04X} ({D.region_of(base)}) :")
    for s in slots:
        print(f"  {s.name:26s} [{s.kind}] {s.doc}")
    e = ev.get((base, off))
    if e is None:
        print("  preuve : jamais mute")
    else:
        vals = " ".join(f"${v:02X}" for v in sorted(e.vals)[:16])
        print(f"  preuve : {e.count} changements, sources={sorted(e.sources)}"
              f"\n           valeurs: {vals}")
        cmds = sorted(c for c in e.cmds if c)[:12]
        if cmds:
            print(f"           commandes: {cmds}")
    return 0


def cmd_xref(base: int | None, off: int | None) -> int:
    """Refs litterales (operandes $XXXX) de block4.asm vers les regions."""
    if not ASM.is_file():
        print(f"(listing absent : {ASM})")
        return 1
    hex4 = re.compile(r"\$([0-9A-Fa-f]{4})")
    hits: dict[int, list[tuple[int, str]]] = {}
    for i, line in enumerate(ASM.read_text(errors="replace").splitlines(), 1):
        if line.lstrip().startswith(";"):
            continue
        for m in hex4.finditer(line):
            a = int(m.group(1), 16)
            if any(b <= a < b + ln for b, ln, _ in D.REGIONS):
                hits.setdefault(a, []).append((i, line.strip()))
    if base is not None:
        want = base + (off or 0)
        sites = hits.get(want, [])
        print(f"${want:04X}: {len(sites)} refs litterales")
        for ln, txt in sites:
            print(f"  {ln}: {txt}")
        return 0
    total = sum(len(v) for v in hits.values())
    print(f"{len(hits)} adresses de region referencees ({total} refs) :")
    for a in sorted(hits):
        print(f"  ${a:04X}: {len(hits[a])} refs")
    return 0


def cmd_gen(write: bool) -> int:
    """Annexe de couverture (stdout, ou injectee dans le doc entre marqueurs)."""
    ev = load_deltas()
    addrs = address_slots()
    lines = [f"couverture (fusion tickdiff+solver) : {len(ev)}/{D.TOTAL_BYTES}"
             f" octets ({100 * len(ev) / D.TOTAL_BYTES:.1f} %).",
             "",
             "| Region | Octets | Couverts | % | Var couverts |",
             "|---|---|---|---|---|"]
    for base, ln, nom in D.REGIONS:
        cov = sum(1 for off in range(ln) if (base, off) in ev)
        var, vcov = set(), set()
        for off in range(ln):
            for s in addrs[(base, off)]:
                if s.kind == D.VAR:
                    var.add(s.name)
                    if (base, off) in ev:
                        vcov.add(s.name)
        lines.append(f"| `${base:04X}` {nom} | {ln} | {cov} | "
                     f"{100 * cov / ln:.1f} | {len(vcov)}/{len(var)} |")
    lines += ["",
              "Detail des variables : `scripts/memmap.py slots [--virgin]` ;",
              "xref statique : `scripts/memmap.py xref`."]
    block = MARK_BEGIN + "\n" + "\n".join(lines) + "\n" + MARK_END
    if not write:
        print(block)
        return 0
    text = DOC.read_text()
    if MARK_BEGIN in text and MARK_END in text:
        text = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END),
                      lambda _m: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    DOC.write_text(text)
    print(f"annexe ecrite dans {DOC.relative_to(ROOT)}")
    return 0


def cmd_sources(ev: dict) -> int:
    """Apport par famille de source (tickdiff run / bfs noeud)."""
    fam_tick, fam_bfs, runs = set(), set(), set()
    for e in ev.values():
        for s in e.sources:
            if s.startswith("tick:"):
                fam_tick.add(s)
            elif s == "bfs":
                fam_bfs.add(s)
    for name, _n in sqlite3.connect(
            f"file:{HOBBIT_DB}?mode=ro", uri=True).execute("SELECT name,0 FROM runs"):
        runs.add(name)
    tick_oct = sum(1 for e in ev.values()
                   if any(s.startswith("tick:") for s in e.sources))
    bfs_oct = sum(1 for e in ev.values() if "bfs" in e.sources)
    print(f"tickdiff : {len(runs)} runs, {tick_oct} octets distincts")
    print(f"bfs      : {bfs_oct} octets distincts")
    print(f"union    : {len(ev)} octets distincts")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    ev = load_deltas()
    c = argv[0]
    if c == "report":
        return cmd_report(ev)
    if c == "slots":
        return cmd_slots(ev, "--virgin" in argv)
    if c == "unnamed":
        return cmd_unnamed(ev)
    if c == "sources":
        return cmd_sources(ev)
    if c == "addr" and len(argv) >= 3:
        return cmd_addr(ev, int(argv[1], 16), int(argv[2], 16))
    if c == "xref":
        if len(argv) >= 3:
            return cmd_xref(int(argv[1], 16), int(argv[2], 16))
        if len(argv) >= 2:
            return cmd_xref(int(argv[1], 16), None)
        return cmd_xref(None, None)
    if c == "gen":
        return cmd_gen("--write" in argv)
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

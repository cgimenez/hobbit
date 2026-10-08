#!/usr/bin/env python3
"""DB SQLite unique des turns sim65 (The Hobbit, Oric).

tickdiff (C) ecrit directement dans build/sim/hobbit.db (--db/--name) ;
ce module offre des requetes pretes pour l'analyse.

Usage :
  tickdb.py traj <base_hex> <off_hex> [--run R6]
  tickdb.py touches <base_hex> <off_hex>
  tickdb.py diverge <runA> <runB>
  tickdb.py morts [--run R6]
  tickdb.py runs | tickdb.py query "<sql>"

Schema : runs(run) / ticks(run,n,cmd,frames) /
deltas(run,n,base,off,avant,apres) / texts(run,n,reponse).
Etat ZP : table state(run,n,ploc,eloc,obj,crec).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "build" / "sim" / "hobbit.db"

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS runs(
  run_id INTEGER PRIMARY KEY, name TEXT UNIQUE,
  image TEXT, cmdfile TEXT, started TEXT);
CREATE TABLE IF NOT EXISTS ticks(
  run_id INTEGER REFERENCES runs, n INTEGER, cmd TEXT, frames INTEGER,
  PRIMARY KEY(run_id, n));
CREATE TABLE IF NOT EXISTS deltas(
  run_id INTEGER, n INTEGER, base INTEGER, off INTEGER,
  avant INTEGER, apres INTEGER,
  PRIMARY KEY(run_id, n, base, off)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_deltas_addr
  ON deltas(base, off, run_id, n);
CREATE TABLE IF NOT EXISTS texts(
  run_id INTEGER, n INTEGER, reponse TEXT,
  PRIMARY KEY(run_id, n));
CREATE TABLE IF NOT EXISTS state(
  run_id INTEGER, n INTEGER, ploc INTEGER, eloc INTEGER,
  obj INTEGER, crec INTEGER,
  PRIMARY KEY(run_id, n));
"""


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(DB)
    cx.executescript(SCHEMA)
    return cx


def cmd_traj(base: str, off: str, run: str | None) -> int:
    cx = connect()
    q = ("SELECT r.name, d.n, t.cmd, d.avant, d.apres FROM deltas d "
         "JOIN runs r ON r.run_id=d.run_id "
         "LEFT JOIN ticks t ON t.run_id=d.run_id AND t.n=d.n "
         "WHERE d.base=? AND d.off=?")
    args: list = [int(base, 16), int(off, 16)]
    if run:
        q += " AND r.name=?"
        args.append(run)
    q += " ORDER BY r.name, d.n"
    for name, n, cmd, av, ap in cx.execute(q, args):
        print(f"{name} tick{n} {cmd!r}: ${av:02X}->${ap:02X}")
    return 0


def cmd_touches(base: str, off: str) -> int:
    cx = connect()
    for name, cmds, cnt in cx.execute(
            "SELECT r.name, GROUP_CONCAT(DISTINCT t.cmd), COUNT(*) "
            "FROM deltas d JOIN runs r ON r.run_id=d.run_id "
            "LEFT JOIN ticks t ON t.run_id=d.run_id AND t.n=d.n "
            "WHERE d.base=? AND d.off=? GROUP BY r.name",
            (int(base, 16), int(off, 16))):
        print(f"{name}: {cnt} changements via [{cmds}]")
    return 0


def cmd_lieu(run: str | None) -> int:
    """Lieu du joueur (ploc) + eloc/obj/crec a chaque tick (table state)."""
    cx = connect()
    q = ("SELECT r.name, s.n, t.cmd, s.ploc, s.eloc, s.obj, s.crec "
         "FROM state s JOIN runs r ON r.run_id=s.run_id "
         "LEFT JOIN ticks t ON t.run_id=s.run_id AND t.n=s.n")
    args: list = []
    if run:
        q += " WHERE r.name=?"
        args.append(run)
    q += " ORDER BY r.name, s.n"
    last: dict[str, int | None] = {}
    for name, n, cmd, ploc, eloc, obj, crec in cx.execute(q, args):
        mark = "" if last.get(name, None) == ploc else "  <--"
        last[name] = ploc
        print(f"{name} tick{n} {cmd!r}: ploc=${ploc:02X} "
              f"eloc=${eloc:02X} obj=${obj:02X} crec=${crec:04X}{mark}")
    return 0


def cmd_diverge(a: str, b: str) -> int:
    cx = connect()
    ida = cx.execute("SELECT run_id FROM runs WHERE name=?",
                     (a,)).fetchone()
    idb = cx.execute("SELECT run_id FROM runs WHERE name=?",
                     (b,)).fetchone()
    if not ida or not idb:
        print("run inconnu")
        return 1
    qa = {r[0:3]: r[3:5] for r in cx.execute(
        "SELECT n, base, off, avant, apres FROM deltas WHERE run_id=?",
        (ida[0],))}
    qb = {r[0:3]: r[3:5] for r in cx.execute(
        "SELECT n, base, off, avant, apres FROM deltas WHERE run_id=?",
        (idb[0],))}
    na = cx.execute("SELECT MAX(n) FROM ticks WHERE run_id=?",
                    (ida[0],)).fetchone()[0]
    nb = cx.execute("SELECT MAX(n) FROM ticks WHERE run_id=?",
                    (idb[0],)).fetchone()[0]
    print(f"{a}: {na} ticks, {b}: {nb} ticks")
    shown = 0
    for key in sorted(set(qa) | set(qb)):
        if qa.get(key) != qb.get(key) and shown < 20:
            n, base, off = key
            print(f"  tick{n} ${base:04X}+${off:04X}: "
                  f"{a}={qa.get(key)} {b}={qb.get(key)}")
            shown += 1
    return 0


def cmd_morts(run: str | None) -> int:
    cx = connect()
    q = ("SELECT r.name, d.n, t.cmd, d.off, d.avant, d.apres FROM deltas d "
         "JOIN runs r ON r.run_id=d.run_id "
         "LEFT JOIN ticks t ON t.run_id=d.run_id AND t.n=d.n "
         "WHERE d.base=10444 AND ((d.off-633) % 7)=0 "
         "AND d.apres=0 AND d.avant!=0")
    args: list = []
    if run:
        q += " AND r.name=?"
        args.append(run)
    for row in cx.execute(q + " ORDER BY r.name, d.n", args):
        print(f"{row[0]} tick{row[1]} {row[2]!r}: "
              f"entite +${row[3]:04X} ${row[4]:02X}->$00")
    return 0


def cmd_coverage() -> int:
    """% des 3623 o jamais mutes (tous runs), par region + apport par run."""
    cx = connect()
    regions = [(0x00BE, 0x18, "ZP"), (0x1B1A, 0x556, "etats"),
               (0x28CC, 0x2F1, "scripts"), (0x211A, 0x5C8, "records")]
    touched: set[tuple[int, int]] = set()
    for base, ln, _ in regions:
        for (off,) in cx.execute(
                "SELECT DISTINCT off FROM deltas WHERE base=?", (base,)):
            touched.add((base, off))
    total = sum(ln for _, ln, _ in regions)
    print(f"couverture globale: {len(touched)}/{total} "
          f"({100 * len(touched) / total:.1f}%)")
    for base, ln, nom in regions:
        n = sum(1 for (b, _) in touched if b == base)
        print(f"  ${base:04X} {nom}: {n}/{ln} ({100 * n / ln:.1f}%)")
    print("apport marginal par run (offsets vus nulle part ailleurs):")
    rows = cx.execute(
        "SELECT r.name, d.base, d.off FROM deltas d "
        "JOIN runs r ON r.run_id=d.run_id").fetchall()
    from collections import Counter
    owners: dict[tuple[int, int], str] = {}
    counts: Counter[tuple[int, int]] = Counter()
    for name, b, o in rows:
        owners.setdefault((b, o), name)
        counts[(b, o)] += 1
    per: Counter[str] = Counter()
    for key, n in counts.items():
        if n == 1:
            per[owners[key]] += 1
    for name, n in per.most_common():
        print(f"  {name}: {n} offsets uniques")
    return 0


def cmd_vierges() -> int:
    """Octets JAMAIS mutes (tous runs) : les vraies cibles du fuzz."""
    cx = connect()
    regions = [(0x00BE, 0x18, "ZP"), (0x1B1A, 0x556, "etats"),
               (0x28CC, 0x2F1, "scripts"), (0x211A, 0x5C8, "records")]
    touched: set[tuple[int, int]] = set()
    for base, _, _ in regions:
        for (off,) in cx.execute(
                "SELECT DISTINCT off FROM deltas WHERE base=?", (base,)):
            touched.add((base, off))
    for base, ln, nom in regions:
        vierges = [o for o in range(ln) if (base, o) not in touched]
        show = " ".join(f"+${o:04X}" for o in vierges[:24])
        more = f" (+{len(vierges) - 24})" if len(vierges) > 24 else ""
        print(f"${base:04X} {nom}: {len(vierges)} vierges : {show}{more}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    c = argv[1]
    if c == "traj" and len(argv) >= 4:
        run = argv[4] if len(argv) > 4 and argv[4] != "--run" else None
        if "--run" in argv:
            run = argv[argv.index("--run") + 1]
        return cmd_traj(argv[2], argv[3], run)
    if c == "touches" and len(argv) >= 4:
        return cmd_touches(argv[2], argv[3])
    if c == "diverge" and len(argv) >= 4:
        return cmd_diverge(argv[2], argv[3])
    if c == "morts":
        run = argv[argv.index("--run") + 1] if "--run" in argv else None
        return cmd_morts(run)
    if c == "lieu":
        run = argv[argv.index("--run") + 1] if "--run" in argv else None
        return cmd_lieu(run)
    if c == "coverage":
        return cmd_coverage()
    if c == "vierges":
        return cmd_vierges()
    if c == "runs":
        for r in connect().execute(
                "SELECT name, (SELECT COUNT(*) FROM ticks t "
                "WHERE t.run_id=r.run_id), (SELECT COUNT(*) FROM deltas d "
                "WHERE d.run_id=r.run_id) FROM runs r ORDER BY name"):
            print(f"{r[0]}: {r[1]} ticks, {r[2]} deltas")
        return 0
    if c == "query":
        cx = connect()
        cur = cx.execute(" ".join(argv[2:]))
        if cur.description:
            for row in cur:
                print(row)
        else:
            cx.commit()
            print(f"({cur.rowcount} lignes)")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

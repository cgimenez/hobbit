#!/usr/bin/env python3
"""Graphe d'exploration The Hobbit : stockage SQLite (phase 1).

Un noeud = un etat jeu complet apres une commande :
  blob 3627 o ("SNAP" + 4 regions SAVE, meme format que sav/*.bin),
  hash sha1 (dedup), etat lisible ploc/eloc/obj/crec, texte ASCII,
  ndiff + edge_deltas vs parent, statut ok/parked/dead/win.

DB : build/sim/solver.db (gitignore, comme hobbit.db).
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "build" / "sim" / "solver.db"

# Regions SAVE, meme ordre que harness/snap.s REGTAB / tickdiff.c.
REGIONS = [(0x00BE, 0x18), (0x1B1A, 0x556), (0x28CC, 0x2F1), (0x211A, 0x5C8)]
SNAP_MAGIC = b"SNAP"
BLOB_LEN = 4 + sum(ln for _, ln in REGIONS)

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS nodes(
  id INTEGER PRIMARY KEY, parent INTEGER REFERENCES nodes,
  cmd TEXT NOT NULL, depth INTEGER NOT NULL,
  blob BLOB NOT NULL, h TEXT NOT NULL,
  ploc INTEGER, eloc INTEGER, obj INTEGER, crec INTEGER,
  text TEXT NOT NULL, ndiff INTEGER NOT NULL,
  status TEXT NOT NULL, fail TEXT, score REAL,
  echo_ok INTEGER NOT NULL DEFAULT 1,
  created TEXT DEFAULT (datetime('now')));
CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_h ON nodes(h);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent);
CREATE TABLE IF NOT EXISTS edge_deltas(
  child INTEGER REFERENCES nodes, base INTEGER, off INTEGER,
  avant INTEGER, apres INTEGER,
  PRIMARY KEY(child, base, off)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS attempts(
  id INTEGER PRIMARY KEY, parent INTEGER REFERENCES nodes,
  cmd TEXT NOT NULL, status TEXT NOT NULL, fail TEXT,
  created TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_attempts_parent ON attempts(parent);
CREATE TABLE IF NOT EXISTS banned_words(
  word TEXT PRIMARY KEY, seen TEXT DEFAULT (datetime('now')));
"""


def get_banned(cx: sqlite3.Connection) -> set[str]:
    return {r[0] for r in cx.execute("SELECT word FROM banned_words")}


def add_banned(cx: sqlite3.Connection, words) -> int:
    n = 0
    for w in words:
        try:
            cx.execute("INSERT INTO banned_words(word) VALUES(?)", (w,))
            n += 1
        except sqlite3.IntegrityError:
            pass
    return n


def verb_fail_counts(cx: sqlite3.Connection, ploc: int) -> dict[str, int]:
    """Nb de parked par (ploc du parent, 1er mot de cmd) : depriorisation."""
    rows = cx.execute(
        "SELECT substr(a.cmd, 1, instr(a.cmd || ' ', ' ') - 1), COUNT(*) "
        "FROM attempts a JOIN nodes n ON n.id=a.parent "
        "WHERE n.ploc=? AND a.status='parked' GROUP BY 1", (ploc,)).fetchall()
    return {v: c for v, c in rows}


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(DB)
    cx.executescript(SCHEMA)
    return cx


def blob_hash(blob: bytes) -> str:
    return hashlib.sha1(blob).hexdigest()


def make_blob(payloads: dict[int, bytes]) -> bytes:
    """Reassemble "SNAP"+3623 depuis {idx: payload} (idx 0..3 requis)."""
    out = bytearray(SNAP_MAGIC)
    for i, (_, ln) in enumerate(REGIONS):
        p = payloads.get(i)
        if p is None or len(p) != ln:
            raise ValueError(f"bloc {i} manquant/incomplet")
        out += p
    return bytes(out)


def split_blob(blob: bytes) -> dict[int, bytes]:
    if blob[:4] != SNAP_MAGIC or len(blob) != BLOB_LEN:
        raise ValueError(f"blob invalide ({len(blob)} o)")
    out, off = {}, 4
    for i, (_, ln) in enumerate(REGIONS):
        out[i] = blob[off:off + ln]
        off += ln
    return out


def state_of(blob: bytes) -> tuple[int, int, int, int]:
    """(ploc, eloc, obj, crec) lus du bloc ZP ($C8/$C9/$C5/$C6)."""
    zp = split_blob(blob)[0]
    ploc, eloc, obj = zp[0x0A], zp[0x0B], zp[0x07]
    crec = zp[0x08] | (zp[0x09] << 8)
    return ploc, eloc, obj, crec


def diff_blobs(a: bytes, b: bytes) -> list[tuple[int, int, int, int]]:
    """[(base, off, avant, apres)] pour chaque octet change (hors magique)."""
    pa, pb = split_blob(a), split_blob(b)
    out = []
    for i, (base, ln) in enumerate(REGIONS):
        xa, xb = pa[i], pb[i]
        for o in range(ln):
            if xa[o] != xb[o]:
                out.append((base, o, xa[o], xb[o]))
    return out


def add_node(cx: sqlite3.Connection, parent: int | None, cmd: str, depth: int,
             blob: bytes, text: str, deltas: list[tuple[int, int, int, int]],
             status: str, fail: str | None = None, score: float | None = None,
             echo_ok: bool = True) -> int:
    ploc, eloc, obj, crec = state_of(blob)
    cur = cx.execute(
        "INSERT INTO nodes(parent,cmd,depth,blob,h,ploc,eloc,obj,crec,"
        " text,ndiff,status,fail,score,echo_ok)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (parent, cmd, depth, blob, blob_hash(blob), ploc, eloc, obj, crec,
         text, len(deltas), status, fail, score, int(echo_ok)))
    nid = cur.lastrowid
    cx.executemany("INSERT INTO edge_deltas VALUES(?,?,?,?,?)",
                   [(nid, b, o, av, ap) for b, o, av, ap in deltas])
    return nid


def find_by_hash(cx: sqlite3.Connection, h: str) -> int | None:
    row = cx.execute("SELECT id FROM nodes WHERE h=?", (h,)).fetchone()
    return row[0] if row else None


def get_node(cx: sqlite3.Connection, nid: int) -> tuple | None:
    return cx.execute(
        "SELECT id,parent,cmd,depth,ploc,eloc,obj,crec,ndiff,status,"
        " fail,score,echo_ok FROM nodes WHERE id=?", (nid,)).fetchone()


def get_blob(cx: sqlite3.Connection, nid: int) -> bytes:
    row = cx.execute("SELECT blob FROM nodes WHERE id=?", (nid,)).fetchone()
    return bytes(row[0])


def get_text(cx: sqlite3.Connection, nid: int) -> str:
    return cx.execute("SELECT text FROM nodes WHERE id=?", (nid,)).fetchone()[0]


def frontier(cx: sqlite3.Connection, limit: int = 1000) -> list[tuple[int, str, int]]:
    """Noeuds ok non etendus (sans enfants), par profondeur croissante."""
    return cx.execute(
        "SELECT n.id, n.cmd, n.depth FROM nodes n"
        " LEFT JOIN nodes c ON c.parent=n.id"
        " WHERE n.status='ok' AND c.id IS NULL"
        " ORDER BY n.depth, n.id LIMIT ?", (limit,)).fetchall()


def record_attempt(cx: sqlite3.Connection, parent: int, cmd: str,
                   status: str, fail: str | None = None) -> int:
    cur = cx.execute("INSERT INTO attempts(parent,cmd,status,fail)"
                     " VALUES(?,?,?,?)", (parent, cmd, status, fail))
    return cur.lastrowid


def stats(cx: sqlite3.Connection) -> dict:
    rows = cx.execute(
        "SELECT status, COUNT(*) FROM nodes GROUP BY status").fetchall()
    out = {s: n for s, n in rows}
    out["attempts"] = cx.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    return out


def tried(cx: sqlite3.Connection) -> set[tuple[int, str]]:
    """(parent, cmd) deja joues : enfants existants + attempts."""
    s = {(r[0], r[1]) for r in
         cx.execute("SELECT parent, cmd FROM nodes WHERE parent IS NOT NULL")}
    s |= {(r[0], r[1]) for r in cx.execute("SELECT parent, cmd FROM attempts")}
    return s


def ok_at_depth(cx: sqlite3.Connection, depth: int) -> list[tuple[int, int]]:
    """Noeuds ok a une profondeur donnee : [(id, ploc)]."""
    return cx.execute("SELECT id, ploc FROM nodes WHERE status='ok'"
                      " AND depth=? ORDER BY id", (depth,)).fetchall()


def max_depth(cx: sqlite3.Connection) -> int:
    row = cx.execute("SELECT MAX(depth) FROM nodes").fetchone()
    return row[0] if row[0] is not None else 0


def path_of(cx: sqlite3.Connection, nid: int) -> list[str]:
    """Commandes racine -> nid."""
    cmds = []
    while True:
        row = cx.execute("SELECT parent, cmd FROM nodes WHERE id=?",
                         (nid,)).fetchone()
        if row is None or row[0] is None:
            break
        cmds.append(row[1])
        nid = row[0]
    return cmds[::-1]


def best_score(cx: sqlite3.Connection) -> tuple[float | None, int | None]:
    row = cx.execute("SELECT MAX(score) FROM nodes WHERE score IS NOT NULL"
                     ).fetchone()
    if not row or row[0] is None:
        return None, None
    nid = cx.execute("SELECT id FROM nodes WHERE score=? ORDER BY depth"
                     " LIMIT 1", (row[0],)).fetchone()[0]
    return row[0], nid

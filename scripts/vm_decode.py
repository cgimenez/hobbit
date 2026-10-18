#!/usr/bin/env python3
"""Desassemble les scripts VM des PNJ (AnimAction, bloc 2 : $28E1-$2B11).

Regles d'instruction (lues dans disasm/block4.asm : script_move $5055,
script_move_short $50B2, dispatch $4F9E-$4FF4, script_rand $51CA,
script_indir $51DA, entity_goto $5858, index_id_table $53C0) :
  nibble 0/2 : MOVE long  [op,wid,arg1,arg2]            (+2 o si bit $10)
  nibble 1/3 : ACT      [op,idx,tiers] (idx -> table $7143) (+2 o si $10)
  nibble 4   : MOVE court [op,wid]                      (+2 o si $10) ;
               wid=$FF + bit $10 : saut absolu [op,FF,lo,hi] (4 o, sans suite)
  nibbles 5-9,A,B,D : INDIR [op,_] -> table[0] (2 o, sans suite)
  nibble C   : GOTO cle [op,cle] -> 1er [cle,lo,hi] de la table (2 o, sans suite)
  nibble E   : GOTO absolu [op,lo,hi] (3 o, sans suite)
  nibble F   : RAND [op,borne] -> table[0..min(borne,nmax)] (2 o, sans suite)
Les 2 octets supplementaires (+$10) sont le vecteur de secours : en cas
d'echec, PC := *(inst+X) (L50FB, X = taille de base) ; en cas de succes,
reprise a inst+taille. Bit $20 = auto-modification (dormant au tour suivant),
sans effet sur le flot.

Usage : scripts/vm_decode.py [--db|--no-db]
  --db (defaut) : recoupe avec les PC observes (build/sim/hobbit.db +
                  build/sim/solver.db, lus en mode ro).
Sortie 0 si structure saine (anomalies listees mais non bloquantes : code
inatteint, idx ACT > 32, bit $10 sur nibble >= 5).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = ROOT / "data" / "hobbit.bin"
IMAGE_BASE = 0x0400
ENT_BASE, ENT_N, ENT_SIZE = 0x2B45, 17, 7
EVT_BASE = 0x2B12
CODE_LO, CODE_HI = 0x28E1, 0x2B11
ACT_TABLE, ACT_MAX = 0x7143, 32  # idx 1..32 -> bloc 4 (releve image)

sys.path.insert(0, str(ROOT / "scripts"))
import memmap_defs as D  # noqa: E402


def img(addr: int) -> int:
    return D._img(addr)


def w16(addr: int) -> int:
    return img(addr) | (img(addr + 1) << 8)


def parse_tables() -> dict[int, list[tuple[int, int]]]:
    """{base: [(cle, cible)]} depuis INDIR_TABLES (entrees [cle,lo,hi], $FF)."""
    out = {}
    for base, _size in D.INDIR_TABLES:
        ent, a = [], base
        while True:
            c = img(a)
            if c == 0xFF:
                break
            ent.append((c, w16(a + 1)))
            a += 3
        out[base] = ent
    return out


def entities() -> list[dict]:
    out = []
    for e in range(ENT_N):
        a = ENT_BASE + e * ENT_SIZE
        out.append({
            "e": e, "id": img(a), "nmax": img(a + 1),
            "pc": w16(a + 2), "base": w16(a + 4), "reply": img(a + 6),
        })
    return out


# --- desassemblage -------------------------------------------------------
class Ins:
    def __init__(self, addr: int, raw: bytes, mn: str, ops: str,
                 edges: list[int], note: str = ""):
        self.addr, self.raw, self.mn = addr, raw, mn
        self.ops, self.edges, self.note = ops, edges, note

    def size(self) -> int:
        return len(self.raw)


def decode_at(addr: int, base: int, nmax: int,
              tables: dict[int, list[tuple[int, int]]]) -> Ins | None:
    """Desassemble une instruction en addr (None horsievee)."""
    op = img(addr)
    nib = op & 0x0F
    sec = bool(op & 0x10) and nib <= 4
    ctl = "".join(b for m, b in ((0x40, "err"), (0x20, "auto"),
                                 (0x10, "sec")) if op & m)
    suf = f" [{ctl}]" if ctl else ""

    def tail(a: int, n: int) -> bytes:
        return bytes(img(a + i) for i in range(n))

    if nib in (0, 2):  # MOVE long
        n = 6 if sec else 4
        r = tail(addr, n)
        edges = [addr + n]
        if sec:
            edges.append(r[4] | (r[5] << 8))
        return Ins(addr, r, "MOVE",
                   f"wid=${r[1]:02X} arg1=${r[2]:02X} arg2=${r[3]:02X}" + suf,
                   edges)
    if nib in (1, 3):  # ACT
        n = 5 if sec else 3
        r = tail(addr, n)
        note = "" if r[1] <= ACT_MAX else "IDX>32 ?"
        edges = [addr + n]
        if sec:
            edges.append(r[3] | (r[4] << 8))
        tgt = w16(ACT_TABLE + 2 * r[1]) if r[1] <= 64 else 0
        return Ins(addr, r, "ACT",
                   f"idx={r[1]} third=${r[2]:02X} -> ${tgt:04X}" + suf,
                   edges, note)
    if nib == 0x4:  # MOVE court / saut $FF
        wid = img(addr + 1)
        if wid == 0xFF and op & 0x10:
            r = tail(addr, 4)
            return Ins(addr, r, "JUMP",
                       f"-> ${r[2] | (r[3] << 8):04X}" + suf,
                       [r[2] | (r[3] << 8)])
        n = 4 if sec else 2
        r = tail(addr, n)
        edges = [addr + n]
        if sec:
            edges.append(r[2] | (r[3] << 8))
        return Ins(addr, r, "MOVE",
                   f"wid=${wid:02X} arg=$FF" + suf, edges)
    if nib == 0xC:  # GOTO cle
        cle = img(addr + 1)
        r = tail(addr, 2)
        tgt = next((t for c, t in tables.get(base, []) if c == cle), None)
        note = "" if tgt is not None else "CLE ABSENTE (fuite entite)"
        return Ins(addr, r, "GOTOKEY", f"cle=${cle:02X}" + suf,
                   [tgt] if tgt is not None else [])
    if nib == 0xE:  # GOTO absolu
        r = tail(addr, 3)
        return Ins(addr, r, "GOTO", f"-> ${r[1] | (r[2] << 8):04X}" + suf,
                   [r[1] | (r[2] << 8)])
    if nib == 0xF:  # RAND
        bound = img(addr + 1)
        r = tail(addr, 2)
        hi = min(bound, nmax)
        tgts = [t for _, t in tables.get(base, [])[:hi + 1]]
        return Ins(addr, r, "RAND",
                   f"borne={bound} -> table[0..{hi}]" + suf, tgts)
    # INDIR 5-9,A,B,D
    r = tail(addr, 2)
    tbl = tables.get(base, [])
    tgt = tbl[0][1] if tbl else None
    note = ""
    if op & 0x10:
        note = "BIT $10 SANS EFFET (pas de step)"
    if tgt is None:
        note = (note + " " if note else "") + "TABLE VIDE ?"
    return Ins(addr, r, "INDIR",
               f"table[0] (${base:04X})" + suf, [tgt] if tgt is not None else [],
               note)


def walk(tables: dict[int, list[tuple[int, int]]],
         ents: dict,
         extra_seeds: list[tuple[int, int, int]] | None = None,
         ) -> tuple[dict[int, Ins], list[str]]:
    """Suivi de flot depuis les PC initiaux (+ graines observees en DB :
    (pc, base, nmax) ; base/nmax = entite proprietaire)."""
    out: dict[int, Ins] = {}
    covered: set[int] = set()
    anoms: list[str] = []
    seen: set[tuple[int, int, int]] = set()
    # Entrees d'abord (decodage canonique), puis graines DB en ordre
    # croissant (une graine au milieu d'une instruction deja decodee
    # est signalee CHEVAUCHEMENT, pas l'inverse).
    todo = sorted(extra_seeds or [], reverse=True)
    todo += [(e["pc"], e["base"], e["nmax"]) for e in ents]
    while todo:
        pc, base, nmax = todo.pop()
        if not (CODE_LO <= pc <= CODE_HI):
            continue
        if (pc, base, nmax) in seen:
            continue
        seen.add((pc, base, nmax))
        if pc in out:
            # meme code, autre contexte (base/nmax) : fusionne les edges
            # et propage le contexte (les triples vus sont sans effet).
            for t in decode_at(pc, base, nmax, tables).edges:
                if CODE_LO <= t <= CODE_HI:
                    if t not in out[pc].edges:
                        out[pc].edges.append(t)
                    todo.append((t, base, nmax))
            continue
        ins = decode_at(pc, base, nmax, tables)
        span = set(range(pc, pc + ins.size()))
        if span & covered:
            other = sorted(span & covered)
            anoms.append(f"CHEVAUCHEMENT ${pc:04X} ({ins.mn}) "
                         f"avec octets {','.join(f'${b:04X}' for b in other)}")
            continue
        out[pc] = ins
        covered |= span
        todo.extend((t, base, nmax) for t in ins.edges
                    if CODE_LO <= t <= CODE_HI)
    return out, anoms


# --- validation ----------------------------------------------------------
def observed_pcs() -> set[int]:
    """PC d'entites observes dans les deux DB (deltas + edge_deltas)."""
    return set().union(*observed_by_entity().values()) if observed_by_entity() else set()


def observed_by_entity() -> dict[int, set[int]]:
    """{e: {PC observes}} par entite."""
    out: dict[int, set[int]] = {e: set() for e in range(ENT_N)}
    out: dict[int, set[int]] = {e: set() for e in range(ENT_N)}
    hdb = ROOT / "build" / "sim" / "hobbit.db"
    sdb = Path(os.environ.get("SOLVER_DB",
                              str(ROOT / "build" / "sim" / "solver.db")))
    if hdb.is_file():
        cx = sqlite3.connect(f"file:{hdb}?mode=ro", uri=True)
        for e in range(ENT_N):
            o = ENT_BASE + e * ENT_SIZE + 2 - 0x28CC  # PClo/PChi (+2/+3)
            q = ("SELECT DISTINCT l.apres + 256*h.apres FROM deltas l "
                 "JOIN deltas h ON l.run_id=h.run_id AND l.n=h.n "
                 f"WHERE l.base=0x28CC AND l.off={o} "
                 f"AND h.base=0x28CC AND h.off={o + 1}")
            out[e].update(r[0] for r in cx.execute(q))
        cx.close()
    if sdb.is_file():
        cx = sqlite3.connect(f"file:{sdb}?mode=ro", uri=True)
        for e in range(ENT_N):
            o = ENT_BASE + e * ENT_SIZE + 2 - 0x28CC  # PClo/PChi (+2/+3)
            q = ("SELECT DISTINCT l.apres + 256*h.apres FROM edge_deltas l "
                 "JOIN edge_deltas h ON l.child=h.child "
                 f"WHERE l.base=0x28CC AND l.off={o} "
                 f"AND h.base=0x28CC AND h.off={o + 1}")
            out[e].update(r[0] for r in cx.execute(q))
        cx.close()
    return out


def main() -> int:
    use_db = "--no-db" not in sys.argv[1:]
    tables = parse_tables()
    ents = entities()
    live = [e for e in ents if e["id"] not in (0x00,)]
    by_ent = observed_by_entity() if use_db else {}
    seeds = [(pc, ents[e]["base"], ents[e]["nmax"])
             for e, pcs in by_ent.items() for pc in pcs
             if CODE_LO <= pc <= CODE_HI]
    n_seed = len(seeds)
    prog, anoms = walk(tables, ents, seeds)
    starts = sorted(prog)
    # bornes d'instructions
    bounds: set[int] = set()
    for ins in prog.values():
        bounds.update(range(ins.addr, ins.addr + ins.size()))
    # octets de code couverts par les tables/events/entites (donnees)
    data = set()
    for b, _s in D.INDIR_TABLES:
        a = b
        while D._img(a) != 0xFF:
            data.update(range(a, a + 3))
            a += 3
        data.add(a)
    data.update(range(EVT_BASE, ENT_BASE + ENT_N * ENT_SIZE + 1))
    # 1. octets de code non atteints
    for a in range(CODE_LO, CODE_HI + 1):
        if a not in bounds and a not in data:
            anoms.append(f"INATTEINT ${a:04X} (octet {D._img(a):02X})")
    # 2. cibles hors plage / notes du decodeur
    for ins in prog.values():
        for t in ins.edges:
            if not (CODE_LO <= t <= CODE_HI):
                anoms.append(f"CIBLE HORS PLAGE ${ins.addr:04X} -> ${t:04X}")
        if ins.note:
            anoms.append(f"${ins.addr:04X} {ins.mn} : {ins.note}")
    # 3. PC observes sur frontieres ?
    if use_db:
        for pc in sorted(observed_pcs()):
            if pc in data:
                continue
            if pc not in prog and pc not in bounds:
                anoms.append(f"PC OBSERVE HORS FRONTIERE ${pc:04X}")
    for e in live:
        ident = D.STATE_IDENTITY.get(e["id"], f"id${e['id']:02X}")
        tbl0 = tables.get(e["base"], [[None, None]])[0][1]
        print(f"== e{e['e']:02d} {ident} id=${e['id']:02X} "
              f"pc0=${e['pc']:04X} base=${e['base']:04X} "
              f"nmax={e['nmax']} table0=${tbl0 if tbl0 else 0:04X}")
    for addr in starts:
        ins = prog[addr]
        raw = " ".join(f"{b:02X}" for b in ins.raw)
        edge = (" -> " + ",".join(f"${t:04X}" for t in ins.edges)
                if ins.edges else " (fin)")
        print(f"  ${addr:04X}: {raw:14s} {ins.mn:7s} {ins.ops}{edge}"
              + (f"  !! {ins.note}" if ins.note else ""))
    print(f"-- {len(prog)} instructions, "
          f"{sum(i.size() for i in prog.values())} o de code"
          + (f" (dont {n_seed} graines DB)" if use_db else ""))
    if anoms:
        from collections import Counter
        print(f"-- {len(anoms)} anomalies "
              f"{dict(Counter(a.split()[0] for a in anoms))} :")
        for a in anoms:
            print(f"   {a}")
    else:
        print("-- aucune anomalie")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Vérifie la cohérence du découpage code/données de `disasm/<bloc>.info`.

Contrôles (bloc 4 par défaut) :
  A. chaque plage CODE se désassemble sans opcode illégal et finit sur
     une frontière d'instruction (règle ``JSR $440D`` appliquée) ;
  B. les cibles de branchements tombent sur des débuts d'instructions ;
  C. les cibles ``JSR``/``JMP`` absolues tombent sur des débuts
     d'instructions (ou, signalé à part, dans des zones de tables) ;
  D. les zones de tables qui se désassemblent comme du code
     (couverture >= 85 %) sont signalées comme code manqué ;
  E. les appels ROM directs sont comparés entre ROM 1.0 et 1.1
     (bloc 1 : informatif, l'écart 1.0/1.1 est le but du bloc) ;
  F. la table de vecteurs du bloc (bloc 4 : ``$2C05``) pointe sur des
     débuts d'instructions ;
  G. chaque ``JSR $440D`` est suivi de 2 octets marqués données ;
  H. les routines documentées (ROUTINE_DOCS) et la zéro-page nommée
     (ZP_NAMES) sont cohérentes avec le fichier d'information.

Sortie 0 si propre, 1 sinon.

Usage : .venv/bin/python scripts/disasm_check.py [--block block1|block4]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import BLOCKS, ZP_NAMES
from disasm_opcodes import BRANCH, INLINE_MSGS, JMP_ABS, JMP_IND, JSR, PRINT_MSG, ilen

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "data" / "hobbit.bin"
ROM10 = ROOT / "data" / "basic10.rom"
ROM11 = ROOT / "data" / "basic11b.rom"
BASE = 0x0400


def load_ranges(info: Path) -> tuple[list[tuple[int, int]], list[tuple[int, int, str]]]:
    code: list[tuple[int, int]] = []
    tabs: list[tuple[int, int, str]] = []
    for line in info.read_text().splitlines():
        m = re.match(r"RANGE \{ START \$(....); END \$(....); TYPE (\w+)", line)
        if m:
            a, b, t = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
            (code if t == "CODE" else tabs).append((a, b) if t == "CODE" else (a, b, t))
    return sorted(code), sorted(tabs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block", default="block4", choices=sorted(BLOCKS))
    args = ap.parse_args()
    block = BLOCKS[args.block]
    INFO = block.info
    routine_docs = block.routine_docs
    lo, hi = block.lo, block.hi

    raw = BIN.read_bytes()

    def B(a: int) -> int:
        return raw[a - BASE]

    code, tabs = load_ranges(INFO)
    code = [(a, b) for a, b in code if lo <= a <= hi]

    def in_tab(a: int) -> bool:
        return any(s <= a <= e for s, e, _ in tabs)

    # Super-plages : plages CODE séparées uniquement par des mots
    # pointeurs $440D (WORDTABLE) — la traversée est normale.
    words = sorted((s, e) for s, e, t in tabs if t == "WORDTABLE")
    supers: list[list[int]] = []
    for s, e in code:
        if supers and any(ws == supers[-1][1] + 1 and we + 1 == s
                          for ws, we in words):
            supers[-1][1] = e
        else:
            supers.append([s, e])
    code = [(a, b) for a, b in supers]

    errors = 0

    # --- A. marche linéaire par plage CODE ---
    starts: set[int] = set()
    illegal: list[int] = []
    brks: list[int] = []
    desync: list[tuple[int, int, int]] = []
    print_sites: list[tuple[int, int]] = []
    for s, e in code:
        pc = s
        while pc <= e:
            starts.add(pc)
            op = B(pc)
            if op == JSR and pc + 2 <= e and (B(pc + 1) | (B(pc + 2) << 8)) in INLINE_MSGS:
                t = B(pc + 1) | (B(pc + 2) << 8)
                if t == PRINT_MSG and pc + 4 <= e:
                    print_sites.append((pc, B(pc + 3) | (B(pc + 4) << 8)))
                pc += 5
                continue
            ln = ilen(op)
            if ln == 0:
                illegal.append(pc)
                pc += 1
            else:
                if op == 0x00:
                    brks.append(pc)
                pc += ln
        if pc != e + 1:
            desync.append((s, e, pc))
    print(f"A. plages CODE: {len(code)}, illégaux: {len(illegal)}, "
          f"BRK: {len(brks)}, désync: {len(desync)}")
    for a in illegal[:20]:
        print(f"   illégal ${a:04X}")
    for s, e, end in desync[:12]:
        print(f"   désync ${s:04X}-${e:04X} (fin décodage ${end:04X})")
    if illegal or desync:
        errors += 1

    # --- B/C. cibles ---
    br_bad: list[tuple[int, int]] = []
    abs_bad: list[tuple[int, int]] = []
    abs_tab: list[tuple[int, int]] = []
    romjsr: dict[int, list[int]] = {}
    for s, e in code:
        pc = s
        while pc <= e:
            op = B(pc)
            if op == JSR and pc + 2 <= e and (B(pc + 1) | (B(pc + 2) << 8)) in INLINE_MSGS:
                pc += 5
                continue
            if op in BRANCH and pc + 1 <= hi + 2:
                rel = B(pc + 1)
                rel -= 256 if rel >= 128 else 0
                t = pc + 2 + rel
                if t not in starts:
                    br_bad.append((pc, t))
                pc += 2
            elif op in (JSR, JMP_ABS) and pc + 2 <= hi + 2:
                t = B(pc + 1) | (B(pc + 2) << 8)
                if lo <= t <= hi:
                    if t not in starts:
                        (abs_tab if in_tab(t) else abs_bad).append((pc, t))
                elif 0xC000 <= t <= 0xFFFF:
                    romjsr.setdefault(t, []).append(pc)
                pc += 3
            elif op == JMP_IND and pc + 2 <= hi + 2:
                pc += 3
            else:
                ln = ilen(op)
                pc += ln if ln else 1
    print(f"B. branches hors code: {len(br_bad)}")
    for pc, t in br_bad[:12]:
        print(f"   br @ ${pc:04X} -> ${t:04X}")
    print(f"C. JSR/JMP hors code (non-table): {len(abs_bad)}")
    for pc, t in abs_bad[:12]:
        print(f"   @ ${pc:04X} -> ${t:04X}")
    print(f"   vers zones TABLE: {len(abs_tab)}")
    for pc, t in abs_tab[:12]:
        print(f"   @ ${pc:04X} -> ${t:04X} (table)")
    if br_bad or abs_bad:
        errors += 1

    # --- D. tables ressemblant à du code ---
    missed = []
    for s, e, t in tabs:
        if not (lo <= s <= hi):
            continue
        if e - s + 1 < 6:
            continue  # trop court pour être significatif
        pc, ok, total = s, 0, e - s + 1
        while pc <= e:
            op = B(pc)
            if op == JSR and pc + 2 <= e and (B(pc + 1) | (B(pc + 2) << 8)) in INLINE_MSGS:
                ok += 5
                pc += 5
                continue
            ln = ilen(op)
            if ln == 0:
                break
            ok += ln
            pc += ln
        if pc == e + 1 and ok / total >= 0.85:
            missed.append((s, e, t))
    print(f"D. tables décodables comme code (>=85%): {len(missed)}")
    for s, e, t in missed[:12]:
        print(f"   ${s:04X}-${e:04X} ({t})")
    if missed:
        errors += 1

    # --- E. appels ROM ---
    r10, r11 = ROM10.read_bytes(), ROM11.read_bytes()
    print(f"E. appels ROM directs: {len(romjsr)} distincts"
          + ("" if block.check_rom_diff else " (informatif : ecart 1.0/1.1 attendu)"))
    for t in sorted(romjsr):
        o = t - 0xC000
        same = r10[o:o + 16] == r11[o:o + 16]
        print(f"   ${t:04X} x{len(romjsr[t])} "
              f"{'IDENTIQUE 1.0/1.1' if same else '*** DIFFERENT 1.0/1.1 ***'}")
        if not same and block.check_rom_diff:
            errors += 1

    # --- F. vecteurs du bloc ---
    if block.vector_table is not None:
        va, n = block.vector_table
        bad_vec = []
        for k in range(n):
            ea = va + 3 * k
            t = B(ea + 1) | (B(ea + 2) << 8)
            if t not in starts:
                bad_vec.append((ea, t))
        print(f"F. vecteurs ${va:04X} hors code: {len(bad_vec)}")
        for ea, t in bad_vec:
            print(f"   vec @ ${ea:04X} -> ${t:04X}")
        if bad_vec:
            errors += 1
    else:
        print("F. vecteurs : sans objet pour ce bloc")

    # --- G. pointeurs $440D marqués données ---
    ptr_ok = ptr_bad = 0
    null_ptr = []
    for pc, t in print_sites:
        if in_tab(pc + 3) and in_tab(pc + 4):
            ptr_ok += 1
        else:
            ptr_bad += 1
        if t == 0:
            null_ptr.append(pc)
    print(f"G. JSR $440D: {len(print_sites)} sites, pointeurs marqués données: "
          f"{ptr_ok}, non marqués: {ptr_bad}, pointeurs nuls: {len(null_ptr)}")
    for pc in null_ptr[:8]:
        print(f"   TODO pointeur nul @ ${pc:04X}")
    if ptr_bad:
        errors += 1

    # --- H. documentation des routines (ROUTINE_DOCS) ---
    info_names: dict[str, list[int]] = {}
    for line in INFO.read_text().splitlines():
        m = re.match(r'RANGE \{ START \$(....); END \$(....); TYPE \w+; NAME "([^"]+)"', line)
        if m:
            info_names.setdefault(m.group(3), []).append(int(m.group(1), 16))
            continue
        m = re.match(r'LABEL \{ NAME "([^"]+)"; ADDR \$(....);', line)
        if m:
            info_names.setdefault(m.group(1), []).append(int(m.group(2), 16))
    doc_bad: list[str] = []
    seen_names: set[str] = set()
    for addr, (name, doc) in sorted(routine_docs.items()):
        tag = f"${addr:04X}"
        if not (lo <= addr <= hi):
            doc_bad.append(f"{tag} hors bloc")
            continue
        if addr not in starts:
            doc_bad.append(f"{tag} pas un debut d'instruction")
        if name is not None:
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                doc_bad.append(f"{tag} nom invalide: {name}")
            if name.startswith(("msg_", "code_")) or re.match(r"^L[0-9A-F]{4}$", name):
                doc_bad.append(f"{tag} nom reserve/auto: {name}")
            if name in seen_names:
                doc_bad.append(f"{tag} nom duplique: {name}")
            seen_names.add(name)
            if sorted(info_names.get(name, [])) != [addr]:
                doc_bad.append(f"{tag} label {name} absent ou duplique dans info")
        if not doc or "\n" in doc or '"' in doc or len(doc) > 160:
            doc_bad.append(f"{tag} resume invalide (1 ligne, sans guillemet, <=160c)")
    for addr, (name, doc) in sorted(ZP_NAMES.items()):
        tag = f"${addr:04X}"
        if not (0x00 <= addr <= 0xFF):
            doc_bad.append(f"{tag} hors zero-page")
            continue
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            doc_bad.append(f"{tag} nom invalide: {name}")
        if name.startswith(("msg_", "code_")) or re.match(r"^L[0-9A-F]{4}$", name):
            doc_bad.append(f"{tag} nom reserve/auto: {name}")
        if name in seen_names:
            doc_bad.append(f"{tag} nom duplique: {name}")
        seen_names.add(name)
        if sorted(info_names.get(name, [])) != [addr]:
            doc_bad.append(f"{tag} label {name} absent ou duplique dans info")
        if not doc or "\n" in doc or '"' in doc or len(doc) > 160:
            doc_bad.append(f"{tag} resume invalide (1 ligne, sans guillemet, <=160c)")
    print(f"H. routines documentees: {len(routine_docs)}, ZP nommee: {len(ZP_NAMES)}, "
          f"anomalies: {len(doc_bad)}")
    for b in doc_bad[:12]:
        print(f"   {b}")
    if doc_bad:
        errors += 1

    print("RÉSULTAT:", "PROPRE" if errors == 0 else f"{errors} catégorie(s) en erreur")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Génère un listing assembleur annoté du bloc 4 de The Hobbit (Oric).

Le découpage code/données est obtenu par **descente récursive** depuis les
points d'entrée (autorun ``$2C00``, ``$2C35`` et les 16 vecteurs ``$2C05``),
en suivant ``JSR``/``JMP``/branchements, jusqu'à point fixe. Les seeds
radare2 validés (décodage propre) et les entrées manuelles complètent la
couverture (dispatch indirect).

Règle spéciale : ``JSR $440D`` (routine d'affichage) est suivi de 2 octets
inline (adresse du message) ; le code reprend à JSR+5. Les pointeurs nuls
sont marqués ``TODO``.

da65 (cc65) produit ensuite le listing à partir du fichier d'information
(``disasm/hobbit.info``) et de ``data/hobbit.bin``.

Prérequis : ``tools/cc65/bin/da65`` (cf. AGENTS.md).
Vérification : scripts/check_disasm.py.

Usage : .venv/bin/python scripts/disasm.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from opcodes6502 import BRANCH, JMP_ABS, JMP_IND, JSR, PRINT_MSG, RTI, RTS, BRK, ilen

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "data" / "hobbit.bin"
DISASM = ROOT / "disasm"
INFO = DISASM / "hobbit.info"
LISTING = DISASM / "block4.asm"
R2CACHE = DISASM / ".r2_afl.txt"
TOOLS = ROOT / "tools" / "cc65" / "bin"
DA65 = TOOLS / "da65"
CA65 = TOOLS / "ca65"
LD65 = TOOLS / "ld65"

BASE = 0x0400
BLOCK1 = (0x0400, 0x0500)
BLOCK2 = (0x0500, 0x2BBD)
BLOCK3 = (0x7AC0, 0x91B1)
BLOCK4 = (0x2C00, 0x7A80)
ENTRY = 0x2C35

# Entrées manuelles confirmées à la main (dispatch indirect, trampolines).
# La table de vecteurs $2C05-$2C34 (16 x JMP) est du code par construction,
# ainsi que les routines suivantes (vérifiées par décodage jusqu'à un
# terminateur propre) que la descente n'atteint pas directement.
MANUAL_ENTRIES: list[int] = (
    [0x2C05 + 3 * k for k in range(16)]
    + [0x32B9, 0x3C8E, 0x5B44, 0x5BC9, 0x5D31, 0x698B,
       0x6A02, 0x6EA7, 0x6D55, 0x6F2A, 0x4599, 0x4DAF]
    + [0x32E9, 0x3CCE, 0x3D39, 0x4569, 0x6A12, 0x6A24, 0x6A5E, 0x6A86,
       0x6F44, 0x6F7E, 0x70D2, 0x6DD0]
)

# Seeds radare2 récusés : chevauchent des pointeurs $440D ou du connu.
# $6DCE = fcn.00006dce, octet haut du pointeur $165A (JSR $440D en $6DCA).
SEED_EXCLUDE = {0x6DCE}

# Routines documentées : adresse -> (nom, résumé une ligne).
# Le nom renomme le label (doit être unique, identifiant ca65 valide) ;
# le résumé est émis en commentaire da65 avant le label. Règles :
# - une seule ligne, sans guillemet `"`, <= 160 caractères ;
# - l'adresse doit être un début d'instruction (vérifié par check_disasm.py).
# Détails longs -> docs/block4-analysis.md (référencé par adresse).
ROUTINE_DOCS: dict[int, tuple[str | None, str]] = {
    # nom None = garde le nom existant (VECTORS), ajoute seulement le résumé.
    0x2C35: (None, "init : copies boot, pile, RAZ vars, prompt '> LOOK.', boucle d'input"),
    0x2DC8: ("init_vars", "RAZ variables ($97.., $AF, $CC/$CD) puis JMP main $7779"),
    0x3097: ("boot_copy", "copie $1B1A->$91D0 (1366 o) ; $6C = compteur"),
    0x30BB: ("boot_copyback", "recopie inverse ($8C)->($8A), meme gabarit"),
    0x440D: ("print_msg", "affiche le message du mot inline ; reprend a JSR+5 via JMP ($6A)"),
    0x44BE: ("msgptr_inc", "INC $6A (+ $6B si retenue) ; avance le pointeur message"),
    0x4737: ("fetch_retaddr", "copie 2 octets de la pile ($0200+$AF-2) en $8A/$8B"),
    0x71DB: ("tape_load", "LOAD bloc cassette via $0417 + verif $32/$33"),
    0x7215: ("tape_save", "SAVE : leader, en-tete 9 o, donnees, checksum EOR"),
    0x72A0: ("tape_prompt", "invites PREPARE TAPE / REWIND / PRESS ANY KEY"),
    0x7353: ("kb_scan", "scan clavier VIA ; A = touche bit7=presente, sinon bit7=0"),
    0x7481: ("kb_wait", "attente bloquante d'une touche (BPL) ; retour & $7F"),
    0x7489: ("cr_out", "affiche CR ($0D) via ch_out"),
    0x7491: ("ch_out", "filtres $0B/$0C/$0D/$C4 (capitales) puis rendu"),
    0x75B4: ("glyph_out", "rend un caractere en hires $A000 (font ($0403), ORA $40)"),
    0x75F6: ("ch_put", "sortie ecran : gere CR, scroll, pause bas d'ecran via kb_scan"),
    0x7619: ("pause_key", "pause 'press any key' : bip $771A, attente relachement+pression"),
    0x7747: ("hires_clear", "remplit $A000-$BFDF de $40"),
    0x7779: ("game_main", "boucle principale du jeu (atteinte via JMP vec_15)"),
}

# Points d'entrée de la table de vecteurs en $2C05 (16 entrées JMP).
VECTORS = {
    0x2C00: "autorun",
    0x2C03: "ptr_block3",
    0x2C05: "vec_init",
    0x2C08: "vec_01",
    0x2C0B: "vec_02",
    0x2C0E: "vec_03",
    0x2C11: "vec_04",
    0x2C14: "vec_05",
    0x2C17: "vec_06",
    0x2C1A: "vec_07",
    0x2C1D: "vec_08",
    0x2C20: "vec_09",
    0x2C23: "vec_10",
    0x2C26: "vec_11",
    0x2C29: "keyin",
    0x2C2C: "print_cr",
    0x2C2F: "putchar",
    0x2C32: "main",
    0x2C35: "start",
}

# Routines ROM (issues du désassemblage 1.0 et 1.1, cf. docs/).
ROM_LABELS = {
    0xE5C6: "PUTBYTE_10",
    0xE630: "READBYTE_10",
    0xE696: "TAPESYNC_10",
    0xE6BA: "WRITELEADER_10",
    0xE6CA: "SETUPTAPE_10",
    0xF73C: "CHAR2SCR_10",
    0xF960: "RESETSTAT_10",
    0xE65E: "PUTBYTE_11",
    0xE6C9: "READBYTE_11",
    0xE735: "SYNCTAPE_11",
    0xE75A: "WRITELEADER_11",
    0xE76A: "SETUPTAPE_11",
    0xF77C: "CHAR2SCR_11",
    0xF9AA: "RESETSTAT_11",
}


def printable_ratio(data: bytes, a: int, b: int) -> float:
    chunk = data[a - BASE:b - BASE + 1]
    if not chunk:
        return 0.0
    ok = sum(1 for c in chunk if 0x20 <= c < 0x7F or c == 0x0D)
    return ok / len(chunk)


def load_r2_seeds(path: Path) -> list[int]:
    seeds: list[int] = []
    try:
        text = path.read_text()
    except FileNotFoundError:
        return seeds
    for line in text.splitlines():
        m = re.match(r"0x([0-9a-f]+)\s+\d+\s+(\d+)\s", line)
        if m:
            seeds.append(int(m.group(1), 16))
    return seeds


def try_decode(raw: bytes, lo: int, hi: int, addr: int,
               starts: set[int], covered: set[int]) -> bool:
    """Valide un candidat : pas de texte, décodage propre (les octets
    pointeurs déjà connus sont dans `covered`). Les cibles de
    branchements/JSR internes doivent être des opcodes légaux.
    Accepté si terminateur RTS/RTI/JMP (>= 3 o, BRK >= 8 o et non
    inclus) ou fusion avec du connu (>= 4 o)."""

    def B(a: int) -> int:
        return raw[a - BASE]

    def word(a: int) -> int:
        return B(a) | (B(a + 1) << 8)

    def legal(a: int) -> bool:
        return lo <= a <= hi and ilen(B(a)) != 0

    chunk = raw[addr - BASE:addr - BASE + 16]
    if len(chunk) < 4:
        return False
    if sum(1 for c in chunk if 0x20 <= c < 0x7F or c == 0x0D) / len(chunk) > 0.5:
        return False
    pc, n = addr, 0
    while lo <= pc <= hi and n < 1024:
        if pc in starts:
            return n >= 4
        if pc in covered:
            return False
        op = B(pc)
        if op == JSR and pc + 2 <= hi and word(pc + 1) == PRINT_MSG:
            pc += 5
            n += 5
            continue
        ln = ilen(op)
        if ln == 0 or pc + ln - 1 > hi:
            return False
        if op == BRK:
            return n >= 8  # le BRK final (padding) n'est pas inclus
        if op in BRANCH and pc + 1 <= hi:
            rel = B(pc + 1)
            rel -= 256 if rel >= 128 else 0
            if not legal(pc + 2 + rel):
                return False
        if op == JSR and pc + 2 <= hi:
            t = word(pc + 1)
            if lo <= t <= hi and ilen(B(t)) == 0:
                return False
        n += ln
        if op in (RTS, RTI, JMP_ABS, JMP_IND):
            return n >= 3
        pc += ln
    return False


def msg_preview(raw: bytes, addr: int, n: int = 28) -> str:
    """Aperçu ASCII du message pointé (sanitisé pour da65)."""
    if addr == 0:
        return "TODO pointeur nul"
    off = addr - BASE
    if off < 0 or off >= len(raw):
        return "(hors image)"
    out = []
    for c in raw[off:off + n]:
        out.append(chr(c) if 0x20 <= c < 0x7F else ".")
    return "".join(out).replace('"', "'")


def sanitize_comment(doc: str) -> str:
    """Sanitise un résumé ROUTINE_DOCS pour da65 (une ligne, sans guillemet)."""
    return doc.replace('"', "'")


def descend(raw: bytes, lo: int, hi: int, entries: list[int]):
    """Descente récursive. Renvoie (code_bytes, ptrs, starts, ext, conflicts)."""

    def B(a: int) -> int:
        return raw[a - BASE]

    def word(a: int) -> int:
        return B(a) | (B(a + 1) << 8)

    def region(a: int) -> str:
        if lo <= a <= hi:
            return "here"
        if BLOCK1[0] <= a <= BLOCK1[1]:
            return "bloc1"
        if BLOCK2[0] <= a <= BLOCK2[1]:
            return "bloc2"
        if BLOCK3[0] <= a <= BLOCK3[1]:
            return "bloc3"
        if 0xC000 <= a <= 0xFFFF:
            return "rom"
        return "autre"

    from collections import Counter

    code_bytes: set[int] = set()
    ptrs: dict[int, int] = {}
    starts: set[int] = set()
    conflicts: list[int] = []
    ext: Counter = Counter()
    worklist = list(entries)

    while worklist:
        pc = worklist.pop()
        if pc in starts:
            continue
        if pc in code_bytes:
            conflicts.append(pc)
            continue
        if not (lo <= pc <= hi):
            continue
        while lo <= pc <= hi:
            if pc in starts:
                break
            if pc in code_bytes:
                conflicts.append(pc)
                break
            op = B(pc)
            ln = ilen(op)
            if ln == 0:
                break
            if op == JSR and pc + 2 <= hi and word(pc + 1) == PRINT_MSG:
                for b in range(pc, pc + 3):
                    code_bytes.add(b)
                ptrs[pc + 3] = word(pc + 3)
                starts.add(pc)
                pc += 5
                continue
            for b in range(pc, pc + ln):
                code_bytes.add(b)
            starts.add(pc)
            if op == JSR:
                t = word(pc + 1)
                r = region(t)
                if r == "here" and t not in starts:
                    worklist.append(t)
                elif r != "here":
                    ext[(r, t)] += 1
                pc += 3
            elif op == JMP_ABS:
                t = word(pc + 1)
                r = region(t)
                if r == "here":
                    worklist.append(t)
                else:
                    ext[(r, t)] += 1
                break
            elif op == JMP_IND:
                break
            elif op in (RTS, RTI, BRK):
                break
            elif op in BRANCH:
                rel = B(pc + 1)
                rel -= 256 if rel >= 128 else 0
                t = pc + 2 + rel
                if region(t) == "here":
                    worklist.append(t)
                pc += 2
            else:
                pc += ln
    return code_bytes, ptrs, starts, ext, conflicts


def build_info(raw: bytes, code_bytes: set[int], ptrs: dict[int, int],
               lo: int, hi: int) -> str:
    ptr_addrs = set()
    for p in ptrs:
        ptr_addrs.add(p)
        ptr_addrs.add(p + 1)

    lines = ['GLOBAL { CPU "6502"; PAGELENGTH 0; };']
    code_ranges: list[list[int]] = []
    cur: list[int] | None = None
    for a in range(lo, hi + 1):
        if a in code_bytes and a not in ptr_addrs:
            if cur is None:
                cur = [a, a]
            else:
                cur[1] = a
        else:
            if cur is not None:
                code_ranges.append(cur)
                cur = None
    if cur is not None:
        code_ranges.append(cur)
    named = {**VECTORS, **ROM_LABELS}
    for addr, (name, _doc) in ROUTINE_DOCS.items():
        if name is not None:
            named[addr] = name
    used: set[int] = set()
    range_starts = {a for a, _b in code_ranges}
    for a, b in code_ranges:
        name = named.get(a, f"code_{a:04X}")
        if a in named:
            used.add(a)
        rng = f'RANGE {{ START ${a:04X}; END ${b:04X}; TYPE CODE; NAME "{name}";'
        doc = ROUTINE_DOCS.get(a, (None, None))[1]
        if a in ROUTINE_DOCS and doc:
            rng += f' COMMENT "{sanitize_comment(doc)}";'
        lines.append(rng + " };")
    for p in sorted(ptrs):
        msg = ptrs[p]
        preview = msg_preview(raw, msg)
        comment = "TODO pointeur $0000" if msg == 0 else f"-> ${msg:04X} {preview}"
        lines.append(f"RANGE {{ START ${p:04X}; END ${p + 1:04X}; TYPE WORDTABLE; }};")
        lines.append(f'LABEL {{ NAME "msg_{p:04X}"; ADDR ${p:04X}; COMMENT "{comment}"; }};')
        used.add(p)
    for addr, (name, doc) in sorted(ROUTINE_DOCS.items()):
        if not (lo <= addr <= hi):
            continue
        if addr in range_starts:
            continue  # déjà nommé+commenté via RANGE (LABEL ferait doublon)
        label = name if name is not None else named.get(addr, f"code_{addr:04X}")
        lines.append(f'LABEL {{ NAME "{label}"; ADDR ${addr:04X}; '
                     f'COMMENT "{sanitize_comment(doc)}"; }};')
        used.add(addr)
    marked = set(code_bytes) | ptr_addrs
    cur = None
    pending: list[list[int]] = []
    for a in range(lo, hi + 1):
        if a not in marked:
            if cur is None:
                cur = [a, a]
            else:
                cur[1] = a
        else:
            if cur is not None:
                pending.append(cur)
                cur = None
    if cur is not None:
        pending.append(cur)
    for ga, gb in pending:
        kind = "TEXTTABLE" if printable_ratio(raw, ga, gb) >= 0.55 else "BYTETABLE"
        lines.append(f"RANGE {{ START ${ga:04X}; END ${gb:04X}; TYPE {kind}; }};")
    for addr, name in named.items():
        if addr not in used:
            lines.append(f'LABEL {{ NAME "{name}"; ADDR ${addr:04X}; }};')
    return "\n".join(lines) + "\n"


def main() -> int:
    import subprocess

    if not BIN.exists():
        print(f"{BIN} manquant : lancez scripts/extract.py")
        return 1
    DISASM.mkdir(exist_ok=True)
    raw = BIN.read_bytes()
    lo, hi = BLOCK4

    def B(a: int) -> int:
        return raw[a - BASE]

    vec_targets = [B(0x2C05 + 3 * k + 1) | (B(0x2C05 + 3 * k + 2) << 8) for k in range(16)]
    entries = [0x2C00, ENTRY] + vec_targets + MANUAL_ENTRIES
    r2seeds = load_r2_seeds(R2CACHE)

    for it in range(10):
        code_bytes, ptrs, starts, ext, conflicts = descend(raw, lo, hi, entries)
        ptr_bytes = set()
        for p in ptrs:
            ptr_bytes.add(p)
            ptr_bytes.add(p + 1)
        added = 0
        for s in r2seeds:
            if not (lo <= s <= hi):
                continue
            if s in SEED_EXCLUDE:
                continue
            if s in starts or s in code_bytes or s in ptr_bytes:
                continue
            if s in entries:
                continue
            if try_decode(raw, lo, hi, s, starts, code_bytes | ptr_bytes):
                entries.append(s)
                added += 1
        print(f"  itération {it}: {len(code_bytes)} octets code, +{added} entrées")
        if not added:
            break

    INFO.write_text(build_info(raw, code_bytes, ptrs, lo, hi))

    print(f"bloc4 ${lo:04X}-${hi:04X} : {len(code_bytes)} octets code, "
          f"{len(ptrs)} pointeurs $440D, {len(set(conflicts))} conflits")
    if conflicts:
        print("  conflits :",
              ", ".join(f"${a:04X}" for a in sorted(set(conflicts))[:12]))
    print("  références externes (top) :")
    for (r, t), n in ext.most_common(12):
        print(f"    {r} ${t:04X} x{n}")
    nulls = [p for p, m in ptrs.items() if m == 0]
    print(f"  pointeurs nuls : {len(nulls)}",
          ", ".join(f"${p:04X}" for p in sorted(nulls)))

    if not DA65.is_file():
        print(f"{DA65} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
        return 1
    slice_path = Path("/tmp/hobbit_block4.bin")
    slice_path.write_bytes(raw[lo - BASE:hi - BASE + 1])
    subprocess.run(
        [str(DA65), "-i", str(INFO), "-S", f"0x{lo:x}", "-o", str(LISTING), str(slice_path)],
        check=True,
    )
    # En-tête da65 volatil (date d'extraction) : on le neutralise pour un
    # listing déterministe (seule la ligne de version est conservée).
    asm = LISTING.read_text().splitlines(keepends=True)
    asm = [ln for ln in asm
           if not ln.startswith("; Created:")
           and not ln.startswith("; Input file:")
           and not ln.startswith("; Page:")]
    header = (
        "; ============================================================\n"
        "; The Hobbit (Oric, 1982) - bloc 4 ($2C00-$7A80)\n"
        "; Listing généré par scripts/disasm.py (descente récursive + da65)\n"
        "; Charge en mémoire à $2C00, entrée autorun $2C00 -> $2C35.\n"
        "; Convention : JSR $440D + pointeur inline (2 octets, adresse du\n"
        "; message) ; reprise du code à JSR+5.\n"
        "; ============================================================\n\n"
    )
    LISTING.write_text(header + "".join(asm))
    print(f"Listing écrit : {LISTING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

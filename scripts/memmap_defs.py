#!/usr/bin/env python3
"""SSOT de la carte memoire SAVE/LOAD (The Hobbit, Oric).

Decomposition des 4 regions basses sauvegardees + nommage des slots.
Consomme par scripts/memmap.py (registre/couverture) et check_memmap.py.

Regions (meme ordre que harness/snap.s REGTAB / solver_db.REGIONS) :
  $00BE   24  ZP joueur/contexte
  $1B1A 1366  etats (61 cles $1A62)
  $28CC  753  tables INDIR + scripts VM + events + entites
  $211A 1480  records (table $2070)

Un slot = une variable/structure nommee rattachee a une adresse. Les blocs
d'etat partitionnent la region par ORDRE D'ADRESSE (bases non monotones en
ordre de cle, cf. savegame-memory-map.md §2) : chaque octet appartient a la
cle dont la base est la plus grande <= adresse (cf. state_owner).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = ROOT / "data" / "hobbit.bin"
IMAGE_BASE = 0x0400

# (base basse, longueur, nom) — ordre SAVE/LOAD.
REGIONS = [(0x00BE, 0x18, "ZP"), (0x1B1A, 0x556, "etats"),
           (0x28CC, 0x2F1, "scripts"), (0x211A, 0x5C8, "records")]
REGION_LEN = {b: ln for b, ln, _ in REGIONS}
TOTAL_BYTES = sum(ln for _, ln, _ in REGIONS)

# Genre de slot : var = variable mutable ; gabarit/table/code/const = statique.
VAR, GABARIT, TABLE, CODE, CONST, UNKNOWN = (
    "var", "gabarit", "table", "code", "const", "?")


@dataclass(frozen=True)
class Slot:
    region: str
    name: str
    kind: str
    doc: str
    addr: int


# --- §1. Zero-page $BE-$D5 (24 o) ---------------------------------------
ZP_NAMES: dict[int, tuple[str, str]] = {
    0xBE: ("exploc", "lieu attendu par l'evenement (copie de key)"),
    0xBF: ("tblA", "pointeur lo table action/patch $7116 (pas 4) ; hi $C0"),
    0xC0: ("tblA_hi", "haut de tblA"),
    0xC1: ("tblB", "pointeur lo table errance/desc $7126 (pas 6) ; hi $C2"),
    0xC2: ("tblB_hi", "haut de tblB"),
    0xC5: ("obj", "objet/entite courant (id ; $FF=personne)"),
    0xC6: ("crec", "enregistrement courant octet bas (base $1B1A)"),
    0xC7: ("crec_hi", "haut de crec"),
    0xCA: ("recptr", "pointeur de record de lieu courant (copie de ptr ; hi $CB)"),
    0xCB: ("recptr_hi", "haut de recptr (toujours $21-$26 = region records)"),
    0xCC: ("score", "score courant en points (lu par SCORE $3CD4 ; hi $CD)"),
    0xCD: ("score_hi", "haut du score (remis a 0 apres victoire)"),
    0xC8: ("ploc", "lieu du joueur"),
    0xC9: ("eloc", "lieu de l'entite (visibilite : eloc==ploc)"),
    0xCE: ("once", "verrou one-shot (pose, teste+consomme)"),
}

# --- §2. Etats $1B1A (1366 o), 61 cles $1A62 ----------------------------
# (cle, base) ; trou $2C-$3B sans cle.
STATE_KEYS: list[tuple[int, int]] = [
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
# Offsets de champ (sens generique d'un bloc d'etat). +0 = regime, jamais
# mute (doc §6 : "jamais modifie") -> constante.
STATE_FIELD: dict[int, tuple[str, str, str]] = {
    0x00: ("type", CONST, "octet de type ($01 localise, autres regimes)"),
    0x01: ("carrier", VAR, "porteur (id entite ; $FF=personne)"),
    0x05: ("hp", VAR, "degats/vie (act_p14_00 : +10/coup, bit7=>tue ; x2 transfo $6F1B)"),
    0x06: ("tough", VAR, "seuil de robustesse (compare aux degats +$05 ; act_p14_01)"),
    0x07: ("flags", VAR, "flags (b1/b3 combat, b5 ouvert portes, b7 divers)"),
    0x08: ("tpl", GABARIT, "template de description (tokens runtime)"),
    0x0A: ("altptr", VAR, "pointeur secondaire (2 o ; ex. $098F pose par $6F1B)"),
    0x0B: ("altptr_hi", VAR, "haut de altptr"),
    0x10: ("eloc", VAR, "lieu de l'entite (si +0==$01)"),
}
# Champs specifiques a une cle (cle, offset) -> (nom, genre, doc).
STATE_SPECIAL: dict[tuple[int, int], tuple[str, str, str]] = {
    (0x00, 0x05): ("falls", VAR, "compteur de chutes (>>1 ; 0=mort)"),
    (0x06, 0x07): ("lock", VAR, "verrou-fenetre $0E/$0F (bit $20 ouvre)"),
    (0x08, 0x07): ("lock", VAR, "verrou-fenetre $F2 porte rouge (bit $20 ouvre)"),
    (0x0C, 0x07): ("lock", VAR, "verrou-fenetre $180 ($20->$21)"),
}
# Partition des blocs par ordre d'ADRESSE (pas de chevauchement) : chaque
# octet appartient a la cle dont la base est la plus grande <= adresse.
# Verifie sur les 32 references litterales de block4.asm (0 ambiguite).
_STATE_BASES: list[tuple[int, int]] = sorted((b, k) for k, b in STATE_KEYS)
_STATE_LO, _STATE_HI = 0x1B1A, 0x2070


def state_owner(addr: int) -> tuple[int, int] | None:
    """(cle, offset) du bloc contenant addr, ou None hors region etats."""
    if not (_STATE_LO <= addr < _STATE_HI):
        return None
    key, base = None, None
    for b, k in _STATE_BASES:
        if b <= addr:
            base, key = b, k
        else:
            break
    return None if key is None else (key, addr - base)

# Identites connues des cles (savegame-memory-map.md §2 ; "presume" = a
# confirmer). Token court -> nom lisible du slot.
STATE_IDENTITY: dict[int, str] = {
    0x00: "player",       # bloc global (compteur de chutes +$05)
    0x01: "rock_door",    # the heavy rock door ($06 N->$07 ; +7 bit0=verrou, bit5=ouvert)
    0x03: "map",
    0x04: "key",          # the large key (porte par le troll hideux $47 a $05)
    0x0E: "sword",        # the short strong sword (source de lumiere : +4 b7, +7 $94)
    0x10: "ring",         # the valuable golden ring (cache en $3D ; pocket de Gollum $1CC5<-$44)
    0x26: "lunch",
    0x3E: "gandalf",
    0x41: "dragon",       # presume
    0x42: "butler",       # dormant, eloc $20 ; presume
    0x44: "gollum",       # presume
    0x47: "troll_hideous",
    0x48: "troll_vicious",
}

# --- §3. Scripts/tables $28CC (753 o) -----------------------------------
INDIR_TABLES: list[tuple[int, int]] = [
    (0x28CC, 7), (0x28D3, 7), (0x28DA, 7), (0x2943, 15), (0x2984, 10),
    (0x29B2, 10), (0x29C3, 4), (0x29E4, 10), (0x2A2E, 10), (0x2A4D, 7),
    (0x2A70, 7), (0x2A88, 7), (0x2AC9, 7),
]
EVENTS_BASE, EVENTS_N, EVENTS_SIZE = 0x2B12, 10, 5
EVENTS_FIELD = ["id", "cpt", "actA", "cond", "actB"]
# id/actA/cond/actB = configuration (immuable) ; seul cpt est le compteur
# mutable (evt_tick : cpt--, armement cpt:=id).
EVENTS_KIND = [CONST, VAR, CONST, CONST, CONST]
ENTITIES_BASE, ENTITIES_N, ENTITIES_SIZE = 0x2B45, 17, 7
ENTITIES_FIELD = ["id", "n", "PClo", "PChi", "balo", "bahi", "s6"]
# id (reveil dormant), PC (errance VM) et s6 (quasi-statique) = variables ;
# n et base = configuration fixe (doc §6).
ENTITIES_KIND = [VAR, CONST, VAR, VAR, CONST, CONST, VAR]


def _load_image() -> bytes:
    try:
        return IMAGE.read_bytes()
    except OSError:
        return b""


_RAW = _load_image()


def _img(addr: int) -> int:
    i = addr - IMAGE_BASE
    return _RAW[i] if 0 <= i < len(_RAW) else 0


def _rec_table() -> dict[int, int]:
    """{id: adresse record} depuis $2070 (id<$50, pointeur non nul)."""
    out = {}
    for i in range(0x50):
        w = _img(0x2070 + 2 * i) | (_img(0x2070 + 2 * i + 1) << 8)
        if w:
            out[i] = w
    return out


RECORDS: dict[int, int] = _rec_table()
_REC_SORTED = sorted(RECORDS.items(), key=lambda kv: kv[1])
RECORD_FIELD = {
    "b0": (0, VAR, "flags record (bit6=visite pose au LOOK, &$0E template)"),
    "b1": (1, CONST, "flags record (bit6 inclusion recherche ; immuable)"),
    "conds": (2, GABARIT, "signature d'appartenance (3 paires mot/masque)"),
    "desc": (8, GABARIT, "pointeur description LOOK"),
    "exits": (10, GABARIT, "sorties [dir,cond,dest]* terminees $FF"),
}


def _record_of(addr: int) -> int | None:
    """id du record contenant addr (par borne basse suivante)."""
    for k, (i, base) in enumerate(_REC_SORTED):
        nxt = (_REC_SORTED[k + 1][1] if k + 1 < len(_REC_SORTED)
               else base + 0x40)
        if base <= addr < nxt:
            return i
    return None


def annotate(base: int, off: int) -> list[Slot]:
    """Tous les slots candidats pour l'octet (base, off) de la region."""
    addr = base + off
    out: list[Slot] = []
    if base == 0x00BE:
        nm = ZP_NAMES.get(addr)
        if nm:
            out.append(Slot("ZP", nm[0], VAR, nm[1], addr))
        else:
            out.append(Slot("ZP", f"zp${addr:02X}", UNKNOWN,
                            "inconnu (scratch ?, cf. carte §1)", addr))
    elif base == 0x1B1A:
        own = state_owner(addr)
        if own is not None:
            key, d = own
            sp = STATE_SPECIAL.get((key, d))
            fld = sp or STATE_FIELD.get(d)
            if fld:
                nm, kind, doc = fld
            else:
                nm, kind, doc = f"+${d:02X}", UNKNOWN, "offset de bloc"
            ident = STATE_IDENTITY.get(key, f"state${key:02X}")
            out.append(Slot("etats", f"{ident}.{nm}", kind,
                            f"cle ${key:02X} : {doc}", addr))
    elif base == 0x28CC:
        if EVENTS_BASE <= addr < EVENTS_BASE + EVENTS_N * EVENTS_SIZE:
            e = (addr - EVENTS_BASE) // EVENTS_SIZE
            f = (addr - EVENTS_BASE) % EVENTS_SIZE
            out.append(Slot("scripts", f"evt{e}.{EVENTS_FIELD[f]}",
                            EVENTS_KIND[f],
                            "evenement differe [id,cpt,actA,cond,actB]", addr))
        elif ENTITIES_BASE <= addr < ENTITIES_BASE + ENTITIES_N * ENTITIES_SIZE:
            e = (addr - ENTITIES_BASE) // ENTITIES_SIZE
            f = (addr - ENTITIES_BASE) % ENTITIES_SIZE
            out.append(Slot("scripts", f"ent{e}.{ENTITIES_FIELD[f]}",
                            ENTITIES_KIND[f],
                            "entite VM [id,n,PC,base,s6]", addr))
        else:
            tbl = next(((a, s) for a, s in INDIR_TABLES if a <= addr < a + s),
                       None)
            if tbl:
                out.append(Slot("scripts", f"indir${tbl[0]:04X}+${addr-tbl[0]}",
                                TABLE, "table de sauts 3 o [cle,lo,hi]", addr))
            else:
                out.append(Slot("scripts", f"code${addr:04X}", CODE,
                                "script VM (opcodes)", addr))
    elif base == 0x211A:
        i = _record_of(addr)
        if i is None:
            out.append(Slot("records", f"rec?${addr:04X}", UNKNOWN,
                            "hors record (trou ?)", addr))
        else:
            d = addr - RECORDS[i]
            fld = None
            for nm, (fo, kind, doc) in RECORD_FIELD.items():
                if d == fo or (nm == "conds" and 2 <= d < 8):
                    fld = (nm, kind, doc)
                    break
                if nm == "desc" and 8 <= d < 10:
                    fld = (nm, kind, doc)
                    break
                if nm == "exits" and d >= 10:
                    fld = (nm, kind, doc)
                    break
            if not fld:
                fld = ("?", UNKNOWN, "offset de record")
            out.append(Slot("records", f"rec${i:02X}.{fld[0]}", fld[1],
                            fld[2], addr))
    return out


def region_of(base: int) -> str:
    for b, _ln, nom in REGIONS:
        if b == base:
            return nom
    return "?"


def inv_regions() -> list[tuple[int, int, str]]:
    return list(REGIONS)


if __name__ == "__main__":
    print(f"regions: {len(REGIONS)}, octets: {TOTAL_BYTES}")
    print(f"cles d'etat: {len(STATE_KEYS)}, "
          f"INDIR: {len(INDIR_TABLES)}, records: {len(RECORDS)}")
    for b, off in [(0x00BE, 0x0A), (0x1B1A, 0x05), (0x1B1A, 0x10),
                   (0x28CC, 0x246), (0x28CC, 0x279), (0x211A, 0x00)]:
        print(f"  ${b:04X}+${off:04X} -> "
              + "; ".join(f"{s.name}[{s.kind}]" for s in annotate(b, off)))

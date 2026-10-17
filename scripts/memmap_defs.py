#!/usr/bin/env python3
"""SSOT de la carte memoire SAVE/LOAD (The Hobbit, Oric).

Decomposition des 4 regions basses sauvegardees + nommage des slots.
Consomme par scripts/memmap.py (registre/couverture) et memmap_check.py.

Regions (meme ordre que src/6502/snap.s REGTAB / solver_db.REGIONS) :
  $00BE   24  ZP joueur/contexte
  $1B1A 1366  etats (61 cles $1A62)
  $28CC  753  tables INDIR + scripts VM + events + entites
  $211A 1480  records (table $2070)

Un slot = une variable/structure nommee rattachee a une adresse. Les blocs
d'etat partitionnent la region par ORDRE D'ADRESSE (bases non monotones en
ordre de cle, cf. memory-map.md §2) : chaque octet appartient a la
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
    0xC5: ("obj", "entite/acteur courant (id ; $FF=personne) ; acteur du log AnimAction (ref. Wilderland L_ACTING_ANIMAL)"),
    0xC6: ("crec", "enregistrement courant octet bas (base $1B1A)"),
    0xC7: ("crec_hi", "haut de crec"),
    0xCA: ("recptr", "pointeur de record de lieu courant (copie de ptr ; hi $CB)"),
    0xCB: ("recptr_hi", "haut de recptr (toujours $21-$26 = region records)"),
    0xCC: ("score", "score courant en points (lu par SCORE $3CD4 ; hi $CD)"),
    0xCD: ("score_hi", "haut du score (remis a 0 apres victoire)"),
    0xC8: ("ploc", "lieu du joueur"),
    0xC9: ("eloc", "lieu de l'entite (visibilite : eloc==ploc)"),
    0xCE: ("once", "verrou one-shot (pose, teste+consomme)"),
    0xC3: ("dflag", "flag action dragon (init 0 par l'intro, jamais arme)"),
    0xC4: ("sflag", "flag sortie texte (evt_disarme7 : ajoute H apres s/S)"),
    0xCF: ("cand", "index de candidat, tables deplacement $48D3/$48D5"),
    0xD0: ("mwt", "budget/poids deplacement (errance : $0A moins couts)"),
    0xD1: ("qrd", "curseur lecture file d'actions $4905 (RAZ/commande)"),
    0xD2: ("qwr", "curseur ecriture file d'actions $4905 (RAZ/commande)"),
    0xD3: ("macc", "accumulateur de poids (errance)"),
    0xD4: ("mcnt", "compteur de candidats retenus (errance)"),
    0xD5: ("said", "flag PNJ a parle/refuse (code_6C2E/act_v14_13)"),
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
    0x00: ("nloc", CONST, "N = nombre de lieux (WL.h P0_OFF_QTY) ; lieux en +$10..+$10+N-1 (N=1 objet localise ; N>1 portes/eau/toile, cf. L5FFA)"),
    0x01: ("carrier", VAR, "porteur (id entite ; $FF=personne) (= WL.h P1_OFF_MO, 'Mother object')"),
    0x02: ("volume", CONST, "volume (objet) / capacite (contenant) (WL.h P2_OFF_VOLUME) ; act_p14_13 'IS TOO FULL' ; ref. npc_stats"),
    0x03: ("masse", CONST, "masse/poids de portage (WL.h P3_OFF_MASS ; obj_count_add $5C2B ; ref. npc_stats Mass)"),
    0x04: ("oclass", CONST, "bits0-2 = classe d'objet/contenant ($06 = cas special) ; obj_type_route $5B9B (WL.h P4_OFF)"),
    0x05: ("hp", VAR, "force/degats (WL.h P5_OFF_STRENGTH ; combat : +10/coup, bit7=>tue ; x2 transfo $6F1B ; ref. npc_stats Strength)"),
    0x06: ("tough", VAR, "seuil de robustesse (WL.h P6_OFF ; compare aux degats +$05 ; act_p14_01)"),
    0x07: ("flags", VAR, "attributs (= WL.h ATTRIBUTE_OFF ; ATTR_*) : b0 verrou, b1 fluide, b2 plein, b3 casse/mort, b4 eclaire, b5 ouvert, b6 animal, b7 visible"),
    0x08: ("noun", GABARIT, "mot du dictionnaire = nom de l'objet (word_render ; name_from_record $5A9D) ; sert de gabarit au LOOK"),
    0x09: ("noun_hi", GABARIT, "haut de noun"),
    0x0A: ("adj1/altptr", VAR, "adjectif 1 (mot dico) ; reutilise en pointeur secondaire (ex. $098F pose par $6F1B)"),
    0x0B: ("adj1_hi", VAR, "haut de adj1"),
    0x0C: ("adj2/descp", VAR, "adjectif 2 (mot dico) ; RAZ en pointeur de description runtime (obj_state_clear $5AF0)"),
    0x0D: ("adj2_hi", VAR, "haut de adj2"),
    0x10: ("eloc", VAR, "premier des N lieux (+$00) (= WL.h P10_OFF_ROOM) ; liste +$10..+$10+N-1"),
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
# Partie fixe d'un bloc = champs +0..+$0F (16 o). Suivent : N lieux (+$10..,
# N = octet +0, balayes par L5FFA) puis la **liste des verbes autorises**
# (paires 2 o [verbe, param], terminee $FF) a l'offset 16+N, accordee au record
# et lue par verb_obj_ok ($52FB, via index_id_table2 ; cf. block4.asm:5959-5961).
_STATE_FIELD_LEN = 0x10
_KEY_BASE: dict[int, int] = dict(STATE_KEYS)


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

# Identites des cles = mot designe par +$08/+$09 (cle de dictionnaire rendue
# par word_render $4241, cf. memmap.py ident). Suffixe = cle hex quand le mot
# se repete (DOOR x9, KEY x4, WATER x4, GOBLIN x6, RIVER x2, TROLL x2), pour
# garantir l'unicite du nom de slot.
STATE_IDENTITY: dict[int, str] = {
    0x00: "player",       # YOU
    0x01: "rock_door",    # DOOR ($06 N->$07 ; +7 bit0=verrou, bit5=ouvert)
    0x02: "key02",        # KEY
    0x03: "map",          # MAP
    0x04: "key",          # KEY (la grande cle, portee par le troll hideux $47)
    0x05: "door05",       # DOOR
    0x06: "crack",        # CRACK
    0x07: "web",          # WEB
    0x08: "door08",       # DOOR
    0x09: "river09",      # RIVER
    0x0A: "door0a",       # DOOR
    0x0B: "door0b",       # DOOR
    0x0C: "door0c",       # DOOR
    0x0D: "door0d",       # DOOR
    0x0E: "sword",        # SWORD (source de lumiere : +4 b7, +7 $94)
    0x0F: "key0f",        # KEY (cle rouge presume, portee par le butler $42)
    0x10: "ring",         # RING (l'anneau d'or ; pocket de Gollum $1CC5<-$44)
    0x11: "door11",       # DOOR
    0x12: "rope",         # ROPE
    0x13: "barrel",       # BARREL
    0x14: "wine",         # WINE
    0x15: "water15",      # WATER
    0x16: "water16",      # WATER
    0x17: "water17",      # WATER
    0x18: "water18",      # WATER
    0x19: "bow",          # BOW
    0x1A: "arrow",        # ARROW
    0x1B: "window",       # WINDOW
    0x1C: "torch",        # TORCH
    0x1D: "sand",         # SAND
    0x1E: "door1e",       # DOOR
    0x1F: "cache",        # CACHE
    0x20: "curtain",      # CURTAIN
    0x21: "cupboard",     # CUPBOARD
    0x22: "food",         # FOOD
    0x23: "treasure",     # TREASURE
    0x24: "wall",         # WALL
    0x25: "chest",        # CHEST
    0x26: "lunch",        # LUNCH
    0x27: "portcullis",   # PORTCULLIS
    0x28: "stone",        # STONE
    0x29: "boat",         # BOAT
    0x2A: "river2a",      # RIVER
    0x2B: "key2b",        # KEY
    0x3C: "dragon",       # DRAGON (dormant, arme par event)
    0x3D: "nasty_goblin",   # NASTYGOBLIN (Wilderland OBJNR_NASTYGOBLIN, "nG")
    0x3E: "gandalf",      # GANDALF (OBJNR_GANDALF)
    0x3F: "thorin",       # THORIN (OBJNR_THORIN)
    0x40: "wood_elf",     # ELF (OBJNR_ELF, "WE")
    0x41: "elrond",       # ELROND (OBJNR_ELROND ; corrige l'ancien « dragon presume »)
    0x42: "butler",       # BUTLER (OBJNR_BUTLER, dormant, eloc $20)
    0x43: "warg",         # WARG (OBJNR_WARG)
    0x44: "gollum",       # GOLLUM (OBJNR_GOLLUM)
    0x45: "hideous_goblin", # OBJNR_HIDEOUSGOBLIN, "hG"
    0x46: "bard",         # BARD (OBJNR_BARD, dormant)
    0x47: "hideous_troll",  # TROLL (OBJNR_HIDEOUSTROLL, "hT")
    0x48: "vicious_troll",  # TROLL (OBJNR_VICIOUSTROLL, "vT")
    0x49: "horrible_goblin", # OBJNR_HORRIBLEGOBLIN, "oG"
    0x4A: "mean_goblin",  # OBJNR_MEANGOBLIN, "mG"
    0x4B: "vicious_goblin", # OBJNR_VICIOUSGOBLIN, "vG"
    0x4C: "disgusting_goblin", # OBJNR_DISGUSTINGGOBLIN, "dG"
}

# --- §3. Scripts/tables $28CC (753 o) -----------------------------------
# Taille = nombre d'entrees [cle,lo,hi] * 3 + 1 (octet $FF terminal).
INDIR_TABLES: list[tuple[int, int]] = [
    (0x28CC, 7), (0x28D3, 7), (0x28DA, 7), (0x2943, 25), (0x2984, 10),
    (0x29B2, 10), (0x29C3, 4), (0x29E4, 10), (0x2A2E, 10), (0x2A4D, 7),
    (0x2A70, 7), (0x2A88, 7), (0x2AC9, 7),
]
EVENTS_BASE, EVENTS_N, EVENTS_SIZE = 0x2B12, 10, 5
EVENTS_FIELD = ["id", "cpt", "actA", "cond", "actB"]
# id/actA/cond/actB = configuration (immuable) ; seul cpt est le compteur
# mutable (evt_tick : cpt--, armement cpt:=id).
EVENTS_KIND = [CONST, VAR, CONST, CONST, CONST]
ENTITIES_BASE, ENTITIES_N, ENTITIES_SIZE = 0x2B45, 17, 7
# [id, nmax, PClo, PChi, balo, bahi, reply] ; voir entity_tick ($4ED5).
ENTITIES_FIELD = ["id", "nmax", "PClo", "PChi", "balo", "bahi", "reply"]
# id (reveil dormant) et PC (errance VM) = variables ; nmax/base/reply =
# configuration fixe (jamais ecrits ; doc §6).
ENTITIES_KIND = [VAR, CONST, VAR, VAR, CONST, CONST, CONST]


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
    "b0": (0, VAR, "flags : bit6=visite (pose au LOOK), bit7=visible/examinable (act_p14_14 : clair -> IT IS DARK), bits1-3 (&$0E)=index template $2110"),
    "b1": (1, CONST, "flags : bit6=inclusion dans la recherche (immuable)"),
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
            ident = STATE_IDENTITY.get(key, f"state${key:02X}")
            n = _img(_KEY_BASE[key])
            vl = _STATE_FIELD_LEN + n  # debut de la liste des verbes autorises
            if d >= vl:
                if _img(addr) == 0xFF:
                    nm, kind, doc = "vlend", CONST, "fin liste verbes autorises"
                else:
                    i = (d - vl) // 2
                    if (d - vl) % 2 == 0:
                        nm, kind, doc = (f"verb{i}", GABARIT,
                                         "verbe autorise (0 = action enchaine ; verb_obj_ok $52FB)")
                    else:
                        nm, kind, doc = (f"act{i}", GABARIT,
                                         "action du verbe (index table $7014/$7114)")
                out.append(Slot("etats", f"{ident}.{nm}", kind,
                                f"cle ${key:02X}, +${d:02X} : {doc}", addr))
            else:
                sp = STATE_SPECIAL.get((key, d))
                fld = sp or STATE_FIELD.get(d)
                if fld:
                    nm, kind, doc = fld
                else:
                    nm, kind, doc = f"+${d:02X}", UNKNOWN, "offset de bloc"
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
                            "entite VM [id,nmax,PC,base,reply]", addr))
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

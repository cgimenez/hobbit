#!/usr/bin/env python3
"""Construit l'image sim65 du jeu : hobbit.bin + shims + patchs.

- Assemble src/6502/shim.s (ca65+ld65, cale a $C000).
- Assemble src/6502/tape.s (stubs cassette B1, cales a $F700).
- Patch : JMP $C000 sur $7353 (scan clavier VIA -> shim paravirt),
  JMP stubs sur les 6 vecteurs bloc 1 $0405-$0414 (ROM 1.0 morte sous
  sim65 ; $0417 = loader jeu conserve, cf. src/6502/tape.s).
- Packe au format sim65 (header + load $0400 + reset $2C00 + SPAddr $02).

Artefacts dans build/sim/ (regenerables, gitignore). Sortie 0 si OK.

Usage : .venv/bin/python scripts/sim_pack.py [--hires] [--fast]
                                             [--tape FILE] [--solver]
           --hires : active aussi le dump de l'ecran hires ($A000-$BFFF).
           --fast : force $56=0 au boot (pas d'illustrations vectorielles ;
             img_show devient no-op -> avance rapide texte seul).
             Sortie build/sim/hobbit_fast.sim (le .sim stock est inchange).
           --tape FILE : pre-remplit le buffer cassette $E804+ avec FILE
             (save produite par scripts/tape_save.py) ; RD/WR inits.
             Combine avec --fast (sortie build/sim/hobbit_fast.sim).
          --snapshot NOM : image checkpoint (sortie build/sim/NOM.sim) :
            assemble src/6502/snap.s AU LIEU de tape.s (slot $F700),
            patch vec_02/03/04 ($2C0B/$2C0E/$2C11) vers snap_load/
            snap_save/s_clc (bypass couche octet), bake NOM en $F700+19,
            embarque sav/NOM.bin (ou --snap-file F) en $E800 ("SNAP"+3623).
            Implique --fast ($56=0). Incompatible avec --tape.
           --snap-file F : blob snapshot explicite (defaut : sav/NOM.bin).
           --solver : variante capture ASCII (shim -D SOLVER, hooks L75B8/
             L7694, pas de dumps @@FRAME/@@MEM) pour scripts/solver*.py
             ET play.sh. Se combine avec --snapshot (ex. --snapshot SLVW
             --solver) ; seul, produit l'image FROIDE solveur
             (build/sim/hobbit_solver.sim : boot $2C00, pas de snapshot,
             stubs cassette B1 comme les images classiques). Implique
             --fast ($56=0, texte seul). Patche aussi pause_key : le
             `JSR get_key` de la pause de lecture ($7628) est neutralise
             (LDA #$00) pour qu'elle n'absorbe plus un octet du flux
             clavier pre-injecte (cf. journal, "touche sacrifiee") ; les
             images classiques ne sont pas touchees.
"""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import BASE, BIN, CA65, LD65, ROOT  # noqa: E402

SHIM_SRC = ROOT / "src" / "6502" / "shim.s"
SHIM_CFG = ROOT / "src" / "6502" / "shim.cfg"
SHIM_ADDR = 0xC000  # zone "ROM" : le jeu n'y ecrit jamais (ROM sur Oric)
KB_SCAN = 0x7353  # scan clavier VIA -> remplace par JMP shim
# Hooks ASCII (variante --solver) : L75B8 (plot, `stx L75E0`), L7694
# (scroll/CR mode texte, `pha`) et L7514 (scroll/CR mode RAW = echo ligne de
# commande, `pha`) -> JMP shims (verifies sur data/hobbit.bin).
PLOT_ADDR, PLOT_WANT = 0x75B8, bytes((0x8E, 0xE0, 0x75))
EOL_ADDR, EOL_WANT = 0x7694, bytes((0x48, 0xA9, 0x00))
EOL2_ADDR, EOL2_WANT = 0x7514, bytes((0x48, 0xA9, 0x00))
PLOT_BACK, EOL_BACK, EOL2_BACK = 0x75BE, 0x7697, 0x7517  # reprises (shim.s)
TAPE_SRC = ROOT / "src" / "6502" / "tape.s"
TAPE_CFG = ROOT / "src" / "6502" / "tape.cfg"
TAPE_ADDR = 0xF700  # stubs cassette B1 (zone ROM, cf. tape.s)
TAPE_VECS = (0x0405, 0x0408, 0x040B, 0x040E, 0x0411, 0x0414)
# ($0417 n'est pas un vecteur : loader jeu conserve ; cf. src/6502/tape.s)
TAPE_RD, TAPE_WR, TAPE_DATA, TAPE_END = 0xE800, 0xE802, 0xE804, 0xF700
TAPE_CAP = TAPE_END - TAPE_DATA  # 3820 o utiles
# Bypass snapshots : vec_02/03/04 -> snap_load/snap_save/s_clc.
VEC02, VEC02_WANT = 0x2C0B, 0x71DB  # JMP tape_load (mesure image)
VEC03, VEC03_WANT = 0x2C0E, 0x7215  # JMP tape_save
VEC04, VEC04_WANT = 0x2C11, 0x71CB  # JMP L71CB (verify)
SNAP_SRC = ROOT / "src" / "6502" / "snap.s"
SNAP_CFG = ROOT / "src" / "6502" / "snap.cfg"
SNAP_ADDR = 0xF700  # meme slot que tape.s (remplace en mode --snapshot)
SNAP_BLOB = 0xE800  # "SNAP" + 3623 o (sim_pack --snapshot)
SNAP_LEN = 4 + 0x0018 + 0x0556 + 0x02F1 + 0x05C8  # 3627 o
SNAP_NAMELEN_OFF = SNAP_ADDR + 18
SNAP_NAME_OFF = SNAP_ADDR + 19
SNAP_NAME_MAX = 15
SAV_DIR = ROOT / "sav"
HIBIT_ADDR = 0xC2F2
TXTSH, TXTSH_END = 0xC300, 0xC300 + 0x460
VARS, VARS_END = 0xC2F0, 0xC300
# Charset ROM 1.0 (font lue en ($0403) = $FC70 ; limite runtime $FFC0).
ROM10 = ROOT / "data" / "basic10.rom"
FONT_LO, FONT_HI = 0xFC70, 0xFFC0

BUILD = ROOT / "build" / "sim"
OBJ = BUILD / "hobbit_shim.o"
SHIM_BIN = BUILD / "hobbit_shim.bin"
TAPE_OBJ = BUILD / "hobbit_tape.o"
TAPE_BIN = BUILD / "hobbit_tape.bin"
OUT = BUILD / "hobbit.sim"
FAST_OUT = BUILD / "hobbit_fast.sim"
# start: LDX #$FF / TXS / BNE L2C49 ($56=1 force) ; L2C49 = LDA #$01.
# Forcer $56=0 (pas d'images) = patcher l'immediat $2C4A ($01 -> $00).
NOIMG_ADDR, NOIMG_WANT = 0x2C4A, 0x01
# Pause de lecture (pause_key, $7620-) : tous les 16 CR, `JSR $7353` (get_key)
# detecte une touche et, si presente, la consomme (BMI $7640). Avec un flux
# clavier pre-injecte (solver/play.sh), cette pause absorbe le 1er caractere
# de la commande suivante (cf. journal : "touche sacrifiee"). En mode
# --solver on remplace le JSR par `LDA #$00` (A=0 = aucune touche, 3 octets) :
# la pause ne consomme plus rien, elle se contente de son delai (la branche
# BMI $7640 devient inatteignable). Comme un joueur qui ne presse pas.
PAUSE_CONSUME, PAUSE_WANT = 0x7628, bytes((0x20, 0x53, 0x73))
PAUSE_PATCH = bytes((0xA9, 0x00, 0xEA))  # LDA #$00 ; NOP


def main() -> int:
    hires = "--hires" in sys.argv
    fast = "--fast" in sys.argv
    solver = "--solver" in sys.argv
    tape_file = None
    if "--tape" in sys.argv:
        i = sys.argv.index("--tape")
        if i + 1 >= len(sys.argv):
            print("--tape exige un fichier")
            return 1
        tape_file = Path(sys.argv[i + 1])
        if not tape_file.is_file():
            print(f"fichier tape introuvable : {tape_file}")
            return 1
    snap_name = None
    if "--snapshot" in sys.argv:
        i = sys.argv.index("--snapshot")
        if i + 1 >= len(sys.argv):
            print("--snapshot exige un nom")
            return 1
        snap_name = sys.argv[i + 1]
        if not (1 <= len(snap_name) <= SNAP_NAME_MAX) or any(
                c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                         "abcdefghijklmnopqrstuvwxyz0123456789_-."
                for c in snap_name) or snap_name in (".", ".."):
            print(f"nom snapshot invalide : {snap_name!r} "
                  f"(1-{SNAP_NAME_MAX} car. [A-Za-z0-9_-.])")
            return 1
        fast = True  # checkpoints = jeu texte, toujours sans images
    if solver:
        fast = True  # solveur = capture texte seule, jamais d'images
    snap_file = None
    if "--snap-file" in sys.argv:
        i = sys.argv.index("--snap-file")
        if i + 1 >= len(sys.argv):
            print("--snap-file exige un fichier")
            return 1
        snap_file = Path(sys.argv[i + 1])
        if not snap_file.is_file():
            print(f"fichier snapshot introuvable : {snap_file}")
            return 1
    if snap_name is not None and tape_file is not None:
        print("--snapshot et --tape sont incompatibles (zone $E800 partagee)")
        return 1
    if solver and hires:
        print("--solver et --hires sont incompatibles (pas de dumps en solver)")
        return 1
    if snap_file is not None and snap_name is None:
        print("--snap-file exige --snapshot NOM")
        return 1
    if snap_name is not None and snap_file is None:
        snap_file = SAV_DIR / f"{snap_name}.bin"
        if not snap_file.is_file():
            print(f"snapshot introuvable : {snap_file} "
                  f"(jouer SAVE d'abord, ou --snap-file F)")
            return 1
    if snap_name is not None:
        out = BUILD / f"{snap_name}.sim"
    elif solver:
        out = BUILD / "hobbit_solver.sim"  # froid solveur (pas de snapshot)
    else:
        out = FAST_OUT if fast else OUT
    BUILD.mkdir(parents=True, exist_ok=True)
    for tool in (CA65, LD65):
        if not Path(tool).is_file():
            print(f"{tool} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
            return 1
    SHIM_LST = BUILD / "hobbit_shim.lst"
    ca65_flags = ["-D", "SOLVER"] if solver else []
    subprocess.run([str(CA65), *ca65_flags, "-l", str(SHIM_LST),
                    "-o", str(OBJ), str(SHIM_SRC)], check=True)
    subprocess.run([str(LD65), "-C", str(SHIM_CFG), "-o", str(SHIM_BIN), str(OBJ)], check=True)
    shim = SHIM_BIN.read_bytes()
    if len(shim) > 0x2F0:
        print(f"shim trop gros : {len(shim)} > 752 octets")
        return 1
    hook_addrs: dict[str, int] = {}
    if solver:
        import re as _re
        for line in SHIM_LST.read_text().splitlines():
            m = _re.match(r"^([0-9A-F]{6})r\s+1\s+(asc_plot|asc_eol|asc_eol2):$", line)
            if m:
                hook_addrs[m.group(2)] = SHIM_ADDR + int(m.group(1), 16)
        if set(hook_addrs) != {"asc_plot", "asc_eol", "asc_eol2"}:
            print(f"hooks introuvables dans {SHIM_LST}")
            return 1
        print(f"hooks solver : "
              + " ".join(f"{k}=${v:04X}" for k, v in hook_addrs.items()))
    import struct as _st
    if snap_name is not None:
        SNAP_OBJ = BUILD / "hobbit_snap.o"
        SNAP_BIN = BUILD / "hobbit_snap.bin"
        subprocess.run([str(CA65), "-o", str(SNAP_OBJ), str(SNAP_SRC)], check=True)
        subprocess.run([str(LD65), "-C", str(SNAP_CFG), "-o", str(SNAP_BIN), str(SNAP_OBJ)], check=True)
        snap = SNAP_BIN.read_bytes()
        if len(snap) > 0x500:
            print(f"shims snap trop gros : {len(snap)} > 1280 octets")
            return 1
        entries = _st.unpack("<9H", snap[:18])
        if entries[0] < SNAP_ADDR or max(entries) >= 0xFC00:
            print(f"table snap hors zone : {[f'{a:04X}' for a in entries]}")
            return 1
        _, _, _, _, _, _, e_save, e_load, e_clc = entries
    else:
        subprocess.run([str(CA65), "-o", str(TAPE_OBJ), str(TAPE_SRC)], check=True)
        subprocess.run([str(LD65), "-C", str(TAPE_CFG), "-o", str(TAPE_BIN), str(TAPE_OBJ)], check=True)
        tape = TAPE_BIN.read_bytes()
        if len(tape) > 0x500:
            print(f"stubs tape trop gros : {len(tape)} > 1280 octets")
            return 1
        entries = _st.unpack("<6H", tape[:12])
        if entries[0] < TAPE_ADDR or max(entries) >= 0xFC00:
            print(f"table tape hors zone : {[f'{a:04X}' for a in entries]}")
            return 1

    img = bytearray(BIN.read_bytes())
    # Patch clavier : $7353 (STX $1E / STY $1F) -> JMP shim.
    kb_off = KB_SCAN - BASE
    jmp = bytes((0x4C, SHIM_ADDR & 0xFF, SHIM_ADDR >> 8))
    print(f"patch ${KB_SCAN:04X} : "
          f"{' '.join(f'{b:02X}' for b in img[kb_off:kb_off + 3])} -> {' '.join(f'{b:02X}' for b in jmp)}")
    img[kb_off:kb_off + 3] = jmp
    if solver:
        # Hooks ASCII : verifie les octets d'origine puis JMP shims.
        for addr, want, name in ((PLOT_ADDR, PLOT_WANT, "asc_plot"),
                                 (EOL_ADDR, EOL_WANT, "asc_eol"),
                                 (EOL2_ADDR, EOL2_WANT, "asc_eol2")):
            off = addr - BASE
            if bytes(img[off:off + 3]) != want:
                print(f"refus hook {name} : ${addr:04X} = "
                      f"{' '.join(f'{b:02X}' for b in img[off:off + 3])} "
                      f"(attendu {' '.join(f'{b:02X}' for b in want)})")
                return 1
            hook = hook_addrs[name]
            img[off:off + 3] = bytes((0x4C, hook & 0xFF, hook >> 8))
            print(f"hook {name} : ${addr:04X} -> JMP ${hook:04X}")
        # Pause de lecture : ne consomme plus d'octet scripte (cf. ci-dessus).
        off = PAUSE_CONSUME - BASE
        if bytes(img[off:off + 3]) != PAUSE_WANT:
            print(f"refus patch pause : ${PAUSE_CONSUME:04X} = "
                  f"{' '.join(f'{b:02X}' for b in img[off:off + 3])} "
                  f"(attendu {' '.join(f'{b:02X}' for b in PAUSE_WANT)})")
            return 1
        img[off:off + 3] = PAUSE_PATCH
        print(f"patch pause ${PAUSE_CONSUME:04X} : "
              f"{' '.join(f'{b:02X}' for b in PAUSE_WANT)} -> "
              f"{' '.join(f'{b:02X}' for b in PAUSE_PATCH)} "
              f"(pause sans consommation)")
    # Patch cassette : $0405-$0417 -> JMP stubs B1 (table en $F700).
    for vec, stub in zip(TAPE_VECS, entries):
        off = vec - BASE
        old = bytes(img[off:off + 3])
        new = bytes((0x4C, stub & 0xFF, stub >> 8))
        print(f"patch ${vec:04X} : "
              f"{' '.join(f'{b:02X}' for b in old)} -> {' '.join(f'{b:02X}' for b in new)}")
        img[off:off + 3] = new
    if fast:
        off = NOIMG_ADDR - BASE
        if img[off] != NOIMG_WANT:
            print(f"refus patch --fast : ${NOIMG_ADDR:04X} = {img[off]:02X} (attendu {NOIMG_WANT:02X})")
            return 1
        img[off] = 0x00
        print(f"patch --fast ${NOIMG_ADDR:04X} : 01 -> 00 ($56=0, sans images)")
    # Colle le shim (zero-fill jusqu'a SHIM_ADDR).
    if len(img) < SHIM_ADDR - BASE:
        img += bytes(SHIM_ADDR - BASE - len(img))
    img[SHIM_ADDR - BASE:SHIM_ADDR - BASE + len(shim)] = shim
    # Colle les stubs ($F700 : tape.s ou snap.s selon le mode).
    lowcode = snap if snap_name is not None else tape
    lowname = "snap" if snap_name is not None else "tape"
    if len(img) < TAPE_ADDR + len(lowcode) - BASE:
        img += bytes(TAPE_ADDR + len(lowcode) - BASE - len(img))
    img[TAPE_ADDR - BASE:TAPE_ADDR - BASE + len(lowcode)] = lowcode
    print(f"{lowname} : {len(lowcode)} o @ ${TAPE_ADDR:04X} "
          f"({' '.join(f'{a:04X}' for a in entries)})")
    if snap_name is not None:
        # Bypass SAVE/LOAD : vec_02/03/04 -> snap_load/save/s_clc.
        for vec, want, new in ((VEC02, VEC02_WANT, e_load),
                               (VEC03, VEC03_WANT, e_save),
                               (VEC04, VEC04_WANT, e_clc)):
            off = vec - BASE
            op, lo, hi = img[off], img[off + 1], img[off + 2]
            if op != 0x4C or (lo | (hi << 8)) != want:
                print(f"refus patch ${vec:04X} : JMP ${lo | (hi << 8):04X} "
                      f"(attendu ${want:04X})")
                return 1
            img[off + 1:off + 3] = bytes((new & 0xFF, new >> 8))
            print(f"patch ${vec:04X} : JMP ${want:04X} -> JMP ${new:04X}")
        # Blob snapshot en $E800 ("SNAP" + 3623 o, magique verifie).
        blob = snap_file.read_bytes()
        if len(blob) != SNAP_LEN or blob[:4] != b"SNAP":
            print(f"snapshot invalide : {snap_file} "
                  f"({len(blob)} o, magique {blob[:4]!r}, "
                  f"attendu 3627 o + 'SNAP')")
            return 1
        if len(img) < SNAP_BLOB + len(blob) - BASE:
            img += bytes(SNAP_BLOB + len(blob) - BASE - len(img))
        img[SNAP_BLOB - BASE:SNAP_BLOB - BASE + len(blob)] = blob
        print(f"snapshot embarque : {snap_file} "
              f"({len(blob)} o @ ${SNAP_BLOB:04X})")
        # Bake du nom en $F700+18/+19 (SNAP_NAMELEN/SNAP_NAME).
        nb = snap_name.encode("ascii")
        img[SNAP_NAMELEN_OFF - BASE] = len(nb)
        img[SNAP_NAME_OFF - BASE:SNAP_NAME_OFF + 16 - BASE] = \
            nb + bytes(16 - len(nb))
        print(f"snapshot nom : {snap_name!r}")
    else:
        # Buffer cassette $E800 : RD/WR := $E804 (+ pre-remplissage --tape).
        if len(img) < TAPE_WR + 2 - BASE:
            img += bytes(TAPE_WR + 2 - BASE - len(img))
        img[TAPE_RD - BASE:TAPE_RD - BASE + 2] = TAPE_DATA.to_bytes(2, "little")
        wr = TAPE_DATA
        if tape_file is not None:
            blob = tape_file.read_bytes()
            if len(blob) > TAPE_CAP:
                print(f"tape trop grosse : {len(blob)} > {TAPE_CAP} octets")
                return 1
            if len(img) < TAPE_DATA + len(blob) - BASE:
                img += bytes(TAPE_DATA + len(blob) - BASE - len(img))
            img[TAPE_DATA - BASE:TAPE_DATA - BASE + len(blob)] = blob
            wr = TAPE_DATA + len(blob)
            print(f"tape pre-remplie : {tape_file} ({len(blob)} o)")
        img[TAPE_WR - BASE:TAPE_WR - BASE + 2] = wr.to_bytes(2, "little")
    # Charset ROM 1.0 a son adresse (font lue en ($0403) = $FC70).
    rom = ROM10.read_bytes()
    if len(img) < FONT_HI - BASE:
        img += bytes(FONT_HI - BASE - len(img))
    img[FONT_LO - BASE:FONT_HI - BASE] = rom[FONT_LO - 0xC000:FONT_HI - 0xC000]
    # Etat initial du shim (sim65 remplit la RAM de $FF : tout expliciter).
    # Vars $C2F0-$C2FF a zero (KBSTATE=0 = attente d'octet), HIBIT selon
    # option, miroir texte $C300-$C75F a $FF (== ecran vierge sous sim65
    # -> pas de dump fantome au 1er appel).
    if len(img) < VARS_END - BASE:
        img += bytes(VARS_END - BASE - len(img))
    img[VARS - BASE:VARS_END - BASE] = bytes(VARS_END - VARS)
    img[HIBIT_ADDR - BASE] = 1 if hires else 0
    if len(img) < TXTSH_END - BASE:
        img += bytes(TXTSH_END - BASE - len(img))
    img[TXTSH - BASE:TXTSH_END - BASE] = bytes([0xFF]) * (TXTSH_END - TXTSH)
    print(f"font : ROM 1.0 ${FONT_LO:04X}-${FONT_HI - 1:04X} "
          f"({FONT_HI - FONT_LO} o)")

    hdr = b"sim65" + bytes((2, 0, 0x02)) + struct.pack("<HH", 0x0400, 0x2C00)
    out.write_bytes(hdr + bytes(img))
    end = 0x0400 + len(img) - 1
    print(f"pack : {out}, image $0400-${end:04X} "
          f"({len(img)} o), reset $2C00, shim {len(shim)} o @ ${SHIM_ADDR:04X}"
          f", {lowname} {len(lowcode)} o @ ${TAPE_ADDR:04X}"
          + (", hires ON" if hires else "")
          + (", $56=0 (fast)" if fast else "")
          + (f", --tape {tape_file}" if tape_file is not None else "")
           + (f", --snapshot {snap_name}" if snap_name is not None else "")
           + (", --solver froid" if solver and snap_name is None else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

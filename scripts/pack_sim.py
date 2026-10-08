#!/usr/bin/env python3
"""Construit l'image sim65 du jeu : hobbit.bin + shims + patchs.

- Assemble harness/shim.s (ca65+ld65, cale a $C000).
- Assemble harness/tape.s (stubs cassette B1, cales a $F700).
- Patch : JMP $C000 sur $7353 (scan clavier VIA -> shim paravirt),
  JMP stubs sur $0405-$0417 (bloc 1 cassette, ROM 1.0 morte sous sim65).
- Packe au format sim65 (header + load $0400 + reset $2C00 + SPAddr $02).

Artefacts dans build/sim/ (regenerables, gitignore). Sortie 0 si OK.

Usage : .venv/bin/python scripts/pack_sim.py [--hires] [--fast]
                                             [--tape FILE]
          --hires : active aussi le dump de l'ecran hires ($A000-$BFFF).
          --fast : force $56=0 au boot (pas d'illustrations vectorielles ;
            img_show devient no-op -> avance rapide texte seul).
            Sortie build/sim/hobbit_fast.sim (le .sim stock est inchange).
          --tape FILE : pre-remplit le buffer cassette $E804+ avec FILE
            (save produite par scripts/save_tape.py) ; RD/WR inits.
            Combine avec --fast (sortie build/sim/hobbit_fast.sim).
"""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import BASE, BIN, CA65, LD65, ROOT  # noqa: E402

SHIM_SRC = ROOT / "harness" / "shim.s"
SHIM_CFG = ROOT / "harness" / "shim.cfg"
SHIM_ADDR = 0xC000  # zone "ROM" : le jeu n'y ecrit jamais (ROM sur Oric)
KB_SCAN = 0x7353  # scan clavier VIA -> remplace par JMP shim
TAPE_SRC = ROOT / "harness" / "tape.s"
TAPE_CFG = ROOT / "harness" / "tape.cfg"
TAPE_ADDR = 0xF700  # stubs cassette B1 (zone ROM, cf. tape.s)
TAPE_VECS = (0x0405, 0x0408, 0x040B, 0x040E, 0x0411, 0x0414, 0x0417)
TAPE_RD, TAPE_WR, TAPE_DATA, TAPE_END = 0xE800, 0xE802, 0xE804, 0xF700
TAPE_CAP = TAPE_END - TAPE_DATA  # 3820 o utiles
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


def main() -> int:
    hires = "--hires" in sys.argv
    fast = "--fast" in sys.argv
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
    out = FAST_OUT if fast else OUT
    BUILD.mkdir(parents=True, exist_ok=True)
    for tool in (CA65, LD65):
        if not Path(tool).is_file():
            print(f"{tool} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
            return 1
    subprocess.run([str(CA65), "-o", str(OBJ), str(SHIM_SRC)], check=True)
    subprocess.run([str(LD65), "-C", str(SHIM_CFG), "-o", str(SHIM_BIN), str(OBJ)], check=True)
    shim = SHIM_BIN.read_bytes()
    if len(shim) > 0x2F0:
        print(f"shim trop gros : {len(shim)} > 752 octets")
        return 1
    subprocess.run([str(CA65), "-o", str(TAPE_OBJ), str(TAPE_SRC)], check=True)
    subprocess.run([str(LD65), "-C", str(TAPE_CFG), "-o", str(TAPE_BIN), str(TAPE_OBJ)], check=True)
    tape = TAPE_BIN.read_bytes()
    if len(tape) > 0x500:
        print(f"stubs tape trop gros : {len(tape)} > 1280 octets")
        return 1
    import struct as _st
    entries = _st.unpack("<7H", tape[:14])
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
    # Colle les stubs cassette B1 en $F700.
    if len(img) < TAPE_ADDR + len(tape) - BASE:
        img += bytes(TAPE_ADDR + len(tape) - BASE - len(img))
    img[TAPE_ADDR - BASE:TAPE_ADDR - BASE + len(tape)] = tape
    print(f"tape : {len(tape)} o @ ${TAPE_ADDR:04X} "
          f"({' '.join(f'{a:04X}' for a in entries)})")
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
          f", tape {len(tape)} o @ ${TAPE_ADDR:04X}"
          + (", hires ON" if hires else "")
          + (", $56=0 (fast)" if fast else "")
          + (f", --tape {tape_file}" if tape_file is not None else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Construit l'image sim65 du jeu : hobbit.bin + shims + patchs.

- Assemble harness/shim.s (ca65+ld65, cale a $9200).
- Patch : JMP $9200 sur $7353 (scan clavier VIA -> shim paravirt).
- Packe au format sim65 (header + load $0400 + reset $2C00 + SPAddr $02).

Artefacts dans /tmp (regenerables). Sortie 0 si OK.

Usage : .venv/bin/python scripts/pack_sim.py [--hires]
         --hires : active aussi le dump de l'ecran hires ($A000-$BFFF).
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
HIBIT_ADDR = 0xC202
TXTSH, TXTSH_END = 0xC300, 0xC300 + 0x460
VARS, VARS_END = 0xC200, 0xC210
# Charset ROM 1.0 (font lue en ($0403) = $FC70 ; limite runtime $FFC0).
ROM10 = ROOT / "data" / "basic10.rom"
FONT_LO, FONT_HI = 0xFC70, 0xFFC0

OBJ = Path("/tmp/hobbit_shim.o")
SHIM_BIN = Path("/tmp/hobbit_shim.bin")
OUT = Path("/tmp/hobbit.sim")


def main() -> int:
    hires = "--hires" in sys.argv
    for tool in (CA65, LD65):
        if not Path(tool).is_file():
            print(f"{tool} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
            return 1
    subprocess.run([str(CA65), "-o", str(OBJ), str(SHIM_SRC)], check=True)
    subprocess.run([str(LD65), "-C", str(SHIM_CFG), "-o", str(SHIM_BIN), str(OBJ)], check=True)
    shim = SHIM_BIN.read_bytes()
    if len(shim) > 0x200:
        print(f"shim trop gros : {len(shim)} > 512 octets")
        return 1

    img = bytearray(BIN.read_bytes())
    # Patch clavier : $7353 (STX $1E / STY $1F) -> JMP shim.
    kb_off = KB_SCAN - BASE
    jmp = bytes((0x4C, SHIM_ADDR & 0xFF, SHIM_ADDR >> 8))
    print(f"patch ${KB_SCAN:04X} : "
          f"{' '.join(f'{b:02X}' for b in img[kb_off:kb_off + 3])} -> {' '.join(f'{b:02X}' for b in jmp)}")
    img[kb_off:kb_off + 3] = jmp
    # Colle le shim (zero-fill jusqu'a SHIM_ADDR).
    if len(img) < SHIM_ADDR - BASE:
        img += bytes(SHIM_ADDR - BASE - len(img))
    img[SHIM_ADDR - BASE:SHIM_ADDR - BASE + len(shim)] = shim
    # Charset ROM 1.0 a son adresse (font lue en ($0403) = $FC70).
    rom = ROM10.read_bytes()
    if len(img) < FONT_HI - BASE:
        img += bytes(FONT_HI - BASE - len(img))
    img[FONT_LO - BASE:FONT_HI - BASE] = rom[FONT_LO - 0xC000:FONT_HI - 0xC000]
    # Etat initial du shim (sim65 remplit la RAM de $FF : tout expliciter).
    # Vars $C200-$C20F a zero (KBSTATE=0 = attente d'octet), HIBIT selon
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
    OUT.write_bytes(hdr + bytes(img))
    end = 0x0400 + len(img) - 1
    print(f"pack : /tmp/hobbit.sim, image $0400-${end:04X} "
          f"({len(img)} o), reset $2C00, shim {len(shim)} o @ ${SHIM_ADDR:04X}"
          + (", hires ON" if hires else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

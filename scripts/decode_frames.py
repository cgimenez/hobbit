#!/usr/bin/env python3
"""Décode les captures du harnais sim65 (marqueurs @@FRAME text/hires).

Rend chaque écran hires en texte via le charset ROM 1.0 ($FC70, cf.
scripts/pack_sim.py) : grille 8 px, 40 colonnes, ordre bit5-gauche.
N'affiche que les lignes non vides (tout avec --all). Les captures
tronquées (timeout sim65 en plein dump) sont signalées et ignorées.

Usage : .venv/bin/python scripts/decode_frames.py frames.bin [--all]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROM10 = ROOT / "data" / "basic10.rom"
FONT_BASE = 0xFC70


def load_font() -> dict[bytes, str]:
    rom = ROM10.read_bytes()
    off = FONT_BASE - 0xC000
    return {bytes(rom[off + ch * 8:off + ch * 8 + 8]): chr(ch + 0x20)
            for ch in range(96)}


def main() -> int:
    show_all = "--all" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: decode_frames.py frames.bin [--all]")
        return 1
    font = load_font()
    data = Path(args[0]).read_bytes()
    chunks = re.split(b"@@FRAME text\n", data)[1:]
    print(f"captures: {len(chunks)}")
    for n, ch in enumerate(chunks, 1):
        m = re.search(b"@@FRAME hires\n", ch)
        if not m or len(ch) < m.end() + 8192:
            print(f"===== capture {n} (hires partiel, ignoree) =====")
            continue
        h = ch[m.end():m.end() + 8192]
        print(f"===== capture {n} =====")
        for brow in range(0, 200, 8):
            line = ""
            for col in range(40):
                g = bytes(h[(brow + r) * 40 + col] & 0x3F for r in range(8))
                line += font.get(g, ".")
            if show_all or line.strip(". "):
                print(f"{brow:3d}: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

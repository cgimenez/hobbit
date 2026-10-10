#!/usr/bin/env python3
"""Décode les 13 illustrations vectorielles du bloc 3 -> SVG.

Charge data/hobbit.bin (base $0400), lit la table d'images $7AC0 (13 entrées
[clé,lo,hi], sentinelle $FF) et réplique le moteur bloc 4 (vec_setup, dispatch
d'opcodes, vec_pos/vec_line/vec_fill/vec_skip, vec_plot/vec_addr) pour
rasteriser chaque image dans un canvas 240x128 (le charset $B400 limite la
zone dessinable aux 128 premières lignes du hires Oric 240x200).

Couleurs : octet mode -> papier = mode & 7, encre = (mode >> 4) & 7
(attributs écrits en col 0/1 ; cf. vec_setup $7990). Palette Oric 8 couleurs.

Usage : .venv/bin/python scripts/vec_decode.py [--out DIR] [--mono]
        [--scale N]
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "data" / "hobbit.bin"
BASE = 0x0400
TBL = 0x7AC0

W, H = 240, 128
X_ORIGIN = 12  # le moteur écrit en $A002 : 2 colonnes d'attributs (paper/ink)
MASK = (0x20, 0x10, 0x08, 0x04, 0x02, 0x01)

ORIC = ("#000000", "#ff0000", "#00ff00", "#ffff00",
        "#0000ff", "#ff00ff", "#00ffff", "#ffffff")


class Canvas:
    """Bitmap 128x40 octets (6 px/octet), pixel = encre."""

    def __init__(self) -> None:
        self.buf = [[0] * 40 for _ in range(H)]

    def _loc(self, x: int, y: int):
        if x < 0x0E or x >= 0xF2 or y < 0 or y > 0x7F:
            return None
        px = x - 0x0E
        return 0x7F - y, px // 6, px % 6

    def testpx(self, x: int, y: int) -> int:
        loc = self._loc(x, y)
        if loc is None:
            return 0xFF
        r, c, b = loc
        return self.buf[r][c] & MASK[b]

    def plot(self, x: int, y: int) -> None:
        loc = self._loc(x, y)
        if loc is not None:
            r, c, b = loc
            self.buf[r][c] |= MASK[b]


def vec_line(cv: Canvas, x: int, y: int, op: int, b: int):
    """Segment : $2D = pas mineur, $2E (b & $3F) = longueur totale."""
    vert = op & 1
    yneg = op & 2
    xneg = op & 4
    minor = (((op & 0x78) >> 1) | (((b >> 7) & 1) << 1) | ((b >> 6) & 1)) + 1
    total = b & 0x3F
    m = minor
    while True:
        cv.plot(x, y)
        if vert == 0:
            if xneg == 0:
                x = (x + 1) & 0xFF
                if x == 0:
                    return (x - 1) & 0xFF, y
            else:
                x = (x - 1) & 0xFF
                if x == 0xFF:
                    return (x + 1) & 0xFF, y
        else:
            if yneg == 0:
                y += 1
                if y >= 0x80:
                    return x, y - 1
            else:
                y -= 1
                if y < 0:
                    return x, y + 1
        m -= 1
        if m == 0:
            m = minor
            if vert == 0:
                if yneg == 0:
                    y += 1
                    if y >= 0x80:
                        return x, y - 1
                else:
                    y -= 1
                    if y < 0:
                        return x, y + 1
            else:
                if xneg == 0:
                    x = (x + 1) & 0xFF
                    if x == 0:
                        return (x - 1) & 0xFF, y
                else:
                    x = (x - 1) & 0xFF
                    if x == 0xFF:
                        return (x + 1) & 0xFF, y
        total -= 1
        if total < 0:
            return x, y


def vec_fill(cv: Canvas, x: int, y: int):
    """Remplissage par spans (seed-fill), réplique de $783F-$78C0."""
    stack: list[tuple[int, int]] = []
    while True:
        if cv.testpx(x, y) == 0:
            while x != 0 and cv.testpx(x, y) == 0:
                x -= 1
            if cv.testpx(x, y) != 0:
                x += 1
        below = above = False
        while True:
            cv.plot(x, y)
            if y != 0x7F:
                y += 1
                if cv.testpx(x, y) == 0:
                    if not below:
                        stack.append((x, y))
                        below = True
                else:
                    below = False
                y -= 1
            if y != 0:
                y -= 1
                if cv.testpx(x, y) == 0:
                    if not above:
                        stack.append((x, y))
                        above = True
                else:
                    above = False
                y += 1
            x = (x + 1) & 0xFF
            if x == 0 or cv.testpx(x, y) != 0:
                break
        if not stack:
            return x, y
        x, y = stack.pop()


def decode(rom: bytes, addr: int) -> tuple[Canvas, int]:
    def rd(a: int) -> int:
        return rom[a - BASE]

    cv = Canvas()
    p = addr
    mode = rd(p)
    p += 1
    x = y = 0
    while True:
        op = rd(p)
        if op == 0:
            break
        if op == 0x08:
            p += 1
            x = rd(p)
            p += 1
            y = rd(p)
            p += 1
        elif op & 0x80:
            x, y = vec_line(cv, x, y, op, rd(p + 1))
            p += 2
        elif op & 0x40:
            p += 1
            x = rd(p)
            p += 1
            y = rd(p)
            p += 1
            x, y = vec_fill(cv, x, y)
        elif op & 0x20:
            p += 1
            while rd(p) != 0xFF:
                p += 1
            p += 1
        else:
            p += 1
    return cv, mode


def runs(cv: Canvas):
    """Itère (row, x0, x1) des runs horizontaux de pixels allumés.

    Le bitmap interne est indexé en colonnes mémoire (0..39, base $A002) ;
    le rendu décale de X_ORIGIN (2 colonnes d'attributs paper/ink à gauche).
    """
    for r in range(H):
        c = 0
        while c < 40:
            byte = cv.buf[r][c]
            if not byte:
                c += 1
                continue
            start = None
            x0 = X_ORIGIN + c * 6
            for b in range(6):
                if byte & MASK[b]:
                    if start is None:
                        start = x0 + b
                    last = x0 + b
                elif start is not None:
                    yield r, start, last
                    start = None
            if start is not None:
                yield r, start, last
            c += 1


def svg(cv: Canvas, paper: str, ink: str, scale: int) -> str:
    parts = []
    for r, x0, x1 in runs(cv):
        n = x1 - x0 + 1
        parts.append(f"M{x0} {r}h{n}v1h-{n}z")
    path = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W * scale}" height="{H * scale}" '
        f'viewBox="0 0 {W} {H}" shape-rendering="crispEdges">'
        f'<rect width="{W}" height="{H}" fill="{paper}"/>'
        f'<path d="{path}" fill="{ink}"/></svg>\n'
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs" / "vectors"))
    ap.add_argument("--mono", action="store_true",
                    help="noir sur blanc au lieu de la palette Oric")
    ap.add_argument("--scale", type=int, default=1)
    args = ap.parse_args()

    rom = BIN.read_bytes()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    entries = []
    i = 0
    while rom[TBL - BASE + i * 3] != 0xFF:
        key = rom[TBL - BASE + i * 3]
        addr = rom[TBL - BASE + i * 3 + 1] | (rom[TBL - BASE + i * 3 + 2] << 8)
        entries.append((key, addr))
        i += 1

    for key, addr in entries:
        cv, mode = decode(rom, addr)
        if args.mono:
            paper, ink = "#ffffff", "#000000"
        else:
            paper, ink = ORIC[mode & 7], ORIC[(mode >> 4) & 7]
        name = out / f"vec_{key:02x}.svg"
        name.write_text(svg(cv, paper, ink, args.scale))
        npx = sum(bin(b).count("1") for row in cv.buf for b in row)
        print(f"${key:02X} @ ${addr:04X} mode=${mode:02X} "
              f"papier={paper} encre={ink} px={npx} -> {name}")

    print(f"{len(entries)} images -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

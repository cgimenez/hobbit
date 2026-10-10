#!/usr/bin/env python3
"""Carte des lieux (The Hobbit, Oric 1982) -> docs/map.d2 + docs/map.svg.

Graphe statique via scripts/map_static.build_graph (78 lieux, sorties dirigees)
+ statut de visite (build/sim/{solver,hobbit}.db). Rendu D2 (theme default,
layout dagre). Annotations : direction, conditions, lieux patch-only, zones
sombres, sorties "vide/mort" ($00).

Usage : .venv/bin/python scripts/draw_map.py [--no-render]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_static as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D2 = ROOT / "docs" / "map.d2"
SVG = ROOT / "docs" / "map.svg"
SOLVER_DB = ROOT / "build" / "sim" / "solver.db"
HOBBIT_DB = ROOT / "build" / "sim" / "hobbit.db"

DIR_CODE = {1: "N", 2: "S", 3: "E", 4: "W", 5: "NE", 6: "NW", 7: "SE",
            8: "SW", 9: "UP", 10: "DOWN"}
PATCH_ONLY = {0x08, 0x14, 0x15, 0x1A, 0x1B, 0x1C, 0x1D, 0x32, 0x42, 0x43}
DARK = {0x1E, 0x1F, 0x20}


def visited() -> set[int]:
    """Ids de lieux observes (ploc) dans les deux bases d'exploration."""
    import sqlite3
    out: set[int] = set()
    for db, col, tab in ((SOLVER_DB, "ploc", "nodes"),
                         (HOBBIT_DB, "ploc", "state")):
        if not db.is_file():
            continue
        try:
            cx = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            out |= {r[0] for r in cx.execute(
                f"SELECT DISTINCT {col} FROM {tab}")}
            cx.close()
        except sqlite3.Error:
            pass
    return {v for v in out if 1 <= v <= 0x4F}


def esc(text: str) -> str:
    """Échappe pour D2 : '$' ouvre une substitution, on le neutralise."""
    return text.replace("$", "\\$")


def clean(desc: str) -> str:
    """Retire les marqueurs de décodage (<END>, <CR>, .<CR>) des libellés."""
    for tok in ("<END>", ".<CR>", "<CR>"):
        desc = desc.replace(tok, "")
    return desc.strip()


def node_label(i: int, g: dict) -> str:
    desc = clean(M.short_desc(g["desc"])).replace('"', "'").strip()
    if not desc or desc == "(sans desc propre)":
        desc = "(sans desc)"
    return esc(f"${i:02X}  {desc[:36]}")


def node_class(i: int, vis: set[int]) -> str:
    if i in PATCH_ONLY:
        return "patch"
    if i in DARK:
        return "sombre"
    if i in vis:
        return "visite"
    return "inconnu"


def edge_label(exits: list[tuple[int, int]]) -> str:
    parts = []
    for d, c in exits:
        code = DIR_CODE.get(d, "?%d" % d)
        parts.append(f"{code} [cond ${c:02X}]" if c else code)
    return esc("\\n".join(parts))


def build_d2(graph: dict, vis: set[int]) -> str:
    lines = [
        "# The Hobbit (Oric-1/Atmos 1982) - carte des lieux",
        "# GENERE par scripts/draw_map.py - NE PAS EDITER A LA MAIN.",
        "direction: right",
        "classes: {",
        '  visite: { style: { fill: "#e6f4ea"; stroke: "#2e7d32"; '
        'font-color: "#1b3a24" } }',
        '  patch:  { style: { fill: "#dbe7fb"; stroke: "#1565c0"; '
        'font-color: "#0d2b52"; stroke-dash: 4 } }',
        '  sombre: { style: { fill: "#eceff1"; stroke: "#546e7a"; '
        'font-color: "#263238" } }',
        '  inconnu: { style: { fill: "#ffffff"; stroke: "#9e9e9e"; '
        'font-color: "#616161" } }',
        '  vide:   { style: { fill: "#f5f5f5"; stroke: "#9e9e9e"; '
        'font-color: "#616161"; stroke-dash: 4 } }',
        "}",
        "",
    ]
    for i in sorted(graph):
        lines.append(f'p{i:02X}: "{node_label(i, graph[i])}" '
                     f"{{ class: {node_class(i, vis)} }}")
    lines.append('vide: "vide / mort\\n(cible \\$00)" '
                 "{ class: vide; shape: circle }")
    lines.append("")

    pairs: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for src in sorted(graph):
        for d, c, dst in graph[src]["exits"]:
            pairs.setdefault((src, dst), []).append((d, c))
    for (src, dst), exits in pairs.items():
        tgt = f"p{dst:02X}" if dst in graph else "vide"
        style = " { class: vide }" if dst not in graph else ""
        lines.append(f'p{src:02X} -> {tgt}: "{edge_label(exits)}"{style}')
    return "\n".join(lines) + "\n"


def main() -> int:
    graph, warns = M.build_graph()
    vis = visited()
    D2.write_text(build_d2(graph, vis))
    print(f"{D2.relative_to(ROOT)} : {len(graph)} lieux, "
          f"{sum(len(g['exits']) for g in graph.values())} sorties, "
          f"{len(vis & set(graph))} visites, {len(PATCH_ONLY)} patch-only")
    for w in warns:
        print("  avertissement:", w)
    if "--no-render" in sys.argv:
        return 0
    try:
        subprocess.run(["d2", str(D2), str(SVG)], check=True)
    except FileNotFoundError:
        print("  d2 absent : source .d2 ecrite, SVG non rendu")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"  echec rendu d2 (code {exc.returncode})")
        return 1
    print(f"{SVG.relative_to(ROOT)} : {SVG.stat().st_size} o")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

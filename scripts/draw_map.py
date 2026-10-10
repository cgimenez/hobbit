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

# 5 zones (sous-graphes) : regroupement geographique du monde.
ZONES = [
    ("z_ouest", "Ouest : tunnel & Trollshaws",
     {0x01, 0x04, 0x05, 0x06, 0x07, 0x09}),
    ("z_brumeux", "Monts Brumeux",
     {0x0A, 0x0B, 0x0C, 0x0E, 0x0F, 0x16, 0x18, 0x19, 0x42, 0x43, 0x32}),
    ("z_gobelins", "Cavernes gobelines (nord)",
     {0x0D, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x34, 0x35, 0x36, 0x37, 0x38,
      0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41}),
    ("z_foret", "Foret noire, Lac & Montagne solitaire",
     {0x02, 0x03, 0x08, 0x17, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x21,
      0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D,
      0x2E, 0x30, 0x31, 0x33}),
    ("z_ne", "Hauts du nord-est",
     {0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F}),
]
ZONE_OTHER = ("z_autres", "Autres")


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
    zone_of: dict[int, str] = {}
    zones = list(ZONES)
    for key, _title, ids in ZONES:
        for i in ids:
            zone_of[i] = key
    extra = sorted(set(graph) - set(zone_of))
    if extra:
        zones.append((ZONE_OTHER[0], ZONE_OTHER[1], set(extra)))
        for i in extra:
            zone_of[i] = ZONE_OTHER[0]

    lines = [
        "# The Hobbit (Oric-1/Atmos 1982) - carte des lieux par zones",
        "# GENERE par scripts/draw_map.py - NE PAS EDITER A LA MAIN.",
        "direction: down",
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
    for key, title, ids in zones:
        lines.append(f'{key}: "{title}" {{')
        lines.append("  direction: down")
        for i in sorted(ids):
            if i in graph:
                lines.append(f'  p{i:02X}: "{node_label(i, graph[i])}" '
                             f"{{ class: {node_class(i, vis)} }}")
        lines.append("}")
    lines.append('vide: "vide / mort\\n(cible \\$00)" '
                 "{ class: vide; shape: circle }")
    lines.append("")

    def ref(i: int) -> str:
        return f"{zone_of[i]}.p{i:02X}"

    pairs: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for src in sorted(graph):
        for d, c, dst in graph[src]["exits"]:
            pairs.setdefault((src, dst), []).append((d, c))
    for (src, dst), exits in pairs.items():
        tgt = ref(dst) if dst in graph else "vide"
        style = " { class: vide }" if dst not in graph else ""
        lines.append(f'{ref(src)} -> {tgt}: "{edge_label(exits)}"{style}')
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

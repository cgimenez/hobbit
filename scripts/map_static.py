#!/usr/bin/env python3
"""Graphe statique des lieux (The Hobbit, Oric) depuis data/hobbit.bin.

Record (via table $2070, id <$50) :
  [b0, b1, cond(6 o), desc_lo, desc_hi, (dir, cond, dest)*, $FF]
  dir = 1..10 (NORTH..DOWN, cf. $26DA), cond = cle d'etat $1A62
  ($00 = libre ; evaluee via L5331+8 dans cond_eval, voie direct=0),
  dest = id de record.

Sort le graphe complet + descriptions (1re ligne) + recoupement
des mouvements observes sous harnais (F1-F5).
Port minimaliste de /tmp/dict.py (word_render) + /tmp/msgdec.py.
"""

import sys

RAW = open("data/hobbit.bin", "rb").read()
BASE = 0x0400


def B(a):
    return RAW[a - BASE]


def W(a):
    return B(a) | (B(a + 1) << 8)


DIRS = {1: "NORTH", 2: "SOUTH", 3: "EAST", 4: "WEST", 5: "NORTHEAST",
        6: "NORTHWEST", 7: "SOUTHEAST", 8: "SOUTHWEST", 9: "UP",
        10: "DOWN"}  # mots $26DA+wid*8 verifies au word_render

SUF = bytes(RAW[0x4322 - BASE:0x4322 - BASE + 24])


def ch(c):
    return chr(ord("A") + c - 1) if 1 <= c <= 26 else "?%d?" % c


def word_render(lo, hib, obj=0, arg1=0):
    if (hib & 0x0F) == 0 and lo == 0:
        return ("<null>", hib >> 4)
    a = 0x0500 + ((hib & 0x0F) << 8) + lo
    y, x, out = 0, 0, ""
    while True:
        b = B(a + y)
        c = b & 0x1F
        if c == 0:
            break
        out += ch(c)
        x += 1
        y += 1
        if not (B(a + y - 1) & 0x80):
            continue
        if x == 2:
            continue
        if x != 3:
            break
        if B(a + y - 2) & 0x80:
            continue
        break
    return (out, hib >> 4)


ENDS = {0x14: "<CR>", 0x15: ".<CR>", 0x16: "<END>"}


def decode_msg(a, depth=0):
    words, out, t, n = [], [], 0, 0

    def flush():
        if words:
            out.append(" ".join(words))
            words.clear()

    while n < 400:
        n += 1
        b = B(a + t)
        if b >= 0x80:
            hi, lo = b & 0x7F, B(a + t + 1)
            t += 2
            nib = hi & 0xF0
            w, _ = word_render(lo, hi)
            if nib in (0x30, 0x20, 0x60):
                words.append(w)
                flush()
                out.append(".<CR>" if nib == 0x30 else
                           ("<CR>" if nib == 0x60 else "<END>"))
                break
            words.append(w)
        elif b >= 0x60:
            lo = B(0x1117 + 2 * (b - 0x60))
            hi = B(0x1117 + 2 * (b - 0x60) + 1)
            w, _ = word_render(lo, hi)
            words.append(w)
            t += 1
        elif b >= 0x20:
            flush()
            out.append(chr(b))
            t += 1
        elif b == 0x0B:
            off = B(a + t + 1)
            off = off - 256 if off >= 0x80 else off
            if depth < 4:
                flush()
                out.append("{" + decode_msg(a + t + 1 + off, depth + 1) + "}")
            else:
                out.append("<t0B>")
            t += 2
        elif b == 0x0D:
            flush()
            out.append("<CR>")
            t += 1
        elif b in ENDS:
            flush()
            out.append(ENDS[b])
            t += 1
            break
        elif b == 0x02:
            off = B(a + t + 1)
            off = off - 256 if off >= 0x80 else off
            if depth < 8:
                flush()
                sub = decode_msg(a + t + 1 + off, depth + 1)
                out.append("{GOTO>" + sub + "}")
                t += 2
                break
            out.append("<t02>")
            t += 2
        else:
            flush()
            out.append("<t%02X>" % b)
            t += 1
    else:
        out.append("<TRUNC>")
    flush()
    return "".join(out)


def short_desc(addr):
    if not addr:
        return "(sans desc propre)"
    d = decode_msg(addr)
    first = d.split("<CR>")[0]
    return first[:110]


def plan_path(graph, src, dst):
    """BFS sur le graphe statique (sorties ignorées les conditions) :
    rend [(dir, cond, id), ...] de src a dst, ou None."""
    from collections import deque
    if src not in graph or dst not in graph:
        return None
    prev = {src: None}
    q = deque([src])
    while q:
        cur = q.popleft()
        if cur == dst:
            break
        for d, c, t in graph[cur]["exits"]:
            if t in graph and t not in prev:
                prev[t] = (cur, d, c)
                q.append(t)
    if dst not in prev:
        return None
    out = []
    cur = dst
    while prev[cur] is not None:
        p, d, c = prev[cur]
        out.append((d, c, cur))
        cur = p
    return out[::-1]


def build_graph():
    """Graphe des lieux : {id: {"addr", "b0", "desc", "exits": [(dir,cond,dst)]}}.

    Renvoie (graph, warns). Le record $00 (pointeur non nul, corps illisible)
    est la sentinelle "vide/mort" : il n'est pas inclus dans le graphe mais il
    reste une destination valide des sorties."""
    recs = {}
    for i in range(0x50):
        r = W(0x2070 + 2 * i)
        if r:
            recs[i] = r
    srt = sorted(recs.items(), key=lambda kv: kv[1])
    graph = {}
    warns = []
    for idx, (i, r) in enumerate(srt):
        end = srt[idx + 1][1] if idx + 1 < len(srt) else r + 64
        desc = W(r + 8)
        body = [B(a) for a in range(r + 10, end)]
        if 0xFF not in body:
            warns.append("$%02X : pas de FF terminateur" % i)
            continue
        body = body[:body.index(0xFF)]
        if len(body) % 3:
            warns.append("$%02X : queue non-triplet (%d o)" % (i, len(body)))
            continue
        exits = []
        for k in range(0, len(body), 3):
            d, c, dst = body[k:k + 3]
            if d not in DIRS:
                warns.append("$%02X : dir %d inconnue" % (i, d))
            exits.append((d, c, dst))
        graph[i] = {"addr": r, "b0": B(r), "desc": desc, "exits": exits}
    return graph, warns


def main():
    graph, warns = build_graph()
    # Mode planification : map_static.py --path <from> <to> [--via A,B,...]
    if "--path" in sys.argv:
        k = sys.argv.index("--path")
        src, dst = int(sys.argv[k + 1], 16), int(sys.argv[k + 2], 16)
        via = []
        if "--via" in sys.argv:
            via = [int(x, 16) for x in
                   sys.argv[sys.argv.index("--via") + 1].split(",")]
        legs = [src] + via + [dst]
        for a, b in zip(legs, legs[1:]):
            seg = plan_path(graph, a, b)
            if seg is None:
                print(f"# pas de chemin $%02X -> $%02X" % (a, b))
                return 1
            print(f"# $%02X -> $%02X (%d sorties)" % (a, b, len(seg)))
            for d, c, t in seg:
                nm = DIRS.get(d, "?%d" % d)
                cond = "" if c == 0 else "  [cond $%02X]" % c
                print("%-10s # -> $%02X%s" % (nm, t, cond))
        return 0
    # recoupement terrain : (src, dir_id, dst) observes
    seen = [(0x01, 3, 0x04), (0x04, 3, 0x05), (0x04, 1, 0x05),
            (0x04, 5, 0x06), (0x09, 3, 0x0A), (0x09, 4, 0x05)]
    ecarts = []
    for s, d, t in seen:
        if not any(e[0] == d and e[2] == t for e in graph[s]["exits"]):
            ecarts.append("ECART ($%02X %s -> $%02X absent)" % (s, DIRS[d], t))
    print("# graphe : %d records, %d sorties" %
          (len(graph), sum(len(v["exits"]) for v in graph.values())))
    for i in sorted(graph):
        g = graph[i]
        print("\n## $%02X @ $%04X (b0=$%02X) : %s" %
              (i, g["addr"], g["b0"], short_desc(g["desc"])))
        for d, c, dst in g["exits"]:
            extra = "" if c == 0 else " [cond etat $%02X]" % c
            nm = DIRS.get(d, "?%d" % d)
            dd = "$%02X" % dst
            if dst in graph:
                dd += " (%s)" % short_desc(graph[dst]["desc"])[:60]
            print("  %-10s -> %s%s" % (nm, dd, extra))
    if warns:
        print("\n# avertissements :")
        print("\n".join("  " + w for w in warns))
    print("\n# recoupement terrain :",
          "OK (%d mouvements)" % len(seen) if not ecarts else "ECARTS")
    for e in ecarts:
        print("  " + e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

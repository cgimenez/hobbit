#!/usr/bin/env python3
"""Solveur graphe BFS + SQLite, runs rapides sans sleeps (phase 2).

Modes :
  --scenario : validation dirigee (root -> OPEN CHEST -> EAST -> WAIT x10).
  Defaut (BFS) : expansion generique par niveaux : directions + CORE +
  VERBE x objets extraits du texte du lieu, N workers sim65 en parallele.

Usage : .venv/bin/python scripts/solver.py [--fresh] [--scenario]
        [--depth D] [--budget B] [--workers N] [--samples K]
"""

from __future__ import annotations

import queue
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from solver_db import (ROOT, add_node, best_score, blob_hash, connect,  # noqa: E402
                       find_by_hash, get_banned, get_blob, get_node, get_text,
                       max_depth, ok_at_depth, path_of, record_attempt,
                       state_of, stats, tried, verb_fail_counts)
from solver_run import ensure_workers, run_one  # noqa: E402

PARKED_PATTERNS = [
    "I DO NOT KNOW", "YOU CANNOT GO", "I SEE NOTHING",
    "YOU'RE DOING FINE", "HAVE MASTERED", "WHICH ",
    "TALK TO WHAT", "I DO NOT SEE THE", "IS OPEN", "ALREADY ",
]
DEATH_PATTERNS = ["YOU ARE DEAD", "KILLS YOU", "EATS YOU", "RESTART GAME"]
WIN_SCORE = 99.5  # 'mastered X%' : victoire au-dela

# --- vocabulaire d'actions (ct. docs/aventure.md §102 + seances) ---
MOVES = ["NORTH", "SOUTH", "EAST", "WEST", "NORTHEAST", "NORTHWEST",
         "SOUTHEAST", "SOUTHWEST", "UP", "DOWN",
         "RUN NORTH", "RUN SOUTH", "RUN EAST", "RUN WEST"]
CORE = ["LOOK", "INVENTORY", "WAIT", "SING", "SIT", "SLEEP", "ENTER", "CLIMB"]
# Verbes transitifs par priorite (les 1ers : effets prouves en jeu).
ACT_HI = ["OPEN", "GET", "GIVE", "TAKE", "DROP", "KILL", "EXAMINE", "TALK",
          "ENTER", "PUSH", "EAT", "THROW"]
ACT_LO = ["CLOSE", "ATTACK", "BREAK", "READ", "FOLLOW", "LIGHT", "LOCK",
          "UNLOCK", "FILL", "EMPTY", "DRINK", "PULL", "WEAR", "TIE", "UNTIE"]
PERSONS = ["GANDALF", "THORIN", "ELROND", "ELF", "TROLL", "HIDEOUS",
           "VICIOUS", "WARG"]
OBJ_VOCAB = ["MAP", "CHEST", "DOOR", "KEY", "LUNCH", "ROCK", "BARREL",
             "TORCH", "WINE", "ROPE", "LAMP", "CANDLE", "LANTERN", "MATCHES",
             "RIVER", "BOAT", "GOLD", "RING", "SWORD", "BREAD", "FOOD",
             "WATER", "STONE", "BRIDGE", "GATE", "PATH", "HILL", "CAVE",
             "HOUSE", "WALL", "WINDOW", "TABLE", "BED", "STAIRS"] + PERSONS


def split_cmd(cmd: str) -> tuple[str, str | None]:
    """(verbe, 1er complement) : 'GIVE MAP TO THORIN' -> ('GIVE', 'MAP'),
    'TALK TO GANDALF' -> ('TALK', 'GANDALF'), 'EAST' -> ('EAST', None)."""
    parts = cmd.split()
    verb = parts[0] if parts else ""
    obj = next((w for w in parts[1:] if w not in ("TO", "AT", "THE")), None)
    return verb, obj


def verb_of(cmd: str) -> str:
    return cmd.split()[0] if cmd else ""


def extract_objects(text: str) -> list[str]:
    """Noms du vocabulaire presents dans l'ecran (mots entiers, insensible)."""
    up = text.upper()
    return [w for w in OBJ_VOCAB if re.search(r"\b" + w + r"\b", up)]
    """Noms du vocabulaire presents dans l'ecran (mots entiers, insensible)."""
    up = text.upper()
    return [w for w in OBJ_VOCAB if re.search(r"\b" + w + r"\b", up)]


WORD_RE = re.compile(r'I DO NOT KNOW THE WORD\s+"?\s*([A-Z]+)',
                      re.IGNORECASE)


def parse_unknown(text: str) -> list[str]:
    """Mots inconnus cites par le parser : bannissables globalement
    (dictionnaire fixe, independant de l'etat). UNIQUEMENT la variante
    WORD : la variante VERB ("DO NOT KNOW THE VERB") designe une
    combinaison inconnue, pas un mot a bannir."""
    return list({m.group(1).upper() for m in WORD_RE.finditer(text)})


def actions_for(text: str, banned: set[str] | None = None,
                moves_only: bool = False) -> list[str]:
    """Actions candidates pour un lieu : mouvements + CORE + VERBE x objets,
    moins tout ce qui contient un mot banni. moves_only : directions seules
    (cartographie des lieux, sans verbe)."""
    banned = banned or set()
    if moves_only:
        return [m for m in MOVES if not any(w in banned for w in m.split())]
    objs = [o for o in extract_objects(text) if o not in banned]
    persons = [p for p in PERSONS if p in objs]
    acts = list(MOVES) + list(CORE)
    for v in ACT_HI + ACT_LO:
        if v in banned:
            continue
        for o in objs:
            acts.append(f"{v} {o}")
    for p in persons:
        acts.append(f"TALK TO {p}")
        for o in objs:
            if o != p:
                acts.append(f"GIVE {o} TO {p}")
    return [a for a in acts
            if not any(w in banned for w in a.split())]


def classify(cmd: str | None, text: str, ndiff: int,
             ploc: int, parent_ploc: int | None) -> tuple[str, str | None]:
    up = text.upper()
    if cmd is None:
        return "ok", None
    for p in DEATH_PATTERNS:
        if p in up:
            return "dead", p
    if (parent_ploc is not None and parent_ploc != 0x01
            and ploc == 0x01 and ndiff >= 30):
        return "dead", "REBOOT-TUNNEL"
    if ndiff == 0:
        for p in PARKED_PATTERNS:
            if p in up:
                return "parked", p
        return "parked", "NO_TICK"
    return "ok", None


def score_of(text: str) -> float | None:
    m = re.search(r"mastered\s+([\d.]+)", text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def play(parent_blob: bytes | None, cmd: str | None, worker: int = 0) -> dict:
    """Un run + retry padde si frappe probablement mangee (0 tick, ni echo
    ni motif connu dans le texte complet)."""
    r = run_one(parent_blob, cmd, worker=worker)
    if (r["valid"] and cmd is not None and r["ndiff"] == 0
            and not r["echo_ok"]
            and not any(p in r["full"].upper()
                        for p in PARKED_PATTERNS + DEATH_PATTERNS)):
        r = run_one(parent_blob, cmd, pad=2, worker=worker)
    return r


def process_result(cx, parent: int | None, cmd: str | None, depth: int,
                   parent_blob: bytes | None, parent_ploc: int | None,
                   r: dict, dt: float) -> int | None:
    """Classe + insere (noeud ou attempt). Main thread uniquement."""
    if not r["valid"]:
        print(f"  ! {cmd!r}: run invalide ({r.get('reason')}, "
              f"blocs={r.get('got')}) [{dt:.2f}s]", flush=True)
        return None
    if cmd is not None and r["ndiff"] == 0:
        # Pas de tick : pas de nouvel etat -> attempts (pas de noeud).
        ploc = parent_ploc if parent_ploc is not None else 0
        _, fail = classify(cmd, r["full"], 0, ploc, parent_ploc)
        record_attempt(cx, parent, cmd, "parked", fail)
        # Seule generalisation dure et sure : le mot inconnu l'est partout
        # (dictionnaire fixe). Le reste depend de l'etat (porte ouverte ou
        # non, objets portes...) : cf. EAST $01 parked puis ok.
        new = parse_unknown(r["full"])
        if new:
            add_banned(cx, new)
            print(f"    mots bannis: {sorted(new)}", flush=True)
        cx.commit()
        print(f"  - {cmd!r}: parked ({fail}) [{dt:.2f}s]", flush=True)
        return None
    h = blob_hash(r["blob"])
    hit = find_by_hash(cx, h)
    if hit is not None:
        print(f"  = {cmd!r}: deja vu -> noeud {hit} "
              f"(ndiff={r['ndiff']}) [{dt:.2f}s]", flush=True)
        return hit
    ploc, _, _, _ = state_of(r["blob"])
    score = score_of(r["full"])
    if score is not None and score >= WIN_SCORE:
        status, fail = "win", None
    else:
        status, fail = classify(cmd, r["full"], r["ndiff"], ploc, parent_ploc)
    nid = add_node(cx, parent, cmd or "", depth, r["blob"], r["text"],
                   r["deltas"], status, fail, score, r["echo_ok"])
    cx.commit()
    tag = (cmd or "ROOT")
    print(f"  + noeud {nid}: {tag!r} depth={depth} ploc=${ploc:02X} "
          f"ndiff={r['ndiff']} status={status}"
          + (f" fail={fail}" if fail else "")
          + (f" score={score}" if score else "")
          + f" [{dt:.2f}s]", flush=True)
    return nid


def step(cx, parent: int | None, cmd: str | None, depth: int,
         parent_blob: bytes | None = None, parent_ploc: int | None = None,
         ) -> int | None:
    t0 = time.time()
    r = play(parent_blob, cmd)
    return process_result(cx, parent, cmd, depth, parent_blob, parent_ploc,
                          r, time.time() - t0)


def seed_root(cx, name: str) -> int | None:
    """Racine d'exploration = checkpoint sav/<name>.bin (mode coverage).

    Insere un noeud racine porte sur le blob du checkpoint, texte = un LOOK
    joue depuis ce blob (vocabulaire d'objets du lieu). Le blob racine reste
    l'etat pre-LOOK (le tick du LOOK n'est pas commite dans la racine)."""
    path = ROOT / "sav" / f"{name}.bin"
    if not path.is_file():
        print(f"-- seed: fichier absent {path}")
        return None
    blob = path.read_bytes()
    from solver_db import BLOB_LEN
    if len(blob) != BLOB_LEN:
        print(f"-- seed: blob {len(blob)} o != {BLOB_LEN}")
        return None
    r = play(blob, "LOOK")
    text = r["text"] if r["valid"] else ""
    hit = find_by_hash(cx, blob_hash(blob))
    if hit is not None:
        print(f"-- seed: sav/{name}.bin deja present (noeud {hit})")
        return hit
    nid = add_node(cx, None, f"SEED:{name}", 0, blob, text, [], "ok",
                   None, None, True)
    cx.commit()
    print(f"-- seed: noeud {nid} depuis sav/{name}.bin (ploc="
          f"${state_of(blob)[0]:02X})", flush=True)
    return nid


def coverage_report() -> None:
    """Couverture des variables nommees (fusion hobbit.db + solver.db)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import memmap
        ev = memmap.load_deltas()
        addrs = memmap.address_slots()
        print("== couverture variables (memmap) ==")
        for base, ln, nom in memmap.D.REGIONS:
            var, cov = set(), set()
            for off in range(ln):
                for s in addrs[(base, off)]:
                    if s.kind == memmap.D.VAR:
                        var.add(s.name)
                        if (base, off) in ev:
                            cov.add(s.name)
            print(f"  ${base:04X} {nom}: {len(cov)}/{len(var)} var nommees")
    except Exception as exc:  # noqa: BLE001
        print(f"  (couverture indisponible : {exc})")



def pick_jobs(cx, todo: list[tuple[int, str, int]],
              tried_all: set, budget_left: int, samples: int,
              full: dict[int, list[str]] | None = None) -> list:
    """Selection en deux phases (elagage par verbe-representant) :
    1. mouvements + CORE + representant canonique de chaque verbe (1er
       objet dans l'ordre d'actions_for -- STABLE d'un tour a l'autre) ;
    2. autres objets seulement pour les verbes ACTIFS (un enfant existe).
    Les verbes inactifs vont en attempts ('schema-skip', reversible).
    Retour : jobs [(nid, cmd, depth)]."""
    by_parent: dict[int, list] = {}
    for nid, cmd, dd in todo:
        by_parent.setdefault(nid, []).append((cmd, dd))
    # Representants canoniques (stables) par parent.
    canon: dict[int, dict[str, str]] = {}
    if full:
        for nid, acts in full.items():
            seen: set[str] = set()
            for a in acts:
                v, o = split_cmd(a)
                if o is not None and v in (ACT_HI + ACT_LO) and v not in seen:
                    seen.add(v)
                    canon.setdefault(nid, {})[v] = a
    jobs: list = []
    for nid, cmds in by_parent.items():
        if len(jobs) >= budget_left:
            break
        phase1, rest = [], []
        for cmd, dd in cmds:
            v, o = split_cmd(cmd)
            if (o is not None and v in (ACT_HI + ACT_LO)
                    and canon.get(nid, {}).get(v) != cmd):
                rest.append((nid, cmd, dd, v))  # non-representant
            else:
                phase1.append((nid, cmd, dd))   # mouvements/CORE/representant
        for j in phase1:
            if len(jobs) >= budget_left:
                break
            jobs.append(j)
        # Phase 2 : differee a la fin du niveau (verbes actifs connus).
        # Stockee via l'ordre : on les ajoute apres, le niveau les jouera
        # dans le meme batch ; l'elagage effectif a lieu au niveau suivant
        # via verb_active().
        for nid_, cmd, dd, v in rest:
            if len(jobs) >= budget_left:
                break
            if verb_active(cx, nid_, v):
                jobs.append((nid_, cmd, dd))
            # sinon : elague pour ce tour (reste candidat plus tard si le
            # verbe devient actif ; attempts note le skip).
        # Note les skips (reversible : pas dans tried_all ; sans doublon).
        already = {(r[0], r[1]) for r in cx.execute(
            "SELECT parent, cmd FROM attempts WHERE parent=?", (nid,)).fetchall()}
        skipped = [(nid_, cmd) for nid_, cmd, _, v in rest
                   if not verb_active(cx, nid_, v)
                   and (nid_, cmd) not in tried_all
                   and (nid_, cmd) not in already]
        for nid_, cmd in skipped:
            record_attempt(cx, nid_, cmd, "schema-skip", f"verbe {cmd.split()[0]} inactif")
        if skipped:
            cx.commit()
    # Echantillonnage loterie (mouvements) : K copies.
    out: list = []
    for nid, cmd, dd in jobs:
        k = samples if verb_of(cmd) in (
            "NORTH", "SOUTH", "EAST", "WEST", "NORTHEAST", "NORTHWEST",
            "SOUTHEAST", "SOUTHWEST", "UP", "DOWN", "RUN") else 1
        for _ in range(k):
            if len(out) >= budget_left:
                break
            out.append((nid, cmd, dd))
        if len(out) >= budget_left:
            break
    return out


def verb_active(cx, nid: int, verb: str) -> bool:
    """Un verbe est actif pour un parent si son representant (ou tout objet)
    a deja produit un etat nouveau (noeud enfant) depuis ce parent."""
    row = cx.execute(
        "SELECT COUNT(*) FROM nodes WHERE parent=? AND cmd LIKE ?",
        (nid, verb + " %")).fetchone()
    return (row[0] or 0) > 0


def worker_loop(w: int, tasks: "queue.Queue", results: "queue.Queue") -> None:
    """Thread dedie : fichiers image/capture propres (SLVW_<w>.sim)."""
    while True:
        t = tasks.get()
        if t is None:
            results.put(None)
            return
        parent, cmd, pblob = t
        t0 = time.time()
        r = play(pblob, cmd, worker=w)
        results.put((parent, cmd, pblob, r, time.time() - t0))


def run_level(tasks: list[tuple[int, str, int, bytes, int]],
              nworkers: int) -> list[tuple]:
    """Joue un niveau en parallele. Tache = (parent, cmd, depth, pblob, pploc).
    Retour : [(parent, cmd, depth, pblob, pploc, r, dt)]."""
    tq: queue.Queue = queue.Queue()
    rq: queue.Queue = queue.Queue()
    for parent, cmd, depth, pblob, _ in tasks:
        tq.put((parent, cmd, pblob))
    for _ in range(nworkers):
        tq.put(None)
    threads = [threading.Thread(target=worker_loop, args=(w, tq, rq),
                                daemon=True) for w in range(nworkers)]
    for th in threads:
        th.start()
    out, done = [], 0
    while done < nworkers:
        item = rq.get()
        if item is None:
            done += 1
            continue
        out.append(item)
    for th in threads:
        th.join()
    bykey = {(p, c): (r, dt) for p, c, _, r, dt in out}
    return [(p, c, d, pb, pp, *bykey[(p, c)]) for p, c, d, pb, pp in tasks]


def bfs(cx, depth_max: int, budget: int, nworkers: int, samples: int,
        moves_only: bool = False) -> int:
    """Expansion generique par niveaux jusqu'a epuisement/budget/win."""
    ensure_workers(nworkers)
    tried_all = tried(cx)
    spent, win_at = 0, None
    while spent < budget:
        banned = get_banned(cx)
        # Niveau le plus bas produisant des jobs non-vides (un niveau dont
        # tout le reste est skippe de schema est saute, pas bloquant).
        found = None
        for d in range(max_depth(cx) + 1):
            if d >= depth_max:
                continue
            cands = [(nid, ploc) for nid, ploc in ok_at_depth(cx, d)]
            full = {nid: actions_for(get_text(cx, nid), banned, moves_only)
                    for nid, _ in cands}
            todo = [(nid, c, d) for nid, _ in cands for c in full[nid]]
            todo = [t for t in todo if (t[0], t[1]) not in tried_all]
            if not todo:
                continue
            prio: dict[int, dict[str, int]] = {}
            for nid, _, _ in todo:
                if nid not in prio:
                    ploc = get_node(cx, nid)[4]
                    prio[nid] = verb_fail_counts(cx, ploc)
            todo.sort(key=lambda t: prio[t[0]].get(t[1].split()[0], 0))
            jobs = pick_jobs(cx, todo, tried_all, budget - spent, samples,
                             full)
            if jobs:
                found = (d, jobs)
                break
        if found is None:
            print("-- plus rien a explorer (frontiere vide ou que des skips) --",
                  flush=True)
            break
        d, jobs = found
        print(f"-- niveau {d}: {len(jobs)} runs ({nworkers} workers) --",
              flush=True)
        t0 = time.time()
        tasks = [(nid, cmd, dd, get_blob(cx, nid), get_node(cx, nid)[4])
                 for nid, cmd, dd in jobs]
        for parent, cmd, dd, pblob, pploc, r, dt in run_level(tasks, nworkers):
            tried_all.add((parent, cmd))
            nid = process_result(cx, parent, cmd, dd + 1, pblob, pploc, r, dt)
            if nid is not None:
                row = get_node(cx, nid)
                if row[9] == "win":
                    win_at = nid
                    break
        spent += len(jobs)
        el = time.time() - t0
        print(f"   niveau {d}: {len(jobs)} runs en {el:.1f}s "
              f"({len(jobs) / max(el, 0.01):.1f}/s), total {spent}/{budget}, "
              f"stats={stats(cx)}", flush=True)
        if win_at is not None:
            break
    if win_at is not None:
        print(f"== WIN noeud {win_at} : {' / '.join(path_of(cx, win_at))} ==")
    sc, sc_nid = best_score(cx)
    if sc is not None:
        print(f"== meilleur score : {sc}% (noeud {sc_nid}) : "
              f"{' / '.join(path_of(cx, sc_nid))} ==")
    return win_at or 0


def scenario(cx) -> int:
    t_all = time.time()
    print("== root (boot + SAVE) ==")
    root = step(cx, None, None, 0)
    if root is None:
        return 1
    root_ploc = get_node(cx, root)[4]

    print("== sondes parked (root) ==")
    for cmd in ["GO EAST", "FLURB", "SCORE", "SOUTH"]:
        step(cx, root, cmd, 1, get_blob(cx, root), root_ploc)

    print("== traversee nominale ==")
    n_chest = step(cx, root, "OPEN CHEST", 1, get_blob(cx, root), root_ploc)
    if n_chest is None:
        return 1
    # Porte deja ouverte par Gandalf sur le tick OPEN CHEST -> parked attendu,
    # pas bloquant : on tente EAST depuis n_chest dans tous les cas.
    n_door = step(cx, n_chest, "OPEN DOOR", 2,
                  get_blob(cx, n_chest), get_node(cx, n_chest)[4])
    base, base_depth = (n_door, 2) if n_door is not None else (n_chest, 1)
    n_east = step(cx, base, "EAST", base_depth + 1,
                  get_blob(cx, base), get_node(cx, base)[4])
    if n_east is None:
        return 1

    print("== WAIT x10 (ticks PNJ) ==")
    prev, prev_ploc = n_east, get_node(cx, n_east)[4]
    prev_depth = get_node(cx, n_east)[3]
    for k in range(1, 11):
        nxt = step(cx, prev, "WAIT", prev_depth + 1,
                   get_blob(cx, prev), prev_ploc)
        if nxt is None:
            break
        prev, prev_ploc = nxt, get_node(cx, nxt)[4]
        prev_depth += 1

    print(f"== stats: {stats(cx)} en {time.time() - t_all:.1f}s ==")
    return 0


def route(cx, rt_file: str, seed_name: str | None,
          save_name: str | None) -> int:
    """Jeu dirige : sequence de commandes (1/ligne, '#' commentaire) depuis
    un checkpoint (--seed) ou le boot, avec suivi de couverture. S'arrete a
    la mort ou a une commande invalide. --save ecrit l'etat final."""
    if seed_name:
        p = ROOT / "sav" / f"{seed_name}.bin"
        if not p.is_file():
            print(f"-- route: checkpoint absent {p}")
            return 1
        blob = p.read_bytes()
    else:
        r0 = run_one(None, None)
        if not r0["valid"]:
            print("-- route: boot invalide")
            return 1
        blob = r0["blob"]
    cmds = [ln.strip() for ln in Path(rt_file).read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    import memmap
    base = set(memmap.load_deltas())
    touched: set[tuple[int, int]] = set()
    print(f"route {rt_file}: {len(cmds)} commandes, depart "
          f"ploc=${state_of(blob)[0]:02X}", flush=True)
    for i, cmd in enumerate(cmds, 1):
        r = play(blob, cmd)
        if not r["valid"]:
            print(f"{i:3d} {cmd:16} INVALIDE ({r.get('reason')})")
            break
        for b, o, _av, _ap in r["deltas"]:
            touched.add((b, o))
        ploc = state_of(r["blob"])[0]
        status, _fail = classify(cmd, r["full"], r["ndiff"], ploc, None)
        first = next((ln for ln in r["text"].splitlines() if ln.strip()), "")
        flag = " MORT" if status == "dead" else ""
        print(f"{i:3d} {cmd:16} ploc=${ploc:02X} nd{r['ndiff']:3d}{flag}  "
              f"{first[:52]}", flush=True)
        if status == "dead":
            break
        blob = r["blob"]
    new = touched - base
    print(f"couverture: {len(touched)} octets touches, {len(new)} nouveaux")
    if new:
        print("  nouveaux:", " ".join(f"${b:04X}+${o:04X}"
                                      for b, o in sorted(new)[:40]))
    if save_name:
        (ROOT / "sav" / f"{save_name}.bin").write_bytes(blob)
        print(f"  save sav/{save_name}.bin (ploc=${state_of(blob)[0]:02X})")
    return 0


def main(argv: list[str]) -> int:
    from solver_db import DB
    if "--fresh" in argv:
        DB.unlink(missing_ok=True)

    def flag(name: str, default: int) -> int:
        return int(argv[argv.index(name) + 1]) if name in argv else default

    cx = connect()
    t_all = time.time()
    goal = (argv[argv.index("--goal") + 1] if "--goal" in argv else "win")
    if "--route" in argv:
        rt = argv[argv.index("--route") + 1]
        seed = argv[argv.index("--seed") + 1] if "--seed" in argv else None
        save = argv[argv.index("--save") + 1] if "--save" in argv else None
        return route(cx, rt, seed, save)
    if "--scenario" in argv:
        rc = scenario(cx)
    else:
        if cx.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 0:
            if "--seed" in argv:
                if seed_root(cx, argv[argv.index("--seed") + 1]) is None:
                    return 1
            else:
                print("== DB vide : seed root ==")
                if step(cx, None, None, 0) is None:
                    return 1
        elif "--seed" in argv:
            seed_root(cx, argv[argv.index("--seed") + 1])
        d_default = 8 if goal == "coverage" else 3
        rc = bfs(cx, depth_max=flag("--depth", d_default),
                 budget=flag("--budget", 150),
                 nworkers=flag("--workers", 4), samples=flag("--samples", 1),
                 moves_only="--moves-only" in argv)
    print(f"== stats: {stats(cx)} en {time.time() - t_all:.1f}s, DB={DB} ==")
    coverage_report()
    return 0 if rc is not None else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Un tick solver = un noeud : restaure le blob parent, joue CMD, capture.

Image : build/sim/SLVW.sim (pack --snapshot SLVW --solver, --fast implicite).
Protocole par run (gabarit \\r, $0D -- JAMAIS \\n brut, lu comme touche) :
  root  : page-turn + SAVE (+sacrificielles)
  noeud : page-turn + LOAD (+sacrificielle vec_05) + CMD + SAVE (+sacrificielle
          vec_06). Le blob parent est patche directement dans le .sim
          (offset 12+(0xE800-0x0400)), pas de repack.
Capture ASCII a la source (shim -D SOLVER, hooks L75B8/L7694) sur FICHIER
(pas de pipe : le scan Python octet-par-octet faisait du backpressure sur
sim65 et triplait le temps) : stdout -> slv_run.bin, scrutation
incrementale avec bytes.find (vitesse C), kill des que les 4 blocs @@SNAP
sont complets (+0,4 s de grace). ~17 Ko/run (vs ~240 Ko de frames).
Marqueurs : @@A+octet (caractere rendu, curseur '+' inclus), @@EOL,
@@P (caractere '>' = prompt : fin de tour), @@K+octet (octet lu sur
stdin, diagnostic), @@SNAP (blob, complétion).
Segmentation : lignes nettoyees ('+' retire) ; texte du noeud = lignes
entre l'echo '> CMD.' et le prompt suivant ; full = tout (motifs).

Retour run_one : dict(text, full, blob, ndiff, echo_ok, valid).
"""

from __future__ import annotations

import subprocess
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from solver_db import BLOB_LEN, REGIONS, ROOT, diff_blobs, make_blob  # noqa: E402

SIM65 = ROOT / "tools" / "cc65" / "bin" / "sim65"
SIM0 = ROOT / "build" / "sim" / "SLVW.sim"
OUT0 = ROOT / "build" / "sim" / "slv_run.bin"
BLOB_OFF = 12 + (0xE800 - 0x0400)
CAP_CYCLES = "1000000000"
GRACE_S = 0.4
TIMEOUT_S = 60
# Pas de cap : ~30 ecrans x 8 Ko = 240 Ko/run, necessaire pour la fenetre
# d'echo/classification (la reponse CMD sort vite des derniers ecrans).

REG_LEN = [ln for _, ln in REGIONS]
M_SNAP = b"@@SNAP\n"          # 7 + NLEN+NOM+IDX+LEN(2) + payload
M_A = b"@@A"                  # 3 + 1 octet (caractere rendu)
M_EOL = b"@@EOL\n"            # 6 (fin de ligne)
M_P = b"@@P\n"                # 4 ('>' prompt : fin de tour)
M_K = b"@@K"                  # 3 + 1 octet (lu sur stdin)
TAIL = 32  # queue retenue si aucun marqueur (marqueur a cheval)


def clean_line(raw: bytes) -> str:
    """Retire les '+' (curseur $2B transient + repos) ; aucun '+' en prose
    (a valider vs charset : cf. --diag)."""
    return raw.replace(b"+", b"").decode("ascii", errors="?").rstrip()


class Capture:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.pos = 0
        self.snap: dict[int, bytes] = {}
        self.cur = bytearray()          # ligne en cours (octets bruts)
        self.alines: list[bytes] = []   # lignes terminees (brutes)
        self.aprompts: list[tuple[int, int]] = []  # (idx_ligne, col) des '>'
        self.keys = bytearray()         # octets lus sur stdin (@@K)

    def feed(self, data: bytes) -> None:
        if data:
            self.buf += data
        b, n, p = self.buf, len(self.buf), self.pos
        while True:
            js = b.find(M_SNAP, p)
            ja = b.find(M_A, p)
            je = b.find(M_EOL, p)
            jp = b.find(M_P, p)
            jk = b.find(M_K, p)
            cand = [(j, k) for k, j in (("s", js), ("a", ja), ("e", je),
                                        ("p", jp), ("k", jk)) if j != -1]
            if not cand:
                p = max(p, n - TAIL)
                break
            j, k = min(cand)
            if k == "a":
                if n - j < 4:
                    p = j
                    break
                self.cur.append(b[j + 3])
                p = j + 4
            elif k == "e":
                if n - j < 6:
                    p = j
                    break
                self.alines.append(bytes(self.cur))
                self.cur = bytearray()
                p = j + 6
            elif k == "p":
                if n - j < 4:
                    p = j
                    break
                self.aprompts.append((len(self.alines), len(self.cur)))
                p = j + 4
            elif k == "k":
                if n - j < 4:
                    p = j
                    break
                self.keys.append(b[j + 3])
                p = j + 4
            else:
                if n - j < 8:
                    p = j
                    break
                nl = b[j + 7]
                if n - j < 8 + nl + 3:
                    p = j
                    break
                idx = b[j + 8 + nl]
                ln = b[j + 8 + nl + 1] | (b[j + 8 + nl + 2] << 8)
                if idx >= 4 or ln != REG_LEN[idx]:
                    p = j + 1
                    continue
                if n - j < 8 + nl + 3 + ln:
                    p = j
                    break
                self.snap[idx] = bytes(b[j + 8 + nl + 3:j + 8 + nl + 3 + ln])
                p = j + 8 + nl + 3 + ln
        self.pos = p
        if self.pos > 65536:  # compacte le prefixe consomme
            del self.buf[:self.pos]
            self.pos = 0

    def complete(self) -> bool:
        return len(self.snap) == 4


def sim_of(worker: int) -> Path:
    return SIM0 if worker == 0 else SIM0.parent / f"SLVW_{worker}.sim"


def out_of(worker: int) -> Path:
    return OUT0 if worker == 0 else OUT0.parent / f"slv_run_{worker}.bin"


def ensure_workers(n: int) -> None:
    """Duplique l'image par worker (patch blob independant par run)."""
    import shutil
    assert SIM0.is_file(), f"image manquante : {SIM0} (pack --snapshot SLVW --solver)"
    for w in range(1, n):
        shutil.copyfile(SIM0, sim_of(w))


def patch_blob(blob: bytes, worker: int = 0) -> None:
    assert len(blob) == BLOB_LEN, f"blob {len(blob)} o != {BLOB_LEN}"
    with open(sim_of(worker), "r+b") as f:
        f.seek(BLOB_OFF)
        f.write(blob)


def build_cmd(cmd: str | None, pad: int = 0) -> bytes:
    """Sequence \\r. pad = lignes vides supplementaires (retry anti-mange)."""
    if cmd is None:  # racine : boot + SAVE direct (pas de LOAD sur zeros)
        lines = ["", "", "SAVE"] + [""] * (2 + pad)
    else:
        lines = (["", "", "LOAD"] + [""] * (3 + pad)
                 + ["", ""] + [cmd] + [""] * (4 + pad)
                 + ["", "SAVE"] + [""] * (2 + pad))
    return ("\r".join(lines) + "\r").encode("ascii")


def decode_screen(h: bytes, font: dict[bytes, str]) -> str:
    """Decode charset (conserve pour la validation ASCII vs frames)."""
    out = []
    for brow in range(0, 200, 8):
        line = "".join(
            font.get(bytes(h[(brow + r) * 40 + col] & 0x3F for r in range(8)), ".")
            for col in range(40))
        if line.strip(". "):
            out.append(line.rstrip(". "))
    return "\n".join(out)


def segment_text(cap: Capture, cmd: str | None) -> tuple[str, str, bool]:
    """full = toutes les lignes nettoyees ; text = reponse segmentee ;
    echo_ok = echo '> CMD.' vu. Le jeu n'imprime souvent aucun CR entre
    prompts (LOAD + sacrificiels + CMD + SAVE sur UNE ligne) : on
    decoupe d'abord en segments de prompt (split sur '> ', chaque '>'
    du flux est un prompt : @@P se declenche sur tout $3E trace).
    L'echo cherche est le DERNIER avant SAVE (tuto LOOK rejoue, WAIT
    auto de grace apres, exclus par la borne SAVE)."""
    if cap.cur:  # queue partielle (kill pendant un WAIT auto)
        cap.alines.append(bytes(cap.cur))
        cap.cur = bytearray()
    segs: list[str] = []
    for raw in cap.alines:
        for part in re.split("(?=> )", clean_line(raw)):
            part = part.rstrip()
            if part:
                segs.append(part)
    full = "\n".join(segs)
    save_idx = None
    for i, s in enumerate(segs):
        if s.startswith("> SAVE."):
            save_idx = i
            break
    if cmd is None:  # racine : tout avant l'echo SAVE (boot + tuto + LOOK)
        cut = save_idx if save_idx is not None else len(segs)
        return "\n".join(segs[:cut]), full, save_idx is not None
    needle = "> " + cmd + "."
    zone = save_idx if save_idx is not None else len(segs)
    echo_at = None
    for i in range(zone - 1, -1, -1):
        if segs[i].startswith(needle):
            echo_at = i
            break
    if echo_at is None:
        return full, full, False
    j = echo_at + 1
    while j < len(segs) and not segs[j].startswith(">"):
        j += 1
    # Reponse sur le segment d'echo lui-meme (pas de CR : echec...) :
    # ex. '> GIVE DOOR TO THORIN.  YOU ARE NOT CARRYING IT.'
    tail = segs[echo_at][len(needle):].strip()
    seg = ([tail] if tail else []) + segs[echo_at + 1:j]
    return ("\n".join(seg) if seg else full), full, True


def run_one(parent_blob: bytes | None, cmd: str | None, pad: int = 0,
             worker: int = 0) -> dict:
    """Joue cmd depuis parent_blob (None = boot frais). Voir module docstring."""
    from solver_db import SNAP_MAGIC
    zero = SNAP_MAGIC + bytes(BLOB_LEN - 4)
    patch_blob(zero if parent_blob is None else parent_blob, worker)
    payload = build_cmd(cmd, pad)
    sim, out = sim_of(worker), out_of(worker)

    cap = Capture()
    t0 = time.time()
    with open(out, "wb") as fout, open(out, "rb") as fin:
        # fin et fout : descriptions distinctes (sans O_APPEND) : fout ecrit
        # a la fin, fin lit a son offset.
        fout.truncate(0)
        proc = subprocess.Popen([str(SIM65), "-x", CAP_CYCLES, str(sim)],
                                stdin=subprocess.PIPE, stdout=fout,
                                stderr=subprocess.DEVNULL)
        try:
            proc.stdin.write(payload)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        done = False
        while time.time() - t0 < TIMEOUT_S:
            chunk = fin.read()
            if chunk:
                cap.feed(chunk)
            if cap.complete():
                done = True
                break
            if proc.poll() is not None:
                chunk = fin.read()
                if chunk:
                    cap.feed(chunk)
                if cap.complete():
                    done = True
                break
            time.sleep(0.01)
        if done:  # grace : texte final jusqu'au prompt qui suit SAVE
            # (astuce @@P : fin de tour = affichage du prompt ; borne seche)
            np = len(cap.aprompts)
            t1 = time.time()
            while time.time() - t1 < GRACE_S:
                chunk = fin.read()
                if chunk:
                    cap.feed(chunk)
                if len(cap.aprompts) > np:
                    break
                time.sleep(0.02)
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
        tail = fin.read()
        if tail:
            cap.feed(tail)
    wall = time.time() - t0

    if not cap.complete():
        return {"valid": False, "wall": wall, "reason": "snap-incomplet",
                "got": sorted(cap.snap)}
    text, full, echo_found = segment_text(cap, cmd)
    if parent_blob is not None:
        deltas = diff_blobs(parent_blob, cap_snap_blob(cap))
    else:
        deltas = []  # racine : pas de parent (vs zeros = artefact)
    norm = full.replace(" ", "")
    echo_ok = True if cmd is None else cmd.replace(" ", "") in norm
    return {"valid": True, "wall": wall, "blob": cap_snap_blob(cap),
            "text": text, "full": full, "ndiff": len(deltas),
            "deltas": deltas, "echo_ok": echo_ok, "echo_seg": echo_found,
            "lines": len(cap.alines), "nprompt": len(cap.aprompts),
            "keys": bytes(cap.keys)}


def cap_snap_blob(cap: Capture) -> bytes:
    return make_blob(cap.snap)


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "diag":
        # Structure du run racine : lignes, prompts @@P vs '>' initiaux,
        # cles lues, segmentation.
        r = run_one(None, None)
        print({k: (v if k not in ("blob", "deltas", "text", "full", "keys")
                   else f"<{len(v)}>")
               for k, v in r.items()})
        if r.get("valid"):
            print("---- cles lues ----")
            print(repr(r["keys"]))
            # Reparse brut pour correler @@P : relit le fichier de capture.
            cap2 = Capture()
            cap2.feed(open(out_of(0), "rb").read())
            raws = [bytes(l) for l in cap2.alines]
            if cap2.cur:
                raws.append(bytes(cap2.cur))
            cleans = [clean_line(l) for l in raws]
            init = [i for i, l in enumerate(cleans) if l.startswith(">")]
            print(f"prompts @@P={len(cap2.aprompts)} "
                  f"lignes '>'={len(init)}")
            no_gt = [(li, col) for li, col in cap2.aprompts
                     if li >= len(raws) or b">" not in raws[li]]
            print(f"@@P sur ligne sans '>' : {no_gt[:10]}")
            print(f"lignes '>' : {init}")
            print("---- texte segmente (racine) ----")
            print(r["text"])
        sys.exit(0)
    r = run_one(None, None)
    print({k: (v if k not in ("blob", "deltas", "text", "full") else f"<{len(v)}>")
           for k, v in r.items()})
    if r.get("valid"):
        print("---- ecran ----")
        print(r["text"][-800:])

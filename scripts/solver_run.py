#!/usr/bin/env python3
"""Un tick solver = un noeud : restaure le blob parent, joue CMD, capture.

Image : build/sim/SLVW.sim (pack --snapshot SLVW --hires, --fast implicite).
Protocole par run (gabarit \\r, $0D -- JAMAIS \\n brut, lu comme touche) :
  root  : page-turn + SAVE (+sacrificielles)
  noeud : page-turn + LOAD (+sacrificielle vec_05) + CMD + SAVE (+sacrificielle
          vec_06). Le blob parent est patche directement dans le .sim
          (offset 12+(0xE800-0x0400)), pas de repack.
Capture sur FICHIER (pas de pipe : le scan Python octet-par-octet faisait
du backpressure sur sim65 et triplait le temps) : stdout -> slv_run.bin,
scrutation incrementale avec bytes.find (vitesse C), kill des que les 4
blocs @@SNAP sont complets (+0,4 s de grace). ~0,7-0,8 s/noeud en serie.

Retour run_one : dict(text, full, blob, ndiff, echo_ok, valid).
  text = dernier ecran (stocke en DB), full = ecrans gardes concatenes
  (fenetre d'echo + classification).
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from solver_db import BLOB_LEN, REGIONS, ROOT, diff_blobs, make_blob  # noqa: E402
from decode_frames import load_font  # noqa: E402

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
M_HIRES = b"@@FRAME hires\n"  # 14 + 8192
M_TEXT = b"@@FRAME text\n"    # 13 + 1120 (remplissage, saute)
M_MEM = b"@@MEM "             # 6 + 10 header + payload (saute)
M_SNAP = b"@@SNAP\n"          # 7 + NLEN+NOM+IDX+LEN(2) + payload
TAIL = 32  # queue retenue si aucun marqueur (marqueur a cheval)


class Capture:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.pos = 0
        self.snap: dict[int, bytes] = {}
        self.frames: list[bytes] = []

    def feed(self, data: bytes) -> None:
        if data:
            self.buf += data
        b, n, p = self.buf, len(self.buf), self.pos
        while True:
            jh = b.find(M_HIRES, p)
            jt = b.find(M_TEXT, p)
            jm = b.find(M_MEM, p)
            js = b.find(M_SNAP, p)
            cand = [(j, k) for k, j in (("h", jh), ("t", jt), ("m", jm), ("s", js))
                    if j != -1]
            if not cand:
                p = max(p, n - TAIL)
                break
            j, k = min(cand)
            if k == "h":
                if n - j < 14 + 8192:
                    p = j
                    break
                self.frames.append(bytes(b[j + 14:j + 14 + 8192]))
                p = j + 14 + 8192
            elif k == "t":
                if n - j < 13 + 1120:
                    p = j
                    break
                p = j + 13 + 1120
            elif k == "m":
                if n - j < 16:
                    p = j
                    break
                try:
                    ln = int(b[j + 11:j + 15], 16)
                except ValueError:
                    p = j + 1
                    continue
                if n - j < 16 + ln:
                    p = j
                    break
                p = j + 16 + ln
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
    assert SIM0.is_file(), f"image manquante : {SIM0} (pack --snapshot SLVW --hires)"
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
    out = []
    for brow in range(0, 200, 8):
        line = "".join(
            font.get(bytes(h[(brow + r) * 40 + col] & 0x3F for r in range(8)), ".")
            for col in range(40))
        if line.strip(". "):
            out.append(line.rstrip(". "))
    return "\n".join(out)


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
        if done:  # grace : dernieres frames (prompts SAVE/verify)
            t1 = time.time()
            while time.time() - t1 < GRACE_S:
                chunk = fin.read()
                if chunk:
                    cap.feed(chunk)
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
    font = load_font()
    decoded = [decode_screen(h, font) for h in cap.frames]
    text = decoded[-1] if decoded else ""
    full = "\n---\n".join(decoded)
    if parent_blob is not None:
        deltas = diff_blobs(parent_blob, cap_snap_blob(cap))
    else:
        deltas = []  # racine : pas de parent (vs zeros = artefact)
    norm = full.replace(" ", "")
    echo_ok = True if cmd is None else cmd.replace(" ", "") in norm
    return {"valid": True, "wall": wall, "blob": cap_snap_blob(cap),
            "text": text, "full": full, "ndiff": len(deltas),
            "deltas": deltas, "echo_ok": echo_ok, "frames": len(decoded)}


def cap_snap_blob(cap: Capture) -> bytes:
    return make_blob(cap.snap)


if __name__ == "__main__":
    r = run_one(None, None)
    print({k: (v if k not in ("blob", "deltas", "text", "full") else f"<{len(v)}>")
           for k, v in r.items()})
    if r.get("valid"):
        print("---- ecran ----")
        print(r["text"][-800:])

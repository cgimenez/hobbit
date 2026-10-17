#!/usr/bin/env python3
"""Comparaison RAM differentielle natif vs WASM, tour par tour, en lockstep.

Les deux moteurs tournent en mode --serve (cf. docs/protocol.md §4.3) :
apres le boot, chacun emet un snapshot "@@M" (0x10000 o) puis, par commande,
un delta "@@D" (octets changes : addr+old+new). Le driver alterne :
  1 tour -> natif, 1 tour -> wasm, compare les deltas.
Au premier octet divergent : stop + explication (memmap_defs.annotate).

Usage : .venv/bin/python scripts/mem_diff.py [cmdfile] [--max N] [--keep]
  cmdfile : 1 commande/ligne (#... ignore, vides = tours CR legitimes).
            Defaut : SOLUTION de web/ui/solution.js.
  --max N : borne le nombre de tours.  --keep : garde les logs build/sim/.
Sortie exit 0 si RAM strictement identique, 1 sinon (premiere divergence).
"""
import os
import re
import select
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memmap_defs as D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
READ_TIMEOUT = 180.0
MEMLEN = 0x10000


def solution_cmds() -> list[str]:
    """SOLUTION de web/ui/solution.js (echappements JS decodes)."""
    src = (ROOT / "web" / "ui" / "solution.js").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"^  '((?:[^'\\]|\\.)*)',?$", src, re.M):
        s = m.group(1).replace("\\r", "\r").replace("\\n", "\n") \
                       .replace("\\'", "'").replace("\\\\", "\\")
        out.append(s)
    assert out, "SOLUTION introuvable dans web/ui/solution.js"
    return out


def load_cmds(path: str | None) -> list[str]:
    if path is None:
        return solution_cmds()
    cmds = []
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # artefact du \n final (les vides internes = tours CR)
    for ln in lines:
        s = ln.rstrip("\r")
        if s.startswith("#"):
            continue
        cmds.append(s)
    return cmds


def read_exact(fd: int, n: int, what: str) -> bytes:
    buf = b""
    while len(buf) < n:
        r, _, _ = select.select([fd], [], [], READ_TIMEOUT)
        if not r:
            raise TimeoutError(f"delai {what} ({len(buf)}/{n} o)")
        chunk = os.read(fd, n - len(buf))
        if not chunk:
            raise EOFError(f"canal ferme pendant {what}")
        buf += chunk
    return buf


def read_sync(rfd: int) -> bytes:
    magic = read_exact(rfd, 4, "sync magic")
    if magic != b"@@M\n":
        raise ValueError(f"sync magic inattendu : {magic!r}")
    return read_exact(rfd, MEMLEN, "sync snapshot")


def read_delta(rfd: int) -> tuple[int, int, dict[int, tuple[int, int]]]:
    magic = read_exact(rfd, 4, "delta magic")
    if magic != b"@@D\n":
        raise ValueError(f"delta magic inattendu : {magic!r}")
    hdr = read_exact(rfd, 5, "delta header")
    turn, rc, nlen = struct.unpack("<HBH", hdr)
    body = read_exact(rfd, nlen * 4, f"delta tour {turn}")
    d: dict[int, tuple[int, int]] = {}
    for i in range(nlen):
        addr, old, new = struct.unpack("<HBB", body[i * 4:i * 4 + 4])
        d[addr] = (old, new)
    return turn, rc, d


def locate(addr: int) -> str:
    """Nom lisible d'une adresse (memmap_defs si region SAVE/LOAD)."""
    for b, ln in D.REGION_LEN.items():
        if b <= addr < b + ln:
            slots = D.annotate(b, addr - b)
            if slots:
                s = slots[0]
                return f"{s.region}:{s.name}[{s.kind}] — {s.doc}"
            return f"{D.region_of(b)}:${addr:04X}"
    fb = [(0xBB80, 0xBFE0, "framebuffer texte"),
          (0xA000, 0xC000, "hires (inutilise, fast)"),
          (0x0400, 0x2BBE, "bloc1+bloc2 (bootstrap/donnees)"),
          (0x2C00, 0x7A81, "bloc4 (code 6502)"),
          (0x7AC0, 0x91B2, "bloc3 (vecteurs)"),
          (0xC000, 0xC300, "shim solveur"),
          (0xE800, 0xF700, "blob SAVE"),
          (0xF700, 0xFC00, "snap.s")]
    for lo, hi, nm in fb:
        if lo <= addr < hi:
            return f"{nm} ${addr:04X}"
    return f"${addr:04X} (hors regions nommees)"


def explain(addr: int, nat: tuple[int, int] | None,
            wasm: tuple[int, int] | None) -> str:
    loc = locate(addr)
    if nat is None:
        return f"${addr:04X} : change cote WASM seul {wasm} | {loc}"
    if wasm is None:
        return f"${addr:04X} : change cote natif seul {nat} | {loc}"
    no, nn = nat
    wo, wn = wasm
    return (f"${addr:04X} : natif ${no:02X}->${nn:02X} vs "
            f"WASM ${wo:02X}->${wn:02X} | {loc}")


def spawn(argv: list[str], mem_w: int, log: Path):
    lf = open(log, "wb")
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=lf,
                         stderr=subprocess.STDOUT, cwd=ROOT,
                         pass_fds=(mem_w,), close_fds=True)
    return p, lf


def main() -> int:
    av = sys.argv[1:]
    pos = []
    maxn = None
    keep = "--keep" in av
    j = 0
    while j < len(av):
        a = av[j]
        if a == "--max" and j + 1 < len(av):
            maxn = int(av[j + 1])
            j += 2
        elif a.startswith("--max="):
            maxn = int(a.split("=", 1)[1])
            j += 1
        elif a == "--keep":
            j += 1
        elif a.startswith("--"):
            j += 1
        else:
            pos.append(a)
            j += 1
    cmds = load_cmds(pos[0] if pos else None)
    if maxn is not None:
        cmds = cmds[:maxn]
    print(f"mem_diff : {len(cmds)} tours, lockstep natif <-> WASM")

    simdir = ROOT / "build" / "sim"
    simdir.mkdir(parents=True, exist_ok=True)
    rn, wn = os.pipe()
    rw, ww = os.pipe()
    pn, lfn = spawn(["build/host/hobplay", "--serve", "--memfd", str(wn)],
                    wn, simdir / "memdiff_native.log")
    pw, lfw = spawn(["node", "web/smoke.mjs", "--serve", "--memfd", str(ww)],
                    ww, simdir / "memdiff_wasm.log")
    for w in (wn, ww):
        os.close(w)

    rc = 0
    try:
        sn = read_sync(rn)
        sw = read_sync(rw)
        if sn == sw:
            print(f"sync post-boot : OK (0x10000 o identiques)")
        else:
            for a in range(MEMLEN):
                if sn[a] != sw[a]:
                    print(f"DIVERGENCE post-boot ${a:04X} : natif "
                          f"${sn[a]:02X} vs WASM ${sw[a]:02X} | "
                          f"{locate(a)}")
                    break
            return 1
        for i, cmd in enumerate(cmds):
            raw = cmd.encode("latin1") + b"\n"
            pn.stdin.write(raw)
            pn.stdin.flush()
            pw.stdin.write(raw)
            pw.stdin.flush()
            tn, rcn, dn = read_delta(rn)
            tw, rcw, dw = read_delta(rw)
            tag = f"tour {i + 1:3d} [{cmd[:24]!r}]"
            if tn != i + 1 or tw != i + 1:
                print(f"{tag} TOUR DESYNC natif={tn} wasm={tw}")
                return 1
            if rcn != rcw:
                print(f"{tag} RC DIVERGENT natif={rcn} wasm={rcw} "
                      f"(changements natif={len(dn)} wasm={len(dw)})")
                return 1
            if dn == dw:
                print(f"{tag} OK ({len(dn)} octets, rc={rcn})")
                continue
            print(f"{tag} DIVERGENCE (natif={len(dn)} wasm={len(dw)} "
                  f"octets, rc={rcn})")
            for a in sorted(set(dn) | set(dw)):
                if dn.get(a) != dw.get(a):
                    print("  " + explain(a, dn.get(a), dw.get(a)))
                    break
            only_n = sorted(set(dn) - set(dw))[:5]
            only_w = sorted(set(dw) - set(dn))[:5]
            if only_n:
                print("  natif seul : " + ", ".join(
                    f"${a:04X}" for a in only_n))
            if only_w:
                print("  wasm seul  : " + ", ".join(
                    f"${a:04X}" for a in only_w))
            return 1
        print(f"RAM IDENTIQUE : sync + {len(cmds)} deltas "
              f"(natif cc == WASM emcc)")
    except (TimeoutError, EOFError, ValueError) as e:
        print(f"ERREUR protocole : {e}")
        rc = 1
    finally:
        for p, lf, rfd in ((pn, lfn, rn), (pw, lfw, rw)):
            try:
                p.stdin.close()
            except Exception:
                pass
            try:
                p.wait(timeout=30)
            except Exception:
                p.kill()
            lf.close()
            os.close(rfd)
        if not keep:
            for f in ("memdiff_native.log", "memdiff_wasm.log"):
                try:
                    (simdir / f).unlink()
                except FileNotFoundError:
                    pass
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Pilote froid sequentiel de sim65 (remplace le brute-force emu.cpp).

Joue une liste de commandes sur une image froide (reset $2C00), UNE par
UNE, sans LOAD/SAVE (continuite RNG exacte, contrairement a run_one) :
envoie CMD+CR, attend l'echo puis le prompt @@P (shim solveur), injecte
un CR sacrificiel si pause sans prompt (wait_for_key, comme play_turn),
max 6 par tour. Capture texte via solver_run.Capture (@@A/@@EOL/@@P/@@K).

Usage :
  .venv/bin/python scripts/sim_cold.py --image build/sim/hobbit_solver.sim \
      --cmds cmds.txt [--cycles 1000000000] [--timeout 30]
  cmds.txt : 1 commande/ligne. Sortie : texte des tours + verdict.
Retourne 0 si victoire (cheering crowd), 2 sinon.
"""

from __future__ import annotations

import argparse
import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver_run import Capture  # noqa: E402

SIM65 = Path(__file__).resolve().parent.parent / "tools" / "cc65" / "bin" / "sim65"
POLL_S = 0.05


def play(cmds: list[str], image: str, cycles: str = "1000000000",
         turn_timeout: float = 30.0, max_sac: int = 6,
         quiet: bool = False) -> dict:
    """Joue cmds a froid. Rend {texts, victory, stall_at, wall}."""
    t0 = time.time()
    texts: list[str] = []
    stall_at = None
    # PTY sur stdout : sim65 (stdio C) devient line-buffered -> les marqueurs
    # @@P/@@EOL (fin de ligne) arrivent au fil de l'eau, pas par blocs de 4K.
    # stdin reste un pipe (ecriture selon besoin, flush explicite).
    master, slave = pty.openpty()
    try:
        proc = subprocess.Popen(
            [str(SIM65), "-x", str(cycles), str(image)],
            stdin=subprocess.PIPE, stdout=slave, stderr=subprocess.DEVNULL,
            close_fds=True)
    finally:
        os.close(slave)
    os.set_blocking(master, False)
    cap = Capture()

    def pump() -> None:
        while True:
            r, _, _ = select.select([master], [], [], 0)
            if not r:
                break
            try:
                ch = os.read(master, 65536)
            except OSError:
                break
            if not ch:
                break
            cap.feed(ch)

    def nprompt() -> int:
        return len(cap.aprompts)

    def wait_for(growth: int, timeout: float) -> bool:
        """Vrai si aprompts a cru de `growth` avant timeout (pompe en continu)."""
        base = nprompt()
        t1 = time.time()
        while time.time() - t1 < timeout:
            pump()
            if nprompt() - base >= growth:
                return True
            if proc.poll() is not None:
                pump()
                return nprompt() - base >= growth
            time.sleep(POLL_S)
        pump()
        return nprompt() - base >= growth

    try:
        # Boot : attend le 1er prompt (tuto LOOK rejoue).
        if not wait_for(1, turn_timeout):
            return {"texts": texts, "victory": False,
                    "stall_at": -1, "wall": time.time() - t0}
        seen = 0
        texts.append(_new_text(cap, seen))
        seen = _nlines(cap)

        for idx, cmd in enumerate(cmds):
            try:
                proc.stdin.write(cmd.encode("ascii") + b"\r")
                proc.stdin.flush()
            except BrokenPipeError:
                stall_at = idx
                break
            # Echo ('> CMD.' => @@P) puis prompt de fin de tour (@@P).
            # Si pas de 2e @@P (pause wait_for_key), CR sacrificiel.
            sac = 0
            base = nprompt()
            done = False
            t1 = time.time()
            while time.time() - t1 < turn_timeout and sac <= max_sac:
                pump()
                grown = nprompt() - base
                if grown >= 2:
                    done = True
                    break
                # Quiescence sans prompt : pause probable -> sacrificiel.
                time.sleep(0.5)
                pump()
                if nprompt() == base + grown and grown < 2:
                    if grown >= 1 or (time.time() - t1) > turn_timeout / 3:
                        try:
                            proc.stdin.write(b"\r")
                            proc.stdin.flush()
                        except BrokenPipeError:
                            break
                        sac += 1
                        base = nprompt()
                        t1 = time.time()
                if proc.poll() is not None:
                    break
            texts.append(_new_text(cap, seen))
            seen = _nlines(cap)
            if not done and sac > max_sac:
                stall_at = idx
                break
            if proc.poll() is not None:
                stall_at = idx
                break
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            os.close(master)
        except OSError:
            pass
    full = "\n".join(texts)
    victory = "cheering crowd of dwarves" in full.lower()
    return {"texts": texts, "victory": victory, "stall_at": stall_at,
            "wall": time.time() - t0}


def _nlines(cap: Capture) -> int:
    return len(cap.alines) + (1 if cap.cur else 0)


def _new_text(cap: Capture, seen: int) -> str:
    """Lignes apparues depuis `seen` (segmentation par tour)."""
    from solver_run import clean_line  # noqa: E402
    raws = [bytes(l) for l in cap.alines]
    if cap.cur:
        raws.append(bytes(cap.cur))
    lines = [clean_line(l) for l in raws if clean_line(l).strip()]
    return "\n".join(lines[seen:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--cmds", required=True)
    ap.add_argument("--cycles", default="1000000000")
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()
    cmds = [l.rstrip("\n") for l in open(a.cmds, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    r = play(cmds, a.image, cycles=a.cycles, turn_timeout=a.timeout)
    print("\n".join(r["texts"][-3:]))
    print(f"# victory={r['victory']} stall_at={r['stall_at']} "
          f"wall={r['wall']:.1f}s tours={len(r['texts'])}", file=sys.stderr)
    return 0 if r["victory"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

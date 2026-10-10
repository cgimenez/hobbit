#!/usr/bin/env python3
"""Filtre interactif pour play.sh : stdout sim65 (variante SOLVER) -> texte.

Affiche :
  @@A+octet : caractere ('+' curseur jete, $08 = backspace, $0D/$0A =
              newline, autres controles ignores).
  @@EOL  : newline (scroll mode texte).
  @@EOLR : newline du mode RAW (fin de ligne de commande) ; supprime s'il
           est immediatement suivi d'un @@EOL (RETURN + reponse = 1 saut).
  @@P (prompt) / @@K (octet lu) : ignores.

Persistance SAVE/LOAD (mode --snapshot) : le jeu emet 4 blocs
  "@@SNAP\\n" + NLEN + NOM + IDX + LEN(2 LE) + payload
via harness/snap.s. Des que les 4 regions sont vues, le blob 3627 o
("SNAP" + regions idx 0..3) est ecrit dans l'argument (sav/play.bin) :
la session suivante le recharge (pack --snapshot).

os.read (1 appel systeme) : rend l'octet disponible immediatement
(sys.stdin.buffer.read(N) attendrait N octets et figerait l'affichage).
Octets hors marqueurs (anomalie) : ignores, comptes sur stderr en fin.
"""

import os
import sys

M_A = b"@@A"              # 3 + 1 octet
M_EOL = b"@@EOL\n"        # 6  (scroll mode texte)
M_EOLR = b"@@EOLR\n"      # 7  (scroll mode RAW = echo ligne de commande)
M_P = b"@@P\n"            # 4
M_K = b"@@K"              # 3 + 1 octet
M_SNAP = b"@@SNAP\n"      # 7 + NLEN(1) + NOM + IDX(1) + LEN(2) + payload
TAIL = 32
# Regions SAVE, meme ordre que harness/snap.s REGTAB / sim_tickdiff.c /
# solver_db.REGIONS : idx 0 = ZP $00BE/24 ; 1 = etats $1B1A/1366 ;
# 2 = scripts $28CC/753 ; 3 = records $211A/1480.
REGION_LENS = (0x0018, 0x0556, 0x02F1, 0x05C8)


def main() -> int:
    blob_path = sys.argv[1] if len(sys.argv) > 1 else None
    infd = sys.stdin.fileno()
    out = sys.stdout
    err = sys.stderr
    buf = bytearray()
    pos = 0
    regions: dict[int, bytes] = {}
    saved = False
    skipped = 0
    eof = False

    def maybe_write() -> None:
        nonlocal saved
        if not blob_path or len(regions) != 4:
            return
        blob = b"SNAP" + b"".join(regions[i] for i in range(4))
        with open(blob_path, "wb") as f:
            f.write(blob)
        saved = True

    while not eof:
        try:
            chunk = os.read(infd, 65536)
        except OSError:
            chunk = b""
        if chunk:
            buf += chunk
        else:
            eof = True
        n = len(buf)
        while True:
            cand = [(buf.find(m, pos), k) for k, m in
                    (("a", M_A), ("e", M_EOL), ("r", M_EOLR), ("p", M_P),
                     ("k", M_K), ("s", M_SNAP))]
            cand = [(j, k) for j, k in cand if j != -1]
            if not cand:
                if eof:
                    pos = n
                else:
                    pos = max(pos, n - TAIL)
                break
            j, k = min(cand)
            if j > pos:
                skipped += j - pos  # hors marqueurs : resync (anomalie)
                pos = j
            if k == "a":
                if n - j < 4:
                    break
                c = buf[j + 3]
                if c in (0x0D, 0x0A):
                    out.write("\n")
                elif c == 0x08:
                    out.write("\b \b")
                elif c == ord("+"):
                    pass  # curseur transient / repos
                elif 0x20 <= c < 0x7F:
                    out.write(chr(c))
                elif c > 0x7F:
                    out.write("?")
                # autres controles : ignores
                out.flush()
                pos = j + 4
            elif k == "e":
                if n - j < 6:
                    break
                out.write("\n")
                out.flush()
                pos = j + 6
            elif k == "r":
                # Scroll RAW (fin de ligne de commande). S'il est suivi
                # (en sautant les curseurs '+') d'un scroll texte (reponse),
                # ne pas doubler le saut : le "@@EOL" texte fera la ligne.
                if n - j < 7:
                    break
                q = j + 7
                while buf[q:q + 4] == M_A + b"+":
                    q += 4
                if n - q >= 6 or eof:
                    if bytes(buf[q:q + 6]) != M_EOL:
                        out.write("\n")
                        out.flush()
                    pos = j + 7
                else:
                    break  # attendre la suite pour decider
            elif k in ("p", "k"):
                if n - j < 4:
                    break
                pos = j + 4
            else:  # "s" : bloc snapshot
                if n - j < 8:
                    break
                nl = buf[j + 7]
                if n - j < 8 + nl + 3:
                    break
                idx = buf[j + 8 + nl]
                ln = buf[j + 8 + nl + 1] | (buf[j + 8 + nl + 2] << 8)
                if idx >= 4 or ln != REGION_LENS[idx]:
                    pos = j + 1  # faux positif : resync
                    continue
                if n - j < 8 + nl + 3 + ln:
                    break
                regions[idx] = bytes(
                    buf[j + 8 + nl + 3:j + 8 + nl + 3 + ln])
                maybe_write()
                pos = j + 8 + nl + 3 + ln
        if pos > 65536:
            del buf[:pos]
            pos = 0
    out.flush()
    if skipped:
        err.write(f"\n[sim_play: {skipped} octets hors marqueurs ignores]\n")
    if blob_path:
        err.write(f"[sauvegarde : {blob_path}"
                  + (" (ecrite)" if saved else " (inchangee)")
                  + "]\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

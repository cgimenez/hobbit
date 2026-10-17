#!/usr/bin/env python3
"""Compare une trace memoire @@M/@@D (ex. mem_browser.bin) a la reference
native. Utilise pour diagnostiquer une divergence navigateur (cf. MEM btn).

Usage : .venv/bin/python scripts/mem_cmp.py TRACE_BIN [REF_BIN]
  Defaut REF_BIN = build/sim/native_ref.bin (regenere par hobplay --serve).
Sortie exit 0 si identique, 1 sinon (premier octet divergent explique).
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mem_diff import locate  # noqa: E402  (explication d'adresses)

ROOT = Path(__file__).resolve().parent.parent
MEMLEN = 0x10000


def frames(data: bytes):
    p = 0
    assert data[p:p + 4] == b"@@M\n", data[p:p + 8]
    sync = data[4:4 + MEMLEN]
    p = 4 + MEMLEN
    out = []
    while p < len(data):
        assert data[p:p + 4] == b"@@D\n", (p, data[p:p + 8])
        turn, rc, nlen = struct.unpack("<HBH", data[p + 4:p + 9])
        body = data[p + 9:p + 9 + nlen * 4]
        d = {}
        for i in range(nlen):
            a, o, n = struct.unpack("<HBB", body[i * 4:i * 4 + 4])
            d[a] = (o, n)
        out.append((turn, rc, d))
        p += 9 + nlen * 4
    return sync, out


def main() -> int:
    trace = Path(sys.argv[1])
    ref = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        ROOT / "build" / "sim" / "native_ref.bin"
    s1, f1 = frames(trace.read_bytes())
    s2, f2 = frames(ref.read_bytes())
    if s1 != s2:
        for a in range(MEMLEN):
            if s1[a] != s2[a]:
                print(f"SYNC post-boot diverge ${a:04X} : trace "
                      f"${s1[a]:02X} vs ref ${s2[a]:02X} | {locate(a)}")
                break
        return 1
    print(f"sync post-boot : OK (0x10000 o)")
    for (t1, r1, d1), (t2, r2, d2) in zip(f1, f2):
        if (t1, r1) != (t2, r2) or d1 != d2:
            print(f"tour {t1} : DIVERGENCE (trace rc={r1} "
                  f"{len(d1)} o, ref rc={r2} {len(d2)} o)")
            for a in sorted(set(d1) | set(d2)):
                if d1.get(a) != d2.get(a):
                    v1, v2 = d1.get(a), d2.get(a)
                    f = (lambda v: "absent" if v is None
                         else f"${v[0]:02X}->${v[1]:02X}")
                    print(f"  ${a:04X} : trace {f(v1)} vs ref {f(v2)} "
                          f"| {locate(a)}")
                    break
            return 1
    if len(f1) != len(f2):
        print(f"longueurs : trace {len(f1)} tours vs ref {len(f2)}")
        return 1
    print(f"TRACES IDENTIQUES : sync + {len(f1)} deltas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

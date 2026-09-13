#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decode_few.py — decoder for the Flammenkamp .few encoding (official 90-char alphabet)
Source: https://wwwhomes.uni-bielefeld.de/achim/no3in/encoding (retrieved 2026-09-03)
Usage: python decode_few.py <file.few> [more.few ...]
Output: writes <base>_decoded.txt next to each input, one "x y" point per line (0-indexed).
"""
import sys, os

# index -> char (official 90-char alphabet)
ALPHABET = ("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.")
assert len(ALPHABET) == 90, len(ALPHABET)
CTV = {c: i for i, c in enumerate(ALPHABET)}

SYM_CHAR = {'.': 'iden', 'o': 'rot4', ':': 'rot2', 'c': 'rct4',
            'x': 'dia2', '/': 'dia1', '-': 'ort1', '+': 'ort2', '*': 'full'}

def decode_line(line):
    line = line.strip()
    if not line:
        return None
    sym = line[0]
    rest = line[1:]
    if len(rest) % 2 != 0:
        raise ValueError(f"odd payload length {len(rest)}")
    n = len(rest) // 2
    pts = []
    for r in range(n):
        c1 = CTV[rest[2*r]]
        c2 = CTV[rest[2*r+1]]
        pts.append((r, c1))
        pts.append((r, c2))
    return SYM_CHAR.get(sym, f"unk:{sym}"), n, pts

if __name__ == '__main__':
    for path in sys.argv[1:]:
        sols = []
        for line in open(path, encoding='utf-8'):
            if not line.strip():
                continue
            sols.append(decode_line(line))
        out = os.path.splitext(path)[0] + "_decoded.txt"
        with open(out, 'w', encoding='utf-8') as f:
            for k, (sym, n, pts) in enumerate(sols, 1):
                f.write(f"# solution {k}\n# n={n} sym={sym} source={os.path.basename(path)} (Flammenkamp DB 2026-09-03)\n")
                for x, y in pts:
                    f.write(f"{x} {y}\n")
        ns = sorted({n for _, n, _ in sols})
        print(f"{os.path.basename(path)}: {len(sols)} solutions, n={ns} -> {out}")

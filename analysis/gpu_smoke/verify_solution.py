#!/usr/bin/env python3
"""
Independent verifier for a no-three-in-line 2n-point solution.

Reads a solution produced by n3line_gpu.exe (one "pt i: (r,c)" line per point,
or a bare "r c" per line). Checks:
  (1) exactly 2 points per row, n rows,
  (2) no three of the 2n points are collinear (exact integer cross-product test).

Usage:  python verify_solution.py < sol.txt
        python verify_solution.py n12_seed7.sol
"""
import sys
from itertools import combinations


def parse(path=None):
    pts = []
    lines = open(path, encoding="utf-8").read().splitlines() if path else sys.stdin.read().splitlines()
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        # accept "pt i: (r,c)" or "r c"
        if ln.startswith("pt"):
            seg = ln.split("(", 1)[1].rstrip(")")
            a, b = seg.split(",")
            pts.append((int(a), int(b)))
        elif ln[0].isdigit() or ln[0] in "-":
            a, b = ln.replace("(", " ").replace(")", " ").split()
            pts.append((int(a), int(b)))
    return pts


def collinear(p, q, r):
    # exactly-zero cross product => collinear
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    pts = parse(path)
    n = len(pts) // 2
    # (1) 2 per row
    from collections import Counter
    rowc = Counter(r for r, c in pts)
    bad_rows = {r: k for r, k in rowc.items() if k != 2}
    # (2) no triple collinear
    triples = 0
    bad = []
    for (i, j, k) in combinations(range(len(pts)), 3):
        triples += 1
        if collinear(pts[i], pts[j], pts[k]):
            bad.append((pts[i], pts[j], pts[k]))
    ok = (not bad_rows) and (len(bad) == 0) and (len(pts) == 2 * n)
    print(f"points={len(pts)}  rows={n}  triples_checked={triples}")
    print(f"rows-with-bad-count: {bad_rows if bad_rows else 'none'}")
    print(f"collinear-triples: {len(bad)}")
    if bad:
        for t in bad[:5]:
            print("  BAD:", t)
    print("VERDICT:", "VALID no-three-in-line" if ok else "INVALID")


if __name__ == "__main__":
    main()

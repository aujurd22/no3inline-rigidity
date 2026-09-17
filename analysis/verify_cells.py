#!/usr/bin/env python3
"""Independent brute-force verifier for rot4-NTIL cell sets produced by csearch.cpp.

Reads a cells file (one "x y" per line, or the csearch FOUND cells: line) and checks
that the 4m C4-lifted points on the 2m x 2m grid contain NO three collinear.

Ground truth: C4 rotation on N=2m grid:
  r=0 (x, y) ; r=1 (N-1-y, x) ; r=2 (N-1-x, N-1-y) ; r=3 (y, N-1-x)
Collinearity: (q.x-p.x)*(r.y-p.y) == (r.x-p.x)*(q.y-p.y)  (exact integer, no division).
"""
import sys
from itertools import combinations


def c4(x, y, r, N):
    if r == 0:
        return (x, y)
    if r == 1:
        return (N - 1 - y, x)
    if r == 2:
        return (N - 1 - x, N - 1 - y)
    return (y, N - 1 - x)


def load_cells(path):
    cells = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # accept either "x y" per line or a csearch "cells: (x,y) (x,y) ..." line
            if line.startswith("cells:"):
                line = line[len("cells:"):]
            import re
            for mobj in re.finditer(r"\((\d+),(\d+)\)", line):
                cells.append((int(mobj.group(1)), int(mobj.group(2))))
            # also plain "x y" tokens
            if not cells:
                toks = line.replace(",", " ").split()
                if len(toks) >= 2:
                    cells.append((int(toks[0]), int(toks[1])))
    return cells


def main():
    if len(sys.argv) < 2:
        print("usage: verify_cells.py <cellsfile> [m]")
        sys.exit(2)
    path = sys.argv[1]
    cells = load_cells(path)
    if not cells:
        print("NO CELLS PARSED")
        sys.exit(1)
    m = len(cells)
    N = 2 * m
    pts = []
    for (x, y) in cells:
        for r in range(4):
            pts.append(c4(x, y, r, N))
    # dedupe check (C4 orbit of a cell should be 4 distinct points unless degenerate)
    assert len(pts) == 4 * m, f"expected {4*m} points, got {len(pts)}"
    bad = 0
    bad_triples = []
    for (i, j, k) in combinations(range(len(pts)), 3):
        p, q, r = pts[i], pts[j], pts[k]
        if (q[0] - p[0]) * (r[1] - p[1]) == (r[0] - p[0]) * (q[1] - p[1]):
            bad += 1
            if len(bad_triples) < 5:
                bad_triples.append((p, q, r))
    print(f"m={m} N={N} npts={len(pts)} collinear_triples={bad}")
    if bad:
        for t in bad_triples:
            print("  BAD:", t)
        sys.exit(1)
    else:
        print("VALID rot4-NTIL: no three collinear.")
        sys.exit(0)


if __name__ == "__main__":
    main()

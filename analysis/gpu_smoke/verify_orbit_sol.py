#!/usr/bin/env python3
"""Quick verifier for a solution output by orbit_reduced_gpu.exe."""
import sys
from itertools import combinations

n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
pts = []
for line in sys.stdin:
    line = line.strip()
    if not line or not line.startswith("("): continue
    # Parse "  (r,c) -> (a,b)"
    seg = line.split()[0]  # (r,c)
    r, c = seg.strip("(),").split(",")
    pts.append((int(r), int(c)))

# Build full 2n-point set via R180
full = []
for p in pts:
    full.append(p)
    full.append((n - 1 - p[0], n - 1 - p[1]))

print(f"seeds={len(pts)}  points={len(full)}  n={n}")
bad = 0
for a, b, c in combinations(range(len(full)), 3):
    if (full[b][0]-full[a][0])*(full[c][1]-full[a][1]) == (full[c][0]-full[a][0])*(full[b][1]-full[a][1]):
        bad += 1
        if bad <= 5: print(f"  BAD: {full[a]} {full[b]} {full[c]}")
print(f"collinear triples: {bad}")
print(f"VERDICT: {'VALID' if bad == 0 and len(pts) == n else 'INVALID'}")

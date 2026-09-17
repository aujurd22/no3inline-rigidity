"""Characterize defect lines of the loop vs best-split structured seeds:
how many involve the inserted vertex 36 (insertion defects) vs only original
vertices (geometry-shift defects). Informs what SA must fix."""
import os, sys, json
from math import isqrt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import Board

HERE = os.path.dirname(os.path.abspath(__file__))
cells36 = [tuple(c) for c in json.load(open(os.path.join(HERE,'results/solutions/m36.json')))['cells']]

def edges_from_cells(cells): return [tuple(sorted(c)) for c in cells]

def analyze(name, cells):
    b = Board(37); b.build(edges_from_cells(cells), cells)
    X = b.verify_total()
    inv36 = 0; orig = 0; total = 0
    for k, p in b.pc.items():
        s = (1+isqrt(1+8*p))//2
        if s >= 3:
            total += 1
            verts = set(i>>2 for i in b.line_pts[k])
            if 36 in verts:
                inv36 += 1
            else:
                orig += 1
    print(f"{name}: X={X} n_defect_lines={total}  involve_v36={inv36}  original_only={orig}")

# loop seed
analyze("loop (add v36 as loop)", cells36 + [(36,36)])
# best split seed (31,10)
c = (31,10)
nc = [cc for cc in cells36 if cc!=c] + [(31,36),(36,10)]
analyze("split(31,10)", nc)
# a few more splits
for c in [(32,26),(8,23),(12,23)]:
    a,b = c
    nc = [cc for cc in cells36 if cc!=c] + [(a,36),(36,b)]
    analyze(f"split{c}", nc)

"""D4 quick scan: measure initial (X) of structured m=37 seeds derived from the
m=36 rot4 solution (loop-extension + 36 single-edge splits). No SA yet."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import Board, line_of, isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
cells36 = json.load(open(os.path.join(HERE, 'results/solutions/m36.json')))['cells']
cells36 = [tuple(c) for c in cells36]
assert len(cells36) == 36, len(cells36)

def edges_from_cells(cells):
    return [tuple(sorted(c)) for c in cells]

def initial_X(cells, m=37):
    edges = edges_from_cells(cells)
    b = Board(m)
    b.build(edges, cells)
    return b.verify_total(), b.total_bad, len(b.lifts)

# loop extension: keep all 36 cells, add isolated loop vertex 36
loop_cells = cells36 + [(36, 36)]
lx, linc, ln = initial_X(loop_cells)

print(f"loop-extension: initial verify_total(X)={lx}  (incremental {linc})  lifts={ln}")

# split extensions
print("\nsplit extensions (insert vertex 36 into edge cell (a,b)):")
rows = []
for c in cells36:
    a, b = c
    if c == (a, b):
        new_cells = [cc for cc in cells36 if cc != c] + [(a, 36), (36, b)]
    else:  # c == (b, a)
        new_cells = [cc for cc in cells36 if cc != c] + [(b, 36), (36, a)]
    x, inc, n = initial_X(new_cells)
    rows.append((x, c, n))

rows.sort()  # ascending by X
print(f"{'X':>6}  cell(removed)")
for x, c, n in rows[:10]:
    print(f"{x:>6}  {c}")
print("...")
for x, c, n in rows[-5:]:
    print(f"{x:>6}  {c}")
print(f"\nmin split X = {rows[0][0]}  at cell {rows[0][1]}")
print(f"max split X = {rows[-1][0]}  at cell {rows[-1][1]}")
print(f"loop X      = {lx}")

"""
lll_matching.py (LEAN) -- exact LLL bounds in the STUB-MATCHING space for m=37.

Key realization vs lll_pilot.py:
  * The pilot used a FIXED-SKELETON + random-bijection space (only 37 labels),
    giving d=1.44e6, p=2e-4, e*p*(d+1)=7.8e2 -> FAIL.
  * The CORRECT canonical space is the STUB-MATCHING space (74 stubs, uniform
    perfect matching = uniform over ALL 2-factors). Here a specific k-cell set
    is selected with probability 1/(73*71*...), and two events are dependent
    only if they share a STUB (codegree), not all 37 labels.

We compute EXACTLY (no full event storage needed):
  N            : # conflict events (collinear cell-sets)
  n_2cell      : # 2-cell ("binary") conflicts (a cell with 2 lifted points on a
                 line + another cell on that line -> 3 collinear lifted points)
  n_3cell      : # 3-cell conflicts
  avg_deg_cell : avg # conflicts containing a given cell
  max_ev_per_stub : max # conflict events through any single stub (exact)
  max_stubs_event : max # distinct stubs used by any one event (exact)
  d_max_upper  : max_stubs_event * max_ev_per_stub   (rigorous upper bound)
  e*p*(d+1)    : symmetric-LLL value using p_max (worst-case event prob)

CONCLUSION: even in the correct space, the binary (2-cell) conflicts have
p = 1/(73*71) = 1.9e-4 and codegree ~1e4, so e*p*d > 1. LLL fails in BOTH
spaces. The viable route is conflict-free MATCHING (Graves 2024, codegree-based)
or the nibble, which succeeds on codegree/sparsity, not on e*p*(d+1)<=1.
"""
import sys, math, time
from collections import defaultdict
from itertools import combinations

sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints

m = 37
n = 2 * m
t0 = time.time()
reps, line_cons, _ = generate_constraints(m, use_2factor=False)
print(f"[build] generate_constraints done in {time.time()-t0:.1f}s; "
      f"{len(reps)} cells, {len(line_cons)} lines", flush=True)

# cell (a,b) uses out-stub of a and in-stub of b
cell_stubs = {}
cell_index = {}
for i, (a, b) in enumerate(reps):
    cell_stubs[i] = {("o", a), ("i", b)}
    cell_index[(a, b)] = i

cell_count = [0] * len(reps)      # # conflict events containing this cell
n_3cell = 0
two_cell_set = set()              # dedup 2-cell events (small, ~O(m^2))
max_stubs = 0

for pos_w in line_cons:
    cells = list(pos_w.keys())
    cnt = {c: pos_w[c] for c in cells}
    # 3-cell events (no dup possible: 3 collinear cells -> unique line)
    for trio in combinations(cells, 3):
        n_3cell += 1
        for c in trio:
            cell_count[c] += 1
        st = set()
        for c in trio:
            st |= cell_stubs[c]
        if len(st) > max_stubs:
            max_stubs = len(st)
    # 2-cell binary events: cell with >=2 lifted pts on this line + another cell
    heavy = [c for c in cells if cnt[c] >= 2]
    for h in heavy:
        for c in cells:
            if c == h:
                continue
            ev = frozenset((h, c))
            if ev in two_cell_set:
                continue
            two_cell_set.add(ev)
            for cc in ev:
                cell_count[cc] += 1
            st = set()
            for cc in ev:
                st |= cell_stubs[cc]
            if len(st) > max_stubs:
                max_stubs = len(st)

n_2cell = len(two_cell_set)
N = n_3cell + n_2cell
print(f"[events] N={N:,}  (2-cell={n_2cell:,}  3-cell={n_3cell:,})", flush=True)
avg_deg = (2 * n_2cell + 3 * n_3cell) / len(reps)
print(f"[deg]   avg conflicts per cell = {avg_deg:.1f}   "
      f"(empirical x_deg_per_cell was ~157)", flush=True)

# max # events through any single stub = max over vertices of (row/col sum of
# cell_count). A stub ('o',a) is used by all cells (a,*) i.e. row a; stub
# ('i',b) by all cells (*,b) i.e. col b.
max_ev_per_stub = 0
for v in range(m):
    row = sum(cell_count[cell_index[(v, y)]] for y in range(m))
    col = sum(cell_count[cell_index[(x, v)]] for x in range(m))
    max_ev_per_stub = max(max_ev_per_stub, row, col)
print(f"[stub]  max events per stub = {max_ev_per_stub:,}", flush=True)
print(f"[evt]   max stubs per event = {max_stubs}", flush=True)

d_upper = max_stubs * max_ev_per_stub
print(f"[dep]   d_max <= {d_upper:,}  (rigorous upper bound)", flush=True)

def p_of(k):
    prod = 1.0
    for j in range(k):
        prod *= (73 - 2 * j)
    return 1.0 / prod

p2 = p_of(2)   # 1/(73*71)   -- worst case (binary events exist)
p3 = p_of(3)   # 1/(73*71*69)
p_max = max(p2, p3)
print(f"[prob]  p(2-cell)={p2:.3e}  p(3-cell)={p3:.3e}  p_max={p_max:.3e}", flush=True)

e = math.e
sym = e * p_max * (d_upper + 1)
print(f"[LLL] symmetric e*p_max*(d+1) <= {sym:.3e}  "
      f"({'PASS' if sym <= 1 else 'FAIL (>>1)'})  [d upper bound]", flush=True)
# what if binary events were absent (3-cell only)?
sym3 = e * p3 * (d_upper + 1)
print(f"[LLL] (if no 2-cell) e*p3*(d+1) <= {sym3:.3e}  "
      f"({'PASS' if sym3 <= 1 else 'FAIL'})", flush=True)
print(f"[intuition] expected #bad ~ N*p_max = {N*p_max:.1f} "
      f"(LLL needs e*p*(d+1)<=1, not N*p<1)", flush=True)

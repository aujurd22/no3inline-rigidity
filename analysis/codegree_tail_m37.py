"""
codegree_tail_m37.py -- tail distribution E_tau of the rot4-NTIL conflict
hypergraph H_cf at m=37, to test the hypothesis:

    "avg positive codegree ~99 but max co3 = 1132 -> the max is caused by a
     FEW special cell-pairs, not by typical density."

Goals (per research roadmap 2026-07-14):
  1. Count E_tau = #{ {u,v} : co3(u,v) > tau } for tau in {100,200,400,800};
     report edges, max-degree, connected components of the induced graph.
  2. Histogram of co3 over all positive pairs (tail shape).
  3. Geometric classification of HIGH-co3 pairs (co3 > 200):
       - offset category: same_row / same_col / diagonal / knight
       - share a center-ray (collinear with board centre (18,18))
       - C4-rotation-related about the centre
       - offset has gcd(|dx|,|dy|) >= 2  (large-common-divisor direction)
     This tells whether the anomaly is structurally concentrated (good for the
     delete-anomalies + absorber route) or diffuse.

Reuses generate_constraints() and vectorises the codegree accumulation.
"""
import time, sys
import numpy as np
sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints

m = 37
ncell = m * m
CEN = (m - 1) / 2.0

t0 = time.time()
reps, line_cons, _ = generate_constraints(m, use_2factor=False)
print(f"[build] {len(reps)} cells, {len(line_cons)} lines in {time.time()-t0:.1f}s",
      flush=True)

co3 = np.zeros((ncell, ncell), dtype=np.int32)
deg3 = np.zeros(ncell, dtype=np.int64)

t1 = time.time()
for pos_w in line_cons:
    cells = list(pos_w.keys())
    L = len(cells)
    if L < 3:
        continue
    c2 = (L - 1) * (L - 2) // 2
    idx = np.array(cells, dtype=np.int64)
    deg3[idx] += c2
    ii, jj = np.triu_indices(L, k=1)
    v = L - 2
    co3[idx[ii], idx[jj]] += v
co3 = co3 + co3.T          # symmetrise (diagonal untouched -> stays 0)
print(f"[loop] done in {time.time()-t1:.1f}s", flush=True)

iu, ju = np.triu_indices(ncell, k=1)
co_up = co3[iu, ju]
pos = co_up[co_up > 0]
nX = int(pos.sum() // 3)
max_co3 = int(pos.max())
avg_co3 = float(pos.mean())
med_co3 = float(np.median(pos))
print(f"|V|={ncell}  nX={nX:,}  max_co3={max_co3:,}  avg(pos)={avg_co3:.2f}  "
      f"median(pos)={med_co3:.1f}  #pairs>0={len(pos):,}")
print(f"(cross-check nX should be 30,992,032)")
print()

# ---- 1. tail E_tau ----
print("==== TAIL E_tau (induced graph of pairs with co3 > tau) ====")
taus = [100, 200, 400, 800]
for tau in taus:
    mask = co_up > tau
    n_edges = int(mask.sum())
    deg = (co3 > tau).sum(axis=1)
    max_deg = int(deg.max())
    # connected components via union-find
    parent = list(range(ncell))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    eu = iu[mask]; ev = ju[mask]
    for a, b in zip(eu.tolist(), ev.tolist()):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = set(find(x) for x in range(ncell))
    print(f"  tau={tau:4d}: edges={n_edges:>9,}  max_deg={max_deg:>6,}  "
          f"components={len(roots):>5,}")
print()

# ---- 2. histogram of co3 ----
print("==== HISTOGRAM of positive co3 (pair counts) ====")
buckets = [(1, 10), (11, 25), (26, 50), (51, 100),
           (101, 200), (201, 400), (401, 800), (801, 10**9)]
for lo, hi in buckets:
    cnt = int(((pos >= lo) & (pos <= hi)).sum())
    bar = "#" * min(60, cnt // max(1, (pos.size // 6000)))
    print(f"  [{lo:>4}-{hi if hi<10**9 else '+':>4}] : {cnt:>9,} {bar}")
print()

# ---- 3. geometric classification of HIGH-co3 pairs (co3 > 200) ----
print("==== GEOMETRIC CLASSIFICATION of pairs with co3 > 200 ====")
hi = co_up > 200
ha = iu[hi]; hb = ju[hi]; hco = co_up[hi]
nh = len(ha)
cat = {"same_row": 0, "same_col": 0, "diagonal": 0, "knight": 0}
center_ray = 0
c4rel = 0
gcd2 = 0
top = []   # (co3, (ax,ay),(bx,by))
for k in range(nh):
    a = int(ha[k]); b = int(hb[k]); cc = int(hco[k])
    ax, ay = a // m, a % m
    bx, by = b // m, b % m
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy != 0:
        cat["same_row"] += 1
    elif dy == 0 and dx != 0:
        cat["same_col"] += 1
    elif dx != 0 and dy != 0 and abs(dx) == abs(dy):
        cat["diagonal"] += 1
    else:
        cat["knight"] += 1
    cax, cay = ax - CEN, ay - CEN
    cbx, cby = bx - CEN, by - CEN
    if cax * cby == cbx * cay:       # collinear with centre -> share centre ray
        center_ray += 1
    if (bx - CEN) == -(ay - CEN) and (by - CEN) == (ax - CEN):
        c4rel += 1                    # exactly a 90 deg rotation about centre
    g = int(np.gcd(abs(dx), abs(dy)))
    if g >= 2:
        gcd2 += 1
    if cc >= 600:                     # collect the very top as examples
        top.append((cc, (ax, ay), (bx, by), (dx, dy)))
print(f"  total high pairs (co3>200) = {nh:,}")
print(f"  offset category : same_row={cat['same_row']:,}  same_col={cat['same_col']:,}  "
      f"diagonal={cat['diagonal']:,}  knight(other)={cat['knight']:,}")
print(f"  share centre-ray (collinear w/ centre) = {center_ray:,} "
      f"({100*center_ray/nh:.1f}%)")
print(f"  C4-rotation-related about centre        = {c4rel:,} "
      f"({100*c4rel/nh:.1f}%)")
print(f"  offset gcd(|dx|,|dy|) >= 2               = {gcd2:,} "
      f"({100*gcd2/nh:.1f}%)")
print()
print(f"  top pairs (co3>=600), showing (co3, cellA,(a,b), cellB,(a,b), d(a,b)):")
for cc, A, B, d in sorted(top, reverse=True)[:20]:
    print(f"    co3={cc:>5}  A={A}  B={B}  d={d}")
print()

# ---- 4. hottest cells in the high-codegree graph (tau=200) ----
deg_hi = (co3 > 200).sum(axis=1)
hot = np.argsort(deg_hi)[::-1][:15]
print("==== HOTTEST CELLS in co3>200 graph (top 15 by degree) ====")
for c in hot:
    ci = int(c)
    ax, ay = ci // m, ci % m
    print(f"  cell ({ax},{ay}) : high-co3-degree={int(deg_hi[ci]):,}")
print()
print(f"[done] total {time.time()-t0:.1f}s")

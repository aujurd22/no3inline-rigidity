"""
codegree_residual_m37.py -- after forbidding the extreme high-codegree pairs
(co3 > tau), what is the RESIDUAL max codegree? If it drops below Glock's (C3)
threshold d^{0.95} (d=1369 -> ~952), then the residual conflict hypergraph
satisfies the conflict-free matching theorem, and the extreme tail is the
SOLE culprit.

This is the key theorem-path check for the m=37 bottleneck:
  "complete conflict hypergraph high codegree + 2-factor coupling".

Also reports:
  - whether the forbidden pairs form a matching (max cell-degree 1 => free to
    forbid in a 2-factor encoding, no structural cost)
  - residual (C2)/(C3) verdict per threshold
  - how many originally-extreme cells survive (kept as normal vertices)
"""
import time, sys
import numpy as np
sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints

m = 37
ncell = m * m
d = ncell
C3 = d ** 0.95          # Glock codegree threshold
print(f"[setup] m={m} |V|={ncell} Glock (C3) threshold d^0.95={C3:.1f}")

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
    co3[idx[ii], idx[jj]] += (L - 2)
co3 = co3 + co3.T
print(f"[loop] done in {time.time()-t1:.1f}s", flush=True)

iu, ju = np.triu_indices(ncell, k=1)
co_up = co3[iu, ju]
orig_max = int(co_up.max())
print(f"[orig] max_co3={orig_max:,}  (C3) original verdict: "
      f"{'PASS' if orig_max <= C3 else 'FAIL'} (threshold {C3:.1f})")
print()

for tau in [200, 400, 800]:
    # forbid all pairs with co3 > tau
    forbid = co_up > tau
    n_forbid = int(forbid.sum())
    # max cell-degree within the forbidden graph (is it a matching?)
    fdeg = np.zeros(ncell, dtype=np.int32)
    fa, fb = iu[forbid], ju[forbid]
    for a, b in zip(fa.tolist(), fb.tolist()):
        fdeg[a] += 1
        fdeg[b] += 1
    max_fdeg = int(fdeg.max())
    # residual max codegree = max co3 over pairs NOT forbidden
    residual_max = int(co_up[~forbid].max())
    c3_pass = residual_max <= C3
    print(f"tau={tau:4d}: forbid {n_forbid:>7,} pairs | "
          f"forbidden-graph max-cell-deg={max_fdeg} "
          f"({'MATCHING' if max_fdeg <= 1 else 'NOT matching'}) | "
          f"residual max_co3={residual_max:>5,} | "
          f"(C3) residual: {'PASS' if c3_pass else 'FAIL'}")

print()
print("[interpretation]")
print("  If residual (C3) PASS for some tau, then forbidding those pairs makes")
print("  the residual conflict hypergraph satisfy Glock's conflict-free matching")
print("  theorem => a large conflict-free cell-set exists in the residual.")
print("  The only remaining bridge is: turn that set into a 2-factor")
print("  (absorber / switch argument).")
print(f"[done] {time.time()-t0:.1f}s")

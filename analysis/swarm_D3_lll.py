"""
swarm_D3_lll.py -- rigorous Lovasz Local Lemma analysis of the (X) conflict
hypergraph for m=37.

We enumerate the EXACT conflict hypergraph H:
  * vertices = the m^2 = 1369 fundamental cells
  * hyperedges = unordered triples of DISTINCT cells whose 4m C4-lifts contain
    3 collinear points (a type-(X) conflict)
(Special 2-cell collinearities correspond to loops / 2-cycles, which are
forbidden in a legal 2-factor, so they are excluded from H.)

Then we check the symmetric LLL condition for the bad events
  A_T = "all 3 cells of hyperedge T are selected in the 2-factor":
      e * p * (d + 1) <= 1
with p = E[#bad] / N  (E[#bad] = 265 from conflict_hypergraph sampling) and
d = max dependency degree (max # of other hyperedges sharing a cell with T).
"""
import sys, json, time
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("st", "solver_theory_m37.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

m = 37
n = 2 * m
t0 = time.time()

# all fundamental cells
cells = [(x, y) for x in range(m) for y in range(m)]
NC = len(cells)  # 1369

# lifts (4 per cell), packed as x*n+y
lifts = []
point_to_cell = {}
for ci, (x, y) in enumerate(cells):
    for r in range(4):
        px, py = st.c4(x, y, r, n)
        key = px * n + py
        lifts.append((px, py))
        point_to_cell[key] = ci

NPT = len(lifts)  # 5476
print(f"cells={NC} lifts={NPT}  build {time.time()-t0:.1f}s", flush=True)

ptset = set(point_to_cell.keys())

# enumerate collinear triples via pair reflections (each triple counted once,
# when the pair is the two smallest indices and the third has largest index).
triples = set()          # frozenset of 3 cell indices
cell_deg = [0] * NC
t1 = time.time()
cnt = 0
for i in range(NPT):
    xi, yi = lifts[i]
    # only consider pairs where i is the smallest index -> j>i
    for j in range(i + 1, NPT):
        xj, yj = lifts[j]
        # candidate k = 2*pj - pi  (so i<j<k expected) and k' = 2*pi - pj
        kx, ky = 2 * xj - xi, 2 * yj - yi
        kk = kx * n + ky
        if kk in ptset:
            ci = point_to_cell[lifts[i][0] * n + lifts[i][1]]
            cj = point_to_cell[lifts[j][0] * n + lifts[j][1]]
            ck = point_to_cell[kk]
            if ci != cj and ci != ck and cj != ck:
                triple = (ci, cj, ck) if (ci < cj < ck) else tuple(sorted((ci, cj, ck)))
                triples.add(triple)
        kx2, ky2 = 2 * xi - xj, 2 * yi - yj
        k2 = kx2 * n + ky2
        if k2 in ptset:
            ci = point_to_cell[lifts[i][0] * n + lifts[i][1]]
            cj = point_to_cell[lifts[j][0] * n + lifts[j][1]]
            ck = point_to_cell[k2]
            if ci != cj and ci != ck and cj != ck:
                triple = tuple(sorted((ci, cj, ck)))
                triples.add(triple)
    cnt += 1
    if cnt % 1000 == 0:
        pass

t2 = time.time()
print(f"enumerated pairs in {t2-t1:.1f}s; raw triple-sets={len(triples)}", flush=True)

N = len(triples)
for (a, b, c) in triples:
    cell_deg[a] += 1
    cell_deg[b] += 1
    cell_deg[c] += 1

max_deg = max(cell_deg)
# dependency degree for hyperedge {a,b,c}: other hyperedges sharing a cell
# upper bound = (deg[a]+deg[b]+deg[c]) - 3  (subtract the hyperedge itself)
# exact upper bound on distinct neighbors:
def dep_of(t):
    a, b, c = t
    return cell_deg[a] + cell_deg[b] + cell_deg[c] - 3
d_max = max(dep_of(t) for t in triples)

# bad-event probability (average over the symmetric hypergraph)
E_bad = 265.185  # avg_x_per_factor for m=37 from conflict_hypergraph_params.json
p = E_bad / N

import math
L = math.e * p * (d_max + 1)

# also report avg/median degree, fraction of cells unused
used = sum(1 for d in cell_deg if d > 0)
print(f"N (distinct (X)-triples) = {N}")
print(f"max per-cell degree = {max_deg}; mean = {sum(cell_deg)/NC:.2f}; "
      f"cells in >=1 triple = {used}/{NC}")
print(f"max dependency degree d_max = {d_max}")
print(f"p = E[#bad]/N = {p:.6e}")
print(f"e*p*(d_max+1) = {L:.4f}")
print(f"LLL (symmetric) condition e*p*(d+1) <= 1 : {'HOLDS' if L <= 1 else 'FAILS'} "
      f"(margin {L:.3f}x)")

# Asymmetric LLL improvement (via the standard "Lovasz" form using exp bound):
# condition sum_{E'~E} p(E') <= 1/e  ~  but with the simple 'e p (d+1)' it's symmetric.
# Report the slack needed:
if L > 1:
    print(f"To satisfy symmetric LLL, need p*(d+1) <= 1/e = {1/math.e:.4f}; "
          f"current {p*(d_max+1):.4f} -> factor {p*(d_max+1)*math.e:.3f} too large.")
print(f"elapsed {time.time()-t0:.1f}s")

out = {
    "m": m, "N_X_triples": N, "max_cell_degree": max_deg,
    "mean_cell_degree": sum(cell_deg) / NC, "cells_used": used,
    "d_max_dependency": d_max, "E_bad_per_factor": E_bad,
    "p_event": p, "LLL_L": L, "LLL_holds": bool(L <= 1),
    "note": ("Symmetric LLL on the UNRESTRICTED cell-selection space "
             "(each (X)-triple a bad event). The 2-factor global constraint "
             "is NOT modeled; this bounds the intrinsic conflict density."),
}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "results", "swarm_D3_lll.json"), "w"), indent=2)
print("saved results/swarm_D3_lll.json")

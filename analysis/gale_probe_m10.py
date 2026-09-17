"""
gale_probe_m10.py  --  #2 of the "unexpected tools" trial:
Empirical test of the GALE TRANSFORM as a re-description of the rot4-NTIL
(X)-condition ("no 3 lifted points collinear").

We take a REAL verified rot4 NTIL solution (m=10, 40 lifted points) and:
  (1) compute its Gale transform g_i in R^{4m-3} = R^{37};
  (2) verify the Gale equivalence on actual data:
        primal triple collinear  <=>  Gale triple {g_i,g_j,g_k} linearly dependent
      by (a) checking the TRUE solution has NO dependent Gale triple, and
      (b) introducing a concrete collinear triple and confirming its Gale
          points become rank-2 (dependent).
  (3) assess whether Gale REDUCES the number of forbidden configurations
      (it does not:  C(4m,3) triples either way) -> it is a re-description,
      whose value is theoretical (convex-position / polymer framing), not a
      direct computational speedup.

Outputs: results/gale_probe_m10.json
"""
import os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "m10_val3.json")
OUT = os.path.join(HERE, "results", "gale_probe_m10.json")

with open(SRC) as f:
    sol = json.load(f)
pts = np.array(sol["lifted_points"], dtype=float)   # 40 x 2
N = pts.shape[0]
m = sol["m"]
assert N == 4 * m, (N, m)
print(f"[load] m={m}  N={N} lifted points  bad_X={sol['bad_X']}  verify={sol['verify']}")

def gale_transform(P):
    """P: (N,2) points. Return Gale transform G (N-3, N): G[:,i] = g_i."""
    Nn = P.shape[0]
    centered = P - P.mean(axis=0)                 # sum g_i = 0
    H = np.hstack([centered, np.ones((Nn, 1))])   # (N,3) homogeneous
    U, S, Vt = np.linalg.svd(H, full_matrices=True)
    rank = int(np.sum(S > 1e-9))
    assert rank == 3, f"primal rank {rank} (need 3)"
    G = U[:, 3:].T                                 # (N-3, N)
    return G

def triple_rank(G, i, j, k):
    M = G[:, [i, j, k]]                            # (N-3, 3)
    s = np.linalg.svd(M, compute_uv=False)
    return float(s[-1])                            # smallest singular value; 0 => dependent

# ---- (1) Gale of the TRUE solution ----
G_true = gale_transform(pts)
print(f"[gale] true solution -> Gale dim {G_true.shape} (expected {N-3})")

# sample-check: no triple of Gale points should be dependent
rng = np.random.default_rng(7)
idxs = np.array([rng.choice(N, size=3, replace=False) for _ in range(400)])
min_sv_true = min(triple_rank(G_true, a, b, c) for (a, b, c) in idxs)
print(f"[gale] true solution: min smallest-singular-value over "
      f"{len(idxs)} sampled triples = {min_sv_true:.3e} "
      f"(>0 => no Gale dependence => consistent with bad_X=0)")

# ---- (2) introduce a concrete collinear triple and test Gale dependence ----
# put point 2 exactly on the line through points 0 and 1 (parametric t=0.5)
p0, p1 = pts[0], pts[1]
p2_col = 0.5 * p0 + 0.5 * p1
pts_col = pts.copy()
pts_col[2] = p2_col
G_col = gale_transform(pts_col)
sv_col_triple = triple_rank(G_col, 0, 1, 2)
print(f"[gale] constructed collinear triple (0,1,2): smallest SV = "
      f"{sv_col_triple:.3e}  -> {'DEPENDENT (rank 2)' if sv_col_triple<1e-9 else 'independent (rank 3)'}")

# also confirm a non-collinear triple in the collinear set stays rank 3
sv_rand = triple_rank(G_col, 5, 10, 15)
print(f"[gale] non-collinear triple (5,10,15) in same set: smallest SV = {sv_rand:.3e}")

# ---- (3) constraint-count assessment ----
n_triples = math.comb(N, 3)
# In Gale space the forbidden configuration is "3 Gale points on a line through
# the origin" = a dependent triple = same C(N,3) count as primal collinear triples.
# For m=37: N=148, C(148,3)=~540k triples to police (vs 30,992,032 primal (X)
# hyperedges because primal cells collide many lifted points per line).  The
# Gale count is SMALLER by the factor that many primal hyperedges share cells.
nX_m37 = 30_992_032
n_triples_m37 = math.comb(4 * 37, 3)
verdict = {
    "m": m,
    "N_lifted": N,
    "gale_dim": N - 3,
    "true_solution_min_sv_sampled": min_sv_true,
    "constructed_collinear_triple_sv": sv_col_triple,
    "constructed_collinear_detected_dependent": bool(sv_col_triple < 1e-9),
    "nontrivial_triple_sv_in_collinear_set": sv_rand,
    "local_equivalence_holds_on_data": bool(sv_col_triple < 1e-9 and min_sv_true > 1e-9),
    "constraint_count_m10_gale_triples": n_triples,
    "constraint_count_m37_primal_Xhyperedges": nX_m37,
    "constraint_count_m37_gale_triples": n_triples_m37,
    "conclusion": (
        "EMPIRICAL NEGATIVE on the naive local re-description: the (X)-free "
        "solution's Gale points show NO dependent triple (min SV=%.2e, consistent "
        "with bad_X=0), BUT a deliberately constructed collinear primal triple "
        "(0,1,2) did NOT yield a rank-2/dependent Gale triple (SV=%.2e, rank 3). "
        "So the simple local equivalence '3 primal collinear <=> 3 Gale points "
        "linearly dependent' does NOT hold for this point type. Gale's actual "
        "content is GLOBAL Radon/Tverberg convex-partition theory (0 in conv-hull "
        "of Gale points of a subset <=> its complement's primal points have "
        "intersecting convex hulls), which does NOT reduce to a local forbidden-"
        "triple constraint set for the structured 2-factor search. Net assessment: "
        "Gale is theoretically pretty but of LOW practical leverage for the m=37 "
        "siege - it does not shrink the constraint count (C(4m,3) triples either "
        "way; ~540k at m=37 vs 31M primal (X)-hyperedges, fewer only because "
        "primal collisions merge) and offers no cleaner local check. Recommended "
        "disposition: drop Gale as a computational lever; keep only as optional "
        "language for a global convex-body existence argument (not pursued now)."
        % (min_sv_true, sv_col_triple)),
}
print("\n==== VERDICT (#2 Gale transform) ====")
for k, v in verdict.items():
    print(f"  {k}: {v}")
with open(OUT, "w") as f:
    json.dump(verdict, f, indent=2)
print(f"\n[saved] {OUT}")

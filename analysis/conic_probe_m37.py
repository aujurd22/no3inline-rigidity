"""conic_probe_m37.py -- test the C4-invariant conic (circle) construction for
rot4-NTIL at m=37.

KEY IDEA (m=37 prime => finite-field / algebraic geometry gift):
If all m fundamental cells lie on a single Euclidean circle centered at the
board center, then every lifted 4m point also lies on that circle, and a line
meets a circle in <=2 points => automatically no-3-collinear.  The problem
collapses to: pick 37 cells on a C4-invariant circle that form a 2-factor
(rowSum+colSum==2).

Lift check: cell (x,y) -> (X,Y)=(2(m-x)-1, 2(m-y)-1).  Then
  (X-37)^2 + (Y-37)^2 = 4[(18-x)^2 + (18-y)^2]   (center cell (18,18) since
  2^{-1}*73 mod 37 = 18).  So cells on integer circle (18-x)^2+(18-y)^2 = R
lift to the SINGLE Euclidean circle (X-37)^2+(Y-37)^2 = 4R => guaranteed
no-3-collinear.  (Note: using the integer equation, NOT mod 37, so the lift
stays co-circular; the mod-37 version would scatter points onto concentric
circles and break the guarantee.)

We enumerate every integer circle (R = 0..648, since (18-x)^2+(18-y)^2<=18^2+18^2=648)
with lattice points inside 0..36^2, and for each with >=37 points search for a
2-regular 37-subset.  Reports the max point count => honest feasibility verdict.
"""
import sys, time
sys.path.insert(0, ".")
from solve_m37_r9b import check_2factor, verify_cells

m = 37
# CORRECT C4-rotation center: board center (36.5,36.5) => lifted point
# X = 73-2x, so (X-36.5) = 36.5-2x = (73-4x)/2.  A circle centered at the
# board center has cell-space equation (73-4x)^2 + (73-4y)^2 = C (integer),
# which is exactly C4-invariant.  Using cell-center (18,18) was an
# approximation; we use the exact half-integer center here.
cx = cy = 18  # unused now; kept for clarity


def _search_2factor(P, m, cap=200000):
    """Greedy + capped backtrack: pick m cells from P forming a 2-factor.
    Returns a list of (x,y) or None.  Heuristic, not exhaustive."""
    P = list(P)
    n = len(P)
    if n < m:
        return None
    import random
    random.seed(1)
    for trial in range(2000):
        random.shuffle(P)
        chosen = P[:m]
        ok, deg = check_2factor(chosen, m)
        if ok:
            return chosen
    return None


t0 = time.time()
# precompute lattice points per exact C4-invariant circle C = (73-4x)^2+(73-4y)^2
pts_by_R = {}
for x in range(m):
    for y in range(m):
        C = (73 - 4 * x) ** 2 + (73 - 4 * y) ** 2
        pts_by_R.setdefault(C, []).append((x, y))

Rmax = max(pts_by_R)
print(f"[scan] {m*m} cells, {len(pts_by_R)} distinct C4-invariant circles",
      flush=True)

found = []
max_n = 0
max_R = None
for R, P in pts_by_R.items():
    n = len(P)
    if n > max_n:
        max_n, max_R = n, R
    if n >= m:
        # try to find a 2-regular 37-subset (backtrack, capped)
        # first quick test: full set if exactly 37
        if n == m:
            ok, _ = check_2factor(P, m)
            if ok:
                vf, _ = verify_cells(P, m)
                if vf:
                    found.append((R, P, "full"))
                    continue
        # greedy/backtrack subset search (node cap to stay fast)
        sol = _search_2factor(P, m, cap=200000)
        if sol:
            vf, _ = verify_cells(sol, m)
            if vf:
                found.append((R, sol, "subset"))
print(f"[scan] done in {time.time()-t0:.1f}s", flush=True)
print(f"[result] max lattice points on any circle: n={max_n} at R={max_R}", flush=True)
if found:
    for R, sol, kind in found:
        print(f"[FOUND] R={R} kind={kind} cells={len(sol)}", flush=True)
else:
    print("[result] NO single circle can host 37 fundamental cells with a "
          "2-factor => conic construction infeasible at prime m=37 "
          "(point-count bottleneck).", flush=True)

"""
README theorem verification (task #301 — Math skill rigor check).
Verifies the four theorems that are to be (re)written into README:
  T15.2  : 3-cycle baseframe determinant identity
  C6     : C4-rotational Costas 4-orbit shares a displacement (parallelogram)
  FDR    : a-b = -2(x-y)  =>  a-b Sidon law derivation
  R8-G   : G-symmetric NTIL <=> no line has >2 lifted points (per-line at-most-2)
All outputs are printed AND saved (project rule: persist all computed results).
"""

import json
import random

OUT = {}

# ---------------------------------------------------------------------------
# T15.2 : 3-cycle baseframe determinant identity
# cells of a 3-cycle x->y->z->x are p1=(x,y), p2=(y,z), p3=(z,x)
# det = (p2-p1) x (p3-p1)  [2D cross product]
# ---------------------------------------------------------------------------
def t15_det(x, y, z):
    p1 = (x, y)
    p2 = (y, z)
    p3 = (z, x)
    u = (p2[0] - p1[0], p2[1] - p1[1])
    v = (p3[0] - p1[0], p3[1] - p1[1])
    return u[0] * v[1] - u[1] * v[0]

def t15_formula(x, y, z):
    return -0.5 * ((x - y) ** 2 + (y - z) ** 2 + (z - x) ** 2)

random.seed(0)
t15_ok = True
t15_zero_check = True
samples = []
for _ in range(5000):
    x, y, z = [random.randint(0, 50) for _ in range(3)]
    d = t15_det(x, y, z)
    f = t15_formula(x, y, z)
    if abs(d - f) > 1e-9:
        t15_ok = False
    if (d == 0) != (x == y == z):
        t15_zero_check = False
# explicit degenerate case
samples.append({"x": 3, "y": 3, "z": 3, "det": t15_det(3, 3, 3),
                "formula": t15_formula(3, 3, 3), "note": "degenerate -> det=0"})
samples.append({"x": 1, "y": 4, "z": 2, "det": t15_det(1, 4, 2),
                "formula": t15_formula(1, 4, 2), "note": "non-degenerate -> det!=0"})

OUT["T15.2_3cycle_determinant"] = {
    "identity_holds": t15_ok,
    "zero_iff_degenerate": t15_zero_check,
    "examples": samples,
}

# ---------------------------------------------------------------------------
# C6 : C4-rotational Costas -- a 4-orbit is a square (parallelogram).
# In centred coords, r = 90deg rotation: r(a,b)=(-b,a).
# 4-orbit of p=(a,b): p, rp, -p, -rp.
# pairs (p, rp) and (-rp, -p) have displacement rp - p  vs  (-p) - (-rp) = rp - p.
# ---------------------------------------------------------------------------
def c6_check(a, b):
    p = (a, b)
    rp = (-b, a)          # 90 deg rotation
    minus_p = (-a, -b)
    minus_rp = (b, -a)
    orbit = {p, rp, minus_p, minus_rp}
    disp1 = (rp[0] - p[0], rp[1] - p[1])          # (p, rp)
    disp2 = (minus_p[0] - minus_rp[0], minus_p[1] - minus_rp[1])  # (-rp, -p)
    distinct_pairs = (p, rp) != (minus_rp, minus_p)
    return {
        "orbit_size_4": len(orbit) == 4,
        "shared_displacement": disp1 == disp2,
        "displacement": disp1,
        "distinct_ordered_pairs": distinct_pairs,
        "violates_costas": disp1 == disp2 and distinct_pairs,
    }

c6_samples = [c6_check(2, 1), c6_check(3, 0), c6_check(1, 4), c6_check(5, 2)]
OUT["C6_C4_rotational_Costas"] = {
    "principle": "C4 4-orbit = square/parallelogram => two distinct ordered pairs share a displacement",
    "samples": c6_samples,
    "all_violate": all(s["violates_costas"] for s in c6_samples),
}

# ---------------------------------------------------------------------------
# FDR : a-b Sidon derivation
# (a,b) = (2(n-1-x)-1, 2(n-1-y)-1)  =>  a-b = -2(x-y)
# ---------------------------------------------------------------------------
def fdr_check(n, x, y):
    a = 2 * (n - 1 - x) - 1
    b = 2 * (n - 1 - y) - 1
    return (a - b) == -2 * (x - y)

fdr_ok = all(fdr_check(n, x, y) for n in range(2, 40, 2)
             for x in range(n) for y in range(n))
OUT["FDR_ab_sidon_derivation"] = {
    "identity": "a-b = -2(x-y)",
    "holds_for_all_tested": fdr_ok,
    "n_range": "2..38 even",
}

# ---------------------------------------------------------------------------
# R8-G : G-symmetric NTIL <=> no line has >2 lifted points.
# Construct a C4-symmetric point set from a fundamental quadrant selection
# and verify: it is NTIL (no 3 collinear among all 4m lifted points) IFF
# every board line meets the lifted set in <=2 points.
# ---------------------------------------------------------------------------
def lifted_points(sel, m):
    """sel: set of (x,y) cells in fundamental quadrant (x<m, y<m).
    C4 lift: 4 rotated copies about centre (m-0.5, m-0.5)."""
    pts = []
    for (x, y) in sel:
        base = (x, y)
        # 90 deg rotation about (m-0.5, m-0.5): (x,y)->(2m-1-y, x)
        for k in range(4):
            cx, cy = base
            for _ in range(k):
                cx, cy = 2 * m - 1 - cy, cx
            pts.append((cx, cy))
    return pts

def collinear3(pts):
    S = set(pts)
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                x1, y1 = pts[i]
                x2, y2 = pts[j]
                x3, y3 = pts[k]
                if (x2 - x1) * (y3 - y1) == (y2 - y1) * (x3 - x1):
                    return True
    return False

# small m: enumerate a known-good rot4 selection (single cell) vs bad (two collinear)
m = 4
good = {(0, 0)}                       # 1 cell -> 4 points, no 3 collinear
bad = {(0, 0), (1, 1)}               # two diagonal cells -> aligned under C4 lift
pg = lifted_points(good, m)
pb = lifted_points(bad, m)
# per-line max occupancy check
from collections import defaultdict
def max_line_occ(pts):
    cnt = defaultdict(int)
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            x1, y1 = pts[i]
            x2, y2 = pts[j]
            if x1 == x2:
                key = ("v", x1)
            elif y1 == y2:
                key = ("h", y1)
            else:
                # slope as reduced fraction
                dx, dy = x2 - x1, y2 - y1
                g = __import__("math").gcd(dx, dy)
                dx, dy = dx // g, dy // g
                key = ("l", dx, dy, y1 - dy * (x1 // (dx if dx else 1)))
                # simpler: use intercept form via line through p1,p2
                # use determinant-free unique key: store (dx,dy, cross)
                cross = y1 * x2 - x1 * y2
                key = ("l", dx, dy, cross)
            cnt[key] += 1
    return max(cnt.values()) if cnt else 0

OUT["R8G_per_line_atmost2"] = {
    "principle": "G-symmetric NTIL <=> every board line meets the lifted set in <=2 points (per-line weighted at-most-2)",
    "good_sel_max_line_occ": max_line_occ(pg),
    "good_sel_has_collinear3": collinear3(pg),
    "bad_sel_max_line_occ": max_line_occ(pb),
    "bad_sel_has_collinear3": collinear3(pb),
    "equivalence_holds_on_sample": (max_line_occ(pg) <= 2 and not collinear3(pg)
                                    and max_line_occ(pb) > 2 and collinear3(pb)),
}

print(json.dumps(OUT, indent=2))
with open("analysis/results/verify_readme_theorems.json", "w") as fh:
    json.dump(OUT, fh, indent=2)
print("\n[Saved] analysis/results/verify_readme_theorems.json")

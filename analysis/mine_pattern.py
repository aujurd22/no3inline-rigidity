"""
mine_pattern.py -- extract the algebraic structure of KNOWN rot4 solutions
(cache m=3..36) to look for a hidden constructive pattern (e.g. parabola b(x)).

For each known solution we extract the m fundamental-quadrant cells (top-left
C4 rep of each orbit), then study b as a function of the row index x.
A constant 2nd difference of b(x) would mean b is a quadratic (parabola) in x
-- the classic no-3-collinear construction -- and would directly generalise to
m=37.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rot4_loader as rot4
from solve_m37_r9b import cycle_decomp, check_2factor


def fundamental_cells(sol, m):
    n = 2 * m
    cells = []
    seen = set()
    for (X, Y) in sol:
        # C4 orbit
        orbit = [(X, Y), (n - 1 - Y, X), (n - 1 - X, n - 1 - Y), (Y, n - 1 - X)]
        for (x, y) in orbit:
            if 0 <= x < m and 0 <= y < m:
                if (x, y) not in seen:
                    seen.add((x, y))
                    cells.append((x, y))
                break
    return cells


def analyze(m):
    sols, ext = rot4.load_rot4(2 * m)
    if not sols:
        print(f"m={m}: NO CACHE")
        return
    sol = sols[0]
    cells = fundamental_cells(sol, m)
    # sort by x (row)
    cells.sort(key=lambda c: c[0])
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    # permutation? each row 0..m-1 used exactly once?
    perm = (sorted(xs) == list(range(m)))
    # b as function of x: b = 2(m-y)-1
    b = [2 * (m - y) - 1 for y in ys]
    # 2nd differences of b over x=0..m-1 (only meaningful if permutation)
    if perm:
        d1 = [b[i + 1] - b[i] for i in range(m - 1)]
        d2 = [d1[i + 1] - d1[i] for i in range(m - 2)]
        d2min, d2max = min(d2), max(d2)
        parabolic = (d2max - d2min) <= 2
    else:
        d2 = None
        parabolic = None
    # 2-factor cycle decomposition
    cyc = cycle_decomp(cells, m)
    ok2f, _ = check_2factor(cells, m)
    print(f"m={m} (n={2*m}, cache '{ext}', {len(sols)} sols):")
    print(f"  permutation-type 2-factor : {perm}")
    print(f"  2-factor satisfied        : {ok2f}")
    print(f"  cycle decomposition        : {cyc}")
    if perm:
        print(f"  b(x) = {b[:8]}{'...' if m>8 else ''}")
        print(f"  2nd-diff of b(x)  range   : [{d2min}, {d2max}]  -> "
              f"parabolic? {parabolic}")
    else:
        print(f"  (non-permutation: rows with 0/2 cells; b(x) undefined)")
    print()


if __name__ == "__main__":
    for m in [6, 10, 14, 20, 28, 36]:
        analyze(m)

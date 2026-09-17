"""dump_cells.py -- print the actual fundamental cells of known rot4 solutions
and probe for an algebraic pattern (linear/quadratic mod m, cycle order)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rot4_loader as rot4
from solve_m37_r9b import cycle_decomp


def fundamental_cells(sol, m):
    n = 2 * m
    cells, seen = [], set()
    for (X, Y) in sol:
        for (x, y) in [(X, Y), (n - 1 - Y, X), (n - 1 - X, n - 1 - Y), (Y, n - 1 - X)]:
            if 0 <= x < m and 0 <= y < m:
                if (x, y) not in seen:
                    seen.add((x, y)); cells.append((x, y))
                break
    return cells


def dump(m):
    sols, ext = rot4.load_rot4(2 * m)
    sol = sols[0]
    cells = fundamental_cells(sol, m)
    cells.sort(key=lambda c: c[0])
    print(f"=== m={m} (n={2*m}) cells sorted by x (row) ===")
    print(" x : y   (y mod m)  (2x+y mod m)  (x+2y mod m)  (y-2x mod m)")
    for (x, y) in cells:
        print(f"{x:2d}: {y:2d}    {y%m:2d}       {(2*x+y)%m:2d}        "
              f"{(x+2*y)%m:2d}        {(y-2*x)%m:2d}")
    cyc = cycle_decomp(cells, m)
    print("cycle decomposition:", cyc)
    # reconstruct the cycle order (follow neighbors)
    print()


if __name__ == "__main__":
    for m in [20, 28, 36]:
        dump(m)

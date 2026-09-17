"""
classify_r9d.py -- verify T7 (axis-aligned auto-safety for 2-factors) and
quantify where the quadratic-layer obstruction lives (theorem_r9d).

Reuses reduced_dirs + orbit_c4 from solve_m37_r9b (NO theory re-derived).
Mirrors generate_constraints' (rep->lifted->direction) loop to classify every
per-line at-most-2 constraint by line type:

  axis    : direction (dx,dy) with dx==0 or dy==0   -> horizontal/vertical
  radial  : |dx|==|dy|  (slope +-1 through origin)   -> handled by a-b Sidon
  oblique : everything else                          -> the REAL obstruction

Then:
  (1) T7 empirical check: for known small-m solutions, count lifted points per
      horizontal and per vertical line; assert <= 2 (must hold for ANY 2-factor).
  (2) constraint-count by type, for m in a list (fast: same loop order as
      generate_constraints, ~60s at m=37).

Usage:
  python classify_r9d.py --m 10 20 37
"""
import os, sys, math, argparse, json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solve_m37_r9b import reduced_dirs, orbit_c4, extract_topleft
from quadratic_sidon_completeness import load_known, brute_collinear


def classify_constraints(m):
    n = 2 * m
    reps = [(x, y) for x in range(m) for y in range(m)]
    orbits = [orbit_c4(c, n) for c in reps]
    D = reduced_dirs(n)
    # (dx,dy) -> key -> {rep: weight}   (identical loop to generate_constraints)
    line_w = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for i, (x, y) in enumerate(reps):
        for (X, Y) in orbits[i]:
            for (dx, dy) in D:
                perp = (-dy, dx)
                key = perp[0] * X + perp[1] * Y
                line_w[(dx, dy)][key][i] += 1
    counts = {"axis": 0, "radial": 0, "oblique": 0}
    total_lines = 0
    kept = 0
    for d, lines in line_w.items():
        dx, dy = d
        if dx == 0 or dy == 0:
            t = "axis"
        elif abs(dx) == abs(dy):
            t = "radial"
        else:
            t = "oblique"
        for key, pos_w in lines.items():
            total_lines += 1
            if sum(pos_w.values()) > 2:
                counts[t] += 1
                kept += 1
    return counts, total_lines, kept, len(line_w)


def lifted_points(cells, m):
    pts = []
    for (x, y) in cells:
        a = 2 * (m - x) - 1
        b = 2 * (m - y) - 1
        pts += [(a, b), (-b, a), (-a, -b), (b, -a)]
    return pts


def check_t7(cells, m):
    """max points on any horizontal / vertical line must be <= 2 for a 2-factor."""
    pts = lifted_points(cells, m)
    yb = defaultdict(int)
    xb = defaultdict(int)
    for (X, Y) in pts:
        yb[Y] += 1
        xb[X] += 1
    return max(yb.values()), max(xb.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, nargs="+", default=[10, 20, 37])
    ap.add_argument("--verify-m", type=int, nargs="+",
                    default=[5, 6, 7, 8, 9, 10, 12, 14, 16, 18])
    args = ap.parse_args()

    print("=== T7 empirical verification (known solutions) ===")
    t7_ok = True
    for m in args.verify_m:
        try:
            sols = load_known(m, cap=20)
        except Exception as e:
            print(f"  m={m}: load_known failed ({e}) -- skip")
            continue
        if not sols:
            print(f"  m={m}: no known solutions -- skip")
            continue
        worst_h = worst_v = 0
        for pairs in sols:
            cells = extract_topleft(pairs, m)
            h, v = check_t7(cells, m)
            worst_h = max(worst_h, h)
            worst_v = max(worst_v, v)
        ok = (worst_h <= 2 and worst_v <= 2)
        t7_ok = t7_ok and ok
        print(f"  m={m}: {len(sols)} sols, max pts/horiz={worst_h}, "
              f"max pts/vert={worst_v}  -> T7 {'OK' if ok else 'FAIL'}")

    print("\n=== constraint classification by line type ===")
    print(f"{'m':>3} {'total_lines':>11} {'kept(>2)':>10} "
          f"{'axis':>8} {'radial':>8} {'oblique':>9} {'oblique%':>9}")
    for m in args.m:
        counts, total, kept, ndir = classify_constraints(m)
        ob = counts["oblique"]
        pct = 100.0 * ob / kept if kept else 0
        print(f"{m:>3} {total:>11} {kept:>10} "
              f"{counts['axis']:>8} {counts['radial']:>8} {ob:>9} {pct:>8.1f}%")
        print(f"     (droppable axis given 2-factor={counts['axis']}; "
              f"radial replaced by O(m) a-b Sidon={counts['radial']}; "
              f"oblique non-radial kept={ob})", flush=True)


if __name__ == "__main__":
    main()

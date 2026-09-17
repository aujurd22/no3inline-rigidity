"""
radial_occupancy_analysis.py
===========================
For every cached rot4 solution (m=5..19), lift to board points, group by
radial ring d = (2X-(n-1))**2 + (2Y-(n-1))**2, and tally how many board points
land in each ring (the ring "occupancy"). Then answer:

  Q1. Which rings have exactly 2 points?   (expect: NONE, orbits are size 4)
  Q2. Which rings have exactly 4 points?
  Q3. Which rings have >4 points?  Is >4 usually 8?  where do those sit?

Output: results/radial_occupancy_analysis.md (+ .json)
"""
import sys, json
from collections import Counter, defaultdict
sys.path.insert(0, ".")
from solve_m37_r9b import orbit_c4
from quadratic_sidon_completeness import load_known, cell_xy

def ring_of(X, Y, n):
    c = n - 1
    return (2 * X - c) ** 2 + (2 * Y - c) ** 2

def main():
    report = {}
    per_m = {}
    global_occ = Counter()          # occupancy value -> #rings (across all sols)
    global_occ_rings = defaultdict(Counter)   # occ -> Counter(d value)
    # for occ>4, record normalized radial position of each such ring
    pos_by_occ = defaultdict(list)  # occ -> list of norm_pos in [0,1]
    dminmax_by_occ = defaultdict(lambda: [10**9, -1])
    two_point_rings = []            # (m, d) where occupancy==2

    for m in range(5, 20):
        sols = load_known(m, cap=200)
        if not sols:
            continue
        n = 2 * m
        occ_local = Counter()       # occ -> #rings in this m
        occ_d_local = defaultdict(Counter)
        pos_local = defaultdict(list)
        nsol = len(sols)
        max_occ_m = 0
        for pairs in sols:
            cells = [cell_xy(a, b, m) for (a, b) in pairs]
            board = set()
            for (x, y) in cells:
                board |= set(orbit_c4((x, y), n))
            bc = Counter(ring_of(X, Y, n) for (X, Y) in board)
            # rank rings by d (innermost = 1)
            ds = sorted(bc.keys())
            rank_of = {d: i + 1 for i, d in enumerate(ds)}
            tot = len(ds)
            for d, v in bc.items():
                occ_local[v] += 1
                occ_d_local[v][d] += 1
                global_occ[v] += 1
                global_occ_rings[v][d] += 1
                if v == 2:
                    two_point_rings.append((m, d))
                if v > 4:
                    # normalized position: 0=innermost, 1=outermost occupied
                    norm = (rank_of[d] - 1) / max(1, tot - 1)
                    pos_by_occ[v].append(norm)
                    pos_local[v].append(norm)
                    dminmax_by_occ[v][0] = min(dminmax_by_occ[v][0], d)
                    dminmax_by_occ[v][1] = max(dminmax_by_occ[v][1], d)
                max_occ_m = max(max_occ_m, v)
        per_m[m] = {
            "nsol": nsol,
            "occ_counts": dict(occ_local),
            "max_occ": max_occ_m,
            "pos_stats": {
                str(k): {
                    "n": len(v),
                    "mean_norm": round(sum(v) / len(v), 3) if v else None,
                    "min_norm": round(min(v), 3) if v else None,
                    "max_norm": round(max(v), 3) if v else None,
                } for k, v in pos_local.items()
            },
        }

    report["per_m"] = per_m
    report["global_occ"] = dict(global_occ)
    report["two_point_rings"] = two_point_rings
    report["max_occ_global"] = max(global_occ) if global_occ else 0
    report["pos_by_occ"] = {
        str(k): {
            "n": len(v),
            "mean_norm": round(sum(v) / len(v), 3),
            "min_norm": round(min(v), 3),
            "max_norm": round(max(v), 3),
            "dmin": dminmax_by_occ[k][0],
            "dmax": dminmax_by_occ[k][1],
        } for k, v in pos_by_occ.items()
    }

    # ---- print + write ----
    lines = []
    L = lines.append
    L("# Radial-layer occupancy analysis (all cached rot4 solutions, m=5..19)\n")
    L("## Q1: rings with exactly 2 points")
    if not two_point_rings:
        L("  **NONE.** Every C4 orbit has size exactly 4, so board-point occupancy on")
        L("  any ring is always a multiple of 4. No ring ever contains exactly 2 points.\n")
    else:
        L(f"  Found {len(two_point_rings)} such rings: {two_point_rings}\n")

    L("## Q2/Q3: occupancy distribution (board points per ring)\n")
    L("Global ring-count by occupancy value (summed over all solutions & all m):")
    for v in sorted(global_occ):
        L(f"  occupancy {v:>3}: {global_occ[v]} rings")
    L("")
    L("Per-m breakdown (occ -> #rings):")
    for m in sorted(per_m):
        L(f"  m={m:2d} (nsol={per_m[m]['nsol']:>3}, max_occ={per_m[m]['max_occ']}): "
          f"{per_m[m]['occ_counts']}")

    L("\n## Where do >4-point rings sit? (normalized radial position, 0=innermost,1=outermost)")
    for k in sorted(pos_by_occ, key=lambda x: int(x)):
        s = report["pos_by_occ"][str(k)]
        L(f"  occ={k:>3}: n={s['n']:>5}, mean_norm={s['mean_norm']}, "
          f"range=[{s['min_norm']},{s['max_norm']}], d range=[{s['dmin']},{s['dmax']}]")

    L("\n## Is >4 usually 8?")
    gt4 = sum(global_occ[v] for v in global_occ if v > 4)
    eq8 = global_occ.get(8, 0)
    L(f"  Rings with >4 points: {gt4} total.  Of these, exactly 8: {eq8} "
      f"({100*eq8/gt4:.1f}%).")
    L(f"  By value: " + ", ".join(f"{v}:{global_occ[v]}" for v in sorted(global_occ) if v > 4))

    text = "\n".join(lines)
    print(text)
    with open("results/radial_occupancy_analysis.md", "w") as f:
        f.write(text)
    with open("results/radial_occupancy_analysis.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n[written] results/radial_occupancy_analysis.md / .json")

if __name__ == "__main__":
    main()

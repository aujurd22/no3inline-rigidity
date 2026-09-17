"""
swarm_D1_2_enumerate.py — D1 follow-up: enumerate ALL forbidden orientation combos
for a fixed 2-factor (37 edges, m=37, n=74).

For each triple of edges (e1,e2,e3) and each orientation combo (t1,t2,t3) ∈ {0,1}^3:
  - Compute 3 oriented cells → 12 C4 lifts
  - Check all C(12,3)=220 triples for collinearity
  - If any 3 are collinear → record combo as forbidden (3-CNF clause)

Usage:
    # best-72 config
    python swarm_D1_2_enumerate.py --config solver_theory_m37_long.json \\
        --out swarm_D1_2_best72_clauses.json

    # best-96 config
    python swarm_D1_2_enumerate.py --config solver_theory_m37.json \\
        --out swarm_D1_2_best96_clauses.json

    # random 2-factor
    python swarm_D1_2_enumerate.py --random --seed 42 \\
        --out swarm_D1_2_random_clauses.json

Output JSON contains: edges, n_clauses, clauses [(e1,e2,e3,a,b,c), ...], timing.
"""

import os, sys, json, math, time, random
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import solver_theory_m37 as S

M = 37
N = 2 * M  # 74

def c4_lifts(cell, n):
    """4 C4-rotated lifts of a cell."""
    x, y = cell
    return [(x, y), (n - 1 - y, x), (n - 1 - x, n - 1 - y), (y, n - 1 - x)]

def det_collinear(p1, p2, p3):
    """Determinant test: (p2-p1) × (p3-p1) == 0"""
    return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0]) == 0

def has_any_collinear(pts):
    """Check if any 3 of 12 points are collinear (C(12,3) = 220 checks)."""
    # Inline heavily for speed — local var bindings
    for i in range(12):
        xi, yi = pts[i]
        for j in range(i + 1, 12):
            xj, yj = pts[j]
            dx1 = xj - xi
            dy1 = yj - yi
            for k in range(j + 1, 12):
                xk, yk = pts[k]
                if dx1 * (yk - yi) - dy1 * (xk - xi) == 0:
                    return True
    return False

def enumerate_clauses(edges, n=N):
    """
    For a fixed 2-factor, enumerate all forbidden orientation combos.
    Returns dict with clause data.
    """
    E = len(edges)
    t0 = time.time()

    # Precompute lifts for both orientations of each edge
    L = []
    for u, v in edges:
        if u == v:
            # loop: both orientations yield same cell
            lifts = c4_lifts((u, u), n)
            L.append((lifts, lifts))
        else:
            L.append((c4_lifts((u, v), n), c4_lifts((v, u), n)))

    total_triples = E * (E - 1) * (E - 2) // 6  # C(37,3) = 7770
    clauses = []      # will deduplicate via set
    clause_set = set()
    combos_checked = 0
    collinear_checks = 0

    last_report = time.time()
    report_interval = 10.0  # seconds

    for tidx, (e1, e2, e3) in enumerate(combinations(range(E), 3)):
        # Progress report
        now = time.time()
        if now - last_report > report_interval:
            pct = 100.0 * tidx / total_triples
            elapsed = now - t0
            rate = collinear_checks / elapsed if elapsed > 0 else 0
            print(f"  [{tidx}/{total_triples}] {pct:.1f}% | "
                  f"{elapsed:.0f}s | {rate:.0f} checks/s | "
                  f"{len(clause_set)} clauses found", flush=True)
            last_report = now

        L1, L2, L3 = L[e1], L[e2], L[e3]

        for bits in range(8):
            a = bits & 1
            b = (bits >> 1) & 1
            c = (bits >> 2) & 1

            # Concatenate 12 lifts (4 per edge)
            pts = L1[a] + L2[b] + L3[c]
            combos_checked += 1

            if has_any_collinear(pts):
                key = (e1, e2, e3, a, b, c)
                if key not in clause_set:
                    clause_set.add(key)
                    clauses.append(key)

    dt = time.time() - t0
    n = len(clauses)
    print(f"  DONE: {n} clauses from {combos_checked} orientation combos "
          f"checked across {total_triples} edge triples, {dt:.1f}s", flush=True)

    return {
        "edges": edges,
        "n_clauses": n,
        "clauses": clauses,
        "triples_checked": total_triples,
        "orientation_combos_checked": combos_checked,
        "time_s": dt,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=None,
                    help="JSON config file with 'edges' field")
    ap.add_argument("--random", action="store_true",
                    help="Generate a random 2-factor instead of loading from file")
    ap.add_argument("--seed", type=int, default=20260715,
                    help="Random seed (for --random)")
    ap.add_argument("--out", type=str, default="swarm_D1_2_clauses.json",
                    help="Output JSON path")
    args = ap.parse_args()

    if args.config:
        path = os.path.join(HERE, args.config)
        print(f"Loading config from {path} ...", flush=True)
        data = json.load(open(path))
        edges = [tuple(e) for e in data["edges"]]
        label = args.config.replace(".json", "").replace("solver_theory_m37_", "")
        print(f"  {len(edges)} edges, best_bad={data.get('best_bad', '?')}", flush=True)
    elif args.random:
        rng = random.Random(args.seed)
        edges = S.generate_2factor(M, rng)
        if edges is None:
            print("ERROR: failed to generate random 2-factor", flush=True)
            sys.exit(1)
        label = f"random_seed{args.seed}"
        print(f"Generated random 2-factor with {len(edges)} edges", flush=True)
    else:
        print("ERROR: specify --config or --random", flush=True)
        sys.exit(1)

    result = enumerate_clauses(edges)

    # Store a human-readable summary
    out = {
        "label": label,
        "m": M,
        "n_edges": len(edges),
        "edges": edges,
        "n_clauses": result["n_clauses"],
        "triples_checked": result["triples_checked"],
        "orientation_combos_checked": result["orientation_combos_checked"],
        "clauses": result["clauses"],
        "enumerate_time_s": result["time_s"],
    }

    out_path = os.path.join(HERE, args.out)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}", flush=True)

    # Also write a compact version (just counts + first N clauses as sample)
    sample_path = out_path.replace(".json", "_sample.json")
    sample = {
        "label": label,
        "n_clauses": result["n_clauses"],
        "sample": result["clauses"][:20],
    }
    with open(sample_path, "w") as f:
        json.dump(sample, f, indent=2)
    print(f"Wrote {sample_path}", flush=True)


if __name__ == "__main__":
    main()

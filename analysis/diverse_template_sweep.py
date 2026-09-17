"""
diverse_template_sweep.py — Route 2 (proper): generate several STRUCTURALLY DIVERSE
random 2-factors on m=37, compute each one's frustrated triangles in GEOMETRIC space
(by (u,v) edge-pairs), and intersect across all of them. A non-empty persistent core
across diverse 2-factors is a candidate "inevitable frustrated template" — the kind of
object that could support a universal lower-bound theorem for m=37.

We do NOT need exact min_viol per config (slow CP-SAT); the frustrated-triangle structure
comes directly from the signed graph G_J (fast: enumerate_clauses + build_J + triangle scan).
"""
import sys, os, json, random, time
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J
from solver_2factor_sat_pipeline import enumerate_clauses, generate_2factor_full


def frustrated_triangles_geometric(m, edges):
    edges = [tuple(sorted(e)) for e in edges]
    coord = {i: edges[i] for i in range(len(edges))}
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, _, _ = build_J(clauses)
    adj = defaultdict(dict)
    for (i, j), v in J.items():
        if v == 0:
            continue
        adj[i][j] = 1 if v > 0 else -1
        adj[j][i] = 1 if v > 0 else -1
    tris = set()
    nodes = list(adj.keys())
    for i in nodes:
        for j in adj[i]:
            if j <= i:
                continue
            for k in adj[j]:
                if k <= j:
                    continue
                if k in adj[i]:
                    tris.add(tuple(sorted((i, j, k))))
    fr = set()
    for (i, j, k) in tris:
        if adj[i][j] * adj[j][k] * adj[i][k] < 0:
            fr.add(frozenset({coord[i], coord[j], coord[k]}))
    return fr


def main():
    m = 37
    n_cfg = 8
    rng = random.Random(20260716)
    all_fr = []
    per_size = []
    t0 = time.time()
    for c in range(n_cfg):
        edges = generate_2factor_full(m, rng)
        fr = frustrated_triangles_geometric(m, edges)
        all_fr.append(fr)
        per_size.append(len(fr))
        print(f"  config {c}: {len(fr)} frustrated triangles "
              f"({(time.time()-t0):.1f}s)", flush=True)

    common = set.intersection(*all_fr) if all_fr else set()
    # size distribution of pairwise intersections
    pair_sizes = []
    for a in range(n_cfg):
        for b in range(a + 1, n_cfg):
            pair_sizes.append(len(all_fr[a] & all_fr[b]))
    print(f"\n{n_cfg} diverse configs: frustrated-triangle counts = {per_size}")
    print(f"FULL geometric intersection (all {n_cfg}): {len(common)} triangles")
    print(f"pairwise intersection sizes: min={min(pair_sizes)} "
          f"max={max(pair_sizes)} avg={sum(pair_sizes)/len(pair_sizes):.1f}")

    out = {
        "n_configs": n_cfg,
        "per_config_frustrated_triangles": per_size,
        "full_intersection_size": len(common),
        "pairwise_intersection": {
            "min": min(pair_sizes), "max": max(pair_sizes),
            "avg": sum(pair_sizes) / len(pair_sizes),
        },
        "sample_common": [sorted(t) for t in list(common)[:30]],
    }
    json.dump(out, open("results/diverse_template_sweep.json", "w"), indent=2)
    print("saved results/diverse_template_sweep.json")


if __name__ == "__main__":
    main()

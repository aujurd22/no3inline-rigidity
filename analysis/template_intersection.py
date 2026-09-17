"""
template_intersection.py — Route 2: compare the FRUSTRATED TRIANGLES of two (or more)
low-violation 2-factors in GEOMETRIC space (by (u,v) edge-pairs, which are consistent
across configs), and report their intersection as a candidate "inevitable frustrated
template".

For each config we build the signed graph G_J, find all frustrated triangles
(length-3 cycles with odd number of negative edges), map each triangle from edge-indices
to the frozenset of its 3 geometric (u,v) edge-pairs, then intersect across configs.
"""
import sys, os, json, itertools
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J
from solver_2factor_sat_pipeline import enumerate_clauses


def frustrated_triangles_geometric(m, edge_list):
    """Return (set_of_frozenset_of_3_(u,v)_pairs, count)."""
    edges = [tuple(sorted(e)) for e in edge_list]
    coord = {i: edges[i] for i in range(len(edges))}  # edge index -> (u,v)
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, _, _ = build_J(clauses)
    # signed adjacency
    adj = defaultdict(dict)
    for (i, j), v in J.items():
        if v == 0:
            continue
        sgn = 1 if v > 0 else -1
        adj[i][j] = sgn
        adj[j][i] = sgn
    # enumerate triangles among edge-indices
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
    # frustrated = odd number of negative signs among the 3 edges
    fr = set()
    for (i, j, k) in tris:
        s = adj[i][j] * adj[j][k] * adj[i][k]
        if s < 0:
            fr.add(frozenset({coord[i], coord[j], coord[k]}))
    return fr, len(tris)


def load(m, path):
    d = json.load(open(path))
    if m == 36:
        return [tuple(sorted(c)) for c in d["cells"]]
    out = []
    for x in d["edges"]:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            out.append((x[0], x[1]))
        elif isinstance(x, int):
            out.append((x, x))
    return out


def main():
    configs = {
        "m37_408": (37, "results/config_408_edges.json"),
        "m37_448": (37, "results/mutation_448_satchk.json"),
    }
    frs = {}
    for name, (m, p) in configs.items():
        el = load(m, p)
        fr, ntri = frustrated_triangles_geometric(m, el)
        frs[name] = fr
        print(f"{name}: {ntri} triangles, {len(fr)} frustrated (geometric)", flush=True)

    # intersection
    common = set.intersection(*frs.values())
    print(f"\nGEOMETRIC frustrated-triangle intersection across "
          f"{len(frs)} configs: {len(common)} triangles", flush=True)
    # also pairwise jaccard-like
    names = list(frs.keys())
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            na, nb = names[a], names[b]
            inter = frs[na] & frs[nb]
            union = frs[na] | frs[nb]
            print(f"  {na} ∩ {nb}: {len(inter)} common / "
                  f"union {len(union)} (Jaccard={len(inter)/max(1,len(union)):.3f})", flush=True)

    # report a few common triangles
    common_list = [sorted(t) for t in common]
    print("\nSample common frustrated triangles (geometric (u,v) edges):")
    for t in common_list[:12]:
        print("   ", t)

    out = {
        "per_config_frustrated_triangles": {k: len(v) for k, v in frs.items()},
        "geometric_intersection_size": len(common),
        "sample_common": common_list[:20],
    }
    json.dump(out, open("results/template_intersection.json", "w"), indent=2)
    print("\nsaved results/template_intersection.json")


if __name__ == "__main__":
    main()

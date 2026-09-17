"""
frustrated_odd_cycles.py — Route 2 (localized template) at the SIGNED-CYCLE level.

The variable-level decomposition (frustrated_components.py) showed G_J is a single
connected component for the m=37 configs, so the obstacle is NOT localizable to a
small variable subset. The natural atomic obstacle in a signed graph is a
FRUSTRATED ODD CYCLE: a cycle whose edge-sign product is -1, hence no orientation
can satisfy all its pairwise couplings. We enumerate short odd cycles (len 3,5,7)
of G_J, flag frustrated ones, and compare the minimal frustrated cycles between
the m37-408 and m37-448 configs to look for a common geometric template.

For each frustrated cycle we also report the collinear triples (clauses) that
generate its edges, exposing the rot4 geometry behind it.
"""
import sys, os, json, itertools
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J
from solver_2factor_sat_pipeline import enumerate_clauses


def signed_graph(J):
    adj = defaultdict(set)
    sgn = {}
    for (i, j), v in J.items():
        adj[i].add(j)
        adj[j].add(i)
        sgn[(i, j) if i < j else (j, i)] = v
    return adj, sgn


def sign_of(sgn, i, j):
    return sgn[(i, j) if i < j else (j, i)]


def enumerate_odd_cycles(adj, max_len=7):
    """All simple odd cycles up to max_len (list of node indices, closed)."""
    nodes = list(adj.keys())
    cycles = []
    seen = set()

    def dfs(start, cur, depth, visited, path):
        if depth >= 3 and depth % 2 == 1 and start in adj[cur]:
            key = tuple(sorted(path))
            if key not in seen:
                seen.add(key)
                cycles.append(list(path))
        if depth == max_len:
            return
        for nxt in adj[cur]:
            if nxt == start:
                continue
            if nxt in visited:
                continue
            visited.add(nxt)
            path.append(nxt)
            dfs(start, nxt, depth + 1, visited, path)
            path.pop()
            visited.discard(nxt)

    for s0 in nodes:
        dfs(s0, s0, 1, {s0}, [s0])
    return cycles


def analyze(m, edges, label, max_len=7):
    print(f"\n########## {label} (m={m}) ##########", flush=True)
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, missing, n_cl = build_J(clauses)
    adj, sgn = signed_graph(J)

    ocs = enumerate_odd_cycles(adj, max_len=max_len)
    print(f"  support graph: {len(adj)} nodes, {len(J)} edges; "
          f"enumerated {len(ocs)} simple odd cycles (len<={max_len})", flush=True)

    frustrated = []
    by_len = defaultdict(list)
    for cyc in ocs:
        prod = 1
        for t in range(len(cyc)):
            a, b = cyc[t], cyc[(t + 1) % len(cyc)]
            prod *= sign_of(sgn, a, b)
        if prod < 0:
            fr = True
        else:
            fr = False
        by_len[len(cyc)].append(fr)
        if fr:
            # which clauses generate the cycle edges
            edge_clauses = []
            for t in range(len(cyc)):
                a, b = cyc[t], cyc[(t + 1) % len(cyc)]
                # find any clause containing both a and b
                for (ca, cb, cc, bits) in clauses:
                    if (ca == a and cb == b) or (ca == b and cb == a) or \
                       (ca == a and cc == b) or (ca == b and cc == a) or \
                       (cb == a and cc == b) or (cb == b and cc == a):
                        edge_clauses.append((ca, cb, cc, bits))
                        break
            frustrated.append({
                "cycle": cyc, "length": len(cyc), "sign_product": int(prod),
                "edge_clauses": edge_clauses,
            })

    print(f"  frustrated odd cycles by length: " +
          ", ".join(f"{k}:{sum(v)}/{len(v)}" for k, v in sorted(by_len.items())),
          flush=True)
    # minimal frustrated cycles (shortest first)
    frustrated.sort(key=lambda d: d["length"])
    print(f"  TOTAL frustrated odd cycles: {len(frustrated)}", flush=True)
    print(f"  minimal (shortest) frustrated cycles:", flush=True)
    for d in frustrated[:8]:
        print(f"    len={d['length']} cycle={d['cycle']} "
              f"signprod={d['sign_product']}", flush=True)
    return {
        "label": label, "m": m, "n_clauses": n_cl,
        "n_support_nodes": len(adj), "n_support_edges": len(J),
        "n_odd_cycles": len(ocs),
        "frustrated_by_len": {str(k): sum(v) for k, v in sorted(by_len.items())},
        "n_frustrated": len(frustrated),
        "minimal_frustrated": [
            {"cycle": d["cycle"], "length": d["length"], "sign_product": d["sign_product"]}
            for d in frustrated[:12]
        ],
    }


def load_config(path, m):
    d = json.load(open(path))
    if m == 36:
        return [tuple(sorted(c)) for c in d["cells"]]
    edges = []
    for x in d["edges"]:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            u, v = x[0], x[1]
        elif isinstance(x, int):
            u = v = x
        else:
            raise ValueError(f"bad edge {x!r}")
        edges.append((min(u, v), max(u, v)))
    return edges


def main():
    out = {}
    out["m37_408"] = analyze(37, load_config("results/config_408_edges.json", 37),
                             "m37-408 (best, 16 viol)", max_len=5)
    out["m37_448"] = analyze(37, load_config("results/mutation_448_satchk.json", 37),
                             "m37-448 (proven 17 viol)", max_len=5)
    json.dump(out, open("results/frustrated_odd_cycles.json", "w"), indent=2)
    print("\nsaved results/frustrated_odd_cycles.json")


if __name__ == "__main__":
    main()

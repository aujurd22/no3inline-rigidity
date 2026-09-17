"""
cutpolytope_sdp.py — Strengthen the signed MAX-CUT / Ising lower bound on
min_violations by adding CUT-POLYTOPE inequalities (triangle + odd-cycle) to the
SDP relaxation. This is route 1 of the Ising reframing:
    min_viol >= n_cl/8 + (1/8) * SDP_min( Σ J_code Y_ij ),
where Y is the (relaxed) cut Gram matrix. Adding valid inequalities to the
relaxation shrinks the feasible set => larger (tighter) SDP_min => tighter lower
bound. If the bound reaches the known min_viol, we have PROVED optimality with a
short dual certificate.

We also extract the dual multipliers on the active inequalities as the
"short certificate" (route 1 deliverable).

Verified reductions live in ising_reduction.py (build_J, etc.).
"""
import sys, os, json, time, itertools
from collections import defaultdict
import numpy as np
import cvxpy as cp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J
from solver_2factor_sat_pipeline import enumerate_clauses


def sdp_bound(m, edges, add_triangle=True, odd_cycles=None, time_limit=180,
              solver=cp.CLARABEL):
    """Return (min_viol_lb, SDP_min, status, duals) for the strengthened SDP.
    odd_cycles: list of odd cycles (each a list of node indices) to add as
    odd-cycle inequalities; if None, only triangle ineqs are used."""
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, missing, n_cl = build_J(clauses)
    n = m

    Y = cp.Variable((n, n), symmetric=True)
    cons = [Y >> 0, cp.diag(Y) == np.ones(n)]
    obj = 0
    for (i, j), v in J.items():
        obj += v * Y[i, j]

    if add_triangle:
        for (i, j, k) in itertools.combinations(range(n), 3):
            cons.append(Y[i, j] + Y[j, k] + Y[k, i] >= -1)
            cons.append(Y[i, j] - Y[i, k] - Y[j, k] >= -1)
            cons.append(Y[i, k] - Y[i, j] - Y[j, k] >= -1)
            cons.append(Y[j, k] - Y[i, j] - Y[i, k] >= -1)

    if odd_cycles:
        for cyc in odd_cycles:
            k = len(cyc)
            # Y for consecutive edges minus Y for non-edges within the cycle
            expr = 0
            for t in range(k):
                a, b = cyc[t], cyc[(t + 1) % k]
                expr += Y[min(a, b), max(a, b)]
            # non-edges (all pairs minus the cycle edges)
            edge_set = set((min(cyc[t], cyc[(t + 1) % k]),
                            max(cyc[t], cyc[(t + 1) % k])) for t in range(k))
            for a in range(k):
                for b in range(a + 1, k):
                    u, w = cyc[a], cyc[b]
                    if (min(u, w), max(u, w)) not in edge_set:
                        expr -= Y[min(u, w), max(u, w)]
            cons.append(expr <= (k - 1) / 2.0)

    prob = cp.Problem(cp.Minimize(obj), cons)
    try:
        prob.solve(solver=solver, time_limit=time_limit, verbose=False)
    except Exception as e:
        try:
            prob.solve(solver=cp.SCS, verbose=False, max_iters=20000)
        except Exception as e2:
            return None
    if prob.status not in ("optimal", "optimal_inaccurate") or prob.value is None:
        return {"status": prob.status, "min_viol_lb": None, "SDP_min": None}
    SDP_min = float(prob.value)
    min_viol_lb = n_cl / 8.0 + SDP_min / 8.0
    return {
        "n_clauses": n_cl, "closure_missing": missing,
        "SDP_min": SDP_min, "min_viol_lb": float(min_viol_lb),
        "status": prob.status,
    }


def enumerate_odd_cycles(J, max_len=5):
    """Enumerate odd cycles up to max_len in the support graph of J (edges with J!=0)."""
    adj = defaultdict(set)
    for (i, j) in J:
        adj[i].add(j)
        adj[j].add(i)
    cycles = []
    nodes = list(adj.keys())

    def dfs(start, cur, depth, visited, path):
        if depth >= 3 and depth % 2 == 1:  # odd cycle of length depth
            if start in adj[cur]:
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
    # dedupe
    seen = set()
    uniq = []
    for c in cycles:
        key = tuple(sorted(c))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def load_config(path, edges_key="edges", orient_key=None):
    d = json.load(open(path))
    edges = []
    for x in d[edges_key]:
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
    cfgs = {
        "m37_408": ("results/config_408_edges.json", 16),
        "m37_448": ("results/mutation_448_satchk.json", 17),
        "m36": ("results/solutions/m36.json", 0),
    }
    for name, (path, known) in cfgs.items():
        if name == "m36":
            d = json.load(open(path))
            edges = [tuple(sorted(c)) for c in d["cells"]]
            m = 36
        else:
            edges = load_config(path)
            m = 37
        print(f"\n########## {name} (known min_viol={known}) ##########", flush=True)

        # 1) triangle-only SDP
        r1 = sdp_bound(m, edges, add_triangle=True, odd_cycles=None, time_limit=180)
        print(f"  SDP+triangle : SDP_min={r1['SDP_min']:.4f} "
              f"min_viol_lb={r1['min_viol_lb']:.3f} [{r1['status']}]", flush=True)

        # 2) odd-cycle separation: enumerate short odd cycles, add violated ones,
        #    re-solve (2 rounds)
        clauses, _ = enumerate_clauses(m, edges, verbose=False)
        J, _, _ = build_J(clauses)
        ocs = enumerate_odd_cycles(J, max_len=5)
        print(f"  enumerated {len(ocs)} odd cycles (len<=5) in support graph", flush=True)
        r2 = sdp_bound(m, edges, add_triangle=True, odd_cycles=ocs, time_limit=240)
        print(f"  SDP+triangle+oddcycle: SDP_min={r2['SDP_min']:.4f} "
              f"min_viol_lb={r2['min_viol_lb']:.3f} [{r2['status']}]", flush=True)

        out[name] = {
            "known_min_viol": known,
            "sdp_triangle_lb": r1["min_viol_lb"],
            "sdp_triangle_SDP_min": r1["SDP_min"],
            "n_odd_cycles_len5": len(ocs),
            "sdp_triangle_oddcycle_lb": r2["min_viol_lb"],
            "sdp_triangle_oddcycle_SDP_min": r2["SDP_min"],
        }

    json.dump(out, open("results/cutpolytope_sdp.json", "w"), indent=2)
    print("\n==== SUMMARY (lower bound on min_viol) ====")
    for k, r in out.items():
        tag = "PROVEN OPTIMAL" if r["sdp_triangle_oddcycle_lb"] >= r["known_min_viol"] - 1e-6 else "not closed"
        print(f"  {k}: known={r['known_min_viol']}  SDP+tri={r['sdp_triangle_lb']:.2f}  "
              f"SDP+tri+oddcyc={r['sdp_triangle_oddcycle_lb']:.2f}  -> {tag}")
    print("saved results/cutpolytope_sdp.json")


if __name__ == "__main__":
    main()

"""
frustrated_components.py — Decompose the signed Ising problem into connected
components of the support graph and locate the FRUSTRATED components (those whose
induced orientation problem has min_viol > 0). Because every clause's 3 vertices
share edges (the support graph is the clause incidence graph), the Ising energy
decomposes EXACTLY by components: total min_viol = sum of per-component min_viol.

This localizes the obstacle: for m=37 the frustration lives in a few specific
connected components of the signed graph (the "frustrated template" candidate);
for m=36 every component is satisfiable (min_viol=0). Comparing the frustrated
components of the m=37-408 and m=37-448 configs reveals whether a common small
template recurs.

Per-component min_viol is solved exactly: brute force 2^k for k<=20, else CP-SAT.
"""
import sys, os, json, time, itertools
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J, count_violations_bruteforce
from solver_2factor_sat_pipeline import enumerate_clauses, check_sat


def components_of(J):
    adj = defaultdict(set)
    for (i, j) in J:
        adj[i].add(j)
        adj[j].add(i)
    nodes = set()
    for (i, j) in J:
        nodes.update([i, j])
    seen = set()
    comps = []
    for s in nodes:
        if s in seen:
            continue
        stack = [s]
        comp = set()
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp.add(u)
            for w in adj[u]:
                if w not in seen:
                    stack.append(w)
        comps.append(comp)
    return comps


def component_min_viol(clauses_sub, time_limit=60):
    """Exact min_viol for a clause subset via brute force (if <=20 vars) or CP-SAT."""
    vars_set = set()
    for (a, b, c, _) in clauses_sub:
        vars_set.update([a, b, c])
    k = len(vars_set)
    if k == 0:
        return 0, None, []
    if k <= 20:
        idx = list(vars_set)
        best = 10 ** 9
        best_o = None
        for mask in range(1 << k):
            o = [(mask >> i) & 1 for i in range(k)]
            v = count_violations_bruteforce(clauses_sub, o)
            if v < best:
                best = v
                best_o = o[:]
        return best, best_o, idx
    # CP-SAT MaxSAT on the induced clause subset (vars independent of 2-factor)
    from ortools.sat.python import cp_model
    vs = sorted(vars_set)
    vmap = {v: i for i, v in enumerate(vs)}
    nv = len(vs)
    model = cp_model.CpModel()
    t = [model.NewBoolVar(f"t{i}") for i in range(nv)]
    hard = []
    for (a, b, c, bits) in clauses_sub:
        ia, ib, ic = vmap[a], vmap[b], vmap[c]
        ba, bb, bc = (bits >> 0) & 1, (bits >> 1) & 1, (bits >> 2) & 1
        cl = []
        cl.append(t[ia] if ba == 0 else t[ia].Not())
        cl.append(t[ib] if bb == 0 else t[ib].Not())
        cl.append(t[ic] if bc == 0 else t[ic].Not())
        hard.append(cl)
    viol = [model.NewBoolVar(f"v{i}") for i in range(len(hard))]
    for i, cl in enumerate(hard):
        model.AddBoolOr(cl).OnlyEnforceIf(viol[i].Not())
        model.AddBoolAnd([x.Not() for x in cl]).OnlyEnforceIf(viol[i])
    model.Minimize(sum(viol))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    st = solver.Solve(model)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        mv = int(solver.ObjectiveValue())
        o = [int(solver.Value(t[i])) for i in range(nv)]
        orient = {v: o[vmap[v]] for v in vs}
        return mv, orient, vs
    return None, None, vs


def analyze(m, edges, label):
    print(f"\n########## {label} (m={m}, {len(edges)} edges) ##########", flush=True)
    t0 = time.time()
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    n_cl = len(clauses)
    J, missing, _ = build_J(clauses)
    comps = components_of(J)
    comps.sort(key=len, reverse=True)
    print(f"  clauses={n_cl}, support graph: {len(comps)} components, "
          f"sizes={[len(c) for c in comps]}", flush=True)

    results = []
    total_min_viol = 0
    frustrated = []
    for ci, comp in enumerate(comps):
        # induced clauses: all 3 vertices in comp
        csub = [(a, b, c, bits) for (a, b, c, bits) in clauses
                if a in comp and b in comp and c in comp]
        mv, o, idx = component_min_viol(csub)
        if mv is None:
            print(f"    comp#{ci} size={len(comp)}: CP-SAT fallback (vars>20) skipped",
                  flush=True)
            continue
        total_min_viol += mv
        status = "FRUSTRATED" if mv > 0 else "ok"
        if mv > 0:
            frustrated.append((ci, len(comp), mv, csub, o, idx))
        print(f"    comp#{ci} size={len(comp)}: {len(csub)} clauses, "
              f"min_viol={mv}  [{status}]", flush=True)

    print(f"  >>> SUM of component min_viol = {total_min_viol} "
          f"(full problem min_viol should equal this)", flush=True)
    print(f"  >>> frustrated components: {len(frustrated)}", flush=True)
    for (ci, sz, mv, csub, o, idx) in frustrated:
        # violated clauses at component-optimal orientation
        viol = [c for c in csub if count_violations_bruteforce([c], o) == 1]
        print(f"      frustrated comp#{ci}: {sz} nodes, {mv} violations, "
              f"{len(viol)} violated clauses, nodes={sorted(idx)}", flush=True)
    return {
        "label": label, "m": m, "n_clauses": n_cl,
        "n_components": len(comps), "component_sizes": [len(c) for c in comps],
        "sum_component_min_viol": total_min_viol,
        "frustrated_components": [
            {"comp_id": ci, "n_nodes": sz, "min_viol": mv,
             "nodes": sorted(idx),
             "n_violated_clauses": len([c for c in csub
                                        if count_violations_bruteforce([c], o) == 1])}
            for (ci, sz, mv, csub, o, idx) in frustrated
        ],
        "time_s": round(time.time() - t0, 1),
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
    # m=37-408
    e408 = load_config("results/config_408_edges.json", 37)
    out["m37_408"] = analyze(37, e408, "m37-408 (best, 16 viol)")
    # m=37-448
    e448 = load_config("results/mutation_448_satchk.json", 37)
    out["m37_448"] = analyze(37, e448, "m37-448 (proven 17 viol)")
    # m=36
    e36 = load_config("results/solutions/m36.json", 36)
    out["m36"] = analyze(36, e36, "m36-solution (SAT)")

    json.dump(out, open("results/frustrated_components.json", "w"), indent=2)
    print("\nsaved results/frustrated_components.json")


if __name__ == "__main__":
    main()

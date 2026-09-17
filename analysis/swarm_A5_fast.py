#!/usr/bin/env python
"""
swarm_A5_fast.py — Fast targeted analysis: 
- Test 20 random m=36 2-factors (clause enumeration + SAT)
- Test m=36 2-factors with specific span distributions
- Compare clause structure across both m values
"""
import sys, json, math, time, random, os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b: a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]; dy = q[1] - p[1]
    if dx == 0 and dy == 0: return (0, 0, 0)
    g = igcd(abs(dx), abs(dy))
    A, B = dy // g, -dx // g
    if A < 0 or (A == 0 and B < 0): A, B = -A, -B
    return (A, B, A * p[0] + B * p[1])

def c4_lift(x, y, n):
    pts = [(x, y)]
    for _ in range(3):
        x, y = n - 1 - y, x
        pts.append((x, y))
    return pts

def generate_2factor(m, rng):
    perm = list(range(m))
    rng.shuffle(perm)
    visited = [False] * m
    edges = []
    for i in range(m):
        if not visited[i]:
            cycle = []
            j = i
            while not visited[j]:
                visited[j] = True
                cycle.append(j)
                j = perm[j]
            for k in range(len(cycle)):
                a, b = cycle[k], cycle[(k + 1) % len(cycle)]
                u, v = (a, b) if a <= b else (b, a)
                edges.append((u, v))
    return sorted(edges)

def enumerate_clauses(m, edges):
    n = 2 * m
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        cell_lifts[(idx, 0)] = c4_lift(u, v, n)
        cell_lifts[(idx, 1)] = c4_lift(v, u, n) if u != v else c4_lift(u, v, n)
    E = len(edges)
    clauses = []
    for a in range(E):
        for b in range(a + 1, E):
            for c in range(b + 1, E):
                for bits in range(8):
                    t1 = (bits >> 0) & 1; t2 = (bits >> 1) & 1; t3 = (bits >> 2) & 1
                    lifts = cell_lifts[(a, t1)] + cell_lifts[(b, t2)] + cell_lifts[(c, t3)]
                    bad = False
                    for i in range(12):
                        if bad: break
                        pi = lifts[i]
                        for j in range(i + 1, 12):
                            pj = lifts[j]
                            if pi[0] == pj[0] and pi[1] == pj[1]: continue
                            k0 = line_of(pi, pj)
                            cnt = 2
                            for k in range(12):
                                if k == i or k == j: continue
                                pk = lifts[k]
                                if pk[0] == pi[0] and pk[1] == pi[1]: continue
                                if line_of(pi, pk) == k0:
                                    cnt += 1
                                    if cnt >= 3: bad = True; break
                    if bad:
                        clauses.append((a, b, c, bits))
    return clauses

def check_sat(m, edges, clauses, time_limit=30):
    sys.path.insert(0, "C:/Users/djr82/.workbuddy/binaries/python/envs/default/Lib/site-packages")
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    t = [model.NewBoolVar(f"t_{i}") for i in range(m)]
    for a, b, c, bits in clauses:
        b0 = (bits >> 0) & 1; b1 = (bits >> 1) & 1; b2 = (bits >> 2) & 1
        lit0 = t[a] if b0 == 0 else t[a].Not()
        lit1 = t[b] if b1 == 0 else t[b].Not()
        lit2 = t[c] if b2 == 0 else t[c].Not()
        model.AddBoolOr(lit0, lit1, lit2)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    start = time.time()
    status = solver.Solve(model)
    t_sat = time.time() - start
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        sol_bits = [int(solver.Value(t[i])) for i in range(m)]
        return {"status": "SAT", "orientation": sol_bits, "time": round(t_sat, 3)}
    # MaxSAT
    model2 = cp_model.CpModel()
    t2 = [model2.NewBoolVar(f"t_{i}") for i in range(m)]
    viol = [model2.NewBoolVar(f"v_{i}") for i in range(len(clauses))]
    for ci, (a, b, c, bits) in enumerate(clauses):
        b0 = (bits >> 0) & 1; b1 = (bits >> 1) & 1; b2 = (bits >> 2) & 1
        lit0 = t2[a] if b0 == 0 else t2[a].Not()
        lit1 = t2[b] if b1 == 0 else t2[b].Not()
        lit2 = t2[c] if b2 == 0 else t2[c].Not()
        model2.AddBoolOr(lit0, lit1, lit2, viol[ci])
    model2.Minimize(sum(viol))
    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = time_limit
    solver2.parameters.num_search_workers = 1
    start2 = time.time()
    status2 = solver2.Solve(model2)
    t_maxsat = time.time() - start2
    n_violated = sum(int(solver2.Value(v)) for v in viol)
    return {"status": "UNSAT", "min_violations": n_violated,
            "proven_optimal": status2 == cp_model.OPTIMAL, "time": round(t_sat + t_maxsat, 3)}

def span_hist(edges, m):
    return Counter(min(abs(u-v), m-abs(u-v)) for u, v in edges)

# ── Main ──
random.seed(42)
rng = random.Random(42)

# Load m=36 solution
with open(f"{HERE}/results/solutions/m36.json") as f:
    m36_data = json.load(f)
edges_m36_sol = [tuple(sorted(c)) for c in m36_data['cells']]

# Load m=37 best72
with open(f"{HERE}/results/swarm_D1_2_best72_clauses.json") as f:
    m37_data = json.load(f)
edges_m37_best = [tuple(e) for e in m37_data['edges']]

results = {
    "m36_solution": {"edges": edges_m36_sol, "type": "known_solution"},
    "m37_best72": {"edges": edges_m37_best, "type": "best72"},
    "m36_random": [],
}

# 1. m=36 solution
print("=== m=36 solution ===")
t0 = time.time()
cl = enumerate_clauses(36, edges_m36_sol)
t1 = time.time()
print(f"  {len(cl)} clauses in {t1-t0:.1f}s")
res = check_sat(36, edges_m36_sol, cl, time_limit=30)
print(f"  SAT check: {res['status']} (t={res.get('time',0)}s)")
results["m36_solution"]["n_clauses"] = len(cl)
results["m36_solution"]["sat"] = res
results["m36_solution"]["span_hist"] = dict(sorted(span_hist(edges_m36_sol, 36).items()))
results["m36_solution"]["enum_time"] = round(t1-t0, 1)

# 2. m=37 best72
print("\n=== m=37 best72 ===")
t0 = time.time()
cl = enumerate_clauses(37, edges_m37_best)
t1 = time.time()
print(f"  {len(cl)} clauses in {t1-t0:.1f}s")
res = check_sat(37, edges_m37_best, cl, time_limit=30)
print(f"  SAT check: {res['status']} (min_viol={res.get('min_violations',0)}, t={res.get('time',0)}s)")
results["m37_best72"]["n_clauses"] = len(cl)
results["m37_best72"]["sat"] = res
results["m37_best72"]["span_hist"] = dict(sorted(span_hist(edges_m37_best, 37).items()))
results["m37_best72"]["enum_time"] = round(t1-t0, 1)

# 3. 10 random m=36 2-factors
print("\n=== 10 random m=36 2-factors ===")
for trial in range(10):
    edges = generate_2factor(36, rng)
    t0 = time.time()
    cl = enumerate_clauses(36, edges)
    t1 = time.time()
    print(f"  Trial {trial}: {len(cl)} clauses in {t1-t0:.1f}s", end="", flush=True)
    res = check_sat(36, edges, cl, time_limit=30)
    print(f" → {res['status']} (mv={res.get('min_violations','-')}, t={res.get('time',0):.1f}s)")
    results["m36_random"].append({
        "trial": trial, "n_clauses": len(cl), "sat": res,
        "span_hist": dict(sorted(span_hist(edges, 36).items())),
        "enum_time": round(t1-t0, 1)
    })

# 4. 5 random m=37 2-factors for comparison
print("\n=== 5 random m=37 2-factors ===")
results["m37_random"] = []
for trial in range(5):
    edges = generate_2factor(37, rng)
    t0 = time.time()
    cl = enumerate_clauses(37, edges)
    t1 = time.time()
    print(f"  Trial {trial}: {len(cl)} clauses in {t1-t0:.1f}s", end="", flush=True)
    res = check_sat(37, edges, cl, time_limit=30)
    print(f" → {res['status']} (mv={res.get('min_violations','-')}, t={res.get('time',0):.1f}s)")
    results["m37_random"].append({
        "trial": trial, "n_clauses": len(cl), "sat": res,
        "span_hist": dict(sorted(span_hist(edges, 37).items())),
        "enum_time": round(t1-t0, 1)
    })

# 5. Analysis summary
print("\n\n=== SUMMARY ===")
print(f"m=36 solution: {results['m36_solution']['n_clauses']} clauses → {results['m36_solution']['sat']['status']}")
print(f"m=37 best72: {results['m37_best72']['n_clauses']} clauses → {results['m37_best72']['sat']['status']} (mv={results['m37_best72']['sat'].get('min_violations','-')})")

for label, key in [("m=36 rand", "m36_random"), ("m=37 rand", "m37_random")]:
    items = results[key]
    if items:
        clauses_list = [r["n_clauses"] for r in items]
        sat_list = [r["sat"]["status"] for r in items]
        print(f"\n{label} ({len(items)} trials):")
        print(f"  Clause counts: min={min(clauses_list)}, max={max(clauses_list)}, mean={sum(clauses_list)/len(clauses_list):.0f}")
        print(f"  SAT count: {sat_list.count('SAT')}/{len(items)}")

# Save
with open(f"{HERE}/results/swarm_A5_fast_data.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nData saved to results/swarm_A5_fast_data.json")

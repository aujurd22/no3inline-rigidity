#!/usr/bin/env python
"""
Fast scan: enumerate clauses for random 2-factors, then SAT on promising ones.
Self-contained (no imports from other project files).
"""
import sys, json, math, time, random, os
from collections import Counter

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
    perm = list(range(m)); rng.shuffle(perm)
    visited = [False] * m; edges = []
    for i in range(m):
        if not visited[i]:
            cycle = []; j = i
            while not visited[j]:
                visited[j] = True; cycle.append(j); j = perm[j]
            for k in range(len(cycle)):
                a, b = cycle[k], cycle[(k+1)%len(cycle)]
                edges.append((a, b) if a <= b else (b, a))
    return sorted(edges)

def count_clauses(m, edges):
    """Just count clauses, don't store them."""
    n = 2*m; E = len(edges)
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        cell_lifts[(idx,0)] = c4_lift(u, v, n)
        cell_lifts[(idx,1)] = c4_lift(v, u, n) if u != v else c4_lift(u, v, n)
    count = 0
    for a in range(E):
        for b in range(a+1, E):
            for c in range(b+1, E):
                for bits in range(8):
                    t1 = bits&1; t2 = (bits>>1)&1; t3 = (bits>>2)&1
                    lifts = cell_lifts[(a,t1)] + cell_lifts[(b,t2)] + cell_lifts[(c,t3)]
                    bad = False
                    for i in range(12):
                        if bad: break
                        pi = lifts[i]
                        for j in range(i+1, 12):
                            pj = lifts[j]
                            if pi[0]==pj[0] and pi[1]==pj[1]: continue
                            k0 = line_of(pi, pj)
                            cnt = 2
                            for k in range(12):
                                if k==i or k==j: continue
                                pk = lifts[k]
                                if pk[0]==pi[0] and pk[1]==pi[1]: continue
                                if line_of(pi, pk) == k0:
                                    cnt += 1
                                    if cnt >= 3: bad = True; break
                    if bad: count += 1
    return count

def enumerate_clauses(m, edges):
    """Return clause list for SAT check."""
    n = 2*m; E = len(edges)
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        cell_lifts[(idx,0)] = c4_lift(u, v, n)
        cell_lifts[(idx,1)] = c4_lift(v, u, n) if u != v else c4_lift(u, v, n)
    clauses = []
    for a in range(E):
        for b in range(a+1, E):
            for c in range(b+1, E):
                for bits in range(8):
                    t1 = bits&1; t2 = (bits>>1)&1; t3 = (bits>>2)&1
                    lifts = cell_lifts[(a,t1)] + cell_lifts[(b,t2)] + cell_lifts[(c,t3)]
                    bad = False
                    for i in range(12):
                        if bad: break
                        pi = lifts[i]
                        for j in range(i+1, 12):
                            pj = lifts[j]
                            if pi[0]==pj[0] and pi[1]==pj[1]: continue
                            k0 = line_of(pi, pj)
                            cnt = 2
                            for k in range(12):
                                if k==i or k==j: continue
                                pk = lifts[k]
                                if pk[0]==pi[0] and pk[1]==pi[1]: continue
                                if line_of(pi, pk) == k0:
                                    cnt += 1
                                    if cnt >= 3: bad = True; break
                    if bad: clauses.append((a,b,c,bits))
    return clauses

def check_sat(m, edges, clauses, time_limit=60):
    sys.path.insert(0, "C:/Users/djr82/.workbuddy/binaries/python/envs/default/Lib/site-packages")
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    t = [model.NewBoolVar(f"t_{i}") for i in range(m)]
    for a,b,c,bits in clauses:
        b0 = bits&1; b1 = (bits>>1)&1; b2 = (bits>>2)&1
        lit0 = t[a] if b0==0 else t[a].Not()
        lit1 = t[b] if b1==0 else t[b].Not()
        lit2 = t[c] if b2==0 else t[c].Not()
        model.AddBoolOr(lit0, lit1, lit2)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        sol_bits = [int(solver.Value(t[i])) for i in range(m)]
        return {"status": "SAT", "orientation": sol_bits}
    model2 = cp_model.CpModel()
    t2 = [model2.NewBoolVar(f"t_{i}") for i in range(m)]
    viol = [model2.NewBoolVar(f"v_{i}") for i in range(len(clauses))]
    for ci,(a,b,c,bits) in enumerate(clauses):
        b0 = bits&1; b1 = (bits>>1)&1; b2 = (bits>>2)&1
        lit0 = t2[a] if b0==0 else t2[a].Not()
        lit1 = t2[b] if b1==0 else t2[b].Not()
        lit2 = t2[c] if b2==0 else t2[c].Not()
        model2.AddBoolOr(lit0, lit1, lit2, viol[ci])
    model2.Minimize(sum(viol))
    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = 30
    solver2.parameters.num_search_workers = 1
    status2 = solver2.Solve(model2)
    n_violated = sum(int(solver2.Value(v)) for v in viol)
    return {"status": "UNSAT", "min_violations": n_violated,
            "proven_optimal": status2 == cp_model.OPTIMAL}

# ── Main ──
HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(42)

# Load known edges
with open(f"{HERE}/results/solutions/m36.json") as f:
    m36d = json.load(f)
edges_m36_sol = [tuple(sorted(c)) for c in m36d['cells']]

with open(f"{HERE}/results/swarm_D1_2_best72_clauses.json") as f:
    m37d = json.load(f)
edges_m37_best = [tuple(e) for e in m37d['edges']]

print("=== Phase 1: Enumerate 30 random m=36 2-factors ===")
m36_counts = []
for t in range(30):
    edges = generate_2factor(36, rng)
    t0 = time.time(); nc = count_clauses(36, edges); t1 = time.time()
    m36_counts.append((nc, edges, t))
    print(f"  T{t}: {nc} clauses ({t1-t0:.1f}s)", flush=True)

vals_m36 = sorted([nc for nc,_,_ in m36_counts])
print(f"\nm=36: min={vals_m36[0]}, max={vals_m36[-1]}, mean={sum(vals_m36)/30:.0f}, median={vals_m36[14]}")
print(f"Known solution: 670 clauses")

print("\n=== Phase 2: Enumerate 15 random m=37 2-factors ===")
m37_counts = []
for t in range(15):
    edges = generate_2factor(37, rng)
    t0 = time.time(); nc = count_clauses(37, edges); t1 = time.time()
    m37_counts.append((nc, edges, t))
    print(f"  T{t}: {nc} clauses ({t1-t0:.1f}s)", flush=True)

vals_m37 = sorted([nc for nc,_,_ in m37_counts])
print(f"\nm=37: min={vals_m37[0]}, max={vals_m37[-1]}, mean={sum(vals_m37)/15:.0f}, median={vals_m37[7]}")
print(f"Known best72: 470 clauses")

print("\n=== Phase 3: SAT on selected 2-factors ===")

# Known solution
print("\n--- m=36 solution ---")
t0 = time.time(); cl = enumerate_clauses(36, edges_m36_sol); t1 = time.time()
res = check_sat(36, edges_m36_sol, cl)
print(f"  {len(cl)} clauses (enum {t1-t0:.1f}s) → {res['status']}", flush=True)

# Known best72
print("\n--- m=37 best72 ---")
t0 = time.time(); cl = enumerate_clauses(37, edges_m37_best); t1 = time.time()
res = check_sat(37, edges_m37_best, cl)
print(f"  {len(cl)} clauses (enum {t1-t0:.1f}s) → {res['status']} (mv={res.get('min_violations','-')})", flush=True)

# Top 3 lowest-clause m=36 randoms
for nc, edges, tr in sorted(m36_counts, key=lambda x: x[0])[:3]:
    print(f"\n--- m=36 random #{tr} ({nc} clauses) ---")
    t0 = time.time(); cl = enumerate_clauses(36, edges); t1 = time.time()
    res = check_sat(36, edges, cl)
    print(f"  {len(cl)} clauses (enum {t1-t0:.1f}s) → {res['status']}{' (mv='+str(res.get('min_violations','-'))+')' if res['status']=='UNSAT' else ''}", flush=True)

# Top 2 lowest-clause m=37 randoms
for nc, edges, tr in sorted(m37_counts, key=lambda x: x[0])[:2]:
    print(f"\n--- m=37 random #{tr} ({nc} clauses) ---")
    t0 = time.time(); cl = enumerate_clauses(37, edges); t1 = time.time()
    res = check_sat(37, edges, cl)
    print(f"  {len(cl)} clauses (enum {t1-t0:.1f}s) → {res['status']}{' (mv='+str(res.get('min_violations','-'))+')' if res['status']=='UNSAT' else ''}", flush=True)

# Save data
data = {
    "m36_solution_nclauses": 670,
    "m37_best72_nclauses": 470,
    "m36_random_counts": [nc for nc,_,_ in m36_counts],
    "m37_random_counts": [nc for nc,_,_ in m37_counts],
    "m36_random_min": vals_m36[0],
    "m37_random_min": vals_m37[0],
    "m36_random_mean": sum(vals_m36)/30,
    "m37_random_mean": sum(vals_m37)/15,
}
with open(f"{HERE}/results/swarm_A5_scan_data.json", "w") as f:
    json.dump(data, f, indent=2)
print(f"\nData saved.")
print("Done!")

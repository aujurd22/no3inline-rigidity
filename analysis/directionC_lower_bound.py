"""
方向 C：边不交三元组覆盖下界证明尝试

从 D5v2 发现的模式出发：violations ≈ all-4-pairs / 5

检查所有已保存 2-因子的这个比率。
如果比率稳定，可以尝试证明下界。
"""
import json, time, math, os
from collections import Counter

M = 37; N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3): x, y = N - 1 - y, x; pts.append((x, y))
    return pts

all_lifts = {}
for u in range(M):
    for v in range(M):
        all_lifts[(u, v, 0)] = c4_lift(u, v)
        all_lifts[(u, v, 1)] = c4_lift(v, u) if u != v else c4_lift(u, v)

def is_collinear_12(lifts):
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i+1, 12):
            xj, yj = lifts[j]
            if xi==xj and yi==yj: continue
            dx, dy = xj-xi, yj-yi
            for k in range(j+1, 12):
                xk, yk = lifts[k]
                if xk==xi and yk==yi: continue
                if dx*(yk-yi)==dy*(xk-xi): return True
    return False

def compute_all4pairs(edges):
    """Count triples where ALL 8 orientation combos are collinear (unavoidable)."""
    count = 0
    for a in range(M):
        ea = edges[a]
        pa0 = all_lifts[(ea[0], ea[1], 0)]
        pa1 = all_lifts[(ea[0], ea[1], 1)]
        for b in range(a+1, M):
            eb = edges[b]
            pb0 = all_lifts[(eb[0], eb[1], 0)]
            pb1 = all_lifts[(eb[0], eb[1], 1)]
            for c in range(b+1, M):
                ec = edges[c]
                pc0 = all_lifts[(ec[0], ec[1], 0)]
                pc1 = all_lifts[(ec[0], ec[1], 1)]
                # Check all 8 combos
                all_bad = True
                for oa in (0, 1):
                    pa = pa0 if oa == 0 else pa1
                    for ob in (0, 1):
                        pb = pb0 if ob == 0 else pb1
                        for oc in (0, 1):
                            pc = pc0 if oc == 0 else pc1
                            if not is_collinear_12(pa + pb + pc):
                                all_bad = False
                                break
                        if not all_bad: break
                    if not all_bad: break
                if all_bad:
                    count += 1
    return count

def count_optimal_via_cpsat(edges):
    """Run CP-SAT MaxSAT to find optimal violations for a 2-factor.
    This is the gold standard."""
    from ortools.sat.python import cp_model
    
    # Enumerate all clauses
    clauses = []
    for a in range(M):
        ea = edges[a]
        pa0 = all_lifts[(ea[0], ea[1], 0)]
        pa1 = all_lifts[(ea[0], ea[1], 1)]
        for b in range(a+1, M):
            eb = edges[b]
            pb0 = all_lifts[(eb[0], eb[1], 0)]
            pb1 = all_lifts[(eb[0], eb[1], 1)]
            for c in range(b+1, M):
                ec = edges[c]
                pc0 = all_lifts[(ec[0], ec[1], 0)]
                pc1 = all_lifts[(ec[0], ec[1], 1)]
                # Check each combo
                combo_map = {}
                for oa in (0, 1):
                    pa = pa0 if oa == 0 else pa1
                    for ob in (0, 1):
                        pb = pb0 if ob == 0 else pb1
                        for oc in (0, 1):
                            pc = pc0 if oc == 0 else pc1
                            if is_collinear_12(pa + pb + pc):
                                combo_map[(oa, ob, oc)] = True
                if combo_map:
                    clauses.append((a, b, c, [k for k in combo_map.keys()]))
    
    # CP-SAT MaxSAT
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f'x_{i}') for i in range(M)]
    viol = [model.NewBoolVar(f'v_{i}') for i in range(len(clauses))]
    
    for ci, (a,b,c,combos) in enumerate(clauses):
        # violation occurs when orientation matches a bad combo
        literals = []
        for oa, ob, oc in combos:
            lit = []
            if oa == 0: lit.append(x[a].Not()) 
            else: lit.append(x[a])
            if ob == 0: lit.append(x[b].Not())
            else: lit.append(x[b])
            if oc == 0: lit.append(x[c].Not())
            else: lit.append(x[c])
            literals.append(lit)
        
        # violation = any bad combo is active
        if len(literals) == 1:
            model.AddBoolOr([viol[ci].Not()] + literals[0])
        else:
            # viol == True if any combo fires
            # For each combo: AND of its literals
            # We need: viol >= any_combo_active
            # This is: for each combo, add: literals imply viol
            for lit in literals:
                model.AddBoolOr([viol[ci].Not()] + lit)
            # Also: if no combo fires, no violation
            # This is: all combos inactive -> viol = False
            # Not needed for minimization
    
    model.Minimize(sum(viol))
    
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False
    
    status = solver.Solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return solver.ObjectiveValue(), solver.StatusName(status)
    return None, solver.StatusName(status)

# ── Known configurations to test ─────────────────────────────────
test_configs = []

# 1. config_408
with open(f"{HERE}/results/config_408_maxsat_result.json") as f:
    d = json.load(f)
test_configs.append(("config_408", [(min(u,v),max(u,v)) for u,v in d["edges"]]))

# 2. constructive_best
with open(f"{HERE}/results/constructive_best.json") as f:
    d = json.load(f)
test_configs.append(("constructive_best", d["edges"]))

# 3. best_gv_63 (from direction3)
try:
    with open(f"{HERE}/results/best_gv_63_edges.json") as f:
        d = json.load(f)
    edges = [(min(u,v),max(u,v)) for u,v in d["edges"]]
    test_configs.append(("best_gv_63", edges))
except: pass

# 4. Some mutation results
for fn in os.listdir(f"{HERE}/results/"):
    if fn.startswith("mutate_gv") and fn.endswith("_edges.json"):
        try:
            with open(f"{HERE}/results/{fn}") as f:
                d = json.load(f)
            edges = [(min(u,v),max(u,v)) for u,v in d["edges"]]
            # Verify validity
            deg = Counter()
            for u,v in edges: deg[u]+=1; deg[v]+=1
            if min(deg.values()) == 2 and max(deg.values()) == 2:
                test_configs.append((fn.replace("_edges.json",""), edges))
        except: pass

import os

print(f"Testing {len(test_configs)} configurations...\n", flush=True)

for name, edges in test_configs:
    # Verify 2-regular
    deg = Counter()
    for u,v in edges: deg[u]+=1; deg[v]+=1
    if min(deg.values()) < 2 or max(deg.values()) > 2:
        print(f"  {name}: INVALID (deg {min(deg.values())}-{max(deg.values())})", flush=True)
        continue
    
    # Compute all-4-pairs
    t0 = time.time()
    a4p = compute_all4pairs(edges)
    t_a4p = time.time() - t0
    
    # Compute clause count (triple_clause_count, fast, ~1.5s)
    t0 = time.time()
    total_cl = 0
    for a in range(M):
        ea = edges[a]
        pa0 = all_lifts[(ea[0], ea[1], 0)]
        pa1 = all_lifts[(ea[0], ea[1], 1)]
        for b in range(a+1, M):
            eb = edges[b]
            pb0 = all_lifts[(eb[0], eb[1], 0)]
            pb1 = all_lifts[(eb[0], eb[1], 1)]
            for c in range(b+1, M):
                ec = edges[c]
                pc0 = all_lifts[(ec[0], ec[1], 0)]
                pc1 = all_lifts[(ec[0], ec[1], 1)]
                for oa in (0, 1):
                    pa = pa0 if oa == 0 else pa1
                    for ob in (0, 1):
                        pb = pb0 if ob == 0 else pb1
                        for oc in (0, 1):
                            pc = pc0 if oc == 0 else pc1
                            if is_collinear_12(pa + pb + pc):
                                total_cl += 1
    t_cl = time.time() - t0
    
    print(f"  {name}: a4p={a4p} clauses={total_cl} ratio={total_cl/max(a4p,1):.2f} [{t_a4p:.1f}s/{t_cl:.1f}s]", flush=True)

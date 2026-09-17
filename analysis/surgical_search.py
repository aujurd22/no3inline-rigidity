"""
Surgical attack on config_408.
Phase 1: zero-orient proxy on all valid 2-swaps involving worst cells.
Phase 2: CP-SAT validation of top candidates.
"""
import json, time, sys
from collections import Counter

M = 37
N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
sys.path.insert(0, HERE)

# === C4 lifts ===
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_lifts = {(u, v): c4_lift(u, v) for u in range(M) for v in range(M)}

def is_collinear_12(lifts):
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i + 1, 12):
            xj, yj = lifts[j]
            if xi == xj and yi == yj:
                continue
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi:
                    continue
                if dx * (yk - yi) == dy * (xk - xi):
                    return True
    return False

def zero_clause_count(cells):
    """Zero-orientation clause count (fast proxy)."""
    total = 0
    for a in range(M):
        pa = all_lifts[cells[a]]
        for b in range(a + 1, M):
            pb = all_lifts[cells[b]]
            for c in range(b + 1, M):
                if is_collinear_12(pa + pb + all_lifts[cells[c]]):
                    total += 1
    return total

# Load config_408
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
orig_edges = [(min(u,v), max(u,v)) for u,v in data['edges']]

# Identify worst cells by total violation count (from earlier analysis)
# cell index → violations in optimal orientation
offender_impact = {36: 4, 31: 4, 22: 4, 11: 3, 24: 3, 27: 2, 3: 2, 2: 2, 
                   5: 2, 32: 2, 8: 2, 9: 2, 34: 2, 23: 2, 0: 1, 1: 1, 
                   20: 1, 26: 1, 17: 1, 18: 1, 13: 1, 15: 1, 25: 1, 29: 1, 35: 1, 33: 1}

# Top 10 offenders
worst_cells = sorted(offender_impact.keys(), key=lambda x: -offender_impact[x])[:10]
print(f"Top 10 offenders: {worst_cells}")
print(f"  Their cells: {[orig_edges[i] for i in worst_cells]}")
print(f"  Impact scores: {[offender_impact[i] for i in worst_cells]}")

# Find valid 2-swaps
existing_set = set(orig_edges)
swaps = []
for i in range(M):
    for j in range(i+1, M):
        if i not in worst_cells and j not in worst_cells:
            continue
        i1, j1 = orig_edges[i]
        i2, j2 = orig_edges[j]
        if len({i1, j1, i2, j2}) < 4:
            continue
        # Two possible rewiring patterns
        candidates = [
            ((min(i1,i2), max(i1,i2)), (min(j1,j2), max(j1,j2))),
            ((min(i1,j2), max(i1,j2)), (min(j1,i2), max(j1,i2))),
        ]
        for e1, e2 in candidates:
            if e1 in existing_set or e2 in existing_set or e1 == e2:
                continue
            swaps.append((i, j, e1, e2))

print(f"\nFound {len(swaps)} valid 2-swaps to test")

# Phase 1: zero-orient proxy
print(f"\nPhase 1: Zero-orient screening...")
baseline_zero = zero_clause_count(orig_edges)
print(f"Baseline zero-orient: {baseline_zero}")
print(f"config_408 cells: {list(orig_edges[i] for i in range(37))}")

candidates = []
t0 = time.time()
for idx, (i, j, e1, e2) in enumerate(swaps):
    new_edges = list(orig_edges)
    new_edges[i] = e1
    new_edges[j] = e2
    
    # Quick validity
    deg = Counter()
    for u, v in new_edges:
        deg[u] += 1
        deg[v] += 1
    if min(deg.values()) != 2 or max(deg.values()) != 2:
        continue
    if len(set(new_edges)) != 37:
        continue
    
    cl = zero_clause_count(new_edges)
    candidates.append((cl, new_edges))
    
    if (idx + 1) % 50 == 0:
        best_sofar = min(c[0] for c in candidates)
        print(f"  {idx+1}/{len(swaps)} tested, best_zero={best_sofar} ({time.time()-t0:.0f}s)", flush=True)

t1 = time.time()
print(f"Phase 1 done: {len(candidates)} valid, {t1-t0:.0f}s")
candidates.sort(key=lambda x: x[0])
print(f"\nTop 5:")
for cl, e in candidates[:5]:
    print(f"  {cl} zero-orient clauses")

# Phase 2: CP-SAT validate top candidates
print(f"\nPhase 2: CP-SAT validation...")
from solver_2factor_sat_pipeline import enumerate_clauses
from ortools.sat.python import cp_model

for rank, (zero_cl, test_edges) in enumerate(candidates[:5]):
    print(f"\n  Candidate #{rank+1} (zero={zero_cl}):")
    
    t0 = time.time()
    try:
        clause_list, clause_map = enumerate_clauses(M, test_edges, n=N, verbose=False)
        t_cl = time.time() - t0
        print(f"    {len(clause_list)} clauses, {t_cl:.1f}s")
        
        if len(clause_list) > 600:
            print(f"    SKIP (too many clauses, likely >16)", flush=True)
            continue
        
        # CP-SAT MaxSAT
        model = cp_model.CpModel()
        x = [model.NewBoolVar(f"x{k}") for k in range(M)]
        violations = []
        for idx, (a, b, c, bits) in enumerate(clause_list):
            b1, b2, b3 = (bits >> 0) & 1, (bits >> 1) & 1, (bits >> 2) & 1
            la = x[a] if b1 == 1 else x[a].Not()
            lb = x[b] if b2 == 1 else x[b].Not()
            lc = x[c] if b3 == 1 else x[c].Not()
            v = model.NewBoolVar(f"v{idx}")
            model.AddBoolAnd([la, lb, lc]).OnlyEnforceIf(v)
            model.AddBoolOr([la.Not(), lb.Not(), lc.Not()]).OnlyEnforceIf(v.Not())
            violations.append(v)
        model.Minimize(sum(violations))
        
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 8
        solver.parameters.max_time_in_seconds = 120
        
        t0 = time.time()
        status = solver.Solve(model)
        t_solve = time.time() - t0
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            min_v = int(solver.ObjectiveValue())
            bound = solver.BestObjectiveBound()
            print(f"    min_violations={min_v} (bound={bound:.1f}) {t_solve:.1f}s", flush=True)
            
            if min_v < 16:
                print(f"    ★★★ BREAKTHROUGH: {min_v} < 16! ★★★", flush=True)
                json.dump({"edges": test_edges, "clauses": len(clause_list), 
                          "violations": min_v, "bound": bound},
                         open(f"{HERE}/results/breaktfu.json", "w"))
        else:
            print(f"    No solution (status={status})", flush=True)
            
    except Exception as ex:
        print(f"    ERROR: {ex}", flush=True)

print(f"\nDone.")

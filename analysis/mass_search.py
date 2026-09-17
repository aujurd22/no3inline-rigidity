"""
mass_search.py — 大规模随机 2-因子搜索 + CP-SAT 快速验证

策略：
1. 生成 5000 个随机 2-因子（各种周型）
2. 对每个快速枚举子句数（~0.02s/个）
3. 取子句最少的前 20 个
4. 对每个用 CP-SAT 求最小违例数（~3-30s/个）
5. 找出全局最小
"""

import sys, os, json, time, random
from collections import Counter

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import enumerate_clauses
from ortools.sat.python import cp_model

M = 37

# ===========================================================
# 快速 2-因子生成（随机排列→随机周型）
# ===========================================================
def random_2factor(rng):
    """生成随机 2-因子（用随机排列的循环分解）"""
    perm = list(range(M))
    rng.shuffle(perm)
    visited = [False] * M
    edges = []
    cycles = []
    for i in range(M):
        if not visited[i]:
            cycle = []
            j = i
            while not visited[j]:
                visited[j] = True
                cycle.append(j)
                j = perm[j]
            cycles.append(cycle)
            for k in range(len(cycle)):
                a, b = cycle[k], cycle[(k+1) % len(cycle)]
                edges.append((a, b) if a <= b else (b, a))
    return edges, cycles

def count_clauses_fast(edges):
    """仅计子句数，不存结果（更快）"""
    clause_list, _ = enumerate_clauses(M, edges, verbose=False)
    return len(clause_list)

# ===========================================================
# CP-SAT 最小违例
# ===========================================================
def compute_min_violations(edges, timelimit=20):
    clause_list, _ = enumerate_clauses(M, edges, verbose=False)
    n_cl = len(clause_list)
    
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(M)]
    violation_vars = []
    
    for idx, (a, b, c, bits) in enumerate(clause_list):
        b1, b2, b3 = (bits >> 0) & 1, (bits >> 1) & 1, (bits >> 2) & 1
        lit_a = x[a] if b1 else x[a].Not()
        lit_b = x[b] if b2 else x[b].Not()
        lit_c = x[c] if b3 else x[c].Not()
        v = model.NewBoolVar(f"v{idx}")
        model.AddBoolAnd([lit_a, lit_b, lit_c]).OnlyEnforceIf(v)
        model.AddBoolOr([lit_a.Not(), lit_b.Not(), lit_c.Not()]).OnlyEnforceIf(v.Not())
        violation_vars.append(v)
    
    model.Minimize(sum(violation_vars))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = timelimit
    
    t0 = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - t0
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return int(solver.ObjectiveValue()), status == cp_model.OPTIMAL, round(elapsed, 1), n_cl
    return None, False, round(elapsed, 1), n_cl


# ===========================================================
# 主搜索
# ===========================================================
N_SAMPLES = 5000
N_CP_SAT = 20

print("=" * 60)
print(f"MASS SEARCH — {N_SAMPLES} random 2-factors → top {N_CP_SAT} CP-SAT verified")
print("=" * 60)

rng = random.Random(12345)
t0 = time.time()

# Phase 1: quick enumeration
print(f"\nPhase 1: generating {N_SAMPLES} random 2-factors...")
candidates = []
for i in range(N_SAMPLES):
    if i % 1000 == 0 and i > 0:
        print(f"  {i}/{N_SAMPLES} done ({time.time()-t0:.0f}s)", flush=True)
    edges, cycles = random_2factor(rng)
    n_cl = count_clauses_fast(edges)
    cycle_len = tuple(sorted([len(c) for c in cycles], reverse=True))
    candidates.append((n_cl, edges, cycle_len, i))

# Sort by clause count
candidates.sort(key=lambda x: x[0])
elapsed_phase1 = time.time() - t0

print(f"\nPhase 1 done ({elapsed_phase1:.0f}s)")
print(f"\nTop 20 by clause count:")
for i, (n_cl, edges, cyc, idx) in enumerate(candidates[:20]):
    print(f"  {i+1:2d}. trial #{idx}: {n_cl:4d} clauses, cycle {cyc}")

# Phase 2: CP-SAT verification
print(f"\nPhase 2: CP-SAT verifying top {N_CP_SAT} candidates...")
results = []
global_best = 1e9
global_best_data = None

for i in range(min(N_CP_SAT, len(candidates))):
    n_cl, edges, cyc, idx = candidates[i]
    min_v, optimal, t, n_cl2 = compute_min_violations(edges, timelimit=20)
    
    opt_str = "✅" if optimal else "⏳"
    if min_v is not None:
        print(f"  [{i+1}/{N_CP_SAT}] trial #{idx}: {n_cl} clauses → {min_v} violations {opt_str} ({t}s)", flush=True)
        results.append({"trial": idx, "clauses": n_cl, "min_violations": min_v, "proven_optimal": optimal, "cycle_type": cyc})
        
        if min_v < global_best:
            global_best = min_v
            global_best_data = (edges, cyc, n_cl, min_v, optimal)
            if min_v < 16:
                print(f"    ★★★ BELOW 16 BARRIER! ★★★", flush=True)
    else:
        print(f"  [{i+1}/{N_CP_SAT}] trial #{idx}: {n_cl} clauses → FEASIBLE? ({t}s)", flush=True)

# ===========================================================
# 总结
# ===========================================================
elapsed_total = time.time() - t0
print(f"\n{'='*60}")
print(f"RESULTS (total time: {elapsed_total:.0f}s)")
print(f"{'='*60}")

valid = [r for r in results if r["min_violations"] is not None]
if valid:
    best = min(valid, key=lambda r: r["min_violations"])
    print(f"  Best: trial #{best['trial']}")
    print(f"    Clauses: {best['clauses']}")
    print(f"    Violations: {best['min_violations']}")
    print(f"    Proven optimal: {best['proven_optimal']}")
    print(f"    Cycle type: {best['cycle_type']}")
    
    if global_best < 16:
        print(f"\n  ★★★ FOUND 2-FACTOR WITH {global_best} VIOLATIONS < 16! ★★★")
        edges, cyc, n_cl, min_v, optimal = global_best_data
        result = {
            "m": M,
            "edges": [list(e) for e in edges],
            "cycle_type": list(cyc),
            "min_violations": min_v,
            "n_clauses": n_cl,
            "proven_optimal": optimal,
        }
        with open(f"{HERE}/results/mass_best_result.json", "w") as f:
            json.dump(result, f, indent=1)
        print(f"  Saved to: {HERE}/results/mass_best_result.json")
    
    # Distribution
    print(f"\n  Distribution:")
    dist = Counter(r["min_violations"] for r in valid)
    for v in sorted(dist):
        print(f"    {v:3d} violations: {dist[v]} configs")
else:
    print(f"  No valid results")

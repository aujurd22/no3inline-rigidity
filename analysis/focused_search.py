"""
focused_search.py — 聚焦搜索，只验证子句少的 2-因子

策略：
1. 生成 10000 个随机 2-因子
2. 快速枚举子句数（每个 ~0.02s）
3. 只保留子句数 < 415 的候选（仅这些可能 < 16 违例）
4. 对保留的候选用 CP-SAT 精确求最小违例
"""

import sys, os, json, time, random
from collections import Counter
from itertools import combinations

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import enumerate_clauses, generate_2factor_full
from ortools.sat.python import cp_model

M = 37

def random_2factor_clauses(rng):
    """Generate a random 2-factor and count its clauses. Returns (edges, n_clauses, cycle_type)."""
    edges = generate_2factor_full(M, rng)
    if edges is None:
        return None, None, None
    clause_list, _ = enumerate_clauses(M, edges, verbose=False)
    
    # Also determine cycle type
    adj = {i: [] for i in range(M)}
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = [False] * M
    cycles = []
    for i in range(M):
        if not visited[i]:
            c_len = 0
            j = i
            while not visited[j]:
                visited[j] = True
                c_len += 1
                for n in adj[j]:
                    if not visited[n]:
                        j = n
                        break
            if c_len > 0:
                cycles.append(c_len)
    return edges, len(clause_list), tuple(sorted(cycles, reverse=True))

def compute_min_violations(edges, timelimit=60):
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
    solver.parameters.num_search_workers = 4  # more workers for faster solve
    solver.parameters.max_time_in_seconds = timelimit
    t0 = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - t0
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return int(solver.ObjectiveValue()), status == cp_model.OPTIMAL, round(elapsed, 1), n_cl
    return None, False, round(elapsed, 1), n_cl


# ===========================================================
# Phase 1: Quick filter
# ===========================================================
N_SAMPLES = 10000
CLAUSE_THRESHOLD = 415  # only configs with fewer clauses than this get CP-SAT

print("=" * 60)
print(f"FOCUSED SEARCH — {N_SAMPLES} random 2-factors")
print(f"  Only keep those with < {CLAUSE_THRESHOLD} clauses for CP-SAT")
print("=" * 60)

rng = random.Random(9999)
t0 = time.time()

low_clause_candidates = []
min_clause = 1e9

for i in range(N_SAMPLES):
    edges, n_cl, cyc = random_2factor_clauses(rng)
    if edges is None:
        continue
    
    if n_cl < min_clause:
        min_clause = n_cl
        print(f"  Trial {i}: new min {n_cl} clauses (cycle {cyc})", flush=True)
    
    if n_cl < CLAUSE_THRESHOLD:
        low_clause_candidates.append((n_cl, edges, cyc, i))

elapsed = time.time() - t0
print(f"\nPhase 1 done ({elapsed:.0f}s)")
print(f"  Found {len(low_clause_candidates)} candidates with < {CLAUSE_THRESHOLD} clauses")
print(f"  Minimum clause count: {min_clause}")

# Sort by clause count
low_clause_candidates.sort(key=lambda x: x[0])

print(f"\nTop candidates:")
for i, (n_cl, edges, cyc, idx) in enumerate(low_clause_candidates[:20]):
    print(f"  {i+1:2d}. trial #{idx}: {n_cl:4d} clauses, cycle {cyc}")

# ===========================================================
# Phase 2: CP-SAT verification
# ===========================================================
print(f"\n{'='*60}")
print(f"Phase 2: CP-SAT verification (up to 30 candidates)")
print(f"{'='*60}")

n_verify = min(30, len(low_clause_candidates))
results = []
global_best = 1e9

for i in range(n_verify):
    n_cl, edges, cyc, idx = low_clause_candidates[i]
    min_v, optimal, t, n_cl2 = compute_min_violations(edges, timelimit=60)
    
    opt_str = "✅P" if optimal else "⏳F"
    if min_v is not None:
        print(f"  [{i+1}/{n_verify}] trial #{idx}: {n_cl}cl → {min_v}v {opt_str} ({t}s) cyc={cyc}", flush=True)
        results.append({"idx": idx, "clauses": n_cl, "violations": min_v, "optimal": optimal, "time": t, "cycle_type": list(cyc)})
        if min_v < global_best:
            global_best = min_v
            global_best_edges = edges
            global_best_info = (idx, n_cl, cyc)
            if min_v < 16:
                print(f"    ★★★ BELOW 16 BARRIER! ★★★", flush=True)
    else:
        print(f"  [{i+1}/{n_verify}] trial #{idx}: {n_cl}cl → ? ({t}s)", flush=True)

# ===========================================================
# Results
# ===========================================================
total_time = time.time() - t0
print(f"\n{'='*60}")
print(f"RESULTS (total: {total_time:.0f}s)")
print(f"{'='*60}")

valid = [r for r in results if r["violations"] is not None]
if valid:
    best = min(valid, key=lambda r: r["violations"])
    print(f"\n  Best: trial #{best['idx']}: {best['violations']} violations ({best['clauses']} clauses)")
    print(f"    Cycle type: {best['cycle_type']}")
    print(f"    Proven optimal: {best['optimal']}")
    
    if best['violations'] < 16:
        print(f"\n  ★★★ FOUND 2-FACTOR WITH {best['violations']} VIOLATIONS < 16! ★★★")
        result = {
            "m": M,
            "edges": [list(e) for e in global_best_edges],
            "cycle_type": global_best_info[2],
            "min_violations": best['violations'],
            "n_clauses": best['clauses'],
            "proven_optimal": best['optimal'],
        }
        with open(f"{HERE}/results/focused_best_result.json", "w") as f:
            json.dump(result, f, indent=1)
        print(f"  Saved to: focused_best_result.json")
    else:
        print(f"\n  Best is still ≥ 16 (matches config_408)")
        
        # Distribution
        print(f"\n  Distribution:")
        dist = Counter(r["violations"] for r in valid)
        for v in sorted(dist):
            print(f"    {v:3d} violations: {dist[v]} configs")
    
    # Save all results
    with open(f"{HERE}/results/focused_search_results.json", "w") as f:
        json.dump({"results": results, "total_samples": N_SAMPLES, "time_s": total_time}, f, indent=1)
else:
    print(f"  No valid results")

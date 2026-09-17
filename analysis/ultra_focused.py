"""
ultra_focused.py — 超聚焦搜索：只生成 [28,9] 周型的 2-因子

理由：config_408（[28,9], 408 子句）是已知最优。
只需生成更多 [28,9] 候选，找子句最少的，只验证那一个。
"""

import sys, os, json, time, random
from collections import Counter

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)
from solver_2factor_sat_pipeline import enumerate_clauses
from ortools.sat.python import cp_model

M = 37

# ===========================================================
# 生成 [28,9] 周型 2-因子
# ===========================================================
def generate_28_9(rng):
    """Generate a 2-factor with cycle type [28,9]"""
    vertices = list(range(M))
    rng.shuffle(vertices)
    
    edges = []
    # First 9-cycle
    for k in range(9):
        u = vertices[k]
        v = vertices[(k+1) % 9]
        edges.append((u, v) if u <= v else (v, u))
    # 28-cycle
    for k in range(9, 36):
        u = vertices[k]
        v = vertices[(k+1 - 9) % 28 + 9]
        edges.append((u, v) if u <= v else (v, u))
    # Close the 28-cycle: last vertex back to first
    u = vertices[36]
    v = vertices[9]
    edges.append((u, v) if u <= v else (v, u))
    
    # Verify
    assert len(edges) == M
    assert len(set(edges)) == M, f"Duplicate: {len(edges)} vs {len(set(edges))}"
    deg = Counter([u for e in edges for u in e])
    assert all(d == 2 for d in deg.values()), f"Degree fail"
    return edges

def count_clauses_fast(edges):
    clause_list, _ = enumerate_clauses(M, edges, verbose=False)
    return len(clause_list)

# ===========================================================
# Phase 1: 大量生成 [28,9]，快速计子句
# ===========================================================
N_SAMPLES = 5000
SAVE_TOP = 5

print("=" * 60)
print(f"ULTRA FOCUSED — {N_SAMPLES} [28,9] 2-factors")
print("=" * 60)

rng = random.Random(77777)
t0 = time.time()

candidates = []
min_cl = 1e9
for i in range(N_SAMPLES):
    edges = generate_28_9(rng)
    n_cl = count_clauses_fast(edges)
    candidates.append((n_cl, edges))
    if n_cl < min_cl:
        min_cl = n_cl
        if n_cl <= 410:
            print(f"  Trial {i}: {n_cl} clauses (new min)", flush=True)

elapsed = time.time() - t0
print(f"\nPhase 1 done ({elapsed:.0f}s for {N_SAMPLES} samples)")
print(f"  Minimum clauses: {min_cl}")

# Sort
candidates.sort(key=lambda x: x[0])
print(f"\n  Top 10 clause counts:")
for i in range(min(10, len(candidates))):
    print(f"    {i+1:2d}. {candidates[i][0]} clauses")

# ===========================================================
# Phase 2: CP-SAT 验证前 SAVE_TOP 个候选
# ===========================================================
print(f"\n{'='*60}")
print(f"Phase 2: CP-SAT verifying top {SAVE_TOP} candidates")
print(f"{'='*60}")

results = []
for i in range(SAVE_TOP):
    n_cl, edges = candidates[i]
    
    clause_list, _ = enumerate_clauses(M, edges, verbose=False)
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
    solver.parameters.num_search_workers = 8
    solver.parameters.max_time_in_seconds = 60
    
    t1 = time.time()
    status = solver.Solve(model)
    t = time.time() - t1
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        min_v = int(solver.ObjectiveValue())
        optimal = (status == cp_model.OPTIMAL)
        opt_s = "✅P" if optimal else "⏳F"
        print(f"  [{i+1}/{SAVE_TOP}] {n_cl} clauses → {min_v} violations {opt_s} ({t:.1f}s)", flush=True)
        results.append((n_cl, min_v, optimal, edges))
        
        if min_v < 16:
            print(f"    ★★★ BELOW 16! ★★★", flush=True)
            # Save immediately
            result_data = {
                "m": M, "edges": [list(e) for e in edges],
                "min_violations": min_v, "n_clauses": n_cl, "proven_optimal": optimal,
            }
            with open(f"{HERE}/results/focused_best_result.json", "w") as f:
                json.dump(result_data, f, indent=1)
    else:
        print(f"  [{i+1}/{SAVE_TOP}] {n_cl} clauses → ? (timeout {t:.1f}s)", flush=True)
        results.append((n_cl, None, False, edges))

# ===========================================================
# 结果
# ===========================================================
total_time = time.time() - t0
print(f"\n{'='*60}")
print(f"RESULTS (total: {total_time:.0f}s)")
print(f"{'='*60}")

valid = [r for r in results if r[1] is not None]
if valid:
    best = min(valid, key=lambda r: r[1])
    print(f"\n  Best: {best[0]} clauses, {best[1]} violations (optimal={best[2]})")
    
    if best[1] < 16:
        print(f"\n  ★★★ FOUND 2-FACTOR WITH {best[1]} VIOLATIONS < 16! ★★★")
    elif best[1] == 16:
        print(f"\n  Best still at 16 violations (matches config_408)")
        if best[0] < 408:
            print(f"  But fewer clauses! {best[0]} vs 408 — might need more search")
    else:
        print(f"\n  All ≥ 16 violations")
    
    print(f"\n  Summary:")
    for n_cl, min_v, optimal, _ in results:
        if min_v is not None:
            print(f"    {n_cl:4d} clauses → {min_v:3d} violations {'✅' if optimal else '⏳'}")
else:
    print(f"  No valid results (all CP-SAT timed out)")

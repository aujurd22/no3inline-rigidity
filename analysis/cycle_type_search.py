"""
cycle_type_search.py — 系统搜索各类周型的 2-因子，用 CP-SAT 快速验证

目标是：对每种周型生成多个 2-因子，用 CP-SAT 精确求最小违例数，
找出全局最小的配置。

每个验证仅需 2-30 秒（CP-SAT），因此可处理大量样本。
"""

import sys, os, json, time, random
from collections import Counter

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import enumerate_clauses
from ortools.sat.python import cp_model

M = 37  # fixed

# ===========================================================
# 2-因子生成
# ===========================================================
def generate_by_cycle_type(cycle_type, rng):
    """cycle_type: list of cycle lengths summing to 37, e.g. [9, 28]"""
    assert sum(cycle_type) == M
    vertices = list(range(M))
    rng.shuffle(vertices)
    edges = []
    pos = 0
    for clen in cycle_type:
        cv = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cv[k]; v = cv[(k+1) % clen]
            edges.append((u, v) if u <= v else (v, u))
    # Verify
    assert len(edges) == M
    assert len(set(edges)) == M, f"Duplicate edges! {len(edges)} vs {len(set(edges))}"
    deg = Counter([u for e in edges for u in e])
    assert all(d == 2 for d in deg.values()), f"Degree fail"
    return edges

# ===========================================================
# CP-SAT 最小违例计算
# ===========================================================
def compute_min_violations(edges, timelimit=30):
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
        return int(solver.ObjectiveValue()), status == cp_model.OPTIMAL, round(elapsed, 1), n_cl, clause_list
    return None, False, round(elapsed, 1), n_cl, clause_list

# ===========================================================
# 周型列表
# ===========================================================
# 所有二周型（两个圈）和部分三周型
cycle_types = [
    [28, 9],    # config_408 type
    [29, 8],
    [27, 10],
    [26, 11],
    [25, 12],
    [24, 13],
    [23, 14],
    [22, 15],
    [21, 16],
    [20, 17],
    [19, 18],
    [30, 7],
    [31, 6],
    [32, 5],
    [33, 4],
    [34, 3],
    [35, 2],
    [36, 1],   # Hamiltonian with a loop
    [37],      # Hamiltonian
    # 三周型（精选）
    [15, 12, 10],
    [14, 13, 10],
    [13, 12, 12],
    [12, 10, 15],
    [20, 10, 7],
]

# ===========================================================
# 搜索
# ===========================================================
print("=" * 60)
print("CYCLE TYPE SEARCH — CP-SAT verification")
print(f"  {len(cycle_types)} types, ~{30*len(cycle_types)}s expected")
print("=" * 60)

rng = random.Random(42)
results = []
global_best = 1e9
global_best_info = None

for ct_idx, ct in enumerate(cycle_types):
    ct_label = f"[{','.join(map(str, sorted(ct, reverse=True)))}]"
    print(f"\n  [{ct_idx+1}/{len(cycle_types)}] Type {ct_label}: ", end="", flush=True)
    
    # 对每种周型生成多个样本，取子句最少的
    n_samples = 50  # 取 50 个候选
    candidates = []
    for s in range(n_samples):
        seed = 10000 + ct_idx * 100 + s
        rng2 = random.Random(seed)
        edges = generate_by_cycle_type(ct, rng2)
        clause_list, _ = enumerate_clauses(M, edges, verbose=False)
        candidates.append((len(clause_list), edges))
    
    # 选子句最少的 3 个做 CP-SAT 验证
    candidates.sort(key=lambda x: x[0])
    
    print(f"{candidates[0][0]} clauses (best of {n_samples})", end="", flush=True)
    
    for ci in range(min(3, len(candidates))):
        n_cl, edges = candidates[ci]
        min_v, optimal, t, _, _ = compute_min_violations(edges, timelimit=30)
        
        if min_v is not None:
            opt = "P" if optimal else "F"
            print(f" → {min_v}v/{t}s({opt})", end="", flush=True)
            
            entry = {
                "cycle_type": ct,
                "clauses": n_cl,
                "min_violations": min_v,
                "proven_optimal": optimal,
                "time_s": t,
            }
            results.append(entry)
            
            if min_v < global_best:
                global_best = min_v
                global_best_info = (ct_label, n_cl, min_v, edges)
                print(f" ★", end="", flush=True)
                if min_v < 16:
                    print(f" BELOW 16! ★★★", end="", flush=True)
        else:
            print(f" → ?", end="", flush=True)

# ===========================================================
# 总结
# ===========================================================
print(f"\n\n{'='*60}")
print("FINAL RESULTS")
print(f"{'='*60}")

valid = [r for r in results if r["min_violations"] is not None]
if valid:
    by_type = {}
    for r in valid:
        key = str(r["cycle_type"])
        if key not in by_type or r["min_violations"] < by_type[key]["min_violations"]:
            by_type[key] = r
    
    print(f"\n  Best per cycle type:")
    for key, r in sorted(by_type.items(), key=lambda x: x[1]["min_violations"]):
        print(f"    {key:15s}: {r['min_violations']:3d} violations ({r['clauses']:4d} clauses)")
    
    overall_best = min(valid, key=lambda r: r["min_violations"])
    print(f"\n  ★ Global best: {overall_best['min_violations']} violations")
    print(f"    Cycle type: {overall_best['cycle_type']}")
    print(f"    Clauses: {overall_best['clauses']}")
    print(f"    Proven optimal: {overall_best['proven_optimal']}")
    
    if overall_best['min_violations'] < 16:
        print(f"\n  ★★★ FOUND 2-FACTOR WITH < 16 VIOLATIONS! ★★★")
        
        # 保存最佳配置
        if global_best_info:
            ct_label, n_cl, min_v, edges = global_best_info
            result_data = {
                "m": M,
                "edges": [list(e) for e in edges],
                "cycle_type": global_best_info[0],
                "min_violations": min_v,
                "n_clauses": n_cl,
            }
            path = f"{HERE}/results/best_found_cycle_type.json"
            with open(path, "w") as f:
                json.dump(result_data, f, indent=1)
            print(f"    Saved to: {path}")
else:
    print(f"  No valid results found")

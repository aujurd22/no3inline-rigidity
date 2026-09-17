"""
orientation_maxsat.py — CP-SAT 精确求解取向子问题

问题：对 config_408 的 37 个 edge，找取向分配使违例数最少。
37 个二值变量、408 条三元子句 → 极小 MaxSAT 实例。

CP-SAT 通常能秒解这种规模。
"""

import sys, os, json, time

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import enumerate_clauses

# 加载 config_408
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
edges = [tuple(e) for e in data["edges"]]
N = len(edges)

print(f"Loading OR-Tools CP-SAT...", end=" ", flush=True)
from ortools.sat.python import cp_model
print("done")
print(f"  edges: {N}, enumerating clauses...", end=" ", flush=True)

clause_list, clause_map = enumerate_clauses(37, edges, verbose=False)
print(f"done: {len(clause_list)} clauses")

# ===========================================================
# CP-SAT 模型
# ===========================================================
model = cp_model.CpModel()

# 37 个二值变量
x = [model.NewBoolVar(f"x{i}") for i in range(N)]

# 每条子句：一个违例变量
violation_vars = []
for idx, (a, b, c, bits) in enumerate(clause_list):
    b1 = (bits >> 0) & 1
    b2 = (bits >> 1) & 1
    b3 = (bits >> 2) & 1
    
    # clause = (x[a]==b1 AND x[b]==b2 AND x[c]==b3) → violation
    # Equivalent to: violation >= x[a]_xor_b1 + x[b]_xor_b2 + x[c]_xor_b3 - 2
    # where x_i_xor_b = x[i] if b=1 else 1-x[i]
    
    # literal for "x[a] matches b1":
    lit_a = x[a] if b1 == 1 else x[a].Not()
    lit_b = x[b] if b2 == 1 else x[b].Not()
    lit_c = x[c] if b3 == 1 else x[c].Not()
    
    v = model.NewBoolVar(f"v{idx}")
    # v is True iff all 3 literals are True
    model.AddBoolAnd([lit_a, lit_b, lit_c]).OnlyEnforceIf(v)
    model.AddBoolOr([lit_a.Not(), lit_b.Not(), lit_c.Not()]).OnlyEnforceIf(v.Not())
    
    violation_vars.append(v)

# 目标：最小化违例数
model.Minimize(sum(violation_vars))

# ===========================================================
# 求解
# ===========================================================
solver = cp_model.CpSolver()
solver.parameters.num_search_workers = 8
solver.parameters.max_time_in_seconds = 120.0

print(f"\n{'='*60}")
print(f"SOLVING... ({N} vars, {len(clause_list)} clauses)")
print(f"{'='*60}")
t0 = time.time()
status = solver.Solve(model)
elapsed = time.time() - t0

# ===========================================================
# 结果
# ===========================================================
print(f"\nStatus: {solver.StatusName(status)} (time={elapsed:.1f}s)")
print(f"Objective: {solver.ObjectiveValue()}")
print(f"Best bound: {solver.BestObjectiveBound()}")

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    orient = [int(solver.Value(x[i])) for i in range(N)]
    viol = int(solver.ObjectiveValue())
    bound = solver.BestObjectiveBound()
    
    print(f"\n{'='*60}")
    print(f"OPTIMAL ORIENTATION FOUND")
    print(f"{'='*60}")
    print(f"  Min violations: {viol}")
    print(f"  Best bound: {bound}")
    print(f"  Proven optimal: {status == cp_model.OPTIMAL}")
    print(f"  SDP lower bound: 12.5 (reference)")
    
    if status == cp_model.OPTIMAL:
        print(f"\n  → This IS the global optimum for config_408's 2-factor")
        if viol <= 15:
            print(f"  → BROKE 16 barrier!")
        else:
            print(f"  → 16 IS the true minimum for this 2-factor")
    else:
        print(f"\n  → Not proven optimal (timelimit)")
    
    # 保存
    result = {
        "m": 37,
        "edges": data["edges"],
        "min_violations": viol,
        "proven_optimal": status == cp_model.OPTIMAL,
        "best_bound": bound,
        "sdp_lb": 12.5,
        "n_clauses": len(clause_list),
        "orientation": orient,
        "solver_status": solver.StatusName(status),
        "solve_time_s": round(elapsed, 1),
    }
    path = f"{HERE}/results/config_408_maxsat_result.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=1)
    print(f"\n  Saved to: {path}")
else:
    print(f"\n  Solver could not find solution within timelimit.")

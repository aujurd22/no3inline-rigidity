"""
batch_verify_2factors.py — 用 CP-SAT 批量验证所有保存的 2-因子的最低违例数

对每个已保存的 2-因子配置：
1. 枚举子句
2. CP-SAT MaxSAT 求解最小违例数
3. 找出全局最优
"""

import sys, os, json, time, glob

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import enumerate_clauses
from ortools.sat.python import cp_model

def compute_min_violations(edges, m=37, timelimit=30):
    """CP-SAT MaxSAT for orientation subproblem. Returns (min_viol, optimal, time_s)."""
    clause_list, _ = enumerate_clauses(m, edges, verbose=False)
    
    model = cp_model.CpModel()
    N = len(edges)
    x = [model.NewBoolVar(f"x{i}") for i in range(N)]
    
    violation_vars = []
    for idx, (a, b, c, bits) in enumerate(clause_list):
        b1 = (bits >> 0) & 1
        b2 = (bits >> 1) & 1
        b3 = (bits >> 2) & 1
        lit_a = x[a] if b1 == 1 else x[a].Not()
        lit_b = x[b] if b2 == 1 else x[b].Not()
        lit_c = x[c] if b3 == 1 else x[c].Not()
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
        return int(solver.ObjectiveValue()), status == cp_model.OPTIMAL, round(elapsed, 1), len(clause_list)
    return None, False, round(elapsed, 1), len(clause_list)


# ===========================================================
# 收集所有保存的 2-因子
# ===========================================================
print("=" * 60)
print("BATCH VERIFY ALL SAVED 2-FACTORS")
print("=" * 60)

# 已知的配置文件
config_files = [
    ("config_408", f"{HERE}/results/config_408_edges.json"),
    ("best_gv_63", f"{HERE}/results/best_gv_63_edges.json"),
    ("violation_improved", f"{HERE}/results/violation_improved_edges.json"),
    ("m36_extension", f"{HERE}/results/m36_extension_results.json"),
]

# 检查哪些存在
existing = []
for name, path in config_files:
    if os.path.exists(path):
        existing.append((name, path))
        print(f"  ✓ {name}: {path}")
    else:
        print(f"  ✗ {name}: {path} (not found)")

# 也找 mutate_gv*.json 和其他
for f in sorted(glob.glob(f"{HERE}/results/mutate_gv*.json")):
    name = os.path.splitext(os.path.basename(f))[0]
    existing.append((name, f))
    print(f"  ✓ {name}: {f}")

# 去重
seen = set()
unique = []
for name, path in existing:
    if path not in seen:
        seen.add(path)
        unique.append((name, path))

# ===========================================================
# 批量验证
# ===========================================================
print(f"\n{'='*60}")
print(f"Found {len(unique)} configs to verify")
print(f"{'='*60}")

results = []
for name, path in unique:
    try:
        with open(path) as f:
            data = json.load(f)
        if "edges" in data:
            edges = [tuple(e) for e in data["edges"]]
        elif "best_edges" in data:
            edges = [tuple(e) for e in data["best_edges"]]
        elif "cells" in data:
            cells = data["cells"]
            edges = [(min(u,v), max(u,v)) for u,v in cells]
        else:
            print(f"  ⚠ {name}: unknown format, skipping")
            continue
        
        if len(edges) != 37:
            print(f"  ⚠ {name}: {len(edges)} edges ≠ 37, skipping")
            continue
        
        min_v, optimal, t, n_cl = compute_min_violations(edges)
        
        result = {
            "name": name,
            "n_clauses": n_cl,
            "min_violations": min_v,
            "proven_optimal": optimal,
            "time_s": t,
        }
        results.append(result)
        
        status_str = "✅ OPTIMAL" if optimal else "⏳ FEASIBLE"
        opt_str = f" (PROVEN)" if optimal else ""
        print(f"  {name:25s}: {n_cl:4d} clauses → {min_v:3d} violations{opt_str} [{t:.1f}s]")
        
        # 如果找到 <16 的，标记重点
        if min_v is not None and min_v < 16:
            print(f"    ★★★ BELOW 16 BARRIER! ★★★")
            
    except Exception as e:
        print(f"  ❌ {name}: error - {e}")

# ===========================================================
# 总结
# ===========================================================
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")

valid_results = [r for r in results if r["min_violations"] is not None]
if valid_results:
    best = min(valid_results, key=lambda r: r["min_violations"])
    print(f"  Best config: {best['name']} — {best['min_violations']} violations (PROVEN={best['proven_optimal']})")
    
    # 如果最优 < 16，验证后保存
    if best['min_violations'] < 16:
        print(f"\n  ★★★ FOUND 2-FACTOR WITH < 16 VIOLATIONS! ★★★")
    
    print(f"\n  All results:")
    for r in sorted(valid_results, key=lambda r: r["min_violations"]):
        print(f"    {r['name']:25s}: {r['min_violations']:3d} violations ({r['n_clauses']:4d} clauses)")
else:
    print(f"  No valid results")

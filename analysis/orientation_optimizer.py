"""
orientation_optimizer.py — 纯取向优化求解器（正确版）

问题：对 FIXED 2-因子（config_408 的 37 条 edge (u,v)），寻找最佳取向分配
使违例三元组数最小。

每个 edge 有 2 种取向（seed = (u,v) 或 (v,u)）。每个三元组检查
2×2×2=8 种取向组合，如果有三共线则 forbid 该组合。

等价于：37 个二值变量，每个禁止的组合是一条三元子句(3-CNF)。
求最小违例数 = MaxSAT。

复用 solver_2factor_sat_pipeline.py 的 enumerate_clauses 做精确计算。
"""

import sys, os, json, random, math, time
from collections import defaultdict, Counter
from itertools import combinations

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

# ===========================================================
# 从 solver_2factor_sat_pipeline 复用 enumerate_clauses
# ===========================================================
from solver_2factor_sat_pipeline import enumerate_clauses

# ===========================================================
# 评估函数：给定 orient[37] ∈ {0,1}，计算违例数
# ===========================================================
def count_violations(orient, clause_list):
    """clause_list: [(e1,e2,e3, bits), ...]
    每个子句：如果 orient[e1]==bit0, orient[e2]==bit1, orient[e3]==bit2 → 违例"""
    viol = 0
    for a, b, c, bits in clause_list:
        b1 = (bits >> 0) & 1
        b2 = (bits >> 1) & 1
        b3 = (bits >> 2) & 1
        if orient[a] == b1 and orient[b] == b2 and orient[c] == b3:
            viol += 1
    return viol

def count_violations_fast(orient, clause_dict):
    """clause_dict: {(a,b,c): [(bits, b1,b2,b3), ...]} — faster lookup"""
    viol = 0
    for (a,b,c), clauses in clause_dict.items():
        for bits, b1, b2, b3 in clauses:
            if orient[a] == b1 and orient[b] == b2 and orient[c] == b3:
                viol += 1
                break  # only one clause per triple needs to match
    return viol

# ===========================================================
# 构建快速查询结构
# ===========================================================
def build_clause_lookup(clause_list):
    """Build per-triple lookup for fast evaluation"""
    lookup = {}
    for a, b, c, bits in clause_list:
        t = (a, b, c)
        b1 = (bits >> 0) & 1
        b2 = (bits >> 1) & 1
        b3 = (bits >> 2) & 1
        if t not in lookup:
            lookup[t] = []
        lookup[t].append((bits, b1, b2, b3))
    return lookup

# ===========================================================
# 模拟退火（纯取向）
# ===========================================================
def sa_orient(N, clause_lookup, clause_list, n_iter=100000, seed=42):
    rng = random.Random(seed)
    
    # 随机初始解
    orient = [rng.randint(0, 1) for _ in range(N)]
    curr_v = count_violations_fast(orient, clause_lookup)
    best_orient = list(orient)
    best_v = curr_v
    
    # 冷却
    T0 = 3.0
    T_end = 0.01
    
    for it in range(n_iter):
        T = T0 * (T_end / T0) ** (it / n_iter)
        
        # 翻转一个 cell 的取向
        cell = rng.randint(0, N - 1)
        old_bit = orient[cell]
        new_bit = 1 - old_bit
        
        orient[cell] = new_bit
        new_v = count_violations_fast(orient, clause_lookup)
        delta = new_v - curr_v
        
        if delta < 0 or rng.random() < math.exp(-delta / T):
            curr_v = new_v
            if curr_v < best_v:
                best_v = curr_v
                best_orient = list(orient)
                if best_v <= 15:
                    print(f"    🏆 iter {it}: best_v = {best_v}")
        else:
            orient[cell] = old_bit  # revert
    
    return best_orient, best_v

# ===========================================================
# 运行
# ===========================================================
print("=" * 60)
print("ORIENTATION OPTIMIZER (correct binary version)")
print("=" * 60)

# 加载 config_408 的 edges (the 2-factor)
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)

# 注意：edges 已经是 (u,v) with u≤v
edges = [tuple(e) for e in data["edges"]]
assert len(edges) == 37
assert all(u <= v for u, v in edges)
print(f"\n  2-factor: {len(edges)} edges")

# 枚举子句
print(f"\n  Enumerating clauses...", end=" ", flush=True)
t0 = time.time()
clause_list, clause_map = enumerate_clauses(37, edges, verbose=False)
elapsed = time.time() - t0
print(f"done ({elapsed:.1f}s)")
print(f"  Total clauses: {len(clause_list)}")
print(f"  This = number of forbidden (triple, orient) combos")

# 构建快速查询
clause_lookup = build_clause_lookup(clause_list)

# 统计每个三元组有几个 forbidden 组合
n_triples = 0
n_without_clause = 0
for triple, results in clause_map.items():
    n_triples += 1
    if not any(results):
        n_without_clause += 1

print(f"\n  Triples with 0 forbidden orientations: {n_without_clause} / {n_triples}")
print(f"  = structural harmless triples")

# 每个三元组 forbidden 组合数分布
forbidden_count = Counter()
for results in clause_map.values():
    forbidden_count[sum(results)] += 1
print(f"  Forbidden combos per triple:")
for k in sorted(forbidden_count):
    print(f"    {k}: {forbidden_count[k]} triples")

# ===========================================================
# SA 多次重启
# ===========================================================
print(f"\n{'='*60}")
print(f"SA ORIENTATION SEARCH ({len(clause_list)} clauses, 37 variables)")
print(f"{'='*60}")

N = 37
n_restarts = 30
n_iter_per = 100000
global_best_v = 1e9
global_best_orient = None

for restart in range(n_restarts):
    seed = 2000 + restart
    orient, v = sa_orient(N, clause_lookup, clause_list, 
                          n_iter=n_iter_per, seed=seed)
    if v < global_best_v:
        global_best_v = v
        global_best_orient = orient
        print(f"\n  🔥 Restart {restart+1}: NEW BEST = {v} violations!")
    elif restart % 5 == 4:
        print(f"  Restart {restart+1}: {v} (best: {global_best_v})")

# ===========================================================
# 结论
# ===========================================================
print(f"\n{'='*60}")
print(f"FINAL RESULT")
print(f"{'='*60}")
print(f"  config_408 2-factor: {len(clause_list)} clauses")
print(f"  Best orientation found: {global_best_v} violations")
print(f"  SDP lower bound: 12.5 → ceil = 13")
if global_best_v <= 15:
    print(f"\n  ✅ BROKE THE 16 BARRIER! Below 16!")
    print(f"     Saved to config_408_best_orient.json")
    result = {
        "m": 37,
        "edges": data["edges"],
        "best_violations": global_best_v,
        "best_orientation": global_best_orient,
        "n_clauses": len(clause_list),
        "sdp_lb": 12.5,
    }
    with open(f"{HERE}/results/config_408_best_orient.json", "w") as f:
        json.dump(result, f, indent=1)
else:
    print(f"\n  ❌ Still at {global_best_v} violations (16 is current SA best)")
    gap = min(global_best_v, 16)
    print(f"  SDP bound 12.5 → gap = ceil(12.5)={13} vs found={gap}")
    print(f"  Gap = {gap - 13} is from SDP relaxation not being tight")
    print(f"  OR from orientation search not finding global optimum")

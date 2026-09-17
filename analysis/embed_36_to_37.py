"""
embed_36_to_37.py — 从 m=36 解通过嵌入 vertex 36 生成 m=37 候选

策略：
1. 加载 m=36 解（已知的 C4 解，0 违例）
2. 将 vertex 36 嵌入 m=36 的 36-cycle 中，替代每条边
   即：对每条边 (a,b)，移除 (a,b)，添加 (a,36) 和 (36,b)
3. 共 36 种候选
4. 对每种用 CP-SAT 求最小违例数
5. 也尝试更激进的：同时替换 2-3 条边（~C(36,2)-C(36,3) 种）
"""

import sys, os, json, time
from collections import Counter

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import enumerate_clauses
from ortools.sat.python import cp_model

M = 37

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
        return int(solver.ObjectiveValue()), status == cp_model.OPTIMAL, round(elapsed, 1), n_cl
    return None, False, round(elapsed, 1), n_cl

# ===========================================================
# 加载 m=36 解
# ===========================================================
print("=" * 60)
print("EMBED m=36 SOLUTION → m=37")
print("=" * 60)

with open(f"{HERE}/results/solutions/m36.json") as f:
    m36_data = json.load(f)

# m=36 solution cells
m36_cells = [tuple(c) for c in m36_data["cells"]]
assert len(m36_cells) == 36

# Convert to canonical edges (u,v) with u<=v (for consistent clause counting)
m36_edges = [(u, v) if u <= v else (v, u) for u, v in m36_cells]
print(f"\n  m=36 solution: {len(m36_edges)} edges")

# Find the 36-cycle structure
# Build adjacency
adj = {i: [] for i in range(36)}
for u, v in m36_edges:
    adj[u].append(v)
    adj[v].append(u)

# Trace the cycle
visited = [False] * 36
cycle = []
current = 0
while not visited[current]:
    visited[current] = True
    cycle.append(current)
    # Find unvisited neighbor
    for n in adj[current]:
        if not visited[n]:
            current = n
            break
    else:
        # All visited - check if we're back to start
        if adj[current][0] == cycle[0] or adj[current][1] == cycle[0]:
            pass  # completed cycle
print(f"  Cycle structure: {cycle}")
print(f"  Cycle length: {len(cycle)}")

# Convert cycle to edges list
cycle_edges = []
for k in range(len(cycle)):
    a, b = cycle[k], cycle[(k+1) % len(cycle)]
    cycle_edges.append((a, b) if a <= b else (b, a))

print(f"  Cycle edges: {len(cycle_edges)}")

# ===========================================================
# 方法 1：嵌入 vertex 36，替代每条边
# ===========================================================
print(f"\n{'='*60}")
print("METHOD 1: Replace each edge with (a,36)+(36,b)")
print(f"{'='*60}")

results = []
global_best = 1e9
global_best_config = None

for i, (a, b) in enumerate(cycle_edges):
    # Build 37-vertex 2-factor: remove (a,b), add (a,36) and (36,b)
    new_edges = [(u, v) for u, v in m36_edges if not (u == a and v == b)]
    new_edges.append((a, 36) if a <= 36 else (36, a))
    new_edges.append((36, b) if 36 <= b else (b, 36))
    
    assert len(new_edges) == 37
    deg = Counter([u for e in new_edges for u in e])
    assert all(d == 2 for d in deg.values()), f"Degree fail at edge {i}"
    # Check duplicates
    assert len(set(new_edges)) == 37, f"Duplicate at edge {i}"
    
    min_v, optimal, t, n_cl = compute_min_violations(new_edges, timelimit=30)
    
    if min_v is not None:
        opt = "P" if optimal else "F"
        status = f"{min_v} violations ({opt}, {t}s, {n_cl} clauses)"
        results.append((min_v, optimal, t, n_cl, a, b))
        
        if min_v < global_best:
            global_best = min_v
            global_best_config = new_edges
            print(f"  ★ edge ({a},{b}) → {status}")
            if min_v < 16:
                print(f"    ★★★ BELOW 16! ★★★")
            else:
                print(f"    edge ({a},{b}) → {status}")


# ===========================================================
# 总结
# ===========================================================
print(f"\n{'='*60}")
print("RESULTS")
print(f"{'='*60}")

if results:
    best = min(results, key=lambda r: r[0])
    print(f"\n  Best single-edge embed: edge ({best[4]},{best[5]}) → {best[0]} violations")
    
    if best[0] < 16:
        print(f"\n  ★★★ FOUND {best[0]} VIOLATIONS < 16! ★★★")
        result = {
            "m": 37,
            "method": "embed_m36",
            "replaced_edge": [best[4], best[5]],
            "edges": [list(e) for e in global_best_config],
            "min_violations": best[0],
            "n_clauses": best[3],
        }
        with open(f"{HERE}/results/embed_m36_best.json", "w") as f:
            json.dump(result, f, indent=1)
    else:
        print(f"  All single-edge embeds give ≥ {best[0]} violations")
        print(f"  Best known = 16 (config_408)")
    
    # Distribution
    print(f"\n  Distribution:")
    dist = Counter(r[0] for r in results)
    for v in sorted(dist):
        print(f"    {v:3d} violations: {dist[v]} configs")
    
    # Show sorted
    print(f"\n  Sorted by violations:")
    for r in sorted(results, key=lambda r: r[0]):
        print(f"    edge ({r[4]:2d},{r[5]:2d}): {r[0]:3d} violations (P={r[1]}, {r[2]}s)")
else:
    print(f"  No valid results")

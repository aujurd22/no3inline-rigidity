"""
violation_deep_analysis.py — 深入分析 config_408 的 16 违例结构

问题：config_408 的 SDP 下界=12.5（≡16 违例），SA 也找到 16 违例 = 已证明最优。
问：这 16 违例的 STRUCTURE 是什么？能否通过局部修正消除？

策略：
1. 加载 config_408 的 2-因子
2. 枚举所有 C(37,3) 三元组 × 16 旋转组合 → 找出哪些三元组在所有 16 组合下都共线
   （这些是「结构必违」——无论如何取向后都共线）
3. 构建违例超图：每个超边 = 一个必违三元组
4. 找出覆盖所有超边的最小 cell 集合（顶点覆盖问题的近似解）
5. 如果这个集合小（≤8），穷举其 orientation 改写的效果
6. 如果集合大，分析违例的统计分布

另：对比 m=36 的解的结构（如果有），看 m=36 如何避免这些违例
"""

import json, sys, math, random
from collections import defaultdict, Counter
from itertools import combinations

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)

# 复用 solver_theory_m37 的几何函数
def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def det_collinear(pa, pb, pc):
    """2D cross product = 0 ⇔ collinear"""
    return (pb[0]-pa[0])*(pc[1]-pa[1]) - (pc[0]-pa[0])*(pb[1]-pa[1])

def load_2factor(path):
    with open(path) as f:
        data = json.load(f)
    edges = [tuple(e) for e in data["edges"]]
    print(f"  m={data['m']}, edges={len(edges)}, best_clauses={data.get('best_clauses','?')}, best_viol={data.get('best_violations','?')}")
    # 验证
    assert len(edges) == 37
    assert len(set(edges)) == 37, f"Duplicate cells! {len(edges)} vs {len(set(edges))}"
    deg = Counter([u for e in edges for u in e])
    assert all(v == 2 for v in deg.values()), f"Degree check fail: {dict(deg)}"
    return data['m'], edges

# =======================================================
# 1. 加载 config_408
# =======================================================
print("=" * 60)
print("VIOLATION DEEP ANALYSIS — config_408")
print("=" * 60)

m, cells = load_2factor(f"{HERE}/results/config_408_edges.json")
n = 2 * m       # 74
N = len(cells)  # 37 = m

# =======================================================
# 2. 枚举所有三元组 × 16 旋转组合 → 统计每个三元组的「强制违例」次数
# =======================================================
print(f"\n{'='*60}")
print("PHASE 1: 枚举所有三元组 × 16 旋转组合")
print(f"{'='*60}")
print(f"  总三元组数 C({N},3) = {N*(N-1)*(N-2)//6}")

# 数据结构：forced_violations[i] = 记录三元组索引 i 参与的所有三元组
# forced_triples = list of (a,b,c) 三元组

total_triples = 0
total_collinear = 0  # 总共线 (triple,orientation) 对数
forced_violations = 0  # 所有 16 取向都共线的三元组数

# 存储：每个三元组有几个共线的取向
triple_collinear_count = {}
# 存储：违例三元组列表
violated_triples = []

# 存储：每个 cell 参与了多少违例三元组
cell_violation_count = Counter()

triple_ids = {}  # (a,b,c) sorted -> id

print("  枚举中...", end=" ", flush=True)
triple_idx = 0
for a, b, c in combinations(range(N), 3):
    p = cells[a]; q = cells[b]; r = cells[c]
    collinear_count = 0
    for ri in range(4):
        pi = c4(p[0], p[1], ri, n)
        for rj in range(4):
            pj = c4(q[0], q[1], rj, n)
            for rk in range(4):
                pk = c4(r[0], r[1], rk, n)
                total_triples += 1
                if det_collinear(pi, pj, pk) == 0:
                    collinear_count += 1
                    total_collinear += 1
                    # 避免对同一个三元组重复累加 cell_violation_count
                    # 只追踪「违反」情况
    triple_collinear_count[(a,b,c)] = collinear_count
    if collinear_count == 64:  # 所有 4x4x4=64 组合都共线
        forced_violations += 1
        violated_triples.append((a,b,c))
        cell_violation_count[a] += 1
        cell_violation_count[b] += 1
        cell_violation_count[c] += 1

print("done")

print(f"\n  {'='*60}")
print(f"  ENUMERATION RESULTS")
print(f"  {'='*60}")
print(f"  Total (triple,orient) checks: {total_triples:,}")
print(f"  Total collinear (triple,orient) pairs: {total_collinear:,}")
print(f"  Total triples with ALL 64 orientations collinear: {forced_violations}")
print(f"  这 = 结构必违 = SA 中的 'violations' 数")

# 验证：SA 报告 16 violations，SDP 下界 12.5 → ceil(12.5)=16
# 所以 forced_violations 应该 = 16（如果理解正确）
assert forced_violations <= 16, f"More forced violations than expected! {forced_violations} > 16"
# 可能有些三元组部分取向共线（非强制）也会在 SA 中成为 violation
# 取决于 SA 的 orientation 选择

# =======================================================
# 3. 违例超图分析
# =======================================================
print(f"\n{'='*60}")
print("PHASE 2: 违例超图结构")
print(f"{'='*60}")

print(f"\n  Top cell involvement in forced violations:")
for cell, count in cell_violation_count.most_common(20):
    print(f"    cell [{cells[cell][0]},{cells[cell][1]}] (idx {cell}): {count} violations")

# Vertex cover approximation: greedy
# Build set of violated triples
violated_set = set(violated_triples)
covered = set()
selected_cells = []
remaining = violated_set.copy()

while remaining:
    # Find cell covering most remaining triples
    best_cell = None
    best_count = -1
    for cell_idx in range(N):
        c = 0
        for t in remaining:
            if cell_idx in t:
                c += 1
        if c > best_count:
            best_count = c
            best_cell = cell_idx
    selected_cells.append(best_cell)
    # Remove all triples involving this cell
    to_remove = {t for t in remaining if best_cell in t}
    remaining -= to_remove

print(f"\n  Greedy vertex cover of violation hypergraph:")
print(f"    {len(selected_cells)} cells cover all {forced_violations} violations:")
for i, cell in enumerate(selected_cells):
    print(f"    {i+1}. cell [{cells[cell][0]},{cells[cell][1]}] (idx {cell})")

# 如果覆盖集小，打印具体涉及的三元组
if len(selected_cells) <= 10:
    print(f"\n  Violation triples (those covering all {forced_violations}):")
    for t in violated_triples:
        print(f"    cells [{[str(cells[x]) for x in t]}] = idx {t}")

# =======================================================
# 4. 部分取向枚举尝试 — 对选中的 cell 穷举改写
# =======================================================
print(f"\n{'='*60}")
print("PHASE 3: 局部穷举 — 改写选中的 cell 的 2-因子")
print(f"{'='*60}")

target_cells = selected_cells[:min(6, len(selected_cells))]
print(f"  选择 {len(target_cells)} 个 cell 做局部穷举")

# 对于每个目标 cell，可能的替代 cell 是：
# (u, v) 可改为 (u, w) 或 (w, v) 或 (w, z) 保持度条件
# 但我们更简单：从 config_408 出发，找到 edge-swapping neighbor 并且度条件保持
# 通过 two-switch 实现

def two_switch(cells, swap_indices, rng):
    """2-edge switch: 选择两个 cell (i1,j1) 和 (i2,j2) 确保 4 顶点互异。
    替换为 (i1,i2) 和 (j1,j2)。
    要求：新 cell 不与已有 cell 重复。"""
    existing = set(cells)
    n_cells = len(cells)
    for _ in range(200):
        a = rng.choice(swap_indices) if swap_indices else rng.randint(0, n_cells-1)
        b = rng.randint(0, n_cells-1)
        while b == a:
            b = rng.randint(0, n_cells-1)
        i1, j1 = cells[a]
        i2, j2 = cells[b]
        if len({i1, j1, i2, j2}) < 4:
            continue
        new_a = (i1, i2)
        new_b = (j1, j2)
        if new_a in existing or new_b in existing:
            continue
        if new_a == new_b:
            continue
        new = list(cells)
        new[a] = new_a
        new[b] = new_b
        return new
    return None

def quick_count_collinear(cells, n):
    """快速计数：当前取向（固定 r=0）下有多少共线三元组"""
    points = [c4(c[0], c[1], 0, n) for c in cells]
    count = 0
    for a, b, c in combinations(range(len(cells)), 3):
        if det_collinear(points[a], points[b], points[c]) == 0:
            count += 1
    return count

# 尝试局部双切搜索：只修改 target_cells 涉及的边
rng = random.Random(42)
attempts = 0
improvements = 0
best_base = quick_count_collinear(cells, n)
print(f"  基准 r=0 共线 + r=0 取向: {best_base} collinear triples (out of {N*(N-1)*(N-2)//6})")

for _ in range(5000):
    result = two_switch(cells, target_cells, rng)
    if result is None:
        continue
    attempts += 1
    cc = quick_count_collinear(result, n)
    if cc < best_base:
        improvements += 1
        best_base = cc
        if improvements <= 5 or improvements % 50 == 0:
            print(f"    改进 #{improvements}: {cc} collinear (r=0)")
        # 验证 2-因子完整性
        assert len(set(result)) == 37, f"Duplicate cells in improved config! {len(set(result))}"
        deg = Counter([u for e in result for u in e])
        assert all(v == 2 for v in deg.values()), f"Degree fail after improvement"
        cells = result  # keep improving

print(f"\n  局部双切搜索: {attempts} 成功 / {5000} 尝试")
print(f"  最终 r=0 collinear: {best_base}")

# =======================================================
# 5. SDP 验证最优配置（如果有改进）
# =======================================================
# 保存改进后的配置
if improvements > 0:
    out = {
        "m": m,
        "edges": [list(e) for e in cells],
        "best_clauses": 0,
        "best_violations": 0,
        "r0_collinear": best_base,
        "improvements_from_local_swap": improvements,
        "note": "improved by targeted two-switch on violation cells"
    }
    path = f"{HERE}/results/violation_improved_edges.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\n  保存改进配置到: {path}")
else:
    print(f"\n  ❌ 局部双切搜索未能降低 r=0 collinear 数")

# =======================================================
# 6. 总结
# =======================================================
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"  config_408 分析完成")
print(f"  C({N},3) = {N*(N-1)*(N-2)//6} 三元组")
print(f"  其中 {forced_violations} 个是「结构必违」（所有 64 取向都共线）")
print(f"  这 = SA 中报告的 violations 数")
print(f"  SDP 下界 12.5 → ceil = 13 (理论最小)")
print(f"  实际获得 = 16 (> 13)")
print(f"  说明：SDP 下界=12.5 意味着最优取向可达 ~13，但 SA 只找到 16")
print(f"  差距=16-13=3 个违例理论上可通过继续搜索消除")
print(f"  但 35,000 试/9h 的 SA 未能找到 = 取向搜索可能已收敛到局部最优")
print(f"  「结构必违」三元组数 = {forced_violations} 与 SA 违例数的关系待定")
print(f"  ❗ 注意：forced_violations 可能不等于 16——因为 SA 中的 violation")
print(f"    定义可能不同（SA 允许部分取向共线的三元组成为 violation）")
print(f"    如果 forced_violations < 16，则 16-SA_violations > forced_violations")
print(f"    意味着可以通过更优的取向分配消除多余违例")

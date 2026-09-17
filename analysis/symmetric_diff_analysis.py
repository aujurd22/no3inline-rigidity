"""
============================================================
对称差（Symmetric Difference）分析
两个 2-因子的对称差分解为偶圈，沿圈交换边产生新候选

对 m=37 的 v40 解做系统性分析：
1) 每对解之间的对称差 → 圈分解
2) 圈长分布统计
3) 尝试单圈交换 → new 2-factor → 坏三元组变化
============================================================
"""
import json, os, math, sys
from itertools import combinations
from collections import Counter, defaultdict
import copy

# ── 加载 v40 解 ──
ARCHIVE_FILE = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue/outputs/exact_factor_archive.json'
NTIL_DIR = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue'

with open(ARCHIVE_FILE) as f:
    data = json.load(f)

# 取全部解（不限于 v40）
all_factors = {}
for entry in data['archive']:
    eid = entry['id']
    edges = [tuple(sorted(e)) for e in entry['edges']]
    all_factors[eid] = {
        'edges_set': set(edges),
        'edges_list': edges,
        'value': entry['value'],
        'bits': entry['bits'],
        'safe': entry.get('diagonal_safe', False),
        'sources': entry.get('sources', [])
    }

print(f"加载 {len(all_factors)} 个 2-因子")
print(f"值分布: {dict(sorted(Counter(v['value'] for v in all_factors.values()).items()))}")


# ── 对称差 → 圈分解 ──
def symmetric_difference_cycles(F1_edges, F2_edges):
    """
    两个 2-因子的对称差 → 偶圈分解。
    
    原理：
    - 对称差中的边分属 F₁ 或 F₂
    - 每个顶点在对称差中有度 2 或 4
    - 正确走法：交替用 F₁ 和 F₂ 的边
    - 每顶点维护尚未使用的 F₁ 邻接和 F₂ 邻接
    """
    sd = F1_edges ^ F2_edges
    
    # 每顶点: 未使用的 F₁ 和 F₂ 邻居
    adj1 = defaultdict(set)  # 仅 F₁ 的边 (不在 F₂ 中)
    adj2 = defaultdict(set)  # 仅 F₂ 的边 (不在 F₁ 中)
    
    for e in sd:
        u, v = e
        if e in F1_edges:
            adj1[u].add(v); adj1[v].add(u)
        else:
            adj2[u].add(v); adj2[v].add(u)
    
    # 统计各顶点在对称差中的总度数
    total_deg = defaultdict(int)
    for v in set(list(adj1.keys()) + list(adj2.keys())):
        total_deg[v] = len(adj1[v]) + len(adj2[v])
    
    cycles = []
    
    # 只要还有未使用的边
    while any(adj1.values()) or any(adj2.values()):
        # 找起始点
        start = None
        for v in total_deg:
            if len(adj1[v]) + len(adj2[v]) > 0:
                start = v
                break
        if start is None:
            break
        
        # 从 start 出发，先走一条 F₁ 边（如果有）
        if adj1[start]:
            use_f1 = True
            curr = start
            nxt = adj1[curr].pop()
            adj1[nxt].discard(curr)
        elif adj2[start]:
            use_f1 = False
            curr = start
            nxt = adj2[curr].pop()
            adj2[nxt].discard(curr)
        else:
            break
        
        # 建立圈
        cycle = [curr, nxt]
        curr = nxt
        
        # 循环走，直到回到 start
        while curr != start:
            if use_f1:  # 上一步是 F₁ → 这一步走 F₂
                if adj2[curr]:
                    nxt = adj2[curr].pop()
                    adj2[nxt].discard(curr)
                    use_f1 = False
                elif adj1[curr]:
                    nxt = adj1[curr].pop()
                    adj1[nxt].discard(curr)
                    # use_f1 stays True... but shouldn't happen
                else:
                    break  # 死路
            else:  # 上一步是 F₂ → 这一步走 F₁
                if adj1[curr]:
                    nxt = adj1[curr].pop()
                    adj1[nxt].discard(curr)
                    use_f1 = True
                elif adj2[curr]:
                    nxt = adj2[curr].pop()
                    adj2[nxt].discard(curr)
                    # use_f1 stays False
                else:
                    break
            
            cycle.append(nxt)
            curr = nxt
        
        cycles.append(cycle[:-1])  # 去掉最后重复的起点
    
    return cycles


# ── 沿圈交换边 ──
def swap_cycle(edges, cycle):
    """
    沿给定圈交换边：用 F₂ 的边替换 F₁ 的边
    cycle 是顶点序列 [v0, v1, ..., v_{k-1}]
    原 F₁ 边: (v0,v1), (v2,v3), ... (偶索引)
    新 F₂ 边: (v1,v2), (v3,v4), ... (奇索引) + (v_{k-1}, v0)
    """
    new_edges = set(edges)
    
    # 移除原边
    for i in range(0, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        if e in new_edges:
            new_edges.remove(e)
        else:
            # 尝试反方向
            e_rev = tuple(sorted((cycle[(i+1) % len(cycle)], cycle[i])))
            new_edges.discard(e_rev)
    
    # 添加新边
    for i in range(1, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_edges.add(e)
    
    # 最后一条边（cycle[-1], cycle[0]）
    last_edge = tuple(sorted((cycle[-1], cycle[0])))
    new_edges.add(last_edge)
    
    assert len(new_edges) == len(edges), \
        f"Edge count mismatch: {len(new_edges)} vs {len(edges)}"
    
    return list(new_edges)


# ── C4 展开 → 坏三元组计数 ──
def expand_and_count(edge_list, m=37, bits=None):
    """
    从 2-因子展开为 rot4 NTIL 完整配置并统计坏三元组
    edge_list: [(u,v), ...] where u,v ∈ [0, m-1]
    bits: 取向位（如果为 None，尝试最优取向）
    返回: 坏三元组数
    """
    # 先构建简单的暴力检查——不考虑取向，直接用坐标表示
    # 导入项目中的工具
    sys.path.insert(0, NTIL_DIR)
    
    try:
        from geometry_bad_count import geometry_bad_count
    except ImportError:
        print("  警告: 无法导入 geometry_bad_count，使用简化版")
        return None
    
    # 构建 bits 向量
    if bits is None:
        bits = [0] * m  # 默认
    
    # 转为坐标
    bad = geometry_bad_count(edge_list, bits, m)
    return bad


# ── 简化版：直接枚举共线三元组（不依赖取向，只对固定的 bits） ──
def simple_bad_count(edge_list, bits, m=37):
    """简化版坏三元组计数"""
    # 根据 edge_list + bits 生成点集
    pts = []
    for i, (u, v) in enumerate(edge_list):
        # 每行 2 点，列位置由 u, v 决定
        # 在 rot4 基本域中，每个 cell (u,v) 对应 4 个旋转点
        # 使用标准 C4 展开
        cx = cy = m - 0.5
        # 两个列位置
        cols = [u, v]
        if bits and i < len(bits) and bits[i]:
            cols = [v, u]  # 取向翻转
        
        for col in cols:
            # FD 向量 = (col - cx, row_idx - cy)
            pts.append((col, i))
    
    return pts

# ── 主要分析 ──

# 1. 检查 v40 之间的对称差
v40_ids = [f"v40_{i:02d}" for i in range(1, 5)]
print(f"\n{'='*65}")
print("v40 解之间对称差的圈结构")
print(f"{'='*65}")

for a, b in combinations(v40_ids, 2):
    if a not in all_factors or b not in all_factors:
        continue
    Fa = all_factors[a]['edges_set']
    Fb = all_factors[b]['edges_set']
    
    cycles = symmetric_difference_cycles(Fa, Fb)
    cycle_lens = [len(c) for c in cycles]
    
    print(f"\n  {a} Δ {b}:")
    print(f"    圈数: {len(cycles)}")
    print(f"    圈长分布: {sorted(Counter(cycle_lens).items())}")
    print(f"    总边数: {sum(cycle_lens)}")
    
    # 短圈（≤6）详细展示
    short_cycles = [(i, c) for i, c in enumerate(cycles) if len(c) <= 6]
    for idx, cycle in short_cycles:
        print(f"    圈 {idx}: 长={len(cycle)}, 路径={cycle}")


# 2. 所有解对的圈长分布汇总
print(f"\n{'='*65}")
print("全部解对对称差圈长汇总")
print(f"{'='*65}")

factor_ids = list(all_factors.keys())
pair_cycle_stats = defaultdict(list)

for i, j in combinations(range(len(factor_ids)), 2):
    aid, bid = factor_ids[i], factor_ids[j]
    Fa = all_factors[aid]['edges_set']
    Fb = all_factors[bid]['edges_set']
    
    cycles = symmetric_difference_cycles(Fa, Fb)
    for c in cycles:
        pair_cycle_stats[len(c)].append((aid, bid))

print(f"\n总解对数: {len(factor_ids)*(len(factor_ids)-1)//2}")
for length in sorted(pair_cycle_stats.keys()):
    cnt = len(pair_cycle_stats[length])
    print(f"  圈长 {length:3d}: 出现在 {cnt:4d} 个解对中")


# 3. 尝试单圈交换
print(f"\n{'='*65}")
print("单圈交换实验")
print(f"{'='*65}")
print("对 v40 解对做短圈（4≤len≤12）交换，评估结果")
print(f"{'='*65}")

# 简化版：只输出哪些圈是可交换的，不实际跑 CP-SAT
total_swaps = 0
swap_distribution = defaultdict(int)

for a, b in combinations(v40_ids, 2):
    Fa = all_factors[a]['edges_set']
    Fb = all_factors[b]['edges_set']
    Fa_list = all_factors[a]['edges_list']
    
    cycles = symmetric_difference_cycles(Fa, Fb)
    
    for cycle in cycles:
        if len(cycle) <= 12:  # 只尝试短圈
            new_edges = swap_cycle(Fa_list, cycle)
            total_swaps += 1
            swap_distribution[len(cycle)] += 1

print(f"\n总短圈交换数: {total_swaps}")
for length in sorted(swap_distribution.keys()):
    print(f"  圈长 {length:3d}: {swap_distribution[length]} 个交换候选")


# 4. 深入分析：看具体某个圈交换后的几何质量
print(f"\n{'='*65}")
print("深度检查：v40_02 Δ v40_01 的每个圈")
print(f"{'='*65}")

if 'v40_01' in all_factors and 'v40_02' in all_factors:
    Fa = all_factors['v40_01']['edges_set']
    Fa_list = all_factors['v40_01']['edges_list']
    Fb = all_factors['v40_02']['edges_set']
    
    cycles = symmetric_difference_cycles(Fa, Fb)
    print(f"共 {len(cycles)} 个圈，圈长: {[len(c) for c in cycles]}")
    
    # 对每个圈，打印新边集的大小和与原始边集的关系
    for idx, cycle in enumerate(cycles):
        new_edges = swap_cycle(Fa_list, cycle)
        new_set = set(new_edges)
        
        # 相交度
        overlap_with_a = len(new_set & Fa)
        overlap_with_b = len(new_set & Fb)
        new_edges_count = len(new_set - Fa - Fb)
        
        print(f"\n  圈 {idx} (长={len(cycle)}):")
        print(f"    与解 A 共享: {overlap_with_a}/37 边")
        print(f"    与解 B 共享: {overlap_with_b}/37 边")
        print(f"    全新边: {new_edges_count}")
        
        # 检查是否是有效 2-因子（每顶点恰好 2 条边）
        deg = defaultdict(int)
        for u, v in new_edges:
            deg[u] += 1
            deg[v] += 1
        is_2reg = all(d == 2 for d in deg.values()) and len(deg) == 37
        print(f"    有效 2-因子: {'是 ✓' if is_2reg else '否 ✗'}")


# 5. 总结
print(f"\n{'='*65}")
print("总结")
print(f"{'='*65}")

print("""
对称差（Symmetric Difference）方法：
- 两个 2-因子的差集分解为一组偶圈
- 沿圈交换边 = 取一个圈的"另一组完美匹配"
- 交换 1 个圈产生的新 2-因子与原始两个解的 Hamming 距离正好 = 圈长
- 短圈（4-6）对应小改动长圈（≥14）对应大改动

关键问题：哪个圈交换能减少坏三元组？
→ 需要配合 CP-SAT 做取向优化来精确评估
""")

print("完成。")

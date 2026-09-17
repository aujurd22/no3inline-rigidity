"""
从已知 rot4 解中提取双排列结构，分析冲突在多尺度的分布。
m=5,10,14,36 的已知解 → 对应的双排列 π,σ。
"""
import sys, json, itertools
from collections import Counter, defaultdict
sys.path.insert(0, '.')
from validate_solver import load_positive, c4_lifts_n

def rot4_solution_to_points(edges, bits, N):
    """将 rot4 解展开为 N×N 网格上的 2N 个点"""
    pts = []
    for (u,v), b in zip(edges, bits):
        dc = (v,u) if b else (u,v)
        pts.extend(c4_lifts_n(dc, N))
    return pts

def points_to_perms(pts, n):
    """将 2n 个点 (每行恰2) 分解为两个排列 π,σ。
    返回 (π_arr, σ_arr) where π[i]=第 i 行第 1 个点的 y 坐标。"""
    rows = defaultdict(list)
    for x, y in pts:
        rows[x].append(y)
    pi = [0]*n
    sigma = [0]*n
    for i in range(n):
        ys = sorted(rows[i])
        pi[i] = ys[0]
        sigma[i] = ys[1]
    return pi, sigma

def analyze_conflicts(pi, sigma, n):
    """分析双排列的冲突分布（按方向尺度分层）"""
    points = [(i, pi[i]) for i in range(n)] + [(i, sigma[i]) for i in range(n)]
    
    # 按方向分类所有共线三元组
    conflicts_by_scale = defaultdict(int)
    all_conflicts = []
    
    for (i1, i2, i3) in itertools.combinations(range(2*n), 3):
        x1,y1 = points[i1]; x2,y2 = points[i2]; x3,y3 = points[i3]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            dx = max(abs(x3-x1), abs(x2-x1), abs(x3-x2))
            dy = max(abs(y3-y1), abs(y2-y1), abs(y3-y2))
            dmax = max(dx, dy)
            # 二进尺度
            scale = dmax.bit_length() - 1 if dmax > 0 else 0
            # 类型: 涉及几个 π 点几个 σ 点
            types = []
            for idx in [i1, i2, i3]:
                types.append('π' if idx < n else 'σ')
            conflicts_by_scale[scale] += 1
            all_conflicts.append((scale, types, (x1,y1),(x2,y2),(x3,y3)))
    
    return conflicts_by_scale, all_conflicts

def perm_stats(pi, sigma, n):
    """排列的结构统计"""
    # 循环分解
    def cycles(perm):
        visited = [False]*n
        cyc = []
        for i in range(n):
            if not visited[i]:
                c = []
                j = i
                while not visited[j]:
                    visited[j] = True
                    c.append(j)
                    j = perm[j]
                if len(c) > 1:
                    cyc.append(c)
        return cyc
    
    pi_cycles = cycles(pi)
    sig_cycles = cycles(sigma)
    
    # 差排列 σ∘π⁻¹
    pi_inv = [0]*n
    for i, v in enumerate(pi): pi_inv[v] = i
    diff = [sigma[i] - pi[i] for i in range(n)]
    
    return {
        'pi_cycle_lengths': sorted([len(c) for c in pi_cycles]),
        'sigma_cycle_lengths': sorted([len(c) for c in sig_cycles]),
        'diff_distribution': Counter(diff),
        'n_fixed_pi': n - sum(len(c) for c in pi_cycles),
        'n_fixed_sigma': n - sum(len(c) for c in sig_cycles),
    }

# ===== 分析所有已知解 =====
for m_label in [5, 10, 14, 36]:
    edges, bits, src = load_positive(m_label)
    N = 2 * len(edges)
    pts = rot4_solution_to_points(edges, bits, N)
    
    # 验证每行每列恰 2 点
    row_cnt = Counter(x for x,y in pts)
    col_cnt = Counter(y for x,y in pts)
    assert all(c == 2 for c in row_cnt.values()), f"m={m_label}: 行计数异常 {dict(row_cnt)}"
    assert all(c == 2 for c in col_cnt.values()), f"m={m_label}: 列计数异常"
    
    pi, sigma = points_to_perms(pts, N)
    stats = perm_stats(pi, sigma, N)
    conf_by_scale, all_c = analyze_conflicts(pi, sigma, N)
    
    print(f"\n{'='*60}")
    print(f"m={m_label} (n={N}, 2n={2*N} pts) — 来源: {src}")
    print(f"{'='*60}")
    print(f"π 循环长度: {stats['pi_cycle_lengths'][:10]}{'...' if len(stats['pi_cycle_lengths'])>10 else ''}")
    print(f"σ 循环长度: {stats['sigma_cycle_lengths'][:10]}{'...' if len(stats['sigma_cycle_lengths'])>10 else ''}")
    print(f"固定点: π={stats['n_fixed_pi']}, σ={stats['n_fixed_sigma']}")
    print(f"差分布 top5: {stats['diff_distribution'].most_common(5)}")
    print(f"共线三元组数: {sum(conf_by_scale.values())} (应为0)")
    print(f"冲突尺度分布: {dict(sorted(conf_by_scale.items()))}")
    
    # 如果有冲突，展示前 3 个
    if all_c:
        print(f"前 3 个冲突:")
        for scale, types, p1, p2, p3 in all_c[:3]:
            print(f"  scale={scale}, type={''.join(types)}: {p1}, {p2}, {p3}")

# ===== 额外：分析 m=5 的交替环结构 =====
print(f"\n{'='*60}")
print(f"m=5 交替环分析")
print(f"{'='*60}")
edges5, bits5, _ = load_positive(5)
N5 = 10
pts5 = rot4_solution_to_points(edges5, bits5, N5)
pi5, sigma5 = points_to_perms(pts5, N5)

# 找交替 4-环: 两个行 i,j 间的 σ 值交换
print(f"π={pi5}")
print(f"σ={sigma5}")
print(f"逐行: ", end="")
for i in range(N5):
    print(f"({i}: π={pi5[i]}, σ={sigma5[i]})", end="  ")
print()

# 构造交替图：顶点=行，边=(i,j)如果交换σ[i],σ[j]后行列约束保持
# 行列约束：交换σ[i],σ[j]后，列约束不变（因为σ是排列，交换后仍是排列）
# 行约束也不变（每行仍有2点）
# 唯一影响：可能产生新的三点共线
# 检查所有可能的4-环交换
print("\n交替4-环候选（交换σ[i]↔σ[j]后检查）：")
good_switches = []
for i in range(N5):
    for j in range(i+1, N5):
        # 模拟交换
        sigma2 = sigma5.copy()
        sigma2[i], sigma2[j] = sigma2[j], sigma2[i]
        pts_new = [(r, pi5[r]) for r in range(N5)] + [(r, sigma2[r]) for r in range(N5)]
        bad = 0
        for (i1,i2,i3) in itertools.combinations(range(2*N5), 3):
            x1,y1=pts_new[i1]; x2,y2=pts_new[i2]; x3,y3=pts_new[i3]
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                bad += 1
        if bad == 0:
            good_switches.append((i, j))
            print(f"  交换行{i}↔{j}: σ[{i}]{sigma5[i]}↔σ[{j}]{sigma5[j]} → 0冲突 ✓")

print(f"\n共 {len(good_switches)} 个可交换对")
if good_switches:
    print("→ 交替4-环吸收器存在，可用于修补其他配置的缺陷")

"""
向量代数深入探索：三个方向
1) 范数壳层 (norm shell) + 壳层间角度
2) 跨 m 归一化角度分布对比
3) Minkowski 和 → NTIL 候选解
"""

import os, math, json
from collections import defaultdict
from itertools import combinations
import numpy as np

# ── 加载器 ─────────────────────────────────────────────────────────────
ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}
SYMM = set('.:/-ocx+*')
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def decode_line(line, n):
    line = line.strip()
    body = line[1:] if line and line[0] in SYMM else line
    pts = []
    for r in range(n):
        pts.append((VAL[body[2*r]], r))
        pts.append((VAL[body[2*r+1]], r))
    return pts

def load_rot4_one(n, idx=0):
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if os.path.exists(path):
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip()]
            if idx < len(lines):
                return decode_line(lines[idx], n)
    return None

def get_fd_vectors(pts, n):
    """基本域向量集（按角度排序）"""
    m = n // 2
    cx = cy = (n - 1) / 2.0
    vecs = [(x - cx, y - cy) for (x, y) in pts]
    # C4 轨道分组取代表
    seen = set()
    fd = []
    for v in vecs:
        rots = [v, (-v[1], v[0]), (-v[0], -v[1]), (v[1], -v[0])]
        canon = min(rots)
        if canon not in seen:
            seen.add(canon)
            fd.append(v)
    assert len(fd) == 2 * n // 4
    fd.sort(key=lambda v: math.atan2(v[1], v[0]))
    return fd

# 验证 NTIL
def collinear_count(pts):
    cnt = 0
    for a, b, c in combinations(pts, 3):
        if (b[0]-a[0])*(c[1]-a[1]) == (c[0]-a[0])*(b[1]-a[1]):
            cnt += 1
    return cnt

def expand_c4(fd_vecs, n):
    """基本域向量 → 148 点完整配置"""
    cx = cy = (n - 1) / 2.0
    pts = []
    for vx, vy in fd_vecs:
        pts.append((vx + cx, vy + cy))
        pts.append((-vy + cx, vx + cy))
        pts.append((-vx + cx, -vy + cy))
        pts.append((vy + cx, -vx + cy))
    # 检查重复
    assert len(set(pts)) == len(pts), f"重复点! {len(pts)} vs {len(set(pts))}"
    return pts

# ── 方向 1: 范数壳层 ──────────────────────────────────────────────────

def shell_analysis(n):
    sols = []
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if os.path.exists(path):
            with open(path) as f:
                sols = [decode_line(l.strip(), n) for l in f if l.strip() and len(decode_line(l.strip(), n)) == 2*n]
            break
    if len(sols) < 2:
        return None

    print(f"\n{'='*60}")
    print(f"方向 1: 范数壳层分析 n={n} (m={n//2}, {len(sols)} 解)")
    print(f"{'='*60}")

    # 取第一个解做详细壳层分析
    fd0 = get_fd_vectors(sols[0], n)
    norms = [round(math.hypot(vx, vy), 6) for (vx, vy) in fd0]
    angles = [math.atan2(vy, vx) for (vx, vy) in fd0]

    # 按范数分组
    shells = defaultdict(list)
    for i, (v, nr, ang) in enumerate(zip(fd0, norms, angles)):
        shells[nr].append({'idx': i, 'vec': v, 'angle_deg': round(math.degrees(ang), 2)})

    print(f"  范数壳层数: {len(shells)} (共 {len(fd0)} 向量)")
    for nr in sorted(shells):
        grp = shells[nr]
        angles_str = ', '.join(f"{g['angle_deg']:.1f}°" for g in grp)
        print(f"    |v|={nr:.3f}: {len(grp)} 个向量, 角度=[{angles_str}]")

    # 壳层间角度差（不同范数向量之间的夹角分布）
    intra_angles = []  # 同一壳层内
    inter_angles = []  # 不同壳层间
    for i in range(len(fd0)):
        for j in range(i+1, len(fd0)):
            vi, vj = fd0[i], fd0[j]
            dot = vi[0]*vj[0] + vi[1]*vj[1]
            ni = math.hypot(*vi)
            nj = math.hypot(*vj)
            cos_a = max(-1, min(1, dot/(ni*nj)))
            ang = math.degrees(math.acos(cos_a))
            if abs(ni - nj) < 1e-10:
                intra_angles.append(ang)
            else:
                inter_angles.append(ang)

    if intra_angles:
        print(f"  同一壳层内夹角: 均值={np.mean(intra_angles):.1f}°, 范围=[{min(intra_angles):.1f}°, {max(intra_angles):.1f}°]")
    else:
        print(f"  同一壳层内夹角: (每范数仅 1 向量, 无配对内角)")
    print(f"  跨壳层夹角: 均值={np.mean(inter_angles):.1f}°, 范围=[{min(inter_angles):.1f}°, {max(inter_angles):.1f}°]")

    # 跨解对比同一(norm_id, angle)模式
    print(f"\n  跨解范数壳层一致性:")
    for idx in range(min(3, len(sols))):
        fd = get_fd_vectors(sols[idx], n)
        nrm_set = sorted(set(round(math.hypot(vx, vy), 3) for (vx, vy) in fd))
        print(f"    解 {idx}: {len(nrm_set)} 种范数 → {nrm_set}")

    return shells

# ── 方向 2: 跨 m 角度分布 ──────────────────────────────────────────────

def angular_distribution_across_m(ns):
    print(f"\n{'='*60}")
    print(f"方向 2: 跨 m 归一化角度分布")
    print(f"{'='*60}")

    for n in ns:
        sols = None
        for ext in ('', '.few', '.mvr'):
            path = os.path.join(CACHE, f'n{n}_rot4{ext}')
            if os.path.exists(path):
                with open(path) as f:
                    sols = [decode_line(l.strip(), n) for l in f if l.strip() and len(decode_line(l.strip(), n)) == 2*n]
                break
        if not sols:
            continue

        m = n // 2
        fd = get_fd_vectors(sols[0], n)
        angles = sorted([math.degrees(math.atan2(vy, vx)) for (vx, vy) in fd])

        # 角度集中在第二象限 [-180, 0] 或 [-180, -90]
        # 归一化到 [0, 1]
        ang_min, ang_max = angles[0], angles[-1]
        span = ang_max - ang_min
        norm_angles = [(a - ang_min) / span for a in angles]

        # 角度差（相邻向量间的角距）
        adj_diffs = []
        for i in range(len(angles)):
            d = angles[(i+1) % len(angles)] - angles[i]
            if d < 0:
                d += 360
            adj_diffs.append(d)
        mean_gap = sum(adj_diffs) / len(adj_diffs)
        std_gap = np.std(adj_diffs)
        min_gap = min(adj_diffs)
        max_gap = max(adj_diffs)

        print(f"  n={n:3d} (m={m:2d}): 角度范围=[{ang_min:.1f}°, {ang_max:.1f}°], "
              f"跨度={span:.1f}°, 间距均值={mean_gap:.2f}°±{std_gap:.2f}°, "
              f"最小={min_gap:.2f}°, 最大={max_gap:.2f}°")

        # 与均匀分布的偏差
        uniform_gap = 360.0 / m
        dev = [abs(d - uniform_gap) for d in adj_diffs]
        print(f"    与均匀间距({uniform_gap:.2f}°)偏差: 均值={np.mean(dev):.2f}°, 最大={max(dev):.2f}°")

# ── 方向 3: Minkowski 和 → NTIL 候选 ──────────────────────────────────

def minkowski_ntil_experiment(n):
    sols = None
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if os.path.exists(path):
            with open(path) as f:
                sols = [decode_line(l.strip(), n) for l in f if l.strip() and len(decode_line(l.strip(), n)) == 2*n]
            break
    if not sols or len(sols) < 2:
        return

    print(f"\n{'='*60}")
    print(f"方向 3: Minkowski 和 → NTIL 候选 (n={n}, {len(sols)} 解)")
    print(f"{'='*60}")

    fd_sets = [get_fd_vectors(s, n) for s in sols]

    # 3a) Minkowski 和的碰撞分析
    print(f"\n  3a) Minkowski 和碰撞率:")
    for i, j in combinations(range(min(5, len(sols))), 2):
        va = fd_sets[i]
        vb = fd_sets[j]
        # 所有 v_a + v_b (去重)
        msum = set()
        for vi in va:
            for vj in vb:
                msum.add((round(vi[0] + vj[0], 10), round(vi[1] + vj[1], 10)))
        m_sq = len(va) * len(vb)
        collision_pct = (1 - len(msum) / m_sq) * 100
        print(f"    解 {i} ⊕ 解 {j}: |和|={len(msum)}/{m_sq} ({collision_pct:.1f}% 碰撞)")

    # 3b) 检查 Minkowski 和中哪些点集构成 rot4 NTIL?
    # 思路：取 Minkowski 和，看是否包含一个恰好 m 个向量的子集，
    # 使得在 C4 展开后给出 NTIL 解
    print(f"\n  3b) 是否和集中有 FD 向量出现在原解中?")
    for i, j in combinations(range(min(5, len(sols))), 2):
        va_set = {(round(v[0],8), round(v[1],8)) for v in fd_sets[i]}
        vb_set = {(round(v[0],8), round(v[1],8)) for v in fd_sets[j]}
        va_arr = fd_sets[i]
        vb_arr = fd_sets[j]
        msum_all = set()
        for vi in va_arr:
            for vj in vb_arr:
                msum_all.add((round(vi[0] + vj[0], 8), round(vi[1] + vj[1], 8)))

        # 检查 Minkowski 和是否包含 va 或 vb 的元素
        overlap_a = len(msum_all & va_set)
        overlap_b = len(msum_all & vb_set)
        print(f"    解 {i}⊕{j}: 和集包含解{i}的 {overlap_a}/{len(va_set)}, "
              f"包含解{j}的 {overlap_b}/{len(vb_set)}")

    # 3c) 自 Minkowski 和：v_a - v_b 差集
    print(f"\n  3c) 差集 (v_a - v_b) 中的 NTIL 候选:")
    for i, j in combinations(range(min(5, len(sols))), 2):
        va = fd_sets[i]
        vb = fd_sets[j]
        diff_set = set()
        for vi in va:
            for vj in vb:
                diff = (round(vi[0] - vj[0], 8), round(vi[1] - vj[1], 8))
                diff_set.add(diff)

        # 检查差集中是否有恰好 m 个向量、互不重复、且可 C4 展开
        # 简单检查：差集大小
        m = n // 2
        n_subsets = len(diff_set)
        print(f"    解 {i}⊖{j}: |差集|={n_subsets} (m={m})")

        # 尝试：将差集中的每个向量 + 对应原向量的组合
        # 不太可能有意义，但先展示统计

    # 3d) 取两个基础解的平均值
    print(f"\n  3d) 平均向量集 (v_a + v_b)/2:")
    for i, j in combinations(range(min(3, len(sols))), 2):
        va = fd_sets[i]
        vb = fd_sets[j]
        # 按角度排序后配对平均
        sa = sorted(va, key=lambda v: math.atan2(v[1], v[0]))
        sb = sorted(vb, key=lambda v: math.atan2(v[1], v[0]))
        avg_vecs = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(len(sa))]
        # 检查：展开成 4m 点后有多少几何坏三元组？
        pts = expand_c4(avg_vecs, n)
        bad = collinear_count(list(set(pts)))
        print(f"    解 {i}⊕{j} 平均: 展开 {len(pts)} 点, "
              f"重复={len(pts)-len(set(pts))}, 坏三元组={bad}")

# ── 运行 ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    small_n = [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36]
    large_n = [40, 44]

    # 方向 1: 对几个代表性的 n 做壳层分析
    for n in [10, 16, 20, 30, 36]:
        shell_analysis(n)

    # 方向 2: 跨 m 对比
    angular_distribution_across_m([6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36, 40, 44])

    # 方向 3: Minkowski 和实验（只在解数较少的 n 上跑）
    for n in [10, 12, 14, 16, 18, 20]:
        minkowski_ntil_experiment(n)

    print("\n完成。")

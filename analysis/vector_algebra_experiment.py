"""
向量代数实验：将 rot4 偶数解表示为「基本域 → 原点向量」后做代数运算。

核心思想：
  n=2m 网格，rot4 解有 4m 个点。
  1) 将网格中心平移到原点 O
  2) 对每个 C4 轨道取一个代表点 p，得向量 v = p - O
  3) 基本域 H_m 有 m 个向量（每个 C4 轨道恰一个）
  4) 对不同解做向量集运算：加、减、内积、外积、Gram 矩阵…

含义：
  "没有点的地方为 0" — 基本域的每个 cell 要么有向量 v，要么是零向量。
  因此每个解可视为向量值函数 f: H_m → R² ∪ {0}。
  跨解运算即函数空间中的代数操作。

输出：报告各种运算的发现。
"""

import os, sys, math, json
from collections import defaultdict
from itertools import combinations
import numpy as np

# ── 1. 加载 Flammenkamp rot4 解 ─────────────────────────────────────────

ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}
SYMM = set('.:/-ocx+*')

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def decode_line(line, n):
    """解码 Flammenkamp 一行 → list of (x=col, y=row)."""
    line = line.strip()
    body = line[1:] if line and line[0] in SYMM else line
    pts = []
    for r in range(n):
        c1 = VAL[body[2 * r]]
        c2 = VAL[body[2 * r + 1]]
        pts.append((c1, r))
        pts.append((c2, r))
    return pts

def load_rot4_all(n):
    """Load ALL rot4 solutions for given n (return list of point lists)."""
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if not os.path.exists(path):
            continue
        sols = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                pts = decode_line(line, n)
                if len(pts) == 2 * n:
                    sols.append(pts)
        return sols
    return []

# ── 2. 基本域向量提取 ──────────────────────────────────────────────────

def center_and_extract_fd(pts, n):
    """
    输入: pts = [(x,y) ...], 共 2n 点 (n=2m)
    输出: fd_vectors = list of (vx, vy) — 基本域 m 个向量，按规范顺序
          zero_positions = list of bool — 哪些"理论 cell"没有点
    注意: n=2m, 坐标范围 [0, n-1], 中心 C = ((n-1)/2, (n-1)/2)
    """
    n = int(n)
    m = n // 2
    cx = cy = (n - 1) / 2.0  # = m - 0.5

    # 平移至中心
    vecs = [(x - cx, y - cy) for (x, y) in pts]

    # 去重 + 分组为 C4 轨道
    # C4: (x,y) → (-y,x) → (-x,-y) → (y,-x)
    # 对每个点，找出其 C4 轨道，选代表
    seen = set()
    orbits = []
    for v in vecs:
        # 归一化: 四种旋转选"规范"代表
        vx, vy = v
        # 四个旋转
        rots = [(vx, vy), (-vy, vx), (-vx, -vy), (vy, -vx)]
        # 选词典序最小的作为轨道 ID
        canon = min(rots)
        if canon not in seen:
            seen.add(canon)
            orbits.append(v)
        # 否则跳过（已处理）

    assert len(orbits) == 2 * n // 4, f"预期 {2*n//4} 轨道, 实际 {len(orbits)}"

    # 按角度排序（保持一致性）
    def angle(v):
        return math.atan2(v[1], v[0])
    orbits.sort(key=angle)

    return orbits


def vector_set(pts, n):
    """
    返回基本域向量集 + 元信息
    """
    m = n // 2
    vecs = center_and_extract_fd(pts, n)
    # 向量范数
    norms = [math.hypot(vx, vy) for (vx, vy) in vecs]
    # 角度
    angles = [math.atan2(vy, vx) for (vx, vy) in vecs]
    return {
        'm': m,
        'n': n,
        'vectors': vecs,
        'norms': norms,
        'angles': angles,
        'norm_set': sorted(set(round(n, 10) for n in norms)),
    }


# ── 3. 代数运算 ─────────────────────────────────────────────────────────

def gram_matrix(vecs):
    """Gram 矩阵 G_ij = v_i · v_j"""
    m = len(vecs)
    G = np.zeros((m, m))
    for i in range(m):
        for j in range(m):
            G[i, j] = vecs[i][0] * vecs[j][0] + vecs[i][1] * vecs[j][1]
    return G

def cross_matrix(vecs):
    """外积(行列式)矩阵 D_ij = det(v_i, v_j) = v_i_x * v_j_y - v_i_y * v_j_x"""
    m = len(vecs)
    D = np.zeros((m, m))
    for i in range(m):
        for j in range(m):
            D[i, j] = vecs[i][0] * vecs[j][1] - vecs[i][1] * vecs[j][0]
    return D

def pairwise_dot(vecs_i, vecs_j):
    """两个解之间的所有配对点积"""
    dots = []
    for vi in vecs_i:
        for vj in vecs_j:
            dots.append(vi[0] * vj[0] + vi[1] * vj[1])
    return dots

def vector_sum_set(vecs_i, vecs_j):
    """两个基本域向量集的逐元素和（按角度对齐）"""
    # 先按角度分别排序
    si = sorted(vecs_i, key=lambda v: math.atan2(v[1], v[0]))
    sj = sorted(vecs_j, key=lambda v: math.atan2(v[1], v[0]))
    return [(si[k][0] + sj[k][1], si[k][1] + sj[k][1]) for k in range(len(si))]

def vector_diff_set(vecs_i, vecs_j):
    """逐元素差"""
    si = sorted(vecs_i, key=lambda v: math.atan2(v[1], v[0]))
    sj = sorted(vecs_j, key=lambda v: math.atan2(v[1], v[0]))
    return [(si[k][0] - sj[k][1], si[k][1] - sj[k][1]) for k in range(len(si))]

def minkowski_sum(vecs_i, vecs_j):
    """Minkowski 和：所有 v_i + w_j"""
    s = set()
    for vi in vecs_i:
        for vj in vecs_j:
            s.add((round(vi[0] + vj[0], 10), round(vi[1] + vj[1], 10)))
    return s


# ── 4. 主实验 ──────────────────────────────────────────────────────────

def experiment_same_n(n):
    """同一 n（不同解）之间的代数比较"""
    sols = load_rot4_all(n)
    if len(sols) < 2:
        return None

    print(f"\n{'='*60}")
    print(f"实验: n={n}, m={n//2}, {len(sols)} 个解")
    print(f"{'='*60}")

    fd_sets = [vector_set(s, n) for s in sols]

    # 4a) 同一 n 不同解之间：基本域向量集的差异
    print(f"\n--- 4a) 同 n 解之间: 基本域向量集对比 ---")
    for i, j in combinations(range(len(sols)), 2):
        vi = fd_sets[i]['vectors']
        vj = fd_sets[j]['vectors']
        # 按角度对齐后计算差的范数
        si = sorted(vi, key=lambda v: math.atan2(v[1], v[0]))
        sj = sorted(vj, key=lambda v: math.atan2(v[1], v[0]))
        diff_norms = [math.hypot(si[k][0]-sj[k][0], si[k][1]-sj[k][1]) for k in range(len(si))]
        avg_diff = sum(diff_norms) / len(diff_norms)
        max_diff = max(diff_norms)
        # 共同点比例
        common = len(set((round(v[0],8), round(v[1],8)) for v in vi) &
                     set((round(v[0],8), round(v[1],8)) for v in vj))
        print(f"   解 {i} vs {j}: 平均差={avg_diff:.3f}, 最大差={max_diff:.3f}, 共同向量={common}/{len(vi)}")

    # 4b) Gram 矩阵对比
    print(f"\n--- 4b) Gram 矩阵 ---")
    for idx, fd in enumerate(fd_sets):
        G = gram_matrix(fd['vectors'])
        eig = np.linalg.eigvalsh(G)
        rank = np.linalg.matrix_rank(G, tol=1e-8)
        trace = np.trace(G)
        frob = np.linalg.norm(G, 'fro')
        print(f"   解 {idx}: 特征值范围=[{eig[0]:.2f}, {eig[-1]:.2f}], 秩={rank}/{len(fd['vectors'])}, 迹={trace:.1f}, Frobenius={frob:.1f}")

    # 4c) 外积(行列式)矩阵
    print(f"\n--- 4c) 外积矩阵 (det) ---")
    for idx, fd in enumerate(fd_sets):
        D = cross_matrix(fd['vectors'])
        det_D = np.linalg.det(D)
        abs_D = np.abs(D)
        print(f"   解 {idx}: det(D)={det_D:.2e}, |D|_max={abs_D.max():.2f}, |D|非零比例={np.count_nonzero(abs_D>1e-8)/D.size:.3f}")

    # 4d) 两两 Minkowski 和
    print(f"\n--- 4d) Minkowski 和 的大小 ---")
    for i, j in combinations(range(len(sols)), 2):
        ms = minkowski_sum(fd_sets[i]['vectors'], fd_sets[j]['vectors'])
        print(f"   解 {i} ⊕ 解 {j}: |和集|={len(ms)} (m²理论={len(fd_sets[i]['vectors'])**2})")

    # 4e) 向量范数多重集
    print(f"\n--- 4e) 向量范数分布 ---")
    for idx, fd in enumerate(fd_sets):
        hist = defaultdict(int)
        for nrm in fd['norms']:
            hist[round(nrm, 3)] += 1
        sorted_hist = sorted(hist.items())
        # 只打印前 5
        top5 = sorted_hist[:5]
        rest = sorted_hist[5:]
        print(f"   解 {idx}: {', '.join(f'|v|={r}:{c}' for r,c in top5)}" +
              (f" ... +{len(rest)} 种" if rest else ""))

    # 4f) 向量角度分布
    print(f"\n--- 4f) 向量角度分布（度） ---")
    for idx, fd in enumerate(fd_sets):
        degs = sorted([round(math.degrees(a), 1) for a in fd['angles']])
        print(f"   解 {idx}: 角度范围=[{degs[0]:.1f}°, {degs[-1]:.1f}°]")

    return fd_sets


def experiment_cross_m(ns):
    """跨 n 比较: 归一化后对比基本域向量集"""
    print(f"\n{'='*60}")
    print(f"实验: 跨 m 比较 (n={ns})")
    print(f"{'='*60}")

    data = {}
    for n in ns:
        sols = load_rot4_all(n)
        if not sols:
            continue
        fd = vector_set(sols[0], n)
        m_val = fd['m']
        # 归一化向量: 除以最大范数，使所有向量在单位圆内
        max_norm = max(fd['norms'])
        norm_vecs = [(vx/max_norm, vy/max_norm) for (vx, vy) in fd['vectors']]
        norm_norms = [math.hypot(vx, vy) for (vx, vy) in norm_vecs]
        data[n] = {
            'm': m_val,
            'max_norm': round(max_norm, 4),
            'norm_norms_sorted': sorted([round(n, 4) for n in norm_norms]),
            'norm_norms_hist': dict(sorted(
                (round(n, 3), norm_norms.count(round(n, 10)))
                for n in set(round(x, 3) for x in norm_norms)
            )),
        }

    for n, d in sorted(data.items()):
        nn = d['norm_norms']
        print(f"  n={n} (m={d['m']}): max_norm={d['max_norm']}, "
              f"归一化范数范围=[{min(nn):.3f}, {max(nn):.3f}], "
              f"范数直方图(前5): {dict(list(d['norm_norms_hist'].items())[:5])}")

    # 检查：归一化范数分布是否随 m 稳定？
    return data


def experiment_center_of_mass(n):
    """基本域向量集的质心"""
    sols = load_rot4_all(n)
    if not sols:
        return None

    print(f"\n--- 实验: 基本域质心 (n={n}) ---")
    for idx, s in enumerate(sols[:5]):  # 最多 5 个
        fd = vector_set(s, n)
        vecs = fd['vectors']
        com = (sum(v[0] for v in vecs) / len(vecs), sum(v[1] for v in vecs) / len(vecs))
        com_norm = math.hypot(com[0], com[1])
        # 质心与原点的共线检查
        print(f"   解 {idx}: 质心=({com[0]:.3f}, {com[1]:.3f}), |COM|={com_norm:.4f}")


def experiment_self_dual_check(n):
    """
    检查：基本域向量是否满足某种自对偶性。
    即 {v_i} 和 {-v_i} 的关系 — 对于 rot4 解，若点 p 在基本域，
    则 -p 通过 C4 旋转可映射回基本域吗？
    """
    sols = load_rot4_all(n)
    if not sols:
        return None

    print(f"\n--- 实验: 自对偶检查 (n={n}) ---")
    for idx, s in enumerate(sols[:3]):
        fd = vector_set(s, n)
        vecs = fd['vectors']
        # 对每个 v，检查 -v 是否也在同解中
        neg_set = set((round(-v[0], 8), round(-v[1], 8)) for v in vecs)
        vec_set = set((round(v[0], 8), round(v[1], 8)) for v in vecs)
        overlap = neg_set & vec_set
        print(f"   解 {idx}: {-v} 在基本域中数={len(overlap)}/{len(vecs)}")


def experiment_invariant_angles(n):
    """
    检查：不同解之间，向量间的夹角是否保持稳定？
    即基本域的"角度结构"是否是不变量？
    """
    sols = load_rot4_all(n)
    if len(sols) < 2:
        return None

    print(f"\n--- 实验: 角度不变量 (n={n}) ---")
    fd_sets = [vector_set(s, n) for s in sols]

    for idx_i, i in enumerate(fd_sets):
        for idx_j, j in enumerate(fd_sets):
            if idx_i >= idx_j:
                continue
            vi = sorted(i['vectors'], key=lambda v: math.atan2(v[1], v[0]))
            vj = sorted(j['vectors'], key=lambda v: math.atan2(v[1], v[0]))
            # 角度差
            angle_diffs = [abs(math.atan2(vi[k][1], vi[k][0]) - math.atan2(vj[k][1], vj[k][0])) for k in range(len(vi))]
            # 归一化到 [0, π]
            angle_diffs = [min(d, 2*math.pi - d) for d in angle_diffs]
            mean_diff = sum(angle_diffs) / len(angle_diffs)
            max_diff = max(angle_diffs)
            print(f"   解 {idx_i} vs {idx_j}: 角度差均值={math.degrees(mean_diff):.2f}°, "
                  f"最大={math.degrees(max_diff):.2f}°")


def experiment_flux_balance(n):
    """
    检查：基本域向量是否满足某种"通量平衡"条件。
    即所有向量的和是否为零？是否接近某个常数？
    """
    sols = load_rot4_all(n)
    if not sols:
        return None

    print(f"\n--- 实验: 通量平衡 Σv (n={n}) ---")
    sums = []
    for idx, s in enumerate(sols):
        fd = vector_set(s, n)
        vecs = fd['vectors']
        total = (sum(v[0] for v in vecs), sum(v[1] for v in vecs))
        total_norm = math.hypot(total[0], total[1])
        sums.append(total_norm)
        if idx < 5:
            print(f"   解 {idx}: Σv=({total[0]:.4f}, {total[1]:.4f}), |Σv|={total_norm:.4f}")
    if sums:
        print(f"   所有解: |Σv| 范围=[{min(sums):.4f}, {max(sums):.4f}], 均值={sum(sums)/len(sums):.4f}")


# ── 5. 运行 ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    # 选取几个有代表性的偶数 n
    test_ns = [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36, 40, 44]

    print("=" * 60)
    print("rot4 偶数解 — 基本域向量代数实验")
    print("=" * 60)

    for n in test_ns:
        experiment_same_n(n)

    # 一些特殊实验
    for n in [10, 20, 30, 40]:
        experiment_center_of_mass(n)
        experiment_flux_balance(n)
        experiment_self_dual_check(n)
        experiment_invariant_angles(n)

    # 跨 n 比较
    experiment_cross_m(test_ns)

    print("\n完成。")

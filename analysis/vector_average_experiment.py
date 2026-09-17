"""
关键发现：两个解的 FD 向量平均后，坏三元组大幅减少！
n=10 解 1⊕2 平均 → 仅 4 个坏三元组！
深入探索这个"代数平均"现象。
"""

import os, math
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

def load_all(n):
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if os.path.exists(path):
            with open(path) as f:
                return [decode_line(l.strip(), n) for l in f if l.strip() and len(decode_line(l.strip(), n)) == 2*n]
    return []

def get_fd(pts, n):
    """基本域向量集，按角度排序"""
    m = n // 2
    cx = cy = (n - 1) / 2.0
    vecs = [(x - cx, y - cy) for (x, y) in pts]
    seen = set()
    fd = []
    for v in vecs:
        rots = [v, (-v[1], v[0]), (-v[0], -v[1]), (v[1], -v[0])]
        canon = min(rots)
        if canon not in seen:
            seen.add(canon)
            fd.append(v)
    fd.sort(key=lambda v: math.atan2(v[1], v[0]))
    return fd

def expand_c4(fd_vecs, n):
    """FD → 完整 4m 点"""
    cx = cy = (n - 1) / 2.0
    pts = []
    for vx, vy in fd_vecs:
        pts.append((vx + cx, vy + cy))
        pts.append((-vy + cx, vx + cy))
        pts.append((-vx + cx, -vy + cy))
        pts.append((vy + cx, -vx + cy))
    uniq = list(set(pts))
    return uniq, len(pts) - len(uniq)

def collinear_count(pts):
    cnt = 0
    for a, b, c in combinations(pts, 3):
        if (b[0]-a[0])*(c[1]-a[1]) == (c[0]-a[0])*(b[1]-a[1]):
            cnt += 1
    return cnt

# ── 核心实验：平均 ──────────────────────────────────────────────────────

def average_experiment(n):
    sols = load_all(n)
    if len(sols) < 2:
        return
    m = n // 2
    print(f"\n{'='*65}")
    print(f"平均实验 n={n} (m={m}, {len(sols)} 个解)")
    print(f"{'='*65}")

    fds = [get_fd(s, n) for s in sols]

    results = []

    for i, j in combinations(range(len(sols)), 2):
        va = fds[i]
        vb = fds[j]

        # 方法 1: 按角度排序后配对平均
        sa = sorted(va, key=lambda v: math.atan2(v[1], v[0]))
        sb = sorted(vb, key=lambda v: math.atan2(v[1], v[0]))
        avg1 = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(m)]
        pts1, dup1 = expand_c4(avg1, n)
        bad1 = collinear_count(pts1)

        # 方法 2: 加权平均 3:1
        avg2 = [((3*sa[k][0] + sb[k][0])/4, (3*sa[k][1] + sb[k][1])/4) for k in range(m)]
        pts2, dup2 = expand_c4(avg2, n)
        bad2 = collinear_count(pts2)

        # 方法 3: 加权平均 1:3
        avg3 = [((sa[k][0] + 3*sb[k][0])/4, (sa[k][1] + 3*sb[k][1])/4) for k in range(m)]
        pts3, dup3 = expand_c4(avg3, n)
        bad3 = collinear_count(pts3)

        # 方法 4: 赋范平均（保持范数为整点距离的平方根）
        # 不对，就普通平均就行

        results.append((i, j, bad1, dup1, bad2, dup2, bad3, dup3))

        print(f"  解 {i}+{j}:")
        print(f"    1:1 平均 → 坏={bad1}, 重复={dup1}")
        print(f"    3:1 加权 → 坏={bad2}, 重复={dup2}")
        print(f"    1:3 加权 → 坏={bad3}, 重复={dup3}")

    # 找最优
    best = min(results, key=lambda r: (r[2], r[3]))
    print(f"\n  ★ 最佳: 解 {best[0]}+{best[1]} 1:1 平均 → 坏={best[2]}, 重复={best[3]}")

    # 额外检查：best 候选的 C4 展开是否仍为合法 rot4 配置
    i, j = best[0], best[1]
    va, vb = fds[i], fds[j]
    sa = sorted(va, key=lambda v: math.atan2(v[1], v[0]))
    sb = sorted(vb, key=lambda v: math.atan2(v[1], v[0]))
    best_fd = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(m)]

    # 检查 C4 对称性：看 4 个旋转是否都不同
    pts, dup = expand_c4(best_fd, n)
    assert dup == 0  # 已验证

    # 检查是否两点在同一直线上（斜率±1 线上）
    # 计算对角线上占用
    diag_count = {}
    for px, py in pts:
        d1 = round(px - py, 10)  # slope +1
        d2 = round(px + py, 10)  # slope -1
        diag_count[('+1', d1)] = diag_count.get(('+1', d1), 0) + 1
        diag_count[('-1', d2)] = diag_count.get(('-1', d2), 0) + 1
    max_diag = max(diag_count.values())
    print(f"    对角线最大占用: {max_diag} (NTIL 要求 ≤2)")

    return results


# ── 跨 n 比较最佳平均 ─────────────────────────────────────────────────

def cross_n_average(ns):
    print(f"\n{'='*65}")
    print(f"跨 n 最佳平均对比")
    print(f"{'='*65}")
    print(f"{'n':>4} {'m':>3} {'解数':>4} {'最佳平均坏':>10} {'最佳重复':>8} {'原始最优':>8}")
    print("-" * 45)

    for n in ns:
        sols = load_all(n)
        if len(sols) < 2:
            continue
        m = n // 2
        fds = [get_fd(s, n) for s in sols]

        # 原始解的最好坏三元组
        orig_best = min(collinear_count(expand_c4(fds[i], n)[0]) for i in range(len(sols)))

        # 找最佳平均
        best_bad = 999
        best_dup = 999
        for i, j in combinations(range(min(10, len(sols))), 2):  # 最多 10 个解配对
            sa = sorted(fds[i], key=lambda v: math.atan2(v[1], v[0]))
            sb = sorted(fds[j], key=lambda v: math.atan2(v[1], v[0]))
            avg = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(m)]
            pts, dup = expand_c4(avg, n)
            if dup > 0:
                continue  # 跳过有重复的
            bad = collinear_count(pts)
            if bad < best_bad:
                best_bad = bad
                best_dup = dup

        if best_bad < 999:
            print(f"{n:>4} {m:>3} {len(sols):>4} {best_bad:>10} {best_dup:>8} {orig_best:>8}")


# ── 检查平均法的 C4 对称保持性 ──────────────────────────────────────────

def check_symmetry(n):
    """确认两个 rot4 解的 FD 向量平均后仍保持 C4 对称性"""
    sols = load_all(n)
    if len(sols) < 2:
        return
    print(f"\n--- C4 对称性验证 (n={n}) ---")
    fds = [get_fd(s, n) for s in sols]

    for i in range(min(3, len(sols))):
        for j in range(i+1, min(3, len(sols))):
            sa = sorted(fds[i], key=lambda v: math.atan2(v[1], v[0]))
            sb = sorted(fds[j], key=lambda v: math.atan2(v[1], v[0]))
            avg = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(len(sa))]
            pts, dup = expand_c4(avg, n)
            if dup > 0:
                print(f"  解 {i}+{j}: 重复! 不是合法 rot4 配置")
            else:
                c4_points = expand_c4(avg, n)[0]
                # 验证 rot4 对称性：旋转后点集不变
                rot = [(-py, px) for (px, py) in c4_points]  # 90°旋转
                rot_set = set((round(x,8), round(y,8)) for x,y in rot)
                orig_set = set((round(x,8), round(y,8)) for x,y in c4_points)
                if rot_set == orig_set:
                    print(f"  解 {i}+{j}: C4 对称性保持 ✓")
                else:
                    print(f"  解 {i}+{j}: C4 对称性丢失 ✗ (差 {len(rot_set^orig_set)//2} 点)")


# ── 运行 ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ns = [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36]

    # C4 对称性验证
    for n in [10, 12, 16]:
        check_symmetry(n)

    # 详细平均实验
    for n in [10, 12, 14, 16, 18]:
        average_experiment(n)

    # 跨 n 对比
    cross_n_average(ns)

    print("\n完成。")

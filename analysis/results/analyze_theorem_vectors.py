#!/usr/bin/env python3
"""把已发现定理/现象向量化, 观察其几何结构 (非找签名, 而是刻画定理的向量几何)。

向量化对象:
  T1. SIRH Part I (投影 Sidon): 斜率±1 约束 -> 投影 u=x-y, v=x+y 的差集 Sidon。
      观察: 提升点集的投影值集间隙结构 (Sidon 集倾向均匀, min 非零间隙大)。
  T2. (X) 临界方向 (Part II/III 瓶颈): 真解 bad=0 但有很多 det=1,2,3 的"差点共线"。
      统计这些小 det 三点组的方向类型, 找高危 (X) 方向 = m=37 构造须避开者。
  T3. 幺模三点组 (min|det|=1 深化): det=±1 三点组的方向类分布。
"""
import json, os, math, itertools, random
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
SOLDIR = os.path.join(HERE, "solutions")

def lift_c4(cells, n):
    N = n; pts = []
    for (x, y) in cells:
        pts += [(x, y), (N-1-y, x), (N-1-x, N-1-y), (y, N-1-x)]
    return pts

def norm_dir(dx, dy):
    if dx == 0 and dy == 0:
        return (0, 0)
    g = math.gcd(abs(dx), abs(dy))
    dx //= g; dy //= g
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return (dx, dy)

def is_S(d):
    """方向 d 是否为斜率±1 类 (|dx|==|dy|, 且非0)。"""
    return d[0] != 0 and abs(d[0]) == abs(d[1])

def analyze(pts):
    n = len(pts)
    # --- T1: 投影 Sidon 间隙 ---
    u = sorted(pts[i][0] - pts[i][1] for i in range(n))   # 斜率+1 投影
    v = sorted(pts[i][0] + pts[i][1] for i in range(n))   # 斜率-1 投影
    def min_nonzero_gap(arr):
        g = [arr[i+1]-arr[i] for i in range(len(arr)-1)]
        nz = [x for x in g if x > 0]
        return min(nz) if nz else 0
    gap_u = min_nonzero_gap(u)
    gap_v = min_nonzero_gap(v)
    # (S) 投影重合: 同一投影值出现 >2 次 => 该斜率±1 线上 >2 点
    dup_u = max(Counter(u).values()) if u else 0
    dup_v = max(Counter(v).values()) if v else 0

    # --- T2/T3: 小 det 三点组方向统计 ---
    K = 4  # 统计 det<=K
    s_small = 0          # (S) 类小 det 三点组
    x_small = 0          # (X) 类小 det 三点组
    x_dir_counter = Counter()   # (X) 高危方向: 两向量 norm_dir 对
    unimod_dir = Counter()      # det=1 的三点组方向
    for a, b, c in itertools.combinations(range(n), 3):
        d1x=pts[b][0]-pts[a][0]; d1y=pts[b][1]-pts[a][1]
        d2x=pts[c][0]-pts[a][0]; d2y=pts[c][1]-pts[a][1]
        det = abs(d1x*d2y - d1y*d2x)
        if det == 0:
            continue
        if det > K:
            continue
        nd1 = norm_dir(d1x, d1y); nd2 = norm_dir(d2x, d2y)
        s_flag = is_S(nd1) or is_S(nd2)
        if s_flag:
            s_small += 1
        else:
            x_small += 1
            x_dir_counter[(nd1, nd2)] += 1
        if det == 1:
            unimod_dir[(nd1, nd2)] += 1

    return {
        "n": n,
        "proj_gap": (gap_u, gap_v),
        "proj_dup": (dup_u, dup_v),
        "s_small": s_small, "x_small": x_small,
        "x_top": [[ [list(t[0][0]), list(t[0][1])], t[1]] for t in x_dir_counter.most_common(6)],
        "unimod_top": [[ [list(t[0][0]), list(t[0][1])], t[1]] for t in unimod_dir.most_common(6)],

    }

def random_pts(P, n, seed):
    rnd = random.Random(seed)
    coords = rnd.sample(range(n*n), P)
    return [(c // n, c % n) for c in coords]

def main():
    sol_rows = []
    for f in sorted(os.listdir(SOLDIR)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SOLDIR, f)))
        pts = lift_c4(d["cells"], d["n"])
        r = analyze(pts)
        sol_rows.append((d["m"], r))
        print(f"[真解 m={d['m']:2d}] gap={r['proj_gap']} dup={r['proj_dup']} "
              f"s_small={r['s_small']} x_small={r['x_small']} "
              f"| X_top={r['x_top'][:3]}")

    M = 37; N = 2*M; P = 4*M
    rand_rows = []
    for t in range(4):
        pts = random_pts(P, N, 9600+t)
        r = analyze(pts)
        rand_rows.append(r)
        print(f"[随机 m37 #{t}] gap={r['proj_gap']} dup={r['proj_dup']} "
              f"s_small={r['s_small']} x_small={r['x_small']}")

    # 对照
    s_gap = sum((r['proj_gap'][0]+r['proj_gap'][1])/2 for _, r in sol_rows)/len(sol_rows)
    r_gap = sum((r['proj_gap'][0]+r['proj_gap'][1])/2 for r in rand_rows)/len(rand_rows)
    s_dup = max(max(r['proj_dup']) for _, r in sol_rows)
    r_dup = max(max(r['proj_dup']) for r in rand_rows)
    s_xs = sum(r['x_small'] for _, r in sol_rows)/len(sol_rows)
    r_xs = sum(r['x_small'] for r in rand_rows)/len(rand_rows)
    print(f"\n=== T1 投影 Sidon ===")
    print(f"投影最小非零间隙 (平均): 真解={s_gap:.2f}  随机={r_gap:.2f}")
    print(f"投影最大重复 (dup>2=线>2点): 真解={s_dup}  随机={r_dup}")
    print(f"  -> 真解 dup 应<=2 (每线<=2); 随机可能>2 (有共线)")
    print(f"\n=== T2 (X) 临界方向 ===")
    print(f"det<=4 的 (X) 小三点组数 (平均): 真解={s_xs:.0f}  随机={r_xs:.0f}")
    print(f"  真解的 (X) 小 det 三点组集中在哪些方向 (m=36 示例):")
    for m, r in sol_rows:
        if m == 36:
            print(f"    X_top = {r['x_top']}")
            print(f"    unimod_top = {r['unimod_top']}")

    json.dump({"solutions": [(m, r) for m, r in sol_rows],
               "random_m37": rand_rows},
              open(os.path.join(HERE, "theorem_vectors.json"), "w"), indent=1)
    print(f"\n[saved] {os.path.join(HERE,'theorem_vectors.json')}")

if __name__ == "__main__":
    main()

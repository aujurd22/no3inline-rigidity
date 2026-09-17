#!/usr/bin/env python3
"""方向类分布探索: 差向量约化到规范直线方向, 统计方向类频率 + C4 封闭性。
对照随机 m=37, 寻找 (X) 二次层的几何签名。

norm_dir(dx,dy): 约分 + 首非零分量为正 (无向直线方向, 如 (1,2) 表斜率2的直线)
C4 旋转: (a,b) -> (-b, a)
"""
import json, os, math, random
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

def analyze(pts):
    n = len(pts)
    D = []
    for i in range(n):
        for j in range(i+1, n):
            dx = pts[j][0]-pts[i][0]; dy = pts[j][1]-pts[i][1]
            if dx == 0 and dy == 0:
                continue
            D.append((dx, dy))
    # 方向类频率 (无向)
    dir_freq = Counter()
    # 共线检测: (方向, 截距) 组, 截距 = a*y - b*x (过点)
    line_groups = defaultdict(int)
    for i in range(n):
        for j in range(i+1, n):
            dx = pts[j][0]-pts[i][0]; dy = pts[j][1]-pts[i][1]
            if dx == 0 and dy == 0:
                continue
            d = norm_dir(dx, dy)
            dir_freq[d] += 1
            c = d[0]*pts[i][1] - d[1]*pts[i][0]
            line_groups[(d, c)] += 1
    # bad = 每条线上 (线段数-1) 之和 (线段数>=2 => 该线>=3点)
    bad = 0
    for cnt in line_groups.values():
        if cnt >= 2:
            bad += (cnt - 1)
    # 统计
    total = sum(dir_freq.values())
    n_dir = len(dir_freq)
    max_freq = max(dir_freq.values())
    max_frac = max_freq / total
    # 归一熵
    entropy = 0.0
    for c in dir_freq.values():
        p = c / total
        entropy -= p * math.log(p)
    entropy_norm = entropy / math.log(n_dir) if n_dir > 1 else 0.0
    # C4 封闭性: 每方向旋转90°后仍在集合中
    c4_closed = all(norm_dir(-b, a) in dir_freq for (a, b) in dir_freq)
    # top 方向
    top = dir_freq.most_common(5)
    return {
        "n": n, "nD": len(D), "n_dir": n_dir, "bad": bad,
        "max_freq": max_freq, "max_frac": round(max_frac, 4),
        "entropy_norm": round(entropy_norm, 4),
        "c4_closed": c4_closed,
        "top_dir": [list(t) for t in top],
    }

def random_pts(P, n, seed):
    rnd = random.Random(seed)
    coords = rnd.sample(range(n*n), P)  # 互异点
    return [(c // n, c % n) for c in coords]

def main():
    sol_rows = []
    for f in sorted(os.listdir(SOLDIR)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SOLDIR, f)))
        pts = lift_c4(d["cells"], d["n"])
        r = analyze(pts)
        sol_rows.append((d["m"], r))
        print(f"[真解 m={d['m']:2d}] n_dir={r['n_dir']:4d} bad={r['bad']:3d} "
              f"maxF={r['max_freq']:4d}({r['max_frac']:.3f}) H={r['entropy_norm']:.3f} "
              f"C4close={r['c4_closed']} top={r['top_dir']}")

    M = 37; N = 2*M; P = 4*M
    rand_rows = []
    for t in range(5):
        pts = random_pts(P, N, 9500+t)
        r = analyze(pts)
        rand_rows.append(r)
        print(f"[随机 m37 #{t}] n_dir={r['n_dir']:4d} bad={r['bad']:4d} "
              f"maxF={r['max_freq']:4d}({r['max_frac']:.3f}) H={r['entropy_norm']:.3f} "
              f"C4close={r['c4_closed']} top={r['top_dir']}")

    # 对照总结
    s_max = sum(r['max_frac'] for _, r in sol_rows)/len(sol_rows)
    r_max = sum(r['max_frac'] for r in rand_rows)/len(rand_rows)
    s_H = sum(r['entropy_norm'] for _, r in sol_rows)/len(sol_rows)
    r_H = sum(r['entropy_norm'] for r in rand_rows)/len(rand_rows)
    s_close = all(r['c4_closed'] for _, r in sol_rows)
    r_close = all(r['c4_closed'] for r in rand_rows)
    print(f"\n=== 对照 (平均) ===")
    print(f"max_frac (方向最集中占比): 真解={s_max:.3f}  随机={r_max:.3f}")
    print(f"entropy_norm (方向分散度): 真解={s_H:.3f}  随机={r_H:.3f}")
    print(f"C4 方向类封闭: 真解={s_close}  随机={r_close}")
    print(f"注: 真解 C4 必封闭(提升集对称); 随机不封闭. 这是'对称性'签名非'解'签名.")

    json.dump({"solutions": [(m, r) for m, r in sol_rows],
               "random_m37": rand_rows},
              open(os.path.join(HERE, "direction_classes.json"), "w"), indent=1)
    print(f"\n[saved] {os.path.join(HERE,'direction_classes.json')}")

if __name__ == "__main__":
    main()

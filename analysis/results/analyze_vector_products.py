#!/usr/bin/env python3
"""探索性: 已知真解上"向量相乘"的统计签名 (点积/叉积/长度谱)。
每次都加随机 m=37 对照, 判断是否有区分度。

'两组向量相乘' = 任取两差向量 d1,d2:
  - 点积 dot = d1x*d2x + d1y*d2y
  - 叉积 cross = d1x*d2y - d1y*d2x   (平行四边形有向面积)
'多组' = 整个差向量库 D 的统计签名 (长度平方谱 / 上述谱的全局分布)
"""
import json, os, math, random
from collections import Counter

HERE = os.path.dirname(__file__)
SOLDIR = os.path.join(HERE, "solutions")

def lift_c4(cells, n):
    N = n; pts = []
    for (x, y) in cells:
        pts += [(x, y), (N-1-y, x), (N-1-x, N-1-y), (y, N-1-x)]
    return pts

def diff_vectors(pts):
    D = []
    n = len(pts)
    for i in range(n):
        for j in range(i+1, n):
            D.append((pts[j][0]-pts[i][0], pts[j][1]-pts[i][1]))
    return D

def analyze(pts, K=60000, seed=0):
    D = diff_vectors(pts)
    N = len(D)
    # 长度平方谱
    len_cnt = Counter(dx*dx + dy*dy for dx, dy in D)
    top_len = len_cnt.most_common(6)
    # 采样点积/叉积谱
    rnd = random.Random(seed)
    dot_cnt = Counter(); cross_cnt = Counter()
    for _ in range(K):
        a, b = rnd.sample(range(N), 2)
        dx1, dy1 = D[a]; dx2, dy2 = D[b]
        dot_cnt[dx1*dx2 + dy1*dy2] += 1
        cross_cnt[dx1*dy2 - dy1*dx2] += 1
    # 小 |值| 的频率 (最具结构性)
    dot_small = sorted([(abs(v), c) for v, c in dot_cnt.items() if abs(v) <= 12],
                       key=lambda x: -x[1])[:6]
    cross_small = sorted([(abs(v), c) for v, c in cross_cnt.items() if abs(v) <= 12],
                         key=lambda x: -x[1])[:6]
    return {
        "nD": N,
        "top_len": top_len,
        "dot_zero": dot_cnt.get(0, 0),
        "cross_zero": cross_cnt.get(0, 0),
        "dot_small": dot_small,
        "cross_small": cross_small,
    }

def random_pts(P, n, seed):
    rnd = random.Random(seed)
    return [(rnd.randrange(n), rnd.randrange(n)) for _ in range(P)]

def main():
    # 真解
    sol_rows = []
    for f in sorted(os.listdir(SOLDIR)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SOLDIR, f)))
        pts = lift_c4(d["cells"], d["n"])
        r = analyze(pts)
        sol_rows.append((d["m"], r))
        print(f"[真解 m={d['m']:2d}] nD={r['nD']:5d} | "
              f"top_len={[ (int(math.sqrt(l)),c) for l,c in r['top_len'][:4]]} | "
              f"dot0={r['dot_zero']} crs0={r['cross_zero']} | "
              f"dot_small={r['dot_small']} | crs_small={r['cross_small']}")

    # 随机 m=37 对照
    M = 37; N = 2*M; P = 4*M
    rand_rows = []
    for t in range(5):
        pts = random_pts(P, N, 9000+t)
        r = analyze(pts, seed=7000+t)
        rand_rows.append(r)
        print(f"[随机 m=37 #{t}] nD={r['nD']:5d} | "
              f"top_len={[ (int(math.sqrt(l)),c) for l,c in r['top_len'][:4]]} | "
              f"dot0={r['dot_zero']} crs0={r['cross_zero']} | "
              f"dot_small={r['dot_small']} | crs_small={r['cross_small']}")

    # 对照总结: 把随机的 dot0/crs0 平均
    rdot0 = sum(r["dot_zero"] for r in rand_rows)/len(rand_rows)
    rcrs0 = sum(r["cross_zero"] for r in rand_rows)/len(rand_rows)
    sdot0 = sum(r["dot_zero"] for _, r in sol_rows)/len(sol_rows)
    scrs0 = sum(r["cross_zero"] for _, r in sol_rows)/len(sol_rows)
    print(f"\n=== 对照 ===")
    print(f"dot=0 (垂直差向量对) 平均: 真解={sdot0:.0f}  随机m37={rdot0:.0f}")
    print(f"cross=0 (共线差向量对) 平均: 真解={scrs0:.0f}  随机m37={rcrs0:.0f}")
    print(f"注: cross=0 => 四点共线; 真解应为0(bad=0), 随机应>>0")
    # 长度谱: 真解出现最多的长度是否稳定
    print(f"\n真解 top 长度(欧氏)分布示例:")
    for m, r in sol_rows:
        print(f"  m={m:2d}: {[ (int(math.sqrt(l)),c) for l,c in r['top_len'] ]}")

    json.dump({"solutions": [(m, r) for m, r in sol_rows],
               "random_m37": rand_rows},
              open(os.path.join(HERE, "vector_products.json"), "w"), indent=1)
    print(f"\n[saved] {os.path.join(HERE,'vector_products.json')}")

if __name__ == "__main__":
    main()

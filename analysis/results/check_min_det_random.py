#!/usr/bin/env python3
"""对照实验：随机 m=37 配置(148 点)的 min|det| 分布。
检验 min|det|=1 不变量是否对解有区分度。"""
import random, math, itertools, json

N = 74   # n = 2m, m=37
P = 148  # 4m

def random_pointset(P, N, seed):
    random.seed(seed)
    return [(random.randrange(N), random.randrange(N)) for _ in range(P)]

def min_det_sampled(pts, K=30000, full=False):
    """随机采样 K 个三元组找 |det|=1；若未找到且 full=True 则穷举。"""
    n = len(pts)
    if full:
        md = None
        for a, b, c in itertools.combinations(range(n), 3):
            d1x=pts[b][0]-pts[a][0]; d1y=pts[b][1]-pts[a][1]
            d2x=pts[c][0]-pts[a][0]; d2y=pts[c][1]-pts[a][1]
            det = abs(d1x*d2y - d1y*d2x)
            if det == 0: return 0
            if md is None or det < md: md = det
        return md
    # 采样
    rnd = random.Random(12345)
    for _ in range(K):
        a, b, c = rnd.sample(range(n), 3)
        d1x=pts[b][0]-pts[a][0]; d1y=pts[b][1]-pts[a][1]
        d2x=pts[c][0]-pts[a][0]; d2y=pts[c][1]-pts[a][1]
        det = abs(d1x*d2y - d1y*d2x)
        if det == 1:
            return 1
    return None  # 采样未找到

def count_bad(pts):
    """共线三点组数 (完全穷举, 仅用于少量配置)。"""
    n = len(pts); bad = 0
    for a, b, c in itertools.combinations(range(n), 3):
        d1x=pts[b][0]-pts[a][0]; d1y=pts[b][1]-pts[a][1]
        d2x=pts[c][0]-pts[a][0]; d2y=pts[c][1]-pts[a][1]
        if d1x*d2y == d1y*d2x: bad += 1
    return bad

TRIALS = 200
has1 = 0
unknown = 0
unknown_full = []
for t in range(TRIALS):
    pts = random_pointset(P, N, 1000+t)
    r = min_det_sampled(pts, K=30000, full=False)
    if r == 1:
        has1 += 1
    else:
        unknown += 1
        unknown_full.append((1000+t, pts))

# 对未找到的配置穷举确认
confirmed_gt1 = 0
for seed, pts in unknown_full:
    md = min_det_sampled(pts, full=True)
    if md is not None and md > 1:
        confirmed_gt1 += 1

# 额外：对 3 个随机配置算 bad 量级，对比真解 bad=0
bad_samples = []
for seed in [2001, 2002, 2003]:
    pts = random_pointset(P, N, seed)
    bad_samples.append(count_bad(pts))

print(f"随机 148 点集 TRIALS={TRIALS}")
print(f"  min|det|=1 (采样命中): {has1}")
print(f"  采样未命中:            {unknown}")
print(f"    其中穷举确认 min|det|>1: {confirmed_gt1}")
print(f"  => min|det|=1 在随机配置中占比 ≈ {has1/(has1+unknown):.3%}")
print(f"对照: 随机配置 bad(共线三元组) 抽样 = {bad_samples}  (真解 bad=0)")

out = {
    "trials": TRIALS, "has1": has1, "unknown": unknown,
    "confirmed_gt1": confirmed_gt1,
    "random_bad_samples": bad_samples,
}
json.dump(out, open(__file__.replace(".py", "_out.json"), "w"), indent=1)
print("[saved]", __file__.replace(".py", "_out.json"))

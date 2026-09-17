#!/usr/bin/env python3
"""
radial_longitudinal.py -- 所有 m 的 rot4 解的径向层 + 纵向(跨 m)对比

目标: 把每个 rot4 解还原成 cell 级径向层(到中心距离分环), 用「基本域最大半径」做
全局归一化(不同 m 的 x 轴 = 绝对归一半径 rho∈[0,1]), 看不同 m 的径向密度曲线
是否形状守恒 / 是否存在普适的「偏好半径带」。

数据源:
  - flammenkamp_cache/n{n}_rot4  (每 m 多个真实 rot4 解, n=2m)
  - analysis/results/solutions/m{mm}.json (已验证真解, 单解)

坐标: 棋盘 n×n, 点到中心距离 key d = (2x-(n-1))² + (2y-(n-1))² (整数, =4×欧氏²)。
rot4 解的 C4 轨道 4 点等距同环 → cell 级环占用 = 点数/4, 每环 ≤2 cell (research_M)。
全局归一: rho = sqrt(d) / (sqrt(2)*(n-1))  (= sqrt(d)/sqrt(2*(2m-1)²)), 角点 rho=1。
"""
import os, json, math, glob
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "flammenkamp_cache")
SOL = os.path.join(HERE, "results", "solutions")
ALPH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
VAL = {c: i for i, c in enumerate(ALPH)}
B = 24  # 归一半径 bin 数

def decode_line(line, n):
    line = line.rstrip('\n').rstrip('\r')
    if not line:
        return None
    pre = line[0]
    body = line[1:] if pre in '.:/-ocx+*' else line
    if len(body) < 2 * n:
        return None
    cols = []
    for r in range(n):
        c1 = VAL[body[2 * r]]; c2 = VAL[body[2 * r + 1]]
        if not (0 <= c1 < n and 0 <= c2 < n):
            return None
        cols += [c1, c2]
    return cols

def rings_of_points(pts, n):
    """返回 {d: count} (board-point 级)。rot4 → 每环 count 为 4 的倍数。"""
    ctr = (n - 1)
    cnt = Counter()
    for (x, y) in pts:
        d = (2 * x - ctr) ** 2 + (2 * y - ctr) ** 2
        cnt[d] += 1
    return cnt

def solution_cell_rings(pts, n):
    """cell 级环占用: {d: cells} (cells = count/4), 校验 rot4 每环 count%4==0。"""
    cnt = rings_of_points(pts, n)
    cellrings = {}
    for d, c in cnt.items():
        assert c % 4 == 0, f"rot4 解出现非4倍数环: d={d} count={c} (n={n})"
        cellrings[d] = c // 4
    return cellrings

def profile_from_cellrings(cellrings, n, m):
    """全局归一径向密度曲线 (len B, sum=1)。"""
    Rmax = math.sqrt(2) * (n - 1)
    prof = [0.0] * B
    for d, cells in cellrings.items():
        rho = math.sqrt(d) / Rmax
        b = min(B - 1, int(rho * B))
        prof[b] += cells
    tot = sum(prof)
    if tot > 0:
        prof = [v / tot for v in prof]
    return prof

def mean_r(cellrings, n):
    """解的平均归一半径(按 cell 加权)。"""
    Rmax = math.sqrt(2) * (n - 1)
    num = den = 0.0
    for d, cells in cellrings.items():
        rho = math.sqrt(d) / Rmax
        num += rho * cells; den += cells
    return (num / den) if den else 0.0

# ── 收集所有 rot4 解 ──────────────────────────────────────────────────────
solutions_by_m = defaultdict(list)  # m -> [cellrings_per_sol]

# (1) flammenkamp rot4
for path in sorted(glob.glob(os.path.join(CACHE, "n*_rot4"))):
    base = os.path.basename(path)
    n = int(base[1:base.index('_')])
    m = n // 2
    with open(path) as f:
        for line in f:
            cols = decode_line(line, n)
            if not cols:
                continue
            pts = [(r, cols[2 * r]) for r in range(n)] + \
                  [(r, cols[2 * r + 1]) for r in range(n)]
            try:
                cr = solution_cell_rings(pts, n)
            except AssertionError:
                continue  # 非 rot4 形态, 跳过
            if sum(cr.values()) == m:
                solutions_by_m[m].append(cr)

# (2) 已验证 solutions/ (cell 列表)
for path in sorted(glob.glob(os.path.join(SOL, "m*.json"))):
    mm = int(os.path.basename(path)[1:3])
    with open(path) as f:
        d = json.load(f)
    cells = [tuple(c) for c in d["cells"]]
    m = len(cells)
    n = 2 * m
    pts = []
    for (x, y) in cells:
        # cell(x,y) 的 C4 4 个 lift 点 (奇数坐标升到棋盘板坐标)
        # 奇数坐标 (2(m-x)-1, 2(m-y)-1); 棋盘板坐标 = 该值 (0..2m-1)
        a = 2 * (m - x) - 1; b = 2 * (m - y) - 1
        for r in range(4):
            # C4 旋转关于中心 (n-1)/2
            if r == 0: p = (a, b)
            elif r == 1: p = (n - 1 - b, a)
            elif r == 2: p = (n - 1 - a, n - 1 - b)
            else: p = (b, n - 1 - a)
            pts.append(p)
    cr = solution_cell_rings(pts, n)
    solutions_by_m[m].append(cr)

# ── 纵向分析 ─────────────────────────────────────────────────────────────
per_m = {}
all_profiles = []   # (m, profile)
all_meanr = []      # (m, mean_r)
heatmap = {}        # m -> per-bin 占用发生率 (fraction of sols with >=1 cell)
for m in sorted(solutions_by_m):
    sols = solutions_by_m[m]
    profs = [profile_from_cellrings(cr, 2 * m, m) for cr in sols]
    mean_profile = [sum(p[i] for p in profs) / len(profs) for i in range(B)]
    mr = [mean_r(cr, 2 * m) for cr in sols]
    # 占用发生率
    occ = [0.0] * B
    for cr in sols:
        Rmax = math.sqrt(2) * (2 * m - 1)
        bins_hit = set()
        for d, cells in cr.items():
            rho = math.sqrt(d) / Rmax
            bins_hit.add(min(B - 1, int(rho * B)))
        for b in bins_hit:
            occ[b] += 1
    occ = [v / len(sols) for v in occ]
    # 偏好带 (mean_profile 峰值 bin)
    band = max(range(B), key=lambda i: mean_profile[i])
    # 内空心度: 最内 2 bin 平均密度 vs 整体
    hollow = (mean_profile[0] + mean_profile[1]) / 2.0
    per_m[m] = {
        "nsol": len(sols),
        "mean_profile": mean_profile,
        "mean_r_mean": sum(mr) / len(mr),
        "mean_r_std": (sum((x - sum(mr) / len(mr)) ** 2 for x in mr) / len(mr)) ** 0.5,
        "band_center_bin": band,
        "band_center_rho": (band + 0.5) / B,
        "hollow_inner": hollow,
        "occupancy_incidence": occ,
        "_profiles_per_sol": profs,
        "_meanr_per_sol": mr,
    }
    for p in profs:
        all_profiles.append((m, p))
    for x in mr:
        all_meanr.append((m, x))

# 普适形状 = 各 m 平均曲线再平均
universal = [sum(per_m[m]["mean_profile"][i] for m in per_m) / len(per_m) for i in range(B)]
uni_band = max(range(B), key=lambda i: universal[i])

# 曲线间相关性 (各 m mean_profile 两两 Pearson)
def pearson(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((x - mb) ** 2 for x in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0

ms = sorted(per_m)
corrs = []
for i in range(len(ms)):
    for j in range(i + 1, len(ms)):
        c = pearson(per_m[ms[i]]["mean_profile"], per_m[ms[j]]["mean_profile"])
        corrs.append(c)
corr_min = min(corrs); corr_mean = sum(corrs) / len(corrs)

report = {
    "B": B,
    "ms": ms,
    "per_m": {str(m): {k: v for k, v in per_m[m].items() if not k.startswith("_")} for m in ms},
    "universal_profile": universal,
    "universal_band_rho": (uni_band + 0.5) / B,
    "corr_min": corr_min,
    "corr_mean": corr_mean,
    "n_ms": len(ms),
    "total_solutions": sum(per_m[m]["nsol"] for m in ms),
}
os.makedirs("results", exist_ok=True)
with open("results/radial_longitudinal.json", "w") as f:
    json.dump(report, f, indent=2)

# 终端摘要
print(f"=== 纵向径向层分析: {report['total_solutions']} 个 rot4 解, m∈{ms[0]}..{ms[-1]} ({len(ms)} 个 m) ===")
print(f"普适峰值半径 rho* = {report['universal_band_rho']:.3f}  (归一半径, 角点=1)")
print(f"跨 m 曲线相关: mean={corr_mean:.3f}, min={corr_min:.3f}")
print(f"{'m':>3} {'nsol':>4} {'<rho>':>6} {'std':>5} {'band_rho':>8} {'hollow':>6}")
for m in ms:
    p = per_m[m]
    print(f"{m:>3} {p['nsol']:>4} {p['mean_r_mean']:>6.3f} {p['mean_r_std']:>5.3f} "
          f"{p['band_center_rho']:>8.3f} {p['hollow_inner']:>6.3f}")
print("\n逐 m 平均径向密度曲线 (前6 bin / 后6 bin 示意):")
for m in ms:
    prof = per_m[m]["mean_profile"]
    head = " ".join(f"{v:.2f}" for v in prof[:6])
    tail = " ".join(f"{v:.2f}" for v in prof[-6:])
    print(f"  m={m:>2}: [{head} ... {tail}]")

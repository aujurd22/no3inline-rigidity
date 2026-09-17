#!/usr/bin/env python3
"""可视化已知真解的向量结构观察。"""
import json, os, math, itertools
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
rows = json.load(open(os.path.join(HERE, "known_solutions_vectors.json")))
ms = [r["m"] for r in rows]

def lift_c4(cells, n):
    N = n; pts = []
    for (x, y) in cells:
        pts += [(x, y), (N-1-y, x), (N-1-x, N-1-y), (y, N-1-x)]
    return pts

fig, ax = plt.subplots(2, 2, figsize=(13, 10))

# (1) min|det| 平坦不变量
ax[0,0].plot(ms, [r["min_det"] for r in rows], "o-", color="#d62728", lw=2, ms=7)
ax[0,0].set_title("跨 m 刚性余量  min|det|  (幺模不变量)", fontsize=12)
ax[0,0].set_xlabel("m"); ax[0,0].set_ylabel("min |cross-product|")
ax[0,0].set_ylim(0, 3); ax[0,0].axhline(1, ls="--", c="gray", alpha=.6)
ax[0,0].text(0.5, 0.9, "所有真解 min|det| = 1\n(离共线最近但不共线)",
             transform=ax[0,0].transAxes, ha="center", color="#d62728")
ax[0,0].grid(alpha=.3)

# (2) 幺模三点组数 vs m
ax[0,1].plot(ms, [r["n_unimod"] for r in rows], "s-", color="#1f77b4", lw=2, label="全部幺模三点组")
ax[0,1].plot(ms, [r["n_unimod_S"] for r in rows], "^-", color="#2ca02c", lw=2, label="含斜率±1 边")
ax[0,1].set_title("幺模三点组数量 vs m", fontsize=12)
ax[0,1].set_xlabel("m"); ax[0,1].set_ylabel("三点组数 (|det|=1)")
ax[0,1].legend(); ax[0,1].grid(alpha=.3)

# (3) S% (斜率±1 对占比) vs m, 拟合 c/m
sp = [r["s_pair_frac"] for r in rows]
ax[1,0].plot(ms, sp, "o-", color="#9467bd", lw=2, label="实测 S%")
cfit = sum(s*m for s, m in zip(sp, ms))/len(ms)
ax[1,0].plot(ms, [cfit/m for m in ms], "--", color="gray", label=f"~{cfit:.2f}/m")
ax[1,0].set_title("斜率±1 点对占比 vs m", fontsize=12)
ax[1,0].set_xlabel("m"); ax[1,0].set_ylabel("S 对 / 总对")
ax[1,0].legend(); ax[1,0].grid(alpha=.3)

# (4) 一个小 m 真解 (m=10) 的提升点集 + 幺模三点组
sol = json.load(open(os.path.join(HERE, "solutions", "m10.json")))
pts = lift_c4(sol["cells"], sol["n"])
P = len(pts)
xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
# 标出基本域代表点 vs 旋转像
for i, (x, y) in enumerate(pts):
    c = "#d62728" if i % 4 == 0 else "#1f77b4"
    ax[1,1].scatter(x, y, c=c, s=45, zorder=3)
# 画出若干幺模三点组
cnt = 0
for a, b, cc in itertools.combinations(range(P), 3):
    d1x=pts[b][0]-pts[a][0]; d1y=pts[b][1]-pts[a][1]
    d2x=pts[cc][0]-pts[a][0]; d2y=pts[cc][1]-pts[a][1]
    if abs(d1x*d2y-d1y*d2x) == 1:
        tri = [pts[a], pts[b], pts[cc], pts[a]]
        ax[1,1].plot([t[0] for t in tri], [t[1] for t in tri],
                     c="#2ca02c", alpha=.25, lw=1, zorder=1)
        cnt += 1
        if cnt >= 30: break
ax[1,1].set_title(f"m=10 真解提升点集 (40 点)\n绿色=幺模三点组(|det|=1) 前30个",
                  fontsize=11)
ax[1,1].set_xlabel("x"); ax[1,1].set_ylabel("y")
ax[1,1].set_aspect("equal"); ax[1,1].grid(alpha=.3)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.tight_layout()
out = os.path.join(HERE, "known_solutions_vectors.png")
plt.savefig(out, dpi=110)
print("[saved]", out)

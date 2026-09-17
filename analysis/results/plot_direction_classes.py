#!/usr/bin/env python3
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
data = json.load(open(os.path.join(HERE, "direction_classes.json")))
sol = data["solutions"]; rnd = data["random_m37"]
ms = [m for m, _ in sol]
maxf = [r["max_frac"] for _, r in sol]
H = [r["entropy_norm"] for _, r in sol]
r_maxf = sum(r["max_frac"] for r in rnd)/len(rnd)
r_H = sum(r["entropy_norm"] for r in rnd)/len(rnd)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(1, 2, figsize=(12, 5))
# (1) max_frac
ax[0].plot(ms, maxf, "o-", color="#d62728", label="真解")
ax[0].axhline(r_maxf, ls="--", color="gray", label=f"随机 m=37 ({r_maxf:.3f})")
ax[0].set_title("方向最集中占比 max_frac", fontsize=12)
ax[0].set_xlabel("m"); ax[0].set_ylabel("max_frac")
ax[0].legend(); ax[0].grid(alpha=.3)
# (2) entropy_norm
ax[1].plot(ms, H, "s-", color="#1f77b4", label="真解")
ax[1].axhline(r_H, ls="--", color="gray", label=f"随机 m=37 ({r_H:.3f})")
ax[1].set_title("方向分散度 entropy_norm", fontsize=12)
ax[1].set_xlabel("m"); ax[1].set_ylabel("H_norm")
ax[1].legend(); ax[1].grid(alpha=.3)
plt.tight_layout()
out = os.path.join(HERE, "direction_classes.png")
plt.savefig(out, dpi=110)
print("[saved]", out)

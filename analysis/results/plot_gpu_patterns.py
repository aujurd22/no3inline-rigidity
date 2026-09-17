#!/usr/bin/env python3
# plot_gpu_patterns.py -- visualize GPU vector-mining findings for rot4-NTIL m=37.
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CUT = 1100  # ignore sparse extreme tail for readability

def load(p):
    with open(p) as f:
        return json.load(f)

mine = load("results/gpu_pattern_mine.json")
desc = load("results/gpu_pattern_desc.json")

hm, hd = mine["hist"], desc["hist"]
bm = [hm[b] for b in range(CUT)]
bd = [hd[b] for b in range(CUT)]

fig, ax = plt.subplots(1, 2, figsize=(12, 5))

# left: bad-distribution
ax[0].plot(range(CUT), bm, color="tab:blue", lw=1, label="random mine (38.4M)")
ax[0].plot(range(CUT), bd, color="tab:red", lw=1, label="greedy desc G=20 (1.82M)")
ax[0].set_yscale("log")
ax[0].set_xlabel("bad (collinear triples)")
ax[0].set_ylabel("count (log scale)")
ax[0].set_title("Bad-distribution: random vs greedy-descent  [m=37]")
ax[0].axvline(0, color="green", ls="--", lw=1)
ax[0].text(8, ax[0].get_ylim()[1]*0.5, "solution\nbad=0", color="green", fontsize=8)
ax[0].legend(loc="upper right")

# right: (S) fraction vs bad
def sfract(d):
    out = []
    for b in range(CUT):
        if d["hist"][b] > 0:
            x = d["sum_x"][b] / d["hist"][b]
            s = d["sum_s"][b] / d["hist"][b]
            out.append((b, s / (x + s + 1e-9)))
    return out

fm = sfract(mine)
fd = sfract(desc)
ax[1].plot([p[0] for p in fm], [p[1] for p in fm], color="tab:blue", lw=1, label="random")
ax[1].plot([p[0] for p in fd], [p[1] for p in fd], color="tab:red", lw=1, label="greedy")
ax[1].set_xlabel("bad")
ax[1].set_ylabel("S/(X+S)  fraction")
ax[1].set_title("(S)[slope+-1] share of conflicts vs bad")
ax[1].legend(loc="upper left")

fig.tight_layout()
fig.savefig("results/gpu_patterns.png", dpi=120)
print("saved results/gpu_patterns.png")

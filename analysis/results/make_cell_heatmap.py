"""Heatmap of P(cell)/(1/m) for representative m, visualizing the spatial bias of the
'free' fundamental-quadrant cells across known rot4 NTIL solutions."""
import os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from rot4_loader import load_rot4


def quadrant_counts(N):
    m = N // 2
    sols, _ = load_rot4(N)
    cnt = np.zeros((m, m), dtype=np.int64)
    for sol in sols:
        for (x, y) in sol:
            if x < m and y < m:
                cnt[x, y] += 1
    return cnt, len(sols), m


def main():
    specs = [(36, 'm=18  (n=36, 281 sols)'), (56, 'm=28  (n=56, 10441 sols)')]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    im = None
    for ax, (N, title) in zip(axes, specs):
        cnt, nsol, m = quadrant_counts(N)
        P = cnt / nsol
        ratio = P / (1.0 / m)
        # ratio[x,y] -> display with x horizontal, y vertical
        im = ax.imshow(ratio.T, origin='lower', cmap='RdBu_r',
                       norm=TwoSlopeNorm(vcenter=1.0, vmin=0.0, vmax=2.0))
        ax.set_title(title, fontsize=11)
        ax.set_xlabel('x  (quadrant column)')
        ax.set_ylabel('y  (quadrant row)')
        ax.plot([0, m - 1], [0, m - 1], 'k--', lw=0.8, alpha=0.45)  # diagonal x=y
        ax.set_xticks([0, m // 2, m - 1]); ax.set_yticks([0, m // 2, m - 1])
    fig.colorbar(im, ax=axes, fraction=0.025, label='P(cell) / (1/m)   [1.0 = uniform]')
    fig.suptitle('Spatial selection bias of the "free" cells (red = over-selected, blue = avoided)',
                 fontsize=12)
    plt.tight_layout()
    out = os.path.join(HERE, 'cell_distribution_heatmap.png')
    plt.savefig(out, dpi=130)
    print('saved', out)


if __name__ == '__main__':
    main()

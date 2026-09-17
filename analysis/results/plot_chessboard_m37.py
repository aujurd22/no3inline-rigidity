"""Chessboard-format visualization of the m=37 rot4-NTIL solution.

Left  : full 74x74 board as a wood chessboard, 148 solution points plotted as
        pieces, coloured by their C4 orbit (each base-quadrant cell lifts to 4
        points that are 90-degree rotations of each other about the centre).
Right : the 37x37 fundamental quadrant chessboard; the single chosen cell per
        row (a permutation) is highlighted -- this is the rot4 base set.

Usage:
  plot_chessboard_m37.py            -> renders both 'biased' and 'unbiased'
  plot_chessboard_m37.py biased
"""
import os, sys, json, argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37
N = 2 * M
CENTER = (N - 1) / 2.0  # 36.5

# wood colours
LIGHT = '#F0D9B5'
DARK = '#B58863'
# 4 orbit colours (contrast on wood)
ORBIT = ['#1a1a1a', '#c0392b', '#1a5276', '#1e8449']


def lifted_points(x, y, m):
    return [(x, y), (2 * m - 1 - y, x), (2 * m - 1 - x, 2 * m - 1 - y), (y, 2 * m - 1 - x)]


def load(variant):
    fn = os.path.join(HERE, f'solution_m37_{variant}.json')
    d = json.load(open(fn))
    cells = [tuple(c) for c in d['base_quadrant']]
    # rebuild orbits deterministically
    orbits = []
    for (x, y) in cells:
        orbits.append(lifted_points(x, y, M))
    flat = [p for orb in orbits for p in orb]
    return cells, orbits, flat


def chessboard_img(n):
    img = [[( (X + Y) % 2 ) for X in range(n)] for Y in range(n)]
    return img


def plot(variant):
    cells, orbits, flat = load(variant)
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.2))

    # ---------- LEFT: full 74x74 chessboard ----------
    ax = axes[0]
    ax.imshow(chessboard_img(N), origin='lower', extent=[0, N, 0, N],
              cmap=ListedColormap([LIGHT, DARK]), interpolation='nearest')
    # points, coloured by orbit position
    for k, orb in enumerate(orbits):
        xs = [p[0] + 0.5 for p in orb]
        ys = [p[1] + 0.5 for p in orb]
        ax.scatter(xs, ys, s=95, c=ORBIT[k % 4], edgecolors='white',
                   linewidths=0.6, zorder=3)
    # symmetry guides: two diagonals + center cross (C4 axes about CENTER)
    ax.plot([0, N], [0, N], color='gray', ls='--', lw=0.8, alpha=0.6, zorder=2)
    ax.plot([0, N], [N, 0], color='gray', ls='--', lw=0.8, alpha=0.6, zorder=2)
    ax.axvline(CENTER, color='gray', ls=':', lw=0.8, alpha=0.5, zorder=2)
    ax.axhline(CENTER, color='gray', ls=':', lw=0.8, alpha=0.5, zorder=2)
    ax.set_xlim(0, N); ax.set_ylim(0, N)
    ax.set_xticks(range(0, N + 1, 10)); ax.set_yticks(range(0, N + 1, 10))
    ax.set_title(f'm=37 rot4-NTIL  --  full {N}x{N} board\n'
                 f'{len(flat)} pieces (4 per quadrant cell); C4-symmetric', fontsize=11)
    ax.set_xlabel('X'); ax.set_ylabel('Y')
    leg = [Patch(facecolor=ORBIT[i], edgecolor='white', label=f'C4 orbit {i}') for i in range(4)]
    leg.append(Patch(facecolor='none', edgecolor='gray', label='C4 axes'))
    ax.legend(handles=leg, loc='upper left', fontsize=8, framealpha=0.9)

    # ---------- RIGHT: 37x37 fundamental quadrant chessboard ----------
    ax2 = axes[1]
    ax2.imshow(chessboard_img(M), origin='lower', extent=[0, M, 0, M],
               cmap=ListedColormap([LIGHT, DARK]), interpolation='nearest')
    # highlight chosen cells (navy squares)
    chosen_x = [c[0] + 0.5 for c in cells]
    chosen_y = [c[1] + 0.5 for c in cells]
    ax2.scatter(chosen_x, chosen_y, s=180, c='#11246b', marker='s',
                edgecolors='white', linewidths=0.8, zorder=3, label='chosen cell')
    ax2.set_xlim(0, M); ax2.set_ylim(0, M)
    ax2.set_xticks(range(0, M + 1, 5)); ax2.set_yticks(range(0, M + 1, 5))
    ax2.set_title(f'Fundamental quadrant  ({M}x{M})\n'
                  f'{len(cells)} cells, exactly one per row = a permutation', fontsize=11)
    ax2.set_xlabel('column y'); ax2.set_ylabel('row x')
    ax2.legend(loc='upper left', fontsize=8, framealpha=0.9)

    plt.tight_layout()
    out = os.path.join(HERE, f'chessboard_m37_{variant}.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print('wrote', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('variant', nargs='?', default=None)
    args = ap.parse_args()
    variants = [args.variant] if args.variant else ['biased', 'unbiased']
    for v in variants:
        plot(v)


if __name__ == '__main__':
    main()

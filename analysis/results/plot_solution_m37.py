"""Visualize the found m=37 rot4-NTIL solution (solution_m37_biased.json).
Left: fundamental quadrant (37x37) with the solution cells + the empirical prior overlay.
Right: full 2m x 2m = 74x74 board with the 4m=148 lifted points (shows C4 symmetry).
"""
import json, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37
sol = json.load(open(os.path.join(HERE, 'solution_m37_biased.json')))
cells = sol['base_quadrant']            # list of (row, col) in quadrant
pts = sol['full_points']                # 148 C4-lifted points

# empirical prior (same constants as biased_nibble)
AGG_RADIAL = [0.55, 0.83, 0.77, 0.81, 0.93, 1.02, 1.39, 1.33, 0.44, 0.14]
RAD_BINS = [0.05 * (i * 2 + 1) for i in range(10)]
DIAG_R, NEAR_R, OFF_R = 0.50, 0.70, 1.06

def prior(x, y, m):
    cx, cy = m - 0.5, m - 0.5
    rho = math.hypot(x - cx, y - cy) / math.hypot(m - 0.5, m - 0.5)
    if rho <= RAD_BINS[0]:
        rad = AGG_RADIAL[0]
    elif rho >= RAD_BINS[-1]:
        rad = AGG_RADIAL[-1]
    else:
        for i in range(9):
            if RAD_BINS[i] <= rho <= RAD_BINS[i + 1]:
                t = (rho - RAD_BINS[i]) / (RAD_BINS[i + 1] - RAD_BINS[i])
                rad = AGG_RADIAL[i] * (1 - t) + AGG_RADIAL[i + 1] * t
                break
    diag = DIAG_R if x == y else (NEAR_R if abs(x - y) <= 1 else OFF_R)
    return rad * diag

# ---- prior grid ----
gx = [[prior(x, y, M) for y in range(M)] for x in range(M)]
fig, axes = plt.subplots(1, 2, figsize=(13, 6))
# Left: quadrant
ax = axes[0]
im = ax.imshow(gx, origin='lower', cmap='YlOrRd', vmin=0.3, vmax=1.5,
               extent=[0, M, 0, M], aspect='equal')
ax.scatter([c[1] + 0.5 for c in cells], [c[0] + 0.5 for c in cells],
           s=22, c='navy', marker='s', edgecolors='white', linewidths=0.4,
           label='solution cell')
ax.set_title(f'm=37 fundamental quadrant (37 cells)\n'
             f'navy=chosen cell, color=empirical prior P/(1/m)', fontsize=10)
ax.set_xlabel('column y'); ax.set_ylabel('row x')
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='prior ratio')
# show how many chosen cells sit on the diagonal (should be few)
ndiag = sum(1 for (x, y) in cells if x == y)
ax.text(0.5, -0.16, f'cells on diagonal x=y: {ndiag} (prior avoids it)',
        transform=ax.transAxes, ha='center', fontsize=8, color='navy')

# Right: full board
ax2 = axes[1]
N = 2 * M
ax2.set_xlim(0, N); ax2.set_ylim(0, N)
ax2.set_aspect('equal')
# light grid
ax2.set_xticks(range(0, N + 1, 5)); ax2.set_yticks(range(0, N + 1, 5))
ax2.grid(True, color='lightgray', linewidth=0.3)
# plot all lifted points (4 per cell) in one color; C4 symmetry is visible structurally
px = [p[0] for p in pts]; py = [p[1] for p in pts]
ax2.scatter(px, py, s=10, c='#1f77b4', marker='o', alpha=0.8)
ax2.set_title(f'Full 74x74 board: {len(pts)} lifted points (4 per cell)\n'
              f'C4 symmetry visible; no 3 collinear, no slope+-1 line holds >=3', fontsize=10)
ax2.set_xlabel('X'); ax2.set_ylabel('Y')

plt.tight_layout()
out = os.path.join(HERE, 'solution_m37_biased.png')
plt.savefig(out, dpi=130, bbox_inches='tight')
print('wrote', out)

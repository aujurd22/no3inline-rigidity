"""
Empirical spatial distribution of the "free" fundamental-quadrant cells across all known
rot4 (C4-symmetric) NTIL solutions, for a range of m.

Answers: given that the theorems (FDR / Sidon / R8 quadratic layer) only impose NECESSARY
constraints, do the remaining degrees of freedom (the cells actually selected) show a
non-uniform spatial bias -- i.e. do some regions of the quadrant get populated with higher
probability than others?

Method:
  * load rot4 solutions from flammenkamp_cache via rot4_loader (decodes C4-symmetric 2n-point sets)
  * for each solution extract the m cells of the fundamental quadrant (x < m and y < m)
  * accumulate a 2D histogram -> empirical selection probability P(cell)
  * compare against the uniform baseline 1/m (what pure randomness would give)
  * profile P by: row, column, distance from board centre, distance from quadrant centroid,
    main-diagonal membership, and parity (x+y)
Outputs: cell_distribution.json (stats + profiles) and cell_distribution_heatmap.png
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))   # so rot4_loader is importable
from rot4_loader import load_rot4

OUT_JSON = os.path.join(HERE, 'cell_distribution.json')

# (m, board N=2m) ; pick m with >=~90 solutions for smooth stats, plus the two huge ones
TARGETS = [(15, 30), (16, 32), (17, 34), (18, 36), (19, 38), (20, 40),
           (21, 42), (22, 44), (27, 54), (28, 56)]


def quadrant_cells(sol, m):
    return [(x, y) for (x, y) in sol if x < m and y < m]


def radial_profile(P, m, center, nbins=10):
    """Mean P as a function of normalized radius from `center` (in quadrant coords).
    Returns (bin_centers 0..1, mean_P_ratio)."""
    yy, xx = np.mgrid[0:m, 0:m]
    d = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2)
    dmax = d.max()
    rn = (d / dmax).flatten()
    pf = P.flatten()
    bins = np.linspace(0, 1, nbins + 1)
    bc = 0.5 * (bins[:-1] + bins[1:])
    ratio = np.zeros(nbins)
    for i in range(nbins):
        mask = (rn >= bins[i]) & (rn < bins[i + 1])
        if mask.sum() > 0:
            ratio[i] = pf[mask].mean() / (1.0 / m)
        else:
            ratio[i] = np.nan
    return bc, ratio


def main():
    per_m = {}
    agg_board = []   # list of (rho, ratio) across all m for the board-centre profile
    agg_cent = []
    for m, N in TARGETS:
        sols, ext = load_rot4(N)
        if not sols:
            print(f"m={m} (N={N}): no solutions, skip")
            continue
        cnt = np.zeros((m, m), dtype=np.int64)
        bad = 0
        for sol in sols:
            cells = quadrant_cells(sol, m)
            if len(cells) != m:
                bad += 1
            for (x, y) in cells:
                if 0 <= x < m and 0 <= y < m:
                    cnt[x, y] += 1
        nsol = len(sols)
        P = cnt / nsol
        baseline = 1.0 / m
        flat = P.flatten()

        # row / column profiles
        row_profile = [float(P[i, :].mean()) for i in range(m)]
        col_profile = [float(P[:, j].mean()) for j in range(m)]

        # radial: from board centre (far corner of quadrant at (m-0.5, m-0.5))
        board_center = (m - 0.5, m - 0.5)
        bc_b, ratio_b = radial_profile(P, m, board_center)
        # radial: from quadrant centroid
        quad_cent = ((m - 1) / 2.0, (m - 1) / 2.0)
        bc_c, ratio_c = radial_profile(P, m, quad_cent)

        # diagonal membership (x==y) and near-diagonal (|x-y|<=1)
        diag_mask = np.eye(m, dtype=bool)
        near_mask = np.abs(np.mgrid[0:m, 0:m][0] - np.mgrid[0:m, 0:m][1]) <= 1
        diag_P = float(P[diag_mask].mean()) / baseline
        near_P = float(P[near_mask].mean()) / baseline
        off_P = float(P[~near_mask].mean()) / baseline

        # parity x+y even vs odd
        even_mask = ((np.mgrid[0:m, 0:m][0] + np.mgrid[0:m, 0:m][1]) % 2 == 0)
        even_P = float(P[even_mask].mean()) / baseline
        odd_P = float(P[~even_mask].mean()) / baseline

        stats = {
            'm': m, 'N': N, 'ext': ext, 'num_solutions': nsol,
            'bad_quadrant_count': bad,
            'baseline_P': baseline,
            'mean_P': float(flat.mean()), 'std_P': float(flat.std()),
            'min_P': float(flat.min()), 'max_P': float(flat.max()),
            'cv': float(flat.std() / flat.mean()),
            'frac_hot(>1.5x)': float((flat > 1.5 * baseline).mean()),
            'frac_cold(<0.5x)': float((flat < 0.5 * baseline).mean()),
            'never_used_cells': int((cnt == 0).sum()),
            'never_used_frac': float((cnt == 0).mean()),
            'diag_ratio': diag_P, 'near_diag_ratio': near_P, 'off_diag_ratio': off_P,
            'even_parity_ratio': even_P, 'odd_parity_ratio': odd_P,
        }
        per_m[m] = {
            'stats': stats,
            'row_profile_ratio': [r / baseline for r in row_profile],
            'col_profile_ratio': [r / baseline for r in col_profile],
            'board_radial': {'bin_centers': bc_b.tolist(), 'ratio': ratio_b.tolist()},
            'quad_radial': {'bin_centers': bc_c.tolist(), 'ratio': ratio_c.tolist()},
        }
        # collect into aggregate (use ratios; rho comparable across m after normalization)
        for rho, rt in zip(bc_b, ratio_b):
            if not np.isnan(rt):
                agg_board.append((rho, rt))
        for rho, rt in zip(bc_c, ratio_c):
            if not np.isnan(rt):
                agg_cent.append((rho, rt))
        print(f"m={m:>2} N={N:>2} sols={nsol:>5} cv={stats['cv']:.3f} "
              f"never={stats['never_used_cells']:>4}({stats['never_used_frac']*100:.1f}%) "
              f"hot={stats['frac_hot(>1.5x)']*100:.1f}% diag={diag_P:.2f} even={even_P:.2f}")

    # aggregate radial profiles (bin by rho across all m, average ratio)
    def aggregate(pairs):
        arr = np.array(pairs)
        bins = np.linspace(0, 1, 11)
        bc = 0.5 * (bins[:-1] + bins[1:])
        out = []
        for i in range(10):
            mask = (arr[:, 0] >= bins[i]) & (arr[:, 0] < bins[i + 1])
            out.append(float(arr[mask, 1].mean()) if mask.sum() else np.nan)
        return bc.tolist(), out

    agg_bc, agg_b = aggregate(agg_board)
    agg_cc, agg_c = aggregate(agg_cent)

    out = {
        'description': 'Empirical selection-probability distribution of fundamental-quadrant '
                       'cells across known rot4 NTIL solutions. ratio = P(cell)/(1/m); 1.0 = uniform.',
        'per_m': per_m,
        'aggregate_board_radial': {'bin_centers': agg_bc, 'ratio': agg_b},
        'aggregate_quad_radial': {'bin_centers': agg_cc, 'ratio': agg_c},
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved {OUT_JSON}")
    return out


if __name__ == '__main__':
    main()

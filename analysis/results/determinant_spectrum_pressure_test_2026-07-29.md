# Determinant-spectrum pressure test

**Status:** empirical, with every target energy independently recounted,
2026-07-29.

The exact cubic trace identity recovers the mass at determinant zero.  This
experiment asks a harder predictive question: can the distribution of
**nonzero** determinants identify a defect or the move that repairs it without
being told the zero mass?

## Dataset

The 249 configurations were:

| class | count |
|---|---:|
| verified NTIL configurations | 31 |
| one-, two-, and four-orientation-flip controls | 180 |
| random 2-regular C4 configurations | 30 |
| archived `m=37,V=20` states | 6 |
| current `m=38,E=5` states | 2 |

All predictor features were computed from normalized nonzero determinant
histograms or smoothed kernels of those histograms.  The exact number of
zero-determinant triples was not an input feature.

## Global discrimination

On the controlled orientation-flip states, the strongest individual feature
had absolute Spearman correlation

```text
|rho| = 0.3665
```

with exact defect energy.  In particular, archived state `v20_06` is close to
the true `n=74` solution under several spectral summaries despite having 20
bad triples.  The nonzero area spectrum therefore does not reliably separate
zero defect from a small residual defect.

## Held-out local-move recovery

Twelve test states were made by applying one known orientation flip to a true
solution.  Every legal one-flip move in the fixed topology was ranked without
using its resulting exact defect energy.  The correct inverse move is known
because it restores the source solution.

The best tested feature, `kernel(0.02)`, achieved:

| cutoff | successful recoveries |
|---|---:|
| top 1 | 0/12 |
| top 3 | 2/12 |
| top 5 | 6/12 |

The median inverse-move rank was 5.5.  Under the corresponding random-rank
null model, the top-three result has tail probability about 0.470, while the
top-five result has tail probability about 0.0265.

As a second held-out test, the exact best orientation flip for each of the six
V20 and two `m=38,E=5` states was compared with the spectral order.  Only
`3/8` exact best moves appeared in the spectral top five.

## Conclusion

The signal is too weak to serve as an objective or a correctness filter.  It
can be retained as:

- a top-five prefilter before exact move evaluation;
- a diversity feature among moves with the same exact blocker/palette data;
- a diagnostic for testing any future inequality derived from the cubic trace.

It should not replace exact bad-line counts, blocker graphs, CRT palette
collisions, or capacity-closed degree feasibility.

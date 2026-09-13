# The Four-Tight Exception: A Counterexample to the Half-Turn Universality Conjecture (T41)

**Date:** 2026-09-13. Status: verified computational result (double independent verification).

## 1. Background

For half-turn symmetric (rot2 / rct4) NTIL configurations, the census forms reduce to two
functions on ordered triples of distinct half-turn representatives `p, q, r` (centred doubled
coordinates `X = 2x-(n-1), Y = 2y-(n-1)`):

- `F1(p,q,r) = det(q-p, r-p)`  (representative triangle discriminant)
- `F2(p,q,r) = det(q-p, (-r)-p)`  (two representatives plus the antipode of a third)

A solution is called **4-tight** in a class if the minimum non-zero `|F|` over distinct
representative triples equals exactly 4 — the parity floor, since all six forms are
`≡ 0 (mod 4)`. 4-tightness in `F1` is equivalent to: *the representative set contains a
unimodular triangle* (area exactly 1/2).

A census over 39,631 solutions (Sep 2026) found all 5,045 half-turn solutions tested to be
4-tight in both classes, which motivated:

> **Conjecture T-prime.** Every half-turn NTIL solution is 4-tight in both `F1` and `F2`.

## 2. The counterexample

The conjecture is **false**. The exception is solution **#4 of the Flammenkamp `n=8` rot2
file** — i.e. it sits inside the authoritative corpus, not outside it:

```
(0,2) (0,4) (1,5) (1,7) (2,1) (2,3) (3,0) (3,2)
(4,7) (4,1) (5,4) (5,6) (6,2) (6,4) (7,5) (7,7)
```

Verified independently (all C(16,3) = 560 triples checked): 16 points, exactly 2 per row and
column, half-turn symmetric, **zero collinear triples** — a genuine NTIL solution.

- `min|F1| = 8` — **not 4-tight** (no unimodular representative triangle).
- `min|F2| = 4` — tight.

A full enumeration of `n = 8` half-turn solutions (11 D4-orbits / 36 labelled orientations,
36 = 7 pure-rot2 orbits of size 4 + 4 orbits of size 2 with extra symmetry) shows this is the
**only** orbit containing non-tight orientations: 2 of its 4 orientations are non-tight under
the min-lex representative convention, including the stored Flammenkamp orientation.

## 3. Mechanism: parity confinement

All representatives of the exception lie on **even rows**. For even `n = 2m` the half-turn
row-count condition `r(y) + r(n-1-y) = 2` then forces all representatives into a
`m x m`-like coarse lattice, and every doubled-coordinate determinant picks up a factor of 2:
`F1 = 8 * det_coarse`. The coarse collapse (x, y/2) is a legal 2-regular collinear-free
configuration of the 4x4 board, so the minimum lands on `8 x 1 = 8` instead of `4`.

**Conjecture T41-A:** confined solutions exist only at `n = 8`.

Evidence: lifting every coarse `D(m)` solution back to the fine board kills it for all
`m = 5..10` — 32 + 50 + 132 (exhaustive DFS, m=5..7) plus 57 + 51 + 156 (corpus, m=8..10),
**478 coarse solutions, 0 survivors** (both row parities tested). Deaths split between
center-line collinearity (two representatives and the board centre collinear, 18/32 at n=10)
and general F2 collinearity (14/32), with violation slopes concentrated at (±1,±1) and (±2,±1).

## 4. Refined statements (replacing T-prime)

1. **T-prime-F2 (open, no counterexample):** every half-turn NTIL solution satisfies
   `min|F2| = 4`.
2. **T-prime-canon-F1 (open):** every half-turn solution is F1-tight in its **canonical D4
   orientation** (lexicographically smallest image). The exception's orbit satisfies this.
3. **Finiteness:** `min|F1| = 4` for all half-turn solutions with `n >= 10` (corpus-wide), the
   only exception being the `n = 8` confined pair.
4. **Orientation dependence:** 4-tightness under the min-lex representative convention is
   *not* a D4 invariant for half-turn solutions. For rot4 solutions the quadrant
   representative convention is D4-covariant and tightness is stable (42 reflection/rotation
   images tested, 0 changes).

## 5. Why the census missed it

The census pipeline covered rot2 files `n10..n30` only. Root cause chain: single-digit
filenames (`n8_rot2.txt`) sort *after* `n30_rot2.txt` lexicographically; the driver had a
480 s time-box which expired mid-run; the loop therefore silently truncated its intended
"n <= 20 exhaustive" coverage. **Lesson: coverage claims must be audited against the actual
processed-file list, not the loop's intent.**

## 6. Reproduction

- Census tool: [`analysis/census/fourtight.py`](../analysis/census/fourtight.py)
- Counterexample data: [`data/n8_rot2_counterexample.txt`](../data/n8_rot2_counterexample.txt)
- Exhaustive n=8 enumeration and coarse-lift tests: enumerate all column-pair assignments
  (C(8,2)^4 = 614,656 candidates), filter by row condition + NTIL, compute `min|F1|`.

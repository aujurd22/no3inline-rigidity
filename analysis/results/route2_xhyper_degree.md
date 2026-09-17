# Route② — Exact Conflict-Hypergraph Degree / Co-degree (correction of prior `conflict_hypergraph.md`)

**Date:** 2026-07-13 | **Code:** `route2_xhyper_exact.cpp` → `route2_out.txt`
**Ground truth:** C4 lift from `verify_cells.py` (r=0:(x,y); r=1:(N-1-y,x); r=2:(N-1-x,N-1-y); r=3:(y,N-1-x), N=2m).

## 1. What was computed (exact, not sampled)

The conflict hypergraph H has vertex set V = all m² quadrant cells. Two edge types:
- **(X) ternary hyperedge** on a triple of *distinct* cells {a,b,c}: iff ∃ orientation triple
  (r₁,r₂,r₃)∈{0,1,2,3}³ such that the three C4-lifted points are collinear (and pairwise
  distinct — coincident lifted points are skipped).
- **(S) binary edge** on a pair {a,b}: iff some lifted point of a and some lifted point of b
  lie on a common slope-±1 line.

For m ∈ {10,14,18,22,26,30,37} we enumerated **every** cell-triple (C(m²,3) up to 4.28×10⁸ for
m=37) and counted exactly:
- `deg(c)` = # (X)-hyperedges containing cell c (per-cell degree),
- `cod(a,b)` = # (X)-hyperedges containing the pair (a,b) (co-degree),
- (S) edge count and per-cell (S) degree.

## 2. Exact results

| m | N | total (X) | max deg | avg deg | max co-deg | avg co-deg (active) | active pairs | total (S) | max (S)-deg | avg (S)-deg |
|---|---|----------:|--------:|--------:|----------:|--------------------:|------------:|----------:|-----------:|-----------:|
| 10 | 20 | 23,042 | 908 | 691.26 | 60 | 13.97 | 4,948 | 1,140 | 34 | 22.80 |
| 14 | 28 | 107,372 | 2,211 | 1,643.45 | 92 | 16.87 | 19,098 | 3,276 | 50 | 33.43 |
| 18 | 36 | 330,347 | 4,097 | 3,058.77 | 124 | 18.95 | 52,306 | 7,140 | 66 | 44.07 |
| 22 | 44 | 803,372 | 6,703 | 4,979.58 | 156 | 20.62 | 116,862 | 13,244 | 82 | 54.73 |
| 26 | 52 | 1,669,760 | 9,987 | 7,410.18 | 188 | 21.96 | 228,112 | 22,100 | 98 | 65.38 |
| 30 | 60 | 3,114,921 | 13,979 | 10,383.07 | 220 | 23.10 | 404,494 | 34,220 | 114 | 76.04 |
| 37 | 74 | 7,728,944 | 22,982 | 16,937.06 | 276 | 24.76 | 936,326 | 64,824 | 142 | 94.70 |

**Internal consistency check (m=37):** `total(X) = Σdeg/3 = 16937.06×1369/3 = 7,728,944` ✓.
**Conflict probability:** for fixed c, the fraction of the C(m²−1,2)≈934,003 cell-pairs (a,b) that
form an (X) triple with c is `p_X ≈ avgDeg / C(m²−1,2) ≈ 16937/934003 ≈ 0.0181`. So **≈1.8% of
all cell-triples are (X)-conflicting** under some orientation.

## 3. Corrections to the prior `conflict_hypergraph.md`

The prior doc's Table (§3) reported, for m=37, `avg_x_deg/cell = 0.58` and called H
"extremely sparse … each cell participates in <1 (X)-conflict per configuration". That number was
a **per-random-2-factor** sample mean (a 2-factor has only m=37 cells, and each participates in
<1 conflict *within that 2-factor*). It is **not** the structural degree of H. The exact structural
degree is:

- **avg deg ≈ 16,937** (m=37), **max deg ≈ 22,982** — i.e. H is *dense*, not sparse.
- Degree scales with m roughly as `deg ∝ m^{~2.4}` (avg deg / m² grows 6.9→12.4 across the table),
  because `deg(c) ≈ p_X · C(m²,2)` and p_X stays ≈1.8%.

**What is genuinely sparse is the *induced* subhypergraph H[C] on a specific 2-factor C** (each of
the m selected cells participates in <1 conflict inside that factor). This is the quantity the
gating experiment measured, and it is the right object for local-search / switching arguments. The
global H being dense is why LLL-style arguments need the *lop-sided* variant (large dependency
degree, small bad-event probability), not the claim "bounded degree".

## 4. Useful structural bounds established

- **Co-degree is bounded by O(m):** `max cod(a,b)` = 60,92,124,156,188,220,276 ≈ **7.5·m** across
  m=10…37. So any fixed pair of cells is jointly collinear (under some orientation) with at most
  O(m) third cells. This is the relevant bound for a union-bound / nibble analysis over pairs.
- **(S) edges** are far fewer than (X): total (S) = 64,824 vs total (X) = 7,728,944 (≈0.84%),
  confirming (S) is a minor contribution (consistent with the prior doc's ~3% guess in the same
  direction). (S) avg degree ≈ 94.7 (m=37), max 142.

## 5. Conclusion for m=37 attack

The (X) constraint, viewed on the full cell set, couples each cell to ~17k others — far too dense
for a naive "pick an independent set in H" approach. But on any concrete 2-factor the induced
conflicts are tiny (<1/cell), which is exactly why the switching/gating result (every bad config has
a reducing 2-switch, red_config_frac=1.0) is the operative structural fact. The exact degree/co-degree
numbers here pin down the constants for any future LLL/nibble bound attempt.

*Reproduce:* `g++ -std=c++17 -O2 route2_xhyper_exact.cpp -o r2 && ./r2 > route2_out.txt`

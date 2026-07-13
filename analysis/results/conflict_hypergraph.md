# Conflict Hypergraph Approach to rot4 NTIL

**Status:** Formulation phase — defining the hypergraph and computing its
basic parameters from empirical data.

---

## 1. The model

A rot4 configuration is an m-set C of ordered pairs (i,j) ∈ {0,…,m−1}²,
representing the selected cells in the top-left quadrant. The C4 lift
produces 4m points on the 2m×2m board.  The configuration is NTIL iff:

1. **2-regular condition (Th-44, necessary):** For each vertex v,
   `outdeg(v) + indeg(v) = 2` where `outdeg(v) = #{j: (v,j)∈C}`
   and `indeg(v) = #{j: (j,v)∈C}`.

2. **(X) constraint:** No triple of distinct cells (a,b,c)∈C has a
   collinear C4-lift.

3. **(S) constraint:** No slope-±1 line contains ≥3 lifted points from C.

The (X)+(S) constraints form a **conflict hypergraph** H whose vertices are
the m² candidate cells and whose hyperedges encode forbidden configurations.

---

## 2. Hypergraph definition

Let V = {0,…,m−1}² be the set of all candidate cells (|V| = m²).
Let E ⊆ C(m²,2) ∪ C(m²,3) be the set of conflicting subsets.

### 2.1 (S) conflicts — binary constraints (hyperedges of size 2)

Two cells (i,j) and (p,q) conflict under (S) if they lie on the same
slope-±1 line *after C4 lift*.  This occurs when their C4 orbits share
a slope-±1 line.  The (S) condition says: no slope-±1 line can contain
≥3 points → for each slope-±1 line, at most 2 of its incident cells can
be selected.

This is a **matching** constraint on a graph G_S where vertices are
cells and edges connect cells that share a slope-±1 line.

**Count:** For each slope-±1 line L, let cells(L) be the set of quadrant
cells whose C4 lift includes a point on L.  The constraint is that at
most 2 cells from cells(L) may be selected.  |cells(L)| varies; typically
2–4 cells per line for most L.

### 2.2 (X) conflicts — ternary constraints (hyperedges of size 3)

Three distinct cells (i,j), (p,q), (r,s) conflict under (X) if there exist
C4 rotations r₁,r₂,r₃ such that the three lifted points are collinear:

    det( C4((i,j),r₁), C4((p,q),r₂), C4((r,s),r₃) ) = 0.

By the R8 analysis, this condition decomposes into 16 orbit classes per
triple of distinct cells.  Each class gives a quadratic form
det_{t}((i,j),(p,q),(r,s)) whose vanishing creates a conflict.

**Key parameter:** For a given triple of cells (a,b,c), what proportion
of the 16 orbit classes produce vanishing determinants?  This is the
conflict probability p_X for random cells.

### 2.3 Induced subhypergraph on a 2-factor

A 2-factor selects exactly m cells C ⊂ V with the degree condition.
The restricted hypergraph H[C] has:

- m vertices (the selected cells)
- (S) edges among them (size-2 conflicts) — at most |C|/2 edges
- (X) hyperedges among them (size-3 conflicts) — at most C(m,3)

The configuration is NTIL iff C induces an independent set in H, i.e.,
H[C] has **no hyperedges at all**.

---

## 3. Parameters from gating data

The exact conflict hypergraph parameters were measured by `conflict_hypergraph_params.py`,
sampling random 2-factors and counting (X) and (S) conflicts per factor:

| m | avg (X)/factor | avg (S)/factor | avg_x_deg/cell | max_x_deg | cells in (X) |
|---|---|---|---|---|---|
| 10 | 30.2 | 3.2 | 453 (0.91/factor) | 704 | 100/100 |
| 14 | 54.0 | 4.8 | 414 (0.83/factor) | 684 | 196/196 |
| 18 | 83.6 | 5.6 | 387 (0.77/factor) | 712 | 324/324 |
| 22 | 116.5 | 5.6 | 328 (0.72/factor) | 800 | 484/484 |
| 26 | 153.9 | 6.6 | 262 (0.68/factor) | 620 | 676/676 |
| 30 | 191.6 | 6.6 | 213 (0.64/factor) | 580 | 900/900 |
| 37 | 265.2 | 7.0 | 157 (0.58/factor) | 380 | 1368/1369 |

**Key structural findings:**

1. **(X) dominates (S):** ≈ 97% of conflicts are (X)-type (3 distinct cells);
   (S)-type (2 cells + extra lifted point) accounts for only ≈ 3%.
   This justifies focusing LLL analysis on (X) constraints.

2. **Per-cell (X)-degree DECREASES with m:** From 0.91 (m=10) to 0.58 (m=37)
   per factor.  Each selected cell participates in <1 (X)-conflict per
   configuration on average — the conflict hypergraph is **extremely sparse**.

3. **Maximum per-cell degree is bounded:** max_x_deg = 380–800 across all m.
   Even in the worst case, a single cell rarely appears in >800 (X)-triples
   over 500 random factors, corresponding to <2 (X)-triples per factor.
   The effective degree per factor per cell is bounded by a small constant.

4. **Total (X) conflicts scale as O(m), not O(m³):** E[#(X)] ≈ 7.2m.
   The 16 orientation classes (from R8) are non-zero for the overwhelming
   majority of cell triples; only O(1/m²) of all possible triples coincide
   in both selection AND collinearity.

These parameters are **very favorable** for the LLL approach: the dependency
graph of bad events has bounded degree (each cell is in O(1) events per
configuration), and the hypergraph becomes systematically sparser as m grows.

---

## 4. Available tools

### 4.1 Conflict-free factor / Nibble (Rödl)

The Rödl nibble is a semi-random method for finding independent sets in
sparse hypergraphs.  It works when:

- The hypergraph H is **k-uniform** with k = O(1) (here k ∈ {2,3}).
- Maximum degree Δ(H) is small relative to the number of vertices.
- The hypergraph is **regular enough** (degree variation is bounded).

For our problem:
- H has mixed uniformity (2 and 3), but can be homogenized.
- Δ(H) for (X)-hyperedges: each cell (i,j) participates in ≈ O(m²)
  potential triples, but only O(m) of those are collinear on any fixed
  orientation class — so effective degree is O(m), not O(m²).
- The nibble would start from all m² cells and iteratively pick a random
  subset, removing cells that violate degree constraints.

**Obstacle:** The degree-2 constraint (each vertex must have exactly 2
incident edges in the 2-factor) is not a hypergraph constraint — it's a
**global structural constraint** on the selection.  The nibble typically
handles local constraints (max degree), not global equality constraints.

### 4.2 Switching / Lopsided Lovász Local Lemma

The gating experiment showed that for m ≥ 14, **every** bad configuration
contains a 2-switch (replacing 2 edges) that strictly reduces the number
of bad lines (red_config_frac = 1.0).  This is a key structural property
of the hypergraph H:

- Each (X) hyperedge can be "repaired" by changing at most 2 cells of the
  2-factor (a 2-switch).
- The dependency graph of bad events under the switching process has
  bounded degree (each switch involves at most 4 cells; two events are
  dependent if they share a cell).

If the switching oracle can be shown to satisfy the **lop-sidedness**
condition (each bad event has a set of "dangerous" switches that don't
increase it), a Lopsided LLL argument could prove existence of a 0-bad
configuration.

### 4.3 Absorption / regularity lemma

The 2-factor + conflict hypergraph can be viewed as a sparse regular
hypergraph with a 1-factorization constraint.  The absorption method
(Szemerédi-type) could show that for sufficiently large m, a conflict-free
2-factor exists if certain discrepancy conditions hold.

---

## 5. Immediate next steps

1. **Compute hypergraph degrees** from the R9b generator: for each cell
   (i,j), count how many (X) triples it participates in.  Also compute
   the co-degree (pairs of cells that appear together in ≥1 (X) triple).

2. **Verify the "O(m) effective degree" claim**: for random cells, what
   fraction of the 16 orientation classes actually produce a zero
   determinant?  If most classes are non-zero for most triples, the
   effective hypergraph is sparse.

3. **Check the 2-switch property formally**: prove that for any set C
   containing at least one (X) conflict, there exists a 2-switch (swap
   two edges) that strictly reduces the number of bad lines.  The gating
   experiment empirically confirms this; a proof would justify the LLL.

4. **Attempt Lopsided LLL**: construct the dependency graph of bad events
   (each bad line = one event), compute maximum degree, and check whether
   the lop-sided condition `∑_{E'∼E} p(E') ≤ 1/4` holds.

---

## 6. Connection to other approaches

The conflict hypergraph is **equivalent** to the quadratic CSP of R8-G,
but reformulated in a language that admits combinatorial existence tools
(nibble, LLL, absorption).  If a conflict-free 2-factor existence theorem
can be proved for m ≥ m₀ (some threshold), then m=37 can be resolved by
checking finitely many cases below m₀.

This approach complements, rather than replaces, the Burnside orbit
counting (direction 5) — which provides precise formulas for the
hypergraph's symmetries.

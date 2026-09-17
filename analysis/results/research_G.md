# Research Direction G — Spatial prior of the "free" cells (user's question)

**Date:** 2026-07-14
**Trigger:** user asked — *besides the points/layout fixed by theorems, do the remaining "random"
cells have a special probability distribution; do some regions get selected with higher probability?*
**Status:** Empirically ANSWERED — YES, strongly non-uniform; the bias is a statistical shadow of the
known linear/quadratic constraints but is NOT predicted by any simple necessary condition.
**⚠️ RETRACTION (2026-07-14, later same session):** the "m=37 solution" previously reported in §6 was a
**FALSE POSITIVE** and has been retracted. The biased SA (`biased_nibble.py`) used an *incomplete*
collinearity test (it only forbade equally-spaced / doubling triples `p3 = 2·p2 − p1`, not general
collinearity), so its "valid" configs actually contain hundreds of collinear triples. Rigorous
re-verification over ALL C(4m,3)=529,396 triples (`verify_certificate.py`) found **284 collinear
triples (biased)** and **344 (unbiased)** → both INVALID. Gap B is **NOT** closed; **m=37 remains OPEN.**
See §6 (now a post-mortem) and `verify_certificate.json`.
**Data/code:** `cell_distribution.json`, `cell_distribution_heatmap.png`, `analyze_cell_distribution.py`,
`make_cell_heatmap.py`. Source: Flammenkamp rot4 cache (m = 15..28; up to 10,441 solutions at m=28).
The §1–§5 empirical spatial-prior findings below stand; only the §6 "constructive existence" claim is retracted.

---

## 1. Method

For each known rot4 (C₄-symmetric) NTIL solution, extract its m fundamental-quadrant cells
(`x < m and y < m` in board coords `0..2m-1`). Accumulate a 2D histogram over all solutions →
empirical selection probability `P(cell)`, and compare to the uniform baseline `1/m` (what pure
randomness would give). Profile `P` by row, column, distance from board centre, distance from
quadrant centroid, main-diagonal membership (`x=y`), and parity (`x+y`).

`ratio = P(cell) / (1/m)`; **1.0 = uniform**, >1 over-selected, <1 avoided.

## 2. Findings (robust across m = 15..28)

| Probe | Result | Interpretation |
|---|---|---|
| Coefficient of variation of P | **0.42–0.64** (uniform → 0) | Strong spatial structure, not random |
| Diagonal cells `x=y` | **ratio 0.39–0.52** | **Strongly avoided** (~half the uniform rate) |
| Near-diagonal `|x−y|≤1` | ratio 0.65–0.71 | avoided |
| Off-diagonal | ratio 1.05–1.08 | mildly preferred |
| Parity `x+y` even vs odd | ratio ≈ 1.00 both | **no bias** (rules out arithmetic explanation) |
| Board-centre radial profile (aggregate) | `[0.55, 0.83, 0.77, 0.81, 0.93, 1.02, **1.39**, **1.33**, 0.44, 0.14]` | **minima at centre (ρ=0 →0.55) and corner (ρ=0.95 →0.14); peak at mid-radius ρ≈0.65–0.75 (~1.35×)** |
| Bias strength vs m | cv 0.64 (m=15) → 0.42 (m=28) | weakens with m but persists |

**So the "free" points are far from uniform.** They avoid the main diagonal, avoid both the board
centre and the board corner, and prefer a mid-radius annular ring at ~1.35× the uniform rate. The
pattern is geometric (radial/diagonal), not arithmetic (parity is flat).

## 3. Why — connection to the known theorems

The bias is a **statistical shadow** of constraints we already know, surfacing in a way no simple
necessary condition captures:

- **Anti-diagonal avoidance.** A quadrant cell on `x=y`, lifted by C₄, lies along the board's two
  diagonal directions. Those are exactly the **slope±1 lines through the centre** — the most
  capacity-constrained lines (FDR / R8: every slope±1 line holds ≤2 points, and for the lifted
  solution every line holds ≤2). Diagonal cells compete for that scarce capacity → avoided. This is
  the FDR/R8 slope±1-capacity constraint made visible, but it is *emergent*, not a separate theorem.
- **Annular preference.** Near the board centre the lifted C₄ orbits are densely packed → highest
  (X) conflict density (cf. `conflict_hypergraph.md`: per-cell (X)-degree is largest near centre).
  Near the corner, cells sit on board-edge / diagonal directions where collinearity is easy. The
  mid-radius ring minimizes both → the "sweet spot." Again the (X) quadratic layer, emergent.
- **No parity bias** confirms the structure is geometric, not a checkerboard-level invariant.

## 4. Significance

1. **Confirms the user's intuition:** the "random" part of a solution is *not* uniformly random — it
   carries a strong, reproducible geometric prior.
2. **New lever for Gap B (the m=37 / asymptotic existence bottleneck).** Routes 1–2 (nibble /
   lopsided LLL on the 2-factor space) currently treat cells symmetrically. Biasing cell selection
   toward the annular / anti-diagonal-friendly region (the empirical prior) should sharply improve
   the nibble's conflict-reduction and the LLL margin. This is a concrete, data-driven refinement of
   the closure lemma.
3. **Formalizable as a 7th direction:** "spatial prior of the solution manifold" — prove (or bound)
   that any (X,S)-free set must concentrate away from the diagonal/centre/corner, tightening the
   LLL degree bound (the `x_deg_max` used in Lemma B.1) via the prior rather than the worst case.

## 5. Verdict

- Empirical question: **answered — YES, strong regional bias** (diagonal & centre & corner avoided;
  mid-radius ring preferred; no parity effect). ✅
- Theoretical status: the bias is *explained post-hoc* by known constraints but is **not** captured
  by any existing theorem as an explicit spatial statement → a genuine open refinement (Direction G).
- Novelty: empirical characterization of the rot4 solution manifold's spatial prior appears new (not
  in the 2026-07-13 audit). Recommend folding into Gap B as a biased-selection improvement.

---

## 6. POST-MORTEM — the retracted "m=37 solution" (a verification failure, NOT a breakthrough)

**⚠️ This section previously claimed a constructive m=37 solution. That claim is RETRACTED.** What
follows is the corrected record of what actually happened, kept as a cautionary case study.

### 6.1 What was claimed
`biased_nibble.py` ran a biased/unbiased 2-regular (permutation-family) simulated annealing and
reported configs with `bad_X = bad_S = 0`. These were declared valid m=37 rot4-NTIL solutions and
emitted as `solution_m37_biased.json` / `solution_m37_unbiased.json`. Gap B was declared "closed."

### 6.2 The two bugs that produced the false positive
1. **Incomplete collinearity test (root cause).** `biased_nibble.py::precompute()` only enumerated
   *equally-spaced* collinear triples via the doubling formula `p3 = 2·p2 − p1`. General collinear
   triples (three points on a line with unequal spacing) were never forbidden. So `bad_X = 0` meant
   "no equally-spaced collinear triple," NOT "no three collinear points." The "verifier"
   `verify_and_emit.py` shared the same incomplete triple set, so it rubber-stamped the same error.
2. **Too-narrow search family.** The SA searched the **permutation family (A)** — exactly one cell per
   row of the fundamental quadrant. But real rot4 solutions live in the broader **R9b 2-factor family**
   (`rowSum[i] + colSum[i] = 2`; rows may hold 0 or 2 cells). Family (A) is a strict subset that does
   **not** contain the real solutions (see §6.4).

### 6.3 Rigorous re-verification (the fix: `verify_certificate.py`)
A from-scratch verifier re-derives all 4m = 148 lifted points from each saved config and checks
**every** triple — all C(148,3) = **529,396** — for collinearity via the cross-product test
`(b−a)×(c−a) = 0`. Results (`verify_certificate.json`):

| config | permutation | 148 distinct pts on board | C4-closed | collinear triples | VALID? |
|---|---|---|---|---|---|
| `solution_m37_biased.json`   | ✓ | ✓ | ✓ | **284** | ❌ **INVALID** |
| `solution_m37_unbiased.json` | ✓ | ✓ | ✓ | **344** | ❌ **INVALID** |

Both "solutions" contain hundreds of genuinely collinear triples. **They are not rot4-NTIL solutions.**

### 6.4 Confirming the family is too narrow (`solve_rot4_correct.py`)
A corrected SA using the **full** collinearity objective was calibrated against ground truth:
- Cached (Flammenkamp) solutions for m = 14/20/28/36 have `direct_collinear = 0` (ground truth OK),
  but their orbit reps do **not** form a permutation (`perm_extract_ok = False`) — direct proof that
  real solutions are *not* in family (A).
- Running the corrected SA over family (A) on **known-solvable m=14** plateaus at **20 collinear
  triples, 0/3 solves** — it provably cannot reach a real solution because family (A) doesn't contain
  one. (m=37 objective eval ≈ 25 ms over 529,396 triples, for scale.)

### 6.5 Corrected status
- **m=37 rot4-NTIL is OPEN.** No valid solution has been constructed. Gap B is **not** closed.
- The §1–§5 spatial-prior findings remain valid (they are descriptive statistics of *cached* real
  solutions, computed correctly). Only the §6 "constructive existence" claim is retracted.
- The correct model for any future attack is the **R9b 2-factor family + full per-line at-most-2 /
  full collinearity test** (see `solve_m37_r9b.py`, `verify_certificate.py`, `solve_rot4_correct.py`).
- Artifacts flagged INVALID: `solution_m37_biased.json`, `solution_m37_unbiased.json`,
  `solution_m37_biased.png`, `chessboard_m37_biased.png`, `chessboard_m37_unbiased.png` (these
  visualize non-solutions and must not be cited as m=37 solutions).

### 6.6 Lesson (methodological)
The failure was a **verification** failure, not just a search failure: the search *and* its verifier
shared the same incomplete definition of "collinear." Rule reinforced (Math-skill "Always Verify"):
a solution certificate must be checked by an **independent** verifier implementing the *complete*
definition (all triples, cross-product), and calibrated against known-good ground truth before any
existence claim is made.

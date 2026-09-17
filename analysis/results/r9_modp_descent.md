# R9 — Mod-p Descent and the 2-Regular Reformulation (notes, 2026-07-13)

**Status:** two results.  R9a is a *corrected* necessary-condition lemma (a natural
conjecture is shown FALSE by a coordinate-collision pitfall).  R9b is a
*structural reformulation* of the m=37 problem that points to the fastest
algorithmic attack.

---

## R9a — Mod-p descent: valid only for p > 2m (a pitfall caught)

**Natural (but FALSE) conjecture.**  "Since m=37 is prime, work modulo 37:
a rot4 NTIL must satisfy the (X)+(S) determinant system over F_37; search
over F_37 first, then lift."  This is *false*, and the reason is instructive.

**Why it fails (coordinate collision).**  The lifted points live on the
`(2m)×(2m)` board with coordinates in `{0,…,2m−1}`.  For m=37, `2m=74 > 37`,
so two *distinct* lifted points can differ by exactly 37 in one coordinate
(e.g. `(x,y)` and `(x+37,y)`) and therefore **coincide modulo 37**.  Any triple
containing two such points has `det ≡ 0 (mod 37)` trivially (the two points are
identical mod 37), so the "no three collinear mod 37" condition is violated by
*every* configuration that has such a congruence — including perfectly valid
integer NTIL configurations.  Hence "no-three-collinear over F_37" is **not**
a necessary condition for rot4 NTIL, and an F_37 search would *reject all valid
solutions*.  The conjecture is dead.

**Corrected lemma (R9a, valid).**  Let `p` be a prime with `p > 2m`.  Then a
rot4 NTIL of order `2m` must satisfy the `(X)+(S)` system over `F_p`.
*Proof.*  Collinearity of three lifted points means an integer determinant
`det = 0`; reducing mod `p` gives `det ≡ 0 (mod p)`, i.e. collinearity over
`F_p`.  Because all coordinates lie in `[0,2m−1] < p`, no two distinct lifted
points coincide mod `p`, so there are **no** spurious degeneracies.  Thus
"no-three-collinear over F_p" is a genuine necessary condition and can be used
as a pre-filter.  For m=37 the smallest such prime is `p=79`.

*Consequence.*  R9a is a correct but **generic** pruner (it works for any m,
not just prime m, and does not exploit primality).  It shrinks the candidate
set but does not simplify the search structurally — the F_p-satisfying set is
still a large superset of the integer solutions.  It is useful as a cheap
rejector inside a search, not as a stand-alone solver.

---

## R9b — The 2-regular reformulation (the real structural breakthrough)

**Theorem (Th-44, restated).**  A rot4 (C4-symmetric) NTIL of order `2m` exists
**iff** there is a decomposition of the `m` odd numbers
`{1,3,…,2m−1}` into a 2-regular digraph (a permutation `π`, i.e. a disjoint
union of directed cycles covering all `m` vertices) with a binary orientation
chosen per edge, such that the induced `m` fundamental-quadrant cells satisfy
the quadratic `(X)+(S)` system.

**Why this matters for speed.**  The current exact attack
(`cpsat_symmetric_ntil.py`) models the problem as *choose an m-subset of the
`m×m` quadrant* — `C(m²,m)` candidate sets, with the 2-regular structure only
*implicitly* enforced by the `(X)+(S)` constraints.  It therefore spends most
of its search on cell-subsets that do **not** correspond to any 2-regular
pairing.  The true combinatorial object is a **permutation** (m! objects, with
m orientation bits), which is *smaller* in the relevant sense and, crucially,
has the 2-regular property **built in for free**.

**Algorithmic prescription.**  Model m=37 as an **assignment/permutation CSP**:
- variables `x[i][j] ∈ {0,1}` for `i,j` in the `m` odd vertices, with
  `Σ_j x[i][j] = 1` (out-degree) and `Σ_i x[i][j] = 1` (in-degree) — a
  permutation, natively handled by CP-SAT;
- an orientation bit per edge;
- the `(X)+(S)` collinearity conditions, written over the cells derived from
  the chosen edges.

This (i) removes the `C(m²,m)` superset waste, (ii) gives CP-SAT a tight
assignment structure to propagate on, and (iii) is the same proven-exact
quadratic characterization (R8), merely re-hosted on the correct variables.  It
is the most promising *method* improvement over the 1.26M-constraint per-line
model, and is the recommended next implementation step once the current
resilient per-line run has been given a long horizon.

---

## Status of m=37 (summary)

- **Existence** is *plausible* (phase-transition analysis: m=37 is not at a
  sharp satisfiability transition; source-ratio ≈ 0.26 and max-cycle ≈ 0.79m
  are continuous through m=36→37; all m=3..36 have solutions) but *extremely
  rare* (Sidon rate dropped ≈50× from m=36 to m=37).
- It is a **decidable finite CSP** (R8): distinct 37-subset of 37×37 satisfying
  (X)+(S).  No theoretical obstruction (parity, modular, or invariant) is known
  that rules it out.
- The open problem is therefore **constructive / computational**, not
  structural: find a satisfying assignment (SAT) or prove none exists (UNSAT).
  Both are now well-posed algebraic questions.  The resilient per-line CP-SAT
  (checkpoint + hot-start) is attacking it; the permutation-space reformulation
  (R9b) is the faster model to build next.

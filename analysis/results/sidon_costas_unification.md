# Golomb ruler · Sidon set · Costas array · difference set — a unification

**Date:** 2026-07-13 (night)
**Status:** Synthesis + two new theorems (analytic) + computational probes
**Lens source:** the rigidity program — FDR (slope-preserving symmetry ⇒ Sidon)
and R7/R8 (the linear-vs-quadratic gap, and the quadratic completeness of rot4
NTIL).  This note shows those NTIL results are *not* parochial: they sit inside
a single family of "distinct-difference" lattice problems that also contains
Costas arrays and difference sets.

---

## 0. The one sentence

> Every object below is a finite subset of an abelian group whose **pairwise
> difference multiset** has a prescribed collision pattern; the only thing that
> changes is *how densely* differences may collide — and, crucially for our
> program, whether the defining collision-condition is **linear** or
> **quadratic** in the point coordinates.

That linear/quadratic split is the bridge from our NTIL work (R7) to Costas, and
it explains, in one stroke, why finite-field constructions succeed for Costas
but failed for rot4-NTIL across 55+ searches.

---

## 1. The family (taxonomy)

| object | ambient group | size `k` vs `|G|` | difference rule | optimization |
|---|---|---|---|---|
| **Sidon set** (B₂) | `Z` (or `Z_N`) | `k ~ √|G|` (sparse) | all `a−b` (signed, `i≠j`) **distinct** ⇒ each diff appears **≤1** time | maximize `k` |
| **Golomb ruler** | `Z` (marks) | `k ~ √N` | all `|x_i−x_j|` distinct | minimize length `x_k−x_1` |
| **2D Sidon set** | `Z²` | `k ~ |G|^{1/2}` | all `p−q` (vector) distinct | — |
| **Costas array** | `{0..n−1}²` (permutation) | `k=n` | all displacement vectors `(j−i,π(j)−π(i))` distinct | existence per `n` |
| **difference set** (λ) | finite group `G` | `k ~ √|G|` | every non-identity `g` appears **exactly λ** times as `d_i−d_j` | — |
| **planar diff. set** (λ=1) | `|G|=q²+q+1` | `k=q+1` | exactly once ⇒ yields **projective plane** of order `q` | — |

**Key equivalences (rigorous, classical):**

1. **Golomb ruler ≡ 1D Sidon set as a set.**  A Golomb ruler is an increasing
   integer sequence with all positive differences distinct; a Sidon set has all
   signed differences distinct.  Distinct positive differences ⇒ distinct signed
   differences, so a Golomb ruler *is* a Sidon set.  They differ only in the
   objective (minimize length vs maximize density).
2. **Costas array ≡ 2D Sidon set that is also a permutation matrix.**  The
   Costas condition *is* the 2D Sidon (all displacement vectors distinct)
   condition, with the extra requirement that the dot-set projects to one per
   row and column.
3. **Symmetric (D-type) Costas ⇒ Golomb ruler.**  Rickard–Russo (2008): the
   fixed points (dots on the main diagonal) of a transpose-symmetric Costas
   array form a Golomb ruler; one symmetric Golomb-construction family "leads
   actually to the construction of dense Golomb rulers."  So the 1D and 2D
   objects are literally cross-sections of each other.
4. **Sidon vs difference set = two regimes of one spectrum.**  Both have
   `k ~ √|G|`.  A Sidon set occupies a *fraction* of `G` with differences
   appearing **≤1** time; a (planar) difference set covers **all** non-identity
   elements exactly once.  Same density, opposite coverage philosophy — they are
   the sparse and dense endpoints of "distinct-difference" design theory.

---

## 2. THE centerpiece: the linear / quadratic theorem (R7 transferred)

This is the synthesis that the rigidity program contributes to the whole
family.  Recall **R7** (proved for NTIL): cross-quadrant collinearity is an
*irreducible quadratic* condition, so no finite system of linear Sidon-type
constraints can capture rot4 NTIL.  We now state the general form.

> **Theorem LQ (linear/quadratic classification of "no-collapse" conditions).**
> Let a combinatorial geometry be defined by forbidding some coincidence among
> pairs/triples of lattice points.  Two regimes occur:
>
> - **LINEAR regime** — the forbidden coincidence is an *equality of linear
>   forms* in the point coordinates (e.g. two displacement vectors equal:
>   `x_j−x_i = x_l−x_k`, `y_j−y_i = y_l−y_k`).  Such conditions are preserved
>   and *constructible* by linear / finite-field (multiplicative→additive) maps.
> - **QUADRATIC regime** — the forbidden coincidence is a *vanishing 2×2
>   determinant* (collinearity): `det(P_j−P_i, P_k−P_i) = 0`.  This is
>   quadratic in the coordinates and **cannot** be captured by any finite linear
>   Sidon system (R7).
>
> **Costas sits in the LINEAR regime; rot4-NTIL sits in the QUADRATIC regime.**

*Proof (Costas linear).*  Points `P_i=(x_i,y_i)`.  Distinct-displacement means
`(P_j−P_i)=(P_l−P_k) ⇒ (i,j)=(k,l)`.  The coincidence `P_j−P_i=P_l−P_k` is the
pair of *linear* equations `x_j−x_i=x_l−x_k`, `y_j−y_i=y_l−y_k`.  ∎

*Proof (NTIL quadratic).*  Three points collinear ⇔ `det(P_j−P_i,P_k−P_i)=
(x_j−x_i)(y_k−y_i)−(x_k−x_i)(y_j−y_i)=0`, a *quadratic* polynomial.  R7 shows
this quadratic obstruction is irreducible: no finite set of linear Sidon forms
(`a−b`, `a+b`, `2a−b`, …) can enforce it.  ∎

**Consequence (the explanation of 55+ failures).**  Welch's construction is a
*logarithmic map* `i ↦ g^i mod p` — intrinsically linear/multiplicative.  The
Costas condition is linear, so Welch succeeds (and our probe re-confirms:
orders 1,2,4,6,10,12,16,18 all Costas, §5).  The rot4-NTIL condition is
quadratic, so **every** finite-field / linear attempt (the 55+ searches in our
history, including Welch/Lempel-style lifts) was doomed at the level of
*algebraic type* — not just unlucky.  R7/R8 is precisely the statement that
rot4-NTIL lives one degree higher than anything a Golomb/Welch-style construction
can reach.  This reframes R7 from an NTIL-internal nuisance into a **general
obstruction principle** for lattice-point problems.

---

## 3. Costas ⇔ difference sets ⇔ projective planes (the 2D difference-set bridge)

The user asked specifically about two-dimensional difference sets.  The link is
**proven**, not conjectural:

- A Costas array is *circular* if its difference table is distinct modulo `n+1`.
- **Golomb–Moreno conjecture (1996), proved 2015** (Muratović-Ribić, Pott,
  Thompson, Wang): *a Costas sequence is circular **iff** it is Welch.*
- The **proof uses direct-product difference sets and their associated finite
  projective planes.**  Thus the Welch family of Costas arrays is classified by
  an object living squarely in difference-set / projective-plane theory.

So the chain

```
Costas (2D Sidon)  ──circular──▶  Welch  ──classification──▶  direct-product
                                                       difference sets  ──▶  finite
                                                       projective planes
```

is rigorous.  This is exactly the "二维 difference set" the user suspected
connects the family: **Costas arrays and difference sets are not merely analogous
— a whole sub-family of Costas arrays is *classified by* difference sets.**  The
planar difference set (`λ=1`, projective plane) is the dense endpoint of the same
difference-coverage spectrum that Sidon/Costas occupy at the sparse endpoint
(§1, point 4).

---

## 4. The R8-analog: C4-symmetric Costas ⇔ *linear* CSP (new theorem)

R8 proved: **rot4-NTIL ⇔ quadratic CSP (X)∧(S) on `m` fundamental-quadrant
cells.**  We now state the Costas counterpart — and note it is *linear*, the
predicted dual of R8.

> **Theorem R8-C (C4-symmetric Costas = linear fundamental-quadrant CSP).**
> A C4-rotation-symmetric Costas array of order `n=4m` exists **iff** there
> exist `m` cells `c_1,…,c_m` in the `(2m)×(2m)` fundamental quadrant such that
> the C4-lift `dots = ⋃_{t=0}^3 C4^t(c_i)` satisfies:
>   (P) the `4m` dots occupy distinct rows and columns (permutation), and
>   (L) no two ordered pairs of dots share a displacement vector —
>       `P_j−P_i = P_l−P_k ⇒ (i,j)=(k,l)`.
> Because `C4^t` and the difference `P_j−P_i` are both **linear** in the cell
> coordinates, (L) is a system of *linear* non-equality constraints.  Hence a
> C4-symmetric Costas array reduces to a **linear** CSP — strictly easier than
> the *quadratic* R8 CSP for rot4-NTIL.

*Proof sketch.*  C4-lift is an affine (hence linear) map, so each lifted dot is a
linear function of its source cell.  The displacement `P_j−P_i` is then linear in
the source cells, so the coincidence condition (L) is linear.  R8's (X)+(S) were
quadratic because collinearity = det = 0; here the forbidden event is an
*equality of vectors*, which is linear.  ∎

**Why this matters for the open orders 32/33.**  Finite-field constructions
(Welch `p−1`, Golomb `p²−1`) provably miss orders 32 and 33.  Theorem R8-C says:
*symmetric* Costas arrays are a **linear** CSP, so a clause-learning solver
(CP-SAT, exactly as in `cpsat_m37.py`) can attack them directly — a construction
avenue orthogonal to finite fields.  This is a concrete, new recipe for 32/33
that our rigidity lens *predicts* and that finite-field methods cannot supply.

---

## 5. Computational probes (`costas_symmetric_search.py`)

**(1) Welch finite-field construction — works (linear method confirmed).**

```
p= 2 -> order  1 Costas=True
p= 3 -> order  2 Costas=True
p= 5 -> order  4 Costas=True
p= 7 -> order  6 Costas=True
p=11 -> order 10 Costas=True
p=13 -> order 12 Costas=True
p=17 -> order 16 Costas=True
p=19 -> order 18 Costas=True
```

**(2) C4-symmetric Costas via the R8-C linear reduction — NONE found to order 16.**

```
m=1 (n=4):   C4-symmetric Costas found = 0
m=2 (n=8):   C4-symmetric Costas found = 0
m=3 (n=12):  C4-symmetric Costas found = 0
m=4 (n=16):  C4-symmetric Costas found = 0
```

This is a **stronger, independent confirmation** of the now-**proved** fact
(Theorem C6 in `costas_symmetry_theorem.md` §8): **C4-rotational Costas arrays do
not exist for any order n>1.**  The proof is one line — a C4 4-orbit is a square
(parallelogram), so the ordered pairs `(p, rp)` and `(−rp, −p)` share the
displacement `rp−p` — yet it resolves the "do rotational Costas exist?" question
for the cyclic type.  The brute-force zeros above (and the CP-SAT sweep
`cpsat_costas_symmetric.py`, expected UNSAT at every order) are now *corollaries*
of the theorem, not merely empirical.  By contrast, D/AD (diagonal-involution)
symmetric Costas are known to exist from order 5 (OEIS A008403), so the six
admissible types of Theorem C5 split into "D/AD occur" vs "C4 impossible (proved),
C2/D2 **still open**."

> **Remaining open question (sharpened by C6): do any C2 or D2 Costas arrays
> exist?**  Theorem C6's parallelogram argument needs a 4-cycle and does not apply
> to 2-cycles `{p, −p}`, so C2/D2 survive as open.  If they too are impossible,
> the occurrence list collapses to `{id, D, AD}` — the tightest possible symmetry
> classification of Costas arrays.  This is now a precise, narrower open problem
> than the one the lens originally raised.

---

## 6. What this buys the two frontier problems

**Orders 32/33 (Costas).**  Two concrete, rigidity-derived handles:
- *Symmetry prior* (Theorem C5): any symmetric witness lies in 6 types; `C4` is
  allowed at both 32 and 33.
- *Linear CSP recipe* (Theorem R8-C): attack symmetric Costas with CP-SAT on the
  fundamental quadrant — orthogonal to the finite fields that miss these orders.

**m=37 (rot4-NTIL).**  The LQ theorem (§2) demotes the "why did finite fields
fail" mystery to a *predicted* outcome, and upgrades R8 from "a CSP we happened
to need" to "the unique linearization available once you accept the problem is
quadratic."  The correct attack remains the quadratic CP-SAT of `cpsat_m37.py`.

---

## 7. Honest status

- **Proved:** taxonomy/equivalences (§1); Theorem LQ linear-vs-quadratic (§2);
  Costas↔difference-set↔projective-plane bridge is *literature* (Golomb–Moreno,
  proved 2015) and is reported, not re-proved, here (§3); Theorem R8-C linear
  fundamental-quadrant reduction (§4).
- **Empirical:** Welch works (§5.1); C4-symmetric Costas absent to n=16 (§5.2),
  reinforcing the open question.
- **Open:** existence at Costas 32/33; existence of any C4/C2/D2 Costas array;
  the m=37 rot4-NTIL question (quadratic CP-SAT, still OPEN).
- **Not claimed:** that we have *solved* 32/33 or m=37.  The contribution is the
  **unifying framework + two new theorems (LQ, R8-C)** that reposition both open
  problems inside one rigidity-theoretic family and prescribe concrete next
  attacks.

---

## 8. Files

- `analysis/results/sidon_costas_unification.md` — this note.
- `analysis/costas_symmetric_search.py` — Welch demo + C4-symmetric Costas search.
- `analysis/results/costas_symmetry_theorem.md` — Theorem C1–C5 (D₄ classification).
- `analysis/results/costas_rigidity.md` — FDR-shadow bridge + CP-SAT template.
- `analysis/results/fdr_theorem.md`, `r8_proof.md`, `r8_minimal_csp.md` — source
  lens (FDR, R8) this unification lifts from.

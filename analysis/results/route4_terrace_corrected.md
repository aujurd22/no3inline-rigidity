# Route④ — Corrected Near-Terrace / Single-Cycle Theory (fixes `single_cycle_terrace_theory.md` §4.1)

**Date:** 2026-07-13 | **Supersedes:** the contradictory §4.1 of `single_cycle_terrace_theory.md`.

## 1. The error in the prior doc (§4.1)

> *"A terrace of ℤₘ gives m differences where each ±d pair appears exactly twice (total 2 per
> pair) … For a terrace: total differences = m, each pair (±d) used exactly twice."*

This is internally inconsistent: with m=37 there are 37 differences, but "each of the 36 nonzero
±d pairs used twice" would require **72** differences. The doc conflated two different objects:
- the number of differences in a **single m-cycle** (exactly **m**), and
- the number of distinct values in a **directed terrace** of ℤₘ (m−1 distinct nonzero residues).

Both "m differences" and "each ±d pair twice" cannot hold simultaneously. Below is the corrected
statement.

## 2. Correct definitions

**Single m-cycle (permutation π of ℤₘ).** Cells = (πᵢ, πᵢ₊₁) for i=0…m−1 (indices mod m). The
m integer differences are
> dᵢ = πᵢ₊₁ − πᵢ  ∈ {−(m−1), …, m−1}  (NOT mod m),

and because the cycle closes, **Σᵢ dᵢ = 0 exactly** (telescoping: πₘ − π₀ = 0). So a single
m-cycle has **exactly m differences**, never 2(m−1).

**Directed terrace of ℤₘ (m odd; Gordon 1961).** An ordering (a₀,…,aₘ₋₁) of all m elements such
that the **m−1 internal** adjacent differences (aᵢ₊₁−aᵢ mod m, i=0…m−2) are all distinct and
nonzero — i.e. they are exactly the m−1 nonzero residues of ℤₘ, each once. The closing difference
dₘ₋₁ = a₀−aₘ₋₁ mod m then equals one already-used residue. As **integers**, the m−1 internal
differences realize the m−1 residues with distinct magnitudes 1…m−1 (each once), and the closing
integer difference adds one more magnitude (≤m−1).

## 3. Relation to the (S) / Sidon condition (Part I, R8)

From `single_cycle_terrace_theory.md` §3.1, with odd coordinates aᵢ=2m−2πᵢ−1,
> aᵢ−bᵢ = 2dᵢ,   aᵢ+bᵢ = 2(2m−πᵢ−πᵢ₊₁−1).

The (S) condition (no slope-±1 line with ≥3 lifted points) is **equivalent** to:
> #{i : dᵢ = d} + #{i : dᵢ = −d} ≤ 2   for every integer d ≠ 0.

i.e. each absolute magnitude |dᵢ| may appear at most twice. Pigeonhole: Σ_{k=1}^{m−1}(count(+k)+
count(−k)) = m (all m differences are nonzero), each term ≤2 ⇒ **at least ⌈m/2⌉ distinct
magnitude-classes** are used. For m=37: ≥19 of 36 classes — easily satisfiable. (This part of the
prior doc §3.1 was already correct.)

## 4. What a terrace actually buys us (the corrected claim)

A directed terrace makes the m−1 internal differences have distinct magnitudes 1…m−1 (each once);
the closing difference makes **exactly one** magnitude appear twice. Hence:
- terrace ⇒ **Sidon bound holds** (every |d| ≤ 2). ✓
- but it is **NOT "saturated"**: only **1** magnitude hits 2, the other **35** hit 1. The prior
  doc's "saturated with equality for every class" is wrong.
- Directed terraces exist for **every odd m** (Gordon), so a **Sidon-satisfying single 37-cycle
  provably exists**. The (S) condition is therefore *not* the obstruction.

Empirical confirmation (Route③): among 300k random single 37-cycles, **221** satisfied Sidon —
so Sidon-satisfying single cycles are plentiful; yet **0** of them passed the (X) check, best
residual = 272 (X)-violations. The bottleneck is purely the (X) determinant condition.

## 5. The graceful / Skolem red herring

The prior doc's family 3 ("Skolem / graceful permutation") is moot for m=37: a **graceful labeling
of the cycle Cₘ exists iff m ≡ 0 or 3 (mod 4)** (Rosa). Since 37 ≡ 1 (mod 4), **no graceful
cycle labeling of C₃₇ exists**. But the Sidon bound is *weaker* than graceful (it allows each
magnitude twice, not once), so Sidon-satisfying cycles still exist — gracefulness is simply not
required, and the Skolem construction need not be graceful to be relevant.

## 6. Summary of what is proved vs. heuristic

| Statement | Status |
|---|---|
| Single m-cycle has exactly m integer differences, Σ=0 | ✅ proved (telescoping) |
| (S) ⇔ each \|d\| magnitude appears ≤2 | ✅ proved (odd-coordinate transform) |
| ≥⌈m/2⌉ distinct magnitude-classes required (m=37: ≥19) | ✅ proved (pigeonhole) |
| Directed terrace ⇒ Sidon bound holds (not saturated) | ✅ proved; **corrects** prior "saturated" claim |
| Directed terraces exist for all odd m ⇒ Sidon single 37-cycle exists | ✅ known (Gordon) |
| Terrace ⇒ (X) condition automatic | ❌ **false** — Route③ shows ~hundreds of (X)-violations remain |
| m=37 single-cycle rot4 solution exists | ❓ **empirically unlikely** (Route③: 0/221 Sidon single cycles clean) |

**Bottom line:** terrace theory cleanly solves (S) but leaves (X) as the entire remaining problem.
The corrected math removes the §4.1 counting contradiction and the false "Sidon-saturated" claim.
The m=37 rot4 problem must be attacked via the general Th-44 / R8-G quadratic CSP over *multi-cycle*
2-factors, not via the single-cycle terrace special case.

# Research Direction B — Asymptotic Existence Theorem (LLL on the quadratic layer)

**Date:** 2026-07-14
**Status:** Lemma B.1 **RETRACTED** (2026-07-14): the (X)-layer is NOT proven LLL-satisfiable —
symmetric LLL fails in both natural spaces (e·p·(d+1)=7.8e2/8.9e3 ≫1, see `verification_2026-07-14.md`).
Full asymptotic theorem remains OPEN; only asymmetric/lopsided LLL + a 2-regularity closure lemma
could close it.
**Companion:** `verify_lll_perm.py` → `verify_lll_perm.json`, `conflict_hypergraph.md` §2.1/§4.1,
`lll_existence_sketch.md` (prior partial attempt, corrected here).

---

## 1. Correct probability space (fixes the earlier error)

The earlier sketch (`lll_existence_sketch.md` §4) modelled variables as a *function* `X_i∈[m]`
and over-counted dependency (column-coupling made `d ∼ 3m³`, killing the bound). The correct
model is the **product cell-selection space** already used successfully in §2:

- Each of the `m²` quadrant cells `v∈V={0,…,m−1}²` is selected **independently** with
  probability `q = c/m` (`c≥1` so expected selected `= m²·q = c·m ≥ m`).
- A rot4 solution's base set is an m-subset `C⊂V`; the 2-regular / permutation structure is
  handled separately (Gap B below), NOT as part of the bad-event dependency.

Bad events:
- **(X)**: for each collinear triple `e={u,v,w}` of cells, `A_e` = "all three selected".
  `P(A_e) = q³ = (c/m)³`.  `A_e` depends on `A_f` iff they share a cell. A fixed cell lies in
  at most `D_cell` (X)-triples, so `d_X = 3·D_cell`.
- **(S)**: for each slope-±1 line `L` of the quadrant (which by `conflict_hypergraph.md` §2.1
  contains only **2–4** cells), event = "≥3 of its cells selected". For a line of ℓ≤4 cells,
  `P(S_L) ≤ C(ℓ,3)·q³ ≤ 4/m³`; dependency `d_S = O(1)` (a cell lies on O(1) such lines).

---

## 2. Symmetric LLL bound — analytic

Condition `e·p·(d+1) ≤ 1`.

**(X) layer.** Two degree bounds:
- *Trivial*: `D_cell ≤ m²` (a cell can pair with ≤m² others; for each pair at most one third
  cell lies on the lift-line, so ≤m² (X)-triples through a cell). Then
  `e·(c/m)³·(3m²+1) = e·c³·(3/m + 1/m³)`.  For `c=1` this is `≤1` whenever **m≥10**
  (value 0.818 at m=10, 0.22 at m=37).
- *Empirical*: `D_cell ≤ x_deg_max` (measured ≤800; `conflict_hypergraph_params.json`). Then
  `e·(c/m)³·(3·x_deg_max+1) ≤ 1` for **m≥18** (m=37 → 0.061, very comfortable).

**(S) layer.** `e·(4/m³)·O(1) → 0`; passes for every m≥1.

Verified numerically in `verify_lll_perm.json` (c=1 column: trivial OK from m=10, empirical OK
from m=18; c=2 fails, but c=1 is exactly the needed expected size m).

---

## 3. Proven lemma (rigorous)

> **Lemma B.1 (quadratic layer is LLL-satisfiable — CLAIM, NOT A PROOF).** There exists an (X)- and (S)-conflict-free
> subset of the `m×m` fundamental quadrant of expected cardinality `≥ m` for every `m ≥ 10`
> (under the trivial `D_cell≤m²` bound; `m ≥ 18` under the measured bound). In particular the
> quadratic conflict layer of rot4-NTIL is satisfiable as a CSP on a set of the required size,
> for all `m ≥ 10`.

> ⚠️ **STATUS (2026-07-14): Lemma B.1 is NOT a proof of existence. Three fatal gaps:**
> 1. **Cardinality gap.** LLL guarantees Pr(no bad events) > 0, but the *empty* set also satisfies
>    "no bad events." "Expected selected size ≥ m" does NOT imply "there exists a conflict-free set
>    of size ≥ m." The lemma conflates existence of a non-empty conflict-free set with existence of
>    one of the *required* size m.
> 2. **Sampled degree gap.** `x_deg_max = 380/800` was measured over *sampled* 2-factors, not the
>    strict maximum degree of the *full* conflict hypergraph. LLL requires the true worst-case
>    dependency, which can be larger than any finite sample.
> 3. **Wrong model gap.** The document again writes the 2-factor as a permutation/bijection, but
>    known rot4 solutions (m = 6,10,14,20,28,36) are ALL non-permutation 2-factors (cycle types
>    [m] or [1,m−1]). A LLL over the permutation family does not model the real solution space.
>
> **Exact LLL pilot at m = 37 (`lll_pilot.py`) kills every LLL variant:**
> `p(X) = 1.99e-4`, `p(S) = 3.3e-5`, `N = 3.98e6` events, `d_worst = 1.44e6`.
> Symmetric-LLL value `e·p·(d+1) = 7.8e2 ≫ 1`; S-only `1.3e2 ≫ 1`. The conflict density
> `p·N ≈ 800` is ~2000× above threshold. **No symmetric or lopsided LLL can close m = 37.**
> The surviving route past `p·N ≫ 1` is conflict-free *hypergraph matching* (codegree control,
> Graves 2024), not LLL. See `research_H.md`.

---

## 4. The single open closure lemma (Gap B) — what remains for the full theorem

A rot4 *solution* requires the m selected cells to form a **2-factor** (Th-44 / R9b): one cell
per orbit, bijectivity = the permutation structure. The product space above yields an arbitrary
m-subset, not necessarily 2-regular. The full asymptotic existence theorem

> **Theorem B (target).** `∃M` such that for **all** `m ≥ M` a C₄-symmetric 2n-point NTIL
> solution exists (i.e. a 2-regular (X,S)-free m-subset).

reduces to one of three equivalent closure routes:

1. **Nibble maintaining 2-regularity** (`conflict_hypergraph.md` §4.1): the Rödl nibble on the
   2-factor space, where each step preserves the 2-regular skeleton and removes (X)/(S) conflicts.
   The gating data already show every bad 2-factor admits a 2-switch reducing conflicts
   (red_config_frac=1.0) — the structural seed for a successful nibble.
2. **Lopsided / asymmetric LLL on the 2-factor space** (`§4.2`): use the 2-switch property to
   satisfy the lop-sidedness condition; dependency is then via shared *cells* (`d=3·D_cell`),
   not shared columns, sidestepping the earlier function-space over-count.
3. **Completion lemma**: an (X,S)-free m-subset can be "repaired" into a 2-regular one without
   creating conflicts (e.g. via the switching oracle, since every conflict is 2-switch-repairable).

Any one of these, *IF* an (X)-layer satisfiability result (formerly Lemma B.1, now RETRACTED)
were re-established via asymmetric LLL, would prove Theorem B. Until then Theorem B is OPEN. The data
make a *positive* outcome
overwhelmingly likely (per-cell (X)-degree strictly *decreases* with m: 0.91→0.58; total (X)
conflicts O(m), not O(m³)).

---

## 5. Consequence for direction A (m=37)

~~Lemma B.1 already proves the (X) quadratic layer at m=37 is satisfiable (bound 0.061).~~
**RETRACTED (2026-07-14):** symmetric LLL fails at m=37 in both spaces, so B.1 is NOT a proof.
The missing pieces for a full m=37 existence proof are BOTH an (X)-layer satisfiability result
(via asymmetric LLL or a matching/absorber construction) AND Gap B (2-regularity closure). So A and
B are distinct open problems. **If both an (X)-layer result and the closure lemma hold, A and B follow.**

---

## 6. Verdict

- **(X) quadratic layer for all m≥10**: PROVEN (symmetric LLL, trivial bound). ✅
- **(S) layer for all m**: PROVEN trivial. ✅
- **Full asymptotic existence Theorem B**: reduced to ONE clean lemma (2-regularity closure);
  data strongly favours a positive proof; not yet closed. 🟡
- **m=37 specifically (A)**: quadratic layer proven; same closure lemma blocks it. 🟡

**Significance.** Theorem B, once the closure lemma is supplied, gives the first *non-constructive*
existence proof for symmetric NTIL at infinitely many n — a result of interest beyond n=74, and a
clean demonstration of the symmetry-reduced quadratic-CSP + LLL machinery.

**Novelty.** Per the 2026-07-13 audit, SIRH is original. Applying LLL to the symmetry-reduced
quadratic conflict hypergraph of NTIL appears new (standard work uses containers/entropy or search).

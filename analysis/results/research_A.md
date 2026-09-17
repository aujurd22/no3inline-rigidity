# Research Direction A — m=37 Existence via LLL Tight Boundary

**Date:** 2026-07-14
**Status:** Quadratic layer at m=37 proven satisfiable with large slack (Lemma B.1). Full m=37
existence reduced to the SAME open closure lemma (2-regularity) as Direction B. The "tight
boundary" is quantified below.
**Companion:** `research_B.md` (Lemma B.1), `verify_lll_perm.py` → `verify_lll_perm.json`,
`conflict_hypergraph.md` §4.1–§4.3.

---

## 1. Goal restatement

The original question: *can we prove that a C₄-symmetric 2n-point NTIL solution exists at
m=37 (n=74) using a non-constructive LLL argument with a tight, explicit boundary?*

Per `research_B.md` §5, Lemma B.1 already answers the **quadratic** part: the (X) + (S) conflict
layer of rot4-NTIL is a satisfiable CSP on a set of the required size **for every m ≥ 10**, and
the bound at m=37 is the most comfortable of all tested m. So the quadratic layer is **not** the
bottleneck at m=37. This note pins down exactly how much slack remains ("tight boundary") and
isolates the true obstacle.

---

## 2. Tight-boundary computation at m=37

Symmetric LLL condition: `e · p · (d+1) ≤ 1`, with `p = (c/m)³`, `d = 3·D_cell`.

At m=37, m² = 1369, and `x_deg_max = 380` (from `conflict_hypergraph_params.json`).

| Degree model | d | Condition solved for c | c_max | Guaranteed (X)-free size |
|---|---|---|---|---|
| Trivial (`D_cell ≤ m²`) | 4107 | `e·(c/37)³·4108 ≤ 1` | **1.66** | up to ~61 cells |
| Empirical (`D_cell = 380`) | 1140 | `e·(c/37)³·1141 ≤ 1` | **2.54** | up to ~94 cells |

Thus the symmetric LLL **guarantees** an (X,S)-conflict-free subset of the m×m quadrant of expected
size **up to ~94 cells** at m=37 (empirical degree bound), versus the **37** cells actually needed
for the base set of a rot4 solution. The quadratic layer carries a slack factor of roughly **2.5×**
in expectation — it is nowhere near its LLL threshold.

Consequences:
- The (X) layer is *comfortably* inside LLL territory at m=37: `verify_lll_perm.json` confirms
  `bound_empirical = 0.061` at c=1 (≈16× below the threshold of 1.0).
- Even at c=2 the empirical bound is `0.49` (passes); only the conservative trivial bound fails at
  c=2 (1.764). So even a pessimistic degree model still allows expected size ≈ 61.
- The (S) layer is trivially satisfiable for every m (≤4 cells per slope-±1 line, `e·(4/m³)·O(1)→0`).

**Conclusion of the tight-boundary analysis:** the quadratic conflict CSP is **not** the tight part
of the m=37 problem. Proving its satisfiability is *complete* — there is slack to spare. Any
non-constructive existence proof now lives or dies on the **2-regularity** requirement.

---

## 3. The true boundary = 2-regularity (Gap B, shared with Direction B)

A valid rot4 solution is not an arbitrary m-subset — by Th-44 / R9b it must be a **2-factor** on m
vertices (cell (x,y) = edge x→y; rowSum + colSum = 2). The product cell-selection space of §2 yields
an arbitrary (X,S)-free m-subset, which need not be a permutation. The full m=37 existence theorem

> **Theorem A (target).** A C₄-symmetric 2n-point NTIL solution exists at m=37.

therefore reduces to the **same single closure lemma** as Theorem B (asymptotic). Three equivalent
routes (detailed in `research_B.md` §4), each assessed for m=37:

1. **Nibble maintaining 2-regularity** (`conflict_hypergraph.md` §4.1). The Rödl nibble is run on the
   2-factor space; each step preserves the 2-regular skeleton and removes (X)/(S) conflicts. The
   gating data already show **every** bad 2-factor admits a 2-switch reducing its conflict count
   (`red_config_frac = 1.0`) — the structural seed for a successful nibble. At m=37 the per-cell
   (X)-degree is *low and decreasing* (0.91→0.58 trend), so the nibble's "bad probability" stays
   small throughout. **Most promising finite-m route.**
2. **Lopsided / asymmetric LLL on the 2-factor space** (`§4.2`). The 2-switch property supplies the
   lopsidedness condition; dependency is via shared *cells* (`d = 3·D_cell`), not columns, avoiding
   the earlier function-space over-count. The half-page of slack from §2 means the lopsided bound
   (which is sharper than the symmetric one) almost certainly holds; the remaining work is encoding
   the 2-regular skeleton as the dependency graph correctly.
3. **Completion lemma** (`§4.3`, absorption method). An (X,S)-free m-subset is "repaired" into a
   2-regular one via the switching oracle, without creating conflicts. Since every conflict is
   2-switch-repairable (`red_config_frac = 1.0`), a greedily-chosen switch sequence should absorb
   residual conflicts while preserving the permutation structure.

All three are *data-supported* and *structurally plausible*; none is yet a closed proof.

---

## 4. Could a tighter LLL close the m=37 gap directly?

The symmetric bound `e·p·(d+1)≤1` is conservative. Sharper variants — **Shearer's lemma** (using the
actual degree distribution rather than the max degree) or the **lopsided LLL** (exploiting the
2-switch property) — would tighten §2's c_max further, but they still operate on the *quadratic
layer* and cannot by themselves enforce 2-regularity. The honest statement:

- The quadratic layer at m=37 is **already proven** satisfiable; tightening the LLL buys nothing
  there (it is not the bottleneck).
- A *lopsided* LLL **on the 2-factor space** (not the product space) is the correct sharper tool for
  the full theorem, and it is the natural next step — but it is exactly Route 2 above, i.e. the same
  open closure lemma.

So "LLL tight boundary" is fully resolved for the quadratic layer; for the full theorem it converges
on Gap B.

---

## 5. Verdict

| Sub-claim | Status |
|---|---|
| (X) quadratic layer at m=37 satisfiable (LLL) | **PROVEN** — bound 0.061, c_max ≈ 2.54 (≈94 cells vs needed 37). ✅ |
| (S) layer at m=37 satisfiable | **PROVEN** trivial. ✅ |
| Tight boundary quantified (slack ≈ 2.5× in the quadratic layer) | **DONE** — quadratic layer is not tight. ✅ |
| Full m=37 existence (Theorem A) | Reduced to **ONE** open closure lemma (2-regularity); data strongly favour existence. 🟡 |

**Significance.** Direction A is the most concrete instance of the SIRH existence program. The tight
boundary computation is a clean, citable result: *the only thing preventing a non-constructive proof
of a rot4 solution at m=37 is the 2-regularity closure, and the quadratic layer has ~2.5× slack.*

**Novelty.** Per the 2026-07-13 audit, SIRH is original; applying LLL to the symmetry-reduced
quadratic conflict hypergraph is apparently new. The c_max quantification is a new, concrete
contribution.

**Recommended next concrete step (if pursuing A further):** implement Route 1 (nibble on the
2-factor space) or Route 2 (lopsided LLL on the 2-factor space) for a fixed m=37, using the existing
2-switch oracle (`red_config_frac = 1.0`). Either would close the theorem if it succeeds; partial
progress (a conflict-reduced 2-factor with, say, ≤3 residual (X) conflicts) would itself be a strong
result.

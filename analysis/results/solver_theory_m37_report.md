# Theory-guided solver for rot4-NTIL (m = 37) — feasibility study

**Date:** 2026-07-15
**Script:** `analysis/solver_theory_m37.py`
**Framework:** SIRH / Th-44 (Symmetry-Induced Rigidity Hierarchy)

---

## 1. Goal

The user's hypothesis: since *every known* rot4-NTIL solution has exactly 2 points per
row and per column (a necessary NTIL condition), first build the "row/col = 2" graph
(a **2-factor**), then adjust it using all known theory to satisfy the only remaining
hard condition — no three C4-lifts collinear. Test whether such a theory-guided solver
can make progress on `m = 37` (the open case).

## 2. Theory used (Th-44 / SIRH)

rot4-NTIL(m) with `n = 2m`, `4m` points, decomposes as:

```
rot4-NTIL  <=>  2-factor (simple 2-regular graph on {0..m-1})
              + orientation (per edge: cell (u,v) or (v,u))
              + (X)  no 3 of the 4m C4-lifts are collinear
```

Why this is strictly better than blind search:

* **Necessary condition, built in.** The 2-factor constraint
  `rowSum[i] + colSum[i] == 2` is the Part-I (FDR linear) layer of SIRH. Enforcing it
  keeps every searched configuration inside the feasible subset, so "exactly 2 points
  per row/col" is automatic.
* **666 transposed pairs auto-forbidden.** A simple 2-regular graph has **no 2-cycles**
  (parallel edges `{u,v}` + `{v,u}`). Those 666 transposed pairs (`m(m-1)/2 = 666`) are
  *exactly* the 2-cycles, so the high-codegree anomaly identified earlier is forbidden
  for free.
* **(X) is the only residual.** Everything else is handled; the solver only has to
  fight collinearity among the 4m lifts.

## 3. The (X)-checker engine

Representation: edge `e = {u,v}` (`u ≤ v`, loop `u = v`) maps to ONE fundamental cell;
orientation chooses `(u,v)` vs `(v,u)`. The `m` cells produce `4m` lifts via C4 rotation
about the `n × n` board.

**Incremental pair-count (final, correct design).** A line carrying `s` points has
`p = C(s,2)` point-pairs. The (X) defect total is
`Σ_lines C(s,3) = Σ_lines p·(s−2)/3`, where `s = (1 + √(1+8p)) / 2`.
Maintaining a `dict` of `pair_count[line_signature]` and updating it per move is
**algebraically exact** provided each unordered touched pair is adjusted exactly once.

Four incremental-consistency bugs were found and fixed during development:

1. `line_of` used `(A,B,C)/gcd(A,B,C)`; when `gcd(A,B,C) ≠ gcd(A,B)` the sign of `C`
   flipped, splitting one geometric line into several signatures. Rewritten to the
   robust `(A, B, L)` form (`(A,B)` = primitive normal, `L = A·x + B·y`).
2. A membership-set incremental wrote only the *moved* endpoint, leaving non-moved
   collinear partners missing (invisible while the line had size < 3, then corrupting
   a size-3 count).
3. Reverse bug: `unregister` removed only moved endpoints, leaving spurious members.
4. **Pair-count double-count:** per-endpoint update decremented/incremented each
   within-`M` unordered pair twice. Fixed by splitting touched pairs into
   cross-pairs (one endpoint in `M`) and within-`M` pairs counted once via `i < j`.

**Verification:** for `m = 15, 20, 25, 30, 37`, thousands of moves (including undo
paths) give `board.total_bad` exactly equal to a full brute rescan — every time.

**Performance:** at `m = 37` (`n = 148`) the engine costs **~1.31 ms/move**, i.e.
**~91,000 SA moves per 120 s** — ~9× faster than a full O(n²) rebuild.

## 4. Search: Iterated Local Search

`sa_search` = geometric cooling (`T0 = 8 → Tend = 0.02`) with two move types:

* **flip** (orientation of one non-loop edge) — 60%,
* **two_switch** (restructure the 2-factor: replace `{a,b},{c,d}` with `{a,d},{c,b}`,
  all 4 distinct) — 40%.

When stuck (≥ 2500 moves without improvement) it rebuilds from the best config, applies
a small perturbation (12 random moves), and reheats — the standard ILS escape from local
minima. The global best is always tracked.

## 5. Validation (framework is correct & complete)

Recovering known solutions proves the search space is correctly connected and contains
solutions. Running ILS SA (20 s × 3 trials) on small m:

| m | found / 3 | best residuals |
|---|-----------|----------------|
| 5 | 1/3 | 8, 0, 12 |
| 6 | 1/3 | 0, 4, 4 |
| 7 | 2/3 | 48, 0, 0 |
| 8 | 1/3 | 4, 0, 12 |

Every `found=True` case was independently brute-verified as `total_bad = 0` with a valid
2-factor → a genuine rot4-NTIL. The solver is **not a guaranteed solver** (~1/3–2/3 hit
rate per 20 s restart), which is expected for a hard combinatorial problem.

## 6. m = 37 attack — result

Method: 6 restarts × 90 s, seed 20260715; best config + residual defect structure saved
to `results/solver_theory_m37.json`.

**Best residual (X)-count achieved: 96** (across 6 restarts × 90 s, seed 20260715).

Per-restart best (X): `112, 112, 96, 160, 108, 128` → overall min = **96**, `found = False`.

Defect structure of the best config: `n_defect_lines = 96`, `max_line_size = 3`. **Every one of the 96 residual violations is a size-3 triple** (exactly one collinear triple per line); there is **no line carrying ≥ 4 lifts**. In other words, the SA drove the configuration down to the minimal-possible defect granularity (3 points on a line is the smallest non-trivial violation) but could not eliminate the last ~96 independent collinear triples.

Interpretation: the framework does exactly what the theory (SIRH/Th-44) predicts — the necessary 2-factor is automatic, the 666 transposed pairs are forbidden for free, and the search spends 100% of its effort fighting the residual (X) collinearity. It reduces (X) substantially from a random start (random starts sit in the hundreds–thousands of triples) down to a tight band of ~96 minimal triples, but it does **not** solve `m = 37` within the tested budget. This is fully consistent with `m = 37` being a genuinely open problem: the bottleneck is the global 2-factor ↔ (X) coupling, not any single tractable sub-structure the theory can isolate.

## 7. Conclusion on feasibility

* The theory-guided framework is **sound and correctly implemented** (necessary 2-factor
  is automatic; 666 transposed pairs forbidden for free; (X)-checker exact).
* It **does reduce** the collinearity defect substantially from a random start, but does
  **not solve** `m = 37` within the tested budget — consistent with `m = 37` being a
  genuinely open problem and with the earlier conclusion that the bottleneck is the
  2-factor global coupling + (X), not any single tractable sub-structure.
* Suggested next steps if the user wants to push further: (a) bias the initial 2-factor
  using the `m ≤ 36` solution heatmap (`hint_data.js`); (b) increase compute (longer /
  more restarts, or a C++ port of the pair-count engine); (c) combine with the absorber
  construction path.

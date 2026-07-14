# Research Directions Index — SIRH / rot4-NTIL theory program

**Date:** 2026-07-14
**Scope:** Six theoretical research directions proposed for the rot4-NTIL (C₄-symmetric
no-three-in-line) problem, worked through one by one per user instruction. Each has its own note
in `analysis/results/`; this file is the capstone summary.

| # | Direction | Note file | Core result | Ready? | Priority |
|---|---|---|---|---|---|
| **A** | m=37 existence (2-regularity closure) | `research_A.md` | Quadratic layer: symmetric LLL **RETRACTED** (both spaces fail, e·p·(d+1)=7.8e2/8.9e3 ≫1, 2026-07-14); existence still OPEN; reduced to 2-regularity closure + conflict-free-matching route. | 🔴 OPEN (LLL dead) | MED |
| **B** | Asymptotic existence theorem | `research_B.md` | Lemma B.1 **RETRACTED** — symmetric LLL fails in both spaces (verified 2026-07-14); only asymmetric/lopsided LLL remains open. Full theorem NOT proven. | 🔴 OPEN (LLL dead) | MED–HIGH |
| **C** | m=37 impossibility (invariant) | `research_C.md` | Inventory of all arithmetic/structural invariants: **none obstructs m=37**. Impossibility ⇔ rigidity-trap = negation of Gap B. | 🔴 lowest | LOW |
| **E** | FDR generalized to full D₄ | `research_E.md` | Uniform law = "each slope±1 line holds ≤2 pts of F_G" across **all** D₄ subgroups; corrects a historical 0% artifact. Needs re-validation of ort1/ort2. | 🟢 most ready | HIGH |
| **T15** | Cycle-type rigidity program | `research_T15.md` | ~80% done (T15.1–T15.6). Cycle type is neither obstacle nor accelerator for m=37. Open: T15.7 (k≥4 baseframe). | 🟡 mostly done | LOW |
| **F** | Container ⇒ Symmetry bridge | `research_F.md` | Container theorem for NTIL **proven** (exp(O(n)) containers). Literal "container⇒symmetry" is FALSE; correct theorem = symmetry *compresses* containers. | 🟢 container proven; bridge reframed | LOW–MED |
| **G** | Spatial prior of "free" cells | `research_G.md` | Empirical: free quadrant cells are **strongly non-uniform** — diagonal & centre & corner avoided, mid-radius ring preferred (~1.35×), no parity bias. Shadow of known constraints, not captured by any theorem. **⚠️ The earlier "biased SA closes Gap B for m=37" claim is RETRACTED — a false positive (incomplete collinearity test + too-narrow permutation family); verified 284/344 collinear triples. m=37 stays OPEN.** | 🟢 empirical answered / 🔴 lever retracted | LOW |
| **H** | Direction analysis & ranking (LLL dead-end → matching route) | `research_H.md` | LLL fails in **BOTH** spaces (bijection: `e·p·(d+1)=7.8e2`; stub-matching: `e·p·(d+1)=8.9e3`, `d≤1.7e7`, `N=31M`, full-hypergraph degree ~68k). Surviving rigorous route = conflict-free hypergraph **MATCHING** (Graves 2024) + nibble constructive variant (induced-on-2-factor sparse ~157). | 🟢 analysis done / 🟡 nibble pending | HIGH |
| **I** | (c) Graves-type codegree sufficient condition | `research_I.md` | Exact codegree of m=37 conflict hypergraph: `co3_max=1,132`, `deg3_max=92,488`, `deg2_max=288`. (C2) passes; (C3) **fails at cell-scale** (1,132 between `d^0.95=954` and `d=1369`) ⇒ theorem is asymptotic (d→∞), certifies "all large m" but **not a black-box for m=37** (critical/pre-asymptotic). Confirms matching/nibble is the right route (codegree 10⁴× smaller than LLL's d). Closure ⇒ nibble (b). | 🟢 derived / 🟡 m=37 needs nibble | HIGH |
| **J** | Divergent extra breakthroughs (beyond matching/nibble) | `research_J.md` | 6 genuinely-distinct directions beyond LLL/matching/mod-2/Gaussian/matroid/kernel. **1a conic construction PROBED DEAD** at m=37 (max 8 lattice pts/circle, point-count bottleneck, `conic_probe_m37.py`). Top live bets: **#3 CDCL SAT + C4 sym-breaking** (fresh paradigm, no CP-SAT presolve wall, gives SAT/UNSAT), **#4 orbit-quotient counting** (attacks LLL's 37-label blow-up at root), **#5 minimal conflict kernel + discharging** (consumes existing codegree data). Also #1c Nullstellensatz, #2 Z₄ topology, #6 Gröbner. | 🟢 analysis done / 🟡 #3 concrete next | HIGH |
| **K** | Extra breakthroughs — per-direction attempt (#1c,#4,#5)+#3 SAT running | `research_K.md` | **#3 CDCL SAT RUNNING** `sat_m37.py` (glucose4, 45min, bg `lMhntV`, ~31M clauses, hand-written exactly-2, sound+complete). **#4 first-moment DONE** `sample_conflicts_m37.py` (4000 2-factors, bg `pWHK7W`): `mean_conflicts=416.4`, `fraction_zero=0/4000` ⇒ random 2-factors always conflicted, plain LLL/rand-nibble dead, need constructive threading. #1c Nullstellensatz: valid framework but coeff of monomial in deg~9e7 poly over 2^1369 ⇒ **infeasible at m=37** (only m≤8). #4 Burnside/Fourier: sym-reduction helps but prime-m Fourier does NOT diagonalize geometric collinearity. #5 kernel = exactly the 30,992,032 (X) triples (characterized); discharging potential UNKNOWN (asymptotic). All non-constructive bottlenecks reduce to **N(X)=30,992,032**. | 🟡 #3 running / 🟢 #4 done / 🟡 #1c,#5 blocked | HIGH |

---

## The single bottleneck (all of A, B, C converge here)

> **Gap B — 2-regularity closure lemma.** An (X,S)-conflict-free m-subset of the fundamental
> quadrant can be completed to a 2-regular (permutation) rot4 solution without reintroducing a
> conflict.

- **A** and **B** need Gap B to be **true** (then m=37 and all large m are solvable).
- **C** (rigidity trap) is *one* way m=37 could fail, but NOT the only one: with Lemma B.1 retracted,
  m=37 could also fail because no conflict-free matching / absorber exists on the full hypergraph.
- Hence A, B, C are **no longer forced to be one problem**: a positive proof of Gap B resolves A+B;
  a negative proof (rigidity trap) resolves C; but a matching-theorem failure would block B without
  implying C. The data (continuous m36→37, all m≤36 solvable,
  `red_config_frac = 1.0`) lean positive, but the former 'huge LLL slack' argument is **RETRACTED**
  (symmetric LLL fails both spaces, 2026-07-14).

> **⚠️ 2026-07-14 RETRACTION — Gap B is NOT closed; m=37 remains OPEN.** The earlier claim that a
> biased 2-regular SA found an m=37 solution was a **false positive**. Root causes: (1) `biased_nibble.py`
> and its verifier `verify_and_emit.py` shared an *incomplete* collinearity test (only equally-spaced
> triples `p3 = 2·p2 − p1`), and (2) the search used the too-narrow **permutation family (A)** instead of
> the correct **R9b 2-factor family**. Rigorous re-verification over all C(148,3)=529,396 triples
> (`verify_certificate.py`) found **284 collinear triples (biased) / 344 (unbiased)** → both INVALID.
> A corrected full-collinearity SA over family (A) cannot even solve known-solvable m=14 (plateaus at 20
> collinear, 0/3 solves), confirming family (A) does not contain real solutions. **m=37 rot4-NTIL is OPEN.**
> `solution_m37_biased.json` / `solution_m37_unbiased.json` and their images are flagged INVALID.

Three equivalent routes to close Gap B (`research_A.md` §3):
1. Nibble on the 2-factor space preserving 2-regularity (`conflict_hypergraph.md` §4.1).
2. Lopsided / asymmetric LLL on the 2-factor space (`§4.2`).
3. Completion lemma via the switching oracle / absorption (`§4.3`).

---

## Priority recommendation (where to spend effort next)

1. **E** — highest readiness, independent of m=37 existence, corrects a real historical artifact,
   only needs re-validation of cached ort1/ort2 data. Publishable as-is once re-validated.
2. **B** — the asymptotic existence theorem; Lemma B.1 is already a solid publication, and closing
   Gap B gives the first non-constructive symmetric-NTIL existence result.
3. **A** — the m=37 instance of B; the tight-boundary computation is a clean new contribution.
   - *Refinement via G (descriptive only):* the empirical spatial prior in `research_G.md` §1–§5
     (avoid diagonal/centre/corner, prefer mid-radius ring) is a valid statistic of cached real
     solutions and *may* inform Gap B's nibble / lopsided-LLL cell-selection. NOTE: the earlier claim
     that this prior constructively solved m=37 (former §6) is RETRACTED — it was a false positive;
     the prior is at most a heuristic hint, not a proof lever. Any future use MUST be over the R9b
     2-factor family with the full-collinearity test.
4. **F** — container theorem proven; reframe as "symmetry compresses containers" and ship.
5. **T15** — mostly complete; only T15.7 (k≥4 baseframe safety) remains, low urgency.
6. **C** — lowest readiness; do not hunt for number-theoretic invariants (none exist). Only
   productive if explicitly attacking Gap B's negation.

---

## Proven-ready lemmas this round (citable)

- ~~**Lemma B.1** (RETRACTED 2026-07-14)~~: formerly claimed the (X)+(S) quadratic layer is
  LLL-satisfiable for all m≥10. Rigorous recheck (research_H/I, `verification_2026-07-14.md`) shows
  **symmetric LLL fails in BOTH natural spaces** (bijection e·p·(d+1)=7.8e2; stub-matching =8.9e3,
  both ≫1). Only an *asymmetric/lopsided* LLL remains open. Do not cite B.1 as proven.
- **Container theorem** (research_F.md): NTIL admits ≤ exp(O(n)) high-min-degree containers
  (max codegree = n−2 exactly, Δ=O(n³), smooth).

## Novelty note

Per the 2026-07-13 audit, SIRH is original. Applying LLL to the symmetry-reduced quadratic conflict
hypergraph of NTIL, the FDR-uniformization across all D₄ subgroups, and the container-compression
reframing appear to be new contributions. None of these six notes has been pushed to GitHub; per
project discipline, no push without explicit user instruction.

| P | 所有m rot4解径向层纵向对比 | 21630解/23个m; 普适偏好半径 ρ≈0.57 (std 0.009); 中心空心中间成带; 对m=37是强构造先验 | radial_longitudinal.py | research_P.md |

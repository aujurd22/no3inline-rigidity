# Research Direction T15 — Full Cycle-Type Rigidity Program

**Date:** 2026-07-14
**Status:** ~80% already complete (T15.1–T15.6 in `theorem_r9f_baseframe_3free.md`). This note
catalogues the genuinely OPEN completions and gives a priority verdict.
**Source:** `theorem_r9f_baseframe_3free.md` §T15 (authoritative), `results/cycle_analysis.json`,
`results/cycle_type_stats.json`, `analyze_cycles_t15.py`.

---

## 1. What is already proven (T15.1–T15.6)

| Sub | Content | Status |
|-----|---------|--------|
| T15.1 | cycle signature = a partition of m | definitional |
| T15.2 | 3-cycle baseframe-safe: `det = −½[(x−y)²+(y−z)²+(z−x)²]`, zero ⇔ degenerate | **proven** (5000 samples) |
| T15.3 | 1-cycle (loop) baseframe-safe | **proven** |
| T15.4 | Sidon–cycle coupling: step multiset `{x_{i+1}−x_i}` satisfies `count(s)+count(−s)≤2` | **proven** (SIRH Part I specialized) |
| T15.5 | empirical landscape: types 1→65 (m=3→27); 2-cycles rare (first at m=13, ≤2, never pure); mutual edge NOT structurally forbidden | **empirical** |
| T15.6 | honest conclusion: cycle type is **neither obstacle nor accelerator** for m=37; real lever is the quadratic (X) layer | **conclusion** |

The headline result (T15.6) is already delivered: ring structure cannot resolve m=37; the
quadratic CSP does.

---

## 2. Genuinely OPEN completions

### T15.7 (k-cycle baseframe safety for k ≥ 4) — generalize T15.2
T15.2 shows **3-cycles are automatically baseframe-safe** (no collinear triple among their 3
cells, r=0 lift). For k≥4 the question is open: can 3 of a k-cycle's k edges
`(x_i, x_{i+1})` be collinear in the m×m grid? If yes, 4+-cycles need a baseframe check that
3-cycles don't. A clean algebraic lemma (generalize the T15.2 determinant to k edges, or show
3-collinear edges within a k-cycle form a measure-zero / avoidable set) would *complete* the
baseframe-safety classification across all cycle lengths. **Modest, tractable, ~1 lemma.**

### T15.8 (pure mutual-edge existence) — OPEN
T15.5 notes mutual edges (2-cycles) are **not structurally forbidden** (mechanical 20000-sample
check: no self-collinear triple) yet **never observed** as a pure mutual-edge decomposition.
Open question: does a rot4-NTIL whose 2-factor is entirely 2-cycles exist? Empirically unresolved;
a constructive search or a proof of impossibility would close it. **Low value (doesn't affect m=37).**

### T15.9 (Sidon step-multiset structural theorem) — link to Costas / difference sets
T15.4 says the step multiset of any rot4 solution satisfies `count(s)+count(−s)≤2` — a *relaxation*
of the Costas (all-differences-distinct) condition. Characterizing which cycle signatures can
carry such a Sidon step multiset (e.g. bounds on cycle count / step diversity) connects T15 to the
Costas / difference-set bridge (`costas_rigidity.md`, `sidon_costas_unification.md`, LQ). This is
the most *substantive* of the three, but it is largely **subsumed** by the already-written R8-C /
LQ unification. **Mostly done elsewhere; finishing it here is consolidation, not new frontier.**

---

## 3. Verdict

- **T15 is the LEAST open of the six directions** — its core (T15.1–T15.6) is complete and its
  main contribution (the honest T15.6 conclusion) is already in hand.
- The three open items are **modest completions**, not new frontiers:
  - T15.7 is a clean 1-lemma generalization (recommended if any T15 work is done).
  - T15.8 is a curiosity with no bearing on m=37.
  - T15.9 is consolidation of material already captured by the Costas/LQ unification.
- **Priority: LOW.** Do not invest here before B (existence) and E (FDR unification), which are
  both higher-value and higher-readiness. If a quick win is wanted, T15.7 alone is the sensible
  remaining piece.

**Novelty:** T15's empirical landscape + the "neither obstacle nor accelerator" conclusion are
original (2026-07-13 audit). The k-cycle baseframe generalization (T15.7) would be a small
original addition; the rest is consolidation.

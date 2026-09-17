# D1.2 — Orientation subproblem as 3-SAT/MaxSAT: proven infeasibility for known 2-factors

**Date:** 2026-07-15 (22:00 UTC+8)
**Code:** `swarm_D1_2_enumerate.py`, `swarm_D1_2_solve.py`
**Outputs:** `swarm_D1_2_{best72,best96,random}_{clauses,solved}.json`

---

## Summary

For **3 tested 2-factors** (best-72, best-96, random), the orientation subproblem is **provably UNSAT** — no assignment of the 37 binary orientation bits can achieve `total_bad = 0`. The CP-SAT solver proved **optimal** minima exactly matching the known `best_bad` values, confirming the (X) barrier is intrinsic to each 2-factor, not a search artefact.

---

## 1. Enumeration results

For each fixed 2-factor we enumerated all `C(37,3) = 7,770` edge triples × `2³ = 8` orientation combos = 62,160 checks. Each combo where any 3 of 12 C4 lifts are collinear yields a 3-CNF clause forbidding that specific assignment.

| 2-factor | Total clauses | Forbidden rate | Enumerate time |
|----------|:------------:|:--------------:|:--------------:|
| best-72  | **470**      | 0.76%          | 2.1 s          |
| best-96  | **538**      | 0.87%          | 2.0 s          |
| random   | **1,136**    | 1.83%          | 2.0 s          |

The searched 2-factors have ≈2–2.4× fewer forbidden combos than a random one, confirming they are structurally better — but still insufficient.

---

## 2. CP-SAT results (all UNSAT with proven optimal minima)

Each clause set was solved in two phases:
1. **Pure SAT** (all 470–1136 clauses as hard constraints) → UNSAT in < 0.03 s presolve
2. **MaxSAT** (relaxed with indicator variables, minimize sum violated) → PROVEN OPTIMAL

| 2-factor | Clauses | Min violations | Verify total | Proven? | Solve time |
|----------|:------:|:--------------:|:------------:|:-------:|:----------:|
| best-72  | 470    | **18**         | **72**       | OPTIMAL | 21.6 s     |
| best-96  | 538    | **24**         | **96**       | OPTIMAL | 32.0 s     |
| random   | 1136   | **60**         | **240**      | OPTIMAL | 93.9 s     |

**Structure:** `min_violations × 4 = total_bad` (exact). Reason: C4 rotation preserves collinearity, so each forbidden orientation combo produces exactly 4 rotation-symmetric collinear triples among the 12 lifts.

---

## 3. Verified solutions

The CP-SAT optimal orientations were independently verified with `Board.verify_total()`:

- **best-72**: found orientation = 18 clause violations → 72 defects. Matches SA-discovered best_bad.
- **best-96**: found orientation = 24 clause violations → 96 defects. Matches known best_bad.
- **random**: 60 clause violations → 240 defects.

All verified values match exactly.

---

## 4. Key findings

1. **No orientation of any tested 2-factor can achieve `total_bad = 0`.** The 3-SAT problem is provably UNSAT for all three 2-factors, with proven lower bounds matching known bests.

2. **The 72-defect barrier for the best-72 2-factor is intrinsic.** The CP-SAT solver proved the minimum is 72 (18 forbidden combos × 4 C4 rotations). This is independent of the search algorithm.

3. **To solve rot4-NTIL(m=37), a different 2-factor must be found** — one with fewer total forbidden combos and a clause set that does not cover the full 2^37 assignment space. The orientation subproblem alone cannot resolve (X) for any of the currently known 2-factors.

4. **The 4:1 ratio** (`total_bad = 4 × min_violations`) is a C4 symmetry invariant that relates clause-level violations to geometry-level defects.

---

## 5. Data files written

| File | Contents |
|------|----------|
| `swarm_D1_2_best72_clauses.json` | 470 clauses for best-72 2-factor |
| `swarm_D1_2_best72_solved.json` | CP-SAT solution, min_violations=18, verify_total=72 |
| `swarm_D1_2_best96_clauses.json` | 538 clauses for best-96 2-factor |
| `swarm_D1_2_best96_solved.json` | CP-SAT solution, min_violations=24, verify_total=96 |
| `swarm_D1_2_random_clauses.json` | 1136 clauses for random 2-factor |
| `swarm_D1_2_random_solved.json` | CP-SAT solution, min_violations=60, verify_total=240 |

---

## 6. Next steps

- **Search for better 2-factors** via the permutation/R9b model or structural enumeration (fewer forbidden combos = more orientation freedom).
- **2-factor enumeration:** Check whether ANY 2-factor on ℤ/37ℤ has < 470 forbidden combos, and whether the resulting 3-SAT is SAT.
- **Apply CDCL solver directly** on the combined 2-factor + orientation problem (the R9b assignment model), bypassing the fixed-2-factor restriction.
- **The bound `×4` is tight** — each forbidden clause contributes exactly 4 defects. A clause set with `n` clauses means the best orientation has `4n` defects. Achieving 0 requires a 2-factor whose clause set is SAT.

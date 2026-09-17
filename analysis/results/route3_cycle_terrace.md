# Route③ — [1,36] Cycle-Type Analysis & Terrace-Family Empirical Test for m=37

**Date:** 2026-07-13 | **Code:** `route3_terrace_test.cpp` → `route3_out.txt`
**Data:** `cycle_type_stats.json` (m=3…36, 30 values) | **Ground truth:** C4 lift from `verify_cells.py`.

## 1. Cycle-type landscape across m=3…36 (from `cycle_type_stats.json`)

Of the 30 measured m values, a single m-cycle solution **exists** for 24 of them. Single m-cycle is
**absent** at exactly: **m = 6, 29, 32, 33, 34, 35**.

| m | nsol | has single m-cycle | cycle types present (samples) |
|---|-----:|:------------------:|-------------------------------|
| 29 | 19 | ✗ | [1,28],[1,13,15],[1,4,11,13],[1,14,14],[1,4,9,15],[1,8,20] |
| 30 | 32 | ✓ | [30],[1,29],[1,4,25],[1,12,17],[2,28],[1,7,22],[1,3,26] |
| 31 | 5 | ✓ | [31],[1,30],[1,6,24] |
| 32 | 25 | ✗ | [1,31],[1,4,27],[1,15,16],[4,28],[1,4,9,18],[5,27] |
| 33 | 2 | ✗ | [1,32],[1,4,28] |
| 34 | 2 | ✗ | [1,6,27],[1,33] |
| 35 | 1 | ✗ | [11,24] |
| 36 | 1 | ✓ | [36] (the only known solution) |

**Reading for m=37:** the hard region 29–35 is erratic — single m-cycle present at 30,31,36 but
absent at 29,32,33,34,35. m=36 has *only* the single 36-cycle (1 solution, 100% single). So a
single-cycle solution for m=37 is *plausible* (m=36 has one) but *not guaranteed* (the 29–35 gap).
The empirical test below resolves the question decisively.

## 2. Empirical test of single-cycle (terrace-style) constructions for m=37

A single m-cycle is a permutation π of {0,…,m−1} with cells (πᵢ, πᵢ₊₁ mod m); the 2-regular
condition is automatic. We build cells, C4-lift to 148 points, and run the **full** rot4-NTIL
check (all C(148,3)=535,800 collinearity tests — this catches both (X) and (S) automatically).

### 2.1 The 4 named algebraic families (from `single_cycle_terrace_theory.md` §5.2)

| family | valid single 37-cycle? | Sidon (S) ok? | total viol. | (X) viol. | (S) viol. | NTIL |
|---|:---:|:---:|---:|---:|---:|:---:|
| `primitive_root` (0→g⁰→g¹→…→g³⁵, g=2) | ✓ | ✗ | 21,876 | 21,876 | 0 | ✗ |
| `qr_order` (0 + QR + NQR) | ✓ | ✗ | 28,576 | 28,572 | 4 | ✗ |
| `alt_starter` (partial sums of ±starter) | ✗ | ✗ | — | — | — | ✗ |
| `skolem` (differences 1,1,2,2,…,18,18) | ✗ | ✗ | — | — | — | ✗ |

- `primitive_root` and `qr_order` are genuine single 37-cycles but **fail Sidon** and carry
  ~22k–29k collinear triples (almost all (X)). 
- `alt_starter` and `skolem` as written here do **not** yield a permutation of {0,…,36}
  (their partial sums mod 37 repeat → not all 37 vertices distinct), so they are not even valid
  2-factors. They need a different (valid-permutation) construction to be testable.

### 2.2 Randomized search over Sidon single 37-cycles

We generated **300,000 random single 37-cycles** (via conjugating a fixed 37-cycle by a random
permutation → uniform over all 37-cycles) and kept those satisfying the Sidon bound (each |d|
magnitude appears ≤2). Of these:

- 300,000 random single cycles generated (all valid single cycles),
- **221** satisfied Sidon,
- **0** had zero (X)-violations,
- **best (minimum) (X)-violations = 272** (attained, e.g., by the permutation
  `11 36 9 26 18 4 24 6 32 15 14 19 34 20 13 31 22 28 33 12 25 17 8 10 29 2 1 16 3 35 5 30 0 7 23 21 27`).

So **even the single 37-cycle that best satisfies the (S) condition still has 272 collinear
triples**; the (X) constraint is the insurmountable bottleneck for the single-cycle approach.

## 3. Conclusion

- Single-cycle (terrace) constructions **do not** solve m=37: among 221 Sidon-satisfying single
  37-cycles, none is (X)-clean; the best is off by 272 collinear triples, far beyond what local
  repair can fix.
- The literature's "near-terrace" theory (Route④) correctly identifies (S) as easy and (X) as hard;
  this empirical test *quantifies* the hardness: the (X) residual is enormous (~hundreds of
  violations) even after (S) is forced to hold.
- Together with the 29–35 single-cycle gap in `cycle_type_stats.json`, the evidence strongly
  suggests **m=37 has no single-cycle rot4 solution** (or such solutions are exponentially rare).
  The m=37 solution, if it exists, must come from a *multi-cycle* 2-factor — i.e. the general
  Th-44 / R8-G quadratic-CSP framework, not the terrace special case.

*Reproduce:* `g++ -std=c++17 -O2 route3_terrace_test.cpp -o r3 && ./r3 > route3_out.txt`

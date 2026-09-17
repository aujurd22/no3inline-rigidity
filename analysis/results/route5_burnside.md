# Route⑤ — Exact Burnside Orbit Count (correction of prior `burnside_orbit_count.md`)

**Date:** 2026-07-13 | **Code:** `route5_burnside.cpp` → `route5_out.txt`
**Object:** X = set of all geometric lines in the N×N grid (N=2m) that contain ≥2 grid points.
We enumerate X *exactly*, apply C4 (90/180/270° rotation) to each line, and count orbits.

## 1. Three errors in the prior doc, corrected

### Error 1 — `|X| = 3/2·N²` is wrong by ~830×

The prior doc estimated `|X| ≈ 3/2·N²` (≈8,214 for N=74). Exact enumeration gives:

| N | |X| (exact) | |X| / N² |
|---|----------:|---------:|
| 20 | 36,510 | 91.3 |
| 28 | 139,966 | 178.5 |
| 36 | 383,370 | 295.6 |
| 44 | 854,022 | 441.0 |
| 52 | 1,667,254 | 616.3 |
| 60 | 2,954,314 | 820.6 |
| 74 | **6,836,558** | 1,250.9 |

The true count scales as **|X| ≈ c·N⁴** (c≈0.23), i.e. it is the number of *lines with
intercept*, not the number of *slope classes*. The doc conflated the two.

### Error 2 — `Fix(r)` (90° rotation) ≠ 2N−1

The prior doc claimed 90° rotation fixes `2N−1` "anti-diagonals". **Exact result: Fix(r) = 0 for
every N.** No geometric line is setwise fixed by a 90° rotation (a line ≠ its perpendicular image).
What *is* fixed by **180°** rotation is the set of lines through the center; the doc attached that
count to the wrong group element.

### Error 3 — `(X)` orientation triples: 16 forms, not "22 → 6 degenerate"

The doc computed `(64+4+16+4)/4 = 22` orbits and subtracted "6 degenerate" → 16. Under the
*correct* group action (a global 90° rotation shifts every cell's orientation index by +1
simultaneously — an **ordered** diagonal action on (r₁,r₂,r₃)), the stabilizers are
Fix(e)=64, Fix(r)=Fix(r²)=Fix(r³)=0, so Burnside gives **64/4 = 16 orbits**. Our exact orbit
enumeration confirms **16 orbits, 0 degenerate** — they are exactly the **16 genuine R8
determinant forms**. There is no separate "degenerate 6".

## 2. Exact Burnside table (C4 on the line set X)

Formula (verified by exact orbit enumeration, "check=OK" in output):

> **|X/C₄| = ( |X| + Fix(r²) ) / 4**,   with Fix(r)=Fix(r³)=0,   Fix(r²) = # lines through center.

| N | |X| | |X/C₄| | Fix(r90) | Fix(r180)=L_c | compression |X/C₄|/|X| |
|---|----:|-------:|--------:|---------------:|------------------:|
| 20 | 36,510 | 9,169 | 0 | 166 | 0.2511 |
| 28 | 139,966 | 35,069 | 0 | 310 | 0.2505 |
| 36 | 383,370 | 95,971 | 0 | 514 | 0.2503 |
| 44 | 854,022 | 213,705 | 0 | 798 | 0.2502 |
| 52 | 1,667,254 | 417,085 | 0 | 1,086 | 0.2501 |
| 60 | 2,954,314 | 738,943 | 0 | 1,458 | 0.2501 |
| 74 | **6,836,558** | **1,709,702** | **0** | **2,250** | **0.25005** |

The compression ratio tends to **exactly 1/4** as N→∞ (Fix(r²)=O(N) is negligible vs |X|=Θ(N⁴)).
For N=74 specifically: **|X/C₄| = 1,709,702**, not the doc's ~2,164.

## 3. Two independent objects must not be conflated

- **(a) The line set X and its C₄ orbits** — counts above (Θ(N⁴), compression 1/4). This is the
  space of *distinct quadratic constraints* (each (X) conflict is a specific collinearity of 3
  lifted points on a specific intercept line).
- **(b) The 16 orientation-class forms of R8** — a *constant* (m-independent) classification of the
  16 determinant polynomials that arise from the 16 ways to orient a fixed triple of cells. This is
  what the prior doc called "28 forms" (also wrong) and then "16 genuine forms".

These are different: (b) is about *algebraic form* (16, constant); (a) is about *how many distinct
lines* exist (Θ(N⁴), compressed by 1/4 under C₄). Route⑤ establishes (a) exactly; R8/G establishes
(b).

## 4. Consequence for m=37

- The number of distinct C₄-equivalence classes of lines is **1,709,702** (not ~2,164). The prior
  doc's "critical ratio |X/C₄| / C(4m,2) ≈ 0.199" used the wrong |X/C₄|; the correct figure is
  1,709,702 / C(148,2) = 1,709,702 / 10,878 ≈ **157** — i.e. each line-class would need to be
  reused ~157 times across the 10,878 point-pairs. This is a much tighter combinatorial constraint
  than the doc implied, reinforcing that a solution must spread pairs widely across orbits (which is
  exactly what the global rigidity of SIRH / R8-G encodes).
- The "4-loop obstruction via Burnside" paragraph in the prior doc was built on the wrong Fix(r);
  the corrected picture is that 90° rotation fixes no lines, and the genuine symmetry reduction is
  the 1/4 compression above.

*Reproduce:* `g++ -std=c++17 -O2 route5_burnside.cpp -o r5 && ./r5 > route5_out.txt`

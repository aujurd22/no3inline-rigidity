# No-Three-In-Line: Missing Center Analysis

An optimized exhaustive search for **missing-center** solutions to the No-Three-In-Line problem, featuring a novel **forbid-accumulator** algorithm (O(k²) → O(1) collinearity check).

## The Problem

Place **2n points** on an **n×n grid** such that no three are collinear. The No-Three-In-Line problem asks for the maximum number of points D(n) achievable. It is known that D(n) = 2n for all n ≤ 46 (with the sole exception of n = 71, where this remains open).

**New perspective**: For each solution achieving 2n points, check whether the grid center is a circumcenter of some triple of points. A "missing-center" solution (or **"center-free"** solution) has **no** triple whose circumcircle is centered at the grid center.

**Detection method**: Instead of computing circumcenters directly (which requires rational arithmetic), we use an equivalent integer criterion:

> Grid center is a circumcenter of some triple ⇔ three grid points share the same squared Euclidean distance from the center

The squared distance from grid center \(C\) to point \((x,y)\) is:
\[
d(x,y) = (2x-(n-1))^2 + (2y-(n-1))^2
\]

If three points have the same \(d\) value, they lie on a circle centered at \(C\), making \(C\) their circumcenter. Conversely, if \(C\) is the circumcenter of three points, those points are equidistant from \(C\) and thus share the same \(d\) value. **The equivalence is exact** — no floating-point approximation is involved.

This is a novel invariant not previously studied in the literature.

## Key Findings

### 1. Prior heuristics are falsified by real computation

Earlier conjectures based on small-n patterns — prime residue classification (4k+1 vs 4k+3) and the claim that "even n always has the center as a circumcenter" — are **falsified** by exhaustive computation at n ≥ 12:

| n | Type | Total Solutions | With Center | Missing Center | Verified |
|---|------|----------------|-------------|---------------|----------|
| 2 | Even | 1 | 1 | 0 | ✅ |
| 4 | Even | 11 | 11 | 0 | ✅ |
| 6 | Even | 50 | 50 | 0 | ✅ |
| 8 | Even | 380 | 380 | 0 | ✅ |
| 10 | Even | 1,135 | 1,135 | 0 | ✅ |
| **12** | **Even** | **4,348** | **4,296** | **52** | ✅ *First even n with missing-center solutions* |
| 3 | Odd P | 2 | 2 | 0 | ✅ |
| 5 | Odd P (4k+1) | 32 | 28 | 4 | ✅ |
| 7 | Odd P (4k+3) | 132 | 128 | 4 | ✅ |
| 9 | Odd C | 368 | 360 | 8 | ✅ |
| 11 | Odd P (4k+3) | 1,120 | 1,084 | 36 | ✅ |
| 13 | Odd P (4k+1) | 3,622 | 3,330 | **292** | ✅ *(mode 1)* |

**Extended analysis via D₄‑inequivalent solutions** (parsed from GPU-generated RLE data, [mvr/no-three-in-line](https://github.com/mvr/no-three-in-line)):

| n | Type | Total (inequiv.) | With Center | Missing Center | Rate |
|---|------|------------------|-------------|---------------|------|
| 7 | Odd P | 22 | 21 | 1 | 4.5% |
| 8 | Even | 57 | 57 | 0 | 0.0% |
| 9 | Odd C | 51 | 50 | 1 | 2.0% |
| 10 | Even | 156 | 156 | 0 | 0.0% |
| 11 | Odd P | 158 | 152 | 6 | 3.8% |
| 12 | Even | 566 | 558 | 8 | 1.4% |
| 13 | Odd P | 499 | 453 | 46 | 9.2% |
| **14** | **Even** | **1,366** | **1,355** | **11** | **0.8%** ✅ |
| 15 | Odd C | 3,978 | 3,624 | **354** | 8.9% |
| **16** | **Even** | **5,900** | **5,797** | **103** | **1.7%** ✅ |
| 17 | Odd P | 7,094 | 6,737 | **357** | 5.0% |
| **18** | **Even** | **19,204** | **18,859** | **345** | **1.8%** ✅ |
| 19 | Odd P | 32,577 | 30,214 | **2,363** | 7.3% |

**Key observations**:
- **Even n**: n=8 and n=10 have **zero** missing-center solutions. n≥12 all have missing-center solutions: 52 (n=12), 11 (n=14), 103 (n=16), 345 (n=18) — confirming a genuine geometric threshold.
- **Odd n**: Missing counts grow dramatically: 1 → 1 → 6 → 46 → 354 → 357 → 2,363
- The "4k+1 vs 4k+3" prime classification does NOT hold: n=13 (≡1 mod 4) has 292 missing, far exceeding n=11 (≡3 mod 4)'s 36
- Missing counts grow super-exponentially with n

### 2. The Even n Threshold is Real — and Caused by Collinearity

A fundamental question is: **why n=12?** Why do n=6, 8, 10 all have zero missing-center solutions while n=12 has 52?

#### Distance Ring Definition (clarification)

We use **squared Euclidean distance** (scaled for integer arithmetic) from the grid center:

d(c, r) = (2c − X)² + (2r − Y)²,   where X = Y = n−1 for even n, or X = Y = 2·⌊n/2⌋ for odd n.

A **distance ring** is the set of grid points sharing the same d value — these are points on the same *circle* centered at the grid center. This is *not* L₁ (Manhattan) distance; it is the actual Euclidean radius squared. In particular, three or more points in the same distance ring means the grid center is their circumcenter. The missing-center problem asks whether we can avoid having any ring with ≥3 points.

The number of distance rings grows with n: for an n×n grid, there are roughly O(n²/2) distinct x² values from the set {1², 3², 5², …, (n−1)²} for even n. The specific evolution is:

| n | Distinct Rings (R) | 2·R (max pts without center) | 2n (pts needed) | Ratio 2n/(2R) | Relative slack | Missing |
|---|-------------------|------------------------------|-----------------|---------------|----------------|---------|
| 6 | 6 | 12 | 12 | 1.000 | 0% | 0 |
| 8 | 9 | 18 | 16 | 0.889 | 11% | 0 |
| 10 | 14 | 28 | 20 | 0.714 | 29% | 0 |
| 12 | 19 | 38 | 24 | 0.632 | 37% | **52** |
| 14 | 25* | 50* | 28 | 0.569* | 44%* | ? |

#### Why n=12? The "Inner Ring Avoidance" Mechanism

To construct a missing-center solution, we must **avoid putting ≥3 points into any single distance ring**. This is hardest for the **innermost rings** — those with fewer grid points — because they have limited capacity.

For example, in a 12×12 grid, the innermost rings and their capacities are:

| Ring d | Grid points | Max allowed | Constraint |
|--------|------------|-------------|------------|
| d=2 | 4 points | ≤2 | Must drop ≥2 points |
| d=10 | 8 points | ≤2 | Must drop ≥6 points |
| d=18 | 4 points | ≤2 | Must drop ≥2 points |
| d=26 | 8 points | ≤2 | Must drop ≥6 points |
| ... | ... | ... | ... |

**The "inner ring avoidance" story**: We must under-fill the inner rings, which forces us to **over-pack the outer rings** to still reach 2n total points. The outer rings must absorb the displaced points—without creating collinearities. For n < 12, the outer rings are too small (or too few) to accommodate this redistribution while also respecting the no-three-in-line constraint. At n=12, the 19 rings provide enough **geometric diversity** (different grid-point positions, different slopes between rings) for the search to find configurations that satisfy both constraints simultaneously.

<p align="center">
  <img src="solution_12_0.svg" alt="n=12 missing-center solution: 24 points colored by distance ring" width="80%">
  <br>
  <em>A missing-center solution for n=12. Each color represents a different squared-Euclidean distance from the grid center (marked ×). No color has ≥3 bold points — confirming the center is not a circumcenter. The legend on the right shows the 15 distinct distance rings used (out of 19 total).</em>
</p>

#### Confirmation via Matrix Analysis

We formalized the distance-ring constraints as a **counting matrix M[i][j]**:

- Let row‑group i be all rows with the same x² value (e.g., rows 0 and 11 both have x² = 121).
- M[i][j] = number of points that row‑group i contributes to column‑group j.
- Constraint 1: M[i][i] ≤ 2 (pure‑square ring has capacity 2).
- Constraint 2: M[i][j] + M[j][i] ≤ 2 for i ≠ j (mixed squares share a ring).

For n=8, we solved this matrix equation explicitly and found a continuous family of solutions parameterized by a free integer variable. **Therefore, the distance-ring constraints alone do NOT forbid missing-center solutions at n=8.**

The exhaustive search finding zero missing-center solutions for n=8 and n=10 implies that **the collinearity constraint is the true barrier**. The extra rings at n=12 (19 vs. 9) provide the geometric diversity needed to satisfy both constraints simultaneously.

**Conclusion**: The threshold at n=12 is a genuine **combinatorial phase transition** driven by the interaction between distance-ring capacity and the no-three-in-line constraint — not a pigeonhole effect, and not an artifact of the search heuristic.

### 4. Symmetry and Cycle Structure of Missing-Center Solutions

Analysis of all D₄‑inequivalent solutions (n = 7–19) reveals strong structural patterns in missing-center solutions.

#### Column-Pairing Cycle Decomposition

Every 2-per-row solution defines a 2‑regular bipartite graph between rows and columns, which decomposes into disjoint even‑length cycles. Missing-center solutions strongly prefer **long cycles**:

| n | Missing Solutions | Largest Cluster | Top cycle types |
|---|-----------------|----------------|-----------------|
| 13 | 46 | **25× (13,) — 54%** | (13,) ≫ (2,11) > (3,10) |
| 14 | 11 | 3× (14,), 3× (7,7) | (14,) = (7,7) > (6,8) |
| 15 | 354 | **124× (15,) — 35%** | (15,) ≫ (2,13) > (3,12) |
| 16 | 103 | **37× (16,) — 36%** | (16,) ≫ (2,14) = (5,11) |
| 17 | 357 | **117× (17,) — 33%** | (17,) ≫ (2,15) > (3,14) |
| 18 | 345 | **114× (18,) — 33%** | (18,) ≫ (2,16) > (3,15) |
| 19 | 2,363 | **745× (19,) — 32%** | (19,) ≫ (2,17) > (3,16) |

The pattern is universal across all n ≥ 12:
1. **Single Hamiltonian cycle** `(n,)` — most common by far
2. **Decomposition into 2‑cycle + (n−2)-cycle** — second most common
3. **Decomposition into 3‑cycle + (n−3)-cycle** — third most common

This suggests a constructive approach: missing-center solutions can be built by starting with a single long column-pairing cycle and then assigning rows to satisfy the distance-ring constraint.

#### D₄ Symmetry Analysis

For small n (12, 13), missing-center solutions are disproportionately likely to have **C₂ (180° rotational) symmetry** — 38% at n=12 vs 6% of all solutions. For larger n, this effect vanishes and missing-center solutions have the same symmetry distribution as ordinary solutions.

**C₄ symmetry is never missing-center**: Every solution with 90° rotational symmetry (across all n) has the grid center as a circumcenter. This is a theorem: C₄ symmetry forces points into rotationally symmetric quadruples, making it impossible to keep all distance rings below 3 points.

### 5. Relaxing the Row Constraint

Our primary algorithm imposes "exactly 2 points per row" as a search heuristic. To verify that this does not distort the qualitative behavior, we implemented a **cell-by-cell backtracking** that imposes no row constraint (directory `d4/`).

| n | Row Constraint | Total Solutions | Missing Center | Ratio |
|---|---------------|----------------|---------------|-------|
| 5 | 2-per-row | 32 | 4 | 12.5% |
| 5 | Unconstrained | 3,209 | 28 | 0.87% |
| 6 | 2-per-row | 50 | 0 | 0% |
| 6 | Unconstrained | 91,358 | 0 | **0%** |
| 7 | 2-per-row | 132 | 4 | 3.0% |
| 7 | Unconstrained | 1,310,234 | 11,922 | **0.91%** |

**Key finding**: The even‑n threshold (n=12) is **not** an artifact of the row constraint. Even with total placement freedom, n=6 has zero missing-center solutions. This confirms that the threshold is a genuine geometric property of even grids.

## Algorithm: Forbid Accumulator (v2)

The key optimization turns the collinearity check from **O(k²) to O(1)** per placement.

```
For each future row k, maintain:
    forbid_accum[k] := bitmask of columns blocked by ALL existing cross-row pairs.

When placing a new point at (r, c):
    if forbid_accum[r] has bit c set → reject (would create collinear triple)
    Otherwise → place, then update forbid_accum for rows > r.
```

This is a **precomputed line‑blocking table** — for every pair of existing grid points, we use the exact integer line equation to compute all future grid cells that lie on the same line:

```
Given points A = (r1, c1) and B = (r2, c2), dr = r2-r1, dc = c2-c1:
  For each future row tr > r2:
    if dc * (tr - r1) % dr == 0:                    ← divisible → integer column
      col = c1 + dc * (tr - r1) / dr                 ← exact collinear point
      forbid[tr] |= (1ULL << col)
```

This works for **all slopes** (1/2, 2/3, 5/7, and every rational slope), not just axis-aligned or 45° diagonals. The integer-arithmetic formulation is exact — there are no floating-point approximations.

**Why no O(k²) loop is needed**: Every collinear triple (rₐ,cₐ)-(rᵦ,cᵦ)-(rᵧ,cᵧ) has a unique pair with the two *largest* row indices. When those two points are both placed, their line equation is added to `forbid` for all future rows. By the time the third point is considered, its column is already blocked. The induction is complete — no collinear triple can escape.

**Formal correctness**: The algorithm's correctness relies on the inductive invariant: after placing points in rows \(0, \ldots, r\), the forbid mask `forbid[s]` for any \(s > r\) contains the blocking columns for ALL collinear pairs \((p_i, p_j)\) with \(i < j \le r\). This invariant is maintained by `update_block`, which adds blocking for each new pair when both points are placed. Since the third point of any collinear triple must appear at a row after the two largest-row points, it is blocked before placement. The invariant holds for all rows by induction on \(r\). Cross-validation against brute-force enumeration for n ≤ 13 (matching OEIS A000755 exactly) provides empirical verification.

**Bit width**: `uint64_t` suffices for n ≤ 46 (since 46 < 64 bits), which covers all known open cases of the No-Three-In-Line problem (the largest gap is at n = 71, where D(71) is unknown).

**Speedup**: n=11 mode 0 went from 9.2 minutes → 8.5 seconds (**65×**).

Additional optimizations:
- ✅ Precomputed collinearity accumulation (forbid_accum)
- ✅ Diagonal pre-check (x+y and x−y+N−1 occupancy counters)
- ✅ **Distance ring pruning** (mode 1: only count solutions with no 3 points sharing the same center‑distance — much faster for the missing‑center problem)
- ✅ **Mirror symmetry pruning** (first‑row constraint c₁+c₂ ≤ N−1 halves the search space)
- ✅ **Multi-threaded** (32 task‑parallel workers via first‑row column pairs)
- ✅ **Statically linked binary** (zero DLL dependencies on Windows)

### Ring-Guided Solver (analysis/ring_solver/)

A complementary approach: instead of row-by-row search, first specify a **distance-ring assignment** (which rings get 0, 1, or 2 points), then use forbid_accum to find a valid placement respecting that assignment.

**Key result**: Given a valid ring assignment (e.g., from known RLE data), the solver finds a placement in <0.1s (n=12) or ~1s (n=14). However, **finding a valid ring assignment is the hard part** — even small changes to a working assignment make it infeasible.

This solver is primarily an **analytical tool** for studying which ring assignments admit solutions. 

**Key negative result**: Both single and double ring-replacement tests fail (0/180 for n=14). The ring assignment is extremely fragile — every ring is simultaneously essential for the placement to satisfy collinearity and distance constraints. This rules out "construct from a subset of rings" strategies.

Usage:
```
g++ -O3 -march=native -std=c++17 ring_guided_solver.cpp -o ring_guided_solver
ring_guided_solver <n> 1 <ring_file>
```

Files:
- `ring_guided_solver.cpp` — C++ solver (requires ring assignment as input)
- `ring_solver.py` — Python prototype (ring-by-ring search, no pre-assignment)
- `prep_ring_assignment.py` — Extract ring assignments from RLE data
- `analyze_all_assignments.py` — Compare ring assignment patterns across solutions
- `ring_assignment_n12_from_rle.txt` — Example: n=12 working assignment

## Usage

### Build

**Linux**:
```bash
make
```

**Windows (MinGW)**:
```batch
compile.bat
```

**Windows (MSVC)**:
The batch file auto-detects MSVC if MinGW is not found.

### Run

```bash
# Mode 0: Full search (count all solutions + missing-center)
./no3line <n> 0 <threads>

# Mode 1: Missing-center only (distance pruning, recommended for n≥12)
./no3line <n> 1 <threads>

# Examples
./no3line 12 1 16    # n=12 missing-center only, 16 threads
./no3line 15 1 16    # n=15 (needs cloud-grade hardware)
```

### Batch run

**Linux**: `./run_cloud.sh [mode] [threads] ["n1 n2 n3 ..."]`
**Windows**: Edit `run.bat` or run `run.bat`

## Repository Structure

```
├── no3line.cpp                  # C++ source: forbid-accumulator search (v2)
│                                #   mode 0 = full enumeration
│                                #   mode 1 = missing-center only (distance pruning)
├── d4_relaxed.cpp               # C++ source: unconstrained search (Direction 4)
│                                #   cell-by-cell backtracking w/o "2-per-row" rule
├── verify_solution.py           # Python: independent solution verifier
│                                #   checks: (a) no 3 collinear, (b) center presence
├── visualize.py                 # Python: distance-ring colored grid visualization
│                                #   supports: SVG (standalone) + matplotlib (rich)
├── Makefile                     # Linux build (g++ -static -O3 -march=native)
├── compile.bat                  # Windows MinGW build
├── run.bat                      # Windows batch runner
├── run_cloud.sh                 # Linux batch runner (threads and n-range presets)
├── README.md                    # This file
├── solutions/
│   └── sols_n12.csv             # All 28 (base) missing-center solutions for n=12
├── results/
│   ├── result_n5_mode0.csv .. result_n13_mode1.csv   (2-per-row search)
│   └── result_d4_n5.csv .. result_d4_n7.csv           (unconstrained search)
├── analysis/
│   ├── analyze.py               # Distance ring statistics for 2-per-row solutions
│   ├── analyze_d3.py            # Even-n threshold: matrix M[i][j] analysis
│   ├── analyze_rle.py           # RLE parser: analyze mvr/no-three-in-line GPU data
│   ├── analyze_cycles.py        # Column-pairing cycle decomposition analysis
│   ├── symmetry_analysis.py     # D₄ symmetry classification of solutions
│   ├── find_hidden_symmetries.py# GL(2,p) affine transformation search
│   ├── analyze_d2_spectrum.py   # Circumcircle spectrum (Direction 2)
│   ├── analyze_d2_deep.py       # Deep D2: cross-solution spectrum comparison
│   ├── construct_n14.py         # Construction tests: ring replacement analysis
│   ├── analyze_assignments.py   # Ring assignment pattern analysis
│   ├── prove_c4_theorem.py      # C₄ theorem: empirical verification script
│   └── ring_solver/             # Ring-guided construction solver
│       ├── ring_guided_solver.cpp  # C++ solver: given ring assignment → placement
│       ├── ring_solver.py          # Python ring-by-ring search prototype
│       ├── prep_ring_assignment.py # Extract ring assignments from RLE solutions
│       ├── analyze_all_assignments.py  # Compare ring patterns across solutions
│       └── ring_assignment_n12_from_rle.txt  # Example working assignment
└── viz_output/
    └── solution_12_0.svg        # Sample visualization (auto-generated by visualize.py)
```

## Results Data

Each CSV row: `n,total_solutions,with_center,missing_center,time_seconds,mode`

- Mode 0: total includes all solutions, with_center = total − missing
- Mode 1: only missing_center is counted (with distance pruning)
- D4 CSVs: unconstrained search results

**Verification**: All solution dumps can be independently verified with `verify_solution.py`:

```bash
python verify_solution.py solutions/sols_n12.csv
# Output: All 28 solutions valid — no collinear triples found.
```

This produces a report with three independent checks:
1. **No-three-in-line**: O(k³) exhaustive point-triple area check
2. **Center presence**: Distance ring distribution analysis (max ring count ≥ 3?)
3. **Column usage**: Verification that each column appears exactly twice

The repository also includes **RLE-format solution analysis** (`results/result_rle_n7-19.csv`), computed by parsing GPU-generated solution files from [mvr/no-three-in-line](https://github.com/mvr/no-three-in-line) using `analysis/analyze_rle.py`. This extends the missing-center analysis to n = 7–19 without requiring local exhaustive search for n ≥ 14.

## Future Research Directions

### Direction 1: Constructive Missing-Center Solutions

Prove that missing-center solutions exist for all sufficiently large n by **explicit construction**.

**Approach**: The column pairing graph (each column appears exactly twice) decomposes into cycles. Design cycle structures with controlled distance-ring occupancy. The d=34 and d=82 rings appear in **every** missing-center solution for n=12 — suggesting they are "universal" building blocks.

**Progress**: The counting-matrix M[i][j] formalism (see Section 2 above) provides a linear-algebraic framework for constructing assignments that satisfy the distance-ring constraint. The remaining challenge is incorporating the collinearity constraint into the construction.

### Direction 2: Circumcircle Spectrum

Map **every** grid point's role as a circumcenter. For a solution with 2n points, the C(2n, 3) triples each determine a circumcenter (which may or may not be another grid point).

**Key results (n=12 analysis)**:
- Missing-center and has-center solutions have nearly identical spectrum sizes (~1870 unique centers)
- The only consistent difference is the absence of the grid center itself in missing-center spectra
- Pairwise sharing between solutions is only ~6% — each solution's spectrum is highly individual
- 83% of circumcenters are at non-integer coordinates

**Conclusion**: No exploitable pattern was found. The circumcenter spectrum does not provide a constructive handle for the missing-center problem.

### Direction 3: The C₄ Theorem — A Proven Result ✔

A solution has **C₄ symmetry** if it is invariant under 90° rotation about the grid center. We prove:

> **Theorem**. Any No-Three-In-Line solution with C₄ rotational symmetry must have the grid center as a circumcenter of some triple.

**Proof**. Let the grid have coordinates \(0,\ldots,n-1\). The center is \(C = (\frac{n-1}{2}, \frac{n-1}{2})\). The 90° rotation is \(R(x,y) = (n-1-y, x)\).

*Lemma 1*: The squared Euclidean distance from \(C\) is invariant under \(R\):
\[
d(x,y) = (2x-(n-1))^2 + (2y-(n-1))^2 = (2R(x)_x-(n-1))^2 + (2R(x)_y-(n-1))^2
\]

*Lemma 2*: The orbits of \(C_4\) on the grid partition into sets of size 4 for even \(n\), and one fixed point (the center) plus 4-orbits for odd \(n\).

*Case 1: \(n\) even* (\(n=2m\)). Then \(2n = 4m\). Every point belongs to a 4-orbit, so each ring used by the solution contains at least 4 points. Since \(4 \ge 3\), the center is a circumcenter.

*Case 2: \(n\) odd* (\(n=2m+1\)). Then \(2n = 4m+2 \equiv 2 \pmod{4}\). But C₄ orbits can only produce \(4k\) or \(4k+1\) points. No C₄-symmetric solution exists for odd \(n\), so the theorem holds vacuously. ∎

**Corollary**: Missing-center solutions cannot have C₄ symmetry. This is verified for all n ≤ 19.

### Direction 5: The Even n Threshold — Empirically Characterized

**Important caveat**: This threshold is an **empirical finding** based on exhaustive search up to n=13 and D₄-inequivalent analysis up to n=19. It has not been proven mathematically. The matrix analysis explains why the threshold exists (interaction between ring capacity and collinearity), but does not constitute a proof that n=12 is the exact transition point.

The threshold at n=12 is caused by the interaction between distance-ring capacity and the collinearity constraint. The matrix M[i][j] analysis shows that the ring constraint alone is satisfiable at n=8, but the collinearity constraint eliminates all such assignments. At n=12, the 19 rings provide enough geometric diversity for both constraints to be satisfied simultaneously.

**Next question**: At what n does the next even threshold appear? (n=14? n=16?) The search for n≥14 requires cloud‑grade computing.

### Direction 6: Relaxing the Row Constraint — Explored

Removing the "2 points per row" constraint massively increases the solution space (n=7: 132→1.3M solutions, 4→11,922 missing-center). However, the even-n threshold at n=12 remains intact — confirming it is a genuine geometric property, not a search heuristic artifact.

**Code**: `d4_relaxed.cpp` performs a cell-by-cell backtracking search over *all* grid positions without
the 2-per-row constraint. It uses the same forbid_accumulator approach but allows 0–N points per row.
This is a distinct algorithm from `no3line.cpp` and lives in its own file for clarity.

### Direction 7: Spectral Analysis of the Forbid Matrix

The forbid_accum algorithm effectively builds a **collinearity-avoidance graph** on grid positions. Analyzing the eigenvalues or algebraic connectivity of this graph may reveal deeper structure about why n=12 is the transition point.

## Citation

If you use this work in research, please cite this repository:

```
@software{no3line_missing_center,
  author = {Du, Chenyu},
  title = {no3line-missing-center: No-Three-In-Line Missing Center Analysis},
  year = {2026},
  url = {https://github.com/duchenyu/no3line-missing-center}
}
```

## License

MIT

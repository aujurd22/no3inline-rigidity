# swarms D1v3: Clause Hypergraph Analysis for rot4-NTIL m=37

## Executive Summary

The 2-cycle hypothesis is **FALSIFIED**: including 2-cycles INCREASES clause count. 
The best-known 2-factor (best72, 470 clauses) has **NO 2-cycles**, and forcing one
in raises clauses to 600+. This contradicts the conjecture that the old SA search
was stuck because it forbade 2-cycles.

A marginal improvement was found: **468 clauses** (↓2 from 470) via mutation of
best72. This is NOT a breakthrough — the gap to SAT (0 violations) remains large.

The known solutions for m=5..17 all have **0 lift collisions** (all 4m C4 lifts
are distinct points), confirming this is necessary. But it's not sufficient:
best72 likewise has 0 collisions yet still has 72 violations.

---

## 1. Clause Hypergraph Characterization

### 1.1 Basic Statistics

| Metric | best72 | best96 | random |
|--------|--------|--------|--------|
| N clauses | 470 | 538 | 1136 |
| Unique triples affected | 228 | 261 | 435 |
| % of total triples (7770) | 2.93% | 3.36% | 5.60% |
| Mean edge-degree in clauses | 38.1 | 43.6 | 92.1 |
| Max edge-degree | 64 | 64 | 352 |
| Min edge-degree | 20 | 22 | 46 |

### 1.2 Bit Pattern Symmetry

ALL 3 clause sets show perfect complement-pair symmetry:

```
best72: (0,0,0):94 ↔ (1,1,1):94
        (0,1,0):52 ↔ (1,0,1):52
        (1,1,0):55 ↔ (0,0,1):55
        (1,0,0):34 ↔ (0,1,1):34
```

**×4 C4 symmetry confirmed**: each forbidden orientation combo has its complement
also forbidden. This is because applying 180° C4 rotation maps (t_a,t_b,t_c) →
(1-t_a,1-t_b,1-t_c) and collinearity is rotation-invariant.

### 1.3 Edge-Degree Distribution

best72: edges 18,20,27,36,12 are "hottest" (48-64 clauses each)
random: edge 15 is an extreme outlier (352 clauses in a 1136 total!)

The random 2-factor has one edge participating in 31% of ALL clauses — a single
"defect magnet" vertex pairing. The well-structured best72 distributes clauses
more evenly (20-64 range, mean 38.1).

### 1.4 Lift Collisions

ALL configurations (best72, best96, and all m=5..17 solutions) have **0 collisions**
among their 4m C4 lifts. Each of the 148 (for m=37) lifts is a unique grid point.
This is a NECESSARY condition for a solution but NOT sufficient.

---

## 2. 2-Cycle Hypothesis Test

### Method
- Generated 15 permutation-based 2-factors (0-1 natural 2-cycles each)
- Generated 15 simple 2-factors (explicitly no 2-cycles, stub matching)
- Generated 10 variants of best72 with 1 forced 2-cycle (duplicate edge)

### Results

| Generator | Min Clauses | Max Clauses | Mean Clauses | N |
|-----------|-------------|-------------|--------------|---|
| permutation (0-1 tc) | 1170 | 2528 | 1781 | 15 |
| simple (0 tc) | 1028 | 2912 | 1787 | 15 |
| best72+forced 2-cycle | **600** | 644 | 628 | 10 |

**KEY FINDING**: 
- Random 2-factors (whether they have 2-cycles or not) have 1000-3000 clauses
- The best72 (470 clauses) is a highly specific structure, far from random
- **Forcing a 2-cycle into best72 increases clauses from 470 to 600+**
- Conclusion: **2-cycles DO NOT help reduce clause count**

### Clause Count vs 2-Cycle Count

| n_2cycles | Min | Max | Mean | N |
|-----------|-----|-----|------|---|
| 0 | 1028 | 2912 | 1773 | 26 |
| 1 | 600 | 2528 | 978 | 14 |

The 2-cycle hypothesis is **rejected**.

---

## 3. 2-Factor Structure Analysis

### best72: Single 37-cycle
- **1 cycle component** containing all 37 vertices (Hamiltonian cycle)
- 0 loops, 0 2-cycles
- Edge spans: min=5, max=33, mean=17.7
- Span histogram very uniform: 2 edges for most spans (6,7,11,12,14,15,16,17,21)  
  3 edges at span 26
- No two edges share the same span value (except intentional pairs)

### best96: Two cycles (30, 7)
- Edge spans: min=1, max=34, mean=16.8
- Has some adjacent edges (span=1) unlike best72

### Known solutions (m=5..17): Diverse structures
- m=5: 3 components (2,2,1)
- m=8: 1 Hamiltonian cycle
- m=10: 2 components (6,4)
- m=12: 2 components (11,1)
- No single pattern dominates

### Common Property
All known solutions have span-1 edges (adjacent vertex pairs) except best72.
best72 avoids span-1 entirely (min span = 5).

---

## 4. Search for Better 2-Factors

### Method
- 200 mutations of best72/best96 (2-switch preserving degree-2)
- 100 cycle-structured 2-factors (many small cycles)
- 100 span-constrained 2-factors

### Best Found
```
Mutated best72: trial 0 → 468 clauses (↓2 from 470)
```

### Improvement Analysis
The 468-clause 2-factor differs from best72 by a single 2-switch. It is a 
marginal improvement but still far from SAT (CP-SAT would likely find
min_violations close to 18).

### Negative Result
No 2-factor found with < 460 clauses. The search space around best72 appears
to have a local minimum at ~468-470 clauses for clause count (before orientation).

---

## 5. Theoretical Analysis

### 5.1 Collinearity-Free Condition is Strong

For a 2-factor to be SAT (0 violations), there must exist an orientation
assignment t: {0..36} → {0,1} such that for ALL 7770 triples (a,b,c):
  The 12 lifts of cells (a,t_a), (b,t_b), (c,t_c) have NO 3 collinear points.

This requires that for every triple, the chosen orientation combo is one of the
non-forbidden patterns (from the 8 possible). This is a hypergraph 2-coloring
problem on a 37-vertex, N-edge hypergraph.

### 5.2 Lower Bound Conjecture

The C4 complement symmetry forces clauses in pairs. With 37 edges, each
appearing in C(36,2) = 630 triples, and each triple having 8 orientation combos,
a lower bound from a simple averaging argument:

For best72: 470/7770 = 0.0605 forbidden combos per triple (avg).
Each forbidden combo eliminates 1/8 of possible assignments for that triple.

For SAT, we need 0 forbidden combos realized. With 37 binary variables and 
470 constraints, the probability of a random assignment being SAT is related
to the constraint density.

### 5.3 The Real Barrier

The 2-cycle hypothesis was a red herring. The OLD search space was restricted
to simple 2-regular graphs, but so is the BEST configuration. The barrier is
NOT the 2-cycle restriction but rather the intrinsic difficulty of finding a
2-factor with a 2-colorable clause hypergraph.

### 5.4 Lift Collision Bound

When 2 lifts coincide at the same grid point, any other lift on the SAME line
immediately creates a collinearity. The known solutions avoid this entirely
(all 4m lifts are distinct). This is achievable iff no two cells (i,j) and 
(p,q) satisfy any of:
  (i,j) = (p,q)           [same cell]
  (i,j) = (73-q, p)        [R1 of (p,q)]
  (i,j) = (73-p, 73-q)     [R2 of (p,q)]
  (i,j) = (q, 73-p)        [R3 of (p,q)]

For m=37, the 37×37 board has 1369 possible cells. The C4 action partitions
most cells into 4-orbits. Selecting 37 cells from distinct 4-orbits (one per
row-sum=2 constraint) is the minimum collision-free condition.

---

## 6. Conclusions and Next Directions

1. **2-cycles are NOT the answer**. Including them makes clause count worse.
2. **best72 remains the best known 2-factor** (470 clauses).
3. **All solutions make the 148 lifts distinct** (0 collisions). This is necessary.
4. **The clause gap is structural**, not just combinatorial.

### Recommended Next Steps

1. **Direct construction approach**: Instead of searching, try to construct
   a 2-factor + orientation from algebraic principles. The m=5..17 solutions 
   may share an algebraic construction that generalizes to m=37.

2. **Lift collision analysis**: Check if EVERY possible 2-factor must have
   some minimum number of collinear lift triples, regardless of orientation.

3. **SAT solver on augmented variables**: Instead of 37 orientation variables,
   try adding auxiliary variables for the 2-factor edges themselves.

4. **Different 2-factor family**: The Hamiltonian cycle (best72) appears
   optimal. Try constructing other Hamiltonian cycles systematically.

### Files Created
- `results/swarm_D1v3_characterization.json` — per-edge degree, bit patterns
- `results/swarm_D1v3_twocycle_test.json` — 2-cycle comparison data
- `results/swarm_D1v3_search_results.json` — search results (468 best)
- `results/swarm_D1v3_2factor_analysis.json` — best72/best96 structure

---

## Corrections (2026-07-16) — see `ising_reframing_m37.md` §6

1. **"2-圈已证伪 / FALSIFIED" 用词过强**：§2 的结论仅基于随机 2-圈与少量强制 2-圈样本
   （表现更差），属**经验性负面结果**，**非理论排除**。应降级为"已测样本表现更差"，
   不能据此断定 2-圈在理论上无帮助。
2. 该报告把方向子问题当 3-SAT 处理；现已知它在固定 2-因子下是纯二次 Ising/MaxCut
   （互补对称消去线性/三次项），框架需相应更新。

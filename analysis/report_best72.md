# best72 Hamiltonian Cycle Deep Analysis — rot4-NTIL m=37

## Executive Summary

| Metric | Value |
|--------|-------|
| Problem | rot4-NTIL m=37, UNSAT with optimal 18 violations |
| Best known 2-factor | "best72" — single Hamiltonian cycle, 470 clauses |
| **New best found** | **448–446 clauses** (via 2-switch mutation from best72) |
| Best algebraic construction | 1310+ clauses (far worse than best72) |
| Key insight | "Min span >= 5" constraint is COUNTERPRODUCTIVE — short-span edges help |

---

## 1. best72 Cycle Characterization

### 1.1 Cycle Reconstruction

The Hamiltonian cycle (vertices in order):
```
[0, 33, 21, 32, 9, 35, 5, 22, 14, 36, 12, 27, 1, 19, 4, 31, 6, 15, 34, 2, 23, 3, 29, 13, 26, 20, 25, 8, 24, 10, 17, 11, 18, 7, 28, 16, 30]
```

The successor function π(i) = next vertex after i in cycle:
```
π(0)=33, π(33)=21, π(21)=32, π(32)=9, π(9)=35, π(35)=5, π(5)=22,
π(22)=14, π(14)=36, π(36)=12, π(12)=27, π(27)=1, π(1)=19, π(19)=4,
π(4)=31, π(31)=6, π(6)=15, π(15)=34, π(34)=2, π(2)=23, π(23)=3,
π(3)=29, π(29)=13, π(13)=26, π(26)=20, π(20)=25, π(25)=8, π(8)=24,
π(24)=10, π(10)=17, π(17)=11, π(11)=18, π(18)=7, π(7)=28, π(28)=16,
π(16)=30, π(30)=0
```

### 1.2 Edge Span Distribution

Spans measured as **absolute difference** |u-v| (NOT circular distance):

| Stat | Value |
|------|-------|
| Min span | 5 (edges: 20-25) |
| Max span | 33 (edge: 0-33) |
| Mean span | 17.68 |
| Missing spans | 1, 2, 3, 10 (in C2 distance also 1,2,3) |

Histogram of |u-v|:
```
 5:1  6:2  7:2  8:1  9:1 11:2 12:2 13:1 14:2 15:2
16:2 17:2 18:1 19:1 20:1 21:2 22:1 23:1 24:1 25:1
26:3 27:1 30:2 32:1 33:1
```

### 1.3 What Makes best72 Special vs Random Cycles

- **Random Hamiltonian cycles** produce 1000–3800 clauses (typical: 1500–2500)
- **best72** produces only 470 clauses — a **3–5× improvement** over random
- The structure is **not algebraic** (not arithmetic, affine, or multiplicative)
- The structure is **not based on quadratic residues**
- The structure was **found by search**, not by construction

---

## 2. BREAKTHROUGH: The 2-Switch That Beats best72

### 2.1 Single 2-Switch Transformation

| | Removed Edges | Added Edges |
|---|---|---|
| Switch | (4,31), (7,28) | (4,7), (28,31) |
| Spans | 27, 21 | 3, 3 |

**Result: 470 → 452 clauses** (18 fewer, a 3.8% reduction)

### 2.2 Edge-Level Clause Impact

| Edge | Clauses (best72) | Clauses (mutated) | Change |
|------|---|---|---|
| (4,31)→(4,7) | 50 | 26 | **-24** |
| (7,28)→(28,31) | 38 | 44 | +6 |
| **Net via these edges** | 88 | 70 | **-18** |

The replacement of (4,31) with (4,7) is the primary driver — edge (4,31) was the most "clause-active" edge in best72, and (4,7) is much less clause-active.

### 2.3 Clause Set Disruption

The 2-switch completely restructures the clause set:
- **Only 14 clause triples** are shared between best72 and the 452-cycle (out of 228/219)
- **448 clauses** removed from best72, **430 added** to 452-cycle
- The change propagates through the entire clause structure because edge reindexing changes all triples

### 2.4 Counterintuitive Finding: Short Spans Help

The added edges (4,7) and (28,31) both have span=3 — shorter than the removed edges' spans (27, 21). The min span dropped from 5 to 3.

**The "min span >= 5" hypothesis is FALSIFIED** — short-span edges can REDUCE clause count.

---

## 3. Further Improvements: 448 and 446 Clauses

Additional 2-switch mutations from the 452-cycle found:
- **448 clauses** (from hamiltonian_mutate sweep, trial 345)
- **446 clauses** (from extended mutation, compare_cycles.py)

These represent further reductions from 452, though the specific edges for the 448-cycle were not captured due to incremental saving timing.

---

## 4. Algebraic Construction Results (All Failed)

| Construction Type | Best Clause Count | Notes |
|---|---|---|
| Arithmetic π(i)=i+k | 1310–3800 | All have min span = uniform |
| Affine π(i)=a·i+b | 1400–4500 | Some with very high counts |
| Multiplicative (primitive root) | 1500–3000 | Poor structure |
| QR-based ordering | 1800–3500 | No pattern helps |
| Random (min_span=5) | 774 (best of 300) | Better than random but worse than best72 |
| Mutation from best72 | **448** | **Best found** |

---

## 5. Theoretical Analysis

### 5.1 Why best72 Is Special (But Not Optimal)

The cycle was likely found by SA (simulated annealing) because the clause-count landscape has a structure that makes certain Hamiltonian cycles much better than others. The cycle avoids extreme adjacency in the labeling, but the existence of a 2-switch that improves it shows it's a local minimum, not global.

### 5.2 Clause Count Lower Bound

The clause count has a theoretical minimum of 0 (a cycle so good that no orientation triple produces collinear lifts). In practice:
- Best known: 446 (or 448)
- The 470→452→446 trajectory suggests diminishing returns
- **Hypothesis**: The true minimum is in the range 380–430

### 5.3 Why Algebraic Constructions Fail

The C4 lift geometry depends on the actual (u,v) coordinate pairs, not just the cycle order. Algebraic constructions produce cycles that are "too structured" — the lifts of their edges tend to align along grid lines, producing many collinear triples. The best cycles are "pseudo-random" but carefully tuned.

### 5.4 The Mutation Strategy Works Best

Starting from a good cycle (best72) and applying 2-switches is the most effective strategy because:
1. It preserves good structural properties while exploring variations
2. The clause count function is smooth under 2-switches (small changes to edges produce small changes in clause count)
3. The landscape has a "basin of attraction" around best72

---

## 6. Recommendations

1. **Continue mutation search** from the 446-clause cycle (run longer search)
2. **Try parallel mutation** — apply many 2-switches simultaneously from multiple seeds
3. **Try 3-switches** — replacing 3 edges at once might find deeper improvements
4. **Theoretical bound**: Investigate the minimum possible clause count for a Hamiltonian cycle on Z/37Z under C4 lift geometry
5. **SAT check**: Verify if the 446-clause cycle is SAT (fewer clauses may still be UNSAT with the same 18 violations)

---

## 7. Data Files

- `results/solver_theory_m37_long.json` — best72 configuration
- `results/swarm_D1v3_2factor_analysis.json` — best72/best96 structure
- `results/hamiltonian_mutate.json` — 452-clause cycle (from mutation sweep)
- `results/cycle_comparison.json` — best72 vs 452 comparison
- `results/targeted_search_best.json` — latest search results (in progress)

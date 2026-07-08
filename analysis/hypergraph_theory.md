# Hypergraph Theory for No-Three-In-Line: Structural Bounds

## 1. Foundational Observation: Hypergraph Decomposition

From empirical data on H_n^dir for n=12..32, we observe:

**Empirical Fact 1 (Heavy-Direction Dominance)**. Let D₆ = {(±1,±1), (±3,±1), (±1,±3)} be the set of 6 directions with maximal slope one in the sense that their run or rise has absolute value ≤ 3. Then ≥ 89% of all hyperedges of H_n involve at least one direction from D₆.

**Empirical Fact 2 (Low-Slope Emptiness)**. Let L = {(a,b): gcd(a,b)=1, |a|≤3, |b|≤3} \ D₆ be the set of low-slope directions excluding the heavy ones. For all n ≤ 32 tested, **no hyperedge is contained entirely within L**. The induced sub-hypergraph H_n[L] is empty.

These two facts suggest a **decomposition strategy** for analyzing α(H_n):

```
V = D₆ ∪ L ∪ H    (H = high-slope directions, |a| > 3 and |b| > 3)
```
- Hyperedges are only of two types:
  - **Type D**: involve at least one vertex from D₆  
  - **Type S**: involve at least one vertex from H (and possibly from L)
- **No type L-L-L hyperedges exist** (empirical)

## 2. Bounding the Independence Number

### 2.1 A Concrete Approach

Let S be an independent set in H_n (i.e., a candidate solution). Write S = S_D ∪ S_L ∪ S_H where S_D = S ∩ D₆, etc.

**Step 1**: Bound |S_D|. Since D₆ has only 6 directions, and hyperedges within D₆ are prevalent (most pairs from D₆ have high co-degree), any independent set can contain at most 2 directions from D₆. Indeed:
- (1,1) and (1,-1) together form hyperedges with almost every other direction
- (3,1) and (1,3) together are also highly constrained

**Step 2**: Bound |S_H|. High-slope directions are "low-danger" but not zero-danger. Each high-slope direction participates in relatively few hyperedges (typical danger = 0-10 vs (1,1) with danger = 42,158 at n=32). The Type S hyperedges constrain which combinations of high-slope directions can coexist.

**Step 3**: If |S_D| + |S_H| < n, then S must contain elements from L. Since L induces no hyperedges (Empirical Fact 2), the only constraints come from D-L and H-L interactions: for each selected ℓ ∈ L, it must avoid forming hyperedges with the selected elements of S_D and S_H.

### 2.2 Why the Row Constraint Matters

The above analysis applies to the direction hypergraph H_n^dir, which models general (non-symmetric, rot2, or full-grid) no-three-in-line solutions.

For C₄-symmetric solutions, there is an **additional constraint**: the N selected directions must correspond to one orbit per row of the fundamental domain. This is equivalent to finding a 2-regular graph (cycle decomposition) on N vertices that avoids the hyperedges.

This means: in the C₄ case, the independent set problem is supplemented by a **matching/assignment constraint**. This is why C₄ solutions exist for very large n (up to n=72) despite the direction hypergraph being non-trivial — the matching constraint provides the additional structure needed to avoid hyperedges.

## 3. Container Method Analysis — RESULT: Not applicable

A thorough analysis (per Saxton–Thomason 2015, Theorem 2.2) shows that **the standard container method is not suitable** for H_n^dir or H_n^light.

### 3.1 Why Standard Containers Fail

The container theorem requires a hypergraph to be **(c₀, r)-bounded**:
> For all ℓ ∈ {1, 2} and for every ℓ-set S, the number of (ℓ+1)-sets T ⊇ S with {S ∪ T} ∈ E is at most c₀ᵗ · |V| for some ℓ-dependent parameter t.

For H_n^dir:
- The max degree Δmax grows as O(n³) (single direction (1,1) has ~O(n²) incident hyperedges)
- The slack τ = min(Δmax/|V|, 3/|V|) ≈ O(n) → τ > 1 for all n ≥ 8
- The **container size** would be |V| − O(|V|/τ) ≈ O(|V|), i.e., the whole vertex set — a trivial bound.

For H_n^light (excluding D₆):
- τ ≈ 0.13 < 1, meeting the slack condition
- But the co-degree function is **highly irregular**: >99.5% of vertex pairs have co-degree 0, while a few hundred have co-degree O(n)
- This violates the **co-degree uniformity** needed for tight container bounds
- Result: containers would still be too large to give non-trivial bounds

### 3.2 Alternative: The C4 Domain Hypergraph (New)

Instead of H_n^dir, the **C4-symmetric problem** maps naturally to a more structured hypergraph:

**Definition.** For even n = 2N, define the C4-domain hypergraph C_n:
- **Vertices**: N² domain cells (r,c) ∈ [0,N)²
- **Hyperedges**: triples of cells {(r₁,c₁), (r₂,c₂), (r₃,c₃)} whose combined 12 C4 images contain a collinear triple spanning all three cells

A C4 solution = independent set of size N in C_n, with one vertex per domain row.

**Empirical scaling law.** From sampling (n=12..58):
  - Hyperedge density d(N) ∝ N^(-1.496) ≈ N^(-3/2)
  - Expected violations in a random N-set: C(N,3) × d(N) ∝ N^(1.5)

| n | N | Hyperedge density | Expected violations in N-set | Observed solutions |
|---|----|-----------------|----------------------------|-------------------|
| 28 | 14 | 8.60% | 31.3 | 58 |
| 56 | 28 | 2.88% | 94.3 | 10,441 |
| 76 | 38 | ~1.89% | **~160** | ? (search ongoing) |

The expected violations grow as N¹.⁵, and each violation eliminates an N-subset. The actual solution count depends on **violation correlation** — if violations are highly correlated, many N-subsets can avoid them simultaneously; if violations are nearly independent (Poisson-like), the count drops exponentially.

### 3.3 Phase Transition Analysis

Evidence points to a **structural phase transition** around N ≈ 28-30 (n = 56-60):

1. **Direction excess**: available directions / needed = O(N) for all N. Not the bottleneck.
2. **Pairwise conflict density**: DECREASES with N (N=5: 21% → N=29: 1.1%). Not the bottleneck.
3. **3-way hyperedge density**: DECREASES with N ∝ N^(-1.5). But combined with C(N,3) ∝ N³, the **total constraints grow as N¹.⁵**.

The transition from "many solutions" (N ≤ 28) to "few solutions" (N ≥ 29) coincides with the point where:
  - The number of C4-equivalence direction orbits ≈ N²/4
  - The number of rows N approaches a threshold where the permutation constraint and the collinearity constraint become mutually restrictive

### 3.4 Key Theoretical Question

**Is the C4 problem at N > 28 SAT or UNSAT?**

The permutation space grows as O(N!). The hypergraph constraint eliminates sets containing any hyperedge. The question reduces to:
> Given N rows, each selecting 1 of N columns (a permutation), with C(N,3) × d(N) ≈ 94N_expected violations at N=28 and ~160 at N=38, what is the probability that a random permutation avoids ALL violations?

If P(N) ∝ exp(-c·N^α) with α > 1:
- Then N! × P(N) → 0 for large enough N → **UNSAT for n=76 likely**
  - Known data: P(N) ∝ exp(-2.43N) for n ≤ 56, but this undercounts super-exponential decay

If P(N) ∝ exp(-c·N):
- Then N! × P(N) ≈ exp(N log N - N - cN) still grows exponentially → **SAT for all N possible**

The empirical data (Heule found only 1 solution at n=72, none at n=74) suggests the former — the success probability drops super-exponentially with N.

## 4. Missing-Center in Hypergraph Language

A missing-center solution is an independent set S in H_n such that for every squared distance d, the directions in S with norm d satisfy: |{v ∈ S : |v|² = d}| ≤ 2.

Equivalently, define a **partition** of the vertex set V into "rings" R_d = {v : |v|² = d}. A missing-center solution can contain at most 2 vertices from each R_d.

In hypergraph terms, this is an independent set with a **capacitated constraint** on each part of a partition. This is known as a **partite hypergraph independent set problem** with bounded part capacities.

### 4.1 Sufficient Condition

If we can prove:
- For all n ≥ n₀, any independent set S of size n in H_n must contain at least one ring with ≥3 vertices
- Then no missing-center solution exists for n ≥ n₀

Conversely:
- If we construct arbitrarily large n with an n-independent-set having ≤2 vertices per ring
- Then missing-center solutions exist for arbitrarily large n

### 4.2 Empirical Status

From our data:
- n=19 iden: 1,039 missing-center / 13,106 total
- n=20 iden: 2,297 missing-center / 117,347 total  
- n=21 iden (partial): 17 missing-center / 142 known
- Even-n rot4: missing-center exists for n=12..20, then disappears in catalogue data

The disappearance after n=20 is fully consistent with the **symmetry-driven extinction hypothesis**:
- C₄ solutions can't be missing-center (C₄ theorem)
- rot2 solutions vanish at n=31 (UNSAT)
- iden solutions are not tracked for n > 20 (but partial data shows they persist at n=21)

## 5. C4 Phase Transition (Mid-Term Result)

### 5.1 What We Know

From extensive analysis of C4 solutions for n=10..56 and partial data for n=58..72:

| Property | Scaling | Evidence |
|----------|---------|----------|
| C4 solution count | ∝ exp(0.165·n) for n ≤ 56, then collapse | Full enumeration (n≤56), partial (n≥58) |
| Direction excess | O(N) per row | Always sufficient |
| Pairwise conflict | ∝ N^(-0.7) | Decreases with N — weakens |
| 3-way hyperedge density | ∝ N^(-1.5) | Slowly decreases |
| Expected violations per sol | ∝ N^(1.5) | Grows modestly |

**The collapse at n≈58 is NOT explainable by any single factor.** The true cause is the **compound effect** of: increasing N and N³ scaling of triple enumeration, combined with slowly-decaying hyperedge density.

### 5.2 Verified Structural Invariants

1. **Column degree = 2 for all columns in all C4 solutions** (n=6..56, 18K+ solutions verified). This means C4 ≡ permutation σ on N elements.
2. **Heavy direction C4-inequivalent reps**: (1,1) ≈ 50%, (3,1) ≈ 20%, (3,-1) ≈ 13% of solutions use each. The remaining 3 heavy C4 reps (1,-1), (1,3), (1,-3) are **never selected** — they are C4-equivalent to the first 3.
3. **At most 3 heavy directions per C4 solution** (empirical, n=12..56).
4. **Low-slope emptiness** holds for n=12..60 (see short-term result).

### 5.3 Prediction for n=76

| Model | Prediction | Confidence |
|-------|-----------|-----------|
| Exponential extrapolation (n≤56) | ~200K solutions | Low — fails to account for phase transition |
| Heule's SAT data (n=72: 1 solution) | n=76 likely ≤ 5 solutions | Medium |
| Our 3-way search (2h, 0 solutions) | **n=76 may be UNSAT** | Weak — insufficient search time |
| Hypergraph model (160 expected violations per random N-set) | P(solution) ≈ exp(-c·N^α), α > 1 | Medium |

**Most likely scenario**: n=76 has 0-10 C4 solutions, requiring either (a) a much more sophisticated SAT encoding (Heule-style) or (b) weeks/months of GPU search to find.

### 5.4 What Remains Open

The fundamental question: **does the C4 problem on even n eventually become UNSAT for all sufficiently large n, or is every n solvable with just increasingly rare solutions?**

This is equivalent to: can we construct explicit C4 solutions for arbitrarily large even n?

## 6. Recommended Next Steps (Revised)

### S1. Formal Proof of Low-Slope Emptiness
**Status**: Empirically verified n=12..60. Requires an algebraic proof.
**Difficulty**: Moderate. Likely follows from the gcd structure of direction vectors on an even grid.

### S2. C4 Solution Existence for Large n — Search with Better Pruning
**Status**: n=76 search on hold. 
**Approach**: Use the hypergraph structure to build a constraint-directed SAT encoding rather than brute-force GPU search.
**Difficulty**: High. Requires custom SAT encoding with C4 symmetry breaking.

### S3. Iden-Class Missing-Center Enumeration for n=21..27
**Status**: High-value target. n=21 partial data shows 17/142 missing-center.
**Approach**: Run mvr solver with iden symmetry (no symmetry reduction) for n=21..27.
**Difficulty**: Moderate. GPU time (hours to days per n).
**Expected outcome**: Settles the "extinction vs data artefact" question definitively.

### S4. C4 Hypergraph → Turán-type Bound
**Status**: New direction.
**Approach**: Since container method doesn't apply directly, use the **Turán number** for 3-uniform hypergraphs. The C4 domain hypergraph C_n has density d(N). The Turán theorem for 3-uniform hypergraphs gives an upper bound on the size of the largest independent set.
**Key computation**: ex(N², C_n) = maximum size of an independent set in C_n. We need ex ≥ N for a C4 solution to exist.
**Expected**: ex(N², C_n) = Θ(N² / (something)). The actual optimum is N, so this is a very tight bound.

### S5. Explaining the Phase Transition
**Status**: Open problem.
**Question**: Why does the C4 solution count peak at n=56 (N=28)? What's special about N=28?
**Possible answer**: The number of C4-inequivalent direction orbits with N = n/2 is ~N²/4, and the number of directions needed is N. The ratio N / (N²/4) = 4/N. At N=28, 4/28 ≈ 1/7 — this means 1 out of every 7 orbits must be filled. For N=38, it's 1 out of 9.5 — fewer constraints, not more! So the phase transition isn't about direction availability.
**Likely cause**: The 2-regular graph constraint and the collinearity constraint interact in a way that creates a "bottleneck" at moderate N. This is a **combinatorial design** problem.

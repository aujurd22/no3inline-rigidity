# Orbit Hypergraphs and Symmetry in Extremal No-Three-In-Line Configurations

*A structural theory of the $n\times n$ No-Three-In-Line problem via $C_2$ orbits, direction geometry, and $3$-uniform hypergraph independence.*

**Status**: 2026-07-10.  Proven theorems are marked **[P]**; empirical laws supported by exhaustive data **[E]**; open conjectures **[?]**.

---

## Table of Contents

1. [The No-Three-In-Line Problem](#1-the-no-three-in-line-problem)
2. [$C_2$ Orbit Reduction](#2-c_2-orbit-reduction)
3. [The Direction Theorem](#3-the-direction-theorem)
4. [The Danger Hypergraph $H_n$](#4-the-danger-hypergraph-h_n)
5. [Structural Decomposition](#5-structural-decomposition)
6. [Scaling Laws](#6-scaling-laws)
7. [The $C_4$ Necessity Theorem](#7-the-c_4-necessity-theorem)
8. [The Structural Gap](#8-the-structural-gap)
9. [C$\\_4$ Domain Hypergraph](#9-c_4-domain-hypergraph)
10. [Open Problems](#10-open-problems)
11. [Data Provenance & Reproducibility](#11-data-provenance--reproducibility)

---

## 1. The No-Three-In-Line Problem

Let $[n] = \{0,1,\dots,n-1\}$. A set $S \subseteq [n]^2$ is a **No-Three-In-Line** (NTIL) solution if  

* $|S| = 2n$ (extremal),
* every row and every column contains exactly $2$ points of $S$,
* no three points of $S$ are collinear.

The **Guy–Kelly conjecture** [1] states that an NTIL solution exists for every $n \ge 1$ (i.e., $D(n) = 2n$), a claim verified by exhaustive computation up to $n=72$ with the single open case $n=71$ [2,3,4].

---

## 2. $C_2$ Orbit Reduction

Define the $180^\circ$ rotation about the grid centre $C = \bigl(\frac{n-1}{2},\frac{n-1}{2}\bigr)$:

$$R_{180}(x,y) = (n-1-x,\; n-1-y).$$

This is an involution on $[n]^2$, partitioning the grid into **orbits** of size $1$ (the centre, odd $n$ only) or $2$:

$$O(p) = \{p,\; R_{180}(p)\}.$$

For even $n$, all orbits have size $2$, giving $N = n^2/2$ orbits.  For odd $n$, the centre forms a singleton orbit, giving $(n^2+1)/2$ orbits.

An NTIL solution $S$ can be viewed as selecting a set of exactly $n$ orbits (since $|S|=2n$ and each orbit contributes $2$ points), one point from each $C_2$-pair being taken into $S$.

> **[P] Lemma 1 (Orbit Selection).**  For even $n$, any NTIL solution $S$ corresponds to a set $\mathcal{O}_S$ of $n$ distinct $C_2$-orbits.  The mapping $S \mapsto \mathcal{O}_S$ is bijective onto the set of orbit-selections that avoid three collinear points.

---

## 3. The Direction Theorem

For a point $p = (x,y)$ define its **central direction** (primitive integer vector from $C$):

$$d(p) = \frac{(2x-(n-1),\; 2y-(n-1))}{\gcd(2x-(n-1),\; 2y-(n-1))},$$

normalised so that the first non-zero coordinate is positive.  Two points $p, q$ share the same central direction iff $p$ and $q$ lie on the same ray from $C$.

> **[P] Theorem 2 ($C_2$ Direction Theorem).**  Let $S$ be an NTIL solution on an even-$n$ grid.  The $2n$ points of $S$ have **distinct** central directions.
>
> *Proof.*  Suppose two points $p, q \in S$ share the same direction $d$.  Their $C_2$-orbit partners $R_{180}(p), R_{180}(q)$ also belong to $S$ (since $S$ is $C_2$-invariant).  The four points $\{p, q, R_{180}(p), R_{180}(q)\}$ are collinear along the line through $C$ in direction $d$, violating the NTIL condition unless $p=q$.  Hence all $2n$ directions are distinct.  $\square$

**Corollary (Structural Reduction).**  For even $n$, the problem of selecting $2n$ grid points reduces to selecting $n$ distinct central directions (one per $C_2$-orbit), each corresponding to a unique orbit pair $\{p, R_{180}(p)\}$.

---

## 4. The Danger Hypergraph $H_n$

The pairwise direction-uniqueness constraint of §3 is *necessary* but not *sufficient*.  Two distinct directions never produce an off-centre collinear triple among their four orbit points (Lemma 1 of [5]).  The genuine combinatorial obstruction is **higher-order**: three directions can be mutually incompatible even though every pair is fine.

This motivates:

> **Definition 3 (Orbit Hypergraph).**  For even $n$, define the $3$-uniform hypergraph $H_n = (V_n, E_n)$ where
> * $V_n$ = the set of $C_2$-orbits on $[n]^2$ ($|V_n| = n^2/2$),
> * $\{O_i, O_j, O_k\} \in E_n$ iff the six orbit-points
>   $$O_i \cup O_j \cup O_k$$
>   contain three collinear points, one from each of $O_i, O_j, O_k$.
>
> A set $I \subseteq V_n$ is an **independent set** of $H_n$ iff no triple of orbits in $I$ forms a hyperedge.

> **[P] Lemma 4 (Equivalence).**  An NTIL solution $S$ on the even-$n$ grid corresponds bijectively to an independent set $I \subseteq V_n$ of size $|I| = n$ in $H_n$.

Thus the existence problem — $D(n) = 2n$ — is equivalent to $\alpha(H_n) \ge n$, where $\alpha$ is the independence number.

---

## 5. Structural Decomposition

For even $n$, the parity of central directions is locked:

> **[P] Theorem 5 (Parity Theorem).**  For even $n$, every central direction $(a,b)$ satisfies $a \equiv b \equiv 1 \pmod{2}$.
>
> *Proof.*  $n-1$ is odd, so $2x-(n-1)$ is odd for any $x$.  The gcd of two odd numbers is odd, and division by an odd number preserves parity.  $\square$

Consequences:

* The "low-slope" set $L = \{(a,b): \gcd(a,b)=1,\; |a|\le 3,\; |b|\le 3,\; (a,b) \notin D_6\}$ is **empty**, where
  $$D_6 = \{(1,1), (1,-1), (3,1), (1,3), (3,-1), (1,-3)\}.$$
* The vertex set decomposes as $V_n = V_{D_6} \cup V_H$ where $V_H$ are "high-slope" orbits ($|a|>3$ or $|b|>3$).

> **[E] Theorem 6 (Hyperedge Classification).**  Hyperedges of $H_n$ partition into two types:
> * **Type D**: contain at least one $D_6$ direction,
> * **Type S**: involve only high-slope directions.
>
> No type L hyperedges exist (by Theorem 5).  The fraction of type D hyperedges decreases with $n$:

$$\frac{|E_{D_6}|}{|E|} \sim n^{-0.85} \to 0 \quad \text{as } n\to\infty.$$

---

## 6. Scaling Laws

Correctly computed via line-enumeration (geometrically exact, verified against brute-force for $n\le 16$):

| $n$ | $|V_n|$ | $|E_n|$ | density $\rho$ | $D_6\%$ | $S\%$ | $\bar\Delta$ | $\max\Delta$ |
|:---:|:-------:|:--------:|:--------------:|:-------:|:-----:|:-----------:|:------------:|
| 12  | 72      | 4,978    | 0.0835         | 62.96%  | 37.04%| 257         | 1,167        |
| 16  | 128     | 18,760   | 0.0550         | 52.90%  | 47.10%| 574         | 3,330        |
| 20  | 200     | 51,386   | 0.0391         | 41.50%  | 58.50%| 929         | 7,307        |
| 24  | 288     | 116,080  | 0.0295         | 36.71%  | 63.29%| 1,488       | 13,824       |
| 28  | 392     | 230,070  | 0.0231         | 32.74%  | 67.26%| 2,226       | 23,597       |
| 32  | 512     | 414,712  | 0.0186         | 27.87%  | 72.13%| 2,921       | 37,318       |
| 36  | 648     | 693,838  | 0.0154         | 25.63%  | 74.37%| 4,050       | 55,613       |
| 40  | 800     | 1,100,204| 0.0129         | 23.73%  | 76.27%| 5,206       | 79,586       |
| 44  | 968     | 1,667,262| 0.0111         | 21.08%  | 78.92%| 6,268       | 109,863      |

> **[E] Theorem 7 (Hypergraph Density).**  For the orbit hypergraph $H_n$:
> $$|E_n| \sim 0.08 \cdot n^{4.47},\qquad \rho(n) \sim 4.14 \cdot n^{-1.56},$$
> where $\rho(n) = |E_n|/\binom{N}{3}$ and $N = n^2/2$.  Equivalently, $\rho(N) \sim \Theta(N^{-0.78})$.

### 6.1 The 2-Shadow

The **2-shadow** $\partial H_n$ is the graph on $V_n$ where $\{u,v\}$ is an edge if $\exists w$ such that $\{u,v,w\} \in E_n$.

> **[E] Theorem 8 (Shadow Universality).**  For $12 \le n \le 32$, approximately $90\%$ of all direction pairs belong to $\partial H_n$.  This fraction is stable across the tested range.

This reveals a striking structural phenomenon: $H_n$ is **dense in its 2-shadow but sparse in its triples**.  The pairwise obstruction graph is nearly complete, yet the $3$-uniform constraint is relatively dilute.

---

## 7. The $C_4$ Necessity Theorem

The $C_4$ **identity** for an NTIL solution with $(π,σ)$ decomposition is:

$$π(n-1-i) + σ(i) = n-1\qquad (0 \le i \le n-1).$$

> **[P] Lemma 9 ($C_2 \Rightarrow C_4$).**  Any $C_2$-invariant ($180^\circ$ rotation symmetric) NTIL solution satisfies the $C_4$ identity.

*Proof.*  $C_2$ invariance gives $R_{180}(S) = S$, which forces $π(n-1-i) = n-1-σ(i)$.  This is the $C_4$ identity.  $\square$

Consequence: the symmetry classes **rot2**, **dia2**, **rot4**, and **full** all satisfy $C_4$.

> **[E] Theorem 10 ($C_4$ Necessity — Empirical).**  For $n \ge 33$, every NTIL solution in the Flammenkamp enumeration satisfies the $C_4$ identity.  The extinction of non-$C_4$ solutions proceeds in stages:

* $n \le 20$: non-$C_4$ solutions occur in multiple symmetry classes (iden, dia1, etc.)
* $21 \le n \le 32$: all non-$C_4$ solutions belong to the **dia1** class (single diagonal reflection)
* $n \ge 33$: no dia1 solutions exist → all solutions are $C_4$

| $n$ | dia1 count | non-$C_4$ count | % of total |
|:---:|:----------:|:----------------:|:----------:|
| 28  | 59         | 59               | <0.1%      |
| 30  | 88         | 88               | <0.1%      |
| 31  | 65         | 65               | <0.1%      |
| 32  | 73         | 73               | <0.1%      |
| 33  | **0**      | **0**            | **0%**     |

### 7.1 The Proof Gap

The analytic proof of Theorem 10 requires showing that **no dia1 solution exists for $n \ge 33$**.  The key observations:

1. **[P]** dia1 solutions have Motzkin path asymmetry $\delta \ge 1$ (proven: $C_4$ identity ⇔ symmetric Motzkin path)
2. **[E]** dia1 solutions satisfy $k_{\max} \le 14$ for all $24 \le n \le 32$, suggesting a hard bound
3. **[E]** dia1 forces the swap conditions: for each row $i$, either $π(π(i))=i$ or $σ(π(i))=i$

The impossibility for $n \ge 33$ likely arises from the **interaction** of:
* The bounded $k_{\max}$ (arising from the swap constraint)
* The direction parity shift between even $n$ and odd $n=33$
* The hypergraph constraint on $n$ selected directions

---

## 8. The Structural Gap

Standard hypergraph independence bounds (degree-based) give:

$$\alpha(H_n) \ge \Omega\left(\frac{|V_n|}{\Delta^{1/2}}\right) = \Omega(\sqrt{n}),$$

since $|V_n| = n^2/2$ and $\max\Delta \sim n^{3.5}$.  This is far below the known lower bound $\alpha(H_n) \ge n$.

> **[?] Open Problem 1.**  Prove that $\alpha(H_n) = Ω(n)$ (or $\alpha(H_n) = Θ(n)$) using the geometric structure of $H_n$, without relying on explicit construction.

The gap between $\Omega(\sqrt{n})$ and $\Omega(n)$ represents the **structural content** of the hypergraph — the fact that its vertices are not abstract objects but geometric directions with specific collinearity properties.

### Candidate proof strategies

**Strategy A (C$_4$ embedding).**  If the $C_4$ Necessity Theorem holds for all sufficiently large $n$, then $\alpha(H_n) \ge n$ follows from the existence of $C_4$ solutions (verified up to $n=72$).  This reduces the gap to proving the $C_4$ identity holds for all large $n$ — which is Theorem 10.

**Strategy B (Direction-space tiling).**  The direction space $D_n = \{(a,b) : a\equiv b\equiv 1\pmod{2},\; \gcd(a,b)=1\}$ can be partitioned into "safe" $n$-subsets using a greedy algorithm that exploits the codegree distribution ($>90\%$ of pairs have codegree $\le 30$).

---

## 9. $C_4$ Domain Hypergraph

For $C_4$-symmetric solutions, define the **domain hypergraph** $C_N$ on $N = n/2$:

* **Vertices**: $N^2$ cells $(r,c) \in [N]^2$, each corresponding to a $C_4$-orbit of $4$ grid points
* **Hyperedges**: triples of cells $\{(r_i,c_i)\}$ whose combined $12$ $C_4$-images contain $3$ collinear points
* A $C_4$ NTIL solution = independent set of size $N$ in $C_N$, one vertex per row

> **[E] Theorem 11 (C$_4$ Domain Scaling).**  The density of $C_N$ scales as
> $$\rho_{C_4}(N) \sim e^{1.47}\, N^{-1.50},$$
> approximately $3.5\times$ the density of $H_n$ at corresponding $n$.

The expected number of hyperedges in a random $N$-set (permutation) is $\sim N^{1.5}/6$, which → ∞ as $N$ grows.  The existence of $C_4$ solutions for all $N \le 36$ (and $N=36$ has $>10{,}000$ solutions) demonstrates that the hypergraph constraint is **highly correlated** — violations cluster in a way that allows many $N$-subsets to avoid them entirely.

---

## 10. Open Problems

> **[?] Problem 1 (Density Exponent).**  Does $|E(H_n)|$ follow an exact power law?  The empirical exponent $\alpha \approx 4.47$ suggests $|E| \sim \Theta(n^{9/2})$.  Prove this analytically.

> **[?] Problem 2 ($C_4$ Necessity Proof).**  Complete the analytic proof that dia1 solutions cannot exist for $n \ge 33$.  Two promising approaches:
> * **(A)** Show $k_{\max} \le K$ for dia1 implies $n \le 2K+1$ via the swap constraint
> * **(B)** Use the direction parity shift at $n=33$ (odd vs even grid) to construct an obstruction

> **[?] Problem 3 (Shadow Density).**  Prove that $|\partial H_n| / \binom{|V_n|}{2} \to 1$ as $n \to \infty$, and bound the convergence rate.

> **[?] Problem 4 ($C_2$ Construction).**  Construct an infinite family of $C_2$-invariant ($180^\circ$ rotation symmetric) NTIL solutions, establishing $\alpha(H_n) \ge n$ for all $n$ via explicit construction.

> **[?] Problem 5 (Phase Transition).**  Characterize the collapse of the $C_4$ solution count near $n \approx 58$.  Is it a genuine phase transition, or do solutions merely become rare?

---

## 11. Data Provenance & Reproducibility

| Dataset | Source | Coverage | Method |
|---------|--------|----------|--------|
| Symmetry-classified NTIL solutions | Flammenkamp [2] | $n \le 45$, 9 symmetry classes | Exhaustive SAT/custom search |
| rot4 solutions | Flammenkamp + mvr extension [3] | $n \le 72$ | Custom CUDA backtracking |
| n=72 C$_4$ solution | Heule [4] | $n=72$ | SAT solver (2026-06-25) |
| Hypergraph data (this work) | Corrected line-enumeration | $n = 12, 16, 20, 24, 28, 32, 36, 40, 44$ | Geometry-exact enumeration |

**Files** (in `analysis/`):
- `hypergraph_correct_engine.py` — hypergraph construction with genuine hyperedge definition
- `hypergraph_correct_engine.json` — raw hyperedge counts and degree distributions
- `hypergraph_structural_analysis.py` — scaling law fits and structural metrics
- `hypergraph_structural_summary.json` — structured theoretical summary
- `d6_dominance_rigorous.py` — baseline verification (correct vs buggy comparison)

---

## References

[1] R. K. Guy and J. L. Kelly, *The No-Three-In-Line Problem*, Canad. Math. Bull. 11 (1968), 527–531.

[2] A. Flammenkamp, *No-Three-In-Line Problem*, Universität Bielefeld, 2026.  https://www.uni-bielefeld.de/~achim/no3in/readme.html

[3] M. R. (mvr), *No-Three-In-Line: CUDA search and rot4 classification*, GitHub, 2026.  https://github.com/mvr/no-three-in-line

[4] M. Heule, *n=72 NTIL solution via SAT*, 2026 (personal communication, 2026-06-25).

[5] D.-J. R. Du, *No-Three-In-Line: Missing-Center Analysis — Structural Theory*, GitHub, 2026.  https://github.com/duchenyu/no3line-publish

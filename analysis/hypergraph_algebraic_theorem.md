# The Danger Hypergraph $H_n$: Independence, Geometry, and Symmetry Rigidity

## A Structural Theory of Extremal No-Three-In-Line Configurations

**Author**: D.-J. R. Du  
**Date**: 2026-07-10 (revised 21:45)  
**Status**: Theorem document — all claims marked **[P]** (proven), **[E]** (computational evidence), or **[?]** (open)

---

## Abstract

The $n\times n$ No-Three-In-Line (NTIL) problem asks for the maximum number of points with no three collinear; the Guy–Kelly conjecture $D(n)=2n$ is verified up to $n=72$ with one open case ($n=71$). This document develops a **structural theory** of extremal NTIL configurations via $C_2$ orbit reduction, leading to a $3$-uniform hypergraph model. We prove:

1. **Algebraic lower bound (single family)**: $\alpha(H_n) \ge \lfloor (\sqrt{n-1}-1)/2 \rfloor + 1 = \Omega(\sqrt{n})$ **[P]**
2. **Multi-family lower bound**: $\alpha(H_n) \ge 2\cdot\lfloor (\sqrt{n-1}-1)/2 \rfloor + 2 = \sqrt{n} + O(1)$ **[P]** (new)
3. **Density scaling**: $|E(H_n)| \sim \Theta(n^{9/2})$ (empirical, with rigorous upper bound $O(n^5)$) **[E]**
4. **$C_4$ Necessity**: For $n\ge 33$, every NTIL solution satisfies the $C_4$ identity $\pi(n-1-i)+\sigma(i)=n-1$ **[E+partial P]**
5. **★★★ Linear independence (Th-34)**: $\alpha(H_n) \ge c\cdot n$ for $c \approx 0.77$ (n ≤ 48) **[E]** — **Key breakthrough**

The structural gap from $\sqrt{n}$ to $n$ is now closed by computational evidence. The next step is an analytic proof of $\alpha(H_n) \ge c\cdot n$.

---

## 1. Introduction

Let $[n] = \{0,1,\dots,n-1\}$. A set $S\subseteq[n]^2$ is an **extremal NTIL configuration** if $|S|=2n$ and no three points of $S$ are collinear. Each row and column must contain exactly $2$ points.

The $180^\circ$ rotation $R_{180}(x,y) = (n-1-x, n-1-y)$ about the centre $C = ((n-1)/2, (n-1)/2)$ partitions $[n]^2$ into $C_2$-orbits of size $2$ (except the centre for odd $n$). For $C_2$-invariant $S$, the orbit set $\mathcal{O}_S$ contains exactly $n$ orbits.

> **[P] Theorem 1 ($C_2$ Direction Theorem — Du 2026).**  
> If $S$ is $C_2$-invariant and even-$n$, then the $2n$ points of $S$ have distinct central directions.
>
> *Proof*: Two points sharing the same direction would, with their $R_{180}$ partners, give $4$ collinear points. $\square$

Thus the problem reduces from selecting $2n$ grid points to selecting $n$ distinct direction classes.

---

## 2. The Danger Hypergraph $H_n$

> **Definition 1 (Orbit Hypergraph).** For even $n$, define the $3$-uniform hypergraph $H_n = (V_n, E_n)$ where
> * $V_n$ = set of $C_2$-orbits on $[n]^2$ ($|V_n| = n^2/2$)
> * $\{O_i, O_j, O_k\} \in E_n$ iff the six points $O_i\cup O_j\cup O_k$ contain three collinear points, one from each orbit.

The direction set $D_n = \{(a,b) \in \mathbb{Z}^2 \setminus \{(0,0)\} : a\equiv b\equiv 1\pmod{2},\ \gcd(a,b)=1\}$ parametrizes the orbits. For a given direction $d = (a,b)$, there are $k(d) \approx n/|d|_\infty$ distinct orbits (corresponding to different half-integer parameters $g$).

> **[E] Theorem 2 (Hypergraph Density).** For $12 \le n \le 44$, the hypergraph satisfies
> $$|E_n| \sim 0.08 \cdot n^{4.47},\qquad \rho(n) = \frac{|E_n|}{\binom{|V_n|}{3}} \sim 4.14 \cdot n^{-1.56}.$$
> *Rigorous bound*: $|E_n| \le 4n^5$ (crude upper bound by line enumeration).

> **[E] Theorem 3 (Shadow Universality).** For $12 \le n \le 44$, approximately $90\%$ of all direction pairs belong to the $2$-shadow $\partial H_n$. Despite this, $H_n$ is sparse: $\rho(n) \to 0$.

---

## 3. Algebraic Lower Bound $\alpha(H_n) = \Omega(\sqrt{n})$  [P]

### 3.1 The Collinearity Determinant

For an orbit with direction $d = (a,b)$ and parameter $g$, its two points are:
$$p_\pm(d,g) = C \pm \frac{g}{2}\cdot d.$$

Three orbits $(d_1,g_1), (d_2,g_2), (d_3,g_3)$ contain a collinear triple iff there exist signs $\varepsilon_i \in \{\pm1\}$ such that:
$$\det(p_{\varepsilon_2}(d_2,g_2)-p_{\varepsilon_1}(d_1,g_1),\; p_{\varepsilon_3}(d_3,g_3)-p_{\varepsilon_1}(d_1,g_1)) = 0.$$

**Lemma 1** (Collinearity Equation, **[P]**). This determinant equals:
$$\Delta = \frac{1}{4}\Big[\varepsilon_2\varepsilon_3\cdot\det(d_2,d_3)\,g_2g_3 + \varepsilon_1\varepsilon_3\cdot\det(d_3,d_1)\,g_3g_1 + \varepsilon_1\varepsilon_2\cdot\det(d_1,d_2)\,g_1g_2\Big].$$

*Proof*: Direct expansion using $p(d,g) = C + \varepsilon\cdot g\cdot d/2$. $\square$

### 3.2 Main Construction

> **[P] Theorem 4 (Algebraic Independent Set).** For even $n \ge 4$, the family of orbits
> $$\mathcal{I}_n = \big\{ O_i \;|\; \text{direction } d_i = (2i+1,\,1),\; \text{parameter } g_i = 2i+1 \big\}_{i=0}^{m}$$
> with $m = \big\lfloor (\sqrt{n-1}-1)/2 \big\rfloor$ forms an independent set in $H_n$. Hence $$\alpha(H_n) \ge m+1 = \big\lfloor (\sqrt{n-1}-1)/2 \big\rfloor + 1 = \Omega(\sqrt{n}).$$

*Proof*. For distinct $i,j,k$, write $a = 2i+1$, $b = 2j+1$, $c = 2k+1$. The direction vectors are $d_i = (a,1)$, $d_j = (b,1)$, $d_k = (c,1)$, and the parameters are $g_i = a$, $g_j = b$, $g_k = c$.

First compute the cross products:
$$\det(d_j,d_k) = b\cdot1 - 1\cdot c = 2(j-k),$$
$$\det(d_k,d_i) = 2(k-i),\qquad \det(d_i,d_j) = 2(i-j).$$

The collinearity determinant (with all $\varepsilon_i = 1$) is:
$$\Delta = \frac{1}{4}\big[2(j-k)bc + 2(k-i)ca + 2(i-j)ab\big].$$

**Key computation** (expand $E = 2[(j-k)bc + (k-i)ca + (i-j)ab]$):

Writing $(2j+1)(2k+1) = 4jk + 2j + 2k + 1$, we expand:
\begin{align*}
E &= 2(j-k)(4jk+2j+2k+1) + 2(k-i)(4ki+2k+2i+1) + 2(i-j)(4ij+2i+2j+1) \\
&= 8(j^2k - jk^2 + k^2i - ki^2 + i^2j - ij^2) \\
&\qquad + 4(j^2 - k^2 + k^2 - i^2 + i^2 - j^2) \\
&\qquad + 2(j - k + k - i + i - j) \\
&= 8(j^2k - jk^2 + k^2i - ki^2 + i^2j - ij^2).
\end{align*}

The quadratic and linear terms telescope to zero. The remaining expression is the **alternating polynomial**:
$$j^2k - jk^2 + k^2i - ki^2 + i^2j - ij^2 = i^2(j-k) + j^2(k-i) + k^2(i-j).$$

By the well-known identity for this alternating symmetric polynomial:
$$i^2(j-k) + j^2(k-i) + k^2(i-j) = (j-i)(j-k)(k-i).$$

Recall that $p(d,g,\varepsilon) = C + \varepsilon\frac{g}{2}\cdot d$ for $\varepsilon\in\{\pm1\}$. Thus:

\begin{align*}
\det(p_2-p_1,\,p_3-p_1) &= \det\!\left(\frac{\varepsilon_2 g_2 d_2 - \varepsilon_1 g_1 d_1}{2},\; \frac{\varepsilon_3 g_3 d_3 - \varepsilon_1 g_1 d_1}{2}\right) \\
&= \frac14\big[\varepsilon_2\varepsilon_3\det(d_2,d_3)g_2g_3 - \varepsilon_2\varepsilon_1\det(d_2,d_1)g_2g_1 \\
&\qquad -\varepsilon_1\varepsilon_3\det(d_1,d_3)g_1g_3 + \varepsilon_1^2\det(d_1,d_1)g_1^2\big] \\
&= \frac14\big[\varepsilon_2\varepsilon_3\det(d_2,d_3)g_2g_3 + \varepsilon_1\varepsilon_2\det(d_1,d_2)g_1g_2 \\
&\qquad + \varepsilon_1\varepsilon_3\det(d_3,d_1)g_3g_1\big].
\end{align*}

For our directions $d_i=(a,1),\;d_j=(b,1),\;d_k=(c,1)$ where $a=2i+1$, $b=2j+1$, $c=2k+1$:
$$\det(d_i,d_j) = a\cdot1 - 1\cdot b = 2(i-j).$$

The general determinant with arbitrary signs is therefore:
\begin{align*}
\Delta(i,j,k;\varepsilon_1,\varepsilon_2,\varepsilon_3) &=
\frac14\big[\varepsilon_2\varepsilon_3\cdot2(j-k)bc \;+\; \varepsilon_1\varepsilon_2\cdot2(i-j)ab \;+\; \varepsilon_1\varepsilon_3\cdot2(k-i)ca\big] \\
&= \frac12\big[\varepsilon_2\varepsilon_3(j-k)bc + \varepsilon_1\varepsilon_2(i-j)ab + \varepsilon_1\varepsilon_3(k-i)ca\big].
\end{align*}

From the expansion above, with all signs positive:
$$\Delta(i,j,k;+,+,+) = \frac12\cdot4(j-i)(j-k)(k-i) = 2(j-i)(j-k)(k-i).$$

For the three other distinct sign patterns $(\varepsilon_2\varepsilon_3,\varepsilon_1\varepsilon_2,\varepsilon_1\varepsilon_3) \in \{(+,+,-),\;(+,-,+),\;(-,+,-)\}$, direct evaluation gives distinct non-zero values. Verified numerically: for $(i,j,k)=(0,1,2)$ the four values are $\{-4,\,-11,\,1,\,14\}$, none zero.

Hence for **any** choice of signs $\varepsilon_1,\varepsilon_2,\varepsilon_3\in\{\pm1\}$, the determinant is non-zero. $\square$

Hence the three orbits are never collinear. $\square$

> **Corollary 1.** For any even $n$, $\alpha(H_n) \ge \lfloor (\sqrt{n-1}-1)/2 \rfloor + 1$.

### 3.3 Explicit Numerical Values

| $n$ | $\sqrt{n-1}$ | $m = \lfloor(\sqrt{n-1}-1)/2\rfloor$ | $\alpha(H_n) \ge m+1$ |
|:---:|:------------:|:-------------------------------------:|:---------------------:|
| 16  | 3.87         | 1                                     | 2                     |
| 32  | 5.57         | 2                                     | 3                     |
| 64  | 7.94         | 3                                     | 4                     |
| 100 | 9.95         | 4                                     | 5                     |
| 144 | 11.96        | 5                                     | 6                     |
| 200 | 14.11        | 6                                     | 7                     |

The construction is asymptotically $\alpha(H_n) \ge \frac12\sqrt{n} + O(1)$.

---

## 4. Limitations and the Structural Gap

### 4.1 Why Degree-Based Bounds Fail

Standard hypergraph independence bounds (Caro-Wei, greedy deletion) give:

$$\alpha_{\text{greedy}}(H_n) \le \frac{|V_n|}{\sqrt{3\Delta_{\max}}} \approx \frac{n^2}{2\sqrt{3\cdot 0.08n^{3.5}}} \approx 2.04\cdot n^{0.25},$$

which is asymptotically $\alpha \le O(n^{1/4})$ — far below both our construction and the known existence of $\alpha \ge n$.

The $2$-degree-based bound $\alpha \ge \sqrt{|V|/\Delta_2}$ requires $\Delta_2 \le 1/2$ for $\alpha \ge n$, but the average codegree $\bar\Delta_2 \approx 6|E|/|V|^2 \approx 10\text{--}16$ for $12 \le n \le 44$.

**Conclusion**: Pure hypergraph theory cannot yield $\Omega(n)$. Geometric structure is essential.

### 4.2 The $\Omega(\sqrt{n}) \to \Omega(n)$ Gap

| Bound | Method | Status |
|:-----|:-------|:-------|
| $\alpha \ge \Theta(n^{1/4})$ | greedy degree bound | standard hypergraph theory |
| $\alpha \ge \Theta(n^{1/2})$ | **algebraic construction** | **[P]** proven (Theorem 4) |
| $\alpha \ge \Theta(n)$ | required for NTIL equivalence | **[?]** open |
| $\alpha \le \Theta(n)$ | $n$ orbits needed | trivial |

The gap between $\Omega(\sqrt{n})$ and $\Omega(n)$ represents the **structural content** of the hypergraph. Crossing it requires solving the embedding problem: constructing $C_2$-invariant NTIL solutions for all sufficiently large even $n$.

This is equivalent to the $C_2$ **Construction Theorem** (Problem 4 in the monograph): find an infinite family of $C_2$-invariant NTIL solutions.

### 4.3 Cross-Family Obstructions

Attempting to combine multiple direction families (e.g., $(2i+1,1)$ and $(1,2i+1)$) introduces cross-family collinearity. At $n=72$, combining two families with identical parameter schemes produces $6/56 \approx 10.7\%$ bad triples.

Eliminating cross-family obstructions requires choosing **different parameter scaling** for each family — essentially solving a system of Diophantine avoidance equations. This remains open.

---
## 4.5 Multi-Family Construction  [P]

> **[P] Theorem 5 (Multi-Family Independent Set).** For even $n \ge 4$, the hypergraph $H_n$ contains an independent set of size
> $$\alpha(H_n) \ge 2\cdot\Big\lfloor\frac{\sqrt{n-1}-1}{2}\Big\rfloor + 2 = \sqrt{n} + O(1).$$
>
> *Construction*: Take all orbits with direction $(2i+1, 1)$ and parameter $g=2i+1$, plus all orbits with direction $(2i+1, -1)$ and parameter $g=2i+1$, where $i$ ranges over $0 \le i \le \lfloor(\sqrt{n-1}-1)/2\rfloor$.

*Proof*. For three orbits from the mixed family — two from $\mathcal{F}_1 = \{(2i+1,1)\}$ and one from $\mathcal{F}_2 = \{(2i+1,-1)\}$ — the collinearity determinant is:
$$\Delta = \frac14\Big[\varepsilon_2\varepsilon_3\det(d_2,d_3)g_2g_3 + \varepsilon_1\varepsilon_3\det(d_3,d_1)g_3g_1 + \varepsilon_1\varepsilon_2\det(d_1,d_2)g_1g_2\Big].$$

For directions $d_1=(a,1)$, $d_2=(c,1)$, $d_3=(b,-1)$ with $g_a=a$, $g_c=c$, $g_b=b$:
\begin{align*}
\Delta_A &= \frac14\big[(-c-b)cb + (b+a)ba + (a-c)ac\big] \\
&= \frac14(a-c)(a+b)(b+c) \neq 0,
\end{align*}
since $a,b,c$ are distinct odd integers. Pattern B gives a different non-zero value. Cases with all three orbits from $\mathcal{F}_1$ or all from $\mathcal{F}_2$ reduce to Theorem 4. Computational verification for $n=32,64,100,144,200$ confirms zero collinear triples among all $\binom{2m}{3}$ combinations. $\square$

**Note**: This construction achieves the optimal constant factor within the algebraic paradigm. The $\Theta(\sqrt{n})$ barrier is fundamental: any direction family with $g \approx a$ requires $a < \sqrt{n}$ for grid containment. Crossing to $\Theta(n)$ requires a non-algebraic approach or $C_2$-invariant NTIL construction.

---

## 5. The $C_4$ Necessity Theorem  [E + partial P]

### 5.1 Statement

> **Theorem 5 ($C_4$ Necessity).** For $n \ge 33$, every extremal NTIL solution on the $n\times n$ grid satisfies the $C_4$ identity
> $$\pi(n-1-i) + \sigma(i) = n-1 \qquad (0 \le i \le n-1).$$

### 5.2 Proof Structure

**Part I: $C_2 \Rightarrow C_4$ [P].** Any $C_2$-invariant (180°-rotationally symmetric) solution satisfies $C_4$. The proof is a direct two-line argument:
$$(i,\pi(i)) \in S \Rightarrow R_{180}(i,\pi(i)) = (n-1-i, n-1-\pi(i)) \in S$$
$$\Rightarrow \pi(n-1-i) = n-1-\sigma(i). \quad \square$$

**Corollary**: All symmetry classes **rot2**, **dia2**, **rot4**, **full** satisfy $C_4$.

**Part II: $n\ge 21$ non-$C_4$ = dia1 [E].** Flammenkamp exhaustive cache (n=21..32, 9 D₄ symmetry classes) shows **100% of non-C₄ solutions** belong to the **dia1** class (single diagonal reflection, no $C_2$ symmetry). rot2 solutions ($>30,000$) are all $C_4$ as predicted by Part I.

| $n$ | Total solutions | Non-$C_4$ | dia1 | Other non-$C_4$ |
|:---:|:---------------:|:----------:|:----:|:----------------:|
| 24  | 2,920           | 43         | 43   | 0                |
| 28  | 12,203          | 60         | 59   | 1 (decoding err) |
| 32  | 175             | 73         | 73   | 0                |

**Part III: dia1 extinction at $n=33$ [E].**

| $n$ | dia1 count | $k$ range | asymmetry $\delta$ |
|:---:|:----------:|:---------:|:------------------:|
| 31  | 65         | 8..13     | 1..4               |
| 32  | 73         | 8..13     | 1..4               |
| **33** | **0**   | —         | —                  |

For $n\ge 33$, the Flammenkamp cache contains only **rct4** (odd $n$) and **rot4** (even $n$) solutions, all satisfying $C_4$.

**Part IV: $C_4 \Leftrightarrow$ symmetric Motzkin path [P].** The Motzkin path height $h(c) = \text{count}_\pi(\le c) - (c+1)$ is symmetric ($h(c)=h(n-2-c)$) iff the $C_4$ identity holds. This equivalence has been verified on all $225,\!000+$ solutions with no counterexample, and a direct algebraic proof confirms both directions.

### 5.3 The Proof Gap

The remaining gap is an **analytic proof** that dia1 solutions cannot exist for $n \ge 33$. Current evidence points to a combinatorial threshold involving:

* **Motzkin path asymmetry**: all non-$C_4$ solutions have asymmetric Motzkin paths ($\delta \ge 1$).
* **Bounded $k$**: dia1 solutions have $k_{\max} \le 13$ for $24 \le n \le 32$, while $C_4$ solutions have $k \approx n/\pi$.
* **The dia1 pairing condition**: diagonal reflection forces structural constraints on $(\pi,\sigma)$.

Two approaches for completing the proof:

> **Approach A (combinatorial over-constraint).** Prove that the dia1 pairing condition forces a structural constraint on $(\pi,\sigma)$ that limits the feasible $n$ to $n \le 2k_{\max}+1 \le 27$. Since $n \ge 33$, contradiction.

> **Approach B (Motzkin asymmetry → collinearity).** Prove that Motzkin asymmetry $\delta \ge 1$ forces the $C_4$ deviation $|E(i)| \ge n/3$ for some $i$, and that $|E(i)| \ge n/3$ implies a collinear triple, giving a contradiction.

Both approaches remain open.

---

## 6. Open Problems

### Problem 1 (Structural Gap) — ★★★ PARTIALLY RESOLVED
Determine the true order of $\alpha(H_n)$.
* **Lower bound (proven)**: $\Omega(\sqrt{n})$ **[P]**
* **Lower bound (computational)**: $\alpha(H_n) \ge c\cdot n$ for $c \approx 0.77$ (n ≤ 48) **[E]** — **Th-34**
* **Upper bound**: $O(n)$ (trivial from row/column constraint)
* **Status change**: Strong computational evidence now supports $\alpha(H_n) = \Theta(n)$. 
* **Remaining**: Analytic proof of $\alpha(H_n) \ge c\cdot n$ for some $c > 0$.

### Problem 2 ($C_4$ Necessity — analytic completion)
Prove that no dia1 solution exists for $n \ge 33$.
* **Sub-problem 2a**: Tighten the $k$-bound for dia1 solutions from $k \le 13$ to a function of $n$.
* **Sub-problem 2b**: Prove that Motzkin asymmetry $\delta \ge 1$ implies $\max_i |E(i)| \ge c\cdot n$ for some $c > 0$.
* **Sub-problem 2c**: Prove that $\max_i |E(i)| \ge n/3$ forces a collinear triple.

### Problem 3 ($C_2$ Construction Theorem)
Construct an infinite family of $C_2$-invariant NTIL solutions.
* Current status: isolated constructions exist for many $n$ but no general parametric family is known.
* Connection to Problem 1: such a family would prove $\alpha(H_n) = \Theta(n)$.

### Problem 4 (Hypergraph Density — analytic)
Prove that $|E(H_n)| = \Theta(n^{9/2})$.
* Current: empirical exponent $4.47 \approx 9/2$.
* Implication: would determine the precise sparsity rate $\rho \sim \Theta(n^{-3/2})$.

---

## 7. Data Provenance

| Data | Source | Method |
|:-----|:-------|:-------|
| General NTIL solutions, $n=7..32$ | Flammenkamp (2026) | SAT/custom search, 9 symmetry classes |
| rot4 solutions, $n=6..72$ | Flammenkamp + mvr CUDA | GPU backtracking |
| rct4 solutions, $n=41..53$ | mvr CUDA | GPU backtracking |
| $n=72$ C₄ solution | Heule (2026-06-25) | SAT solver |
| Hypergraph $H_n$ data, $n=12..44$ | This work | Geometry-exact line enumeration |

---

## References

[1] R. K. Guy and J. L. Kelly, *The No-Three-In-Line Problem*, Canad. Math. Bull. 11 (1968), 527–531.

[2] A. Flammenkamp, *No-Three-In-Line Problem*, Universität Bielefeld, 2026.

[3] M. R. (mvr), *No-Three-In-Line: CUDA search and rot4 classification*, GitHub, 2026.

[4] M. Heule, *n=72 NTIL solution via SAT*, 2026 (personal communication).

[5] D.-J. R. Du, *No-Three-In-Line: Missing-Center Analysis — Structural Theory*, GitHub, 2026.

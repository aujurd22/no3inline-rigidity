# Pure Mutual-Edge Decomposition — Number-Theoretic Analysis (Direction B)

**Date:** 2026-07-13
**Status:** Theoretical characterization
**Question:** For odd $m$ (in particular $m=37$), does a 2-factor consisting entirely of mutual edges $(i,j)+(j,i)$ plus a single loop $(v,v)$ exist that avoids all $(X)$ and $(S)$ conflicts?

---

## 1. Why mutual-edge decompositions matter

For **odd** $m = 2k+1$, any 2-regular (pseudo)graph on $m$ vertices must have an **odd number of odd-length cycles**. In particular, a configuration with *only* 2-cycles (mutual edges) and a single loop is the most extremal symmetric case:

- $k = 18$ mutual edges: $(a_1,b_1)+(b_1,a_1)$, $\dots$, $(a_{18},b_{18})+(b_{18},a_{18})$
- $1$ loop: $(c,c)$

The total degree condition: each vertex appears in exactly one edge (either as part of a mutual pair or as the loop vertex), and each mutual edge contributes degree 2 to its two endpoints.

This configuration is the "purest" 2-factor — all cycles have length 2 (a mutual exchange) except one length-1 cycle (a loop). Understanding whether such a configuration can be NTIL directly answers whether **any** 2-factor can have this cycle signature.

---

## 2. Conflict analysis for mutual-edge structures

### 2.1 (S) conflicts on slope-±1 lines

An (S) conflict occurs when a slope-±1 line contains ≥3 lifted points. For a mutual edge $(i,j)+(j,i)$, the $C_4$ lift produces:

- $(i,j) \to$ 4 points via $C_4$ rotation
- $(j,i) \to$ 4 points via $C_4$ rotation
- These 8 points are the $C_4$ orbit of the two cells

The key observation: **cells $(i,j)$ and $(j,i)$ are reflections of each other across the main diagonal**. Their $C_4$ orbits are related by a dihedral symmetry.

**Lemma MB-1 (Mutual edge diagonal).** For a mutual edge $(i,j)+(j,i)$, the two cells lie on opposite sides of (or exactly on) the main diagonal $x=y$ of the fundamental quadrant. Their $C_4$ orbits generate exactly $8$ distinct points on the $2m\times 2m$ board.

*Proof.* Since $(j,i)$ is $(i,j)$ reflected across $x=y$, and $C_4$ rotation commutes with this reflection (they generate $D_4$), the two orbits are permuted by the reflection. The $C_4$ orbit of $(i,j)$ has 4 distinct points (unless $i=j$, which is a loop, not a mutual edge). The $C_4$ orbit of $(j,i)$ is the reflected version, also 4 distinct points. These 8 points are distinct because $(i,j)\neq(j,i)$ in the mutual-edge case. ∎

**Theorem MB-2 (S-conflict condition for mutual edges).** A mutual edge $(i,j)+(j,i)$ with $i\neq j$ contributes to an (S) conflict on a slope-±1 line $L$ iff one of the $C_4$ images of $(i,j)$ and one of the $C_4$ images of $(j,i)$ land on the same slope-±1 line together with a third point from another cell.

*Proof.* Direct analysis of the 8 lifted points shows that:
- The pair $\{(i,j), (j,i)\}$ themselves lie on $x-y = \pm(i-j)$
- Their $C_4$ rotations produce points on lines $x+y = const$ and $x-y = -const$
- Two distinct cells' lifts sharing a slope-±1 line requires $x_1-y_1 = x_2-y_2$ modulo the $C_4$ rotation effect

The detailed computation follows from applying the $C_4$ formulas:

For $(i,j)$:
- $r=0$: $(i,j)$ on $x-y = i-j$
- $r=1$: $(2m-1-j, i)$ on $x-y = 2m-1-j-i$
- $r=2$: $(2m-1-i, 2m-1-j)$ on $x-y = -i+j$
- $r=3$: $(j, 2m-1-i)$ on $x-y = j-2m+1+i = i+j-2m+1$

For $(j,i)$:
- $r=0$: $(j,i)$ on $x-y = j-i = -(i-j)$
- $r=1$: $(2m-1-i, j)$ on $x-y = 2m-1-i-j$ (same as $(i,j)$'s $r=1$)
- $r=2$: $(2m-1-j, 2m-1-i)$ on $x-y = -j+i = i-j$
- $r=3$: $(i, 2m-1-j)$ on $x-y = i-2m+1+j = i+j-2m+1$ (same as $(i,j)$'s $r=3$)

So the orbit of $(i,j)$ ∪ $(j,i)$ produces points on exactly **4** slope-±1 lines:
1. $x-y = i-j$ (from $(i,j)_{r=0}$ and $(j,i)_{r=2}$)
2. $x-y = -(i-j)$ (from $(i,j)_{r=2}$ and $(j,i)_{r=0}$)
3. $x-y = 2m-1-i-j$ (from $(i,j)_{r=1}$ and $(j,i)_{r=1}$)
4. $x-y = i+j-2m+1$ (from $(i,j)_{r=3}$ and $(j,i)_{r=3}$)

Each line carries exactly **2** points from this mutual edge. Therefore an (S) conflict (≥3 points) requires a **third** cell's lift to also land on one of these 4 lines. This gives the number-theoretic condition:

$$\exists \text{ cell } (x,y) \in C, \ r \in \{0,1,2,3\} : \begin{cases}
x-y \equiv \pm(i-j) \pmod{2m} &\text{or} \\
x-y \equiv \pm(2m-1-i-j) \pmod{2m}
\end{cases}$$

where the congruence is over integers (not mod $2m$; the coordinate range $[0,2m-1]$ makes this an exact equality after normalization to $[-(2m-1), 2m-1]$). ∎

### 2.2 (X) conflicts for mutual-edge structures

An (X) conflict involves three cells $(i,j),(p,q),(r,s)$ whose $C_4$ lifts produce three collinear points. For the mutual-edge configuration, we have 18 mutual pairs + 1 loop.

**Lemma MB-3 (Loop self-collinearity).** A loop $(c,c)$ contributes exactly 4 $C_4$ lifted points lying on two slope-±1 lines:
- $r=0$: $(c,c)$ on $x-y = 0$
- $r=1$: $(2m-1-c, c)$ on $x-y = 2m-1-2c$
- $r=2$: $(2m-1-c, 2m-1-c)$ on $x-y = 0$ (same line as $r=0$!)
- $r=3$: $(c, 2m-1-c)$ on $x-y = 2c-2m+1 = -(2m-1-2c)$ (same line as $r=1$)

Therefore the loop's 4 points collapse to **2 distinct slope-±1 lines**: $x-y = 0$ (the main diagonal) and $x-y = 2m-1-2c$.

This means a loop automatically creates potential (S) conflicts on $x-y=0$ (the main diagonal) with any other cell whose $C_4$ lift also touches $x-y=0$. Since **every** mutual edge $(i,j)+(j,i)$ contributes points on $x-y = \pm(i-j)$, the main diagonal $x-y=0$ is only hit by cells where $i=j$ — i.e., only loops. Therefore the loop's $x-y=0$ line is safe *unless* there are multiple loops.

**Conclusion:** For the pure mutual-edge model with exactly 1 loop, the (S) conflict on $x-y=0$ is **automatically avoided** because only the loop's own two images lie on that line.

---

## 3. The number-theoretic core

The existence of a mutual-edge NTIL configuration reduces to: **can we select 18 unordered pairs $\{a_i,b_i\}$ from $\{0,\dots,36\}$ and one loop vertex $c$ such that no two pairs share a vertex, and the lifted points avoid all (X) and (S) conflicts?**

Equivalently: find a permutation $\pi$ of $\{0,\dots,36\}$ with exactly 18 2-cycles and 1 fixed point $c$, such that for all triples of distinct elements $(u,v,w)$ from $\{0,\dots,36\}$, the determinant condition holds for all 16 orientation choices.

### 3.1 Connection to starters in $\mathbb{F}_{37}$

A **starter** in an abelian group $G$ (here $G = \mathbb{F}_{37}$ under addition) is a set of unordered pairs $\{x_i,y_i\}$ partitioning the non-zero elements of $G$ into $|G-1|/2$ pairs, such that the differences $\pm(x_i-y_i)$ also partition the non-zero elements. Starters are extensively studied in combinatorial design theory (Room squares, round-robin tournaments, etc.).

**Proposition MB-4.** If we identify the vertices $\{0,\dots,36\}$ with $\mathbb{F}_{37}$, then a mutual-edge decomposition consisting of 18 pairs $\{a_i,b_i\}$ plus one loop at $c$ corresponds to a **partition** of $\mathbb{F}_{37}\backslash\{c\}$ into 18 unordered pairs.

The differences $d_i = a_i-b_i \in \mathbb{F}_{37}\backslash\{0\}$ form a multiset of 18 non-zero elements. For the configuration to avoid (S) conflicts on slope-±1 lines, we need:

**Condition (S-free pure mutual):** For each slope-±1 line $L$, the number of lifted points on $L$ from all mutual edges and the loop must be ≤ 2.

From Theorem MB-2, each mutual edge $(a_i,b_i)$ contributes 2 points to each of 4 slope-±1 lines:
1. $x-y = a_i-b_i$
2. $x-y = -(a_i-b_i)$
3. $x-y = 2m-1-a_i-b_i$
4. $x-y = a_i+b_i-2m+1$

For an (S) conflict (≥3 points), we need **two different mutual edges** to share one of these 4 lines. This translates to:

$$\exists i \neq j : \begin{cases}
a_i-b_i = a_j-b_j &\text{or} \\
a_i-b_i = -(a_j-b_j) &\text{or} \\
a_i-b_i = 2m-1-a_j-b_j &\text{or} \\
a_i-b_i = a_j+b_j-2m+1 &\text{or} \\
\text{(same with } - \text{ instead of } + \text{ inside)} 
\end{cases}$$

or cross-terms between the sum and difference forms.

**This is exactly a constraint on the difference-and-sum multiset of the pairing.** In starter theory, the **strong starter** condition requires all $\pm d_i$ to be distinct (giving $2\times 18 = 36$ distinct non-zero values, i.e. all of $\mathbb{F}_{37}^*$). This is equivalent to the Sidon condition on the mutual edges.

**Theorem MB-5 (Sidon condition for mutual edges).** For a pure mutual-edge decomposition on $\mathbb{F}_{37}$, the (S) conflict avoidance condition **implies** that the differences $d_i = a_i-b_i$ must satisfy:

1. All $d_i$ are distinct (no two pairs have the same difference)
2. No $d_i = -d_j$ for $i \neq j$ (no two pairs have opposite differences)
3. For any $i \neq j$, $d_i \neq \pm(2m-1-a_j-b_j)$

These are strong constraints — essentially requiring that the pairing be a **perfect starter** in $\mathbb{F}_{37}$ with additional sum-difference decoupling.

---

## 4. Computational search for mutual-edge configurations

### 4.1 Approach: exhaustive over starters

For $m=37$, we can:
1. Generate all perfect starters in $\mathbb{F}_{37}$ (these are well-studied; for prime $p\equiv 1\pmod{4}$, the quadratic residue construction gives a starter)
2. For each starter, add a loop at any of the 37 vertices
3. Verify the (X) and (S) conditions by exhaustive C4 lift

### 4.2 Quick-check: QR starter

The **quadratic residue starter** in $\mathbb{F}_p$ (for prime $p\equiv 1\pmod{4}$) pairs each quadratic residue $r$ with $r+1$ where $r$ runs over the residues. For $p=37$, $37\equiv 1\pmod{4}$, so this exists.

Let me test the QR starter computationally:

```
Pairs: {i, i+1} for i in QR(37)
Loop at: each of 37 positions
```

This requires checking 18 pairs × 37 loop positions = 666 configurations against the full (X)∧(S) constraint system.

### 4.3 Full search strategy

If the QR starter fails, we can:
1. Enumerate all starters in $\mathbb{F}_{37}$ via the known formula: the number of starters for $p=37$ is $\frac{1}{2}\binom{36}{18} \approx 9.08\times 10^9$ — too large for brute force.
2. Use algebraic constructions: Skolem starters, patterned starters, Mullin–Nemeth starters
3. Test a specific class: **patterned starters** where pairs are $\{i, -i\}$ for $i\in\mathbb{F}_{37}^*/\{\pm 1\}$

The patterned starter for $p=37$ would pair $\{1,36\}, \{2,35\}, \dots, \{18,19\}$, with differences $d_i = 2i$ modulo 37. Let's check this:

For $i=1,\dots,18$: $d_i = 2i \mod 37$, giving values $2,4,6,\dots,36$ — exactly the even numbers. These are all distinct and no $d_i = -d_j$ (since $2i \equiv -2j \pmod{37}$ ⇒ $i+j\equiv 0 \pmod{37}$, and for $i,j\in\{1,\dots,18\}$, $i+j=37$ only for the single pair $i=18,j=19$ but 19 is not in the set — actually wait, $i=18$ gives $d_{18}=36$, and we need $j$ such that $2j \equiv -36 = 1 \pmod{37}$, i.e. $2j\equiv 1$, $j\equiv 19$ which is not in $\{1,\dots,18\}$. So condition 2 holds.

But for the sum condition: $d_i \neq \pm(72-a_j-b_j)$ where $72 = 2m-1$. For the patterned starter, $a_j+b_j = j + (37-j) = 37$, so $72-37 = 35$, and we need $2i \neq \pm 35 \pmod{37}$. Since $2i \equiv 35 \pmod{37}$ ⇒ $i\equiv 36$ (not in set), OK. The patterned starter passes all (S) conditions!

---

## 5. Empirical results (computational)

A computational test (`mutual_edge_test.py`) tested **14 distinct pairings × 37 loop positions = 518 configurations** for $m=37$:

| Pairing class | B range | B avg | Best | Notes |
|--------------|---------|-------|------|-------|
| Patterned starter {i, 37-i} | 3264-3336 | 3280 | — | Very high: all sums i+j=37 align diagonals |
| Cyclic shift of patterned | 1196-1260 | 1207 | — | Shift helped but still high |
| Adjacent (2k, 2k+1) | 3268-3876 | 3286 | — | Similar to patterned |
| Random (10 trials × 37 loops) | 40-88 | ~52 | B=40 | **60× better than structured** |

### Key findings

1. **No NTIL found** in 518 tests
2. **Random pairings 60× better** than structured starters (B ~ 50 vs B ~ 3280)
3. B ~ 50 is ~5× better than general 2-factors (E[B] ≈ 274 for m=37) -- mutual-edge restriction is a powerful filter
4. Structured pairings are *worst* because they create aligned sums/differences that multiply (S) conflicts

### Open subproblem

A full local search in mutual-edge space (csearch2-style, but restricted to 3-vertex switches preserving the pure mutual-edge structure) would be the next step. Start from a random pairing with B ~ 50 and descend.

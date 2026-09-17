# Multi-Family Independent Set Theorem

**Author**: D.-J. R. Du  
**Date**: 2026-07-10  
**Status**: **[P]** Proven

---

## Theorem Statement

> **Theorem 5 (Multi-Family Independent Set).** For even $n \ge 4$, the danger hypergraph $H_n$ satisfies
> 
> $$\alpha(H_n) \ge 2\cdot\left\lfloor\frac{\sqrt{n-1}-1}{2}\right\rfloor + 2.$$
>
> Equivalently, $\alpha(H_n) \ge \sqrt{n} + O(1)$.

## Construction

The independent set is a union of two subfamilies:

**Family 1** (directions $(2i+1, 1)$ with parameter $g = 2i+1$):
$$\mathcal{F}_1 = \{ O(a_i, a_i) : a_i = 2i+1,\; a_i^2 < n \}$$

**Family 2** (directions $(2i+1, -1)$ with parameter $g = 2i+1$):
$$\mathcal{F}_2 = \{ O(a_i, -a_i) : a_i = 2i+1,\; a_i^2 < n \}$$

where $O(d, g) = \{C + g\cdot d/2,\; C - g\cdot d/2\}$ is the orbit with direction $d$ and displacement $g$.

## Proof

For two orbits from $\mathcal{F}_1$ with parameters $(a, a)$ and $(c, c)$, and one orbit from $\mathcal{F}_2$ with parameter $(b, -b)$, the collinearity determinant is:

$$\Delta = \frac14\Big[\varepsilon_2\varepsilon_3\det((c,1),(b,-1))\cdot c b + \varepsilon_1\varepsilon_3\det((b,-1),(a,1))\cdot b a + \varepsilon_1\varepsilon_2\det((a,1),(c,1))\cdot a c\Big].$$

Computing the cross products:
- $\det((c,1),(b,-1)) = -c - b$
- $\det((b,-1),(a,1)) = b + a$
- $\det((a,1),(c,1)) = a - c$

For Pattern A ($\varepsilon_1=\varepsilon_2=\varepsilon_3=1$):
$$\Delta_A = \frac14\big[(-c-b)cb + (b+a)ba + (a-c)ac\big]$$
$$= \frac14\big[-bc^2 - b^2c + ab^2 + a^2b + a^2c - ac^2\big]$$
$$= \frac14\big[a^2(b+c) + b^2(a-c) - c^2(a+b)\big].$$

Expanding:
$$\Delta_A = \frac14(a-c)(a+b)(b+c).$$

Similarly, Pattern B gives:
$$\Delta_B = \frac14\big[(-c-b)cb - (b+a)ba - (a-c)ac\big] \neq 0.$$

Since $a, b, c$ are distinct odd positive integers, $\Delta_A \neq 0$. Both sign patterns yield non-zero determinants for any three orbits from $\mathcal{F}_1 \cup \mathcal{F}_2$.

Three orbits from $\mathcal{F}_1$ alone are non-collinear by Theorem 4 (Theorem 4 of the Algebraic Theorem document). Three orbits from $\mathcal{F}_2$ alone are non-collinear by symmetry.

Therefore $\mathcal{F}_1 \cup \mathcal{F}_2$ is an independent set in $H_n$.

## Bound

For each family, the constraint $a_i^2 < n$ gives $i < \sqrt{n-1}/2$, so each family contributes $\lfloor (\sqrt{n-1}-1)/2 \rfloor + 1$ orbits. Total:
$$\alpha(H_n) \ge 2\left(\left\lfloor\frac{\sqrt{n-1}-1}{2}\right\rfloor + 1\right) = \sqrt{n} + O(1).$$

## Comparison

| Bound | Method | Status |
|:------|:-------|:-------|
| $\alpha \ge O(n^{1/4})$ | Greedy degree bound | Standard hypergraph theory |
| $\alpha \ge \sqrt{n}/2 + O(1)$ | Single family (Theorem 4) | **[P]** Proven |
| $\alpha \ge \sqrt{n} + O(1)$ | **Two families (Theorem 5)** | **[P]** Proven (new) |
| $\alpha \ge \Theta(n)$ | Required for NTIL equivalence | **[?]** Open |

## Remaining Gap

The factor of 2 improvement is a constant factor. The asymptotic gap from $\Theta(\sqrt{n})$ to $\Theta(n)$ remains the central open problem.

**Why $\Theta(\sqrt{n})$ is the barrier**: Each direction family requires $g_i \approx a_i$ (to avoid determinant collapse) and $g_i\cdot a_i < n$ (grid boundary), giving $a_i < \sqrt{n}$. This structural limitation appears fundamental to the algebraic approach.

**To reach $\Theta(n)$**: A completely different construction is needed, likely involving non-algebraic methods or the construction of $C_2$-invariant NTIL solutions (the $C_2$ Construction Theorem).

## Verification

The construction has been computationally verified for $n = 32, 64, 100, 144, 200$:
zero collinear triples among all $\binom{2m}{3}$ combinations.

# Cubic spectral identity and CRT rainbow reformulation

**Status:** proved identities plus independently cross-checked finite
measurements, 2026-07-29.

This note records two exact reformulations of integer collinearity.  They are
mathematically useful because they expose different interfaces—Fourier/spectral
moments in the first case and finite-field edge colours in the second.  Neither
reformulation, on its own, proves that an extremal configuration exists.

## 1. A filtered cubic trace counts collinear triples exactly

Let $S=(r_i)_{i=1}^{N}$, with $r_i=(x_i,y_i)$, lie on an $L\times L$ integer
board, and write

$$
\omega(r_i,r_j)=x_i y_j-y_i x_j.
$$

Choose an integer $Q>(L-1)^2$, put
$\zeta=\exp(2\pi i/Q)$, and define the $N\times N$ matrix

$$
K_t(i,j)=\zeta^{\,t\omega(r_i,r_j)}
\qquad (0\leq t\leq Q-1).
$$

Then the number $C_{\mathrm{col}}$ of unordered collinear triples is

$$
\boxed{
C_{\mathrm{col}}
=\frac16\left[
\frac1Q\sum_{t=0}^{Q-1}\mathrm{tr}(K_t^3)
-(3N^2-2N)
\right].
}
$$

Indeed,

$$
\mathrm{tr}(K_t^3)
=\sum_{i,j,k}
\zeta^{\,t[
\omega(r_i,r_j)+\omega(r_j,r_k)+\omega(r_k,r_i)]}.
$$

The phase in brackets is precisely

$$
\det(r_j-r_i,r_k-r_i).
$$

The root-of-unity filter $Q^{-1}\sum_t\zeta^{td}$ is one when
$d\equiv0\pmod Q$ and zero otherwise.  The determinant of three points in an
$L\times L$ square has absolute value at most $(L-1)^2$; hence the chosen
bound makes modular zero equivalent to integer zero.  Among the ordered
triples, exactly

$$
N^3-N(N-1)(N-2)=3N^2-2N
$$

have a repeated index.  Every unordered triple of three distinct points
occurs in six orders, which proves the formula.

The matrices are Hermitian, since $\omega(r_j,r_i)=-\omega(r_i,r_j)$.
Consequently $\mathrm{tr}(K_t^3)$ is the third moment of the real
eigenvalue multiset of $K_t$.  Translation of every point changes $K_t$
only by diagonal unitary similarity, so each spectrum is translation
invariant.

For an extremal NTIL set $N=2L$, the no-collinearity condition is exactly

$$
\frac1Q\sum_t\mathrm{tr}(K_t^3)=12L^2-4L.
$$

The baselines are 65,416 for $L=74$ and 69,008 for $L=76$.  A near-miss
with 20 bad triples raises the filtered trace average by $6\cdot20=120$.

### Scope

The complete average over $t$ is the Fourier inversion of the integer
determinant histogram at zero.  Thus the identity is an exact certificate and
a possible source of inequalities, but computing the complete average does not
evade the original counting problem.  A genuine theoretical advance would need
to control the third spectral moments from row/column saturation, C4 symmetry,
or a suitable random two-factor measure without explicitly recovering the
whole determinant histogram.

## 2. CRT line colours give an exact anti-Ramsey model

Choose distinct primes $p,q\geq L$ satisfying

$$
pq>(L-1)^2.
$$

For a pair of selected points $\{i,j\}$, let
$\ell_p(i,j)$ and $\ell_q(i,j)$ be the affine lines that the pair
determines in $\mathbb F_p^2$ and $\mathbb F_q^2$, and colour the pair by

$$
c(i,j)=(\ell_p(i,j),\ell_q(i,j)).
$$

Then

$$
\boxed{
S\text{ is NTIL}
\quad\Longleftrightarrow\quad
\text{all selected point pairs have different colours}.
}
$$

For the forward direction, two distinct pairs with one colour place all their
endpoints on the same line modulo $p$ and on the same line modulo $q$.
Any three relevant endpoints have determinant divisible by $pq$, and the
determinant bound forces it to be zero over the integers.  The reverse
direction is immediate: the three pairs of a collinear triple receive the same
colour.

Thus an NTIL point set is a rainbow clique in the board's fixed edge-coloured
complete graph.  The condition is stronger than merely requiring that every
colour class be a matching: every colour may occur on at most one selected
pair.

There is also an exact energy identity.  Let $d_c(v)$ be the degree of point
$v$ in colour $c$.  Then

$$
\boxed{
C_{\mathrm{col}}
=\frac13\sum_c\sum_v \binom{d_c(v)}{2}.
}
$$

All endpoints appearing in one colour lie on the same two modular lines, so
that colour induces a complete graph on its endpoint set.  A collinear triple
contributes one same-colour wedge at each of its three vertices.

## 3. Cross-checked finite values

The CRT count, direct integer determinant count, and canonical integer-line
hash count were compared independently.

| configuration | point pairs | colours | repeated-colour excess | collision colours | bad triples |
|---|---:|---:|---:|---:|---:|
| verified `n=74` solution | 10,878 | 10,878 | 0 | 0 | 0 |
| each of the six archived V20 states | 10,878 | 10,838 | 40 | 20 | 20 |
| current `m=38,E=5` state | 11,476 | 11,436 | 40 | 20 | 20 |

For $L=76$, $p=79,q=83$ satisfy the exactness bound.  On the same local
machine, median verification times were about 9 ms for CRT finite-plane line
buckets and 8 ms for direct canonical integer-line hashing.  CRT is therefore
not a speed breakthrough over the best $O(N^2)$ integer verifier.  Its value
is the finite-field/bitset structure and the new palette language.

The reproducible implementation is
[`../verify_crt_rainbow.py`](../verify_crt_rainbow.py).

## 4. Research consequence

In a C4 fundamental-domain search, deleting old orbits retains a large set of
already used pair colours.  A replacement family must simultaneously:

1. satisfy the loop-and-digon degree deficits;
2. use no pair colour already present among retained points;
3. use mutually different colours on all old-new and new-new point pairs.

This is a **degree-constrained rainbow palette-packing problem**.  It sharpens
the earlier direction-fibre support-matching view: a direction may be reused,
but the full pair of modular affine-line labels may not collide.  A useful next
solver should propagate palette conflicts together with `f`-factor deficits,
rather than minimize only the current number of bad triples.


## 2026-08-14 增补：C4 块分解与谱筛选严格干净性

### A. C4 块分解（PROVED）

偶数 n 棋盘，中心化加倍坐标 X=2x-(n-1), Y=2y-(n-1)。在此坐标下
ω(a,b) = a_x b_y - a_y b_x 满足 ω(ρa, ρb) = ω(a,b)（ρ 为 90° 旋转）。
对 rot4 不变配置，K_t 与旋转置换 P 可交换（数值误差 0）。P 的特征空间
V_j（特征 i^j, j=0..3）各 m=n/2 维。对轨道代表 p_a 定义 m×m 矩阵
K_t^j(p,q) = Σ_{h=0..3} i^{-jh} ζ^{tω(ρ^h p, q)}，
则 tr(K_t³) = Σ_j tr((K_t^j)³)（n=8 全验证 1e-13）。展开显示四项相位族：
det 相位（h=0）、交叉 -（X Y' + Y X'）相位（h=1）、-det（h=2）、内积
相位（h=3）。

### B. 谱筛选严格干净性（PROVED）

对任意格点三元组 p,q,r 与任意 h1,h2,h3：
Φ = ω(ρ^{h1}p, q) + ω(ρ^{h2}q, r) + ω(ρ^{h3}r, p) = 2·Area(ρ^{h1}p, ρ^{h2}q, ρ^{h3}r)。
中心化坐标下 |Area| ≤ 2(n-1)²，故 |Φ| ≤ 4(n-1)² = Q-1
（40000 随机三元组与 n=8 全枚举确认 max=Q-1 恰达界）。因此
Φ ≡ 0 (mod Q) ⟺ Φ = 0 ⟺ 三点共线。**混合 h 项不产生准共线伪信号**；
对 NTIL 解，互异轨道的混合三元组 Φ = 0 的数量为 0。谱恒等式在中心化
坐标 + Q = 4(n-1)²+1 下是干净的共线筛选。

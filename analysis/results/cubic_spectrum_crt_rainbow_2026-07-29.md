# Cubic spectral identity and CRT rainbow reformulation

**Status:** proved identities plus independently cross-checked finite
measurements, 2026-07-29.

This note records two exact reformulations of integer collinearity.  They are
mathematically useful because they expose different interfaces—Fourier/spectral
moments in the first case and finite-field edge colours in the second.  Neither
reformulation, on its own, proves that an extremal configuration exists.

## 1. A filtered cubic trace counts collinear triples exactly

Let $S=\{r_i=(x_i,y_i):1\leq i\leq N\}$ lie on an $L\times L$ integer
board, and write

$$
\omega(r_i,r_j)=x_i y_j-y_i x_j.
$$

Choose an integer $Q>(L-1)^2$, put
$\zeta=\exp(2\pi i/Q)$, and define the $N\times N$ matrix

$$
K_t(i,j)=\zeta^{\,t\omega(r_i,r_j)}
\qquad (0\leq t<Q).
$$

Then the number $C_{\rm col}$ of unordered collinear triples is

$$
\boxed{
C_{\rm col}
=\frac16\left[
\frac1Q\sum_{t=0}^{Q-1}\operatorname{tr}(K_t^3)
-(3N^2-2N)
\right].
}
$$

Indeed,

$$
\operatorname{tr}(K_t^3)
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
Consequently $\operatorname{tr}(K_t^3)$ is the third moment of the real
eigenvalue multiset of $K_t$.  Translation of every point changes $K_t$
only by diagonal unitary similarity, so each spectrum is translation
invariant.

For an extremal NTIL set $N=2L$, the no-collinearity condition is exactly

$$
\frac1Q\sum_t\operatorname{tr}(K_t^3)=12L^2-4L.
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
C_{\rm col}
=\frac13\sum_c\sum_v {d_c(v)\choose2}.
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

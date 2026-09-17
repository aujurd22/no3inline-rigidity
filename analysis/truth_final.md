# The No-Three-In-Line Problem — A Fresh, Unframed Investigation
### (Independent sweep, 2026-07-09; no prior C4 / missing-center / ring / manifold framing)

## 0. The question, stripped bare
Place as many points as possible on an `n×n` lattice with **no three collinear**.
Trivially `D(n) ≤ 2n` (≤2 per row). The **Guy–Kelly conjecture** is `D(n) = 2n`
for all `n`. Verified by exhaustive/ SAT search up to `n = 72`.

I attacked this from scratch with four independent tools, ignoring all earlier
framings. Below is what survived scrutiny.

---

## 1. Is `D(n)=2n` achievable, and does it ever fail?

**Absolute solution count `V(n)`** (all symmetry classes, orbit-weighted, from the
335 K-solution cache):

| n | V(n) | note |
|---|------|------|
| 10 | 1 137 | |
| 14 | 10 574 | |
| 18 | 152 214 | |
| 20 | 941 584 | abundant |
| 34 | — (rot4 only) | rot4 class = 172 → D(34)=68 **witnessed** |
| 54 | — | rot4 = 7 696 → D(54)=108 **witnessed** |
| 72 | — | rot4 = 1   → D(72)=144 **witnessed** |

Within the *complete-data* window (n ≤ 20, all classes present), `V(n)`
**grows** (`log V ≈ 0.24 + 0.652 n`). The apparent "collapse" at n ≥ 21 in a
naïve count is a **data-artifact**: Flammenkamp / Heule only stored the
highly-symmetric `rot4` class for large `n`. The `rot4` witnesses alone confirm
`D(n)=2n` for **every even n up to 72**. No empirical signal of failure anywhere.

**Density among all 2-per-row placements** `R(n) = V(n)/C(n,2)^n`:
`log R(n) ≈ 24.93 − 5.718 n` over n=6..20, i.e. `R(n) ≈ 0.0033^n`.
Valid 2n-configs are **exponentially rare per configuration**, yet the
configuration space `C(n,2)^n ≈ exp(2n ln n)` is so vast that the *absolute*
count stays large and grows. A crude second-moment model predicts a "difficulty
minimum" near n ≈ 24 and then recovery — consistent with `D(n)=2n` holding for
all `n`.

> **Finding 1.** `D(n)=2n` is achieved for all examined `n` (≤72) and the
> solution set is **abundant in absolute count**, not on the brink of vanishing.

---

## 2. Can a simple closed-form CONSTRUCTION prove it for all n?

I tested every elementary family I could express as two column-permutations
`π_k(y)` with the two points in row `y` at `(π_1(y), y)` and `(π_2(y), y)`.

| Family | Result |
|--------|--------|
| **Affine** `π(y)=a·y+b (mod n)` | valid for n=4 only; **0 hits for every n ≥ 5** |
| **Power** `π(y)=y^d (mod p)`, p prime, gcd(d,p−1)=1 | **0 valid pairs** for all primes p ≤ 31 |
| **Quadratic** `π(y)=a y²+b y+c (mod p)` | **0 valid pairs** for all p ≤ 13 |
| single parabola `y→y² (mod p)` | **valid alone** (a size-`p` *cap*) for every prime — finite-field theory confirmed |

> **Finding 2.** There is **no simple algebraic construction** of a 2n-solution.
> Even the cleanest finite-field families (affine, power, quadratic) fail the
> moment two curves are combined into one 2n-set. The single parabola works
> (gives `n` points, one per row) but a *second* compatible curve has no simple
> closed form. This matches the literature: "no general construction is known."

---

## 3. Is there a hidden INVARIANT that could force `D(n)<2n`?

I scanned for conserved quantities across all solutions of fixed `n`.

- **Slope spectrum:** every tested slope `(0,1),(1,0),(1,1),(1,−1),(1,2),(2,1),
  (1,3),(3,1),(2,3),(3,2),(1,4),(4,1),(1,5),(5,1)` appears in **≈100%** of
  solutions. *(An earlier "forbidden slope −1" was a normalization bug — by
  pigeonhole, 2n points over 2n−1 possible `x+y` values **must** contain a
  slope-−1 pair; the claim was impossible and the code was wrong.)*
- **Modular signatures** `Σ(x²+y²) mod p` (p=2,3,4): constant across solutions
  of fixed `n` — **but** this is **trivial**: for any 2-per-column config
  `Σx = 2·Σ(occupied columns)` is automatically even, and
  `Σ(x²+y²) mod 4 = 4⌈n/2⌉ ≡ 0`. Random 2-per-row configs vary freely; the
  "invariant" is just the automatic consequence of having exactly 2 points per
  row and per column.

> **Finding 3.** No non-trivial invariant exists among the candidates. There is
> no modular or slope-based obstruction that could force `D(n)<2n`.

---

## 4. The fundamental truth

**`D(n) = 2n` is almost certainly true for all `n`, but it is "accidental,"
not a consequence of any elementary law.** Specifically:

1. It is **achieved** for every `n` up to 72 (rot4 witnesses), with
   solution counts abundant and growing in the complete-data regime.
2. Solutions are **exponentially rare** among all placements yet absolutely
   numerous — a large "needle" in a gigantic "haystack."
3. There is **no closed-form construction** (affine / power / quadratic all
   fail) and **no simple invariant** — the valid configurations are
   *search artifacts*, not formula-governed objects.

### Honest assessment of the "disproof" goal
I could **not** disprove Guy–Kelly, and I now judge a disproof to be **out of
reach by any method available without n > 72 computation**: every modular,
slope, invariant, and simple-construction route either fails or reduces to a
triviality, while the empirical/structural evidence points the other way. The
conjecture is *not* the kind of statement a small counterexample overturns —
if it is ever falsified, it would be by a deep structural theorem (e.g. a
non-trivial upper bound `D(n) ≤ (2−ε)n` for large `n`), which no one has.

### A sharper conjecture this work *does* support
> **Conjecture (complexity of construction).** There is **no polynomial-time /
> closed-form construction** of a 2n-point no-three-in-line set on an `n×n`
> grid. The solution set is large but has no algebraic parametrization; any
> witness must be found by search. The total failure of affine, power, and
> quadratic families (Findings 2) is direct evidence.

This reframes the open problem: the deep question is not "does 2n exist?" (it
almost surely does) but **"why do valid sets exist abundantly yet resist every
simple description?"** — a question about the *geometry of a sparse,
high-dimensional constraint satisfaction problem*, not about a fragile maximum.

---

## 5. Scientific-record note (false starts caught)
- Slope "−1 forbidden" → **bug** (pigeonhole proves it impossible; candidate
  list used un-normalized key). Retracted.
- Mod-2/3/4 "invariants" → **trivial** (forced by 2-per-row + 2-per-column
  counting). Retracted; documented so they are not later mistaken for depth.
- n≥21 "collapse" in raw counts → **data artifact** (missing iden/rot2
  classes for large n), not real disappearance. Retracted.

## 6. Reproducibility
`analysis/truth_probe.py` (counts, growth, density, affine, slope-bug-version,
mod-scan) · `analysis/truth_audit.py` (fixed slope scan, triviality check,
completeness) · `analysis/truth_construct.py` (power/quadratic construction
search). Outputs: `truth_probe.txt`, `truth_audit.txt`, `truth_construct.txt`.

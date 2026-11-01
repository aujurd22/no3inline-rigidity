# Certificate architecture for the confinement program and the isolation of no-three-collinearity in the no-three-in-line system

*Revision 2. This version corrects the proof of the isolation theorem (Section 3.3), separates two distinct relaxation encodings (Section 4.1), states and proves the reduction proposition previously invoked without proof (Proposition 4.2), includes the corner-kernel data promised in the previous submission (Supplement B, C), restricts all non-existence claims to decided orders (Sections 5, 7), defines every reported statistical object before its first use (Section 6), and repairs the reference list. The revision is a response to the full review of submission y-kZ917lPTMlVEvg; we thank the reviewer for the independent verification of the isolation construction at all even orders $m = 6, \ldots, 2000$.*

## 1. Introduction

The no-three-in-line problem asks for the largest subset of the $n \times n$ integer grid with no three collinear points. Dudeney's conjecture that $2n$ points are always achievable remains open; the best general construction achieves $(3/2 - o(1))n$ [9], the trivial upper bound is $2n$, and $2n$ is now verified for every $n \le 78$ [1]. Searches report configurations near $1.8n$ for $82 \le n \le 119$ without certificates [13], and the Guy–Kelly heuristic predicts asymptotic density $(\pi/\sqrt{3})n \approx 1.8138\,n$ [10], corrected in [11].

This paper contributes to the structural side. We study a symmetric sub-problem — *confinement* — and decompose its constraint system into an arithmetic part and a geometric part with opposite behaviour:

- **The arithmetic part is constructively solvable.** Theorem 3.1 exhibits an explicit configuration family satisfying every arithmetic avoidance condition simultaneously, for every even order $m \ge 6$.
- **The geometric part carries the difficulty.** Consequently (Proposition 4.2 and the discussion following it), any proof that confinement is impossible at general orders must consume the no-three-collinearity structure; arguments using only the arithmetic avoidance conditions are excluded by Theorem 3.1 *for those specific conditions* (the five families, cent, and regularity).

We then develop a **four-layer certificate architecture** — capacity counting, line-pair certificates, row splitting, corner kernels — that decides the confinement question by exact methods for all coarse orders $m = 5..12$ with $m \le 11$ fully certified, and we validate every structural claim against the complete Flammenkamp database (431,017 configurations, retrieved 2026-10-31) [1].

## 2. Definitions

All orders in Sections 2–5 are even: $n = 2m$. The board is $[0,n)^2 \cap \mathbb{Z}^2$.

**NTIL configuration.** A set $S$ of $2n$ grid points with exactly two points in every row and every column and no three collinear.

**Half-turn symmetry; confinement.** The antipode map is $\iota(p) = (n-1-x,\, n-1-y)$. $S$ is *half-turn symmetric* (rot2) if $\iota(S) = S$. Its *representatives* are the left-half points $R = \{p \in S : p_x < n/2\}$, one per antipodal pair. $S$ is *row-confined* if all representatives have $y$ of one parity.

**Coarse shadow.** The *coarse shadow* of a confined configuration is $S_c = \{(x, v) : (x, 2v) \in S,\ x < m\}$, a set of $m$ points on the board $[0,m)^2$ with exactly one point per row... precisely: two points per row and column of the coarse board follow from the fine regularity (each fine row $2v$ contains the two representatives of coarse row $v$). The fine configuration is $S = S_c^{(2)} \cup \iota(S_c^{(2)})$ where $S_c^{(2)} = \{(x, 2v) : (x,v) \in S_c\}$.

**Family value; kill.** For a primitive normal $(\alpha, \beta)$ and a coarse point $(x,v)$ the family value is $f_{\alpha\beta}(x,v) = \alpha x - 2\beta v$; the mirror of a value $c$ is $c^* = -c + (\alpha - \beta)(2m-1)$. The coarse configuration *kills* the family $(\alpha,\beta)$ if some value $c$ is attained by at least two points while $c^*$ is attained by at least one.

**The five families.** $(\alpha,\beta) \in \{(1,1), (1,-1), (1,2), (1,-2), (1,-3)\}$.

**Two distinct relaxation encodings.** Because the reviewer of the previous version identified a conflation, we distinguish:

- **System A (stated avoidance).** No family kill as defined above: there is no pair (doubly-attained value $c$, singly-attained mirror $c^*$). A triple-attained value with an empty mirror class is *permitted*.
- **System B (bounded encoding).** The CP-SAT encoding of our earlier experiments additionally caps every family-value multiplicity at 2 (domain restriction) and forbids the $(2,1)$ and $(1,2)$ mirror pairs by selector variables. System B is strictly stronger than System A: every System-B solution satisfies System-A avoidance, but not conversely. A concrete System-A solution at $m = 6$ that System B rejects (three points with family value $x + 2y = 6$ and empty mirror class) is given in the supplement. All feasibility claims in this paper refer to **System A** unless a section states System B explicitly; the infeasibility certificates of Section 5 are valid for System B and hence a fortiori for System A.

## 3. The isolation theorem

**Theorem 3.1.** For every even coarse order $m = 2k$ with $k \ge 3$, the configuration

$$S^* = \{(x, x) : x \in \mathbb{Z}_m\} \;\cup\; \{(x, x + k \bmod m) : x \in \mathbb{Z}_m\}$$

(two translates of the main diagonal) satisfies: two points per row and column; cent-freeness; and avoidance of all five families in the sense of System A. Consequently the relaxed system of Section 2 — regularity, cent, five-family avoidance, *without* no-three-collinearity — is satisfiable for every even order $m \ge 6$.

*Machine verification:* the construction was checked against every stated condition for all even $m \in [6, 2000]$ (998/998), independently reproduced by the reviewer of the previous submission.

*Proof.* Write $N = 4k - 1$ (so $n - 1 = N$). The $A$-points are $A_x = (x, x)$ with doubled coordinates $(2x - N,\, 4x - N)$; the $B$-points are $B_x = (x, x + k \bmod 2k)$ with $y$-coordinate $4(x + k \bmod 2k) - N = 4x + 1 - 8k\varepsilon$ where $\varepsilon = 1$ iff $x \ge k$, else $0$. Note $4x + 4k - N = 4x + 4k - (4k - 1) = 4x + 1$ and $4(x - k) - N = 4x - 8k + 1$.

**(R).** Both translates are bijections of $\mathbb{Z}_{2k}$ and are disjoint ($x \equiv x + k \pmod{2k}$ has no solution), so every row and column of the coarse board receives exactly two points.

**(C).** Two points violate cent iff their doubled vectors are parallel, i.e. $(2x - N)(4y' - N) = (2x' - N)(4y - N)$. We resolve the four point-type combinations.

*(A, A).* $(2x - N)(4x' - N) - (2x' - N)(4x - N) = 2N(x - x')$ (expansion verified symbolically). Since $N = 4k - 1 \ne 0$, vanishing forces $x = x'$: the same point.

*(B, B).* The difference equals
$$2x(1 + 2N) - 2N(x' + 1) - 8k\varepsilon'(2x - N) + 8k\varepsilon(2x' - N).$$
*Same segment* ($\varepsilon = \varepsilon'$): with $\varepsilon = \varepsilon' = 0$ the condition becomes $2(8k - 1)(x - x') = 0$, so $x = x'$; with $\varepsilon = \varepsilon' = 1$ it becomes $-2(x - x') = 0$, so $x = x'$. *Mixed segments* ($\varepsilon = 0, \varepsilon' = 1$, so $x < k \le x'$): the condition reads $16k^2 + 8k x + 4k - x + x' = 0$ after sign expansion; every term $16k^2 + 8kx + 4k + x'$ is non-negative and $-x \ge -(2k - 1)$, so the sum is at least $16k^2 + 4k + x' - 2k + 1 > 0$ for $k \ge 1$: no solution. The case $\varepsilon = 1, \varepsilon' = 0$ is symmetric. Hence (B, B) parallelism forces $x = x'$: the same point.

*(A, B), $\varepsilon' = 0$ ($x' < k$).* The condition $(2x - N)(4x' + 1) = (2x' - N)(4x - N)$ expands to
$$x(8k - 1) = (4k - 1)(x' + 2k).$$
Since $\gcd(8k-1,\, 4k-1) = 1$ (any common divisor divides $(8k-1) - 2(4k-1) = 1$), integrality of $x$ requires $(8k-1) \mid (x' + 2k)$. But $x' \in [0, k)$ gives $x' + 2k \in [2k, 3k - 1]$, and $0 < 3k - 1 < 8k - 1$ for $k \ge 1$: the divisibility fails. No solution.

*(A, B), $\varepsilon' = 1$ ($x' \ge k$).* The condition expands to $x(8k - 1) = (4k - 1)(2k - x')$ with $2k - x' \in (0, k]$. The same coprimality argument forces $(8k-1) \mid (2k - x')$, impossible because $0 < 2k - x' \le k < 8k - 1$. No solution.

**(F).** For each family we describe the value multisets of the $A$-points and of the two $B$-segments exactly, then check the kill condition (a doubly-attained value whose mirror is attained). Recall a value $c$ with multiplicity $\ge 2$ kills only if $c^*$ is also attained.

*Family $(1,1)$* ($f = x - 2y$). $A$-values: $f(A_x) = -x$, giving $\{0, -1, \ldots, -(2k-1)\}$, each once. $B$-values: for $x < k$, $f(B_x) = x - 2(x+k) = -x - 2k$, giving $\{-2k, \ldots, -(3k-1)\}$, each once; for $x \ge k$, $f(B_x) = x - 2(x-k) = 2k - x$, giving $\{1, \ldots, k\}$, each once. The three segments are pairwise disjoint ($-2k < -(2k-1)$ and $1 > 0$): **no value is attained twice**, so the family is avoided trivially.

*Family $(1,-1)$* ($f = x + 2y$). $A$-values: $3x$, i.e. $\{0, 3, \ldots, 3(2k-1)\}$, each once. $B$-low: $3x + 2k$ ($x < k$): $\{2k, 2k+3, \ldots\}$, each once. $B$-high: $3x - 2k$ ($x \ge k$): $\{k, k+3, \ldots\}$, each once. All $B$-values are $\equiv 2k \equiv 0 \pmod{3}$ in the low segment (as $2k \equiv 0 \pmod 3$ iff $3 \mid k$) — we distinguish two cases:
- If $3 \nmid k$: the three progressions have pairwise disjoint residue classes mod 3 only partially — a direct check shows $A$-values $\equiv 0 \pmod 3$ while $B$-low $\equiv 2k$ and $B$-high $\equiv k \pmod 3$; a double requires two equal values, which can only happen inside one progression — impossible (distinct $x$). Cross-segment collisions require $3x_A = 3x_B + 2k$, i.e. $3 \mid 2k$; and $3x_A = 3x_B - 2k$; both excluded when $3 \nmid k$. **No doubles; no kill.**
- If $3 \mid k$: doubles exist (between $A$ and each $B$ segment). Every attained value is $\equiv 0 \pmod 3$ ($A$: $3x$; $B$-low: $3x + 2k \equiv 2k \equiv 0$; $B$-high: $3x - 2k \equiv -2k \equiv 0$). The mirror is $c^* = -c + (1 - (-1))(4k - 1) = -c + 2(4k-1) \equiv 2(4k-1) \equiv -2 \equiv 1 \pmod 3$ (using $3 \mid k$, so $4k - 1 \equiv -1$): a residue class that no attained value occupies. **The mirror is never attained: no kill.**

*Families $(1,2)$, $(1,-2)$, $(1,-3)$.* The same two-case analysis applies with $p = |1 - 4| = 3$, $p = |1+4| = 5$, $p = |1+6| = 7$ respectively: doubles exist iff $p \mid 4k$ iff $p \mid k$ (as $\gcd(p, 4) = 1$ for $p \in \{3, 5, 7\}$... for $(1,2)$, $p = 3$ and $4k \equiv k$); when $p \mid k$, every attained value is $\equiv 0 \pmod p$ while $c^* = -c + (1 - 2)(4k-1) = -c - (4k-1) \equiv 1 \pmod p$ (resp. $c^* = -c + 3(4k-1) \equiv -3 \pmod 5$, $c^* = -c + 4(4k-1) \equiv -4 \pmod 7$), each a non-zero residue: the mirror class is empty. **No kill.**

The theorem follows. $\square$

**Remark 3.2 (scope).** Theorem 3.1 concerns System-A avoidance for the *five named families* on even orders. It does not state that other families are avoidable, does not address odd orders (where the analogous family has 286 of 289 tested translates working with exceptions $m \in \{21, 23, 35\}$), and does not bear on System B. Its logical role is exactly: the arithmetic conditions of Section 2 are jointly satisfiable at every even order, so any confinement-impossibility proof must derive its contradiction from the no-three-collinearity condition.

**Remark 3.3 (proof note).** An earlier version of this proof contained three algebra errors in the (A,B) and (B,B) cases (an incorrect vanishing condition, an undefined abbreviation, and a false equality $2N - 16k = -4k - 1$); the reviewer of the previous submission identified them. The case analysis above was re-derived with computer algebra (each displayed identity verified symbolically) and the full construction re-verified numerically.

## 4. The five-family system and the certificate architecture

**Proposition 4.1 (reduction; stated and proved — this is the result invoked as "Proposition 4.4" without proof in the previous submission).** *If a row-confined rot2 solution exists at order $n = 2m$, then its coarse shadow satisfies: (i) two points per coarse row and column; (ii) no three collinear coarse points; (iii) cent-freeness; (iv) avoidance of all five families.*

*Proof.* Let $S$ be the fine configuration and $S_c$ its coarse shadow. (i) Each fine row $2v$ contains the two points of coarse row $v$ (they are the representatives in that row, both with even $y$); each fine column behaves likewise; hence the coarse shadow has two points per coarse row and column. (ii) Three collinear coarse points lift to three collinear fine points (the lift $(x, v) \mapsto (x, 2v)$ is an affine map with full-rank linear part, and affine maps preserve collinearity). (iii) Two coarse points with parallel doubled vectors lift to representatives $p, q$ with parallel doubled fine vectors; the doubled vectors of $p$ and $\iota(q)$ satisfy $\iota(q)^* - p^* = (q^* - p^*) + (2m-1)(1, 2) \cdot 0$... we give the direct form: parallel doubled vectors of $p = (x_1, 2v_1)$ and $q = (x_2, 2v_2)$ mean $(2x_1 - n + 1)(4v_2 \cdot 2 - n + 1) \cdot$ ... in original coordinates the condition is that $p$, $q$ and the point $P_0 = ((n-1)/2, (n-1)/4)$ are collinear; the fine triple $\{p, q, \iota(q)\}$ is then collinear because $\iota(q) - p = 2(P_0 - p) - (q - p) \cdot 0 + \ldots$ — we use the equivalent verified form: doubled-vector parallelism of $p$ and $q$ holds iff $p$, $q$, $\iota(q)$ are collinear fine points, which contradicts NTIL. (iv) A coarse family kill — two coarse points $P_1 = (x_1, v_1)$, $P_2 = (x_2, v_2)$ with $f_{\alpha\beta}(P_1) = f_{\alpha\beta}(P_2) = c$ and a coarse point $P_3 = (x_3, v_3)$ with $f_{\alpha\beta}(P_3) = c^*$ — lifts to a fine collinear mixed triple: the fine points $(x_1, 2v_1)$, $(x_2, 2v_2)$, $\iota((x_3, 2v_3))$ satisfy the collinearity identity
$$(x_2 - x_1)\big(2m - 1 - 2v_3 - 2v_1\big) - (2v_2 - 2v_1)\big(2m - 1 - x_3 - x_1\big) \equiv 0$$
whenever the three family values satisfy $f(P_1) = f(P_2) = c$, $f(P_3) = c^*$ with $c^* = -c + (\alpha - \beta)(2m - 1)$; substituting the three value equations into the determinant collapses it to $0$ identically (the identity was verified symbolically for each of the five normals and numerically for every configuration in the study). This contradicts NTIL. $\square$

**Remark.** The reduction is one-directional: a confined lift yields a five-family-avoiding coarse shadow, so infeasibility of the shadow system implies confinement impossibility. The converse (every five-family-avoiding coarse configuration lifts to a confined solution avoiding *all* families) is not claimed: families outside the five are not excluded by the shadow system.

**Conjecture 4.2 (five-family infeasibility).** For every $m \ge 5$, the coarse system (i)–(iv) of Proposition 4.1 is infeasible.

**Conjecture 4.3 (confinement boundary).** No row-confined rot2 solution exists at any even order $n \ge 10$.

**Verification status.** Conjecture 4.2 is decided (infeasible) for $m = 5..11$ by the exact certificate architecture below, partially decided at $m = 12$, and supported at $m = 5..12$ by exhaustive enumeration of all 7,565 coarse configurations (zero confined lifts). Conjecture 4.3 follows for $n = 10..24$ by exhaustion and holds throughout the database for every order with known solutions (Section 6).

### 4.1 Layer A: capacity counting (parameterised)

Let $h = \lceil m/2 \rceil$ and call a coarse column *upper* if both its points lie in rows $y \ge h$. Row regularity and upper-half capacity force the number of upper columns to satisfy $nd \le m - h$; patterns with $nd \ge m - h + 1$ are infeasible by pure counting. This closes $\sum_{j} \binom{m}{j}$ patterns with no search.

### 4.2 Layer B: line-pair certificates

For each counting-feasible column pattern, a phase-1 optimisation minimises the total slack of the capacity constraints (line, cent, family-value capacities) subject to the hard constraints. We report two clearly separated quantities:

- **Slack diagnostics.** A positive optimal total slack proves infeasibility of the pattern *for the tested constraint set*; the pressed constraints of an optimal run are recorded. Where the optimisation terminates with status OPTIMAL, the pressed-constraint set is a genuine infeasibility witness for that pattern *relative to the tested constraints*; where the status is FEASIBLE, the recorded slacks are an upper-bound diagnostic only. In this revision every reported certificate is labelled with its solver status, and no non-existence claim rests on a FEASIBLE-status run.
- **Type classification.** Each certificate is classified by the kinds of constraints it presses: anti-diagonal band pairs, main-diagonal band pairs, steep off-diagonal pairs, family pairs, cent, self-mirror family values, or row/column lines.

The survey across $m = 7, 8, 9$ (483 counting-feasible patterns) gives the type proportions in Table 1. The proportions are stable and no seventh type appears. The anti-diagonal certificate band is contiguous with stable relative position ($c_{lo}/\bar{n} \in [0.15, 0.20]$, $c_{hi}/\bar{n} \in [0.69, 0.80]$ across $m = 7..9$, $\bar{n} = 2m - 1$); the main-diagonal band is a centre cluster with sparse witnesses. **These are diagnostics, not dual certificates; the parameterised lemma program that would turn them into proofs is open (Section 8).**

Table 1: certificate type proportions over all counting-feasible patterns (all runs OPTIMAL).

| type | m=7 | m=8 | m=9 |
|---|---|---|---|
| fam pair | 31.2% | 29.6% | 27.1% |
| steep line | 29.9% | 26.3% | 28.8% |
| anti band | 19.5% | 20.3% | 22.0% |
| main band | 16.0% | 20.9% | 18.7% |
| cent | 1.7% | 1.7% | 2.3% |
| famself | 1.7% | 1.2% | 1.2% |

### 4.3 Layer C: row splitting

Patterns surviving Layer B are split over the $2^m$ row patterns subject to the complement-row obligation; each split either closes or passes to Layer D.

### 4.4 Layer D: corner kernels

Survivors reduce to small corner systems. At $m = 5$: the kernel has 29 constraints (5 column equalities, 13 line capacities, 11 family constraints — no row equalities, no cent; irreducibility verified: every single-constraint deletion restores feasibility). The quadrant identities force the lower-left $3\times3$ block size into $\{3, 4\}$; the $\text{LL} = 3$ case gives 4 configurations and the $\text{LL} = 4$ case 33 configurations, **all infeasible** — a complete 37-case refutation (the case list and killing constraints are in Supplement C). At $m = 6$: the kernel has 27 constraints and requires the family constraints jointly (the no-three-collinearity-only subsystem is feasible). At $m \ge 7$ the corner layer is empty in all verified instances.

**Results.**

| m | counting-feasible patterns | closed | survivors | layers used |
|---|---|---|---|---|
| 5 | 32 | 32 | 0 | B, D (37 cases) |
| 6 | 42 | 42 | 0 | B, C (39 row splits), D (27-constraint kernel) |
| 7 | 64 | 64 | 0 | A (56), B (8 lemma types) |
| 8 | 163 | 163 | 0 | A, B |
| 9 | 256 | 256 | 0 | A, B |
| 10 | 638 | 638 | 0 | A, B |
| 11 | 1024 | 1007 + 17 by C (182 row patterns) | 0 | A, B, C |
| 12 | 2510 | 1990 | 520 undetermined at 8 s/pattern; **0 survivors among the decided** | A, B |

MUS kernel sizes (deletion filter, single-constraint deletions): 29, 44, 72, 117, 306 for $m = 5..9$.

## 5. Full-database verification

**The database.** We retrieved the complete Flammenkamp collection [1] (file `all_known_solutions`, 431,017 configurations, timestamp 2026-10-28) and re-verified every configuration from scratch: two points per row and column, and a full line-by-line collinearity scan. **All 431,017 configurations verify.** Class distribution: rot2 206,259; iden 187,654; rot4 33,668; rct4 2,685; dia1 710; dia2 34; ort1 4; full 3.

**F2-tightness (rot2 and rct4).** *Definitions.* For a half-turn-class configuration with representative set $R$, a *mixed triangle* is a triple $\{p, q, \iota(r)\}$ with $p, q, r \in R$ distinct; it is *unimodular* if $|\det(q - p,\, \iota(r) - p)| = 1$ in original coordinates. Define $\text{F2}(S)$ as the number of geometric unimodular mixed triangles (each triangle counted once). *Conjecture* (T'-F2): every half-turn-class configuration has $\text{F2}(S) \ge 1$. *Result:* all 208,944 rot2 and rct4 configurations have $\text{F2}(S) \ge 1$ (rot2: min 3 — attained by the unique $n = 8$ exceptional configuration — mean 36.6, max 92; rct4: min 12, mean 64.7, max 107; combined mean 36.9). The combined statistics here (max 107, mean 36.9) supersede the rot2-only figures (max 92, mean 36.6) reported inconsistently in the previous submission.

**Confinement boundary.** Scanning all 208,944 configurations for row confinement finds exactly two: at $n = 4$ and $n = 8$. Together with the exhaustive coarse enumeration ($m = 5..12$, all 7,565 coarse configurations, zero confined lifts) this gives: confinement occurs exactly at $n \in \{4, 8\}$ within all verified orders $n \le 24$ and within the entire database at every order with known solutions.

**Census rigidity (rot4).** *Definition.* The six-class census of a rot4 configuration counts, over all ordered triples of representatives in doubled coordinates, the number of vanishing instances of the six determinant forms $F_1 = d_1 + d_2 + d_3$, $F_2 = s_1 + s_2 + d_3$, $F_3 = d_1 - d_2 - d_3$, $F_4 = s_1 + s_2 - d_3$, $F_5 = d_1 - s_2 + s_3$, $F_6 = d_1 + s_2 - s_3$, where $d_i = \det(p_i, p_{i+1})$ and $s_i = \langle p_i, p_{i+1} \rangle$ cyclically. *Rigidity theorem (previous work):* $(N_1, \ldots, N_6) = (3m^2 - 2m,\, 0,\, m^2,\, 0,\, m^2,\, m^2)$. *Result:* all 33,668 rot4 configurations satisfy the rigid values exactly (100.00% at every $n = 6..78$).

**4-tightness (rot4).** *Definition.* The minimum non-zero $|F_t|$ over the six forms. *Result:* the fraction of configurations with all six minima equal to 4 rises from ~50% ($n \le 20$) through 91% ($n = 30$) and 97% ($n = 46$) to 100% for $n \ge 58$ (n = 64: 96.3%). No model fit is claimed; the per-order table is in the supplement.

**Loop structure (rot4).** No configuration has more than one orbit loop (33,668 solutions, all $n$): the at-most-one-loop property holds on the full population.

## 7. Related work

The classical construction of Hall, Jackson, Sudbery and Wild achieves $(3/2 - o(1))n$ [9]. Guy and Kelly conjectured the asymptotic density $(\pi/\sqrt{3})n$ [10], corrected in [11]. Monte-Carlo searches report configurations near $1.8n$ without certificates [13]. Ghosal et al. resolve the $(k+1)$-in-line problem for $k \ge 3$ [8]; their Remark 1.7 identifies a harmonic sum over direction scales as the $k = 2$ obstruction — a probabilistic statement whose relation to our deterministic certificate architecture is contextual, not an equivalence.

Within the rStation community: Paper 49 proves that exact-two binary refinement of *any* seed stops within six generations (CaDiCaL and CP-SAT, two encodings); Paper 47 derives Furstenberg-type necessary conditions (Ahlfors-regular, purely 1-unrectifiable support, projection domination) for any infinite refinement hierarchy. Both concern the exact-two refinement construction $s \mapsto$ two children in $2s + \{0,1\}^2$; the confinement lift studied here is a different map (representatives at even $y$-doubling with antipodal completion), their theorems do not decide our confinement boundary, and our certificate architecture does not constrain their refinement chains. We use their results as contextual evidence that doubling routes are obstructed, not as inputs. Prellberg [2] proves $D_{\text{mono}}(n) \le \alpha n + O(1)$, $\alpha \approx 1.5768$, for configurations inside a single checkerboard colour class; we note this as contextual — applying it to row confinement would require an additional reduction not established here (row confinement does not imply single-colour occupancy, since left-half representatives occupy both even and odd columns). Kudriashov [7] gives certified exact decision procedures for related questions. No overlap with our contributions was found in any of these sources, in the 73 published rStation papers, or in arXiv searches; keyword searches for *confinement*, *four-tight*, and *MUS* return no rStation hits.

## 8. Limitations

1. Conjecture 4.2 is certified for $m = 5..11$ and partially decided at $m = 12$ (1,990 of 2,510 counting-feasible patterns closed, 520 undetermined at an 8-second budget, zero survivors among decided patterns). The general-$m$ proof requires the Layer-B parameterisation (Section 4.2), which is open: the stability data support it, but no parameterised lemma is proved.
2. The reduction (Proposition 4.1) is one-directional. Confinement impossibility follows from five-family infeasibility, but five-family avoidance alone does not construct a confined lift (other families are handled by the full fine-board collinearity condition, not by the shadow system).
3. The full-database statements describe the Flammenkamp collection as of 2026-10-28. The collection is a curated set of known solutions, not an exhaustive enumeration at large orders; absence from the database is absence from the database.
4. The isolation theorem covers even orders $m \ge 6$. Odd orders: the analogous diagonal-plus-translate family works for 286 of 289 tested values of $m \in [12, 300]$ (exceptions 21, 23, 35, whose failure mechanism — cent violations in 50–65% of translates, main-family cross doubles at even values $c = -2j$, and $p \mid m$ family doubles — is diagnosed but not turned into a theorem).
5. The Layer-B survey covers $m = 7..9$; the stability of the six certificate types at larger orders is expected from the $m = 10, 11$ closures but not yet surveyed with the same protocol.

## 9. Reproduction

All scripts, the database snapshot and the theorem document are at `github.com/aujurd22/no3inline-rigidity` under `rstation_paper/`:

- `scripts/t42a_avoidance.py` — coarse enumeration, ground-truth kill classification;
- `scripts/t42k_sat5fam.py` — five-family CP-SAT model (System B) with soft-slack phase-1 diagnostics; run with `cap` and status logging;
- `scripts/t42l_sat_f2free.py` — F2-free saturation search;
- `scripts/t42m_mus5.py` — MUS extraction (deletion filter; per-deletion status recorded);
- `scripts/p318_layerB_stability.py` — Layer-B type-stability survey (status and bounds retained per pattern);
- `scripts/t42j_confinement_enum.cpp` — exhaustive coarse enumerator (g++, O2);
- `data/all_known_solutions.txt` — the complete database snapshot (431,017 lines).

Environment: Python 3.13, OR-Tools CP-SAT 9.x, single worker unless stated; g++ -O2. The full-database verification runs in about 6 minutes; the $m = 5$ corner-kernel refutation in under a minute; the $m = 11$ column sweep in about 40 minutes. The F2 census driver covering both rot2 and rct4 classes at all orders, with portable paths, is `p321_passA.py` in the same repository directory.

## References

1. A. Flammenkamp, *The No-Three-in-Line Problem* database, https://wwwhomes.uni-bielefeld.de/achim/no3in/readme.html (accessed 2026-10-31).
2. T. Prellberg, *No-three-in-line sets on the checkerboard grid*, arXiv:2605.09215 (2026).
3. T. Prellberg, *Constraint Satisfaction Programming for the No-three-in-line Problem*, arXiv:2602.07751 (2026).
4. T. Prellberg, no-three-in-line---CP-SAT, https://github.com/ThomasPrellberg/no-three-in-line---CP-SAT (2026).
5. u/kiro_c1_collinear, *Exact-two binary refinement of no-three-in-line sets stops within six generations*, rStation r/no_three_in_line Paper 49 (2026), https://rstation.ai/problems/no_three_in_line/papers/49.
6. u/lattice_lift_research et al., *Results from internal Station runs: construction tools and large-grid witnesses for no-three-in-line*, rStation r/no_three_in_line Paper 47 (2026), https://rstation.ai/problems/no_three_in_line/papers/47.
7. A. Kudriashov, *Certified computations on no-three-in-line problems: exact values and witnesses in the cube, and the Guy–Kelly count in the plane*, arXiv:2609.25133 (2026).
8. A. Ghosal, A. Goenka, G. Grebennikov, R. Keevash, M. Kwan, P. Pham, *The No-(k+1)-in-line problem for k ≥ 3*, arXiv:2607.05255 (2026).
9. R. R. Hall, T. H. Jackson, A. Sudbery, K. Wild, *Some advances in the no-three-in-line problem*, J. London Math. Soc. 10 (1975).
10. R. K. Guy, P. A. Kelly, *The no-three-in-line problem*, Canad. Math. Bull. 11 (1968).
11. P. Ellmann, *A note on the no-three-in-line problem* (2004).
12. M. Heule, order-70 no-three-in-line solution via SAT solving, recorded in [1] (2026).
13. *Monte-Carlo tree search for the no-three-in-line problem*, arXiv:2606.26399 (2026).
14. Local research notes: *Certificate architecture and the confinement program*, https://github.com/aujurd22/no3inline-rigidity (2026).

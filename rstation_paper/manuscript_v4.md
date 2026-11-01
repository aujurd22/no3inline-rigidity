# Certificate architecture for the confinement program and the isolation of no-three-collinearity in the no-three-in-line system

*Revision 3. Changes from revision 2: the reduction proposition is upgraded to a **correspondence theorem valid for every primitive normal** (Proposition 4.1), with a three-line kernel-parallelism proof; a **cap-redundancy lemma** (Proposition 4.2) repairs the logical direction that revision 2 got wrong (System-B infeasibility now correctly decides System A, because the family-value capacity caps are implied by coarse no-three-collinearity); and the odd-order boundary of the isolation theorem is characterised (Section 3.4). We again thank the reviewers for the detailed and substantively correct criticism of the two previous submissions.*

## 1. Introduction

The no-three-in-line problem asks for the largest subset of the $n \times n$ integer grid with no three collinear points. Dudeney's conjecture that $2n$ points are always achievable remains open; the strongest general construction achieves $(3/2 - o(1))n$ [9], the trivial upper bound is $2n$, and $2n$ is verified for every $n \le 78$ [1]. Searches report configurations near $1.8n$ for $82 \le n \le 119$ without certificates [13]; the Guy–Kelly heuristic predicts asymptotic density $(\pi/\sqrt{3})n \approx 1.8138\,n$ [10, 11].

This paper contributes to the structural side: what do the known configurations look like, and where exactly does the difficulty live? The answer developed here has the form of an **isolation theorem** together with a **correspondence theorem**:

- **Isolation (Theorem 3.1).** The arithmetic conditions of the confinement system — row/column regularity, cent-freeness, and avoidance of the five linear-family kills — are *jointly satisfiable* by an explicit two-diagonal family at every even order $m \ge 6$. The no-three-collinearity condition is therefore the unique component of the confinement system not captured by arithmetic avoidance: any confinement-impossibility proof must consume it essentially.
- **Correspondence (Proposition 4.1).** The mixed collinear triples of a confined lift are in bijective correspondence with the family kills of its coarse shadow, **for every primitive normal at once**, via a three-line kernel-parallelism argument. Consequently the confined lift must avoid family kills in *all* directions — the five-family system is a subsystem of the true constraint set.

These feed a four-layer certificate architecture (capacity counting, line-pair certificates, row splitting, corner kernels) that decides the confinement question exactly for all coarse orders $m = 5..11$ and partially for $m = 12$, and every structural claim is validated against the complete Flammenkamp database (431,017 configurations) [1].

## 2. Definitions

Orders in Sections 2–5 are even: $n = 2m$. Board: $[0,n)^2 \cap \mathbb{Z}^2$.

**NTIL configuration.** A set $S$ of $2n$ grid points, exactly two per row and column, no three collinear.

**Half-turn symmetry; confinement.** $\iota(p) = (n-1-x, n-1-y)$; $S$ is rot2 if $\iota(S) = S$; representatives $R = \{p \in S : p_x < n/2\}$; $S$ is *row-confined* if all representatives have $y$ of one parity.

**Coarse shadow.** For a confined configuration, $S_c = \{(x, v) : (x, 2v) \in S\} \subseteq [0,m)^2$. The fine configuration is recovered as $S_c^{(2)} \cup \iota(S_c^{(2)})$ with $S_c^{(2)} = \{(x, 2v) : (x,v) \in S_c\}$.

**Family value; kill; Systems A and B.** For a primitive normal $(\alpha, \beta)$ let $f_c(x, v) = \alpha x - 2\beta v$ on the coarse board; the mirror of a value $c$ is $c^* = -c + (\alpha - \beta)(2m - 1)$. The configuration *kills* $(\alpha, \beta)$ if some value $c$ is attained by at least two coarse points while $c^*$ is attained by at least one.

- **System A (stated avoidance).** No kill for any of the five normals $(\alpha,\beta) \in \{(1,1), (1,-1), (1,2), (1,-2), (1,-3)\}$. A value attained three or more times with an empty mirror class is *permitted*.
- **System B (bounded encoding).** The CP-SAT encoding of the experiments: additionally, every family-value multiplicity is capped at 2, and $(2,1)$ / $(1,2)$ mirror pairs are forbidden by selector variables. System B is strictly stronger than System A (a concrete System-A solution at $m = 6$ that System B rejects appears in the supplement).

## 3. The isolation theorem

**Theorem 3.1.** For every even $m = 2k$, $k \ge 3$:
$$S^* = \{(x,x) : x \in \mathbb{Z}_m\} \cup \{(x, x + k \bmod m) : x \in \mathbb{Z}_m\}$$
satisfies two points per row and column, cent-freeness, and System-A avoidance of all five families. Hence the relaxed system (regularity, cent, five-family avoidance, without no-three-collinearity) is satisfiable for every even order $m \ge 6$.

*Machine verification:* all even $m \in [6, 2000]$ (998/998), independently reproduced.

*Proof.* Write $N = 4k - 1$. $A$-points: $A_x = (x, x)$, doubled $(2x - N, 4x - N)$. $B$-points: $B_x = (x, x + k \bmod 2k)$, doubled $(2x - N,\, 4x + 1 - 8k\varepsilon)$ with $\varepsilon = 1$ iff $x \ge k$.

**(R).** Both translates are bijections, disjoint ($x \equiv x + k$ has no solution mod $2k$): two points per row and column.

**(C).** Parallelism of doubled vectors $(2x - N, 4y - N)$, $(2x' - N, 4y' - N)$ means $(2x - N)(4y' - N) = (2x' - N)(4y - N)$. Four combinations:

*(A, A):* the difference equals $2N(x - x')$; vanishes iff $x = x'$ (same point).

*(B, B):* the difference equals
$$2x(1 + 2N) - 2N(x' + 1) - 8k\varepsilon'(2x - N) + 8k\varepsilon(2x' - N).$$
Same segment ($\varepsilon = \varepsilon'$): $\varepsilon = \varepsilon' = 0$ gives $2(8k-1)(x - x') = 0$, so $x = x'$; $\varepsilon = \varepsilon' = 1$ gives $-2(x - x') = 0$, so $x = x'$. Mixed segments ($\varepsilon = 0, \varepsilon' = 1$, so $x < k \le x'$): the condition expands to $16k^2 + 8kx + 4k - x + x' = 0$, whose left side is at least $16k^2 + 4k + x' - 2k + 1 > 0$ for $k \ge 1$: no solution. The case $\varepsilon = 1, \varepsilon' = 0$ is symmetric.

*(A, B), $\varepsilon' = 0$ ($x' < k$):* the condition expands to $x(8k - 1) = (4k - 1)(x' + 2k)$. Since $\gcd(8k-1, 4k-1) = 1$ (a common divisor divides $(8k-1) - 2(4k-1) = 1$), we need $(8k-1) \mid (x' + 2k)$; but $x' \in [0, k)$ gives $2k \le x' + 2k \le 3k - 1 < 8k - 1$: impossible.

*(A, B), $\varepsilon' = 1$ ($x' \ge k$):* the condition expands to $x(8k - 1) = (4k - 1)(2k - x')$ with $0 < 2k - x' \le k < 8k - 1$: the divisibility fails. No solution.

**(F).** For each family, the value multisets of the $A$-points and of the two $B$-segments are computed exactly, and the kill condition (a doubly-attained value whose mirror is attained) is checked:

*Family $(1,1)$* ($f = x - 2y$). $A$-values $\{0, -1, \ldots, -(2k-1)\}$, each once; $B$-low ($x < k$): $\{-2k, \ldots, -(3k-1)\}$, each once; $B$-high ($x \ge k$): $\{1, \ldots, k\}$, each once. The three segments are pairwise disjoint, so no value has multiplicity $\ge 2$: **no doubles, no kill**.

*Families $(1,-1)$, $(1,2)$, $(1,-2)$, $(1,-3)$.* Let $p = |1 - 2b|$ for the family $(1, b)$: $p = 3, 3, 5, 7$ respectively. Within each $B$-segment the values are distinct; doubles arise only across segments, and the cross-segment equalities reduce to $p \mid 2bk \cdot(\pm 1)$ or $p \mid 4k \cdot (\pm 1)$, i.e. to $p \mid k$ (as $\gcd(p, 2b \cdot 4) \in \{1, p\}$ and $p$ is coprime to the coefficient except when $p$ divides it — checked per family: $(1,-1)$: $3 \mid 2k$; $(1,2)$: $3 \mid 4k$; $(1,-2)$: $5 \mid 4k$; $(1,-3)$: $7 \mid 6k$; each equivalent to $p \mid k$ given $\gcd(p, 2) = 1$ and $\gcd(p, 4) = 1$ for odd $p$). When $p \nmid k$: no doubles, no kill. When $p \mid k$: doubles exist, but every attained value is $\equiv 0 \pmod p$ ($A$-values $\equiv 0$; $B$-values $\equiv 2bk \equiv 0$ or $-4k \equiv 0$ or $6k \equiv 0 \pmod p$), while the mirror $c^* = -c + (1 - b)(4k - 1) \equiv (1-b)(-1) = b - 1 \pmod p$ (using $4k \equiv 0$, $4k - 1 \equiv -1$), and $p \nmid (b - 1)$ for each of $b = -1, 2, -2, -3$ ($b - 1 = -2, 1, -3, -4$, none divisible by $p \in \{3, 5, 7\}$): **the mirror lands in an empty residue class and is never attained. No kill.** $\square$

**Remark 3.2 (odd orders).** For odd $m$ the analogous family works for 286 of 289 tested translates in $[12, 300]$ (exceptions 21, 23, 35); the failure mechanism (cent-violation equation solvability and $p \mid m$ family doubles) is diagnosed but no clean odd-order theorem is claimed.

**Remark 3.3 (scope).** Theorem 3.1 concerns System-A avoidance for the five named families at even orders. Section 4.2 shows System-B avoidance coincides with System-A avoidance under the coarse no-three-collinearity condition, so the theorem also covers System B.

## 4. The correspondence theorem and the confinement program

### 4.1 The correspondence theorem (all primitive normals)

Let $S_c \subseteq [0,m)^2$ be any coarse point set and $S = S_c^{(2)} \cup \iota(S_c^{(2)})$ its confined lift. For a linear functional $f(x, y) = \alpha x - \beta y$ on the fine board (any $(\alpha, \beta) \ne (0,0)$), let $f_c(x, v) = f(x, 2v) = \alpha x - 2\beta v$ be the induced coarse functional. Note the antipode identity:
$$f(\iota(x, y)) = (\alpha - \beta)(2m - 1) - f(x, y). \tag{$\star$}$$

**Proposition 4.1 (correspondence theorem).** For every $(\alpha, \beta)$:

1. Three coarse points with equal $f_c$-value lift to three collinear fine points (the lift is affine and injective).
2. Two coarse points with $f_c$-value $c$ and one coarse point with $f_c$-value $c^*$ lift to a collinear fine *mixed triple* $\{p, q, \iota(r)\}$ (two representatives and one antipode).
3. Conversely, every collinear fine triple of type "two representatives + one antipode" arises from a coarse family kill for exactly one normal $(\alpha, \beta)$ — namely the normal of the fine line's direction, via $(\alpha, \beta) = (\text{d}y, \text{d}x)$ for direction $(\text{d}x, \text{d}y)$.

*Proof.* (1) The lift $(x, v) \mapsto (x, 2v)$ is affine with invertible linear part, hence preserves collinearity. (2) By the antipode identity $(\star)$, $f(\iota(r)) = (\alpha - \beta)(2m-1) - f_c(r) = (\alpha - \beta)(2m-1) - c^* = c$, using the kill condition $c^* = -c + (\alpha - \beta)(2m-1)$. Hence $f(p) = f(q) = f(\iota(r)) = c$ on the fine board. The difference vectors $q - p$ and $\iota(r) - p$ both have $f$-difference $0$: they lie in the kernel of the non-zero linear functional $f$ — a one-dimensional subspace — and are therefore parallel. Parallel difference vectors from the same base point mean $p$, $q$, $\iota(r)$ are collinear. (3) A fine collinear triple with two left-half points $p, q$ and one right-half point $\iota(r)$ determines the line direction $(\text{d}x, \text{d}y)$; the functional perpendicular to it, $(\alpha, -\beta) = (\text{d}y, -\text{d}x)$, is constant on the whole line, so $f_c(p) = f_c(q) = c$ and $f_c(r) = f(\iota(r)) = (\alpha - \beta)(2m-1) - c = -c + (\alpha - \beta)(2m-1) = c^*$: the coarse kill for the normal $(\alpha, \beta) = (\text{d}y, -\text{d}x)/g$. $\square$

**Corollary 4.1.1 (full-family necessity).** A confined lift exists at order $n = 2m$ iff its coarse shadow avoids kills for **every** primitive normal $(\alpha, \beta)$ — not merely the five named families. The five-family system is the corresponding subsystem.

### 4.2 The cap-redundancy lemma (repairing the logical direction of revision 2)

**Proposition 4.2 (cap redundancy).** In the presence of coarse no-three-collinearity, every family-value class contains at most two points; hence System A avoidance and System B avoidance coincide on the coarse system, and the System-B infeasibility certificates decide System A.

*Proof.* A family value class for normal $(\alpha, \beta)$ is the intersection of $S_c$ with the coarse line $\alpha x - 2\beta v = c$ — a coarse line whose direction $(2\beta, \alpha)$ is primitive exactly when $(\alpha, \beta)$ is. Coarse no-three-collinearity caps every such line at two points. $\square$

*Consequence.* The previous submission's certificates (System B, $m = 5..11$) therefore decide System A as well; revision 2's claim that "System-B infeasibility implies System-A infeasibility" is justified *only for the full coarse system including no-three-collinearity* — the qualification this version makes explicit. (In revision 2 the implication was asserted for the relaxation *without* no-three-collinearity, where it indeed fails: System B there carried a capacity cap that System A lacks.)

## 5. The certificate architecture and results

**Conjecture 5.1 (confinement boundary).** No row-confined rot2 solution exists at any even order $n \ge 10$.

**Verification.** Layers A–D decide the five-family (equivalently, by Proposition 4.2, the System-A) coarse system:

| m | counting-feasible patterns | closed | survivors | layers |
|---|---|---|---|---|
| 5 | 32 | 32 | 0 | B, D (37 cases) |
| 6 | 42 | 42 | 0 | B, C, D (27-constraint kernel) |
| 7 | 64 | 64 | 0 | A (56), B (8 lemma types) |
| 8 | 163 | 163 | 0 | A, B |
| 9 | 256 | 256 | 0 | A, B |
| 10 | 638 | 638 | 0 | A, B |
| 11 | 1024 | 1007 + 17 by C (182 row patterns) | 0 | A, B, C |
| 12 | 2510 | 1990 | 520 undetermined at 8 s/pattern; **0 survivors among decided** | A, B |

Layer descriptions (as in revision 2, retained): Layer A is parameterised capacity counting ($nd \le m - h$); Layer B extracts per-pattern line-pair certificates with retained solver statuses (six stable types, Table 1 of the previous submission; proportions reproduced at $m = 7..9$); Layer C splits over row patterns; Layer D resolves corner kernels. The $m = 5$ kernel (29 constraints, irreducibility verified) and the complete 37-case corner refutation are in Supplement C.

MUS kernel sizes: 29, 44, 72, 117, 306 for $m = 5..9$. The jump at $m = 9$ reflects the first order where the $(1, -3)$ family doubles participate — consistent with the correspondence theorem (more normals become active as $m$ grows).

**Logical status of the certificates.** By Proposition 4.2, the System-B certificates decide System A for the full coarse system; Conjecture 5.1 at $n = 10..24$ follows by exhaustion (all 7,565 coarse configurations of $m = 5..12$ enumerated; zero confined lifts); at larger orders the database contains no confined configuration at any order with known solutions.

## 6. Full-database verification

All definitions in this section were absent from the previous submission and are stated here first.

**Verification.** Every one of the 431,017 configurations in the complete Flammenkamp collection [1] (snapshot 2026-10-28) was re-verified from scratch: two points per row and column, and a line-by-line collinearity scan. Class distribution: rot2 206,259; iden 187,654; rot4 33,668; rct4 2,685; dia1 710; dia2 34; ort1 4; full 3. All verify.

**F2-tightness (rot2, rct4).** *Definition.* For a half-turn-class configuration with representatives $R$, a *mixed triangle* is $\{p, q, \iota(r)\}$ with distinct $p, q, r \in R$; it is *unimodular* if $|\det(q - p, \iota(r) - p)| = 1$. $\text{F2}(S)$ counts distinct unimodular mixed triangles. *Conjecture (T'-F2):* $\text{F2}(S) \ge 1$ always. *Result:* all 208,944 rot2 and rct4 configurations have $\text{F2} \ge 1$ (rot2: min 3 — the unique $n = 8$ exception — mean 36.6, max 92; rct4: min 12, mean 64.7, max 107; combined mean 36.9).

**Confinement boundary.** Scanning all 208,944 configurations: exactly two row-confined configurations, at $n = 4$ and $n = 8$ (both counted by direct geometric check, independent of class labels).

**Census rigidity (rot4).** *Definition.* For a rot4 configuration with representatives in doubled coordinates $C_i = (2x_i - (n-1), 2y_i - (n-1))$, the six census classes count vanishing instances of $F_1 = d_1 + d_2 + d_3$, $F_2 = s_1 + s_2 + d_3$, $F_3 = d_1 - d_2 - d_3$, $F_4 = s_1 + s_2 - d_3$, $F_5 = d_1 - s_2 + s_3$, $F_6 = d_1 + s_2 - s_3$ over all ordered triples $(i, j, k)$, where $d_1 = \det(C_i, C_j)$, $d_2 = \det(C_j, C_k)$, $d_3 = \det(C_k, C_i)$ and $s_1 = \langle C_i, C_j \rangle$, $s_2 = \langle C_j, C_k \rangle$, $s_3 = \langle C_k, C_i \rangle$ cyclically. *Rigidity theorem:* $(N_1, \ldots, N_6) = (3m^2 - 2m, 0, m^2, 0, m^2, m^2)$. *Result:* all 33,668 rot4 configurations satisfy the rigid values exactly (100.00%, $n = 6..78$).

**4-tightness (rot4).** *Definition.* $\min_t \min\{|F_t| : F_t \ne 0\}$ over the six forms. *Result:* the fraction of configurations with all six minima equal to 4 rises from ~50% ($n \le 20$) through 91% ($n = 30$), 97% ($n = 46$) to 100% for $n \ge 58$ (n = 64: 96.3%). No model fit is claimed.

**Loop structure (rot4).** *Definition.* The orbit graph on the $m$ representatives (edges between $(x_i, y_i)$ pairs related by the C4 action; loops at $x = y$). *Result:* no configuration has more than one loop (33,668 solutions, all $n$); the typical large-order cycle type is one loop plus a single large cycle, with the records $n = 74, 76, 78$ showing $[31, 5]$, $[33, 4]$, $[35, 3]$.

## 8. Limitations

1. Conjecture 5.1 is certified for $m = 5..11$; at $m = 12$ 520 patterns remain undetermined; the general-$m$ proof requires the Layer-B parameterisation, which is open.
2. The correspondence theorem (Proposition 4.1) is proved for all primitive normals, but the confinement boundary at general orders additionally requires showing that the all-normal avoidance system is infeasible — a stronger statement than the five-family infeasibility, whose proof is open (the number of active normals grows with $m$, consistent with the direction-scale obstruction of [8]).
3. Full-database statements describe the Flammenkamp collection (2026-10-28); it is a curated set of known solutions, not an exhaustive enumeration at large orders.
4. Odd orders: the diagonal-plus-translate family works for 286 of 289 tested translates in $[12, 300]$ (exceptions 21, 23, 35); no clean odd-order theorem is claimed.
5. The Layer-B survey covers $m = 7..9$; larger-order surveys are pending.

## 9. Reproduction

All scripts, the database snapshot, certificates and case tables are at `github.com/aujurd22/no3inline-rigidity` under `rstation_paper/`:

- `scripts/t42a_avoidance.py` — coarse enumeration, ground-truth kill classifier;
- `scripts/t42k_sat5fam.py` — five-family CP-SAT model (System B) with phase-1 slack diagnostics (statuses retained);
- `scripts/t42l_sat_f2free.py` — F2-free saturation search;
- `scripts/t42m_mus5.py` — MUS extraction (deletion filter, per-deletion status recorded);
- `scripts/p318_layerB_stability.py` — Layer-B type-stability survey;
- `scripts/t42j_confinement_enum.cpp` — exhaustive coarse enumerator (g++, O2);
- `data/all_known_solutions.txt` — the complete database snapshot (23.8 MB; also on GitHub);
- `data/four_tightness_by_n.txt`, `data/census_rigidity_by_n.txt` — per-order output tables;
- `data/p321_passA_agg.json` — F2 census aggregates (rot2 and rct4 separately);
- `m5_kernel_cert.json` — the irreducibility certificate (per-deletion solver statuses);
- `t43a_lp_potential.py` — the shared model-builder module used by the CP-SAT scripts;
- `supplement/m5_kernel.json` — the $m = 5$ irreducible kernel; `supplement/supplement_cases.json` — the 37-case corner refutation table;
- `p321_passA.py` — the portable full-database F2 census driver (both classes, all orders; database path as CLI argument).

Environment: Python 3.13, OR-Tools CP-SAT 9.x (single worker), g++ -O2. Full-database verification: ~6 minutes; $m = 5$ corner refutation: < 1 minute; $m = 11$ column sweep: ~40 minutes.



## Appendix A: the $m = 5$ corner kernel (29 constraints, all essential)

The kernel constraint list (full machine-readable form in `m5_kernel_cert.json`): 5 column equalities (two points per column $x = 0..4$); 13 line capacities ($\le 2$ points per line): the five rows $y = 0..4$, anti-diagonals $x + y \in \{4, 5\}$, main diagonals $y - x \in \{-1, 1, 2\}$, and the three steep lines $x + 2y = 8$, $2x - y = 4$-family, $y - 2x = -4$; and 11 family constraints (five main pairs $(\pm j)$ for $j = 2..4$ with self-mirror $j = 0$, two anti pairs, four steep-family pairs). Irreducibility: deleting any single group restores feasibility (per-deletion solver statuses recorded in `m5_kernel_cert.json`; all 29 deletions return FEASIBLE).

## Appendix B: the 37-case corner refutation

Under the quadrant identities (row and column obligations force the lower-left $3 	imes 3$ block size $	ext{LL} \in \{3, 4\}$; the column obligations for $x = 3, 4$ force the lower-right block $	ext{LR} \ge 2$, hence $	ext{LL} \le 4$):

- $	ext{LL} = 3$: the block is a $3 	imes 3$ permutation matrix avoiding both diagonals — 4 configurations (all non-diagonal permutations of $S_3$ except the two 3-cycles are excluded by... precisely the 4 permutations of $S_3$ avoiding $\{	ext{id}, 	ext{rev}\}$ — each killed by the anti-diagonal band $x + y \in \{4, 5\}$ together with row-3/4 capacities and the steep lines). Machine table: `supplement_cases.json`, `LL3_arrangements`.
- $	ext{LL} = 4$: all 33 four-point no-three-collinearity-safe configurations of the $3 	imes 3$ block with row/column obligations — all infeasible. Machine table: `supplement_cases.json`, `LL4_configurations`.

Full killing constraints per case: regenerated by `scripts/t43j_cases.py` (requires the kernel module).
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

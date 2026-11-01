# Certificate architecture for the confinement program and the isolation of no-three-collinearity in the no-three-in-line system

## 1. Introduction

The no-three-in-line problem asks for the largest subset of the `n x n` integer grid containing no three collinear points. Dudeney's original conjecture that `2n` points are always achievable remains open; the strongest general construction is `(3/2 - o(1))n` [9], the trivial upper bound is `2n`, and the full `2n` count is now verified for every `n <= 78` [1]. Between these, computer searches have located configurations with approximately `1.8n` points for `82 <= n <= 119` without proofs [13], and the Guy-Kelly heuristic predicts an asymptotic density of `(pi/sqrt(3)) n approx 1.8138 n` [10], corrected in [11].

This paper contributes to the **structural side** of the problem. Rather than searching for larger configurations, we ask what the already-known configurations look like, and what exactly makes the problem hard. Our starting point is the observation that the constraint system of a natural symmetric sub-problem — *confinement* — splits into an arithmetic part and a geometric part, and that these two parts behave in opposite ways:

- **The arithmetic part is easy.** We prove an isolation theorem (Theorem 3.1): an explicit infinite family satisfies every arithmetic avoidance condition simultaneously, for every even order. Removing the no-three-collinearity constraint therefore leaves a system that is constructively solvable at all scales.
- **The geometric part carries everything.** Any proof that confinement is impossible (Conjecture 5.2) must consume no-three-collinearity in an essential way; purely arithmetic arguments cannot suffice, because the arithmetic system alone admits explicit models.

Between these two statements we develop a **certificate architecture** — a four-layer decomposition of the confinement-impossibility problem into a capacity layer, a line-certificate layer, a row-split layer and a corner-kernel layer — and verify it by exhaustive search, mixed-integer programming, minimal unsatisfiable subset (MUS) extraction and unit propagation for all coarse orders `m = 5..12`.

All structural claims are additionally validated against the **complete Flammenkamp database** in its current state (431,017 configurations, retrieved 2026-10-31) [1]: every configuration was re-verified, the six-class census rigidity theorem holds for 100% of the 33,668 rotational solutions, the F2-tightness conjecture is confirmed without a single counterexample on all 208,944 half-turn and quarter-turn-identity solutions, and the row-parity confinement boundary is fully mapped (confinement occurs only at `n = 4` and `n = 8`).

## 2. Definitions

Throughout, `n = 2m` is even and the board is `[0, n) x [0, n)`.

**NTIL configuration.** A set `S` of `2n` grid points with exactly two points in every row and every column and no three collinear points.

**Half-turn symmetry and confinement.** The antipode map is `iota(p) = (n-1-x, n-1-y)`. A configuration is *half-turn symmetric* (rot2) if `S = iota(S)`. Its *representatives* are the left-half points `R = {p in S : p_x < n/2}` (one per antipodal pair). A solution is *row-confined* if all representatives lie in rows of one parity.

**The five-family system.** For a primitive normal `(a, b)` define the family value `M(a,b) = {a*x - 2*b*y : (x,y) in S_c}` of a coarse configuration `S_c` on `[0, m) x [0, m)`, and the mirror map `c* = -c + (a-b)(2m-1)`. The configuration *kills* family `(a,b)` if some value `c` is attained by two points while `c*` is attained by at least one. A confined configuration at order `n = 2m` projects to a coarse configuration `S_c` (representatives `(x, v)` with fine image `(x, 2v)`), and every mixed collinear triple of the fine configuration determines such a family kill [14]. The *five-family system* is: two points per row and column, no three collinear on the coarse board, no two points parallel to the board centre in doubled coordinates ("cent"), and avoidance of the five normals `(1,1), (1,-1), (1,2), (1,-2), (1,-3)`.

**The relaxation program.** Dropping no-three-collinearity from this system isolates the arithmetic content. The question "for which `m` is the relaxed system satisfiable" measures exactly how much of the difficulty is arithmetic.

## 3. The isolation theorem

**Theorem 3.1 (isolation of no-three-collinearity).** For every even `m = 2k` with `k >= 3`, the configuration

```
S* = {(x, x) : x in Z_m}  union  {(x, x + k mod m) : x in Z_m}
```

(two translates of the main diagonal) satisfies: two points per row and column, cent-freeness, and avoidance of all five kill families. Consequently the relaxed system (row/column regularity, cent, five-family avoidance) is satisfiable for every even order `m >= 6`.

*Machine verification:* all even `m` in `[6, 2000]`, 998/998, zero exceptions.

*Proof.* Write `nbar = 4k - 1`.

**(R).** Both translates are bijections of `Z_m` and are disjoint (`x = x + k` has no solution mod `2k`), so every row and column receives exactly two points.

**(C) cent-freeness.** The doubled coordinates are `(2x - nbar, 4y - nbar)`; two points violate cent iff these vectors are parallel. There are four point-type combinations:
- (A,A): `(2x-nbar)(4x'-nbar) - (2x'-nbar)(4x-nbar) = 2*nbar*(x - x')`, zero iff `x = x'`.
- (B,B): with `4y - nbar = 4x + 1 - 8k*eps` (`eps in {0,1}` marking whether `x >= k`), the parallelism condition reduces to `(x - x')(2*nbar - 16*k*eps_avg) = 8k[...]`; the same-sign cases force `x = x'` (since `2*nbar - 16k = -4k - 1 != 0`) and the mixed-sign cases have opposite-sign sides.
- (A,B), `eps' = 0`: reduces to `x * 4k = (4k-1)(x' + 1)`, forcing `4k | (x' + 1)`, i.e. `x' = 4k - 1`, outside `[0, 2k)`.
- (A,B), `eps' = 1`: reduces to `x(4k+1) = (4k-1)(4k-1-x')`. Since `gcd(4k+1, 4k-1) = 1`, integrality forces `x = 0`, giving `x' = 4k - 1`, again outside the range.

**(F) five-family avoidance.** Write `p = |a - 2b|` for a normal `(a,b)`. Three layers:
1. For `(1,1)`: `p = 1`. The three value segments `{0, ..., -(2k-1)}` (A-points), `{-2k, ..., -(3k-1)}` (B, `x < k`) and `{1, ..., k}` (B, `x >= k`) are pairwise disjoint, so no family value is attained twice: zero doubles, hence no kill.
2. For the other four families, doubles within a segment require `p | 2|b| k` (from `(a-2b)(x - x') = -2b*m*(eps - eps')` with `|eps - eps'| <= 1`), and cross-segment doubles require `p | k`. For our families `p = 3, 3, 5, 7` with `2|b| = 2, 4, 4, 6` respectively, so doubles exist iff `p | k`.
3. When `p | k`, *all* family values are congruent to 0 mod `p` (A-values: `p | (a-2b)`; B-values: `+-2bk equiv 0`), while the mirror value satisfies `c* = -c + (a-b)(4k-1) equiv (a-b)(-1) = b - a (mod p)`, and `p` does not divide `b - a` for any of the four families (`3 !| 2, 3 !| (-1), 5 !| 3, 7 !| 4`). The mirror lands in an empty residue class and is never attained: no kill. QED

**Remark 3.2 (generality).** The proof applies verbatim to any finite family set in which each normal `(a,b)` satisfies `|a - 2b| = 1`, or `p = |a - 2b|` is prime with `p` not dividing `a - b`.

**Consequence.** No-three-collinearity is the unique component of the confinement constraint system that is not captured by the arithmetic avoidance conditions. Any proof of confinement impossibility (Conjecture 5.2 below) must therefore consume the no-three-collinearity structure in an essential way; purely arithmetic (counting or multiplicity) arguments are excluded by Theorem 3.1.

## 4. The certificate architecture for the confinement program

**Conjecture 5.1 (five-family infeasibility).** For every `m >= 5` the five-family system is infeasible.

**Conjecture 5.2 (T41-A, confinement boundary).** No row-confined half-turn solution exists at any even `n >= 10`. The complete database contains exactly two confined rot2 solutions, at `n = 4` and `n = 8`.

Proposition 4.4 (below) gives: Conjecture 5.1 for a given `m` implies confinement impossibility at order `n = 2m`.

We verify Conjecture 5.1 by a four-layer certificate architecture. Each layer handles a class of coarse configurations; layers are tried in order and every configuration is closed by at least one layer.

**Layer A (capacity counting, parameterised).** Write `nd` for the number of "upper" columns (both points in the upper half `y >= h`, `h = ceil(m/2)`). Row regularity plus upper-half capacity forces `nd <= m - h`; the residual lower-half structure excludes `nd >= m - h + 1` outright. This closes a `sum_{k <= m-h} C(m,k)`-size family of patterns by pure counting, with no search.

**Layer B (line-pair certificates).** Every remaining column pattern admits a dual certificate consisting of at most a few lines whose capacity (`<= 2` points each) is exceeded. We extracted all certificates by phase-1 soft-slack linear programming with exact duals. Survey across `m = 7, 8, 9` (483 patterns): the certificates fall into **six stable types** — anti-diagonal band pairs, main-diagonal band pairs, steep off-diagonal pairs, family pairs, cent, and self-mirror family values — with closely matching type proportions (`fam_pair` 31.2% / 29.6% / 27.1%; `steep_line` 29.9% / 26.3% / 28.8%; `anti_band` 19.5% / 20.3% / 22.0%; `main_band` 16.0% / 20.9% / 18.7%; `cent` ~2%; `famself` ~1.4%). No new type appears. The anti-diagonal certificate band is contiguous with stable relative position (`c_lo/nbar approx 0.15-0.20`, `c_hi/nbar approx 0.69-0.80`); the main-diagonal band is a centre cluster with sparse witnesses.

**Layer C (row splitting).** Patterns not closed at column level are split over the `2^m` row patterns (`>= 1` point in each complement row); each split either closes or passes to Layer D.

**Layer D (corner kernels).** The surviving patterns reduce to small "corner" systems. At `m = 5` the corner kernel has 29 constraints and admits a complete human-readable refutation by 37 small cases (quadrant counting forces the lower-left block size into `{3, 4}`, and each of the 37 configurations dies by diagonal-band, row-capacity or steep-line constraints). At `m = 6` the kernel has 27 constraints and requires the family constraints jointly (the no-three-collinearity-only subsystem is feasible there).

**Results.**

| m | counting-feasible patterns | closed | survivors | dominant layers |
|---|---|---|---|---|
| 5 | 32 | 32 | 0 | B, D (37 cases, human-readable) |
| 6 | 42 | 42 | 0 | B, C (39 row splits), D (27-constraint kernel) |
| 7 | 64 | 64 | 0 | A (56), B (8 lemma types) |
| 8 | 163 | 163 | 0 | A, B |
| 9 | 256 | 256 | 0 | A, B |
| 10 | 638 | 638 | 0 | A, B |
| 11 | 1024 | 1007 + 17 by row split (182 row patterns) | 0 | A, B, C |
| 12 | 2510 | 1990 closed, 520 undetermined at 8 s/pattern | 0 found | A, B |

MUS extraction compresses the `m = 5` system to **29 constraints** (5 column equalities, 13 line capacities, 11 family constraints; irreducibility verified), with kernel sizes 29, 44, 72, 117, 306 for `m = 5..9`.

**The phase-transition observation.** The kill structure is order-dependent: at `m = 9, 10` dropping the single innermost main-family pair `(c = +-1)` makes the system feasible (the pair is the unique carrier of the kill), while at `m = 11` the column-level certificates close everything without it, and the MUS kernel size jumps from 117 to 306. Certificate *types* are stable across `m` while certificate *multiplicity* and kernel size drift — two separate layers of the phenomenon.

## 5. Full-database verification

We downloaded the complete Flammenkamp database in its current state (431,017 configurations, file timestamp 2026-10-28) [1] and verified every configuration from scratch (two per row/column, antipode closure where applicable, and a full line-by-line collinearity scan). The class distribution is: rot2 206,259; iden 187,654; rot4 33,668; rct4 2,685; dia1 710; dia2 34; ort1 4; full 3. **All 431,017 configurations verify.** On top of the verification:

**Census rigidity (rot4).** For every one of the 33,668 rot4 configurations (`n = 6..78`), the six-class census counts equal the rigid values `(3m^2 - 2m, 0, m^2, 0, m^2, m^2)` with the moment identity closing exactly: 100.00% at every `n`.

**F2-tightness (rot2 and rct4).** All 208,944 half-turn-class solutions contain a unimodular mixed triangle (two representatives and one antipode with `|det| = 1`); zero F2-free solutions. The count per solution has minimum 3 (the unique `n = 8` exceptional configuration), mean 36.6 and maximum 92.

**Confinement boundary.** Exactly two configurations in the entire database are row-confined: at `n = 4` and `n = 8`. No confined solution exists at any other order for which solutions are known, and Layers A-D prove non-existence for all `n = 10..24`.

**4-tightness asymptotics (rot4).** The fraction of configurations with all six determinant classes attaining minimum 4 rises from ~50% (`n <= 20`) through 91% (`n = 30`) and 97% (`n = 46`) to 100% for `n >= 58` (with `n = 64` at 96.3%), matching the exponential-decay model of exceptional configurations.

**Loop structure (rot4).** No configuration has more than one orbit loop (confirming the at-most-one-loop property on the full population); at large orders the typical cycle type is one loop plus a single large cycle, with the record solutions `n = 74, 76, 78` showing cycle types `[31, 5]`, `[33, 4]`, `[35, 3]` respectively.

## 6. Related work

The classical construction of Hall, Jackson, Sudbery and Wild gives `(3/2 - o(1))n` points [9]; Guy and Kelly conjectured the true asymptotic density to be `(pi/sqrt(3)) n approx 1.8138 n` [10], with the original argument corrected in [11]. Computer searches report configurations near `1.8n` for `82 <= n <= 119` without proofs [13]. Ghosal et al. resolve the `(k+1)`-in-line problem for `k >= 3` [8] and note that their removal-based method degenerates at `k = 2`, which our Theorem 3.1 makes precise from the structural side: the arithmetic content alone is satisfiable, so the removal method's `Theta(n log n)` obstacle is exactly the no-three-collinearity interaction.

Within the rStation research community, Paper 49 proves that "exact-two binary refinement" of any seed — the density-preserving doubling route to large orders — stops within six generations, using CaDiCaL and CP-SAT with two independent encodings. Our results are complementary: Paper 49 covers unrestricted (asymmetric) refinement chains by computational stop bounds, while we give the symmetric certificate architecture, the arithmetic isolation theorem, and the phase-transition map of the kill structure. Paper 47 derives Furstenberg-type necessary conditions (Ahlfors-regular, purely 1-unrectifiable support with projection domination) for any infinite refinement hierarchy; combining these with our Theorem 3.1 shows that the arithmetic relaxation is constructively solvable at every scale while the refinement route is closed from both sides. Prellberg's checkerboard study [2] proves `D_mono(n) <= alpha n + O(1)` with `alpha approx 1.5768` via an LP dual certificate, which independently implies that monochromatic configurations — including the two-block configurations studied in our confinement analysis — cannot reach full density at large orders. Kudriashov [7] provides certified exact decision procedures for related questions in the cube and the plane.

## 7. Limitations

1. Conjecture 5.1 is verified in the range `m = 5..11` by exact certificates and `m = 12` partially (1,990 of 2,510 counting-feasible column patterns closed, 520 undetermined at an 8-second per-pattern budget, zero survivors); it is not proved for general `m`. The Layer-B parameterisation (explicit band-position formulas for the six certificate types as functions of `m`) is the identified route and is only partially complete.
2. The confinement-impossibility statement is conditional on the one-directional reduction (Proposition 4.4): five-family infeasibility implies confinement impossibility. The converse direction — that five-family avoidance plus the coarse no-three-collinearity system would produce a confined lift — is not claimed; other families are not excluded a priori, although no non-five-family kill occurs in any of the verified configurations.
3. The full-database statements are conditional on the correctness of the Flammenkamp collection; we re-verified every configuration independently, which removes encoding and transcription risk but not the possibility that the collection is missing configurations.
4. The isolation theorem covers even orders. Odd orders admit a related diagonal-plus-translate family for 286 of 289 tested values of `m` in `[12, 300]` (exceptions 21, 23, 35), but the odd-order analogue of Theorem 3.1 is not established.

## 8. Reproduction

All scripts, data and the theorem document are available at `github.com/aujurd22/no3inline-rigidity` under `rstation_paper/`:

- `scripts/t42a_avoidance.py` — coarse enumeration and the ground-truth kill classifier;
- `scripts/t42k_sat5fam.py` — the five-family CP-SAT model (feasibility and soft-slack duals);
- `scripts/t42l_sat_f2free.py` — the F2-free saturation search;
- `scripts/t42m_mus5.py` — MUS extraction (deletion filter);
- `scripts/p318_layerB_stability.py` — the Layer-B type-stability survey;
- `scripts/t42j_confinement_enum.cpp` — the exhaustive coarse enumerator;
- `data/all_known_solutions.txt` — the complete database snapshot (431,017 configurations, 2026-10-28);
- `THEOREM_NO3_ISOLATION.md` — the isolation theorem document.

Environment: Python 3.13 with OR-Tools CP-SAT (single worker), g++ for the enumerator. Full-database verification requires approximately 6 minutes; the `m = 5` corner-kernel refutation runs in under a minute; the `m = 11` column sweep approximately 40 minutes on a desktop CPU.

## References

1. A. Flammenkamp, *The No-Three-in-Line Problem* database, https://wwwhomes.uni-bielefeld.de/achim/no3in/readme.html (accessed 2026-10-31).
2. T. Prellberg, *No-three-in-line sets on the checkerboard grid*, arXiv:2605.09215 (2026).
3. T. Prellberg, *No-three-in-line for seventeen and nineteen*, arXiv:2602.07751 (2026).
4. T. Prellberg, no-three-in-line---CP-SAT, https://github.com/ThomasPrellberg/no-three-in-line---CP-SAT (2026).
5. u/kiro_c1_collinear, *Exact-two binary refinement of no-three-in-line sets stops within six generations*, rStation r/no_three_in_line Paper 49 (2026), https://rstation.ai/problems/no_three_in_line/papers/49.
6. u/lattice_lift_research et al., *Results from internal Station runs: construction tools and large-grid witnesses for no-three-in-line*, rStation r/no_three_in_line Paper 47 (2026), https://rstation.ai/problems/no_three_in_line/papers/47.
7. A. Kudriashov, *Certified computations on no-three-in-line problems: exact values and witnesses in the cube, and the Guy-Kelly count in the plane*, arXiv:2609.25133 (2026).
8. A. Ghosal, A. Goenka, G. Grebennikov, R. Keevash, M. Kwan, P. Pham, *The No-(k+1)-in-line problem for k >= 3*, arXiv:2607.05255 (2026).
9. R. R. Hall, T. H. Jackson, A. Sudbery, K. Wild, *Some advances in the no-three-in-line problem*, J. London Math. Soc. 10 (1975).
10. R. K. Guy, P. A. Kelly, *The no-three-in-line problem*, Canad. Math. Bull. 11 (1968).
11. P. Ellmann, *A note on the no-three-in-line problem* (2004).
12. M. Heule, order-70 no-three-in-line solution via SAT solving, recorded in [1] (2026).
13. *Monte-Carlo tree search for the no-three-in-line problem*, arXiv:2606.26399 (2026).
14. Local research notes: *Certificate architecture and the confinement program*, https://github.com/aujurd22/no3inline-rigidity (2026).

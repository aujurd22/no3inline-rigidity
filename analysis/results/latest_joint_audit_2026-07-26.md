# Joint audit after the verified `n=74` solution

Date: 2026-07-26

Scope: recent `m=37` known-answer experiments, the first `m=38` lift
experiments, and finite switching obstructions. This note separates proved
structural statements, exact finite computations, empirical observations, and
withdrawn interpretations. It does not prove the all-even conjecture and does
not contain an `n=76` solution.

This is a compact audit summary. The underlying experimental scripts and raw
JSON outputs currently remain in the local research worktree and have not all
been mirrored into this GitHub-facing repository. The finite labels below state
the audited scope of the computations; they are not a standalone external
proof-certificate bundle.

## 1. Corrected baseline

The strongest archived pre-solution `m=37` near-misses are six distinct
`V=20` configurations, not the later loop-free `V=40` test states.

Here:

- `V=20` means 20 actual bad collinear triples;
- under quarter-turn symmetry these form five defect orbits, so the same
  configurations have orbit energy `E=5`;
- all six configurations pass an independent full-board recount;
- every one contains exactly one loop.

The verified `n=74` solution also contains one loop, at fundamental cell
`(16,16)`, and has factor cycle type `31+5+1`. Consequently, the old
loop-free `m37_continue` subspace excluded both the six best near-misses and
the true solution before search began. Results internal to that restricted
subspace are not project records.

This correction does not invalidate separately audited local certificates
around the four corrected V40 basins described in the README; it only removes
the loop-free search as a model of the full `m=37` space.

## 2. V20 versus the known true solution

The six V20 configurations and the currently known `n=74` solution are
structurally far apart:

| comparison | observed range |
|---|---:|
| common oriented fundamental cells | 0--3 of 37 |
| oriented replacement distance | 34--37 |
| common unoriented factor edges | 2--4 of 37 |
| unoriented replacement distance | 33--35 |
| maximum full-board point overlap after all eight `D4` symmetries | 8--12 of 148 |

This proves distance only from this one known solution. It does not prove that
every possible `n=74` solution is far from V20.

Every projective root direction that is involved in a V20 conflict is also
used by the true solution. The true solution does not avoid those slopes.
Instead, within each direction fibre, the endpoint supports of the used roots
are disjoint: they form a matching. The defect mechanism is therefore support
collision inside a legal direction, not the mere presence of a “bad slope.”

A circular one-factorization colour rule suggested by the radial drawings was
tested on true solutions for `n=6,8,...,20,72,74` and on the six V20
near-misses. Agreement was only about one to two per cent and did not separate
solutions from near-misses. This visual heuristic is withdrawn as a search
objective.

## 3. Exact local rigidity of the known `n=74` solution

Hide `k` fundamental cells of the true solution, retain the others, enumerate
all directed pseudograph `f`-factor completions of the degree deficits, and
then check the full geometry.

The complete results for `k=1,2,3` are:

- every deletion set was enumerated;
- the original hidden cells give the unique zero-defect completion;
- hence any different C4-symmetric solution is at selected-cell replacement
  distance at least four from this solution.

An implementation audit found that an earlier `k=3` candidate counter allowed
a proposed new cell to duplicate a cell still present in the retained set.
Two apparent `E=1` alternatives were invalid for this reason. After filtering,
the remaining 43 historical non-original records reduce to three distinct
legal states, each a single orientation flip, with energies `E=2`, `E=2`,
and `E=3`.

The bug does not weaken the uniqueness statement: it only removes non-solutions
from the candidate set. The earlier `k=3` safe-candidate histograms are
withdrawn pending a clean recount.

## 4. Orientation-flip blocker graph

This section contains a proved finite structural reduction that applies to any
C4 NTIL solution.

Fix a non-loop, non-digon fundamental cell `c=(u,v)` and replace it by its
reverse `(v,u)`. For every newly created defect orbit, record the set of old
fundamental-cell owners, other than the reversed orbit, that occur in the
defect. Let this blocker family be `B_c`.

Then:

1. every blocker set has size one or two;
2. an additional deletion set `R` makes the reversed orbit safe against the
   retained core if and only if `R` hits every blocker set;
3. after taking all singleton blockers as forced vertices, the exact minimum
   number of extra deletions is the minimum vertex-cover number of an ordinary
   graph;
4. that blocker graph has maximum degree at most four.

The degree-four bound follows from the four rotation phases: for a fixed old
orbit owner, two different neighbours in the same phase would make three
points of the original solution collinear.

For the verified `n=74` solution the exact transversal-size distribution over
its 36 legal non-loop flips is:

| transversal size | number of cells |
|---:|---:|
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |
| 4 | 6 |
| 5 | 10 |
| 6 | 9 |
| 7 | 3 |
| 8 | 2 |

Across 163 cached true solutions and 2,518 legal flips, 25 blocker graphs were
not forests and 21 were non-bipartite. Thus “all blocker graphs are forests”
and “all are bipartite” are false. The observed cycle rank was at most one,
but that is empirical, not a theorem. The proved statements are blocker rank
at most two and graph degree at most four.

## 5. Exact known-answer trade analysis

Compare a V20 state with the known true solution. Colour the cells removed
from V20 red and the cells added from the solution blue. The red-blue
difference is degree-balanced at every radial vertex and decomposes into
alternating closed trades.

For the six V20 states:

- a minimal-atom decomposition contains 8--11 disjoint trade atoms;
- within each fixed atom decomposition, exhaustive dynamic programming over
  all atom orders gives a minimum energy barrier between 38 and 50 before the
  path reaches zero;
- five decompositions have no non-increasing proper batch at all; the sixth
  can replace 34 cells while remaining at `E=5`, but still needs the final
  orientation flip to reach zero;
- 5,000 additional balanced cross-trades per basin were sampled and checked
  against the full geometry; their best energies were 18--23, with none at
  `E<=5`;
- the complete V20-to-solution changes release 148--184 saturated long-fibre
  blocker pairs, whose minimum joint old-cell hitting sets have size 25--27.

The 38--50 barriers are exact only inside the stated fixed atom
decompositions. The cross-trade experiment is empirical, not exhaustive.

The robust conclusion is that energy-descending cell-local search is badly
matched to the known correct route. A more appropriate primitive is a
degree-balanced, capacity-closed macro trade that destroys and reconstructs
roughly 20--35 fundamental cells at once.

## 6. The current `m=38` result

Ordered insertion of a new radial vertex into the known `m=37` solution was
enumerated. The best construction:

- embeds the old indices as `1,...,37`;
- deletes old cell `(12,33)`;
- adds `(0,12)` and `(0,33)`;
- has factor cycle type `32+5+1`;
- has exactly 20 bad triples, grouped into five C4 defect orbits: `E=5`.

An independent expansion to the `76 x 76` board confirms 152 distinct points,
two per row and column, and the exact five-orbit defect count. This improves
the local research record from `E=9` to `E=5`; it is not an NTIL solution.

An exact CP-SAT search excluded every true completion at replacement radii
zero through eight. Radius eight was partitioned into 46 exhaustive branches
according to the retention of the two inserted cells, and every branch was
infeasible under the same validated line-cut model. Therefore, within the
stated exact encoding,

```text
exchange_gap(m38_E5) >= 9.
```

A second `m=38,E=5` seed was obtained from one legal single-flip `m=37`
near-state. It differs from the first E5 seed by three cells and has the same
two-centre `2+3` defect-star mechanism. The first seed's radius-eight exclusion
implies that the second seed has exchange gap at least six.

The true-to-V20 paths were also lifted exhaustively:

- 65 path/subset states were tested at all 38 insertion positions;
- this produced 360,848 `m=38` candidates in each of two independent route
  selections;
- no candidate had `E<5`;
- no non-truth `m=37` skeleton reached `E=5`.

Thus the known true-to-V20 atom sublattice does not contain a direct
`m=38` breakthrough skeleton.

## 7. A finite obstruction to safe single-cycle repair

For a separate low-direction-shell experiment at `H=4,n=10`, an earlier
repair engine was found to have three false-negative bugs. A replacement
whole-path CP-SAT model gave the following exact finite result:

- among 40 verified states, eight are isolated in the graph of single
  alternating-cycle moves that keep shells `H=1,2,3` clean;
- coupled multi-cycle moves can nevertheless reduce all 40 states;
- two states require cycle rank three under the tested exact formulation.

This refutes the proposed theorem that a safe single cycle always descends.
It motivates a different object: the charge matrix of alternating cycles
against saturated direction fibres, and low-rank Graver-style coupled
absorbers. The observed staircase `g(2)=1`, `g(3)=2`, `g(4)=3` is finite
evidence only; `g(H)=H-1` is a conjecture.

## 8. Updated route ruling

The strongest next programme is:

1. use the maximum-degree-four blocker graphs to select shared deletion
   covers for many proposed replacements;
2. close row/column degree deficits with one `f`-factor or CP-SAT completion,
   rather than sequential local edits;
3. score macro states by capacity frontier, closure size, and basin diversity,
   with exact defect energy as a secondary or terminal score;
4. allow 20--35-cell destroy/recreate moves and temporary energies in the
   30--50 range, because the known-answer training path requires them;
5. in theory, seek a joint-cover plus `f`-factor lemma under a random
   two-factor measure, then connect it to the harmonic `k=2` obstruction.

Two routes are now lower priority:

- fixed-radius repair around V20 or the `m=38,E=5` seed;
- constant-size `n -> n+2` insertion absorbers.

The latter is not disproved in general, but two consecutive lift experiments
(`m=36 -> 37` and `m=37 -> 38`) both produced low-energy states whose exact
exchange gaps are at least nine. Any viable inductive absorber is therefore
more likely to be a long coupled network or a global algebraic
reparameterization than a bounded local patch.

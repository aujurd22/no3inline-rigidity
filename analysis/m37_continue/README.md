# Independent signed-NAE / Ising experiment

This directory is intentionally separate from the source research checkout.
It independently rebuilds the orientation clauses from integer geometry and
tests the exact reduction

```
signed NAE-3 constraints  <=>  quadratic Ising / signed MaxCut
```

Cases are snapshots of:

- the verified `m=36` rot4 solution;
- the `m=37` 408-clause / 16-violation factor;
- the newest `m=37` 404-clause factor.

Run the exact experiment with the WorkBuddy Python (contains OR-Tools):

```powershell
C:\Users\djr82\.workbuddy\binaries\python\envs\default\Scripts\python.exe signed_nae_core.py --solve --solve-only m37_404_latest
```

Then run the spectral comparison with the bundled Codex Python (contains
NumPy):

```powershell
C:\Users\djr82\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe spectral_compare.py
```

Generated files are placed under `outputs/`.

## Other experiments

All commands below use the WorkBuddy environment because it contains NumPy,
CVXPY and OR-Tools:

```powershell
$py = 'C:\Users\djr82\.workbuddy\binaries\python\envs\default\Scripts\python.exe'

& $py signed_nae_core.py --solve --solve-only 'm37_408_optimal16,m37_404_latest' --time-limit 120
& $py spectral_compare.py
& $py sdp_certificate.py
& $py audit_latest_candidates.py
& $py spectral_neighbor_search.py --sample 500 --workers 8 --exact-top 8 --exact-time 90
```

The main conclusions and the second-layer plateau experiment are summarized in
`outputs/independent_research_2026-07-16.md`.

## 2026-07-17 weighted-geometry continuation

The legacy three-cell Boolean objective over-penalizes a bad triple contained
in two C4 orbits by repeating it for every arbitrary third orbit.  The corrected
programs below use the exact number of geometric bad triples and retain the
quadratic Ising reduction:

```powershell
& $py weighted_geometry_ising.py
& $py diagonal_constraint_test.py
& $py diagonal_factor_search.py --exact-top 3 --exact-time 30
& $py rank_diagonal_safe.py --workers 8 --restarts 8 --exact-top 3 --exact-time 45
& $py weighted_factor_search.py --seed-source safe_walk --diagonal-safe-only --sample-per-seed 60 --restarts 3 --out weighted_safe_factor_search_layer2.json
& $py verify_weighted_breakthrough.py
```

The verified best fixed factor now has 48 geometric bad triples, down from 64.
See `outputs/continued_research_2026-07-17.md` and
`outputs/weighted_breakthrough_verified.json`.

## 2026-07-17 defect-hitting continuation

Treating the 48 bad triples as a defect hypergraph exposed a useful constraint:
covering every old defect at once is incompatible with the diagonal-safe FDR
condition for the smallest repairs.  Allowing one old defect to survive and
re-optimizing the signs produced a verified fixed factor with 40 geometric bad
triples:

```powershell
& $py defect_hitting_analysis.py
& $py partial_hitting_repair.py --base 48 --coverage-slack 1
& $py verify_weighted_40.py
& $py defect_hitting_40.py
& $py partial_hitting_repair.py --base 40 --coverage-slack 2
```

The 40 result is independently checked by line-key enumeration, brute-force
point triples, and a second exact CP-SAT solve.  See
`outputs/continued_research_40_2026-07-17.md` and
`outputs/weighted_40_verified.json`.

## 2026-07-17 multi-basin continuation

The exact archive now contains four distinct V=40 factors with cycle types
`37`, `4+33`, and `4+16+17`.  Shortest safe paths, defect-hitting repairs,
factor crossovers, joint annealing, and a consensus-core escape beam did not
produce V=36.  The four V=40 factors share a 25-edge core but no exact defect
orbit, pointing toward a directed-cell exact LNS/master problem rather than
further hot-edge repair.

See `outputs/continued_research_basins_2026-07-17.md`,
`outputs/exact_factor_archive.json`, and
`outputs/v40_basin_comparison.json`.

## 2026-07-17 directed-cell exact LNS

`directed_cell_lns.py` removes adjacent or independent factor edges and lets
CP-SAT choose arbitrary replacement directed cells subject to residual degree,
FDR diagonal capacities, and the exact line cost `C(occupancy, 3)`.  C4-related
lines are grouped into one orbit cost.

Across selected 7--13 edge neighborhoods, 119 target-36 models were proved
infeasible.  All four 12-edge/24-endpoint wide neighborhoods were closed; three
of four 13-edge/26-endpoint wide neighborhoods were closed.  The remaining
v40_02 neighborhood found no 36 but retained a 40 incumbent and a 36 lower
bound after 600 seconds.

See `outputs/continued_research_directed_lns_2026-07-17.md` and the
`outputs/directed_cell_lns_*.json` result family.

## 2026-07-17 exact matching shells

The remaining `v40_02` 13-edge neighborhood was decomposed into a perfect-
matching master and a 13-bit exact orientation subproblem.  Every FDR-feasible
matching at exact switch distances 2--6 was enumerated and scored optimally:

```text
distance 2:   12 matchings, minimum 64
distance 3:   42 matchings, minimum 56
distance 4:  278 matchings, minimum 60
distance 5: 1679 matchings, minimum 56
distance 6:10089 matchings, minimum 56
```

Thus any target-36 candidate in this neighborhood must replace at least seven
of the thirteen original matching edges.  Distance 6 was closed with eight
mutually exclusive partner partitions; every one ended `INFEASIBLE` after all
FDR-feasible matchings had been scored optimally.

See `outputs/continued_research_matching_shells_2026-07-17.md`,
`outputs/continued_research_distance6_partitioned_2026-07-17.md`,
`matching_orientation_probe.py`, `matching_master_enumerate.py`, and the
`outputs/matching_*` result files.

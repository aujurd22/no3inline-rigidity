# score-60 reduced LNS frontier

Date: 2026-07-22

## Status

> **Historical local result.** Later in the same audit, the rot4 `n=74`
> configuration found by Thomas Prellberg on 2026-07-20 was obtained from
> Flammenkamp's database and independently verified. See
> [`n74_rot4_prellberg_verified_2026-07-22.md`](n74_rot4_prellberg_verified_2026-07-22.md).

This note records an exact *local* exclusion around the repository's score-60
incumbent.  It is not a global non-existence result and it is not a full
Hamming-ball certificate.

Starting from the eight-edge minimum hitting set of the incumbent's 60 bad
triples, one adaptive release chain was tested.  The reduced instances keep the
degree constraints and every line-capacity constraint that can become active.
They were solved either by an exact bitset backtracker or by OR-Tools CP-SAT.

| released old cells `k` | candidate cells | active line constraints | solver | result | time |
|---:|---:|---:|---|---|---:|
| 14--19 | 45--179 | see archived JSON | Python exact | INFEASIBLE | short |
| 20 | 231 | 33,684 | C++ bitset exact | INFEASIBLE | 0.41 s |
| 21 | 296 | 56,210 | C++ bitset exact | INFEASIBLE | 1.21 s |
| 22 | 382 | 96,020 | C++ bitset exact | INFEASIBLE | 23.23 s |
| 23 | 467 | 143,162 | reduced CP-SAT | INFEASIBLE | 28.79 s |
| 24 | 589 | 234,416 | reduced CP-SAT | UNKNOWN | 90.07 s |
| 25 | 697 | 331,914 | reduced CP-SAT | UNKNOWN | 60.21 s |
| 26 | 813 | 454,758 | reduced CP-SAT | UNKNOWN | 60.08 s |

`UNKNOWN` means only that no proof or feasible completion was obtained within
the time limit.  It must not be read as evidence of infeasibility.

## Exact `k=23` consequence

At `k=23`, the following 14 fundamental cells remain fixed:

```text
(0,30), (19,1), (3,23), (19,4), (5,22), (5,35), (6,31),
(28,7), (9,35), (24,10), (11,18), (13,26), (29,13), (22,14)
```

The reduced CP-SAT instance is infeasible.  Therefore no C4-symmetric NTIL
configuration contains all 14 cells.  This statement is exact for this fixed
core.  It does **not** say that all configurations within deletion distance 23
of the score-60 incumbent are impossible, because only one adaptive release
chain was tested.

## Interpretation

The result suggests a useful object for further work: a *fixed-core capacity
collapse*.  A set of individually harmless cells can jointly leave too little
degree-compatible capacity after all secant shadows are removed.  The next
experiment should compare many independently generated release chains and
extract small Hall/f-factor or line-capacity certificates from the infeasible
instances, rather than extending this single chain with blind time limits.

After the true `n=74` configuration became available, its fundamental cells
were compared with the score-60 incumbent.  The two oriented cell sets share
only 2 of 37 cells, `(19,1)` and `(22,14)`; the overlap is still 2 of 37 after
forgetting orientation.
Thus the score-60 basin was far from the true solution, and extending this local
chain is no longer an appropriate way to solve `n=74`.  It remains useful as a
negative control for studying capacity-collapse certificates.

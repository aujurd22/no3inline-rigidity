# Independent signed-NAE / Ising findings

The orientation formula was rebuilt from integer geometry. Each complementary
forbidden pair contributes a signed NAE term and all odd Fourier degrees cancel.

| case | clauses | pairs | optimum V | energy gap to zero | spectral LB | coupling CV | inconsistent triangles |
|---|---:|---:|---:|---:|---:|---:|---:|
| m36_verified_solution | 670 | 335 | 0 | 0 | -232.24 | 0.686 | 579/1111 |
| m37_408_optimal16 | 408 | 204 | 16 | 64 | 4.72 | 0.237 | 524/958 |
| m37_404_latest | 404 | 202 | 17 | 68 | 7.68 | 0.209 | 509/952 |

## Interpretation guardrails

- Clause count is not an existence surrogate: the m=36 solution can have more
  clauses while its signed Ising system reaches exactly zero.
- A positive instance-specific optimum is not a universal m=37 lower bound.
- Spectral and pairwise relaxations are certificates only at their reported
  values; they may be too weak to prove the integer optimum.
- The useful object for a general theorem is the switching class of J(E), not
  the raw hot-edge or span histogram.

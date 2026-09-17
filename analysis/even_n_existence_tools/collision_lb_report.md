# Collision-counting lower bound on min bad_triples — result (2026-07-20)

## Goal (Direction ①)
Replace the expensive `2^W` orientation brute force (`geometry_and_defects`
over all `2^{#witness}` orientations) with a **guaranteed-valid combinatorial
lower bound** `LB ≤ min_orientation bad_triples`, cheap enough to run on CPU
(numpy) so that candidates with `LB > 0` are declared non-solutions without
the brute force.

## Method
For a V20 `k=14` survivor = a 37-slot 2-factor with a free-orientation
witness mask `m` (`W = popcount(m)` slots have free bit), the true minimum
bad_triples over orientations equals

    min_σ  Σ_{distinct cell-triples T} cost_T(σ|_T)      (∗)

where `cost_T` = number of collinear lift-combos among the three cells' C4
orbits (64 = 4³ rotation combos), counting only triples of 3 **distinct**
148-grid points.  (Orbits are disjoint in a valid V20 config, so (∗) holds
exactly.)

Two valid lower bounds were implemented:

- **LB1** (per-triple independent min):
  `LB1 = Σ_T  min_{local orientations of T∩free} cost_T(local)`.
  Valid because each triple's contribution ≥ its local min, so the sum over
  any global σ ≥ Σ_T local-min.

- **LB3** (coupled per-cell / per-pair min, strictly dominates LB1):
  group triples by free-slot count and minimise each free cell's whole
  *star* jointly, and each free *pair*'s triples jointly:
  `LB3 = S0 + Σ_{free c} min_{b_c} star_c(b_c) + Σ_{free (c,d)} min_{b_c,b_d} pair_{c,d}(b_c,b_d)`.
  Valid by `min_x(f+g) ≥ min_x f + min_x g`; the 3-free triples (pure global
  coupling) contribute 0 to the bound.

Both are pure numpy over the 64 lift-combos; **no GPU needed, low CPU**.

## Correctness checks
- On the fully-fixed base config (`m=0`): `LB1 = LB3 = 20` = the exact base
  bad_triples (sanity).
- On all 19 `k=14` survivors (`true_min` = exact `2^14` brute force result):
  `LB1 = LB3 = 0` for **every** survivor, and `LB ≤ true_min` holds for all
  (0 invalid), so the bounds are correct, just non-informative here.

| base | #survivors | true min range | LB1 | LB3 |
|------|-----------|----------------|-----|-----|
| v20_01 | 3 | 48–88   | 0 | 0 |
| v20_02 | 4 | 48–84   | 0 | 0 |
| v20_03 | 6 | 52–104  | 0 | 0 |
| v20_04 | 4 | 60–80   | 0 | 0 |
| v20_05 | 2 | 80–88   | 0 | 0 |
| v20_06 | 0 | —       | — | — |

## Conclusion (negative result for the prescreen)
For these **tight** V20 `k=14` candidates the unavoidable bad triples
(48–104) are **purely an emergent property of global 3-free-cell orientation
coupling**: every individual triple (and every free cell's star, every free
pair's triples) can be made non-collinear by *some* local orientation choice,
so any decomposable bound that does not solve the full `2^W` CSP is exactly 0.

Therefore:
- A **guaranteed-valid cheap LB cannot replace `2^W`** for these candidates.
- The brute force (or a smarter exact method) remains necessary for `k≥15`
  certification — but note the orientation check itself is cheap: `2^14` for
  `k=14`, `2^15` for `k=15`, both trivial even on CPU.
- The **real bottleneck for `k≥15`** is *not* the orientation check but the
  CUDA root-candidate prefilter (`v20_gpu_mask_prefilter.exe`): it enumerates
  fixed-weight masks into a 300 M-survivor buffer and **overflows** at the
  ~1.8×10⁹ root candidates for `k≥15` (RTX 4070 12 GB). The orientation LB
  does not address this.

## Files
- `collision_lb.py` — LB1 implementation + 19-survivor validation runner.
- `collision_lb3.py` — LB3 implementation + 19-survivor validation runner.
- `collision_lb_results.json`, `collision_lb3_results.json` — raw outputs.

## Recommended next direction (NOT yet started)
Enable `k≥15` by making the CUDA prefilter **multi-pass**: partition the
`~1.8×10⁹` `k=15` root candidates into ≤300 M chunks (e.g. by mask prefix) and
run several GPU passes, merging survivors — GPU time is free per user. This
requires editing the NVRTC-JIT prefilter kernel/exe (nvcc unavailable → host
C++ links `cuda.lib`/`nvrtc.lib`, kernel via NVRTC). Awaiting user go-ahead
before this larger build.

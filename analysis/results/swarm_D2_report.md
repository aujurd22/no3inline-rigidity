# Swarm D2 — Heatmap-biased multi-restart SA + hinted CP-SAT for m=37

**Date:** 2026-07-15
**Direction:** D2 (attack the (X)=72 basin via known-solution heatmap bias + many seeds + hinted CP-SAT)
**Engine:** validated `solver_theory_m37.Board` (Th-44) and `solver_cpsat_m37` (CP-SAT), managed pythons as specified.

---

## 1. What was tried

1. **Heatmap prior.** Parsed `hint_data.js` / `results/hint_heatmap_m37.json` (16 known rot4-NTIL
   solutions, m=5..19,36). Built `cell_freq[i][j]` and `edge_freq{u,v} = H[i][j]+H[j][i]`.
2. **Heatmap-biased SA.** New script `swarm_D2_sa.py`:
   - Biased 2-factor init (random 2-factor, then two_switch hill-climb on edge-frequency sum).
   - Biased orientation init (prefer higher-frequency cell).
   - Biased SA acceptance: objective `= total_bad - GAMMA*heat_sum(cells)` with `GAMMA`
     decaying 1→0 so early search is pulled to the heatmap region, then pure `total_bad`.
   - Biased move *proposal*: edges chosen weighted by `(1+edge_freq)`. Optional defect-directed.
   - **24 seeds × 120 s, 16 workers (ProcessPoolExecutor).** Every returned best independently
     re-validated with `Board.verify_total()` (brute force).
3. **Hinted CP-SAT (background).** Found and **fixed a real bug** in `solver_cpsat_m37.py`: a loop
   edge `(u,u)` was contributing degree 4 instead of 2 (appended twice), which would make any
   loop-requiring solution falsely UNSAT. Fixed so a loop adds a single weight-2 entry.
   Built 10 valid loop-free 2-factor hints by a 2-switch extension of the m=36 solution
   (remove one m=36 edge `{a,b}`, add `{a,36}`,`{b,36}`) under identity/180° vertex relabelings.
   Launched 3 hinted CP-SAT solves (`k0s0`, `k0s16`, `k2s8`), each `--time 1200` (~20 min), in background.

## 2. Key finding: the heatmap prior is LOW-SIGNAL at m=37

- Max cell frequency = 1.0 (cell (33,3) across all 16 solutions); most cells 0.25–0.5.
- The known (X)=72 config shares **0%** of its edges with cells of frequency ≥ 1.0, and only
  5/37 edges with the top-30 heatmap edges.
- Conclusion: known small-m solutions barely inform the m=37 structure; the extrapolation is
  unreliable for the open case.

## 3. SA result — did NOT escape the 72 basin

| metric | value |
|---|---|
| seeds | 24 (×120 s, 16 workers) |
| **global best `total_bad`** | **92** |
| escaped 72? | **No** (`n_escaped_72 = 0`) |
| found (total_bad=0)? | No |
| per-seed `total_bad` range | 92 – 144 |
| all configs `verify_total == best_bad`? | **Yes (no false positives)** |

The biased sweep landed in HIGHER-bad basins (92–144) than the known 72 floor. Because the prior
is near-uniform, biasing *toward* it pulled search **away** from the good (72) basin rather than
helping escape it. The unbiased engine baseline (`solver_theory_m37` long run) already reaches 72,
so 72 remains the best known residual.

## 4. CP-SAT (in flight)

3 hinted runs launched (task ids EFw9er, duuNGD, Srh7U1), ~20 min each, results written to
`results/swarm_D2_cpsat_{k0s0,k0s16,k2s8}.json`. Line-set cache (`cpsat_linesets_m37.pkl`, 33 MB)
is prebuilt, so solve time is the bottleneck, not precompute. Will report objective/status on
completion (all use the loop-bug-fixed model).

## 5. Breakthrough?

**No.** m=37 remains OPEN. No `total_bad=0` config found; no impossibility proof; no new theorem.
All SA candidates were independently brute-verified and are consistent (no incremental-drift
false positives).

## 6. Next-step suggestions

1. **De-emphasize the heatmap prior at m=37** — it is too sparse to guide; keep it only as a
   tie-breaker, not a basin driver.
2. **Probe whether 72 is a global floor** with longer/cleaner unbiased SA restarts (uniform move
   selection, `--defect-directed`), tracking the best over many seeds.
3. **New move types to escape 72:** flip + two_switch appear trapped at 72. Try (a) C4-rotating a
   single fundamental cell (a distinct local move), and (b) 3-edge cycle reconnects — these change
   more of the (X) structure at once and may jump basins.
4. **Prioritize the plain CP-SAT sweep** (task ow0cIa) and the loop-bug-fixed model; re-validate
   the fix on m=5..12 before trusting any m=37 UNSAT.
5. A rigorous impossibility proof for m=37 is the real prize, but nothing here constitutes one.

## 7. Artifacts
- `results/swarm_D2_sa.json` — full per-seed SA results (best 92, consistent).
- `results/swarm_D2_hint_m36rot{0,2}_s{0,8,16,24,32}.json` — 10 valid loop-free hints.
- `results/swarm_D2_cpsat_*.json` — CP-SAT outputs (in flight).
- `swarm_D2_sa.py`, `swarm_D2_hints.py` — scripts.
- `solver_cpsat_m37.py` — **loop-degree bug fixed**.

# Swarm D5 — Impossibility / Invariant Attack on m=37 (rot4-NTIL)

**Direction:** D5 (impossibility / invariant proof that no rot4-NTIL exists for m=37).
**Date:** 2026-07-15
**Agent:** parallel sub-agent (D5)
**Engine:** `solver_theory_m37.py` (validated; `Board.verify_total()` independent brute force).
**Status:** NO impossibility proof found. Several genuine invariants proven/verified; all are
satisfiable at m=37, so none obstructs. A serious search attempt could not (yet) beat the
72-config, which is consistent with — but does NOT prove — a global gap.

---

## 1. Engine validation (trust check before any claim)

Independently re-verified every known rot4-NTIL solution with the brute-force checker
`Board.verify_total()`:

| m | verify_total | 2-factor | 4m distinct | rot4 set |
|---|---|---|---|---|
| 5..19, 36 | **0** | True | True | True |

ALL known solutions (m=5..19, m=36) are genuinely (X)-free, legal 2-factors, rot4-symmetric.
The framework and (X)-checker are correct — any invariant tested below is trustworthy, and
any config we later call a solution will be checked by `verify_total()==0`.

---

## 2. Proven invariant D5-P: `(X)-defect count is always EVEN`

**Theorem.** For ANY rot4-symmetric lift set of 4m points on an n=2m board,
`total_bad = Σ_lines C(s,3)` is even.

**Proof (orbit theorem).** Rotate the whole set 90° about the board centre C=(36.5,36.5).
The set is C4-invariant, so this is a bijection on the 4m points. A geometric line L maps to
`rotate(L)` carrying the **same** number s of lifted points (rotation preserves incidence).
`rotate()` has order 2 on undirected lines (180° returns L as a set) and has **no fixed
point** (a line fixed by 90° would need C∈L and direction θ=θ+90 mod 180, impossible). Hence
the defect lines partition into C4-orbit pairs {L, rotate(L)}; each pair contributes
`C(s,3)+C(s,3)=2·C(s,3)`, an even number. Summing over pairs gives an even total. ∎

**Consequence.** A (X)-free config needs `total_bad=0`, which is even — so the parity
invariant is *satisfied* by every (X)-free config and therefore **cannot rule out m=37**.
It does, however, give a cheap validity filter: any claimed config with odd `total_bad`
is automatically invalid.

**Verification.**
- On the 72-config: 72 defect lines = **36 C4-orbit pairs, 0 fixed**; `total_bad=72` (even).
- On 10,000 random m=37 2-factor configs: **0** had odd `total_bad`. (D5-P holds empirically
  to the sampling limit.)

Number of defect lines is likewise always even (same orbit-pairing).

---

## 3. Meta-theorem: all ADDITIVE invariants are forced constant

**Theorem.** Let f be any function on grid points. For a single C4-orbit
O={p,Rp,R²p,R³p}, `Σ_{q∈O} f(q)` depends only on the cell, not on (X)-freeness. Hence any
additive invariant `Σ_{4m lifts} f(point)` reduces to a function of m (and n) ALONE, identical
for every rot4 configuration at fixed m.

**Implication.** Coordinate-sum, moment-sum, mod-p residue-occupancy, etc. are forced to their
m-dependent value for ALL configs ((X)-free or not). They **cannot** distinguish (X)-free from
non-(X)-free and so cannot obstruct m=37.

**Verification.** For p=2, the four residue classes (x mod 2, y mod 2) each receive exactly
m=37 of the 4m=148 points for *every* config (each orbit contributes one point to each class,
since 90° rotation cycles the 4 classes). The 72-config occupancy is `[37,37,37,37]` — exactly
the forced value. (Confirmed for p=3,5 as well.)

**Conclusion for D5.** Any genuine impossibility proof must be **non-additive / structural**
(exploiting pairwise or higher-order relations, like D5-A), not a sum/parity-of-coordinates
invariant.

---

## 4. Non-additive invariant battery (tested on all known solutions)

Any invariant that would rule out m=37 MUST hold for every known (X)-free solution (m≤36).
We tested the following; results:

| invariant | holds on all known | satisfiable at m=37 | obstructs? |
|---|---|---|---|
| D5-P (total_bad even) | yes (0 is even) | yes | no |
| D5-A: base vectors pairwise non-parallel & non-perpendicular | **yes (0 violations everywhere)** | **yes (72-config: 0)** | no |
| diagonal constraint: #cells on the two main diagonals ≤ 1 (a concrete face of D5-A) | **yes (0 or 1 everywhere)** | yes (72-config: 0) | no |
| loop-count parity | varies (0 or 1) | n/a | not universal |
| odd-cycle-count parity | varies | n/a | not universal |
| #distinct base directions = m | **yes (always)** | yes (37/37) | no |

**D5-A** (prior, re-confirmed here): cells' base vectors v_j=(x_j−36.5, y_j−36.5) must be
pairwise non-parallel and non-perpendicular — otherwise a centre line of that direction would
carry ≥4 collinear lifts. This is the *complete* centre-line obstruction. It is easily
satisfiable at m=37 (37 distinct directions, no pair 90° apart, chosen from the many available
odd/odd rational directions). So D5-A does NOT obstruct.

**Diagonal constraint** is just D5-A restricted to the 45°/135° centre lines: a cell on y=x
is a loop (u=u, dir 45°) or a sum-73 edge (u+v=73, dir 135°); at most one such cell is allowed.
Holds on all known solutions; 72-config has 0.

---

## 5. Attempted structural reduction (honest negative)

I attempted to force a contradiction at m=37 from the conjunction:
   (2-factor on 37 vertices, necessarily containing ≥1 odd cycle)
   + D5-A (37 pairwise non-par/non-perp base vectors)
   + (X)-free (no 3 of 4m collinear on non-centre lines).

Findings:
- m=37 odd ⇒ the 2-factor has ≥1 odd cycle. The 72-config is in fact a **single 37-cycle**.
  But odd-cycle existence is *not* in tension with (X)-free (odd m≤19 solutions exist and are
  (X)-free; e.g. m=19 has 3 odd cycles).
- D5-A is the only centre-line condition and is satisfiable; non-centre (X) conflicts are
  generic and sparse (avg 0.58 defects/cell on random factors, per `conflict_hypergraph_params`
  — the full (X) hypergraph has N≈2.8M size-3 edges but is extremely sparse per cell, so naive
  LLL fails, as already established in D3).
- **No double-counting lower bound > 0** on `total_bad` could be derived: random configs have
  ~265 (X)-triples but optimised configs reach 72, and there is no proven barrier between 72
  and 0. The 72 figure is a *deep local minimum* (flip-only greedy is stuck; two-switches
  needed), not a proven global minimum.

**Conclusion:** no non-additive invariant or structural reduction currently obstructs m=37.
An impossibility proof, if it exists, must be genuinely global and go beyond the invariants
catalogued here. This is an honest negative result, not a fabricated proof.

---

## 6. Search probe: is 72 beatable? (tests the impossibility hypothesis)

If a search reaches `total_bad < 72` (ideally 0), that **refutes** impossibility for m=37.
Two searches launched (results filled in on completion):
- `swarm_D5_search2.py`: ILS seeded from the 72-config, two-switch-biased, defect-directed, ~24 min.
- `swarm_D5_search3.py`: fresh random starts, defect-directed SA, ~20 min.

(Results appended when available.)

---

## 7. Honest bottom line

- **Breakthrough (impossibility proof):** NOT achieved.
- **Breakthrough (valid total_bad=0 config):** NOT achieved in this run.
- **Genuine partial results:**
  1. D5-P proven + verified: `total_bad` (and #defect lines) always even.
  2. Meta-theorem proven: all additive/mod-p invariants are forced constant by rot4 symmetry
     → cannot obstruct; any impossibility proof must be structural/non-additive.
  3. D5-A + diagonal constraint re-confirmed as the complete centre-line obstruction,
     satisfiable at m=37.
  4. Established that the known-solution set used (m=5..19,36) satisfies every tested
     invariant, so no simple invariant rules out m=37.

## 8. Next-step suggestion

The only path that can *resolve* m=37 either way:
- **(a) Keep searching** with more compute / better moves (e.g. triple-switches, GPU kernel
  like `gpu_ntile.exe`, or a hint-heatmap-biased 2-factor generator) to push below 72.
  Beating 72 (→0) is a constructive existence proof; failing after a much larger effort
  strengthens the impossibility case.
- **(b) Pursue a genuine structural theorem**: the sparsity of the (X) hypergraph (avg 0.58
  defects/cell) suggests a *probabilistic / nibble* existence proof may be the right tool,
  not an invariant. Reframe D5 as "prove existence via Rödl nibble on the (X) hypergraph
  restricted to 2-factors" rather than "find a parity obstruction". This was flagged earlier
  (conflict_hypergraph.md §4.1) but the global 2-factor constraint makes the nibble non-trivial.
- **(c)** Verify the 72-config is truly a *global* minimum by exact methods on a reduced
  subgraph (fix most of the 2-factor, exhaustively search a critical ~10-vertex subgraph) —
  a feasible exact sub-problem that could either find <72 or prove the surrounding basin is
  minimal.

**Files written:** `swarm_D5_validate_invariants.py` (+JSON), `swarm_D5_quick.py`,
`swarm_D5_search2.py` (+JSON), `swarm_D5_search3.py` (+JSON), this report.

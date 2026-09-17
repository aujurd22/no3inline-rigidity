# Costas arrays of order 32 and 33 — the open frontier, attacked

**Date:** 2026-07-13 (continuation)
**Status:** CP-SAT attacks **running** (background).  Theoretical narrowing via the
complete D₄ classification (Theorem C) is complete; the famous open orders 32/33
remain **OPEN** pending the solver.

---

## 1. What the complete classification (Theorem C) tells us about 32/33

Theorem C (capstone, `costas_symmetry_theorem.md` §10) proved: for `n ≥ 3` a
Costas array's symmetry `G ≤ D₄` lies in `{id, D, AD}`.  Therefore **any**
Costas array at orders 32 or 33, *if symmetric*, must be of diagonal-involution
type `D` (transpose, `π = π⁻¹`) or `AD` (anti-diagonal).  Rotational (`C2`,`C4`)
and axis-reflection (`H`,`V`) symmetries are **provably impossible** there (by
Theorems C1, R, C6).  This is a sharp prior: the symmetry search space for 32/33
is narrowed to two types (plus the generic asymmetric case), not the full D₄
lattice.

Orders 32 and 33 both satisfy the only non-trivial congruence of the admissible
types (`32 ≡ 0 (mod 4)`, `33 ≡ 1 (mod 4)`), so no congruence excludes them; the
Welch (`p−1`) and Golomb (`p²−1`) finite-field constructions simply miss both
(`31−1 = 30`, not 32/33; `p²−1 = 32/33` has no prime `p`), which is why 32/33 are
the first orders with **no known Costas array**.

---

## 2. A tempting-but-FALSE impossibility argument (corrected here)

A natural first move is to use the **Rickard bridge** (symmetric Costas ↔
Golomb ruler) plus a counting bound to rule out the *symmetric* route at 32/33:

> *Naive claim:* a symmetric (transpose) Costas of odd order `n = 2m−1`
> corresponds to a Golomb ruler of order `m` on `Z_n`; such a ruler needs
> `C(m,2)` distinct non-zero differences among only `n−1` residues, so for
> `m = 17` (`n = 33`) we would need `136` differences in `32` residues →
> **impossible** → no symmetric Costas at 33.

**This is FALSE, and `symmetric_costas_golomb.py` shows why.**  Enumerating
transpose-symmetric Costas arrays gives:

```
 n=7  (m=4):  4 symmetric Costas  (need C(4,2)=6 diffs)
 n=9  (m=5):  0 symmetric Costas  (need 10 diffs)   <- gap
 n=11 (m=6):  2 symmetric Costas  (need 15 diffs)   <- EXISTS despite 15 > 10
 n=13 (m=7):  4 symmetric Costas  (need 21 diffs)   <- EXISTS despite 21 > 12
```

So symmetric Costas **do exist** at orders 11 and 13 where `C(m,2) > n−1`.  The
Rickard correspondence is therefore a **periodic Golomb ruler of period `> n`**
(not a ruler on `Z_n`); the period accommodates the `C(m,2)` differences without
failing a modular count.  Consequently the modular-density argument does **not**
rule out symmetric Costas at 32/33.  The open problem stays live on the
symmetric route as well.

*(Honesty note: the n=9 gap — 0 symmetric Costas found — is itself interesting
and may be a genuine absence; it is reported here as an empirical observation,
not a theorem.)*

---

## 3. The decisive route: exact CP-SAT in the distinct-displacement space

The only remaining lever is a direct satisfiability attack.  We built
`cpsat_costas.py` — an **exact** CP-SAT encoder for the general Costas problem:

- `x[i][j] ∈ {0,1}`, row/col exact-1;
- for every displacement `(dx,dy)` with ≥2 ordered cell-pairs, the number of
  active pairs is `≤ 1` (auxiliary `p = x[a][b] ∧ x[c][d]` booleans).

This is the Costas analogue of the per-line at-most-2 NTIL encoder
(`cpsat_m37.py`): both are exact re-encodings of the defining extremal
condition as a clean CSP.  Validated sound + reachable on `n = 1..11` (all
`OPTIMAL`, `is_costas = True`).

**Running attacks (background, 2026-07-13):**
- `cpsat_costas.py --n 32` → task `Pwgapl`
- `cpsat_costas.py --n 33` → task `TDlR4X`

A `SAT` outcome would produce the first known Costas array at that order (a
blockbuster resolving a 90-year-old gap); `UNSAT` would prove non-existence
(equally historic).  Either result auto-notifies.

A **symmetric-targeted** variant (add `x[i][j] = x[j][i]`, i.e. `π = π⁻¹`) is the
most *informed* attack given Theorem C — any symmetric witness at 32/33 must be
`D`/`AD`.  It is a strict subset of the generic search and is the natural next
launch once the generic runs report.

---

## 4. Files

- `analysis/cpsat_costas.py` — exact general Costas CP-SAT encoder (validated).
- `analysis/symmetric_costas_golomb.py` — Rickard-bridge exploration (shows the
  modular-density impossibility is FALSE; periodic ruler, period `> n`).
- `analysis/costas_symmetry_theorem.md` §10 — Theorem C (classification prior).
- `analysis/cpsat_costas_symmetric.py` — C4-symmetric Costas encoder (R8-C; the
  rotational route, already ruled out by C6/R, so not the live route for 32/33).

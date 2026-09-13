# Records Audit 2026: n=76/71/73 and the 2026 solution wave

**Date:** 2026-09-04. All checks independent of the discoverers' pipelines.

## What was audited

1. **Heule records** downloaded and decoded from the Flammenkamp database:
   - n=76 rot4 (2026-08-10, current record for largest solved even board),
   - n=71 rct4 (2026-08-17), n=73 rct4 (2026-08-19).
   Decoding via the 72-character extended alphabet (`.few` encoding, column values 62..71);
   see [`analysis/tools/decode_few.py`](../analysis/tools/decode_few.py).

2. **Full theorem audit (7/7 passed) on n=76:**
   - six-class census rigidity at m=38 — first *predictive* verification of the identity
     `4(N1+3*sum Ni) = 6 C_col + 12 n^2 - 4n` beyond n=20: the solution sits exactly on the
     diagonal bound `N = (3m^2-2m, 0, m^2, 0, m^2, m^2)`;
   - Th-56 intercept-quadruple criterion, Th-58 Sidon condition,
   - CRT rainbow property (all point pairs distinctly coloured, exact C_col = 0),
   - Motzkin path statistics and irreducibility (fz = n-1),
   - half-turn census extension to odd records n=71/73,
   - cycle structure: n=72 record = pure Hamiltonian, 0 loops — correcting "large-n solutions
     have exactly 1 loop" to "0 or 1".

3. **The 2026 solution wave:** ~860 new solutions (Davies' ChatGPT-assisted constructions
   n=21..57, Kudriashov + Claude rot2, Riley GPU enumerations) re-verified independently;
   all pass.

4. **Negative/archival findings:** the local `n76_rot4.txt` in the unified cache was a stale
   artifact (a shifted n=72 solution) — superseded by the decoded true record; the
   "n >= 33 solutions satisfy the C4 identity" claim is refuted by Davies' iden solutions and
   restated as *symmetry emergence* (the C4 identity is equivalent to half-turn symmetry).

## Coverage caveat discovered later (Sep 2026)

The four-tight census built on this audit missed n=6..9 rot2 files (lexicographic glob +
time-box truncation). See [`FOUR_TIGHT_EXCEPTION.md`](FOUR_TIGHT_EXCEPTION.md) for the
counterexample this hid, and for the corrected coverage discipline.

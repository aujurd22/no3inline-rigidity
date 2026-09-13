# Splice Construction: the Nine-Class Covering Lemma (height-1 clean C4 first shell)

**Date:** 2026-09-04 (night research T5). Status: hand-proved theorems (9/9 residue classes) +
exhaustive machine verification to m = 50,000, zero exceptions.

## Statement

For every even `m`, the splice construction on an affine permutation of order `m+1`
(multiplier `m-1`, bias `m-1`, one deleted point) produces `m` C4-orbit representatives whose
**height-1 palette loads are all <= 2** — i.e. the multiset of colour values

- `u = 2m-1-a-b`
- `v = |a-b|`

over the surviving cells (with the loop cell counted twice in colour 0) never exceeds
multiplicity 2. By the height-1 palette theorem this is exactly the condition for the
resulting C4-symmetric configuration to have *no slope-±1 collinear triples within the first
shell* — the clean first shell required by the splice route to All-Even.

This proves the **even-m splice conjecture** for all nine residue classes mod 18
(m ≡ 0, 2, 4, 6, 8, 10, 12, 14, 16 mod 18), via nine covering lemmas (groups A–E):

- **Group A (m ≡ 0 mod 6; classes r ∈ {0,6,12}):** deleted point 0. Unique loop at
  f = m/3; v-multiplicity-2 values exactly `{0} ∪ {3,6,...,m/2}`; unique u-load-2 at
  `u = m/2 + 1`. Proof uses only 3 | m and oddness of m+1.
- **Groups B–E (m ≡ 4, 10, 16 / 2 / 8 / 14 mod 18):** same programme with deleted point m;
  the relabeling regime switches (deleted = 0 → shift r-1; deleted = m → identity), and each
  lemma proves the multiplicity tables branch-by-branch against the modular arithmetic of
  the affine map.

Each lemma states closed-form multiplicity tables for `u` and `v`, proves every load <= 2,
and identifies the exact set of load-2 values; all tables were cross-checked numerically
against `lemma_spec.json` (e.g. m = 1512) and by brute force over every m in the class up to
50,000 with zero exceptions.

## Why it matters

The splice route to All-Even needs, for every even board, a *clean first shell* on which the
direction-fiber capacity system (`Bz = 2, Az <= 2`) can be seeded. The nine covering lemmas
turn "clean first shell for all even m" from a conjecture (verified exhaustively) into a
theorem family, reducing the open part of the splice programme to shell *coupling* (T32/T33:
the obstruction is now localized in slope-±1 shell interaction, cf. Th-56/Th-58).

## Files

- Lemma notes (Chinese lab notebook): `night_research_20260904/outputs/T5_splice/lemma/`
  (groupA–groupE, with per-class multiplicity tables)
- Verifier: `splice_extend.py` (brute force m <= 50,000)

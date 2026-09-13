# Research notes (Aug-Sep 2026)

Curated English summaries of the second research campaign (nocturnal autonomous sessions,
2026-09-03..13). Chinese lab notebooks with full derivations live offline; these documents
are self-contained at theorem-statement level.

| Document | Content |
|---|---|
| [RECORDS_AUDIT_2026.md](RECORDS_AUDIT_2026.md) | Independent audit of the n=76/71/73 records and the 2026 solution wave; census rigidity verified predictively at m=38. |
| [SPLICE_COVERING.md](SPLICE_COVERING.md) | The nine-class covering lemma: clean height-1 C4 first shells for every even m — hand-proved (9/9 classes), machine-checked to m=50,000. |
| [FOUR_TIGHT_EXCEPTION.md](FOUR_TIGHT_EXCEPTION.md) | Counterexample to half-turn 4-tight universality (n=8, in-corpus), its parity-confinement mechanism, and the refined conjectures (T-prime-F2, canon-F1, T41-A). |

## New tools

- [`analysis/census/fourtight.py`](../analysis/census/fourtight.py) — four-tightness census
  over the unified solution corpus (39,631 solutions; resumable; cross-validated).
- [`analysis/tools/decode_few.py`](../analysis/tools/decode_few.py) — decoder for the
  Flammenkamp `.few` extended alphabet (records n > 62).
- [`analysis/tools/audit_batch.py`](../analysis/tools/audit_batch.py) — batch theorem audit
  for decoded solution files.
- [`analysis/tools/parity_lift_lazy.py`](../analysis/tools/parity_lift_lazy.py) — lazy
  cutting-loop solver for the parity-lift problem (attacked n=16; cut libraries persisted).
- [`lean/NTIL.lean`](../lean/NTIL.lean) — Lean 4 formalization (pure core, no mathlib):
  Theorems 1a/1b with complete proofs; computer-assisted facts isolated as axioms with
  Python oracles.

## Headline open problems after this campaign

1. **T41-A:** parity-confined half-turn solutions exist only at n=8 (0/478 coarse-lift
   survivors for n=10..20).
2. **T-prime-F2:** `min|F2| = 4` universally for half-turn solutions (counterexample-free,
   including the n=8 exception).
3. Splice shell coupling (slope-±1 shell interaction), per Th-56/58.

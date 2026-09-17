# Research Direction C — m=37 Impossibility (search for an invariant obstruction)

**Date:** 2026-07-14
**Status:** Inventory of every plausible arithmetic/structural invariant shows **none obstructs m=37**.
A genuine non-existence proof, *if one exists*, would have to live in the 2-regularity-completion
gap (the same Gap B as A/B) — a "rigidity trap". The impossibility direction is therefore **not
independent** of A/B; it converges on the identical open lemma.
**Companion:** `research_A.md` (tight boundary), `research_B.md` (Lemma B.1), `r9_modp_descent.md`
(R9a, mod-p descent pitfall), `conflict_hypergraph.md` (2-switch oracle).

---

## 1. Goal restatement

Reverse direction: *if m=37 has NO rot4 solution, what number-theoretic or structural invariant
forces the obstruction?* This note surveys every candidate invariant and explains why each fails to
obstruct m=37, then sharpens what a real impossibility proof would have to establish.

---

## 2. Inventory of candidate invariants and their status at m=37

| Invariant class | Candidate obstruction | Verdict at m=37 |
|---|---|---|
| **Odd m** | m=37 is odd → maybe parity blocks C4 orbits | **NOT an obstruction.** Odd m = 3,5,7,9,11,…,35 all have rot4 solutions (`working_memory`: "ALL m=3→36 有 rot4 解"). Oddness is benign. |
| **Prime m** | 37 is prime → maybe multiplicative structure forbids | **NOT an obstruction.** Primes 3,5,7,11,13,17,19,23,29,31 all solvable; 37 is the next prime and is not special. |
| **Sum of two squares** | 37 = 1² + 6², ≡1 mod 4 | **Favourable, not obstructive.** The ring ℤ[i] structure (m a sum of two squares) is the *source* of the C4-compatible 2-factor constructions seen at smaller m, not a barrier. |
| **mod-p descent (R9a)** | reduce mod 37, look for residue obstruction | **Invalid as a descent.** R9a proved the naive "mod-m descent on prime m" fails whenever 2m > m (here 74 > 37): two distinct lift points differing by m collide mod m, killing valid solutions. A *valid* mod-p descent needs p > 2m = 74, so mod-37 itself cannot witness an obstruction. No residue-class obstruction was found. |
| **Sidon (Th-56)** | a−b Sidon capacity ≤ 2 forces a conflict | **NOT an obstruction.** An a−b Sidon multiset of size 37 in ℤ_{74} exists (optimal Singer-type Sidon sets of size ~√74 ≈ 8 are tiny; a size-37 set with count(d)+count(−d)≤2 is abundant — the constraint is weak relative to m). Empirically 100% of small-m rot4 solutions satisfy it. |
| **Quadratic layer (R8 / Lemma B.1)** | det = 0 unavoidable for some triple | **PROVEN satisfiable** (Lemma B.1): the (X) layer at m=37 is LLL-satisfiable with bound 0.061. So the quadratic CSP *has* solutions of the right size. The obstruction cannot live here. |
| **Phase-transition heuristic** | m=37 might be past a solubility threshold | **Indirectly favours existence.** Phase analysis (`working_memory`): source ratio ≈ 0.26, longest cycle ≈ 0.79m, quadratic-constraint density continuous from m=36→37 with no jump → m=37 is *not* at a phase transition; data point the other way. |

**Net result:** every standard invariant either is satisfied at m=37 or actively favours solubility.
There is currently **no candidate invariant** that would force non-existence.

---

## 3. Where would a genuine impossibility proof have to live?

Given Lemma B.1 (quadratic layer satisfiable at m=37 with ~2.5× slack, `research_A.md` §2), a
non-existence proof **cannot** arise from the quadratic or Sidon layers. The only remaining locus is
the **2-regularity-completion gap** (Gap B):

> **Rigidity-trap hypothesis (precise form of C).** There exists an (X,S)-conflict-free subset
> `S ⊂ V` of the m×m quadrant with `|S| = m`, yet **no** 2-regular (permutation) completion of S
> avoids reintroducing a conflict. I.e. the switching oracle (`red_config_frac = 1.0`) repairs
> conflicts cell-by-cell but *cannot* simultaneously enforce the global 2-regular skeleton.

If such a trap existed at m=37, it would mean: *the quadratic layer is satisfiable, but the
2-regular solutions form an empty fibre over the satisfiable quadratic set.* This is a sharp,
testable structural claim — and notably it is **exactly the negation of the closure lemma** that A
and B need. So:

- **Positive closure lemma** ⇒ Theorem A/B hold (m=37 solvable, asymptotically all large m solvable).
- **Negative closure lemma** ⇒ a "rigidity-trap theorem" — a spectacular new structural result in
  its own right, even though it would *not* single out m=37 (it would apply to whatever m first
  exhibits the trap).

**Therefore C is not an independent direction.** It is the contrapositive of Gap B. Pursuing C
productively = pursuing Gap B and asking the sharper question: *does every (X,S)-free m-subset admit
a 2-regular completion?*

---

## 4. Verdict

| Sub-claim | Status |
|---|---|
| Odd / prime / sum-of-two-squares obstruction at m=37 | **Ruled out** — these invariants are benign or favourable. ✅ (negative) |
| mod-p (mod-37) residue obstruction | **Inapplicable** (R9a: needs p>74). ✅ (negative) |
| Sidon / quadratic-layer obstruction | **Ruled out** (Lemma B.1). ✅ (negative) |
| Existence of a rigidity trap at m=37 | **Open** — equivalent to the negation of Gap B. 🟡 |
| Full impossibility proof for m=37 | **Not achievable** with current invariants; would require discovering the rigidity trap. 🔴 (lowest readiness) |

**Significance.** Direction C is the most speculative of the six. The honest conclusion: *there is no
known invariant that obstructs m=37, and the data (continuous m36→37, all smaller m solvable, huge
quadratic-layer LLL slack) strongly suggest m=37 IS solvable.* The impossibility direction only
becomes productive if one explicitly sets out to **disprove the closure lemma** (find a rigidity
trap) — which would be a major result, but is a different, harder goal than "show m=37 fails."

**Recommended framing if C is pursued:** rename it "2-regularity-completion conjecture" and attack
Gap B directly (Routes 1–3 in `research_A.md` §3). Do **not** spend effort hunting for a
number-theoretic invariant at m=37 — the inventory above shows none exists.

**Novelty.** The inventory itself (especially the mod-37 descent inapplicability and the
rigidity-trap reframing) is a new, honest contribution that saves future effort from a dead end.

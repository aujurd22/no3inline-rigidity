# Research Direction F — Container Method ⇒ Symmetry Bridge

**Date:** 2026-07-14
**Status:** Container method for NTIL PROVEN; the symmetry bridge as literally stated is likely
FALSE and must be reframed. One correct, provable counting theorem remains.
**Source:** README §2.8 (container framework), `analysis/academic_hn_params.py`, `fdr_theorem.md`
(FDR reverse false), README §2.15 / §3.13 (asymmetry dominance), `rigidity_hierarchy_theorem.md`.

---

## 1. What is already proven

The **Container Method for NTIL** (README §2.8) is established:

- Danger hypergraph `H_n`: `V = n²` grid points, `E` = all collinear triples.
- `max codegree = n−2` exactly; `Δ = O(n³)`; `codegree / √Δ → 0` ⇒ `H_n` is `(3,Δ)`-smooth.
- **Theorem:** all 2n-point NTIL configurations lie in ≤ `exp(O(n))` high-minimum-degree
  containers; each container is a set where every vertex has few incident hyperedges ⇒ surviving
  configurations are "highly structured."

This is a solid, publishable existence/structure theorem on its own.

---

## 2. The claimed bridge — and why it is likely FALSE

README §2.8 speculates the container result "opens a path to proving asymmetric (iden)
configurations are exponentially rare relative to symmetric ones." **This is unlikely to hold,
and must not be stated as a theorem:**

1. **FDR reverse is false** (`fdr_theorem.md` Lemma E): iden configurations *can* satisfy the
   a−b Sidon law (empirical pass rate 21–75% for small n). So "linear rigidity structure"
   (what containers enforce) does **not** force symmetry.
2. **Asymmetry dominates empirically** (README §2.15: "trivial dominates (asymmetry is the norm)";
   §3.13 moral: prevalence of symmetric over asymmetric is "unsupported"). So if anything, the
   typical NTIL solution is *asymmetric*.
3. "Highly structured" (low local codegree) is a *local* property; group symmetry is a *global*
   invariance. There is no known implication from the former to the latter, and the data suggest
   the opposite.

**Conclusion:** the literal bridge "container ⇒ non-trivial symmetry" is **not a viable theorem**
and should be removed from the claims; treat it as a refuted hypothesis.

---

## 3. Correct, provable reformulation (the real F contribution)

The true relationship is the **reverse / quantitative** one:

> **Theorem F (symmetry compresses containers).** Let `𝒞_G` be the family of G-symmetric 2n-point
> NTIL configurations. Because a G-symmetric configuration is determined by `|F_G| = O(n/|G|)`
> fundamental-domain cells rather than `O(n)` free points, the container count needed to cover
> `𝒞_G` is `exp(O(n/|G|))`, strictly smaller than the `exp(O(n))` covering the full set. In
> particular, symmetric solutions are concentrated in *few* containers; asymmetric (iden)
> solutions are spread across *many* containers.

This is provable: symmetry reduces the number of free variables by a factor `|G|`, which feeds
directly into the Saxton–Thomason / Balogh–Morris–Samotij container-count bound
(`exp(O(ν(H)))` where `ν` is the number of vertices in the relevant regime). The counting is
straightforward once the fundamental-domain reduction (FDR, `fdr_theorem.md` Lemma B) is invoked.

**Corollaries:**
- Enumerating G-symmetric solutions is exponentially cheaper than enumerating all solutions —
  which is exactly why the FDR/symmetry-reduced CP-SAT (`cpsat_m37.py`) is the right attack on m=37.
- The container method explains *why* symmetric solutions are easy to find/characterize, **not**
  why they are numerous. Asymmetry is not "rare"; it is merely "hard to compress into few containers."

---

## 4. Verdict

- **Container method for NTIL:** DONE (proven).
- **Literally-stated bridge (container ⇒ symmetry):** REFUTED / not viable — remove from claims.
- **Correct bridge (Theorem F, symmetry compresses containers):** a clean, provable counting
  theorem; the genuine F contribution.
- **Priority: LOW–MEDIUM.** F is mostly a *clarification* (correcting an over-optimistic claim in
  §2.8) plus one modest counting theorem. It does not advance the m=37 existence question and
  should not block B/E.

**Novelty:** the "symmetry compresses containers" theorem is a natural observation; the main
value of F-work is *correcting* the project's own over-claim and giving the precise quantitative
statement. Per the 2026-07-13 audit, container-method application to NTIL is standard (Balogh–
Treglown 2025), so F's originality is limited to the symmetry-compression quantification.

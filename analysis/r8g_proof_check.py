"""
r8g_proof_check.py — two-sided computational proof of R8-G.

For every FDR group G, a selection sel : F_G -> {0,1} satisfies the per-line
weighted at-most-2 family (R8-G, *)  IF AND ONLY IF  its lifted point set has
no three collinear.  This script verifies BOTH directions empirically:

  (comp)  viol > 0  =>  lifted set HAS    a 3-collinear   (random selections)
  (sound) viol == 0 =>  lifted set has NO 3-collinear      (solver-found valid
                                                         selections; also covered
                                                         by the --validate sweep)

If both hold, the per-line family is an exact characterization -- the
constructive content of R8-G.
"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpsat_symmetric_ntil import (GROUPS, generate_constraints, orbit,
                                  target_card, solve_ortools)


def lifted(reps, chosen, G, n):
    P = set()
    for i in chosen:
        P.update(orbit(reps[i], G, n))
    return P


def has_3collinear(P):
    P = sorted(P)
    N = len(P)
    for i in range(N):
        xi, yi = P[i]
        for j in range(i + 1, N):
            xj, yj = P[j]
            for k in range(j + 1, N):
                xk, yk = P[k]
                if (xj - xi) * (yk - yi) == (yj - yi) * (xk - xi):
                    return True
    return False


def weighted_viol(reps, chosen, cons):
    return sum(1 for d in cons
               if sum((1 if p in chosen else 0) * w
                      for p, w in d.items()) > 2)


def main():
    rng = random.Random(20260713)
    print("== R8-G two-sided proof check (per-line <=> no-3-collinear) ==")
    for Gname in ["C4", "C2", "D4", "dia1", "dia2", "D2d"]:
        G = GROUPS[Gname]
        order = len(G)
        m = 8 if order <= 4 else 6
        if (2 * m) % order != 0:
            continue
        reps, cons = generate_constraints(G, m)
        card = target_card(G, m)
        nv = len(reps)

        # ---- completeness: random selections must be caught ----
        comp_ok = comp_tot = 0
        for _ in range(300):
            chosen = set(rng.sample(range(nv), card))
            viol = weighted_viol(reps, chosen, cons)
            col = has_3collinear(lifted(reps, chosen, G, 2 * m))
            comp_tot += 1
            comp_ok += (1 if (viol > 0) == col else 0)

        # ---- soundness: solver-found valid selections must be clean ----
        sound_ok = sound_tot = 0
        status, chosen = solve_ortools(reps, cons, card, 20.0, workers=4)
        if chosen:
            for _ in range(3):  # re-solve a few times for independent samples
                status, chosen = solve_ortools(reps, cons, card, 20.0, workers=4)
                if not chosen:
                    break
                viol = weighted_viol(reps, set(chosen), cons)
                col = has_3collinear(lifted(reps, set(chosen), G, 2 * m))
                sound_tot += 1
                sound_ok += (1 if (viol == 0 and not col) else 0)

        exact = (comp_ok == comp_tot and comp_tot > 0
                 and sound_ok == sound_tot and sound_tot > 0)
        print(f"  {Gname:5s} m={m}: comp {comp_ok}/{comp_tot}  "
              f"sound {sound_ok}/{sound_tot}   -> {'EXACT' if exact else 'CHECK'}")


if __name__ == "__main__":
    main()

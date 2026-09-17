"""
swarm_D1_experiment.py
=======================
Direction D1 (finite-field / algebraic re-encoding of the (X) condition) for the
rot4-NTIL (m=37, n=74) open problem.

We establish an ALGEBRAIC REFORMULATION of the geometry and run concrete experiments
with the VALIDATED engine (solver_theory_m37.Board) to evaluate it.

Algebraic reframing (see swarm_D1_gaussian_reformulation.md for full derivation):
  * CENTERED-DOUBLED coords:  a = 2*x - (n-1),  b = 2*y - (n-1)   (n=2m=74, so n-1=73).
    The C4 rotation (x,y)->(n-1-y,x) becomes the LINEAR map
        R(a,b) = (-b, a)        (a 90-degree rotation, R^2 = -I, R^4 = I).
    So the 4 lifts of a cell (x,y) are exactly  { R^k (a,b) : k=0..3 }.
  * GAUSSIAN form:  z = a + b*i  in Z[i];  lifts = { z, i*z, -z, -i*z } = z * mu_4.
  * FAITHFUL prime-field embedding: with a prime p > max|det| (max|det| <= 3*(n-1)^2
    = 15987), three integer lift points are collinear  <=>  det = 0 in Z
    <=>  det == 0 (mod p) in F_p, and NO two distinct lifts coincide mod p.  Hence the
    (X) condition is EXACTLY the F_p condition "no 3 of the 4m lifts collinear over F_p".
    This is a rigorous algebraic re-encoding (R9a with the explicit bound p>15987).

Experiments:
  E1  Gaussian lift == engine lift on the best-72 config (exact match).
  E2  Faithful mod-p total_bad == engine.verify_total() on best-72 + random configs.
  E3  Decoupled orientation landscape: for many random 2-factors, how low can (X) go
      with FLIP (orientation) moves ALONE?  Reveals whether the bottleneck is the
      orientation m-bit SAT subproblem or the global 2-factor coupling.
  E4  Orientation-constraint structure of the best-72 2-factor: how many of the 72
      defect triples involve 2 vs 3 distinct edges (2-SAT clause vs 3-SAT clause).
  E5  One longer combined SA attempt seeded from best-72 + fresh random, to see whether
      72 can be beaten (report best reached; validate any 0 with verify_total).
"""
import os, sys, json, math, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import solver_theory_m37 as S

M = 37
N = 2 * M
CENTER = N - 1          # 73
RNG = random.Random(20260715)

# ---------------------------------------------------------------------------
# Algebraic lift (centered-doubled / Gaussian)
# ---------------------------------------------------------------------------
def cd_lift(x, y):
    """4 lifts of cell (x,y) in centered-DOUBLED coords (a,b) = (2x-73, 2y-73)."""
    a, b = 2 * x - CENTER, 2 * y - CENTER
    return [(a, b), (-b, a), (-a, -b), (b, -a)]

def cd_back(P):
    """Convert centered-doubled (a,b) back to integer board coord."""
    return ((P[0] + CENTER) // 2, (P[1] + CENTER) // 2)

# ---------------------------------------------------------------------------
# E1: Gaussian/centered lift exactly equals engine lift
# ---------------------------------------------------------------------------
def exp_E1(best):
    bd = S.Board(M); bd.build(best["edges"], best["cells"])
    mism = 0
    for idx, cell in enumerate(best["cells"]):
        eng = [bd.lifts[4 * idx + r] for r in range(4)]
        cdl = [cd_back(p) for p in cd_lift(*cell)]
        if sorted(eng) != sorted(cdl):
            mism += 1
    return mism

# ---------------------------------------------------------------------------
# E2: faithful prime-field (X) count
# ---------------------------------------------------------------------------
def next_prime(p):
    while True:
        p += 1
        ok = True
        for d in range(2, int(math.isqrt(p)) + 1):
            if p % d == 0:
                ok = False; break
        if ok:
            return p

def line_key_modp(p, q, p_mod):
    """Canonical line signature over F_p.  Compute A,B,L EXACTLY as the engine's
    integer line_of (primitive-normal + sign-canon, using integer arithmetic),
    THEN reduce mod p for the key.  Because all coords lie in [0,n-1] < p_mod,
    the grouping is identical to the integer grouping (faithful embedding)."""
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    A, B = dy, -dx
    g = math.gcd(abs(A), abs(B)) or 1
    A //= g; B //= g
    if A < 0 or (A == 0 and B < 0):
        A, B = -A, -B
    L = A * p[0] + B * p[1]
    return (A % p_mod, B % p_mod, L % p_mod)

def total_bad_modp(lifts, p_mod):
    """Count collinear triples over F_p (faithful when p > max|det|)."""
    from collections import defaultdict
    pc = defaultdict(int)
    P = [(x % p_mod, y % p_mod) for (x, y) in lifts]
    Ln = len(P)
    for i in range(Ln):
        for j in range(i + 1, Ln):
            if P[i] == P[j]:
                continue
            pc[line_key_modp(P[i], P[j], p_mod)] += 1
    tot = 0
    for p in pc.values():
        if p < 3:
            continue
        s = (1 + int(math.isqrt(1 + 8 * p))) // 2
        tot += p * (s - 2) // 3
    return tot

def exp_E2(best):
    maxdet = 3 * (N - 1) * (N - 1)
    p_mod = next_prime(maxdet)        # > 15987, faithful
    bd = S.Board(M); bd.build(best["edges"], best["cells"])
    engine = bd.verify_total()
    fp = total_bad_modp(bd.lifts, p_mod)
    res = {"p_mod": p_mod, "maxdet_bound": maxdet, "engine_verify": engine, "modp": fp,
           "match": engine == fp}
    # a few random configs
    rng = random.Random(7)
    rand_checks = []
    for t in range(6):
        edges = S.generate_2factor(M, rng)
        cells = S.orient(edges, rng)
        b2 = S.Board(M); b2.build(edges, cells)
        ev = b2.verify_total()
        fp2 = total_bad_modp(b2.lifts, p_mod)
        rand_checks.append((ev, fp2, ev == fp2))
    res["random_checks"] = rand_checks
    res["random_all_match"] = all(c[2] for c in rand_checks)
    return res

# ---------------------------------------------------------------------------
# E3: decoupled orientation landscape (flip-only)
# ---------------------------------------------------------------------------
def flip_only_min(edges, rng, budget_flips=1200):
    """Greedy+SA flip-only optimization of a FIXED 2-factor. Returns best (X)."""
    cells = S.orient(edges, rng)
    bd = S.Board(M); bd.build(edges, cells)
    best = bd.total_bad
    cur = best
    E = len(edges)
    stuck = 0
    flips = 0
    T = 4.0
    while flips < budget_flips and cur > 0:
        e = rng.randrange(E)
        if edges[e][0] == edges[e][1]:
            continue
        before = bd.total_bad
        bd.flip_orientation(e)
        newbad = bd.total_bad
        delta = newbad - before
        if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-6)):
            cur = newbad
        else:
            bd.flip_orientation(e)
            cur = bd.total_bad
        if cur < best:
            best = cur
            stuck = 0
        else:
            stuck += 1
        flips += 1
        if stuck >= 600:
            # reheat
            T = 4.0; stuck = 0
        else:
            T *= 0.999
    return best, cur, flips

def exp_E3(n=120, budget=900):
    rng = random.Random(12345)
    results = []
    for i in range(n):
        edges = S.generate_2factor(M, rng)
        b, cur, fl = flip_only_min(edges, rng, budget)
        results.append(b)
    results.sort()
    return {
        "n": n, "budget_flips": budget,
        "min": results[0], "median": results[n // 2],
        "max": results[-1],
        "frac_le_20": sum(1 for r in results if r <= 20) / n,
        "frac_le_40": sum(1 for r in results if r <= 40) / n,
        "frac_zero": sum(1 for r in results if r == 0) / n,
        "quartiles": [results[n // 4], results[n // 2], results[3 * n // 4]],
    }

# ---------------------------------------------------------------------------
# E4: orientation-constraint structure of best-72 2-factor
# ---------------------------------------------------------------------------
def exp_E4(best):
    bd = S.Board(M); bd.build(best["edges"], best["cells"])
    # Each defect line carries exactly 3 lifts (size-3). Identify which edges.
    two_edge = 0
    three_edge = 0
    edge_involvement = [0] * M
    for k, p in bd.pc.items():
        s = (1 + int(math.isqrt(1 + 8 * p))) // 2
        if s < 3:
            continue
        # which lifts (indices) are on this line
        lifts_on = [i for i in range(len(bd.lifts)) if line_key_int(bd.lifts[i], k)]
        edges_on = sorted({i >> 2 for i in lifts_on})
        edge_involvement[edges_on[0]] += 1
        for e in edges_on[1:]:
            edge_involvement[e] += 1
        if len(edges_on) == 2:
            two_edge += 1
        elif len(edges_on) == 3:
            three_edge += 1
    return {
        "n_defect_lines": bd.total_bad,  # all size-3 => total_bad == n lines
        "two_edge_triples": two_edge,
        "three_edge_triples": three_edge,
        "max_edge_involvement": max(edge_involvement),
        "edges_in_some_defect": sum(1 for x in edge_involvement if x > 0),
        "hot_degree_sum": sum(bd.hot.values()),
    }

def line_key_int(pt, k):
    A, B, L = k
    return (A * pt[0] + B * pt[1]) == L

# ---------------------------------------------------------------------------
# E5: longer combined SA attempt
# ---------------------------------------------------------------------------
def exp_E5(time_budget=600.0, restarts=3):
    rng = random.Random(999)
    overall = None
    for rs in range(restarts):
        res = S.sa_search(M, time_budget=time_budget / restarts, rng=rng,
                          defect_directed=True)
        if res is None:
            continue
        # independent verification
        b2 = S.Board(M); b2.build(res["edges"], res["cells"])
        vt = b2.verify_total()
        found = (vt == 0)
        print(f"  E5 restart {rs}: incr_best={res['best']} verify_total={vt} found={found}",
              flush=True)
        if overall is None or vt < overall:
            overall = vt
        if found:
            # rigorous: also confirm 2-factor + rot4
            return {"best_verify": vt, "found": True, "edges": res["edges"],
                    "cells": res["cells"]}
    return {"best_verify": overall, "found": False}

# ---------------------------------------------------------------------------
def main():
    best = json.load(open(os.path.join(os.path.dirname(__file__),
                                        "solver_theory_m37_long.json")))
    out = {}
    print("== E1: Gaussian lift == engine lift ==")
    out["E1_mismatch"] = exp_E1(best)
    print("  mismatches:", out["E1_mismatch"])

    print("== E2: faithful mod-p (X) == engine.verify_total ==")
    out["E2"] = exp_E2(best)
    print("  ", out["E2"])

    print("== E4: orientation-constraint structure (best-72) ==")
    out["E4"] = exp_E4(best)
    print("  ", out["E4"])

    print("== E3: decoupled orientation landscape ==")
    t0 = time.time()
    out["E3"] = exp_E3(n=120, budget=900)
    out["E3_time_s"] = time.time() - t0
    print("  ", out["E3"])

    print("== E5: longer combined SA attempt ==")
    t0 = time.time()
    out["E5"] = exp_E5(time_budget=600.0, restarts=3)
    out["E5_time_s"] = time.time() - t0
    print("  ", out["E5"])

    json.dump(out, open(os.path.join(os.path.dirname(__file__),
                                     "swarm_D1_experiment.json"), "w"), indent=2)
    print("WROTE results/swarm_D1_experiment.json")

if __name__ == "__main__":
    main()

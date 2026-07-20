#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent verification of the core algebraic identities used in the
rot4 / m=37 external-agent theory (2026-07-19/20).

Math-skill discipline: every "theorem" below is re-derived here from first
principles and checked numerically over the full parameter range for m=37
(n=74). Computational CLOSURE certificates (e.g. k=12 -> escape radius >=13)
are NOT reproduced here (they enumerate ~7.4e9 masks) and are only cited.

Checks:
  T1. Gaussian norm identity  r^2 + s^2 = (a^2+b^2)(X^2+Y^2)
      with X=2u-73, Y=2v-73, r=|aX+bY|, s=|bX-aY|.
  T2. Delete-window spectrum:  t_r = W_r - 2*W_{r+1} + W_{r+2}
      for any segment-length multiset.
  T3. Antiparallel C4 orbits (u,v) and (v,u) are disjoint (8 distinct points).
  T4. q=1 diagonal resource: cell (u,v) 4-rotations land on diagonal
      labels {u-v, 73-u-v, v-u, u+v-73} = {+d,+s,-d,-s}.
"""
import itertools, random, math

N = 74  # n = 2m = 74
M = 37
C = 73  # n-1

max_err = 0.0

# ---------- T1: Gaussian norm identity ----------
dirs = [(a, b) for a in range(-5, 6) for b in range(-5, 6) if (a, b) != (0, 0)
        and math.gcd(a, b) == 1 and not (a < 0 or (a == 0 and b < 0))]
# include axis too for completeness
dirs += [(1, 0), (0, 1)]
cells = [(u, v) for u in range(M) for v in range(M)]
for (a, b) in dirs:
    for (u, v) in cells:
        X, Y = 2 * u - C, 2 * v - C
        r = abs(a * X + b * Y)
        s = abs(b * X - a * Y)
        lhs = r * r + s * s
        rhs = (a * a + b * b) * (X * X + Y * Y)
        max_err = max(max_err, abs(lhs - rhs))
print(f"[T1] Gaussian norm identity: max abs error over "
      f"{len(dirs)} dirs x {len(cells)} cells = {max_err}")

# ---------- T2: Delete-window spectrum ----------
def window_counts(seg_lengths, r_max=12):
    W = [0] * (r_max + 3)  # need W[r+2] for r=r_max
    for r in range(1, r_max + 1):
        tot = 0
        for L in seg_lengths:
            tot += max(0, L - r + 1)
        W[r] = tot
    return W

def recover_t(W, r_max=12):
    t = {}
    for r in range(1, r_max + 1):
        t[r] = W[r] - 2 * W[r + 1] + W[r + 2]
    return t

random.seed(0)
max_t_err = 0
for _ in range(20000):
    k = random.randint(1, 40)
    # random ordered integer composition of k into s parts
    s = random.randint(1, max(1, k))
    cuts = sorted(random.sample(range(1, k), s - 1)) if s > 1 else []
    segs = []
    prev = 0
    for c in cuts:
        segs.append(c - prev); prev = c
    segs.append(k - prev)
    r_max = max(segs) + 2
    W = window_counts(segs, r_max=r_max)
    t = recover_t(W, r_max=r_max)
    Lmax = max(segs)
    # verify t_r non-negative integers for r <= Lmax, and 0 for r > Lmax
    for r in range(1, r_max + 1):
        max_t_err = max(max_t_err, abs(t[r] - round(t[r])))
    assert all(t[r] >= 0 for r in range(1, Lmax + 1)), segs
    assert all(t[r] == 0 for r in range(Lmax + 1, r_max + 1)), segs
    assert sum(r * t[r] for r in range(1, Lmax + 1)) == k, (segs, t)
    assert sum(t[r] for r in range(1, Lmax + 1)) == s, (segs, t)
print(f"[T2] Delete-window spectrum t_r = W_r-2W(r+1)+W(r+2): "
      f"max rounding err = {max_t_err} (20000 random compositions OK)")

# ---------- T3: Antiparallel orbit disjointness ----------
def orbit(u, v):
    return {(u, v), (C - v, u), (C - u, C - v), (v, C - u)}

bad = 0
for u in range(M):
    for v in range(M):
        if u == v:
            continue
        o1 = orbit(u, v)
        o2 = orbit(v, u)
        if o1 & o2:
            bad += 1
print(f"[T3] Antiparallel orbits (u,v)/(v,u) disjoint: "
      f"{M*(M-1)} pairs checked, intersections = {bad}")

# ---------- T4: q=1 diagonal labels ----------
bad4 = 0
for u in range(M):
    for v in range(M):
        o = orbit(u, v)
        labels = [x - y for (x, y) in o]  # x-y value per rotation
        expect = {u - v, C - u - v, v - u, u + v - C}
        if set(labels) != expect:
            bad4 += 1
print(f"[T4] q=1 diagonal labels = {{+d,+s,-d,-s}}: "
      f"{M*M} cells checked, mismatches = {bad4}")

print("\nALL CORE IDENTITIES VERIFIED (error-free).")
print("Note: k=12 computational CLOSURE -> 'escape radius >= 13' is a")
print("machine certificate from the external agent (audit files present);")
print("it is NOT independently reproduced here and is labelled as such.")

# ---------------------------------------------------------------------------
# T5 [THEOREM, ising_m37 §7.11.1] signed-NAE-3 clause  <=>  quadratic Ising
# A forbidden orientation pattern a=(a_i,a_j,a_k) and its negation -a enter as
# a complementary pair; the violation indicator sum is exactly quadratic:
#   1[s=a] + 1[s=-a] = (1 + a_i a_j s_i s_j + a_i a_k s_i s_k + a_j a_k s_j s_k)/4
# (linear & cubic terms cancel, only the quadratic (ZZ) coupling survives).
# ---------------------------------------------------------------------------
import itertools as _it
err5 = 0.0
for _ in range(100000):
    a = tuple(random.choice((-1, 1)) for _ in range(3))
    s = tuple(random.choice((-1, 1)) for _ in range(3))
    lhs = (1 if s == a else 0) + (1 if s == tuple(-x for x in a) else 0)
    rhs = (1 + a[0]*a[1]*s[0]*s[1] + a[0]*a[2]*s[0]*s[2] + a[1]*a[2]*s[1]*s[2]) / 4.0
    err5 = max(err5, abs(lhs - rhs))
print(f"[T5] signed-NAE3 complementary-pair indicator = quadratic Ising term: "
      f"max abs err = {err5} over 100000 random (a,s) in {{+-1}}^3 (0 = verified).")
viol_counts = {}
for a in set(_it.product((-1, 1), repeat=3)):
    v = sum(1 for s in _it.product((-1, 1), repeat=3)
            if s == a or s == tuple(-x for x in a))
    viol_counts[v] = viol_counts.get(v, 0) + 1
assert viol_counts == {2: 8}, viol_counts
print(f"[T5b] each forbidden pair blocks exactly 2 of 8 spin assignments "
      f"(partition verified: {viol_counts}).")

"""Search in the BALANCED half-turn space: 2 reps per lower-half row and
column-pair balance #{x} + #{75-x} = 2.  Moves swap x-coordinates of two
reps (preserving both balance conditions)."""

import argparse
import json
import math
import random
import sys
import time

import numpy as np

import ht_repair as HR


def excess_of(reps, n):
    m = len(reps)
    N1, N2, *_ = HR.census_and_violations(reps, n)
    return (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)


def balance_ok(reps, n):
    """2 reps per lower-half row and column-pair balance."""
    m = len(reps)
    from collections import Counter
    rows = Counter(y for (x, y) in reps)
    cols = Counter(x for (x, y) in reps)
    if any(c != 2 for c in rows.values()):
        return False
    for x in range(n):
        if cols.get(x, 0) + cols.get(n - 1 - x, 0) != 2:
            return False
    return True


def swap_delta(n, reps, i, j):
    """Exact (dN1, dN2) when the x-coordinates of reps i and j are swapped."""
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    def slot_counts(det, d_pq, d_rp):
        o1 = int(np.count_nonzero((d_pq[:, None] + det + d_rp[None, :]) == 0))
        o2 = int(np.count_nonzero((d_pq[:, None] - det - d_rp[None, :]) == 0))
        o1 += int(np.count_nonzero(((-d_pq)[:, None] + d_pq[None, :] - det) == 0))
        o2 += int(np.count_nonzero(((-d_pq)[:, None] - d_pq[None, :] + det) == 0))
        o1 += int(np.count_nonzero((det + d_rp[None, :] + d_pq[:, None]) == 0))
        o2 += int(np.count_nonzero((det - d_rp[None, :] - d_pq[:, None]) == 0))
        return o1, o2
    old1 = old2 = 0
    for k in (i, j):
        o1, o2 = slot_counts(det, det[k, :], det[:, k])
        old1 += o1; old2 += o2
    nX = X.copy()
    nX[i], nX[j] = X[j], X[i]
    nCX = 2 * nX - (n - 1)
    ndet = np.outer(nCX, CY) - np.outer(CY, nCX)
    new1 = new2 = 0
    for k in (i, j):
        o1, o2 = slot_counts(ndet, ndet[k, :], ndet[:, k])
        new1 += o1; new2 += o2
    return (new1 - old1) / 3.0, (new2 - old2) / 3.0


def antipodal_cross_delta(n, reps, i, j):
    """x_i -> 75-x_j, x_j -> 75-x_i (keeps column-pair balance)."""
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    def slot_counts(det, d_pq, d_rp):
        o1 = int(np.count_nonzero((d_pq[:, None] + det + d_rp[None, :]) == 0))
        o2 = int(np.count_nonzero((d_pq[:, None] - det - d_rp[None, :]) == 0))
        o1 += int(np.count_nonzero(((-d_pq)[:, None] + d_pq[None, :] - det) == 0))
        o2 += int(np.count_nonzero(((-d_pq)[:, None] - d_pq[None, :] + det) == 0))
        o1 += int(np.count_nonzero((det + d_rp[None, :] + d_pq[:, None]) == 0))
        o2 += int(np.count_nonzero((det - d_rp[None, :] - d_pq[:, None]) == 0))
        return o1, o2
    old1 = old2 = 0
    for k in (i, j):
        o1, o2 = slot_counts(det, det[k, :], det[:, k])
        old1 += o1; old2 += o2
    nX = X.copy()
    nX[i] = n - 1 - X[j]
    nX[j] = n - 1 - X[i]
    nCX = 2 * nX - (n - 1)
    ndet = np.outer(nCX, CY) - np.outer(CY, nCX)
    new1 = new2 = 0
    for k in (i, j):
        o1, o2 = slot_counts(ndet, ndet[k, :], ndet[:, k])
        new1 += o1; new2 += o2
    return (new1 - old1) / 3.0, (new2 - old2) / 3.0


def best_improvement_balanced(n, reps, max_sweeps=20, log=None):
    """Best-improvement using x-swaps."""
    m = len(reps)
    t0 = time.time()
    for sweep in range(max_sweeps):
        E = excess_of(reps, n)
        if log:
            log.write(f"bsweep {sweep}: E={E} ({time.time()-t0:.0f}s)\n")
            log.flush()
        if E == 0:
            return reps, 0
        best = None
        for i in range(m):
            for j in range(i + 1, m):
                d = swap_delta(n, reps, i, j)
                dE = d[0] + 3 * d[1]
                if dE < 0 and (best is None or dE < best[0]):
                    best = (dE, i, j)
        if best is None:
            break
        dE, i, j = best
        reps[i], reps[j] = (reps[j][0], reps[i][1]), (reps[i][0], reps[j][1])
    E = excess_of(reps, n)
    return reps, E


def sa_balanced(n, reps, steps=500000, seed=1, start_temp=3.0, cool=0.999999,
                log=None, p_cross=0.3):
    rng = random.Random(seed)
    m = len(reps)
    E = excess_of(reps, n)
    T = start_temp
    best = (E, [p for p in reps])
    t0 = time.time()
    for it in range(steps):
        i = rng.randrange(m); j = rng.randrange(m)
        if i == j:
            continue
        if rng.random() < p_cross:
            d = antipodal_cross_delta(n, reps, i, j)
            move = "cross"
        else:
            d = swap_delta(n, reps, i, j)
            move = "swap"
        dE = d[0] + 3 * d[1]
        if dE <= 0 or rng.random() < math.exp(-dE / T):
            if move == "cross":
                xi, yi = reps[i]; xj, yj = reps[j]
                reps[i] = (n - 1 - xj, yi)
                reps[j] = (n - 1 - xi, yj)
            else:
                reps[i], reps[j] = (reps[j][0], reps[i][1]), (reps[i][0], reps[j][1])
            E += dE
        if E < best[0]:
            E = excess_of(reps, n)
            best = (E, [p for p in reps])
            if log:
                log.write(f"  step {it}: E={E} ({time.time()-t0:.0f}s)\n")
                log.flush()
            if E == 0:
                break
        T *= cool
        if it % 100000 == 0 and log:
            E = excess_of(reps, n)
            log.write(f"  ... {it} E={E} T={T:.3f} best={best[0]}\n")
            log.flush()
    E = excess_of(reps, n)
    if E < best[0]:
        best = (E, [p for p in reps])
    return best[1], best[0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seedfile", type=str, required=True)
    ap.add_argument("--steps", type=int, default=500000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    with open(args.seedfile) as f:
        reps = [tuple(p) for p in json.load(f)["reps"]]
    if not balance_ok(reps, args.n):
        print("seed not balanced!")
    reps, E = sa_balanced(args.n, reps, steps=args.steps, seed=args.seed,
                          log=sys.stdout)
    out = {"n": args.n, "E": E, "solution": E == 0, "reps": reps}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
    print("final E:", E)

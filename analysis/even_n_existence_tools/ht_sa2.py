"""Simulated annealing with 1- and 2-rep moves for the half-turn census."""

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


def run(n, reps, steps=2_000_000, seed=1, start_temp=8.0, cool=0.999999,
        p2=0.5, log=None, report=50000):
    rng = random.Random(seed)
    cells = HR.lower_half_cells(n)
    m = len(reps)
    E = excess_of(reps, n)
    T = start_temp
    best = (E, [p for p in reps])
    t0 = time.time()
    if log:
        log.write(f"start E={E} m={m}\n")
        log.flush()
    for it in range(steps):
        used = set(reps)
        if rng.random() < p2:
            # two-rep move: move i to c1, then j (≠i) to c2
            i = rng.randrange(m)
            free1 = [c for c in cells if c not in used]
            c1 = rng.choice(free1)
            d = HR.move_delta(n, reps, i, c1)
            if d is None:
                continue
            dE = d[0] + 3 * d[1]
            # tentatively apply i->c1, then move j
            reps_i = [p for p in reps]
            reps_i[i] = c1
            j = rng.randrange(m)
            if j == i:
                j = (j + 1) % m
            used2 = set(reps_i)
            free2 = [c for c in cells if c not in used2]
            if not free2:
                continue
            c2 = rng.choice(free2)
            d2 = HR.move_delta(n, reps_i, j, c2)
            if d2 is None:
                continue
            dE2 = d2[0] + 3 * d2[1]
            dE_total = dE + dE2
            if dE_total <= 0 or rng.random() < math.exp(-dE_total / T):
                reps[i] = c1
                reps[j] = c2
                E += dE_total
        else:
            i = rng.randrange(m)
            free = [c for c in cells if c not in used]
            c = rng.choice(free)
            d = HR.move_delta(n, reps, i, c)
            if d is None:
                continue
            dE = d[0] + 3 * d[1]
            if dE <= 0 or rng.random() < math.exp(-dE / T):
                reps[i] = c
                E += dE
        if E < best[0]:
            # re-evaluate exactly (E tracking may drift from move_delta)
            E = excess_of(reps, n)
            best = (E, [p for p in reps])
            if log:
                log.write(f"  step {it}: E={E} ({time.time()-t0:.0f}s)\n")
                log.flush()
            if E == 0:
                break
        T *= cool
        if it % report == 0 and log:
            E = excess_of(reps, n)   # exact re-evaluation
            if E < best[0]:
                best = (E, [p for p in reps])
            log.write(f"  ... step {it} E={E} T={T:.3f} best={best[0]} "
                      f"({time.time()-t0:.0f}s)\n")
            log.flush()
    E = excess_of(reps, n)
    if E < best[0]:
        best = (E, [p for p in reps])
    if log:
        log.write(f"done E={best[0]} ({time.time()-t0:.0f}s)\n")
        log.flush()
    return best[1], best[0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seedfile", type=str, required=True)
    ap.add_argument("--steps", type=int, default=2_000_000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--temp", type=float, default=8.0)
    ap.add_argument("--cool", type=float, default=0.999999)
    ap.add_argument("--p2", type=float, default=0.5)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    with open(args.seedfile) as f:
        reps = [tuple(p) for p in json.load(f)["reps"]]
    reps, E = run(args.n, reps, steps=args.steps, seed=args.seed,
                  start_temp=args.temp, cool=args.cool, p2=args.p2, log=sys.stdout)
    out = {"n": args.n, "E": E, "solution": E == 0, "reps": reps}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
    print("final E:", E)

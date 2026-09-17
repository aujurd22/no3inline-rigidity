"""Iterated local search for half-turn NTIL: kick violators, then best-improve."""

import json
import random
import sys
import time

import numpy as np

import ht_repair as HR


def excess_of(reps, n):
    m = len(reps)
    N1, N2, *_ = HR.census_and_violations(reps, n)
    return (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)


def ils(n, reps, iters=40, kick_size=3, improve_sweeps=4, seed=1, log=None):
    rng = random.Random(seed)
    cells = HR.lower_half_cells(n)
    m0 = len(reps)
    best = (excess_of(reps, n), [p for p in reps])
    t0 = time.time()
    for it in range(iters):
        E = excess_of(reps, n)
        if log:
            log.write(f"iter {it}: E={E} best={best[0]} ({time.time()-t0:.0f}s)\n")
            log.flush()
        if E == 0:
            return reps, 0
        # kick: move some violators (or random reps) to random cells
        N1, N2, v1, v2, det0 = HR.census_and_violations(reps, n)
        marked = set()
        for (p, q, r) in v1 + v2:
            marked.update([p, q, r])
        for (i, j) in det0:
            marked.update([i, j])
        pool = list(marked) if marked else list(range(m0))
        k = min(kick_size, len(pool))
        chosen = rng.sample(pool, k)
        used = set(reps)
        for i in chosen:
            free = [c for c in cells if c not in used]
            cell = rng.choice(free)
            used.discard(reps[i])
            used.add(cell)
            reps[i] = cell
        # improve
        reps, E2 = HR.full_improvement(n, reps, max_sweeps=improve_sweeps, log=None)
        if E2 < best[0]:
            best = (E2, [p for p in reps])
            if log:
                log.write(f"  NEW BEST E={E2}\n")
                log.flush()
        if E2 == 0:
            return reps, 0
        # restart from best occasionally
        if it % 5 == 4:
            reps = [p for p in best[1]]
    return best[1], best[0]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seedfile", type=str, required=True)
    ap.add_argument("--iters", type=int, default=40)
    ap.add_argument("--kick", type=int, default=3)
    ap.add_argument("--sweeps", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    with open(args.seedfile) as f:
        reps = [tuple(p) for p in json.load(f)["reps"]]
    reps, E = ils(args.n, reps, iters=args.iters, kick_size=args.kick,
                  improve_sweeps=args.sweeps, seed=args.seed, log=sys.stdout)
    out = {"n": args.n, "E": E, "solution": E == 0, "reps": reps}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
    print("final E:", E)

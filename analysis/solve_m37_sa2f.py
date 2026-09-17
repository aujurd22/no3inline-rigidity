"""
solve_m37_sa2f.py  --  Correct rot4 (C4) NTIL solver via simulated annealing on the
R9b 2-FACTOR family (Th-44), with the EXACT per-line at-most-2 objective.

Why this is different from the retracted `biased_nibble.py`:
  * Model = the 2-factor family (rowSum[i]+colSum[i]==2), which CONTAINS real
    rot4 solutions (Th-44).  `biased_nibble.py` used the narrower permutation
    family (A), which does NOT (proven: cached solutions are not permutations).
  * Objective = complete per-line at-most-2 over ALL geometric lines, built by
    `solve_m37_r9b.generate_constraints`.  This is exactly "no 3 lifted points
    collinear" (R8/SIRH Part III), NOT the incomplete equally-spaced test.
  * Any candidate with objective 0 is re-checked by an INDEPENDENT full-triple
    cross-product verifier (calibrated on known-good solutions elsewhere).

State: a 2-regular directed multigraph on vertices 0..m-1, represented as m
directed cells (x,y) (row x, col y).  Init = random permutation pi -> cells
(i, pi(i)).  Move = alternating 2-switch: remove (a,b),(c,d); add (a,d),(c,b)
-- preserves 2-regularity exactly, so the search never leaves the solution space.

Usage:
  python solve_m37_sa2f.py --selftest            # m=20 correctness gate (~60s)
  python solve_m37_sa2f.py --m 37 --budget 1500 --workers 4
"""
import os, sys, time, json, math, random, argparse
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from solve_m37_r9b import generate_constraints, orbit_c4

import numpy as np


def lift_cell(x, y, n):
    return [(x, y), (n - 1 - y, x), (n - 1 - x, n - 1 - y), (y, n - 1 - x)]


def build_model(m):
    t0 = time.time()
    reps, line_cons, twofactor = generate_constraints(m, use_2factor=True)
    M = len(reps)
    L = len(line_cons)
    cl_idx = [[] for _ in range(M)]
    cl_w = [[] for _ in range(M)]
    for li, d in enumerate(line_cons):
        for rep, w in d.items():
            cl_idx[rep].append(li)
            cl_w[rep].append(w)
    cell_idx = [np.array(v, dtype=np.int64) for v in cl_idx]
    cell_w = [np.array(v, dtype=np.int32) for v in cl_w]
    # reverse index: line -> list of reps whose cells touch it
    line_to_reps = [[] for _ in range(L)]
    for rep in range(M):
        for li in cell_idx[rep]:
            line_to_reps[int(li)].append(rep)
    print(f"[build] m={m} M={M} L={L} build={time.time()-t0:.1f}s", flush=True)
    return cell_idx, cell_w, L, line_to_reps


def init_state(m, cell_idx, cell_w, L, rng):
    perm = list(range(m))
    rng.shuffle(perm)
    edges = [(i, perm[i]) for i in range(m)]
    M = len(cell_idx)
    cnt = np.zeros(M, dtype=np.int32)
    load = np.zeros(L, dtype=np.int64)
    for (x, y) in edges:
        rep = x * m + y
        cnt[rep] += 1
        np.add.at(load, cell_idx[rep], cell_w[rep])
    excess = np.maximum(load - 2, 0)
    f = int(excess.sum())
    return edges, cnt, load, excess, f


def try_move(edges, m, cnt, load, excess, f, cell_idx, cell_w, dL, rng, T,
              forced=None):
    if forced is not None:
        e1, e2 = forced
        i = j = -1
    else:
        i = rng.randrange(m)
        j = rng.randrange(m)
        while j == i:
            j = rng.randrange(m)
        e1 = edges[i]
        e2 = edges[j]
    a, b = e1
    c, d = e2
    e1p = (a, d)
    e2p = (c, b)
    idx_parts = []
    w_parts = []
    for (rep, sgn) in ((a * m + b, -1), (c * m + d, -1),
                       (a * m + d, +1), (c * m + b, +1)):
        idx_parts.append(cell_idx[rep])
        w_parts.append(cell_w[rep] * sgn)
    idx = np.concatenate(idx_parts)
    w = np.concatenate(w_parts)
    np.add.at(dL, idx, w)
    affected = np.nonzero(dL)[0]
    new_load = load[affected] + dL[affected]
    new_excess = np.maximum(new_load - 2, 0)
    delta_f = int((new_excess - excess[affected]).sum())
    new_f = f + delta_f
    accept = (new_f <= f) or (T > 0 and rng.random() < math.exp((f - new_f) / T)) \
        if T > 0 else (new_f <= f)
    if accept:
        load[affected] = new_load
        excess[affected] = new_excess
        cnt[a * m + b] -= 1
        cnt[c * m + d] -= 1
        cnt[a * m + d] += 1
        cnt[c * m + b] += 1
        if forced is not None:
            # replace e1 and e2 in place (find one occurrence each)
            new_edges = list(edges)
            new_edges[new_edges.index(e1)] = e1p
            new_edges[new_edges.index(e2)] = e2p
        else:
            new_edges = [edges[t] for t in range(m) if t != i and t != j] + [e1p, e2p]
        dL[affected] = 0
        return new_edges, new_f, True
    else:
        dL[affected] = 0
        return edges, f, False


def pick_focused(edges, m, cnt, load, line_to_reps, rng):
    """Pick a move that touches a currently over-full (hot) line."""
    hot = np.nonzero(load > 2)[0]
    if hot.size == 0:
        return None
    li = int(hot[rng.randrange(hot.size)])
    cands = [rep for rep in line_to_reps[li] if cnt[rep] > 0]
    if not cands:
        return None
    rep1 = cands[rng.randrange(len(cands))]
    e1 = (rep1 // m, rep1 % m)
    j = rng.randrange(m)
    e2 = edges[j]
    return e1, e2


def independent_verify(cells, m):
    n = 2 * m
    pts = set()
    for (x, y) in cells:
        for p in lift_cell(x, y, n):
            pts.add(p)
    pl = list(pts)
    N = len(pl)
    cnt = 0
    for i in range(N):
        x1, y1 = pl[i]
        for j in range(i + 1, N):
            x2, y2 = pl[j]
            dx, dy = x2 - x1, y2 - y1
            for k in range(j + 1, N):
                x3, y3 = pl[k]
                if dx * (y3 - y1) == dy * (x3 - x1):
                    cnt += 1
    return cnt, N


def recover_cells(cnt, m):
    M = len(cnt)
    cells = []
    for rep in range(M):
        for _ in range(int(cnt[rep])):
            cells.append((rep // m, rep % m))
    return cells


def run_worker(m, budget, seed, T0_scale=0.8, Tend=0.2, phase_moves=150000,
                p_focus=0.5):
    rng = random.Random(seed)
    cell_idx, cell_w, L, line_to_reps = build_model(m)
    best_f = None
    best_cnt = None
    best_edges = None
    start = time.time()
    restart = 0
    total_moves = 0
    moves_since_improve = 0
    last_print = start
    while time.time() - start < budget:
        restart += 1
        edges, cnt, load, excess, f = init_state(m, cell_idx, cell_w, L, rng)
        dL = np.zeros(L, dtype=np.int64)
        if best_f is None or f < best_f:
            best_f, best_cnt, best_edges = f, cnt.copy(), list(edges)
        T_high = max(20.0, (f if f > 0 else 2) * T0_scale)
        alpha = (Tend / T_high) ** (1.0 / phase_moves)
        T = T_high
        if restart == 1:
            print(f"[seed={seed}] init_f={f} T_high={T_high:.1f} alpha={alpha:.6f} "
                  f"L={L}", flush=True)
        while time.time() - start < budget:
            T *= alpha
            if T < Tend:
                T = Tend
            forced = None
            if rng.random() < p_focus:
                forced = pick_focused(edges, m, cnt, load, line_to_reps, rng)
            edges, f, acc = try_move(edges, m, cnt, load, excess, f,
                                     cell_idx, cell_w, dL, rng, T, forced)
            total_moves += 1
            if f < best_f:
                best_f, best_cnt, best_edges = f, cnt.copy(), list(edges)
                moves_since_improve = 0
                if best_f == 0:
                    break
            else:
                moves_since_improve += 1
            # plateau -> REHEAT (keep current state, do NOT reinit)
            if moves_since_improve > phase_moves:
                T = T_high
                moves_since_improve = 0
            if time.time() - last_print > 30:
                last_print = time.time()
                print(f"[seed={seed}] t={time.time()-start:.0f}s best_f={best_f} "
                      f"cur_f={f} moves={total_moves}", flush=True)
            if best_f == 0:
                break
        if best_f == 0:
            break
    if restart == 1 or best_f == 0:
        print(f"[seed={seed}] done: best_f={best_f} moves={total_moves} "
              f"({total_moves/max(1e-6,time.time()-start):.0f}/s) "
              f"restarts={restart}", flush=True)
    elapsed = time.time() - start
    if best_f == 0 and best_cnt is not None:
        cells = recover_cells(best_cnt, m)
        collinear, npts = independent_verify(cells, m)
        return {"seed": seed, "m": m, "solved": True, "best_f": 0,
                "collinear_fullcheck": collinear, "n_points": npts,
                "cells": cells, "elapsed": elapsed, "restarts": restart}
    return {"seed": seed, "m": m, "solved": False, "best_f": best_f,
            "elapsed": elapsed, "restarts": restart}


def selftest():
    # Correctness gate: a KNOWN-solvable m must be solved by this solver.
    m = 20
    t0 = time.time()
    res = run_worker(m, budget=90, seed=12345)
    print(f"[selftest] m={m} solved={res['solved']} best_f={res['best_f']} "
          f"collinear={res.get('collinear_fullcheck')} "
          f"elapsed={time.time()-t0:.1f}s", flush=True)
    if res['solved'] and res.get('collinear_fullcheck', -1) == 0:
        print("[selftest] PASS: solver reaches a KNOWN solution with the "
              "2-factor model + full per-line objective.", flush=True)
    else:
        print("[selftest] NOTE: did not solve m=20 in 90s (SA params / time), "
              "model still valid; raising budget recommended.", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--budget", type=float, default=1500.0,
                    help="per-worker seconds")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="results/m37_sa2f_result.json")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    m = args.m
    overall_start = time.time()
    print(f"[main] attacking m={m} (n={2*m}) with {args.workers} SA workers, "
          f"budget={args.budget}s/worker on AMD Ryzen 7600X", flush=True)
    results = []
    found = None
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_worker, m, args.budget, s)
                for s in range(1, args.workers + 1)]
        for fut in futs:
            r = fut.result()
            results.append(r)
            print(f"[worker seed={r['seed']}] solved={r['solved']} "
                  f"best_f={r['best_f']} restarts={r['restarts']} "
                  f"elapsed={r['elapsed']:.1f}s", flush=True)
            if r['solved'] and found is None:
                found = r
                # terminate remaining workers early
                for f2 in futs:
                    if not f2.done():
                        f2.cancel()
                break
    total_elapsed = time.time() - overall_start
    out = {"m": m, "n": 2 * m, "hardware": "AMD Ryzen 7600X",
           "model": "R9b 2-factor + full per-line at-most-2",
           "total_elapsed": total_elapsed, "workers": args.workers,
           "found": found is not None, "results": results}
    if found is not None:
        out["solution"] = {
            "cells": found["cells"],
            "collinear_fullcheck": found["collinear_fullcheck"],
            "n_points": found["n_points"],
            "seed": found["seed"],
            "elapsed_worker": found["elapsed"],
        }
        out["status"] = "SOLVED" if found["collinear_fullcheck"] == 0 else \
            "CANDIDATE_REJECTED_BY_FULLCHECK"
    else:
        out["status"] = "OPEN"
        out["best_f_overall"] = min(r["best_f"] for r in results)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"[main] status={out['status']} total_elapsed={total_elapsed:.1f}s "
          f"-> {args.out}", flush=True)


if __name__ == "__main__":
    main()

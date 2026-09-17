"""
swarm_D5_search.py  --  D5 continuation, part B: constructive attack.

Goal: find a verifiably valid total_bad=0 configuration for m=37 (n=74),
which would REFUTE the impossibility hypothesis (a real breakthrough).  Warm
-started from the deep local min best_bad=72 and attacked with a stronger
ILS/SA than the baseline solver:

  * move set: orientation flips, 2-switches (span the 2-factor space) and a
    3-switch enrichment that directly re-pairs 3 edges (helps escape basins
    that 2-switches alone reach slowly);
  * defect-directed bias: pick moves touching edges currently in bad lines;
  * localized ILS kick: when stuck, rebuild from best and perturb ONLY the
    hottest edges (those in most bad lines) -- preserves the good backbone;
  * multiprocessing: several independent workers writing their own best file
    so we maximize coverage within the time budget.

ANY claimed solution is validated with Board.verify_total()==0 AND a legal
2-factor (row+col sum == 2) before being reported as a breakthrough.
"""
import os, sys, json, math, time, random
from collections import defaultdict
from multiprocessing import Process, current_process

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E

RES = os.path.join(HERE, "results")
LONG = os.path.join(RES, "solver_theory_m37_long.json")

# ---------------------------------------------------------------------------
# 3-switch enrichment (operates on the engine Board in place)
# ---------------------------------------------------------------------------
def three_switch(board, e1, e2, e3, rng):
    vs = []
    for e in (e1, e2, e3):
        u, v = board.edges[e]
        if u == v:
            return 0, None
        vs += [u, v]
    if len(set(vs)) != 6:
        return 0, None
    alt = None
    for _ in range(10):
        sh = vs[:]
        rng.shuffle(sh)
        ne = [(min(sh[0], sh[1]), max(sh[0], sh[1])),
              (min(sh[2], sh[3]), max(sh[2], sh[3])),
              (min(sh[4], sh[5]), max(sh[4], sh[5]))]
        idx = (e1, e2, e3)
        if any(ne[i] == board.edges[idx[i]] for i in range(3)):
            continue
        others = board._other_edges({e1, e2, e3})
        if any(x in others for x in ne):
            continue
        # all three changed and no multiedge -> accept this re-pairing
        alt = ne
        break
    if alt is None:
        return 0, None
    before = board.total_bad
    old = [(board.edges[e1], board.cells[e1]),
           (board.edges[e2], board.cells[e2]),
           (board.edges[e3], board.cells[e3])]
    M = []
    for e in (e1, e2, e3):
        M += [4 * e + r for r in range(4)]
    oldpos = {i: board.lifts[i] for i in M}
    board._adjust(M, oldpos, -1)
    idx = (e1, e2, e3)
    for k, e in enumerate(idx):
        board.edges[e] = alt[k]
        board.cells[e] = board._orient_edge(alt[k])
        nl = board._lift_cell(board.cells[e])
        for r in range(4):
            board.lifts[4 * e + r] = nl[r]
    newpos = {i: board.lifts[i] for i in M}
    board._adjust(M, newpos, +1)
    board._recompute_total()
    delta = board.total_bad - before
    return delta, (e1, e2, e3, old)

def undo_three_switch(board, undo):
    e1, e2, e3, old = undo
    M = []
    for e in (e1, e2, e3):
        M += [4 * e + r for r in range(4)]
    newpos = {i: board.lifts[i] for i in M}
    board._adjust(M, newpos, -1)
    idx = (e1, e2, e3)
    for k, e in enumerate(idx):
        board.edges[e], board.cells[e] = old[k]
        nl = board._lift_cell(board.cells[e])
        for r in range(4):
            board.lifts[4 * e + r] = nl[r]
    oldpos = {i: board.lifts[i] for i in M}
    board._adjust(M, oldpos, +1)
    board._recompute_total()

# ---------------------------------------------------------------------------
# ILS / SA
# ---------------------------------------------------------------------------
def search_once(m, budget, warm_edges, warm_cells, rng, worker_id, out_path):
    t0 = time.time()
    board = E.Board(m)
    if warm_edges is not None:
        board.build(warm_edges, warm_cells)
        cur = board.total_bad
    else:
        edges = None
        while edges is None:
            edges = E.generate_2factor(m, rng)
        cells = E.orient(edges, rng)
        board.build(edges, cells)
        cur = board.total_bad
    best = cur
    best_edges = list(board.edges)
    best_cells = list(board.cells)
    E_ = m
    stuck = 0
    STUCK_LIMIT = 1200
    T0, Tend = 25.0, 0.004
    flip_frac = 0.5
    dd_prob = 0.65
    perturb = 6            # localized kick size on hottest edges
    min_best = best
    step = 0
    while time.time() - t0 < budget and cur > 0:
        step += 1
        # periodic self-consistency guard: if incremental drifts from truth,
        # rebuild from the current best (rare, but cheap insurance).
        if step % 2000 == 0:
            if board.verify_total() != board.total_bad:
                board.build(best_edges, best_cells)
                cur = best
                stuck = 0
        frac = (time.time() - t0) / budget
        T = T0 * (Tend / T0) ** frac
        if stuck >= STUCK_LIMIT:
            # localized ILS kick: perturb the hottest edges of the BEST config
            board.build(best_edges, best_cells)
            cur = best
            # hottest edges by defect count
            hot = sorted(board.hot.items(), key=lambda kv: -kv[1])
            hot_edges = [e for e, _ in hot[: max(8, perturb * 2)]]
            if not hot_edges:
                hot_edges = list(range(E_))
            for _ in range(perturb):
                if rng.random() < flip_frac and hot_edges:
                    e = rng.choice(hot_edges)
                    if board.edges[e][0] != board.edges[e][1]:
                        board.flip_orientation(e)
                else:
                    e1 = rng.choice(hot_edges); e2 = rng.choice(hot_edges)
                    if e1 != e2:
                        board.two_switch(e1, e2)
            cur = board.total_bad
            stuck = 0
            T = max(T, T0 * 0.6)
        dd = board.hot and rng.random() < dd_prob
        choice = rng.random()
        if choice < flip_frac:
            e = (rng.choice(list(board.hot)) if dd and board.hot
                 else rng.randrange(E_))
            if board.edges[e][0] == board.edges[e][1]:
                continue
            before = board.total_bad
            board.flip_orientation(e)
            newbad = board.total_bad
            if newbad <= before or rng.random() < math.exp(-(newbad - before) / max(T, 1e-6)):
                cur = newbad
            else:
                board.flip_orientation(e)
                cur = board.total_bad
        elif choice < flip_frac + 0.30:
            e1 = (rng.choice(list(board.hot)) if dd and board.hot
                  else rng.randrange(E_))
            e2 = (rng.choice(list(board.hot)) if dd and board.hot
                  else rng.randrange(E_))
            if e1 == e2:
                continue
            before = board.total_bad
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                continue
            newbad = board.total_bad
            if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-6)):
                cur = newbad
            else:
                board.undo_two_switch(undo)
                cur = board.total_bad
        else:
            # 3-switch enrichment
            e1 = rng.randrange(E_); e2 = rng.randrange(E_); e3 = rng.randrange(E_)
            if len({e1, e2, e3}) != 3:
                continue
            before = board.total_bad
            delta, undo = three_switch(board, e1, e2, e3, rng)
            if undo is None:
                continue
            newbad = board.total_bad
            if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-6)):
                cur = newbad
            else:
                undo_three_switch(board, undo)
                cur = board.total_bad
        if cur < best:
            best = cur
            best_edges = list(board.edges)
            best_cells = list(board.cells)
            stuck = 0
            min_best = min(min_best, best)
        else:
            stuck += 1
    # final validation: check the BEST config (not the current one) with the
    # independent brute-force verifier, and confirm a legal 2-factor.
    vb_board = E.Board(m)
    vb_board.build(best_edges, best_cells)
    vb = vb_board.verify_total()
    rs = [0] * m; cs = [0] * m
    for (x, y) in best_cells:
        rs[x] += 1; cs[y] += 1
    twf = all(rs[i] + cs[i] == 2 for i in range(m))
    found = (best == 0 and vb == 0 and twf)
    out = {
        "worker_id": worker_id,
        "m": m,
        "best_bad": best,
        "verify_total": vb,
        "two_factor": twf,
        "found": found,
        "time": time.time() - t0,
        "edges": best_edges,
        "cells": best_cells,
    }
    with open(out_path, "w") as f:
        json.dump(out, f)
    return out

def worker(worker_id, budget, seed, warm):
    rng = random.Random(seed)
    with open(LONG) as f:
        cfg = json.load(f)
    warm_edges = [tuple(e) for e in cfg["edges"]] if warm else None
    warm_cells = [tuple(c) for c in cfg["cells"]] if warm else None
    out_path = os.path.join(RES, f"swarm_D5_search_w{worker_id}.json")
    res = search_once(37, budget, warm_edges, warm_cells, rng, worker_id, out_path)
    tag = "FOUND" if res["found"] else f"best={res['best_bad']}"
    print(f"[w{worker_id}] {tag} verify={res['verify_total']} "
          f"2factor={res['two_factor']} t={res['time']:.0f}s", flush=True)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget", type=float, default=1000.0)
    ap.add_argument("--warm", action="store_true", default=True)
    ap.add_argument("--no-warm", dest="warm", action="store_false")
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()
    procs = []
    cw = max(1, min(args.workers, (os.cpu_count() or 4)))
    for w in range(cw):
        # alternate warm-start (from the 72 deep-min) and cold-start (random
        # 2-factor) so we explore both the 72-basin neighborhood AND fresh
        # topologies -- a full escape may need a different 2-factor skeleton.
        wflag = args.warm and (w % 2 == 0)
        p = Process(target=worker, args=(w, args.budget, args.seed + w * 7919,
                                          wflag))
        p.start()
        procs.append(p)
    found_path = None
    for p in procs:
        p.join()
    # collect best across workers
    best_overall = None
    for w in range(cw):
        fp = os.path.join(RES, f"swarm_D5_search_w{w}.json")
        if not os.path.exists(fp):
            continue
        with open(fp) as f:
            d = json.load(f)
        if d.get("found"):
            best_overall = d
            found_path = fp
            break
        if best_overall is None or d["best_bad"] < best_overall["best_bad"]:
            best_overall = d
    if best_overall is not None:
        with open(os.path.join(RES, "swarm_D5_search_best.json"), "w") as f:
            json.dump(best_overall, f, indent=2)
        print(f"== overall best_bad={best_overall['best_bad']} "
              f"found={best_overall.get('found')} "
              f"(saved swarm_D5_search_best.json)")
    if found_path:
        print(f"*** BREAKTHROUGH candidate at {found_path} ***")

if __name__ == "__main__":
    main()

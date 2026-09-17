"""swarm_D2_sa.py -- heatmap-biased multi-restart SA to escape the m=37 (X)=72 basin.

Direction D2: bias the search with the known-solution heatmap (hint_data.js /
hint_heatmap_m37.json) and run MANY parallel seeds+restarts of the VALIDATED
Th-44 engine (solver_theory_m37.Board).  Goal: find a basin different from 72,
ideally total_bad=0.

Bias design (keeps the ONLY real objective = total_bad exact, tracks best by it):
  * Biased 2-factor init: random 2-factor, then a short two_switch hill-climb on
    edge-frequency sum -> concentrates the graph on edges that occur in known
    rot4-NTIL solutions (a different basin region than uniform starts).
  * Biased orientation init: prefer the higher-frequency cell orientation.
  * Biased SA acceptance: objective = total_bad - GAMMA*heat_sum(cells), with
    GAMMA decaying 0..1 so early search is pulled to the heatmap region, then
    pure total_bad optimization.  Best tracked by PURE total_bad.
  * Biased move proposal: edges chosen weighted by (1+edge_freq) so moves land on
    solution-relevant edges; optional defect-directed focus on hot edges.

Every returned best is re-validated with Board.verify_total() (independent brute
force) before being called a candidate.
"""
import os, sys, json, math, random, time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as ST

M = 37


# ---------------------------------------------------------------------------
# heatmap
# ---------------------------------------------------------------------------
def load_heatmap():
    p = os.path.join(HERE, "results", "hint_heatmap_m37.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)["heat"]
    # fall back to hint_data.js
    txt = open(os.path.join(HERE, "hint_data.js")).read()
    s = txt.index("[[")
    e = txt.index("]]", s) + 2
    return json.loads(txt[s:e])


HEAT = load_heatmap()            # HEAT[i][j] frequency of cell (i,j)


def edge_freq(e):
    u, v = e
    return HEAT[u][u] if u == v else HEAT[u][v] + HEAT[v][u]


def cell_freq(c):
    return HEAT[c[0]][c[1]]


def heat_sum(cells):
    return sum(cell_freq(c) for c in cells)


def weighted_choice(rng, items, weights):
    total = sum(weights)
    if total <= 0:
        return rng.choice(items)
    r = rng.random() * total
    for it, w in zip(items, weights):
        r -= w
        if r <= 0:
            return it
    return items[-1]


# ---------------------------------------------------------------------------
# biased init
# ---------------------------------------------------------------------------
def biased_2factor(m, rng, climb=250):
    edges = None
    for _ in range(50):
        edges = ST.generate_2factor(m, rng)
        if edges is not None:
            break
    if edges is None:
        return None
    board = ST.Board(m)
    board.build(edges, ST.orient(edges, rng))
    E = m
    cur = sum(edge_freq(e) for e in board.edges)
    for _ in range(climb):
        e1 = rng.randrange(E)
        e2 = rng.randrange(E)
        if e1 == e2:
            continue
        old1, old2 = board.edges[e1], board.edges[e2]
        delta, undo = board.two_switch(e1, e2)
        if undo is None:
            continue
        new = cur - edge_freq(old1) - edge_freq(old2) \
              + edge_freq(board.edges[e1]) + edge_freq(board.edges[e2])
        # accept if improves edge_freq (with tiny tolerance for exploration)
        if new >= cur or rng.random() < math.exp((new - cur) / 1.0):
            cur = new
        else:
            board.undo_two_switch(undo)
    return list(board.edges)


def biased_orient(edges):
    cells = []
    for (u, v) in edges:
        if u == v:
            cells.append((u, u))
        else:
            cells.append((u, v) if HEAT[u][v] >= HEAT[v][u] else (v, u))
    return cells


# ---------------------------------------------------------------------------
# biased SA (single seed)
# ---------------------------------------------------------------------------
def sa_search_biased(seed, time_budget, gamma0, T0, Tend, flip_frac, perturb,
                     defect_directed, unbiased_init):
    rng = random.Random(seed)
    m = M
    if unbiased_init:
        edges = ST.generate_2factor(m, rng)
        if edges is None:
            return None
        cells = ST.orient(edges, rng)
    else:
        edges = biased_2factor(m, rng)
        if edges is None:
            return None
        cells = biased_orient(edges)

    board = ST.Board(m)
    board.build(edges, cells)
    best_bad = board.total_bad
    best_edges = list(board.edges)
    best_cells = list(board.cells)
    cur = best_bad
    E = m
    t0 = time.time()
    stuck = 0
    STUCK_LIMIT = 2500

    def gamma():
        frac = (time.time() - t0) / time_budget
        return gamma0 * max(0.0, 1.0 - frac)

    def obj():
        return board.total_bad - gamma() * heat_sum(board.cells)

    while time.time() - t0 < time_budget and cur > 0:
        frac = (time.time() - t0) / time_budget
        T = T0 * (Tend / T0) ** frac
        if stuck >= STUCK_LIMIT:
            board.build(best_edges, best_cells)
            cur = best_bad
            for _ in range(perturb):
                if rng.random() < flip_frac:
                    e = rng.randrange(E)
                    if board.edges[e][0] != board.edges[e][1]:
                        board.flip_orientation(e)
                else:
                    e1 = rng.randrange(E)
                    e2 = rng.randrange(E)
                    if e1 != e2:
                        board.two_switch(e1, e2)
            cur = board.total_bad
            stuck = 0
            T = max(T, T0 * 0.5)

        dd = defect_directed and board.hot and rng.random() < 0.6
        if rng.random() < flip_frac:
            if dd:
                cand = [e for e in board.hot
                        if board.edges[e][0] != board.edges[e][1]]
                e = rng.choice(cand) if cand else rng.randrange(E)
            else:
                w = [1.0 + edge_freq(board.edges[i]) for i in range(E)]
                e = weighted_choice(rng, list(range(E)), w)
            if board.edges[e][0] == board.edges[e][1]:
                continue
            o_old = board.cells[e]
            before = board.total_bad
            board.flip_orientation(e)
            newbad = board.total_bad
            d = (newbad - before) - gamma() * (cell_freq(board.cells[e])
                                               - cell_freq(o_old))
            if d <= 0 or rng.random() < math.exp(-d / max(T, 1e-9)):
                cur = newbad
            else:
                board.flip_orientation(e)   # toggle back
                cur = board.total_bad
        else:
            if dd:
                e1 = rng.choice(list(board.hot))
                e2 = rng.choice(list(board.hot))
            else:
                w = [1.0 + edge_freq(board.edges[i]) for i in range(E)]
                e1 = weighted_choice(rng, list(range(E)), w)
                e2 = weighted_choice(rng, list(range(E)), w)
            if e1 == e2:
                continue
            before = board.total_bad
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                continue
            newbad = board.total_bad
            d = (newbad - before)   # two_switch keeps same edges -> heat_sum unchanged
            if d <= 0 or rng.random() < math.exp(-d / max(T, 1e-9)):
                cur = newbad
            else:
                board.undo_two_switch(undo)
                cur = board.total_bad

        if cur < best_bad:
            best_bad = cur
            best_edges = list(board.edges)
            best_cells = list(board.cells)
            stuck = 0
        else:
            stuck += 1

    # independent brute validation
    vb = ST.Board(m)
    vb.build(best_edges, best_cells)
    vt = vb.verify_total()
    return {
        "seed": seed,
        "best_bad": best_bad,
        "verify_total": vt,
        "consistent": (vt == best_bad),
        "edges": best_edges,
        "cells": best_cells,
        "time": time.time() - t0,
        "found": best_bad == 0 and vt == 0,
    }


def worker(args):
    seed, tb, gamma0, T0, Tend, ff, pp, dd, ui = args
    try:
        return sa_search_biased(seed, tb, gamma0, T0, Tend, ff, pp, dd, ui)
    except Exception as ex:
        return {"seed": seed, "error": str(ex), "best_bad": None}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=24)
    ap.add_argument("--time", type=float, default=120.0)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--gamma0", type=float, default=10.0)
    ap.add_argument("--out", default="results/swarm_D2_sa.json")
    ap.add_argument("--base-seed", type=int, default=987654321)
    args = ap.parse_args()

    jobs = []
    for i in range(args.seeds):
        # alternate biased vs unbiased-init for diversity; vary gamma0 a bit
        unbiased_init = (i % 4 == 0)
        g0 = args.gamma0 if not unbiased_init else 0.0
        seed = args.base_seed + i * 100003
        jobs.append((seed, args.time, g0, 8.0, 0.02, 0.6, 12,
                     (i % 2 == 0), unbiased_init))

    print(f"== D2 heatmap-biased SA: {args.seeds} seeds x {args.time}s, "
          f"{args.workers} workers, gamma0={args.gamma0} ==", flush=True)
    t0 = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(worker, jobs):
            results.append(r)
            tag = ""
            if r.get("error"):
                tag = f"ERROR {r['error']}"
            else:
                tag = (f"best_bad={r['best_bad']} verify={r['verify_total']} "
                       f"consistent={r['consistent']} found={r['found']}")
            print(f"  seed={r.get('seed')}: {tag}  "
                  f"[{time.time()-t0:.0f}s]", flush=True)

    # aggregate
    valid = [r for r in results if r.get("best_bad") is not None]
    valid.sort(key=lambda r: (r["best_bad"], -r["verify_total"]))
    best = valid[0] if valid else None
    global_best = min((r["best_bad"] for r in valid), default=None)
    n_escaped = sum(1 for r in valid if r["best_bad"] < 72)
    n_found = sum(1 for r in valid if r.get("found"))
    print(f"== global_best_bad={global_best} escaped_72={n_escaped} "
          f"found={n_found} ==", flush=True)

    out = {
        "m": M, "direction": "D2-heatmap-biased-SA",
        "seeds": args.seeds, "time_per_seed": args.time, "gamma0": args.gamma0,
        "global_best_bad": global_best,
        "n_escaped_72": n_escaped,
        "n_found": n_found,
        "best_seed": best["seed"] if best else None,
        "best_consistent": best["consistent"] if best else None,
        "best_edges": best["edges"] if best else None,
        "best_cells": best["cells"] if best else None,
        "per_seed": [{"seed": r["seed"], "best_bad": r["best_bad"],
                      "verify_total": r.get("verify_total"),
                      "consistent": r.get("consistent"),
                      "found": r.get("found")} for r in valid],
    }
    with open(os.path.join(HERE, args.out), "w") as f:
        json.dump(out, f, indent=2)
    print(f"== saved {args.out} ==", flush=True)
    # immediate breakthrough check
    if best and best["found"] and best["consistent"]:
        print("BREAKTHROUGH: verifiably valid total_bad=0 config found!",
              flush=True)


if __name__ == "__main__":
    main()

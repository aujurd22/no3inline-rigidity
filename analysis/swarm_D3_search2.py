"""
swarm_D3_search2.py -- D3 complementary strategy: MANY short random restarts
of hypergraph-aware SA, with the focused nibble integrated into the loop
(greedy sweep over hottest edges every K steps). Different regime from
swarm_D3_search.py (which does 1 long descent from 72 + 1 from random).

Goal: beat the 72 deep-local-min via broader exploration + targeted descent.
"""
import sys, os, json, math, random, time
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("st", "solver_theory_m37.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

m = 37
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "swarm_D3_search2.json")
TIME_BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 1200.0
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 777
NRESTARTS = int(sys.argv[3]) if len(sys.argv) > 3 else 8
rng = random.Random(SEED)

def edge_scores(board):
    sc = {}
    for k, lp in board.line_pts.items():
        s = len(lp)
        if s < 3:
            continue
        per = (s - 1) * (s - 2) // 2
        for e in {i >> 2 for i in lp}:
            sc[e] = sc.get(e, 0) + per
    return sc

def focused_nibble(board, top_k=12, max_rounds=30):
    applied = 0
    for _ in range(max_rounds):
        sc = edge_scores(board)
        if not sc:
            break
        hot = sorted(sc, key=lambda e: -sc[e])[:top_k]
        improved = False
        for e in hot:
            if board.edges[e][0] == board.edges[e][1]:
                continue
            before = board.total_bad
            best_delta = 0
            best_move = None
            board.flip_orientation(e)
            d = board.total_bad - before
            if d < best_delta:
                best_delta = d; best_move = ('flip',)
            board.flip_orientation(e)
            for e2 in range(m):
                if e2 == e:
                    continue
                delta, undo = board.two_switch(e, e2)
                if undo is None:
                    continue
                if delta < best_delta:
                    best_delta = delta; best_move = ('switch', e2)
                board.undo_two_switch(undo)
            if best_move is not None and best_delta < 0:
                if best_move[0] == 'flip':
                    board.flip_orientation(e)
                else:
                    board.two_switch(e, best_move[1])
                improved = True; applied += 1
                break
        if not improved:
            break
    return applied

def sa_restart(edges0, cells0, tb, restart_id):
    board = st.Board(m)
    board.build(list(edges0), list(cells0))
    best = board.total_bad
    be, bc = list(board.edges), list(board.cells)
    cur = best
    T0, Tend = 10.0, 0.015
    stuck = 0
    t0 = time.time()
    last_nibble = 0
    while time.time() - t0 < tb and cur > 0:
        frac = (time.time() - t0) / tb
        T = T0 * (Tend / T0) ** frac
        # periodic focused nibble (integrated)
        if time.time() - last_nibble > 8.0:
            ap = focused_nibble(board, top_k=14, max_rounds=40)
            last_nibble = time.time()
            if board.total_bad < best:
                best = board.total_bad; be = list(board.edges); bc = list(board.cells)
            cur = board.total_bad
        if stuck >= 2500:
            board.build(be, bc); cur = best
            for _ in range(16):
                if rng.random() < 0.6:
                    e = rng.randrange(m)
                    if board.edges[e][0] != board.edges[e][1]:
                        board.flip_orientation(e)
                else:
                    e1 = rng.randrange(m); e2 = rng.randrange(m)
                    if e1 != e2:
                        board.two_switch(e1, e2)
            cur = board.total_bad; stuck = 0; T = max(T, T0 * 0.5)
        # score-weighted edge pick
        sc = edge_scores(board)
        if sc:
            hot = list(sc.keys()); w = [sc[e] + 1 for e in hot]
            e = rng.choices(hot, weights=w, k=1)[0]
        else:
            e = rng.randrange(m)
        if board.edges[e][0] == board.edges[e][1]:
            continue
        if rng.random() < 0.6:
            before = board.total_bad
            board.flip_orientation(e)
            nd = board.total_bad
            dl = nd - before
            if nd <= before or rng.random() < math.exp(-dl / max(T, 1e-9)):
                cur = nd
            else:
                board.flip_orientation(e); cur = board.total_bad
        else:
            sc = edge_scores(board)
            if sc and len(sc) > 1:
                hot2 = list(sc.keys())
                e2 = rng.choices(hot2, weights=[sc[x] + 1 for x in hot2], k=1)[0]
            else:
                e2 = rng.randrange(m)
            if e2 == e:
                continue
            before = board.total_bad
            dl, undo = board.two_switch(e, e2)
            if undo is None:
                continue
            nd = board.total_bad
            if nd <= before or rng.random() < math.exp(-dl / max(T, 1e-9)):
                cur = nd
            else:
                board.undo_two_switch(undo); cur = board.total_bad
        if cur < best:
            best = cur; be = list(board.edges); bc = list(board.cells); stuck = 0
        else:
            stuck += 1
    return best, be, bc

# main: many restarts
t_start = time.time()
global_best = None; gbe = None; gbc = None
per_restart = TIME_BUDGET / NRESTARTS
log = []
d72 = json.load(open(os.path.join(HERE, "results", "solver_theory_m37_long.json")))
edges72 = [tuple(e) for e in d72["edges"]]; cells72 = [tuple(c) for c in d72["cells"]]
for r in range(NRESTARTS):
    if r == 0:
        edges0, cells0 = edges72, cells72
    else:
        edges0 = st.generate_2factor(m, rng); cells0 = st.orient(edges0, rng)
    b, be, bc = sa_restart(edges0, cells0, per_restart, r)
    log.append(f"[{time.time()-t_start:.0f}s] restart {r}: best_bad={b}")
    if global_best is None or b < global_best:
        global_best = b; gbe = be; gbc = bc
    print(f"restart {r}: best_bad={b}  global_best={global_best}", flush=True)

# final verification
bb = st.Board(m); bb.build(gbe, gbc)
vt = bb.verify_total()
deg = [0]*m; seen=set(); twocyc=False
for (x,y) in gbc:
    uu,vv=(x,y) if x<y else (y,x) if x>y else (x,x)
    if uu!=vv:
        ee=(min(uu,vv),max(uu,vv))
        if ee in seen: twocyc=True
        seen.add(ee)
    deg[x]+=1; deg[y]+=1
legal = all(d==2 for d in deg) and not twocyc
out = {"m": m, "seed": SEED, "strategy": "multi-restart hypergraph-aware SA + integrated focused nibble",
       "time_budget": TIME_BUDGET, "nrestarts": NRESTARTS,
       "global_best_bad": global_best, "verify_total": vt, "legal_2factor": legal,
       "is_solution": bool(vt == 0 and legal), "edges": gbe, "cells": gbc, "log": log}
json.dump(out, open(OUT, "w"), indent=2)
print(f"=== search2 done: global_best={global_best} verify={vt} legal={legal} solution={vt==0 and legal}")

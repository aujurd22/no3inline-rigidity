"""
swarm_D3_search.py -- D3 (Conflict-Hypergraph LLL / Nibble) attack on m=37.

Exploits the SPARSITY of the (X) conflict hypergraph:
  * move selection weighted by per-edge triple-load (conflict-hypergraph degree)
  * a "focused nibble": periodic greedy sweep over the top-K hottest edges,
    trying every flip + every valid 2-switch and applying the best improvement
  * ILS perturbation when stuck (escape deep local minima like the 72-min)

Compares HYPERGRAPH-AWARE SA vs UNIFORM SA on the same time budget.
Every candidate reported as a solution MUST pass Board.verify_total()==0.
"""
import sys, os, json, math, random, time
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("st", "solver_theory_m37.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

m = 37
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "swarm_D3_search.json")
TIME_BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 1100.0
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20260715
MODE = sys.argv[3] if len(sys.argv) > 3 else "both"   # both|hyper|uniform
rng = random.Random(SEED)

# ---- per-edge triple-load (how many bad triples an edge is "in") ----
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

def focused_nibble(board, top_k=12, max_rounds=40):
    """Greedy sweep over the hottest edges: for each, try flip + all valid
    2-switches, apply the best strictly-improving move. Repeat until no gain
    or max_rounds. Returns number of improving moves applied."""
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
            best_move = None  # ('flip',) or ('switch', e2)
            # try flip
            board.flip_orientation(e)
            d = board.total_bad - before
            if d < best_delta:
                best_delta = d
                best_move = ('flip',)
            board.flip_orientation(e)  # revert
            # try 2-switches with every other edge
            for e2 in range(m):
                if e2 == e:
                    continue
                delta, undo = board.two_switch(e, e2)
                if undo is None:
                    continue
                if delta < best_delta:
                    best_delta = delta
                    best_move = ('switch', e2)
                board.undo_two_switch(undo)
            if best_move is not None and best_delta < 0:
                if best_move[0] == 'flip':
                    board.flip_orientation(e)
                else:
                    board.two_switch(e, best_move[1])
                improved = True
                applied += 1
                break  # restart sweep with updated board
        if not improved:
            break
    return applied

def run_sa(board, hyper, T0, Tend, time_budget, stuck_limit=3000, perturb=14):
    """Single SA run. hyper=True -> score-weighted (hypergraph-aware) moves."""
    t0 = time.time()
    best = board.total_bad
    best_edges = list(board.edges); best_cells = list(board.cells)
    cur = best
    stuck = 0
    E = m
    while time.time() - t0 < time_budget and cur > 0:
        frac = (time.time() - t0) / time_budget
        T = T0 * (Tend / T0) ** frac
        if stuck >= stuck_limit:
            # ILS perturbation from best
            board.build(best_edges, best_cells)
            cur = best
            for _ in range(perturb):
                if rng.random() < 0.6:
                    e = rng.randrange(E)
                    if board.edges[e][0] != board.edges[e][1]:
                        board.flip_orientation(e)
                else:
                    e1 = rng.randrange(E); e2 = rng.randrange(E)
                    if e1 != e2:
                        board.two_switch(e1, e2)
            cur = board.total_bad
            stuck = 0
            T = max(T, T0 * 0.5)
        # choose edge
        if hyper:
            sc = edge_scores(board)
            if sc:
                hot = list(sc.keys())
                w = [sc[e] + 1 for e in hot]
                e = rng.choices(hot, weights=w, k=1)[0]
            else:
                e = rng.randrange(E)
        else:
            e = rng.randrange(E)
        if board.edges[e][0] == board.edges[e][1]:
            continue
        # move type
        if rng.random() < 0.6:
            before = board.total_bad
            board.flip_orientation(e)
            newbad = board.total_bad
            delta = newbad - before
            if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-9)):
                cur = newbad
            else:
                board.flip_orientation(e); cur = board.total_bad
        else:
            if hyper:
                # pick partner e2 also from hot set if available
                sc = edge_scores(board)
                if sc and len(sc) > 1:
                    hot2 = list(sc.keys())
                    e2 = rng.choices(hot2, weights=[sc[x] + 1 for x in hot2], k=1)[0]
                else:
                    e2 = rng.randrange(E)
            else:
                e2 = rng.randrange(E)
            if e2 == e:
                continue
            before = board.total_bad
            delta, undo = board.two_switch(e, e2)
            if undo is None:
                continue
            newbad = board.total_bad
            if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-9)):
                cur = newbad
            else:
                board.undo_two_switch(undo); cur = board.total_bad
        if cur < best:
            best = cur
            best_edges = list(board.edges); best_cells = list(board.cells)
            stuck = 0
        else:
            stuck += 1
    return best, best_edges, best_cells

def attack_from(board0, hyper, label, time_budget):
    """Run SA from a copy of board0, plus periodic focused nibble."""
    board = st.Board(m)
    board.build(list(board0.edges), list(board0.cells))
    tb = time_budget
    # interleave: SA in chunks, focused nibble when stuck-ish
    best, be, bc = run_sa(board, hyper, T0=8.0, Tend=0.02, time_budget=tb)
    # try a focused nibble on the SA result
    b2 = st.Board(m); b2.build(be, bc)
    ap = focused_nibble(b2, top_k=14, max_rounds=60)
    if b2.total_bad < best:
        best = b2.total_bad; be = list(b2.edges); bc = list(b2.cells)
    return best, be, bc, ap

# ---- main ----
results = {}
log = []

# load the 72 best config
d72 = json.load(open(os.path.join(HERE, "results", "solver_theory_m37_long.json")))
edges72 = [tuple(e) for e in d72["edges"]]
cells72 = [tuple(c) for c in d72["cells"]]

t_start = time.time()
if MODE in ("both", "hyper"):
    log.append(f"[{time.time()-t_start:.0f}s] HYPERGRAPH-AWARE SA from 72-config, {TIME_BUDGET/2:.0f}s")
    b = st.Board(m); b.build(edges72, cells72)
    bh, eh, ch, _ = attack_from(b, True, "hyper@72", TIME_BUDGET / 2)
    # also a fresh random start
    b2 = st.Board(m)
    e2 = st.generate_2factor(m, rng); c2 = st.orient(e2, rng)
    b2.build(e2, c2)
    bh2, eh2, ch2, _ = attack_from(b2, True, "hyper@rand", TIME_BUDGET / 2)
    if bh2 < bh:
        bh, eh, ch = bh2, eh2, ch2
    results["hyper_best"] = bh
    results["hyper_edges"] = eh
    results["hyper_cells"] = ch
    log.append(f"[{time.time()-t_start:.0f}s] hyper best_bad={bh}")

if MODE in ("both", "uniform"):
    log.append(f"[{time.time()-t_start:.0f}s] UNIFORM SA from 72-config, {TIME_BUDGET/2:.0f}s")
    b = st.Board(m); b.build(edges72, cells72)
    bu, eu, cu, _ = attack_from(b, False, "uniform@72", TIME_BUDGET / 2)
    b2 = st.Board(m)
    e2 = st.generate_2factor(m, rng); c2 = st.orient(e2, rng)
    b2.build(e2, c2)
    bu2, eu2, cu2, _ = attack_from(b2, False, "uniform@rand", TIME_BUDGET / 2)
    if bu2 < bu:
        bu, eu, cu = bu2, eu2, cu2
    results["uniform_best"] = bu
    results["uniform_edges"] = eu
    results["uniform_cells"] = cu
    log.append(f"[{time.time()-t_start:.0f}s] uniform best_bad={bu}")

# save
out = {"m": m, "seed": SEED, "time_budget": TIME_BUDGET, "mode": MODE,
       "started_from": "best_bad=72 (verified) + random", "log": log}
out.update(results)
# verify the best found configs
for tag in ("hyper", "uniform"):
    if f"{tag}_edges" in out:
        bb = st.Board(m); bb.build(out[f"{tag}_edges"], out[f"{tag}_cells"])
        vt = bb.verify_total()
        out[f"{tag}_verify_total"] = vt
        # legality: 2-regular simple, no 2-cycle
        deg = [0]*m; seen=set(); twocyc=False
        for (x,y) in out[f"{tag}_cells"]:
            uu,vv=(x,y) if x<y else (y,x) if x>y else (x,x)
            if uu!=vv:
                ee=(min(uu,vv),max(uu,vv))
                if ee in seen: twocyc=True
                seen.add(ee)
            deg[x]+=1; deg[y]+=1
        out[f"{tag}_legal_2factor"] = (all(d==2 for d in deg) and not twocyc)
        out[f"{tag}_is_solution"] = (vt==0 and out[f"{tag}_legal_2factor"])

json.dump(out, open(OUT, "w"), indent=2)
print("=== D3 search done ===")
print("hyper_best =", out.get("hyper_best"), "verify=", out.get("hyper_verify_total"),
      "legal=", out.get("hyper_legal_2factor"))
print("uniform_best =", out.get("uniform_best"), "verify=", out.get("uniform_verify_total"),
      "legal=", out.get("uniform_legal_2factor"))
for l in log:
    print(l)

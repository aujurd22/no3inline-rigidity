import json, os, importlib.util, random, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("solver", os.path.join(HERE, "solver_theory_m37.py"))
solver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solver)

def involved_edges_indep(board):
    """Independent computation of which edges lie on a defect line (s >= 3)."""
    L = board.lifts
    N = len(L)
    groups = defaultdict(set)
    for i in range(N):
        for j in range(i + 1, N):
            if L[i] == L[j]:
                continue
            groups[solver.line_of(L[i], L[j])].add(i)
            groups[solver.line_of(L[i], L[j])].add(j)
    inv = set()
    for pts in groups.values():
        if len(pts) >= 3:
            for i in pts:
                inv.add(i >> 2)
    return inv

def check_engine(rng, m=10, moves=3000):
    edges = solver.generate_2factor(m, rng)
    cells = solver.orient(edges, rng)
    b = solver.Board(m)
    b.build(edges, cells)
    for _ in range(moves):
        if rng.random() < 0.6:
            e = rng.randrange(m)
            if b.edges[e][0] == b.edges[e][1]:
                continue
            b.flip_orientation(e)
            if rng.random() < 0.5:
                b.flip_orientation(e)  # undo
        else:
            e1 = rng.randrange(m); e2 = rng.randrange(m)
            if e1 == e2:
                continue
            d, u = b.two_switch(e1, e2)
            if u is None:
                continue
            if rng.random() < 0.5:
                b.undo_two_switch(u)
        if b.total_bad != b.verify_total():
            return False, "total_bad != verify_total"
        indep = involved_edges_indep(b)
        if set(b.hot.keys()) != indep:
            extra = set(b.hot.keys()) - indep
            missing = indep - set(b.hot.keys())
            dbg = []
            # find the defect line(s) containing a missing edge and dump state
            L = b.lifts
            N = len(L)
            groups = defaultdict(set)
            for i in range(N):
                for j in range(i + 1, N):
                    if L[i] == L[j]:
                        continue
                    kk = solver.line_of(L[i], L[j])
                    groups[kk].add(i); groups[kk].add(j)
            for e in list(missing)[:2]:
                for sig, pts in groups.items():
                    if len(pts) >= 3 and any(i >> 2 == e for i in pts):
                        lp_keys = list(b.line_pts.get(sig, {}).keys())
                        dbg.append(
                            f"edge {e} {b.edges[e]} on line {sig}: pts={sorted(pts)} "
                            f"edges={sorted(i>>2 for i in pts)} pc={b.pc.get(sig)} "
                            f"line_pts_keys={lp_keys} hot={ {i>>2: b.hot.get(i>>2) for i in pts} }")
                        break
            return False, (f"hot mismatch extra={sorted(extra)} missing={sorted(missing)}; "
                           f"dump: {' | '.join(dbg)}")
    return True, "ok"

rng = random.Random(12345)
ok, msg = check_engine(rng, 10, 3000)
print(f"[engine] m=10 3000 moves (flip+two_switch+undo): {'PASS' if ok else 'FAIL'} ({msg})")

# defect_directed finds solutions on small m?
found = 0
for t in range(2):
    res = solver.sa_search(7, time_budget=6.0, rng=rng,
                           defect_directed=True, dd_prob=0.6)
    b2 = solver.Board(7); b2.build(res["edges"], res["cells"])
    bb = b2.verify_total()
    if res["found"] and bb == 0:
        found += 1
    print(f"[dd m=7 trial {t}] found={res['found']} best={res['best']} brute={bb}")
print(f"[dd m=7] found {found}/2 valid solutions")

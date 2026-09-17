"""快速 D=1/L=0 GB 检验（1个2-圈，无自环）"""
import sys, itertools, time, json
from collections import Counter
sys.path.insert(0, '.')
sys.path.insert(0, 'benders')
from benders.benders_global import build_master, y_to_edges
from validate_solver import c4_lifts_n, verify_ntil
from ortools.sat.python import cp_model
import sympy as sp

M, N = 37, 74

def gb_check(edges):
    nc = len(edges)
    cp = {}
    for i, (u, v) in enumerate(edges):
        cp[(i, 0)] = c4_lifts_n((u, v), N)
        cp[(i, 1)] = c4_lifts_n((v, u), N)
    polys = []
    for i, j, k in itertools.combinations(range(nc), 3):
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = cp[(i, oi)] + cp[(j, oj)] + cp[(k, ok)]
            if any((x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)
                   for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(pts, 3)):
                polys.append([(i, oi), (j, oj), (k, ok)])
    xs = sp.symbols('x0:%d' % nc)
    sp_polys = []
    for poly in polys:
        expr = 1
        for vi, o in poly:
            expr *= (xs[vi] if o == 1 else (1 - xs[vi]))
        expanded = sp.expand(expr)
        if expanded != 0:
            sp_polys.append(expanded)
    if not sp_polys:
        return False, 0, 0
    t0 = time.time()
    G = sp.groebner(sp_polys, *xs, order='grevlex')
    return any(g == 1 or g == -1 for g in G), len(G), time.time() - t0

# 生成 D=1/L=0
model, y, pos, p2i = build_master(M, random_obj=True, seed=123)
is2 = {}
for (u, v) in pos:
    if u < v:
        b = model.NewBoolVar(f'is_{u}_{v}')
        is2[(u, v)] = b
        model.Add(y[(u, v)] == 2).OnlyEnforceIf(b)
        model.Add(y[(u, v)] != 2).OnlyEnforceIf(b.Not())
model.Add(sum(is2.values()) == 1)  # D=1
model.Add(sum([y[(i, i)] for i in range(M)]) == 0)  # L=0

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 15
solver.parameters.num_search_workers = 1
seen = set()

for trial in range(5):
    st = solver.Solve(model)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        break
    edges = y_to_edges(solver, y, pos)
    eset = frozenset((min(u, v), max(u, v)) for u, v in edges)
    if eset in seen:
        cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
        conds = [model.NewBoolVar(f"n{trial}_{up}") for up in cnt]
        for cd, (up, rp) in zip(conds, cnt.items()):
            model.Add(y[up] != rp).OnlyEnforceIf(cd)
        model.AddBoolOr(conds)
        continue
    seen.add(eset)
    
    cnt = Counter((min(u, v), max(u, v)) for u, v in edges if u != v)
    d = sum(1 for c in cnt.values() if c >= 2)
    l = sum(1 for u, v in edges if u == v)
    
    is_unsat, gb_sz, gb_t = gb_check(edges)
    status = "UNSAT" if is_unsat else ("SAT" if is_unsat is False else "?")
    print(f"[D1L0] t{trial}: D={d} L={l} n_edges={len(edges)} GB={status} ({gb_t:.0f}s)")
    
    if is_unsat is False:
        print("  *** GB non-[1]! SAT candidate! Trying incremental...")
        from benders.benders_global import incremental_solve_subproblem
        vd, bits, _, _, _ = incremental_solve_subproblem(edges, N, max_iter=500)
        print(f"  incremental: {vd}")
        if vd == 'sat_solution':
            ok, npts, bt = verify_ntil(edges, bits, N)
            print(f"  geom: ok={ok} bt={bt}")
            if ok:
                json.dump({'edges': edges, 'bits': bits, 'source': 'D1L0'},
                          open('m37_sol_D1L0.json', 'w'))
                print("  *** FOUND m=37 ROT4-NTIL SOLUTION!")
    
    cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
    conds = [model.NewBoolVar(f"z{trial}_{up}") for up in cnt]
    for cd, (up, rp) in zip(conds, cnt.items()):
        model.Add(y[up] != rp).OnlyEnforceIf(cd)
    model.AddBoolOr(conds)

print("done")

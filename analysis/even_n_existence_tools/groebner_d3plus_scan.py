"""
Comprehensive D>=3 Groebner basis scan for m=37.
Generates 2-factors with specific (D,L) configs via CP-SAT, runs GB.
D=3: L=0,1,2,3; D=4: L=0,1,2; D=5: L=0,1 (5 samples each = 45 GBs)
Appends to groebner_scan_d2plus.json
"""
import sys, itertools, time, json, math
from collections import Counter
sys.path.insert(0, '.')
sys.path.insert(0, 'benders')
from validate_solver import c4_lifts_n
from benders.benders_global import build_master, y_to_edges
from ortools.sat.python import cp_model
import sympy as sp

N, M = 74, 37

def groebner_quick(edges):
    ncells = len(edges)
    cell_pts = {}
    for idx, (u, v) in enumerate(edges):
        cell_pts[(idx, 0)] = c4_lifts_n((u, v), N)
        cell_pts[(idx, 1)] = c4_lifts_n((v, u), N)
    polys = []
    for i, j, k in itertools.combinations(range(ncells), 3):
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = (cell_pts[(i, oi)] + cell_pts[(j, oj)] + cell_pts[(k, ok)])
            if any((x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)
                   for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(pts, 3)):
                polys.append([(i, oi), (j, oj), (k, ok)])
    xs = sp.symbols('x0:%d' % ncells)
    sp_polys = []
    for poly in polys:
        expr = 1
        for vi, o in poly:
            expr *= (xs[vi] if o == 1 else (1 - xs[vi]))
        expanded = sp.expand(expr)
        if expanded != 0:
            sp_polys.append(expanded)
    if not sp_polys:
        return False, 0, 0, 0
    t0 = time.time()
    G = sp.groebner(sp_polys, *xs, order='grevlex')
    return any(g == 1 or g == -1 for g in G), len(G), time.time() - t0, len(sp_polys)


def test_config(config_name, max_d, max_l, n_samples, seed):
    """Generate n_samples 2-factors with D<=max_d, L<=max_l, run GB."""
    import random as _rand
    _rand.seed(seed)

    model, y, positions, pos2idx = build_master(M, random_obj=True, seed=seed)

    # D constraint
    if max_d is not None and max_d < M:
        is2 = {}
        for (u, v) in positions:
            if u < v:
                b = model.NewBoolVar(f"is2_{u}_{v}")
                is2[(u, v)] = b
                model.Add(y[(u, v)] == 2).OnlyEnforceIf(b)
                model.Add(y[(u, v)] != 2).OnlyEnforceIf(b.Not())
        model.Add(sum(is2.values()) <= max_d)

    # L constraint
    if max_l is not None:
        model.Add(sum([y[(i, i)] for i in range(M)]) <= max_l)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 12
    solver.parameters.num_search_workers = 1
    seen = set()
    results = []

    for trial in range(n_samples * 2):
        if len(results) >= n_samples:
            break
        st = solver.Solve(model)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            results.append({'exhausted': True, 'trial': trial})
            break
        edges = y_to_edges(solver, y, positions)
        eset = frozenset((min(u, v), max(u, v)) for u, v in edges)
        if eset in seen:
            cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
            conds = [model.NewBoolVar(f"z{trial}_{up}") for up in cnt]
            for cond, (up, rp) in zip(conds, cnt.items()):
                model.Add(y[up] != rp).OnlyEnforceIf(cond)
            model.AddBoolOr(conds)
            continue
        seen.add(eset)

        cnt = Counter((min(u, v), max(u, v)) for u, v in edges if u != v)
        d = sum(1 for c in cnt.values() if c >= 2)
        l = sum(1 for u, v in edges if u == v)

        is_unsat, gb_sz, gb_t, n_p = groebner_quick(edges)
        status = "UNSAT" if is_unsat else ("SAT" if is_unsat is False else "?")
        results.append({
            'D': d, 'L': l, 'n_edges': len(edges),
            'gb_unsat': is_unsat, 'gb_size': gb_sz,
            'gb_time': gb_t, 'n_polys': n_p
        })
        print(f"  [{config_name}] t{len(results)}: D={d} L={l} polys={n_p} "
              f"GB={status} ({gb_t:.0f}s)")

        if is_unsat is False:
            print(f"  ★★★ {config_name} GB NOT [1]! Possible SAT candidate!")
            # Try incremental SAT
            from benders.benders_global import incremental_solve_subproblem
            from validate_solver import verify_ntil
            vd, bits, _, _, _ = incremental_solve_subproblem(edges, N, max_iter=500)
            if vd == 'sat_solution':
                ok, npt, bt = verify_ntil(edges, bits, N)
                print(f"    Incremental: ok={ok} bt={bt}")
                if ok:
                    import json as jj
                    jj.dump({'m': 37, 'edges': edges, 'bits': bits, 'source': config_name},
                            open(f'm37_solution_{config_name}.json', 'w'))
                    return results, True

        cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
        conds = [model.NewBoolVar(f"e{trial}_{up}") for up in cnt]
        for cond, (up, rp) in zip(conds, cnt.items()):
            model.Add(y[up] != rp).OnlyEnforceIf(cond)
        model.AddBoolOr(conds)

    return results, False


# Configs to test (extending the existing scan)
configs = [
    ("D3_L1", 3, 1),   # 3 two-cycles + 1 self-loop
    ("D3_L2", 3, 2),   # 3 two-cycles + 2 self-loops
    ("D3_L3", 3, 3),   # 3 two-cycles + 3 self-loops
    ("D4_L0", 4, 0),   # 4 two-cycles, no self-loop
    ("D4_L1", 4, 1),   # 4 two-cycles + 1 self-loop
    ("D4_L2", 4, 2),   # 4 two-cycles + 2 self-loops
    ("D5_L0", 5, 0),   # 5 two-cycles, no self-loop
    ("D5_L1", 5, 1),   # 5 two-cycles + 1 self-loop
]

print("=" * 64)
print(f"Groebner D>=3 scan: {len(configs)} configs x 5 samples = ~45 GB tests")
print("Estimated time: 60-90 min")
print("=" * 64)

# Load existing results
try:
    existing = json.load(open('groebner_scan_d2plus.json'))
except:
    existing = {}

all_new_results = dict(existing)

for cfg_name, max_d, max_l in configs:
    if cfg_name in all_new_results:
        continue  # skip if already done
    print(f"\n--- {cfg_name} (D<={max_d}, L<={max_l}) ---")
    t0 = time.time()
    res, found = test_config(cfg_name, max_d, max_l, 5, seed=hash(cfg_name) % 10000)
    elapsed = time.time() - t0
    all_new_results[cfg_name] = res
    n_u = sum(1 for r in res if r.get('gb_unsat') is True)
    n_s = sum(1 for r in res if r.get('gb_unsat') is False)
    print(f"  => {cfg_name}: {len(res)} samples, UNSAT={n_u} SAT={n_s} ({elapsed:.0f}s)")
    if found:
        print(f"  ★★★ FOUND SOLUTION!")
        break
    # Save incrementally
    json.dump(all_new_results, open('groebner_scan_d2plus.json', 'w'), indent=2)

# Final summary
print(f"\n{'='*64}")
print("FINAL SUMMARY")
print("="*64)
total = sum(len(v) for v in all_new_results.values())
unsat = sum(sum(1 for s in v if s.get('gb_unsat')) for v in all_new_results.values())
sat = sum(sum(1 for s in v if s.get('gb_unsat') is False) for v in all_new_results.values())
print(f"Total: {total} samples, UNSAT={unsat}, SAT={sat}")
for k, v in sorted(all_new_results.items()):
    n_u = sum(1 for s in v if s.get('gb_unsat'))
    n_s = sum(1 for s in v if s.get('gb_unsat') is False)
    print(f"  {k}: {len(v)} ({n_u} UNSAT, {n_s} SAT)")

json.dump(all_new_results, open('groebner_scan_d2plus.json', 'w'), indent=2)
print(f"\nResults saved to groebner_scan_d2plus.json")

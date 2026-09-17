"""
可靠版：D=0/L=0, D=1/L=0, D=1/L=1 各 3 样本 GB 测试。
结果增量写入 groebner_config_scan.json，不被超时 kill。
"""
import sys, itertools, time, json, os
from collections import Counter
sys.path.insert(0, '.')
sys.path.insert(0, 'benders')
from benders.benders_global import build_master, y_to_edges
from validate_solver import c4_lifts_n, verify_ntil
from ortools.sat.python import cp_model
import sympy as sp

M, N = 37, 74
OUT = 'groebner_config_scan.json'

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
        return {'gb_unsat': False, 'gb_size': 0, 'gb_time': 0, 'n_polys': 0}
    t0 = time.time()
    G = sp.groebner(sp_polys, *xs, order='grevlex')
    elapsed = time.time() - t0
    is_unsat = any(g == 1 or g == -1 for g in G)
    return {'gb_unsat': is_unsat, 'gb_size': len(G), 'gb_time': elapsed, 'n_polys': len(sp_polys)}

def test_config(name, max_d, max_l, n_samples, seed):
    model, y, pos, p2i = build_master(M, random_obj=True, seed=seed)
    if max_d is not None and max_d < M:
        is2 = {}
        for (u, v) in pos:
            if u < v:
                b = model.NewBoolVar(f'i_{u}_{v}')
                is2[(u, v)] = b
                model.Add(y[(u, v)] == 2).OnlyEnforceIf(b)
                model.Add(y[(u, v)] != 2).OnlyEnforceIf(b.Not())
        model.Add(sum(is2.values()) <= max_d)
    if max_l is not None:
        model.Add(sum([y[(i, i)] for i in range(M)]) <= max_l)

    solv = cp_model.CpSolver()
    solv.parameters.max_time_in_seconds = 12
    solv.parameters.num_search_workers = 1
    seen = set()
    results = []

    for trial in range(n_samples * 3):
        if len(results) >= n_samples:
            break
        st = solv.Solve(model)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"  [{name}] CP-SAT exhausted after {len(results)} samples")
            break
        edges = y_to_edges(solv, y, pos)
        eset = frozenset((min(u, v), max(u, v)) for u, v in edges)
        if eset in seen:
            cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
            conds = [model.NewBoolVar(f"q{trial}_{up}") for up in cnt]
            for cd, (up, rp) in zip(conds, cnt.items()):
                model.Add(y[up] != rp).OnlyEnforceIf(cd)
            model.AddBoolOr(conds)
            continue
        seen.add(eset)

        cnt = Counter((min(u, v), max(u, v)) for u, v in edges if u != v)
        d = sum(1 for c in cnt.values() if c >= 2)
        l = sum(1 for u, v in edges if u == v)

        print(f"  [{name}] sample {len(results)+1}/{n_samples}: D={d} L={l} "
              f"n_edges={len(edges)} ...", end=' ', flush=True)
        gb_result = gb_check(edges)
        status = "UNSAT" if gb_result['gb_unsat'] else "SAT"
        print(f"GB={status} ({gb_result['gb_time']:.0f}s, "
              f"{gb_result['n_polys']} polys)")

        rec = {
            'config': name, 'sample': len(results),
            'D': d, 'L': l, 'n_edges': len(edges),
            'gb_unsat': gb_result['gb_unsat'],
            'gb_size': gb_result['gb_size'],
            'gb_time': round(gb_result['gb_time'], 1),
            'n_polys': gb_result['n_polys'],
        }

        if not gb_result['gb_unsat']:
            # SAT candidate! Try incremental verification.
            from benders.benders_global import incremental_solve_subproblem
            vd, bits, _, _, _ = incremental_solve_subproblem(edges, N, max_iter=500)
            rec['incremental_verdict'] = vd
            if vd == 'sat_solution':
                ok, npts, bt = verify_ntil(edges, bits, N)
                rec['geom_ok'] = ok
                rec['bad_triples'] = bt
                print(f"    *** INCREMENTAL: {vd} geom_ok={ok} bt={bt}")
                if ok:
                    json.dump({'edges': edges, 'bits': bits, 'source': name},
                              open(f'm37_sol_{name}.json', 'w'))
                    print(f"    *** FOUND m=37 ROT4-NTIL SOLUTION! Saved.")
                    results.append(rec)
                    break

        results.append(rec)

        # Save incrementally
        try:
            existing = json.load(open(OUT)) if os.path.exists(OUT) else {}
        except:
            existing = {}
        existing[name] = results
        json.dump(existing, open(OUT, 'w'), indent=2)

        cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
        conds = [model.NewBoolVar(f"z{trial}_{up}") for up in cnt]
        for cd, (up, rp) in zip(conds, cnt.items()):
            model.Add(y[up] != rp).OnlyEnforceIf(cd)
        model.AddBoolOr(conds)

    return results

# ==== Main ====
configs = [
    ("D0_L0", 0, 0, 3, 42),
    ("D1_L0", 1, 0, 3, 123),
    ("D1_L1", 1, 1, 3, 456),
]

print(f"=== Groebner Config Scan: {len(configs)} configs x ~3 samples ===")
print(f"Output: {OUT}\n")

all_results = {}
for name, md, ml, ns, seed in configs:
    print(f"--- {name} (D<={md}, L<={ml}) ---")
    res = test_config(name, md, ml, ns, seed)
    all_results[name] = res
    n_u = sum(1 for r in res if r.get('gb_unsat') is True)
    n_s = sum(1 for r in res if r.get('gb_unsat') is False)
    print(f"  => {name}: UNSAT={n_u} SAT={n_s} total={len(res)}\n")

print(f"\n===== SUMMARY =====")
for name, res in all_results.items():
    n_u = sum(1 for r in res if r.get('gb_unsat') is True)
    n_s = sum(1 for r in res if r.get('gb_unsat') is False)
    times = [r['gb_time'] for r in res if 'gb_time' in r]
    avg_t = sum(times) / len(times) if times else 0
    print(f"  {name}: UNSAT={n_u} SAT={n_s} avg_GB_time={avg_t:.0f}s")

json.dump(all_results, open(OUT, 'w'), indent=2)
print(f"\nFinal results saved to {OUT}")

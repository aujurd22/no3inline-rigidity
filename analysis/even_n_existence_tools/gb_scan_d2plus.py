"""D>=2 配置 GB 扫描：5 种配置 * 5 样本 = 25 GB 计算 (预计 ~30min)"""
import sys, itertools, time, json
from collections import Counter
sys.path.insert(0, '.')
sys.path.insert(0, 'benders')
from validate_solver import c4_lifts_n
from benders.benders_global import build_master, y_to_edges
from ortools.sat.python import cp_model
import sympy as sp

M, N = 37, 74
OUTPUT = "groebner_scan_d2plus.json"

def groebner_quick(edges):
    nc = len(edges)
    cp = {}
    for idx, (u, v) in enumerate(edges):
        cp[(idx, 0)] = c4_lifts_n((u, v), N)
        cp[(idx, 1)] = c4_lifts_n((v, u), N)
    polys = []
    for i, j, k in itertools.combinations(range(nc), 3):
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = cp[(i, oi)] + cp[(j, oj)] + cp[(k, ok)]
            if any((x2-x1)*(y3-y1) == (x3-x1)*(y2-y1)
                   for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3)):
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
        return False, 0, 0, 0
    t0 = time.time()
    G = sp.groebner(sp_polys, *xs, order='grevlex')
    is_unsat = any(g == 1 or g == -1 for g in G)
    return is_unsat, len(G), time.time() - t0, len(sp_polys)


def test_config(name, max_d, max_l, n_samples, seed=42):
    import random as _rand
    _rand.seed(seed)
    
    model, y, pos, p2i = build_master(M, random_obj=True, seed=seed)
    
    # D constraint: enforce exact number of 2-cycles
    if max_d is not None:
        is2 = {}
        for (u, v) in pos:
            if u < v:
                b = model.NewBoolVar(f"i_{u}_{v}")
                is2[(u, v)] = b
                model.Add(y[(u, v)] == 2).OnlyEnforceIf(b)
                model.Add(y[(u, v)] != 2).OnlyEnforceIf(b.Not())
        # For D>=2, use <= max_d to allow CP-SAT flexibility
        model.Add(sum(is2.values()) <= max_d)
        # Add lower bound to bias toward target D
        model.Add(sum(is2.values()) >= max(0, max_d - 1))
    
    if max_l is not None:
        loops_vars = [y[(i, i)] for i in range(M)]
        model.Add(sum(loops_vars) <= max_l)
        if max_l > 0:
            model.Add(sum(loops_vars) >= max(0, max_l - 1))
    
    solv = cp_model.CpSolver()
    solv.parameters.max_time_in_seconds = 20
    solv.parameters.num_search_workers = 1
    seen = set()
    cfg_res = []
    
    for trial in range(n_samples * 3):
        if len(cfg_res) >= n_samples:
            break
        st = solv.Solve(model)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"    [{name}] CP-SAT exhausted after {len(cfg_res)} samples")
            break
        edges = y_to_edges(solv, y, pos)
        eset = frozenset((min(u, v), max(u, v)) for u, v in edges)
        if eset in seen:
            cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
            conds = [model.NewBoolVar(f"n{trial}_{up}") for up in cnt]
            for cond, (up, rp) in zip(conds, cnt.items()):
                model.Add(y[up] != rp).OnlyEnforceIf(cond)
            model.AddBoolOr(conds)
            continue
        seen.add(eset)
        
        cnt = Counter((min(u, v), max(u, v)) for u, v in edges if u != v)
        d = sum(1 for c in cnt.values() if c >= 2)
        l = sum(1 for u, v in edges if u == v)
        
        print(f"    [{name}] sample {len(cfg_res)}: D={d} L={l} ", end="", flush=True)
        is_unsat, gb_sz, gb_t, n_p = groebner_quick(edges)
        status = "UNSAT" if is_unsat else ("SAT!" if is_unsat is False else "?")
        print(f"GB={status} ({gb_t:.0f}s, {n_p} polys)")
        
        r = {
            'config': name, 'sample': len(cfg_res), 'D': d, 'L': l,
            'n_edges': len(edges), 'gb_unsat': is_unsat,
            'gb_size': gb_sz, 'gb_time': round(gb_t, 1), 'n_polys': n_p
        }
        cfg_res.append(r)
        
        # Write incrementally
        results[name] = cfg_res
        with open(OUTPUT, 'w') as f:
            json.dump(results, f, indent=2)
        
        if is_unsat is False:
            print(f"    ★★★ {name} sample {len(cfg_res)-1}: GB NOT [1]! Possible SAT candidate!")
            # Quick incremental check
            from benders.benders_global import incremental_solve_subproblem
            from validate_solver import verify_ntil
            verdict, bits, _, _, _ = incremental_solve_subproblem(edges, N, max_iter=500)
            if verdict == 'sat_solution':
                ok, npts, bt = verify_ntil(edges, bits, N)
                print(f"    ★ Incremental: ok={ok} bt={bt}")
                if ok:
                    import json as j2
                    j2.dump({'edges': edges, 'bits': bits, 'source': name},
                            open(f'm37_sol_{name}.json', 'w'))
                    return cfg_res, True
        
        cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
        conds = [model.NewBoolVar(f"x{trial}_{up}") for up in cnt]
        for cond, (up, rp) in zip(conds, cnt.items()):
            model.Add(y[up] != rp).OnlyEnforceIf(cond)
        model.AddBoolOr(conds)
    
    return cfg_res, False


if __name__ == "__main__":
    # Load previous results if any
    try:
        with open(OUTPUT) as f:
            results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        results = {}
    
    configs = [
        ("D2_L0", 2, 0, 5),
        ("D2_L1", 2, 1, 5),
        ("D2_L2", 2, 2, 5),
        ("D3_L0", 3, 0, 5),
        ("D3_L1", 3, 1, 5),
    ]
    
    t_start = time.time()
    for name, md, ml, ns in configs:
        if name in results:
            print(f"\n=== {name}: already have {len(results[name])} samples, skipping ===")
            continue
        print(f"\n=== {name} (D={md}, L={ml}) ===")
        res, found = test_config(name, md, ml, ns, seed=hash(name) % 10000)
        if found:
            print(f"\n★★★ {name} FOUND SOLUTION! ★★★")
            break
    
    elapsed = time.time() - t_start
    print(f"\n===== D>=2 SCAN COMPLETE ({elapsed:.0f}s) =====")
    for name, samples in results.items():
        u = sum(1 for s in samples if s.get('gb_unsat') is True)
        s = sum(1 for s in samples if s.get('gb_unsat') is False)
        times = [s['gb_time'] for s in samples if s.get('gb_time')]
        print(f"  {name}: UNSAT={u} SAT={s} (avg GB: {sum(times)/len(times):.0f}s)" if times else f"  {name}: no results")

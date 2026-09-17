"""
分析全坏三元组几何特征 + 扫 D/L 组合找 m=37 解。
"""
import sys, time, json, itertools
from collections import Counter, defaultdict
sys.path.insert(0, '.')
sys.path.insert(0, 'benders')
from validate_solver import c4_lifts_n, load_negatives, load_positive
from benders.benders_global import build_master, y_to_edges
from ortools.sat.python import cp_model
import sympy as sp

N, M = 74, 37

# ===== Part 1: 全坏三元组几何分析 =====
print("=" * 60)
print("Part 1: 全坏三元组几何分析")
print("=" * 60)

def rot4_cycle(pts):
    """返回 pts 的 rot4 轨道（C4 作用）"""
    orbit = []
    for x, y in pts:
        orbit.append((x, y))
        orbit.append((N-1-y, x))
        orbit.append((N-1-x, N-1-y))
        orbit.append((y, N-1-x))
    return orbit

def collinear_check(pts):
    for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            return True
    return False

def analyze_triple(e1, e2, e3, N_val):
    """详细分析一个三元组的 8 种取向"""
    u1,v1 = e1; u2,v2 = e2; u3,v3 = e3
    results = []
    for o1, o2, o3 in itertools.product([0,1], repeat=3):
        pts = []
        pts.extend(c4_lifts_n((v1,u1) if o1 else (u1,v1), N_val))
        pts.extend(c4_lifts_n((v2,u2) if o2 else (u2,v2), N_val))
        pts.extend(c4_lifts_n((v3,u3) if o3 else (u3,v3), N_val))
        bad = collinear_check(pts)
        results.append(((o1,o2,o3), bad))

    n_bad = sum(1 for _, b in results if b)
    return results, n_bad

# 从 V20_01 取出所有全坏三元组
basins = load_negatives()
edges_v01 = basins[0][1]
N_val = 74

cell_pts = {}
for idx, (u, v) in enumerate(edges_v01):
    cell_pts[(idx, 0)] = c4_lifts_n((u, v), N_val)
    cell_pts[(idx, 1)] = c4_lifts_n((v, u), N_val)

all_bad_triples = []
for i, j, k in itertools.combinations(range(37), 3):
    all_bad = True
    for oi, oj, ok in itertools.product([0, 1], repeat=3):
        pts = cell_pts[(i, oi)] + cell_pts[(j, oj)] + cell_pts[(k, ok)]
        if not collinear_check(pts):
            all_bad = False
            break
    if all_bad:
        all_bad_triples.append((i, j, k))

print(f"V20_01 全坏三元组数: {len(all_bad_triples)}")
print(f"最小全坏三元组: cells {all_bad_triples[0]}")
print(f"  对应边: {edges_v01[6]}, {edges_v01[22]}, {edges_v01[26]}")

# 详细分析最小全坏三元组
print(f"\n--- 最小全坏三元组 (cells 6,22,26) 详细分析 ---")
results, n_bad = analyze_triple(
    edges_v01[6], edges_v01[22], edges_v01[26], N_val)
print(f"8 种取向中 {n_bad} 种产生共线")

for (o1, o2, o3), bad in results:
    status = "共线 ✗" if bad else "安全 ✓"
    if bad:
        # 找出哪三点共线
        pts = (c4_lifts_n((edges_v01[6][1],edges_v01[6][0]) if o1 else edges_v01[6], N_val) +
               c4_lifts_n((edges_v01[22][1],edges_v01[22][0]) if o2 else edges_v01[22], N_val) +
               c4_lifts_n((edges_v01[26][1],edges_v01[26][0]) if o3 else edges_v01[26], N_val))
        for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                print(f"  取向({o1},{o2},{o3}): {status}  坏三点={(x1,y1),(x2,y2),(x3,y3)}")
                break

# 分析全坏三元组的边对特征
print(f"\n--- 全坏三元组的边对特征分析 ---")
all_edge_pairs = []
for i, j, k in all_bad_triples:
    e1 = (min(edges_v01[i]), max(edges_v01[i]))
    e2 = (min(edges_v01[j]), max(edges_v01[j]))
    e3 = (min(edges_v01[k]), max(edges_v01[k]))
    all_edge_pairs.append((e1, e2, e3))

# 检查是否有共同的自环或其他结构特征
has_self_loop = sum(1 for e1,e2,e3 in all_edge_pairs
                    if e1[0]==e1[1] or e2[0]==e2[1] or e3[0]==e3[1])
print(f"含自环的全坏三元组: {has_self_loop}/{len(all_bad_triples)}")

# 检查顶点是否形成某种模式
# 对 V20_01 的全坏三元组，找共同的端点和结构
vertex_freq = Counter()
for i, j, k in all_bad_triples:
    for idx in [i, j, k]:
        u, v = edges_v01[idx]
        vertex_freq[u] += 1
        vertex_freq[v] += 1
print(f"最频繁的顶点: {vertex_freq.most_common(8)}")

# 边对出现频次
edge_freq = Counter()
for i, j, k in all_bad_triples:
    for idx in [i, j, k]:
        edge_freq[(min(edges_v01[idx]), max(edges_v01[idx]))] += 1
print(f"最频繁的边对: {edge_freq.most_common(8)}")

# ===== Part 2: 六盆地全坏三元组对比 =====
print(f"\n{'='*60}")
print("Part 2: 六盆地全坏三元组对比")
print("="*60)

for bid, edges in basins:
    cell_pts_b = {}
    for idx, (u, v) in enumerate(edges):
        cell_pts_b[(idx, 0)] = c4_lifts_n((u, v), N_val)
        cell_pts_b[(idx, 1)] = c4_lifts_n((v, u), N_val)

    bad3_count = 0
    for i, j, k in itertools.combinations(range(37), 3):
        all_bad = True
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = cell_pts_b[(i, oi)] + cell_pts_b[(j, oj)] + cell_pts_b[(k, ok)]
            if not collinear_check(pts):
                all_bad = False
                break
        if all_bad:
            bad3_count += 1
    print(f"  {bid}: {bad3_count} 个全坏三元组")

    # 如果有全坏三元组，看它们的边集
    if bad3_count > 0:
        edge_in_bad = Counter()
        for i, j, k in itertools.combinations(range(37), 3):
            all_bad = True
            for oi, oj, ok in itertools.product([0, 1], repeat=3):
                pts = cell_pts_b[(i, oi)] + cell_pts_b[(j, oj)] + cell_pts_b[(k, ok)]
                if not collinear_check(pts):
                    all_bad = False
                    break
            if all_bad:
                for idx in [i, j, k]:
                    edge_in_bad[(min(edges[idx]), max(edges[idx]))] += 1
        top_edges = edge_in_bad.most_common(3)
        print(f"    最常出现在坏三元组的边: {top_edges}")

# ===== Part 3: 扫 D/L 组合用 GB 快速验证 =====
print(f"\n{'='*60}")
print("Part 3: 扫 7 种 D/L 组合 (各 5 样本)")
print("="*60)

def gb_quick(edges, N_use):
    ncells = len(edges)
    cell_pts = {}
    for idx, (u, v) in enumerate(edges):
        cell_pts[(idx, 0)] = c4_lifts_n((u, v), N_use)
        cell_pts[(idx, 1)] = c4_lifts_n((v, u), N_use)
    polys = []
    for i, j, k in itertools.combinations(range(ncells), 3):
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = (cell_pts[(i, oi)] + cell_pts[(j, oj)] + cell_pts[(k, ok)])
            if collinear_check(pts):
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

# 扫描的 D/L 组合
sweeps = [
    ("D0_L0", 0, 0, "纯 37-cycle"),
    ("D0_L1", 0, 1, "1 自环+36-cycle (已知 14/14 UNSAT)"),
    ("D0_L2", 0, 2, "2 自环+35-cycle"),
    ("D1_L0", 1, 0, "1 个 2-圈+35-cycle"),
    ("D1_L1", 1, 1, "1 个 2-圈+1 自环+34-cycle"),
    ("D2_L0", 2, 0, "2 个 2-圈+33-cycle"),
    ("D3_L0", 3, 0, "3 个 2-圈+31-cycle"),
]

sweep_results = {}
import random as _rand

for cfg_name, max_d, max_l, desc in sweeps:
    print(f"\n--- {cfg_name} ({desc}) ---")

    model_s, y_s, pos_s, p2i = build_master(M, random_obj=True, seed=hash(cfg_name) % 10000)
    if max_d is not None:
        is2 = {}
        for (u, v) in pos_s:
            if u < v:
                b = model_s.NewBoolVar(f"i2_{u}_{v}")
                is2[(u, v)] = b
                model_s.Add(y_s[(u, v)] == 2).OnlyEnforceIf(b)
                model_s.Add(y_s[(u, v)] != 2).OnlyEnforceIf(b.Not())
        model_s.Add(sum(is2.values()) <= max_d)
    if max_l is not None:
        model_s.Add(sum([y_s[(i, i)] for i in range(M)]) <= max_l)

    solv_s = cp_model.CpSolver()
    solv_s.parameters.max_time_in_seconds = 15
    solv_s.parameters.num_search_workers = 1
    seen_s = set()
    cfg_res = []

    for trial in range(5):
        st = solv_s.Solve(model_s)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            cfg_res.append({'trial': trial, 'status': 'exhausted'})
            print(f"    t{trial}: CP-SAT 耗尽")
            break
        edges = y_to_edges(solv_s, y_s, pos_s)
        eset = frozenset((min(u, v), max(u, v)) for u, v in edges)
        if eset in seen_s:
            cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
            conds = [model_s.NewBoolVar(f"n{trial}_{up}") for up in cnt]
            for cond, (up, rp) in zip(conds, cnt.items()):
                model_s.Add(y_s[up] != rp).OnlyEnforceIf(cond)
            model_s.AddBoolOr(conds)
            continue
        seen_s.add(eset)

        cnt = Counter((min(u, v), max(u, v)) for u, v in edges if u != v)
        d = sum(1 for c in cnt.values() if c >= 2)
        l = sum(1 for u, v in edges if u == v)

        is_unsat, gb_sz, gb_t, n_p = gb_quick(edges, N)
        status = "UNSAT" if is_unsat else ("SAT" if is_unsat is False else "?")
        print(f"    t{trial}: D={d} L={l} GB={status} ({gb_t:.1f}s, {n_p} polys)")

        cfg_res.append({
            'trial': trial, 'D': d, 'L': l,
            'gb_unsat': is_unsat, 'gb_time': round(gb_t, 1),
            'n_polys': n_p
        })

        # 如果 SAT，尝试增量 SAT 找真解
        if is_unsat is False:
            from benders.benders_global import incremental_solve_subproblem
            verdict, bits, _, _, _, _ = incremental_solve_subproblem(edges, N, max_iter=500)
            if verdict == 'sat_solution':
                from validate_solver import verify_ntil
                ok, npts, bt = verify_ntil(edges, bits, N)
                if ok:
                    print(f"    ★★★ 发现 m=37 rot4-NTIL 解！D={d} L={l}")
                    sol = {'m': 37, 'edges': edges, 'bits': bits,
                           'D': d, 'L': l, 'source': cfg_name}
                    json.dump(sol, open(f"m37_sol_{cfg_name}.json", "w"), indent=2)
                    sweep_results[cfg_name] = {'found_solution': True, 'solution': sol}
                    break
                else:
                    print(f"    sat_但是 bad_triples={bt}")
            elif verdict == 'unsat':
                cfg_res[-1]['incremental_unsat'] = True

        cnt = Counter((min(u, v), max(u, v)) for u, v in edges)
        conds = [model_s.NewBoolVar(f"w{trial}_{up}") for up in cnt]
        for cond, (up, rp) in zip(conds, cnt.items()):
            model_s.Add(y_s[up] != rp).OnlyEnforceIf(cond)
        model_s.AddBoolOr(conds)

    if cfg_name not in sweep_results:
        sweep_results[cfg_name] = {'results': cfg_res}
        n_u = sum(1 for r in cfg_res if r.get('gb_unsat') is True)
        n_s = sum(1 for r in cfg_res if r.get('gb_unsat') is False)
        print(f"  => UNSAT={n_u} SAT={n_s}")

# ===== 汇总 =====
print(f"\n{'='*60}")
print("Part 4: 总结")
print("="*60)

print("\n全坏三元组特征:")
print("- V20_01: 1 个 (cells 6,22,26) — edges (3,31),(11,23),(14,20)")
print("- V20_03: 1 个, V20_04: 1 个, V20_05: 1 个")
print("- V20_02: 0 个, V20_06: 0 个 (但 GB 仍 = [1])")

print("\nD/L 扫描结果:")
for cfg_name, _, _, desc in sweeps:
    if cfg_name in sweep_results:
        r = sweep_results[cfg_name]
        if 'found_solution' in r:
            print(f"  {cfg_name} ({desc}): ★★★ 发现解！")
        elif 'results' in r:
            n_u = sum(1 for x in r['results'] if x.get('gb_unsat') is True)
            n_s = sum(1 for x in r['results'] if x.get('gb_unsat') is False)
            print(f"  {cfg_name} ({desc}): UNSAT={n_u} SAT={n_s}/{len(r['results'])}")
    else:
        print(f"  {cfg_name} ({desc}): (未运行)")

# 保存
json.dump({
    'allbad_analysis': {
        'v20_01_count': len(all_bad_triples),
        'v20_01_smallest': [(int(i), int(j), int(k))
                            for i, j, k in all_bad_triples[:1]],
    },
    'sweep_results': {k: v for k, v in sweep_results.items()}
}, open("allbad_and_sweep_results.json", "w"), indent=2, default=str)
print("\n已保存 allbad_and_sweep_results.json")

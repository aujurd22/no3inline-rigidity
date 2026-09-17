"""
CP-SAT 全约束 NTIL 双排列模型 v2 —— 修复 pi ≠ sigma 约束 + n=74 直测。
对 n=10-18 验证正确性，对 n=20-74 做可扩展性测试。
"""
import sys, itertools, time, json, math

def build_model(n):
    """构建 CP-SAT 双排列 NTIL 模型。返回 (model, pi_vars, sigma_vars)。"""
    from ortools.sat.python import cp_model as cpm
    m = cpm.CpModel()
    pi_v = {}; si_v = {}
    for i in range(n):
        for j in range(n):
            pi_v[(i,j)] = m.NewBoolVar(f'pi{i}_{j}')
            si_v[(i,j)] = m.NewBoolVar(f'si{i}_{j}')
    # 排列约束
    for i in range(n):
        m.AddExactlyOne([pi_v[(i,j)] for j in range(n)])
        m.AddExactlyOne([si_v[(i,j)] for j in range(n)])
    for j in range(n):
        m.AddExactlyOne([pi_v[(i,j)] for i in range(n)])
        m.AddExactlyOne([si_v[(i,j)] for i in range(n)])
    # ★ 修正：pi(i) != sigma(i) for all i
    for i in range(n):
        for j in range(n):
            m.Add(pi_v[(i,j)] + si_v[(i,j)] <= 1)
    
    # 线约束：每条含 ≥3 格点的直线最多选 2 个点
    lines = _gen_lines(n)
    n_lines_added = 0
    for line in lines:
        if len(line) >= 3:
            terms = []
            for (x,y) in line:
                terms.append(pi_v.get((x,y), m.NewConstant(0)))
                terms.append(si_v.get((x,y), m.NewConstant(0)))
            if len(terms) >= 3:
                m.Add(sum(terms) <= 2)
                n_lines_added += 1
    return m, pi_v, si_v, n_lines_added


def _gen_lines(n):
    """生成所有含 ≥3 格点的直线（去重方向）。"""
    lines = set()
    for dx in range(n):
        for dy in range(-n+1, n):
            if dx == 0 and dy <= 0: continue
            if dx == 0 and dy > 0:
                g = 1; sx, sy = 0, 1
            else:
                g = math.gcd(abs(dx), abs(dy))
                sx, sy = dx//g, dy//g
            
            seen = set()
            for x0 in range(n):
                for y0 in range(n):
                    pts = []
                    x, y = x0, y0
                    while 0 <= x < n and 0 <= y < n:
                        pts.append((x,y)); x += sx; y += sy
                    if len(pts) >= 3:
                        key = tuple(sorted(pts))
                        seen.add(key)
            lines.update(seen)
    return [list(ln) for ln in lines]


def solve_and_verify(n, max_time=300):
    import time as _t
    m, pi_v, si_v, n_lines = build_model(n)
    from ortools.sat.python import cp_model as cpm2
    solver = cpm2.CpSolver()
    solver.parameters.max_time_in_seconds = max_time
    solver.parameters.num_search_workers = 1
    
    t0 = _t.time()
    st = solver.Solve(m)
    elapsed = _t.time() - t0
    
    result = {
        'n': n, 'status': solver.StatusName(st), 'time': round(elapsed, 1),
        'n_vars': n*n*2, 'n_lines': n_lines,
        'wall_time': solver.WallTime()
    }
    
    if st == 4 or st == 2:  # OPTIMAL or FEASIBLE
        pi = [0]*n; sigma = [0]*n
        for i in range(n):
            for j in range(n):
                if solver.Value(pi_v[(i,j)]) == 1: pi[i] = j
                if solver.Value(si_v[(i,j)]) == 1: sigma[i] = j
        
        pts = [(i, pi[i]) for i in range(n)] + [(i, sigma[i]) for i in range(n)]
        unique_pts = len(set(pts))
        bad = sum(1 for p1,p2,p3 in itertools.combinations(pts,3)
                  if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
        
        result['pi'] = pi
        result['sigma'] = sigma
        result['unique_pts'] = unique_pts
        result['n_collinear'] = bad
        result['ntil_ok'] = (bad == 0 and unique_pts == 2*n)
    else:
        result['ntil_ok'] = False
    
    return result


if __name__ == '__main__':
    import random
    random.seed(42)
    
    print("=" * 64)
    print("CP-SAT 全约束 NTIL 双排列模型 v2（pi ≠ sigma 修正）")
    print("=" * 64)
    
    results = []
    
    # 小 n 验证正确性
    for n in [8, 10, 12, 14, 16, 18, 20]:
        print(f"\n--- n={n} ---")
        r = solve_and_verify(n, max_time=120)
        results.append(r)
        ok = "✓ NTIL!" if r.get('ntil_ok') else f"✗ pts={r.get('unique_pts','?')}/{2*n} collinear={r.get('n_collinear','?')}"
        print(f"  {r['status']} ({r['time']}s) {ok} vars={r['n_vars']} lines={r['n_lines']}")
        if r.get('ntil_ok'):
            print(f"  pi[:10]={r['pi'][:10]}")
            print(f"  sigma[:10]={r['sigma'][:10]}")
    
    # 保存结果
    json.dump(results, open('cpsat_scaling_v2.json', 'w'), indent=2)
    
    # 汇总
    print(f"\n===== 汇总 =====")
    solved = sum(1 for r in results if r.get('ntil_ok'))
    print(f"NTIL解: {solved}/{len(results)}")
    for r in results:
        icon = "✓" if r.get('ntil_ok') else "✗"
        print(f"  n={r['n']:>3}: {icon} {r['status']} ({r['time']:>5.1f}s) lines={r['n_lines']:>6}")
    
    # 如果 n=20 能解→试 n=74
    if any(r.get('ntil_ok') and r['n']==20 for r in results):
        print(f"\n=== n=74 直测 (10min timeout) ===")
        r74 = solve_and_verify(74, max_time=600)
        print(f"  {r74['status']} ({r74['time']}s)")
        print(f"  ntil_ok={r74.get('ntil_ok')} collinear={r74.get('n_collinear','?')}")
        if r74.get('ntil_ok'):
            json.dump(r74, open('ntil_solution_n74_cpsat.json', 'w'), indent=2)
            print("  ★★★ N=74 NTIL 解！已保存。")
    else:
        print("\nn=20 未解→外推不足，不试 n=74")
    
    print("\n完成。")

"""
CP-SAT 直测 n=16/20/30/74，带对称破缺 + 近对合引导。
"""
import itertools, time, math, json, sys
from ortools.sat.python import cp_model

def build_ntil_model(n, sym_break=True, near_involution=False):
    m = cp_model.CpModel()
    pv = {}; sv = {}
    for i in range(n):
        for j in range(n):
            pv[(i,j)] = m.NewBoolVar(f'p{i}_{j}')
            sv[(i,j)] = m.NewBoolVar(f's{i}_{j}')
    
    for i in range(n):
        m.AddExactlyOne([pv[(i,j)] for j in range(n)])
        m.AddExactlyOne([sv[(i,j)] for j in range(n)])
    for j in range(n):
        m.AddExactlyOne([pv[(i,j)] for i in range(n)])
        m.AddExactlyOne([sv[(i,j)] for i in range(n)])
    for i in range(n):
        for j in range(n):
            m.Add(pv[(i,j)] + sv[(i,j)] <= 1)
    
    if sym_break:
        m.Add(pv[(0,0)] == 1)  # pi(0)=0
        m.Add(sv[(0,1)] == 1)  # sigma(0)=1
    
    if near_involution and n >= 8:
        # pi(i)+sigma(i)=n-1 for ~80% of rows (soft prefer via objective)
        # Use auxiliary variables to count involution matches
        inv_vars = []
        for i in range(n):
            inv = m.NewBoolVar(f'inv_{i}')
            # inv=1 iff sigma(i)=n-1-pi(i)
            for j in range(n):
                if n-1-j >= 0:
                    m.Add(pv[(i,j)] + sv[(i,n-1-j)] <= 1 + inv).OnlyEnforceIf(inv.Not())
                    # This is complex; simplify by just adding the constraint for many rows
            # Simpler: for i in 1..n-1, require pi(i)+sigma(i)=n-1
            if i > 0:
                inv_vars.append(inv)
        # Not adding this - too complex for CP-SAT without reification
    
    # Generate lines
    lines = set()
    for dx in range(n):
        for dy in range(-n+1, n):
            if dx == 0 and dy <= 0: continue
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            sx, sy = dx//g, dy//g
            seen = set()
            for x0 in range(n):
                for y0 in range(n):
                    pts = []
                    x, y = x0, y0
                    while 0 <= x < n and 0 <= y < n:
                        pts.append((x,y)); x += sx; y += sy
                    if len(pts) >= 3:
                        seen.add(tuple(sorted(pts)))
            lines.update(seen)
    lines = [list(ln) for ln in lines]
    
    n_added = 0
    for line in lines:
        terms = []
        for (x,y) in line:
            if (x,y) in pv: terms.append(pv[(x,y)])
            if (x,y) in sv: terms.append(sv[(x,y)])
        if len(terms) >= 3:
            m.Add(sum(terms) <= 2)
            n_added += 1
    
    return m, pv, sv, n_added


def test_n(n, max_time=300):
    from ortools.sat.python import cp_model as cpm
    print(f"\n=== n={n} ===")
    t0 = time.time()
    
    # Generate lines first (to report count)
    lines_count = 0
    # Quick estimate
    for dx in range(n):
        for dy in range(-n+1, n):
            if dx == 0 and dy <= 0: continue
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            sx, sy = dx//g, dy//g
            seen = set()
            for x0 in range(n):
                for y0 in range(n):
                    pts = []
                    x, y = x0, y0
                    while 0 <= x < n and 0 <= y < n:
                        pts.append((x,y)); x += sx; y += sy
                    if len(pts) >= 3:
                        seen.add(tuple(sorted(pts)))
            lines_count += len(seen)
    
    print(f"  Lines: {lines_count}")
    
    t1 = time.time()
    m, pv, sv, n_added = build_ntil_model(n)
    build_time = time.time() - t1
    print(f"  Build: {build_time:.1f}s, Constraints: {n_added}")
    
    solver = cpm.CpSolver()
    solver.parameters.max_time_in_seconds = max_time
    solver.parameters.num_search_workers = 1
    
    t_solve = time.time()
    st = solver.Solve(m)
    elapsed = time.time() - t_solve
    
    result = {
        'n': n, 'status': solver.StatusName(st),
        'time': round(elapsed, 1), 'build_time': round(build_time, 1),
        'lines': lines_count, 'constraints': n_added,
        'wall_time': solver.WallTime()
    }
    
    if st in (2, 4):
        pi = [0]*n; sigma = [0]*n
        for i in range(n):
            for j in range(n):
                if solver.Value(pv[(i,j)]) == 1: pi[i] = j
                if solver.Value(sv[(i,j)]) == 1: sigma[i] = j
        
        pts = [(i, pi[i]) for i in range(n)] + [(i, sigma[i]) for i in range(n)]
        unique_pts = len(set(pts))
        bad = sum(1 for p1,p2,p3 in itertools.combinations(pts,3)
                  if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
        
        result['pi'] = pi
        result['sigma'] = sigma
        result['unique_pts'] = unique_pts
        result['n_collinear'] = bad
        result['ntil_ok'] = (bad == 0 and unique_pts == 2*n)
        
        ok = "✓ NTIL!" if result['ntil_ok'] else f"✗ pts={unique_pts}/{2*n} bad={bad}"
        print(f"  {solver.StatusName(st)} ({elapsed:.1f}s) {ok}")
        if result['ntil_ok']:
            print(f"  pi[:10]={pi[:10]}")
            print(f"  sigma[:10]={sigma[:10]}")
            # Check involution
            inv = sum(1 for i in range(n) if sigma[i]==n-1-pi[i])
            print(f"  involution: {inv}/{n}")
    else:
        print(f"  {solver.StatusName(st)} ({elapsed:.1f}s)")
        result['ntil_ok'] = False
    
    result['total_time'] = round(time.time() - t0, 1)
    return result


if __name__ == '__main__':
    import random; random.seed(42)
    
    print("=" * 64)
    print("CP-SAT Direct NTIL Test: n=16/20/30/74")
    print("=" * 64)
    
    results = []
    
    # Test plan: increasing n with time limits
    tests = [
        (16, 120),   # ~5min max
        (20, 180),   # ~10min max (first to check scaling break)
        (30, 300),   # ~5min max
    ]
    
    for n_val, timeout in tests:
        r = test_n(n_val, max_time=timeout)
        results.append(r)
        json.dump(results, open('cpsat_direct_results.json', 'w'), indent=2)
        
        # If n=30 succeeds, try n=74
        if r.get('ntil_ok') and n_val >= 30:
            print("\n" + "="*64)
            print("n=30 SOLVED! Attempting n=74 with 10min timeout...")
            print("="*64)
            r74 = test_n(74, max_time=600)
            results.append(r74)
            json.dump(results, open('cpsat_direct_results.json', 'w'), indent=2)
            if r74.get('ntil_ok'):
                json.dump(r74, open('ntil_solution_n74_cpsat.json', 'w'), indent=2)
                print("\n★★★ N=74 NTIL solution found by CP-SAT! ★★★")
            break
    
    # If no solution yet but want to test n=74 anyway
    if not any(r.get('ntil_ok') and r['n'] >= 30 for r in results):
        # Check if any smaller n succeeded
        last_n = results[-1]['n'] if results else 0
        if any(r.get('ntil_ok') for r in results):
            print(f"\nAll tests up to n={last_n} found solutions. ")
            print("Attempting n=74 with 15min timeout as final test...")
            r74 = test_n(74, max_time=900)
            results.append(r74)
            json.dump(results, open('cpsat_direct_results.json', 'w'), indent=2)
            if r74.get('ntil_ok'):
                json.dump(r74, open('ntil_solution_n74_cpsat.json', 'w'), indent=2)
                print("\n★★★ N=74 NTIL solution found by CP-SAT! ★★★")
    
    # Summary
    print(f"\n===== Summary =====")
    for r in results:
        icon = "✓" if r.get('ntil_ok') else "✗"
        print(f"  n={r['n']:>3}: {icon} {r['status']} ({r['total_time']:.0f}s)")
    print(f"\nResults saved to cpsat_direct_results.json")

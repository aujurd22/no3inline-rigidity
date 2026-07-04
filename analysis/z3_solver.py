#!/usr/bin/env python3
"""
方向三：Z3 SMT 求解 No-Three-In-Line 缺失中心问题

用 Z3 求解器替代 PySAT（kissat segfaults）。
编码方案相同：变量 + 行列约束 + 共线约束 + 距离环约束。
"""
import sys, math
from collections import defaultdict
from itertools import combinations

try:
    from z3 import *
    HAVE_Z3 = True
except ImportError:
    HAVE_Z3 = False
    print("Z3 not installed. Run: pip install z3-solver")

def solve(n, missing_center=True, timeout_ms=300000):
    if not HAVE_Z3:
        return None
    
    print(f"Z3 Solver: n={n}, missing_center={missing_center}, timeout={timeout_ms}ms")
    print()
    
    # Create solver
    solver = Solver()
    solver.set("timeout", timeout_ms)
    
    # Variables: x[r][c] ∈ {0, 1}
    x = [[Bool(f"x_{r}_{c}") for c in range(n)] for r in range(n)]
    
    # Convert to 0/1 integers for cardinality constraints
    x_int = [[If(x[r][c], 1, 0) for c in range(n)] for r in range(n)]
    
    print(f"  Variables: {n}×{n} = {n*n}")
    
    # Exactly 2 per row
    for r in range(n):
        solver.add(sum(x_int[r][c] for c in range(n)) == 2)
    
    # Exactly 2 per column
    for c in range(n):
        solver.add(sum(x_int[r][c] for r in range(n)) == 2)
    
    print(f"  Row/col constraints: {2*n}")
    
    # Collinearity: at most 2 per collinear triple
    cx2 = cy2 = n - 1
    coll_count = 0
    for r1 in range(n):
        for c1 in range(n):
            for r2 in range(r1, n):
                for c2 in range(n):
                    if r1 == r2 and c1 >= c2: continue
                    for r3 in range(r2, n):
                        for c3 in range(n):
                            if r3 == r2 and c3 <= c2: continue
                            if r3 == r1 and c3 <= c1: continue
                            
                            area = (c2-c1)*(r3-r1) - (c3-c1)*(r2-r1)
                            if area != 0: continue
                            # Skip same row/col (already constrained)
                            if r1 == r2 == r3: continue
                            if c1 == c2 == c3: continue
                            
                            solver.add(Not(And(x[r1][c1], x[r2][c2], x[r3][c3])))
                            coll_count += 1
    
    print(f"  Collinearity constraints: {coll_count}")
    
    # Ring constraint: at most 2 per distance ring
    ring_count = 0
    if missing_center:
        rings = defaultdict(list)
        for r in range(n):
            for c in range(n):
                d = (2*c - cx2)**2 + (2*r - cy2)**2
                rings[d].append((r, c))
        
        for d, pts in rings.items():
            if len(pts) >= 3:
                for (r1,c1),(r2,c2),(r3,c3) in combinations(pts, 3):
                    area = (c2-c1)*(r3-r1) - (c3-c1)*(r2-r1)
                    if area != 0:
                        solver.add(Not(And(x[r1][c1], x[r2][c2], x[r3][c3])))
                        ring_count += 1
        
        print(f"  Ring constraints: {ring_count}")
    
    print(f"  Total constraints: {coll_count + ring_count + 2*n}")
    print()
    print(f"Solving...")
    
    result = solver.check()
    
    if result == sat:
        model = solver.model()
        
        solution = []
        for r in range(n):
            for c in range(n):
                if is_true(model.eval(x[r][c])):
                    solution.append((c, r))
        
        from collections import Counter
        dc = Counter()
        for x_c, y in solution:
            d = (2*x_c - cx2)**2 + (2*y - cy2)**2
            dc[d] += 1
        max_r = max(dc.values())
        
        print(f"  ✅ SATISFIABLE: {len(solution)} points, max_ring={max_r}")
        tag = "✅ Missing center!" if max_r <= 2 else "Has center"
        print(f"    {tag}")
        
        print(f"\n  Solution (row → cols):")
        by_row = defaultdict(list)
        for x_c, y in solution:
            by_row[y].append(x_c)
        for r in range(n):
            cs = sorted(by_row.get(r, []))
            if cs:
                d1 = (2*cs[0]-cx2)**2 + (2*r-cy2)**2
                d2 = (2*cs[1]-cx2)**2 + (2*r-cy2)**2
                print(f"    Row {r:2d}: {cs}  d=({d1},{d2})")
        
        print(f"\n  Ring distribution:")
        for d, cnt in sorted(dc.items()):
            print(f"    d={d:4d}: {cnt} pt(s)")
        
        return solution, model
    elif result == unsat:
        print(f"  ❌ UNSATISFIABLE")
        return None, None
    else:
        print(f"  ? Unknown: {result}")
        return None, None


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    mc = len(sys.argv) <= 2 or sys.argv[2].lower() != 'false'
    t = int(sys.argv[3]) if len(sys.argv) > 3 else 300000
    
    solve(n, mc, t)

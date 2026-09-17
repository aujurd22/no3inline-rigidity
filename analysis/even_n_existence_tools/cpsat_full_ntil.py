"""CP-SAT full 74x74 NTIL model with double-permutation decomposition.
Variables: pi[i][j] and sigma[i][j] (binary, is pi(i)=j / sigma(i)=j).
This reduces from n^2 to 2n^2 variables (still large but structured).
"""
import sys, itertools, math, time
from collections import defaultdict
sys.path.insert(0, '.')
from ortools.sat.python import cp_model

def build_model(n):
    """Build CP-SAT model for n×n NTIL with double-permutation encoding."""
    model = cp_model.CpModel()
    
    # Variables: pi_vars[i][j] = 1 iff pi(i) = j
    pi_vars = {}
    sigma_vars = {}
    for i in range(n):
        for j in range(n):
            pi_vars[(i, j)] = model.NewBoolVar(f"pi_{i}_{j}")
            sigma_vars[(i, j)] = model.NewBoolVar(f"sigma_{i}_{j}")
    
    # Permutation constraints: exactly one j per i, exactly one i per j
    for i in range(n):
        model.AddExactlyOne([pi_vars[(i, j)] for j in range(n)])
        model.AddExactlyOne([sigma_vars[(i, j)] for j in range(n)])
    for j in range(n):
        model.AddExactlyOne([pi_vars[(i, j)] for i in range(n)])
        model.AddExactlyOne([sigma_vars[(i, j)] for i in range(n)])
    
    # No-collinearity: for any 3 points (chosen from the 2n points),
    # enforce that they are not collinear.
    # Since we have 2n points, we need to encode "point k is (i, pi(i)) or (i, sigma(i))"
    # This is complex — instead, we can use the 3-CNF encoding:
    # For each triple of points, if they'd be collinear, forbid the triple.
    
    # Simpler: precompute all lines and add constraints
    lines = set()
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy == 0:
                continue
            g = math.gcd(abs(dx), abs(dy))
            if g > 1:
                continue  # primitive direction only
            sx, sy = dx // g, dy // g
            # Scan all starting points
            for x0 in range(n):
                for y0 in range(n):
                    pts = []
                    x, y = x0, y0
                    while 0 <= x < n and 0 <= y < n:
                        pts.append((x, y))
                        x += sx
                        y += sy
                    if len(pts) >= 3:
                        lines.add(tuple(sorted(pts)))
    
    print(f"n={n}: {len(lines)} lines with ≥3 points")
    
    # For each line, at most 2 of its points can be selected.
    # Each point (i,j) is selected if pi(i)=j OR sigma(i)=j.
    # That is: selected[i][j] = pi_vars[i][j] OR sigma_vars[i][j]
    # → at most 2 per line: sum_{p in line} selected[p] ≤ 2
    
    # But CP-SAT AddMaxEquality for OR is expensive. Use reification:
    # selected[i][j] >= pi_vars[i][j], selected[i][j] >= sigma_vars[i][j]
    # selected[i][j] <= pi_vars[i][j] + sigma_vars[i][j]
    
    selected = {}
    for i in range(n):
        for j in range(n):
            s = model.NewBoolVar(f"sel_{i}_{j}")
            model.Add(s >= pi_vars[(i, j)])
            model.Add(s >= sigma_vars[(i, j)])
            model.Add(s <= pi_vars[(i, j)].__add__(sigma_vars[(i, j)]))
            selected[(i, j)] = s
    
    for line in lines:
        model.Add(sum(selected[p] for p in line) <= 2)
    
    return model, lines, selected, pi_vars, sigma_vars


if __name__ == "__main__":
    for n in [10, 12, 14]:
        print(f"\n=== n={n} ===")
        model, lines, selected, pi_vars, sigma_vars = build_model(n)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 120
        solver.parameters.num_search_workers = 1
        t0 = time.time()
        st = solver.Solve(model)
        elapsed = time.time() - t0
        print(f"Status: {solver.StatusName(st)} ({elapsed:.1f}s)")
        
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            pi_sol = [0] * n
            sigma_sol = [0] * n
            for i in range(n):
                for j in range(n):
                    if solver.Value(pi_vars[(i, j)]) == 1:
                        pi_sol[i] = j
                    if solver.Value(sigma_vars[(i, j)]) == 1:
                        sigma_sol[i] = j
            print(f"pi = {pi_sol}")
            print(f"sigma = {sigma_sol}")
            pts = [(i, pi_sol[i]) for i in range(n)] + [(i, sigma_sol[i]) for i in range(n)]
            bad = sum(1 for p1, p2, p3 in itertools.combinations(pts, 3)
                     if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
            print(f"NTIL: {bad} collinear triples (0=success)")
        elif st == cp_model.INFEASIBLE:
            print(f"INFEASIBLE — no solution exists")
        else:
            print(f"UNKNOWN — {elapsed:.0f}s timeout")

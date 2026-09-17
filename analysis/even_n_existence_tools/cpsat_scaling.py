"""
CP-SAT full NTIL double-permutation model scaling test.
Tests n=10-18 sequentially, records time and result.
"""
import sys, itertools, math, time, json
sys.path.insert(0, '.')
from ortools.sat.python import cp_model


def build_model(n):
    model = cp_model.CpModel()
    pi_v, si_v = {}, {}
    for i in range(n):
        for j in range(n):
            pi_v[(i, j)] = model.NewBoolVar(f"p_{i}_{j}")
            si_v[(i, j)] = model.NewBoolVar(f"s_{i}_{j}")

    for i in range(n):
        model.AddExactlyOne([pi_v[(i, j)] for j in range(n)])
        model.AddExactlyOne([si_v[(i, j)] for j in range(n)])
    for j in range(n):
        model.AddExactlyOne([pi_v[(i, j)] for i in range(n)])
        model.AddExactlyOne([si_v[(i, j)] for i in range(n)])
    # Enforce pi(i) != sigma(i): each cell selected at most once
    for i in range(n):
        for j in range(n):
            model.Add(pi_v[(i, j)] + si_v[(i, j)] <= 1)

    # Precompute all lines
    lines = set()
    for dx in range(n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            sx, sy = dx // g, dy // g
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

    # Selected variables
    sel = {}
    for i in range(n):
        for j in range(n):
            s = model.NewBoolVar(f"sel_{i}_{j}")
            model.Add(s >= pi_v[(i, j)])
            model.Add(s >= si_v[(i, j)])
            model.Add(s <= pi_v[(i, j)] + si_v[(i, j)])
            sel[(i, j)] = s

    for line in lines:
        model.Add(sum(sel[p] for p in line) <= 2)

    return model, pi_v, si_v, sel, len(lines)


if __name__ == "__main__":
    results = []
    for n in [10, 12, 14, 16, 18]:
        print(f"\n=== n={n} ===")
        t0 = time.time()
        model, pi_v, si_v, sel, n_lines = build_model(n)
        build_t = time.time() - t0
        print(f"  build: {build_t:.1f}s, {n_lines} lines")

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 120
        solver.parameters.num_search_workers = 1
        t0 = time.time()
        st = solver.Solve(model)
        solve_t = time.time() - t0

        status = solver.StatusName(st)
        print(f"  status: {status} ({solve_t:.1f}s)")

        r = {"n": n, "n_lines": n_lines, "build_s": build_t,
             "solve_s": solve_t, "status": status}
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            pi_s = [0] * n
            si_s = [0] * n
            for i in range(n):
                for j in range(n):
                    if solver.Value(pi_v[(i, j)]) == 1:
                        pi_s[i] = j
                    if solver.Value(si_v[(i, j)]) == 1:
                        si_s[i] = j
            pts = [(i, pi_s[i]) for i in range(n)] + [(i, si_s[i]) for i in range(n)]
            bad = sum(1 for p1, p2, p3 in itertools.combinations(pts, 3)
                     if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
            r["pi"] = pi_s
            r["sigma"] = si_s
            r["collinear"] = bad
            print(f"  NTIL: {bad} collinear (0=success)")
        results.append(r)

    json.dump(results, open("cpsat_scaling_results.json", "w"), indent=2)
    print("\n=== Summary ===")
    for r in results:
        print(f"  n={r['n']}: {r['status']} ({r['solve_s']:.1f}s) lines={r['n_lines']}")

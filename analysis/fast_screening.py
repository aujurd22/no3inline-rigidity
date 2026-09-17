"""
fast_screening.py — 大容量 2-因子快速粗筛

用 orientation=0（全零取向）作为代理指标：
- 只检查 orientation=0 时的 collinear triples（1/8 工作量）
- 找出子句数最低的 N 个候选
- 再用完整 CP-SAT 验证

速度：~0.3s/配置（vs 18s for full enumerate_clauses）
"""
import json, sys, time, random
from collections import Counter
from itertools import combinations

M = 37
N = 2 * M

# ── Precompute C4 orbits ──────────────────────────────────────────────────
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_orbits_0 = {}  # orientation 0 only
for u in range(M):
    for v in range(M):
        all_orbits_0[(u, v)] = c4_lift(u, v)

def check_12_fast(lifts):
    """Fast check if any 3 of 12 points are collinear."""
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i + 1, 12):
            xj, yj = lifts[j]
            if xi == xj and yi == yj:
                continue
            dx1, dy1 = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi:
                    continue
                if dx1 * (yk - yi) == dy1 * (xk - xi):
                    return True
    return False

def zero_orient_clause_count(edges):
    """Count 'bad orientation combos' when all cells use orientation 0.
    Actually, with orientation fixed, we just check if 3 of 12 lifts are collinear.
    This is a proxy for the full clause count."""
    total = 0
    for a, b, c in combinations(range(M), 3):
        u1, v1 = edges[a]
        u2, v2 = edges[b]
        u3, v3 = edges[c]
        lifts = (all_orbits_0[(u1, v1)] +
                 all_orbits_0[(u2, v2)] +
                 all_orbits_0[(u3, v3)])
        if check_12_fast(lifts):
            total += 1
    return total

# ── Generate [28,9] 2-factors ──────────────────────────────────────────────
def generate_hyphen(m, rng, cycle_lengths):
    """Generate a random 2-factor with given cycle lengths."""
    vertices = list(range(m))
    rng.shuffle(vertices)
    edges = []
    pos = 0
    for clen in cycle_lengths:
        for k in range(clen):
            u = vertices[pos + k]
            v = vertices[pos + (k + 1) % clen]
            edges.append((min(u, v), max(u, v)))
        pos += clen
    # Verify
    assert len(edges) == m
    assert len(set(edges)) == m
    deg = Counter([v for e in edges for v in e])
    assert all(d == 2 for d in deg.values())
    return edges

# ── Load config_408 for validation ─────────────────────────────────────────
print("=== FAST SCREENING ===")
print(f"Loading config_408 for baseline...")

with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\config_408_edges.json") as f:
    data = json.load(f)
ref_edges = [tuple(e) for e in data["edges"]]

t0 = time.time()
ref_zero = zero_orient_clause_count(ref_edges)
t1 = time.time()
print(f"  config_408 zero-orient clauses: {ref_zero} ({t1-t0:.3f}s)")

# ── Generate and score candidates ──────────────────────────────────────────
rng = random.Random(12345)
cycle_types = [
    [28, 9],  # config_408 type
    [29, 8],  # close variant
    [27, 10],
    [26, 11],
    [30, 7],
    [25, 12],
    [24, 13],
    [31, 6],
    [23, 14],
    [22, 15],
    [21, 16],
    [19, 18],
    [15, 12, 10],
    [14, 13, 10],
    [13, 12, 12],
    [37],      # Hamiltonian
]

N_PER_TYPE = 200
# Actually, focus most on [28,9] and close variants
focus_types = {
    (28, 9): 800,
    (29, 8): 400,
    (27, 10): 200,
    (26, 11): 200,
    (30, 7): 200,
    (25, 12): 200,
    (24, 13): 200,
    (31, 6): 200,
    (37,): 200,
    (22, 15): 100,
    (21, 16): 100,
    (19, 18): 100,
    (15, 12, 10): 100,
    (14, 13, 10): 100,
    (13, 12, 12): 100,
}

all_candidates = []
total_generated = 0
t_start = time.time()

for cyc, n_req in focus_types.items():
    cyc_list = list(cyc)
    for i in range(n_req):
        edges = generate_hyphen(M, rng, cyc_list)
        proxy = zero_orient_clause_count(edges)
        all_candidates.append((proxy, cyc_list, edges))
        total_generated += 1
        
        if total_generated % 200 == 0:
            elapsed = time.time() - t_start
            rate = total_generated / elapsed
            print(f"  [{total_generated}] rate={rate:.1f}/s, "
                  f"best so far: {min(c[0] for c in all_candidates)}", 
                  flush=True)

total_time = time.time() - t_start
print(f"\n=== Generated {total_generated} configs in {total_time:.0f}s ===")

# Sort by proxy
all_candidates.sort(key=lambda x: x[0])

print(f"\nTop 20 by zero-orient proxy:")
for i in range(min(20, len(all_candidates))):
    proxy, cyc, _ = all_candidates[i]
    print(f"  {i+1:2d}. proxy={proxy:4d}, type={cyc}")

# Pick top 5 for full CP-SAT verification
print(f"\n=== Running CP-SAT on top 5 ===")
from ortools.sat.python import cp_model
from solver_2factor_sat_pipeline import enumerate_clauses

best_overall = None
for i in range(min(5, len(all_candidates))):
    proxy, cyc, edges = all_candidates[i]
    
    # Full clause enumeration
    clause_list, _ = enumerate_clauses(M, edges, verbose=False)
    n_cl = len(clause_list)
    
    print(f"\n  Candidate {i+1}: type={cyc}, proxy={proxy}, full_clauses={n_cl}", flush=True)
    
    if n_cl > 420:
        print(f"    Skipping (clauses > 420, likely >= 16 violations)")
        continue
    
    # CP-SAT
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(M)]
    violation_vars = []
    for idx, (a, b, c, bits) in enumerate(clause_list):
        b1, b2, b3 = (bits >> 0) & 1, (bits >> 1) & 1, (bits >> 2) & 1
        lit_a = x[a] if b1 else x[a].Not()
        lit_b = x[b] if b2 else x[b].Not()
        lit_c = x[c] if b3 else x[c].Not()
        v = model.NewBoolVar(f"v{idx}")
        model.AddBoolAnd([lit_a, lit_b, lit_c]).OnlyEnforceIf(v)
        model.AddBoolOr([lit_a.Not(), lit_b.Not(), lit_c.Not()]).OnlyEnforceIf(v.Not())
        violation_vars.append(v)
    model.Minimize(sum(violation_vars))
    
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    solver.parameters.max_time_in_seconds = 30
    
    t1 = time.time()
    status = solver.Solve(model)
    t = time.time() - t1
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        min_v = int(solver.ObjectiveValue())
        optimal = (status == cp_model.OPTIMAL)
        opt_s = "✅" if optimal else "⏳"
        print(f"    → {min_v} violations {opt_s} ({t:.1f}s)", flush=True)
        
        if best_overall is None or min_v < best_overall[1]:
            best_overall = (edges, min_v, n_cl, optimal, cyc)
        
        if min_v < 16:
            print(f"      ★★★ BELOW 16! ★★★", flush=True)
            result_data = {
                "m": M, "edges": [list(e) for e in edges],
                "min_violations": min_v, "n_clauses": n_cl,
                "proven_optimal": optimal, "cycle_type": cyc,
            }
            with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\screening_breakthrough.json", "w") as f:
                json.dump(result_data, f, indent=1)
    else:
        print(f"    → timeout ({t:.1f}s)", flush=True)

# Summary
print(f"\n{'='*60}")
print(f"SCREENING SUMMARY")
print(f"{'='*60}")
if best_overall:
    edges, min_v, n_cl, optimal, cyc = best_overall
    print(f"  Best: type={cyc}, {n_cl} clauses, {min_v} violations")
    if min_v < 16:
        print(f"  ★★★ BREAKTHROUGH: {min_v} < 16! ★★★")
    elif min_v == 16:
        print(f"  Matches config_408 at 16 violations (but {n_cl} clauses)")
    else:
        print(f"  Worse than config_408 ({min_v} > 16)")
else:
    print(f"  No configs found with <420 clauses")

total = time.time() - t_start
print(f"  Total time: {total:.0f}s")

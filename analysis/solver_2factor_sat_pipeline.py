"""
solver_2factor_sat_pipeline.py — Core pipeline: generate 2-factor → build 3-CNF clause set → SAT check.

Strategy:
  - Generate 2-factors (ALLOW 2-cycles, unlike the old simple-graph-only model).
  - For each, enumerate all C(37,3)=7,770 edge-triples × 8 orientation combos.
  - For each combo, check if any 3 of 12 C4 lifts are collinear → clause.
  - Feed the clause set to CP-SAT: SAT → decode → verify_total(); UNSAT → record min violations.
  - Build a predictor of clause-count from 2-factor topology.

Usage:
  python solver_2factor_sat_pipeline.py --m 37 --trials 1000 --out results/pipeline_scan.json
  python solver_2factor_sat_pipeline.py --m 37 --check-edge results/ known_2factor.json
"""
import sys, os, json, time, math, random, argparse, pickle
from collections import defaultdict
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ── line_of ──────────────────────────────────────────────────────────────────
def line_of(p, q):
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    if dx == 0 and dy == 0:
        return (0, 0, 0)
    g = math.gcd(abs(dx), abs(dy))
    A = dy // g
    B = -dx // g
    if A < 0 or (A == 0 and B < 0):
        A = -A
        B = -B
    L = A * p[0] + B * p[1]
    return (A, B, L)


# ── 2-factor generation (allow 2-cycles) ─────────────────────────────────────
def generate_2factor_full(m, rng, seed_edges=None, allow_twocycles=True):
    """
    Generate a simple 2-regular graph on {0..m-1}.
    If allow_twocycles=True, 2-cycles (a,b)+(b,a) are ALLOWED as a single edge
    plus the reverse — but in our model edges are {u,v} with u≤v, so a 2-cycle
    is just two copies of the same unordered pair. We handle this at the clause
    level, not the graph level.
    
    Returns: list of (u,v) with u≤v, length m, each vertex degree 2.
    """
    if seed_edges:
        # Use seed edges and complete the 2-factor
        edges = list(seed_edges)
        deg = [0] * m
        for u, v in edges:
            deg[u] += 1
            deg[v] += 1 if u != v else 0
        # find vertices with degree < 2
        deficit = [i for i in range(m) if deg[i] < 2]
        rng.shuffle(deficit)
        # pair up remaining deficits
        while deficit:
            i = deficit.pop()
            if deg[i] >= 2:
                continue
            # find a partner
            candidates = [j for j in deficit if j != i and deg[j] < 2]
            if not candidates:
                # try to close with a degree-0 vertex
                zero = [j for j in range(m) if deg[j] == 0 and j != i]
                candidates = zero
            if not candidates:
                raise ValueError("Cannot complete 2-factor from seed edges")
            j = rng.choice(candidates)
            deficit.remove(j) if j in deficit else None
            u, v = (i, j) if i <= j else (j, i)
            edges.append((u, v))
            deg[u] += 1
            deg[v] += 1 if u != v else 0
        return sorted(edges)
    else:
        # Random 2-factor: generate a random permutation and take its cycles
        perm = list(range(m))
        rng.shuffle(perm)
        visited = [False] * m
        edges = []
        for i in range(m):
            if not visited[i]:
                cycle = []
                j = i
                while not visited[j]:
                    visited[j] = True
                    cycle.append(j)
                    j = perm[j]
                # Turn cycle into edges
                for k in range(len(cycle)):
                    a, b = cycle[k], cycle[(k + 1) % len(cycle)]
                    u, v = (a, b) if a <= b else (b, a)
                    edges.append((u, v))
        return sorted(edges)


# ── Build 3-CNF clauses ─────────────────────────────────────────────────────
def enumerate_clauses(m, edges, n=None, verbose=True):
    """
    For a fixed 2-factor (37 edges), enumerate all C(37,3) edge-triples × 8 orientation combos.
    Return: clause_list = [(e1,e2,e3, bits)], meaning t_e1=bit0, t_e2=bit1, t_e3=bit2 is FORBIDDEN.
            clause_map = { (e1,e2,e3): [list of 8 bool results] }
    Also compute the 4 lift coordinates for each cell orientation.
    """
    if n is None:
        n = 2 * m
    t0 = time.time()
    
    # Precompute cell → 4 lifts for each orientation
    # Cell (u,v): oriented as (u,v) → lifts; as (v,u) → 4 different lifts
    cell_lifts = {}  # (u,v,orient) → [(x,y), ...]  4 C4 rotations
    
    def c4_lift(x, y):
        """4 C4 rotations of point (x,y) on even n=2m grid."""
        pts = [(x, y)]
        for _ in range(3):
            x, y = n - 1 - y, x
            pts.append((x, y))
        return pts
    
    for idx, (u, v) in enumerate(edges):
        # Orientation 0: cell = (u,v)
        pts0 = c4_lift(u, v)
        cell_lifts[(idx, 0)] = pts0
        if u != v:
            # Orientation 1: cell = (v,u)
            pts1 = c4_lift(v, u)
            cell_lifts[(idx, 1)] = pts1
        else:
            # Loop edge: orientation irrelevant, only 4 lifts
            cell_lifts[(idx, 1)] = pts0
    
    # Enumerate all triples
    E = len(edges)
    clauses = []
    clause_map = {}
    checked = 0
    forbidden = 0
    
    for a in range(E):
        for b in range(a + 1, E):
            for c in range(b + 1, E):
                triple = (a, b, c)
                results = []
                for bits in range(8):
                    t1 = (bits >> 0) & 1
                    t2 = (bits >> 1) & 1
                    t3 = (bits >> 2) & 1
                    # Collect all 12 lifts
                    lifts = cell_lifts[(a, t1)] + cell_lifts[(b, t2)] + cell_lifts[(c, t3)]
                    # Check collinearity
                    bad = False
                    for i in range(12):
                        if bad:
                            break
                        pi = lifts[i]
                        for j in range(i + 1, 12):
                            pj = lifts[j]
                            if pi[0] == pj[0] and pi[1] == pj[1]:
                                continue
                            k0 = line_of(pi, pj)
                            cnt = 2
                            for k in range(12):
                                if k == i or k == j:
                                    continue
                                pk = lifts[k]
                                if pk[0] == pi[0] and pk[1] == pi[1]:
                                    continue
                                kk = line_of(pi, pk)
                                if kk == k0:
                                    cnt += 1
                                    if cnt >= 3:
                                        bad = True
                                        break
                    results.append(bad)
                    if bad:
                        forbidden += 1
                clause_map[triple] = results
                # If any combo is forbidden, add a 3-CNF clause blocking that specific assignment
                for bits, bad in enumerate(results):
                    if bad:
                        clauses.append((a, b, c, bits))
                checked += 1
    
    t1 = time.time()
    if verbose:
        n_clauses = len(clauses)
        total_checked = checked * 8
        pct = 100.0 * n_clauses / max(total_checked, 1)
        print(f"  enumerated {checked} triples × 8 = {total_checked} checks"
              f" → {n_clauses} clauses ({pct:.2f}%) in {t1-t0:.1f}s", flush=True)
    
    return clauses, clause_map


# ── CP-SAT SAT/MaxSAT check ─────────────────────────────────────────────────
def check_sat(m, edges, clauses, time_limit=60, verbose=True):
    """
    Use CP-SAT to check if the clauses are SAT (all hard) or MaxSAT (minimize violated).
    Returns dict with status, min_violations, orientation bits.
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        # Fallback: use CP-SAT from envs/default
        sys.path.insert(0, os.path.expandvars("$USERPROFILE/.workbuddy/binaries/python/envs/default/Lib/site-packages"))
        from ortools.sat.python import cp_model
    
    model = cp_model.CpModel()
    t = [model.NewBoolVar(f"t_{i}") for i in range(m)]
    
    # For each clause: (a,b,c,bits) = forbid this specific assignment
    # Add a clause: NOT(t_a=bit0 AND t_b=bit1 AND t_c=bit2)
    # = New clause: (t_a != bit0) OR (t_b != bit1) OR (t_c != bit2)
    for a, b, c, bits in clauses:
        b0 = (bits >> 0) & 1
        b1 = (bits >> 1) & 1
        b2 = (bits >> 2) & 1
        # t_a should NOT be b0 → require t_a == (1-b0)
        lit0 = t[a] if b0 == 0 else t[a].Not()
        lit1 = t[b] if b1 == 0 else t[b].Not()
        lit2 = t[c] if b2 == 0 else t[c].Not()
        model.AddBoolOr(lit0, lit1, lit2)
    
    # Phase 1: pure SAT
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    
    start = time.time()
    status = solver.Solve(model)
    sat_time = time.time() - start
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        sol_bits = [int(solver.Value(t[i])) for i in range(m)]
        return {
            "sat_attempt_time_s": round(sat_time, 3),
            "sat_status": "SAT" if status == cp_model.OPTIMAL else "FEASIBLE",
            "sat_found": True,
            "orientation": sol_bits,
        }
    
    # Phase 2: MaxSAT (find minimal violations)
    # Rebuild with relaxed clauses
    model2 = cp_model.CpModel()
    t2 = [model2.NewBoolVar(f"t_{i}") for i in range(m)]
    viol = [model2.NewBoolVar(f"v_{i}") for i in range(len(clauses))]
    
    for ci, (a, b, c, bits) in enumerate(clauses):
        b0 = (bits >> 0) & 1
        b1 = (bits >> 1) & 1
        b2 = (bits >> 2) & 1
        # violated = NOT(t_a=1-b0 AND t_b=1-b1 AND t_c=1-b2)
        lit0 = t2[a] if b0 == 0 else t2[a].Not()
        lit1 = t2[b] if b1 == 0 else t2[b].Not()
        lit2 = t2[c] if b2 == 0 else t2[c].Not()
        # If viol==0 then (lit0 AND lit1 AND lit2)
        # If viol==1 then the clause is relaxed
        model2.AddBoolOr(lit0, lit1, lit2, viol[ci])
    
    model2.Minimize(sum(viol))
    
    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = time_limit
    solver2.parameters.num_search_workers = 1
    
    start2 = time.time()
    status2 = solver2.Solve(model2)
    maxsat_time = time.time() - start2
    
    orientation = [int(solver2.Value(t2[i])) for i in range(m)]
    n_violated = sum(int(solver2.Value(v)) for v in viol)
    
    result = {
        "sat_attempt_time_s": round(sat_time, 3),
        "sat_status": "UNSAT",
        "sat_found": False,
        "maxsat_attempt_time_s": round(maxsat_time, 3),
        "maxsat_status": ("OPTIMAL" if status2 == cp_model.OPTIMAL
                          else "FEASIBLE" if status2 == cp_model.FEASIBLE
                          else "UNKNOWN"),
        "maxsat_min_violations": n_violated,
        "maxsat_n_violated": n_violated,
        "maxsat_proven_optimal": status2 == cp_model.OPTIMAL,
        "orientation": orientation,
        "maxsat_solution": orientation,
    }
    
    # Decode cells from orientation bits
    cells = []
    for idx, (u, v) in enumerate(edges):
        if u == v:
            cells.append((u, u))
        elif orientation[idx] == 0:
            cells.append((u, v))
        else:
            cells.append((v, u))
    result["cells"] = cells
    
    return result


# ── Verify with Board ────────────────────────────────────────────────────────
def verify_config(m, edges, cells):
    """Use solver_theory_m37.Board to verify total_bad and legality."""
    try:
        sys.path.insert(0, HERE)
        import solver_theory_m37 as S
        board = S.Board(m)
        board.build(edges, cells)
        tb = board.verify_total()
        legal = all(board.rowSum[i] + board.colSum[i] == 2 for i in range(m))
        degree_ok = all(sum(1 for (a, b) in edges if a == i or b == i) == 2 for i in range(m))
        return {"total_bad": tb, "legal_2factor": legal, "degree_ok": degree_ok, "n_lifts": len(board.lifts)}
    except Exception as e:
        return {"error": str(e)}


# ── Multi-run scan ───────────────────────────────────────────────────────────
def scan_2factors(m, n_trials, time_limit_per=60, allow_twocycles=True,
                  seed=42, out=None, verbose=True):
    rng = random.Random(seed)
    results = []
    best_clauses = float("inf")
    best_min_viol = float("inf")
    
    for trial in range(n_trials):
        if verbose:
            print(f"\n--- Trial {trial+1}/{n_trials} ---", flush=True)
        
        edges = generate_2factor_full(m, rng, allow_twocycles=allow_twocycles)
        
        # Check 2-cycles
        edge_set = {}
        has_twocycle = False
        for u, v in edges:
            key = (u, v)
            edge_set[key] = edge_set.get(key, 0) + 1
            if edge_set[key] >= 2:
                has_twocycle = True
        n_twocycles = sum(1 for v in edge_set.values() if v >= 2)
        
        if verbose:
            print(f"  edges generated, has_2cycle={has_twocycle} n_2cycles={n_twocycles}", flush=True)
        
        clauses, _ = enumerate_clauses(m, edges, verbose=verbose)
        n_clauses = len(clauses)
        
        if n_clauses < best_clauses:
            best_clauses = n_clauses
            if verbose:
                print(f"  ** new best clause count: {n_clauses} **", flush=True)
        
        if n_clauses == 0:
            # No clauses → any orientation works! This is a breakthrough
            res = {
                "trial": trial, "n_clauses": 0, "sat_status": "TRIVIAL_SAT",
                "min_violations": 0, "has_twocycle": has_twocycle,
                "n_twocycles": n_twocycles,
                "time_s": 0
            }
        else:
            sat_result = check_sat(m, edges, clauses, time_limit=time_limit_per, verbose=False)
            
            min_viol = sat_result.get("maxsat_min_violations",
                                       sat_result.get("min_violations", -1))
            
            if min_viol >= 0 and min_viol < best_min_viol:
                best_min_viol = min_viol
                if verbose:
                    print(f"  ** new best min_violations: {min_viol} (clauses={n_clauses}) **", flush=True)
            
            res = {
                "trial": trial,
                "n_clauses": n_clauses,
                "sat_status": sat_result.get("sat_status", "?"),
                "maxsat_status": sat_result.get("maxsat_status", "?"),
                "proven_optimal": sat_result.get("maxsat_proven_optimal", False),
                "min_violations": min_viol,
                "has_twocycle": has_twocycle,
                "n_twocycles": n_twocycles,
                "time_s": round(sat_result.get("sat_attempt_time_s", 0) +
                                sat_result.get("maxsat_attempt_time_s", 0), 3),
            }
            
            if min_viol == 0 and n_clauses > 0:
                # SAT! Decode and verify
                if verbose:
                    print(f"  *** SAT FOUND! trial {trial} ***", flush=True)
                cells = sat_result.get("cells", [])
                verify = verify_config(m, edges, cells)
                res["verify"] = verify
                res["edges"] = edges
                res["cells"] = cells
                res["found_solution"] = True
        
        results.append(res)
        
        # Save incremental
        if out and (trial + 1) % 50 == 0:
            with open(out, "w") as f:
                json.dump({"m": m, "n_trials": trial + 1, "seed": seed,
                           "best_clauses": best_clauses,
                           "best_min_viol": best_min_viol,
                           "results": results}, f, indent=2)
    
    return results


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--time-per", type=float, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results/pipeline_scan.json")
    ap.add_argument("--no-twocycles", action="store_true", help="Forbid 2-cycles")
    ap.add_argument("--check-file", help="Check a specific 2-factor from JSON file")
    args = ap.parse_args()
    
    if args.check_file:
        with open(args.check_file) as f:
            data = json.load(f)
        edges = [tuple(e) for e in data.get("edges", data.get("best_edges", []))]
        if not edges:
            # Maybe the file has the structure from solver_theory_m37_long.json
            if "cells" in data:
                # Extract edges from cells
                cells = data["cells"]
                edges = [tuple(sorted(c)) for c in cells]  # approximation
            else:
                print("ERROR: no edges found in", args.check_file)
                return
        print(f"Checking {len(edges)} edges from {args.check_file}...")
        clauses, cmap = enumerate_clauses(args.m, edges, verbose=True)
        print(f"Total clauses: {len(clauses)}")
        if len(clauses) == 0:
            print("*** NO CLAUSES → ANY ORIENTATION WORKS! ***")
        else:
            sat_res = check_sat(args.m, edges, clauses, time_limit=60, verbose=True)
            print(json.dumps(sat_res, indent=2))
        return
    
    out = os.path.join(HERE, args.out) if not os.path.isabs(args.out) else args.out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    
    scan_2factors(args.m, args.trials, time_limit_per=args.time_per,
                  allow_twocycles=not args.no_twocycles,
                  seed=args.seed, out=out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
swarm_A5_experiment.py — Deep investigation: why m=36 has rot4-NTIL but m=37 doesn't.

Steps:
1. Load m=36 solution → verify SAT, compute clauses, edge-span histogram
2. Generate m=37-like 2-factors for m=36 using the same generation strategy
3. Structural comparison: edge-span histograms
4. Parity/mod hypothesis testing
5. Report findings
"""
import os, sys, json, math, random, time, argparse
from collections import defaultdict, Counter
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.expandvars(
    "$USERPROFILE/.workbuddy/binaries/python/envs/default/Lib/site-packages"))

# ── Geometry ──────────────────────────────────────────────────────────────
def igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    if dx == 0 and dy == 0:
        return (0, 0, 0)
    g = igcd(abs(dx), abs(dy))
    A = dy // g
    B = -dx // g
    if A < 0 or (A == 0 and B < 0):
        A = -A
        B = -B
    L = A * p[0] + B * p[1]
    return (A, B, L)

def c4_lift(x, y, n):
    pts = [(x, y)]
    for _ in range(3):
        x, y = n - 1 - y, x
        pts.append((x, y))
    return pts

# ── Enumerate clauses (copied from solver_2factor_sat_pipeline.py) ──────
def enumerate_clauses(m, edges, n=None, verbose=True):
    if n is None:
        n = 2 * m
    t0 = time.time()
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        pts0 = c4_lift(u, v, n)
        cell_lifts[(idx, 0)] = pts0
        if u != v:
            pts1 = c4_lift(v, u, n)
            cell_lifts[(idx, 1)] = pts1
        else:
            cell_lifts[(idx, 1)] = pts0
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
                    lifts = cell_lifts[(a, t1)] + cell_lifts[(b, t2)] + cell_lifts[(c, t3)]
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
                for bits, bad in enumerate(results):
                    if bad:
                        clauses.append((a, b, c, bits))
                checked += 1
    t1 = time.time()
    if verbose:
        n_clauses = len(clauses)
        print(f"  enumerated {checked} triples × 8 checks → {n_clauses} clauses ({t1-t0:.1f}s)", flush=True)
    return clauses, clause_map


# ── 2-factor generation (same strategy as solver_2factor_sat_pipeline.py) ─
def generate_2factor_full(m, rng, allow_twocycles=True):
    """Random 2-factor: generate a random permutation and take its cycles."""
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
            for k in range(len(cycle)):
                a, b = cycle[k], cycle[(k + 1) % len(cycle)]
                u, v = (a, b) if a <= b else (b, a)
                edges.append((u, v))
    return sorted(edges)


# ── Edge-span analysis ──────────────────────────────────────────────────
def edge_spans(edges, m):
    """Compute |u-v| for each edge (mod m, with wrap-around)."""
    spans = []
    for u, v in edges:
        d = abs(u - v)
        spans.append(min(d, m - d))
    return spans


def edge_span_histogram(edges, m):
    spans = edge_spans(edges, m)
    hist = Counter(spans)
    return hist


# ── Lift coordinate analysis ────────────────────────────────────────────
def analyze_lifts(m, edges, cells):
    """Compute all 4m lifts and analyze their parity/mod distribution."""
    n = 2 * m
    lifts_all = []
    for (u, v) in cells:
        lifts_all.extend(c4_lift(u, v, n))
    
    # Parity stats
    x_parity = Counter(x % 2 for (x, y) in lifts_all)
    y_parity = Counter(y % 2 for (x, y) in lifts_all)
    xy_parity = Counter((x % 2, y % 2) for (x, y) in lifts_all)
    
    # Mod 3 stats
    x_mod3 = Counter(x % 3 for (x, y) in lifts_all)
    y_mod3 = Counter(y % 3 for (x, y) in lifts_all)
    
    # Distance from center
    cx = (n - 1) / 2.0
    cy = (n - 1) / 2.0
    dists = [math.sqrt((x - cx)**2 + (y - cy)**2) for (x, y) in lifts_all]
    
    return {
        "x_parity": dict(x_parity),
        "y_parity": dict(y_parity),
        "xy_parity": dict(xy_parity),
        "x_mod3": dict(x_mod3),
        "y_mod3": dict(y_mod3),
        "dist_mean": round(float(sum(dists) / len(dists)), 1),
        "dist_std": round(float((sum((d - sum(dists)/len(dists))**2 for d in dists) / len(dists))**0.5), 1),
        "n_lifts": len(lifts_all),
    }


# ── Check if a 2-factor is the same graph (up to isomorphism) ─────────
def graph_signature(edges):
    """Canonical graph signature: sorted degree sequence + multiset of spans."""
    return tuple(sorted(edge_spans(edges, max(max(e) for e in edges) + 1)))


# ── CP-SAT check ───────────────────────────────────────────────────────
def check_sat(m, edges, clauses, time_limit=60, verbose=True):
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    t = [model.NewBoolVar(f"t_{i}") for i in range(m)]
    for a, b, c, bits in clauses:
        b0 = (bits >> 0) & 1
        b1 = (bits >> 1) & 1
        b2 = (bits >> 2) & 1
        lit0 = t[a] if b0 == 0 else t[a].Not()
        lit1 = t[b] if b1 == 0 else t[b].Not()
        lit2 = t[c] if b2 == 0 else t[c].Not()
        model.AddBoolOr(lit0, lit1, lit2)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    start = time.time()
    status = solver.Solve(model)
    sat_time = time.time() - start
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        sol_bits = [int(solver.Value(t[i])) for i in range(m)]
        return {
            "sat_status": "SAT" if status == cp_model.OPTIMAL else "FEASIBLE",
            "sat_found": True,
            "orientation": sol_bits,
            "time_s": round(sat_time, 3),
        }
    # MaxSAT
    model2 = cp_model.CpModel()
    t2 = [model2.NewBoolVar(f"t_{i}") for i in range(m)]
    viol = [model2.NewBoolVar(f"v_{i}") for i in range(len(clauses))]
    for ci, (a, b, c, bits) in enumerate(clauses):
        b0 = (bits >> 0) & 1
        b1 = (bits >> 1) & 1
        b2 = (bits >> 2) & 1
        lit0 = t2[a] if b0 == 0 else t2[a].Not()
        lit1 = t2[b] if b1 == 0 else t2[b].Not()
        lit2 = t2[c] if b2 == 0 else t2[c].Not()
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
    return {
        "sat_status": "UNSAT",
        "sat_found": False,
        "maxsat_min_violations": n_violated,
        "maxsat_proven_optimal": status2 == cp_model.OPTIMAL,
        "orientation": orientation,
        "time_s": round(sat_time + maxsat_time, 3),
    }


# ── Full scan for m=36 ─────────────────────────────────────────────────
def scan_m36(n_trials=100, time_limit_per=60, seed=42, verbose=True):
    rng = random.Random(seed)
    results = []
    best_clauses = float("inf")
    best_min_viol = float("inf")
    sat_count = 0
    
    for trial in range(n_trials):
        if verbose:
            print(f"--- Trial {trial+1}/{n_trials} ---", flush=True)
        
        edges = generate_2factor_full(36, rng)
        
        # Check twocycles
        edge_set = Counter(edges)
        n_twocycles = sum(1 for v in edge_set.values() if v >= 2)
        
        clauses, cmap = enumerate_clauses(36, edges, verbose=verbose)
        n_clauses = len(clauses)
        
        if n_clauses < best_clauses:
            best_clauses = n_clauses
            if verbose:
                print(f"  ** new best clause count: {n_clauses} **", flush=True)
        
        if n_clauses == 0:
            res = {"trial": trial, "n_clauses": 0, "sat_status": "TRIVIAL_SAT",
                   "min_violations": 0, "n_twocycles": n_twocycles, "time_s": 0}
            sat_count += 1
        else:
            sat_result = check_sat(36, edges, clauses, time_limit=time_limit_per, verbose=False)
            min_viol = sat_result.get("maxsat_min_violations", -1)
            if min_viol == 0:
                sat_count += 1
                if verbose:
                    print(f"  *** SAT FOUND! trial {trial} ***", flush=True)
            if min_viol >= 0 and min_viol < best_min_viol:
                best_min_viol = min_viol
            
            # Estimate: convert orientation to cells
            cells = None
            if "orientation" in sat_result:
                ori = sat_result["orientation"]
                cells = []
                for idx, (u, v) in enumerate(edges):
                    if u == v:
                        cells.append((u, u))
                    elif ori[idx] == 0:
                        cells.append((u, v))
                    else:
                        cells.append((v, u))
            
            res = {
                "trial": trial, "n_clauses": n_clauses,
                "sat_status": sat_result.get("sat_status", "?"),
                "min_violations": min_viol,
                "maxsat_proven_optimal": sat_result.get("maxsat_proven_optimal", False),
                "n_twocycles": n_twocycles,
                "time_s": sat_result.get("time_s", 0),
            }
            if sat_result.get("sat_found"):
                res["found_solution"] = True
                res["orientation"] = ori
                res["cells"] = cells
        
        results.append(res)
    
    return results, best_clauses, best_min_viol, sat_count


# ── Main ────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=50, help="Number of random 2-factors for m=36 scan")
    ap.add_argument("--time-per", type=float, default=60.0, help="CP-SAT time limit per trial (s)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results/swarm_A5_report.md")
    ap.add_argument("--data", default="results/swarm_A5_data.json")
    ap.add_argument("--fast", action="store_true", help="Quick mode: fewer trials")
    args = ap.parse_args()
    
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    
    report_lines = []
    def R(msg):
        print(msg, flush=True)
        report_lines.append(msg)
    
    out_path = os.path.join(HERE, args.out)
    data_path = os.path.join(HERE, args.data)
    n_trials = args.trials
    
    R("# Swarm A5 Report: Why m=36 SAT but m=37 UNSAT?")
    R(f"\nDate: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    R(f"Parameters: trials={n_trials}, time_per={args.time_per}s, seed={args.seed}")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 1: Load and verify m=36 solution
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 1: Load m=36 solution and verify")
    
    with open(os.path.join(HERE, "results/solutions/m36.json")) as f:
        m36_data = json.load(f)
    cells_m36 = m36_data["cells"]
    edges_m36 = [tuple(sorted(c)) for c in cells_m36]
    
    R(f"\n- m=36 cells: {len(cells_m36)} cells")
    R(f"- m=36 edges: {len(edges_m36)} edges (from sorted cells)")
    R(f"- verify field: {m36_data.get('verify')}")
    
    # Check it's a valid 2-factor
    deg = Counter()
    for u, v in edges_m36:
        deg[u] += 1
        deg[v] += 1
    degree_ok = all(d == 2 for d in deg.values())
    R(f"- 2-factor valid: {degree_ok} (all degree 2)")
    
    # Enumerate clauses for m=36 solution's 2-factor
    R("\n### Clause enumeration for m=36 solution's 2-factor")
    clauses_m36, cmap_m36 = enumerate_clauses(36, edges_m36)
    n_cl_m36 = len(clauses_m36)
    R(f"- {n_cl_m36} clauses from {36*35*34//6} = {36*35*34//6} triples")
    
    # Check SAT for m=36 solution
    R("\n### SAT check for m=36 solution's 2-factor")
    sat_m36 = check_sat(36, edges_m36, clauses_m36, time_limit=args.time_per)
    R(f"- SAT result: {json.dumps(sat_m36, indent=2)}")
    R(f"- UNSAT clauses: {n_cl_m36}")
    
    # Edge-span histogram for m=36
    hist_m36 = edge_span_histogram(edges_m36, 36)
    R(f"\n- m=36 edge-span histogram: {dict(sorted(hist_m36.items()))}")
    
    # Lift analysis for m=36
    lift_ana_m36 = analyze_lifts(36, edges_m36, cells_m36)
    # Fix: convert tuple keys for JSON
    lift_ana_clean = {}
    for k, v in lift_ana_m36.items():
        if isinstance(v, dict):
            lift_ana_clean[k] = {str(kk): vv for kk, vv in v.items()}
        else:
            lift_ana_clean[k] = v
    R(f"- m=36 lift analysis: {json.dumps(lift_ana_clean, indent=2)}")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 2: Load m=37 best 2-factor (448-clause winner)
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 2: Load m=37 best 2-factor (best72)")
    
    with open(os.path.join(HERE, "results/swarm_D1_2_best72_clauses.json")) as f:
        m37_best72 = json.load(f)
    edges_m37_best72 = [tuple(e) for e in m37_best72["edges"]]
    R(f"\n- m=37 best72 edges: {len(edges_m37_best72)} edges")
    
    # Load the 448-clause mutation
    with open(os.path.join(HERE, "results/mutation_448_maxsat_long.json")) as f:
        m37_448 = json.load(f)
    R(f"\n- mutation 448-clause: min_violations={m37_448.get('min_violations')}, "
      f"total_bad={m37_448.get('total_bad')}, proven_optimal={m37_448.get('proven_optimal')}")
    
    # Load the solver_theory m37 long for edges
    with open(os.path.join(HERE, "results/solver_theory_m37_long.json")) as f:
        m37_long = json.load(f)
    edges_m37_long = [tuple(e) for e in m37_long.get("edges", [])]
    R(f"\n- m=37 solver_theory long edges: {len(edges_m37_long)} edges")
    
    # Edge-span histograms for m=37
    hist_m37_best72 = edge_span_histogram(edges_m37_best72, 37)
    R(f"\n- m=37 best72 edge-span histogram: {dict(sorted(hist_m37_best72.items()))}")
    
    hist_m37_long = edge_span_histogram(edges_m37_long, 37)
    R(f"\n- m=37 solver_theory long edge-span histogram: {dict(sorted(hist_m37_long.items()))}")
    
    # Enumerate clauses for m=37 best72
    R("\n### Clause enumeration for m=37 best72")
    clauses_m37_best72, cmap_m37_best72 = enumerate_clauses(37, edges_m37_best72)
    n_cl_m37_best72 = len(clauses_m37_best72)
    R(f"- {n_cl_m37_best72} clauses from {37*36*35//6} = {37*36*35//6} triples")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 3: Generate m=37-like 2-factors for m=36
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 3: Generate m=37-like 2-factors for m=36 and test")
    
    # Use the same generation strategy that produces m=37's best 2-factors
    scan_results, best_cl, best_mv, sat_count = scan_m36(
        n_trials=n_trials, time_limit_per=args.time_per, seed=args.seed)
    
    R(f"\n### m=36 random 2-factor scan ({n_trials} trials)")
    R(f"- SAT found: {sat_count}/{n_trials}")
    R(f"- Best clause count: {best_cl}")
    R(f"- Best min violations: {best_mv}")
    
    # Collect clause count distribution
    clause_counts = Counter(r["n_clauses"] for r in scan_results)
    R(f"- Clause count distribution: {dict(sorted(clause_counts.items()))}")
    
    # Collect min violation distribution
    viol_counts = Counter(r.get("min_violations", -1) for r in scan_results)
    R(f"- Min violation distribution: {dict(sorted(viol_counts.items()))}")
    
    # Analyze SAT vs UNSAT cases
    sat_edges_details = []
    for res in scan_results:
        if res.get("found_solution"):
            sat_edges_details.append({
                "trial": res["trial"],
                "n_clauses": res["n_clauses"],
            })
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 4: Compare span distributions systematically
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 4: Systematic span distribution comparison")
    
    # For m=36 scan: find the median clause count and best clause 2-factors
    # and compare their span profiles to m=37's best
    
    # Generate span histograms for m=36 scan
    rng = random.Random(args.seed)
    m36_span_hists = []
    for trial in range(min(100, n_trials)):
        edges = generate_2factor_full(36, rng)
        hist = edge_span_histogram(edges, 36)
        m36_span_hists.append(hist)
    
    # Average span distribution
    all_spans = set()
    for h in m36_span_hists:
        all_spans.update(h.keys())
    
    avg_hist = {s: 0.0 for s in all_spans}
    for h in m36_span_hists:
        for s, c in h.items():
            avg_hist[s] += c
    for s in avg_hist:
        avg_hist[s] /= len(m36_span_hists)
    
    R(f"\n- m=36 average span histogram (over {len(m36_span_hists)} random 2-factors):")
    R(f"  {dict(sorted(avg_hist.items()))}")
    R(f"\n- m=37 best72 span histogram:")
    R(f"  {dict(sorted(hist_m37_best72.items()))}")
    R(f"\n- m=36 solution's span histogram:")
    R(f"  {dict(sorted(hist_m36.items()))}")
    
    # Compute span entropy-ish metric: how many distinct spans?
    R(f"\n- Distinct spans: m=36 solution={len(hist_m36)}, "
      f"m=37 best72={len(hist_m37_best72)}, "
      f"m=37 long={len(hist_m37_long)}")
    
    # Count large-span edges (span > m/2 is considered "large" by some definitions)
    large_thresh = lambda m: m * 0.45
    R(f"\n- Edges with span > 0.45*m:")
    R(f"  m=36 solution: {sum(c for s,c in hist_m36.items() if s > large_thresh(36))} "
      f"(of {sum(hist_m36.values())})")
    R(f"  m=37 best72: {sum(c for s,c in hist_m37_best72.items() if s > large_thresh(37))} "
      f"(of {sum(hist_m37_best72.values())})")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 5: Lifts coordinate analysis (parity/mod hypothesis)
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 5: Lift coordinate analysis (parity/mod hypothesis)")
    
    # For m=36 solution
    R("\n### m=36 solution lift analysis:")
    for k, v in lift_ana_m36.items():
        R(f"  {k}: {v}")
    
    # For m=36, n=72, center = (35.5, 35.5)
    # For m=37, n=74, center = (36.5, 36.5)
    R("\n### Key observation: parity of center")
    R(f"- m=36: n=72, center=({71/2}, {71/2}) = (35.5, 35.5)")
    R(f"- m=37: n=74, center=({73/2}, {73/2}) = (36.5, 36.5)")
    R(f"- Both have half-integer centers (same parity pattern in C4 rotation)")
    R(f"- But 36 is divisible by 3, while 37 is not")
    
    # Analyze lift coordinates mod 3 in detail
    R("\n### Mod 3 analysis:")
    
    def mod3_stats(n, edges, cells):
        lifts = []
        for (u, v) in cells:
            lifts.extend(c4_lift(u, v, n))
        x_mod3 = Counter(x % 3 for (x, y) in lifts)
        y_mod3 = Counter(y % 3 for (x, y) in lifts)
        mod3_pairs = Counter((x % 3, y % 3) for (x, y) in lifts)
        return x_mod3, y_mod3, mod3_pairs
    
    # For m=36
    x3_m36, y3_m36, p3_m36 = mod3_stats(72, edges_m36, cells_m36)
    R(f"- m=36 lifts x mod 3: {dict(sorted(x3_m36.items()))}")
    R(f"- m=36 lifts y mod 3: {dict(sorted(y3_m36.items()))}")
    R(f"- m=36 lifts (x mod 3, y mod 3): {dict(sorted(p3_m36.items()))}")
    
    # For m=37 best72 with its known-best orientation from the 448-clause solver
    # We don't know the orientation for best72, but we can analyze raw edges
    # (cells = oriented edges)
    # For the mutation_448, we have the orientation
    m37_448_ori = m37_448.get("orientation", [])
    R(f"\n- m=37 mutation_448 orientation length: {len(m37_448_ori)}")
    
    # Need to reconstruct cells for mutation_448
    # The mutation_448 file doesn't have edges, only orientation+n_clauses
    # But the best72 file has edges but no orientation
    # Let's use the solver_theory m37 long's edges (same as best72)
    m37_448_cells = []
    for idx, (u, v) in enumerate(edges_m37_best72):
        if u == v:
            m37_448_cells.append((u, u))
        elif m37_448_ori[idx] == 0:
            m37_448_cells.append((u, v))
        else:
            m37_448_cells.append((v, u))
    
    R(f"\n### m=37 448-mutation lift analysis (best72 edges + optimal orientation):")
    x3_m37, y3_m37, p3_m37 = mod3_stats(74, edges_m37_best72, m37_448_cells)
    R(f"- m=37 lifts x mod 3: {dict(sorted(x3_m37.items()))}")
    R(f"- m=37 lifts y mod 3: {dict(sorted(y3_m37.items()))}")
    R(f"- m=37 lifts (x mod 3, y mod 3): {dict(sorted(p3_m37.items()))}")
    
    # Compare with m=36
    R("\n### Mod 3 comparison (m=36 vs m=37):")
    R("- 36 is divisible by 3 → mod-3 residues can be symmetric")
    R("- 37 ≡ 1 (mod 3) → no mod-3 symmetry in the index space")
    
    # Critical: size of the grid
    R(f"\n- Grid size: m=36 → n=72=⌈72/3⌉=24 cells per 3×3 block")
    R(f"- Grid size: m=37 → n=74=⌈74/3⌉≈24.67 cells — NOT aligned to 3")
    
    # Compare lift coordinate distributions
    R("\n### Lift distance from center comparison:")
    R(f"- m=36: mean_dist={lift_ana_m36['dist_mean']}, std={lift_ana_m36['dist_std']}")
    
    lift_ana_m37 = analyze_lifts(37, edges_m37_best72, m37_448_cells)
    R(f"- m=37 (448 mutation): mean_dist={lift_ana_m37['dist_mean']}, std={lift_ana_m37['dist_std']}")
    
    # Lift parity comparison
    R(f"\n### Lift parity comparison:")
    R(f"- m=36 xy_parity: {dict(sorted(lift_ana_m36['xy_parity'].items()))}")
    R(f"- m=37 xy_parity: {dict(sorted(lift_ana_m37['xy_parity'].items()))}")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 6: Mod 2 (grid bipartiteness) analysis
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 6: Mod 2 (even/odd) parity analysis")
    R("\n### C4 rotation parity effect:")
    R("- C4 rotation: (x,y) → (n-1-y, x) → (n-1-x, n-1-y) → (y, n-1-x)")
    R("- For even n: n-1 is ODD")
    R("- n=72: n-1=71 (odd), n=74: n-1=73 (odd)")
    
    # Track how parity changes under C4
    def c4_parity_analysis(n):
        """For a point (x,y) with even n, track parity changes through 4 rotations."""
        return {
            "n": n,
            "n_minus_1": n - 1,
            "n_minus_1_is_odd": (n - 1) % 2 == 1,
        }
    
    R(f"\n- n=72: n-1=71 is odd → C4 alternates parity")
    R(f"- n=74: n-1=73 is odd → C4 alternates parity")
    R(f"- Both have same parity behavior under C4: (even,even) → (odd,even) → (odd,odd) → (even,odd)")
    
    # Cell mod 2 analysis
    R("\n### Cell coordinate mod 2:")
    cells_m36_mod2 = Counter((u % 2, v % 2) for (u, v) in cells_m36)
    cells_m37_mod2 = Counter((u % 2, v % 2) for (u, v) in m37_448_cells)
    R(f"- m=36 cells (u mod 2, v mod 2): {dict(sorted(cells_m36_mod2.items()))}")
    R(f"- m=37 cells (u mod 2, v mod 2): {dict(sorted(cells_m37_mod2.items()))}")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 7: Compare number of solutions in orientation space
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 7: Clause density analysis")
    
    R(f"\n### Clause density (clauses per unit of orientation space):")
    R(f"- m=36 best solution 2-factor: {n_cl_m36} clauses / 2^36 = {n_cl_m36/2**36:.6e}")
    R(f"- m=37 best72 2-factor: {n_cl_m37_best72} clauses / 2^37 = {n_cl_m37_best72/2**37:.6e}")
    
    # Theoretical: how many combos actually forbidden?
    total_triples_m36 = 36 * 35 * 34 // 6
    total_triples_m37 = 37 * 36 * 35 // 6
    R(f"\n### Triple coverage:")
    R(f"- m=36 solution: {n_cl_m36} forbidden combos out of {total_triples_m36}×8 = {total_triples_m36*8}")
    R(f"- m=37 best72: {n_cl_m37_best72} forbidden combos out of {total_triples_m37}×8 = {total_triples_m37*8}")
    R(f"- m=36 solution coverage: {100*n_cl_m36/(total_triples_m36*8):.2f}%")
    R(f"- m=37 best72 coverage: {100*n_cl_m37_best72/(total_triples_m37*8):.2f}%")
    
    # ────────────────────────────────────────────────────────────────────
    # STEP 8: Test m=36 scan — do SAT cases have specific pan profile?
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 8: SAT case characterization (m=36)")
    
    if sat_count > 0:
        R(f"\n### {sat_count} SAT cases found — analyzing their properties")
        sat_avg_clauses = sum(r["n_clauses"] for r in scan_results if r.get("found_solution"))
        R(f"- Average clauses for SAT cases: {sat_avg_clauses/sat_count:.1f}")
    else:
        R(f"\n### No SAT cases found in scan → m=36 is also HARD with random 2-factors")
        R("This means: m=36's solution 2-factor is SPECIAL, not typical!")
    
    # The 448-clause state on m=37: 17 violations is optimal
    R("\n## Step 9: Implications")
    
    # Scan results for m=36: if no SAT found, then m=36's solution is special
    if sat_count == 0 and best_mv > 0:
        R(f"\n### No SAT cases out of {n_trials} random m=36 2-factors")
        R(f"- Best min violations: {best_mv}")
        R(f"- This suggests the m=36 solution's 2-factor is RARE/SPECIAL")
        R(f"- Not just any 2-factor works — only specific ones enable SAT")
        R(f"- This parallels m=37: the best 2-factors still have residual")
        R(f"  violations proven optimal")
    elif sat_count > 0:
        R(f"\n### {sat_count}/{n_trials} SAT cases found — m=36 is more flexible")
        R(f"- But still, most random 2-factors are UNSAT")
        R(f"- Implies: m=36's solution uses a specific 2-factor + orientation")
        R(f"- There may be a SUBCLASS of 'good' 2-factors that work")
    
    # ────────────────────────────────────────────────────────────────────
    # Comparative analysis: what makes the m=36 solution special?
    # ────────────────────────────────────────────────────────────────────
    R("\n## Step 10: What makes m=36 solution's 2-factor special?")
    
    # Number of loops (self-edges) in m=36
    loops_m36 = [(u, v) for (u, v) in edges_m36 if u == v]
    loops_m37_best72 = [(u, v) for (u, v) in edges_m37_best72 if u == v]
    R(f"\n- Loops in m=36 solution: {len(loops_m36)}")
    R(f"- Loops in m=37 best72: {len(loops_m37_best72)}")
    
    # Span diversity
    span_var_m36 = sum((s - sum(edge_spans(edges_m36, 36)) / 36)**2 * c 
                        for s, c in hist_m36.items())
    span_var_m37 = sum((s - sum(edge_spans(edges_m37_best72, 37)) / 37)**2 * c 
                        for s, c in hist_m37_best72.items())
    R(f"- Span variance: m=36={span_var_m36:.1f}, m=37={span_var_m37:.1f}")
    
    # Count edges with specific span=0 (loops), span near m/2, etc.
    R(f"\n- m=36 small spans (0-5): {sum(c for s,c in hist_m36.items() if s <= 5)}")
    R(f"- m=37 small spans (0-5): {sum(c for s,c in hist_m37_best72.items() if s <= 5)}")
    R(f"- m=36 large spans ({18}-18): {hist_m36.get(18, 0)}")
    R(f"- m=37 large spans ({18}-19): {sum(c for s,c in hist_m37_best72.items() if abs(s - 18.5) <= 0.5)}")
    
    # ────────────────────────────────────────────────────────────────────
    # SAVE DATA
    # ────────────────────────────────────────────────────────────────────
    # Clean Counter/dict keys for JSON
    def ck(d):
        return {str(k): v for k, v in d.items()}
    def clean_lift_analysis(la):
        out = {}
        for k, v in la.items():
            if isinstance(v, dict):
                out[k] = ck(v)
            else:
                out[k] = v
        return out
    
    data_out = {
        "m36_solution": {
            "n_clauses": n_cl_m36,
            "sat_result": sat_m36,
            "edge_span_histogram": dict(sorted(hist_m36.items())),
            "lift_analysis": clean_lift_analysis(lift_ana_m36),
        },
        "m37_best72": {
            "edges": edges_m37_best72,
            "n_clauses": n_cl_m37_best72,
            "edge_span_histogram": dict(sorted(hist_m37_best72.items())),
            "lift_analysis": clean_lift_analysis(lift_ana_m37),
        },
        "m36_scan": {
            "n_trials": n_trials,
            "sat_count": sat_count,
            "best_clauses": best_cl,
            "best_min_violations": best_mv,
            "clause_count_distribution": {str(k): v for k, v in sorted(clause_counts.items())},
            "violation_distribution": {str(k): v for k, v in sorted(viol_counts.items())},
            "results": scan_results,
        },
        "comparison": {
            "m36_mod3_lifts": {"x": dict(sorted(x3_m36.items())), "y": dict(sorted(y3_m36.items())),
                               "pairs": {str(k): v for k,v in sorted(p3_m36.items())}},
            "m37_mod3_lifts": {"x": dict(sorted(x3_m37.items())), "y": dict(sorted(y3_m37.items())),
                               "pairs": {str(k): v for k,v in sorted(p3_m37.items())}},
            "m36_cell_mod2": {str(k): v for k, v in sorted(cells_m36_mod2.items())},
            "m37_cell_mod2": {str(k): v for k, v in sorted(cells_m37_mod2.items())},
        },
    }
    
    with open(data_path, "w") as f:
        json.dump(data_out, f, indent=2)
    R(f"\nData saved to {data_path}")
    
    # Write report
    report = "\n".join(report_lines)
    with open(out_path, "w") as f:
        f.write(report)
    R(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    main()

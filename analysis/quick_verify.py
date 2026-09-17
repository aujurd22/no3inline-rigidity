"""
Quick CP-SAT verification for any 2-factor candidate.
Usage: python quick_verify.py <config.json>
Reuses the exact same pipeline as orientation_maxsat.py.
"""
import json, sys, time, os

HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
sys.path.insert(0, HERE)

def verify(edges, label="config"):
    """Verify a 2-factor: enumerate clauses → CP-SAT MaxSAT."""
    from solver_2factor_sat_pipeline import enumerate_clauses
    from ortools.sat.python import cp_model
    
    M = len(edges)
    print(f"Verifying {label}: {M} edges", flush=True)
    
    # Phase 1: enumerate clauses
    t0 = time.time()
    clause_list, clause_map = enumerate_clauses(M, edges, verbose=True)
    t_cl = time.time() - t0
    
    if len(clause_list) > 2000:
        print(f"  WARNING: {len(clause_list)} clauses (config_408 has 408)", flush=True)
        print(f"  Likely > 16 violations, skipping CP-SAT", flush=True)
        return {"n_clauses": len(clause_list), "skipped": True}
    
    # Phase 2: CP-SAT
    print(f"  Building CP-SAT model: {M} vars, {len(clause_list)} clauses...", flush=True)
    t0 = time.time()
    
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(M)]
    
    violation_vars = []
    for idx, (a, b, c, bits) in enumerate(clause_list):
        b1, b2, b3 = (bits >> 0) & 1, (bits >> 1) & 1, (bits >> 2) & 1
        lit_a = x[a] if b1 == 1 else x[a].Not()
        lit_b = x[b] if b2 == 1 else x[b].Not()
        lit_c = x[c] if b3 == 1 else x[c].Not()
        v = model.NewBoolVar(f"v{idx}")
        model.AddBoolAnd([lit_a, lit_b, lit_c]).OnlyEnforceIf(v)
        model.AddBoolOr([lit_a.Not(), lit_b.Not(), lit_c.Not()]).OnlyEnforceIf(v.Not())
        violation_vars.append(v)
    
    model.Minimize(sum(violation_vars))
    
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    solver.parameters.max_time_in_seconds = 120.0
    
    print(f"  Solving...", flush=True)
    t_solve = time.time()
    status = solver.Solve(model)
    t_total = time.time() - t_solve
    
    result = {
        "n_clauses": len(clause_list),
        "solver_status": solver.StatusName(status),
        "min_violations": int(solver.ObjectiveValue()) if (status == cp_model.OPTIMAL or status == cp_model.FEASIBLE) else None,
        "proven_optimal": status == cp_model.OPTIMAL,
        "best_bound": solver.BestObjectiveBound() if (status == cp_model.OPTIMAL or status == cp_model.FEASIBLE) else None,
        "time_enumerate_s": round(t_cl, 1),
        "time_solve_s": round(t_total, 1),
    }
    
    print(f"  Status: {result['solver_status']}", flush=True)
    print(f"  Min violations: {result['min_violations']}", flush=True)
    print(f"  Proven optimal: {result['proven_optimal']}", flush=True)
    
    if result['min_violations'] is not None and result['min_violations'] < 16:
        print(f"\n  ★★★ BREAKTHROUGH! < 16 violations! ★★★", flush=True)
    
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_verify.py <config.json>")
        sys.exit(1)
    
    fn = sys.argv[1]
    with open(fn) as f:
        data = json.load(f)
    
    edges = data.get("edges", data.get("cells", data.get("best_cells", [])))
    if not edges:
        # Try other key names
        for k in data:
            if isinstance(data[k], list) and len(data[k]) == 37:
                edges = data[k]
                break
    
    edges = [(min(u,v), max(u,v)) for u,v in edges if isinstance(u, (int,float))]
    
    if len(edges) != 37:
        print(f"ERROR: expected 37 edges, got {len(edges)}")
        # Try checking as cell tuples directly
        for k in data:
            print(f"  key '{k}': {type(data[k])}, len={len(data[k]) if hasattr(data[k], '__len__') else '?'}")
        sys.exit(1)
    
    result = verify(edges, os.path.basename(fn))
    
    # Save verification result
    out_fn = fn.replace(".json", "_verified.json")
    with open(out_fn, "w") as f:
        json.dump(result, f, indent=1)
    print(f"\nSaved verification to {out_fn}", flush=True)

"""
CP-SAT verification for any 2-factor config.
Reuses the clause enumeration from solver_2factor_sat_pipeline.py
"""
import json, sys, time
sys.path.insert(0, "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis")
from solver_2factor_sat_pipeline import C4RotatedGrid

M = 37
N = 74

def verify_config(edges, label="config", time_limit=60):
    """Run full MaxSAT on a 2-factor config."""
    grid = C4RotatedGrid(N)
    
    # 1. Count clauses (= number of forbidden orientation combos)
    t0 = time.time()
    n_clauses, bad_pairs = grid.enumerate_clauses(edges)
    t_clause = time.time() - t0
    print(f"  Clauses: {n_clauses} ({t_clause:.1f}s)", flush=True)
    
    # 2. Build CP-SAT model
    t0 = time.time()
    model = cp_model.CpModel()
    x = {}
    for u, v in bad_pairs:
        x[(u, v)] = model.NewBoolVar(f"x_{u}_{v}")
        x[(v, u)] = x[(u, v)]  # symmetry (but we only need (u,v) with u<v)
    
    # Clause constraints
    for u, v_list in bad_pairs.items():
        for v in v_list:
            if u < v:
                model.Add(x[(u, v)] >= 1)  # at least one orientation must be bad
    
    # This isn't right either. Let me load the actual solver code.
    return None

if __name__ == "__main__":
    from solver_2factor_sat_pipeline import M, N, C4RotatedGrid
    from ortools.sat.python import cp_model
    
    if len(sys.argv) > 1:
        fn = sys.argv[1]
        with open(fn) as f:
            data = json.load(f)
        edges = [(min(u,v), max(u,v)) for u,v in data.get("edges", data.get("cells", []))]
        if len(edges) != M:
            print(f"ERROR: expected {M} edges, got {len(edges)}")
            sys.exit(1)
        print(f"Verifying {fn}: {len(edges)} cells")
        verify_config(edges, fn)
    else:
        print("Usage: python verify_any.py <config.json>")

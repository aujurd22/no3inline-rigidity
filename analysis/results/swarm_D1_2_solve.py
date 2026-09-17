"""
swarm_D1_2_solve.py — D1 follow-up: solve the 3-SAT / MaxSAT problem from
enumerated orientation clauses, using CP-SAT (ortools).

Usage:
    # Must be run with Python that has ortools:
    C:/Users/djr82/.workbuddy/binaries/python/envs/default/Scripts/python.exe \\
        swarm_D1_2_solve.py --clauses swarm_D1_2_best72_clauses.json \\
        --out swarm_D1_2_best72_solved.json
"""

import os, sys, json, time, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import solver_theory_m37 as S

M = 37


def clauses_to_cnf(clauses):
    """
    Convert clause list [(e1,e2,e3,a,b,c)] to CP-SAT literals.

    Returns:
        cnf_clauses: list of list of (var_idx, negated_bool)
        var_of_edge: edge index → CP-SAT variable index (here they're the same)
    """
    cnf = []
    for e1, e2, e3, a, b, c in clauses:
        # Clause: NOT(t1=a AND t2=b AND t3=c)
        #        = (t1 != a) OR (t2 != b) OR (t3 != c)
        #        = (t1 if a==0 else NOT t1) OR ...
        lits = []
        for var, bit in [(e1, a), (e2, b), (e3, c)]:
            if bit == 0:
                lits.append((var, False))  # t_i must be 1
            else:
                lits.append((var, True))   # t_i must be 0 (negated)
        cnf.append(lits)
    return cnf


def orientation_from_solution(solution, edges):
    """Convert CP-SAT solution vector (list of 0/1) to cells list."""
    cells = []
    for eidx, (u, v) in enumerate(edges):
        if u == v:
            cells.append((u, u))
        elif solution[eidx] == 0:
            cells.append((u, v))
        else:
            cells.append((v, u))
    return cells


def solve_sat(clauses_metadata, time_limit_s=300, label=""):
    """
    Attempt SAT (all clauses hard). If UNSAT, try MaxSAT.
    
    Returns dict with solution status.
    """
    from ortools.sat.python import cp_model

    clauses = clauses_metadata["clauses"]
    n_clauses = len(clauses)
    edges = [tuple(e) for e in clauses_metadata["edges"]]
    E = len(edges)  # should be 37

    result = {
        "label": label,
        "n_clauses": n_clauses,
        "n_vars": E,
    }

    # ---- Step 1: Try pure SAT (all clauses hard) ----
    print(f"\n{'='*60}", flush=True)
    print(f"  SAT attempt: {n_clauses} clauses on {E} vars ({label})", flush=True)
    print(f"{'='*60}", flush=True)
    t0 = time.time()

    model = cp_model.CpModel()
    vars_ = [model.NewBoolVar(f"t_{i}") for i in range(E)]

    cnf = clauses_to_cnf(clauses)
    for lits in cnf:
        model.AddBoolOr([vars_[v] if not neg else ~vars_[v] for v, neg in lits])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True

    status_sat = solver.Solve(model)

    sat_time = time.time() - t0
    result["sat_attempt_time_s"] = sat_time
    result["sat_status"] = solver.StatusName(status_sat)

    if status_sat == cp_model.OPTIMAL or status_sat == cp_model.FEASIBLE:
        solution = [solver.Value(v) for v in vars_]
        cells = orientation_from_solution(solution, edges)

        # Verify with Board
        bd = S.Board(M)
        bd.build(edges, cells)
        vt = bd.verify_total()

        result["sat_solution"] = solution
        result["sat_cells"] = cells
        result["sat_verify_total"] = vt
        result["sat_found"] = (vt == 0)

        print(f"  SAT: FOUND solution with verify_total={vt}", flush=True)
        if vt == 0:
            print(f"  *** BREAKTHROUGH: no-3-in-line orientation found! ***", flush=True)
        return result

    # ---- Step 2: UNSAT → MaxSAT (minimize violated clauses) ----
    print(f"  SAT: UNSAT -> trying MaxSAT (minimize violated clauses)", flush=True)
    t1 = time.time()

    model2 = cp_model.CpModel()
    vars2 = [model2.NewBoolVar(f"t_{i}") for i in range(E)]
    relax_vars = []

    for idx, lits in enumerate(cnf):
        relax = model2.NewBoolVar(f"relax_{idx}")
        relax_vars.append(relax)
        all_lits = [vars2[v] if not neg else ~vars2[v] for v, neg in lits]
        all_lits.append(relax)
        model2.AddBoolOr(all_lits)

    model2.Minimize(sum(relax_vars))

    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = time_limit_s
    solver2.parameters.num_search_workers = 8
    solver2.parameters.log_search_progress = True

    status_max = solver2.Solve(model2)

    max_time = time.time() - t1
    result["maxsat_attempt_time_s"] = max_time
    result["maxsat_status"] = solver2.StatusName(status_max)

    if status_max == cp_model.OPTIMAL or status_max == cp_model.FEASIBLE:
        best_solution = [solver2.Value(v) for v in vars2]
        best_relax = [solver2.Value(r) for r in relax_vars]
        min_violations = int(solver2.ObjectiveValue())
        best_cells = orientation_from_solution(best_solution, edges)

        # Decode which clauses are violated
        violated = [i for i, r in enumerate(best_relax) if r == 1]

        # Verify with Board
        bd = S.Board(M)
        bd.build(edges, best_cells)
        vt = bd.verify_total()

        result["maxsat_solution"] = best_solution
        result["maxsat_cells"] = best_cells
        result["maxsat_min_violations"] = min_violations
        result["maxsat_n_violated"] = len(violated)
        result["maxsat_verify_total"] = vt
        result["maxsat_sample_violated"] = violated[:20]

        print(f"  MaxSAT: min_violations={min_violations}, "
              f"verify_total={vt}, best feasible", flush=True)
        if vt == 0:
            print(f"  *** BREAKTHROUGH: verify_total=0! ***", flush=True)
    else:
        print(f"  MaxSAT: no feasible solution found within time limit", flush=True)

    return result


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--clauses", type=str, required=True,
                    help="JSON file with clause data from enumerate step")
    ap.add_argument("--out", type=str, default=None,
                    help="Output JSON path (default: based on input name)")
    ap.add_argument("--time-limit", type=float, default=300.0,
                    help="Time limit per solver call (seconds)")
    args = ap.parse_args()

    inpath = os.path.join(HERE, args.clauses)
    print(f"Loading clauses from {inpath} ...", flush=True)
    data = json.load(open(inpath))
    label = data.get("label", args.clauses)

    if args.out is None:
        outpath = inpath.replace("_clauses.json", "_solved.json")
    else:
        outpath = os.path.join(HERE, args.out)

    result = solve_sat(data, time_limit_s=args.time_limit, label=label)

    # Write results
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {outpath}", flush=True)


if __name__ == "__main__":
    main()

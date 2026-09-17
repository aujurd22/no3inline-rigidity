"""Solve the continuous relaxation of a short-direction overflow layer.

This tests whether a CP-SAT obstruction is already a linear-capacity
obstruction.  The arbitrary-deletion model is purely linear before the
overflow objective is added, so its Boolean variables can be relaxed to their
proto domains and passed directly to HiGHS through scipy.optimize.linprog.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

from ortools.linear_solver import pywraplp

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    build_general_model,
    short_direction_lines,
)


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument("--triple-count", type=int, default=None)
    parser.add_argument("--quadruple-count", type=int, default=None)
    parser.add_argument("--direction-q", type=int, required=True)
    parser.add_argument("--hard-direction-q", type=int, default=0)
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    problem = build_general_model(
        base,
        hitting["defect_owner_sets"],
        candidate_blockers(base),
        args.size,
        args.adjacency_count,
        args.triple_count,
        None,
        None,
        None,
        args.quadruple_count,
    )
    proto = problem["model"].Proto()
    original_variables = len(proto.variables)
    hard_lines = sorted(short_direction_lines(args.hard_direction_q))
    objective_lines = sorted(
        set(short_direction_lines(args.direction_q)) - set(hard_lines)
    )
    solver = pywraplp.Solver.CreateSolver("GLOP")
    assert solver is not None
    solver.SetTimeLimit(int(args.time_limit * 1000))
    infinity = solver.infinity()
    variables = []
    for index, variable in enumerate(proto.variables):
        domain = list(variable.domain)
        assert len(domain) == 2
        variables.append(
            solver.NumVar(float(domain[0]), float(domain[1]), variable.name or f"v{index}")
        )
    overflow_variables = [
        solver.NumVar(0.0, infinity, f"overflow_{line_no}")
        for line_no in range(len(objective_lines))
    ]
    linear_constraints = []

    for number, constraint in enumerate(proto.constraints):
        assert constraint.has_linear()
        assert not constraint.enforcement_literal
        linear = constraint.linear
        coefficients = list(zip(linear.vars, linear.coeffs))
        lower, upper = linear.domain
        name = constraint.name or f"cp_{number}"
        lp_constraint = solver.Constraint(
            float(lower) if abs(lower) < 10**18 else -infinity,
            float(upper) if abs(upper) < 10**18 else infinity,
            name,
        )
        for index, coefficient in coefficients:
            lp_constraint.SetCoefficient(variables[index], float(coefficient))
        linear_constraints.append((name, lp_constraint))

    def occupancy_coefficients(key):
        a, b, c = key
        old_counts = [
            sum(a * x + b * y == c for x, y in orbit)
            for orbit in problem["base_orbits"]
        ]
        coefficients = [
            (problem["removed"][index].Index(), -count)
            for index, count in enumerate(old_counts)
            if count
        ]
        for cell, orbit in problem["candidate_orbits"].items():
            count = sum(a * x + b * y == c for x, y in orbit)
            if count:
                coefficients.append(
                    (problem["cell_variable"][cell].Index(), count)
                )
        return coefficients, sum(old_counts)

    for key in hard_lines:
        coefficients, offset = occupancy_coefficients(key)
        name = f"hard_line_{key}"
        constraint = solver.Constraint(-infinity, 2 - offset, name)
        for index, coefficient in coefficients:
            constraint.SetCoefficient(variables[index], coefficient)
        linear_constraints.append((name, constraint))
    for line_no, key in enumerate(objective_lines):
        coefficients, offset = occupancy_coefficients(key)
        name = f"overflow_line_{key}"
        constraint = solver.Constraint(-infinity, 2 - offset, name)
        for index, coefficient in coefficients:
            constraint.SetCoefficient(variables[index], coefficient)
        constraint.SetCoefficient(overflow_variables[line_no], -1)
        linear_constraints.append((name, constraint))
    objective = solver.Objective()
    for variable in overflow_variables:
        objective.SetCoefficient(variable, 1.0)
    objective.SetMinimization()
    started = time.time()
    status = solver.Solve()
    status_names = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }
    success = status == pywraplp.Solver.OPTIMAL
    payload = {
        "parameters": vars(args),
        "status": status_names.get(status, str(status)),
        "success": success,
        "objective": objective.Value() if success else None,
        "original_variable_count": original_variables,
        "overflow_variable_count": len(objective_lines),
        "constraint_count": solver.NumConstraints(),
        "elapsed_s": round(time.time() - started, 3),
    }
    if success:
        values = [variable.solution_value() for variable in variables]
        fractionality = [
            min(value - math.floor(value), math.ceil(value) - value)
            for value in values
        ]
        payload["fractional_variable_count"] = sum(
            value > 1e-7 for value in fractionality
        )
        payload["max_fractionality"] = max(fractionality, default=0.0)
        payload["active_overflow_lines"] = [
            {
                "line": list(key),
                "overflow": overflow_variables[line_no].solution_value(),
            }
            for line_no, key in enumerate(objective_lines)
            if overflow_variables[line_no].solution_value() > 1e-7
        ]
        dual_support = [
            {
                "constraint": name,
                "dual": constraint.dual_value(),
            }
            for name, constraint in linear_constraints
            if abs(constraint.dual_value()) > 1e-7
        ]
        dual_support.sort(key=lambda item: -abs(item["dual"]))
        payload["nonzero_constraint_dual_count"] = len(dual_support)
        payload["largest_constraint_duals"] = dual_support[:100]
    path = HERE / args.out
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "success": payload["success"],
                "objective": payload["objective"],
                "fractional_variable_count": payload.get(
                    "fractional_variable_count"
                ),
                "elapsed_s": payload["elapsed_s"],
            },
            indent=2,
        )
    )
    print(path)


if __name__ == "__main__":
    main()

"""Intersect abstract line-capacity moment constraints across rot4 directions.

This is a global relaxation: it does not choose fundamental cells.  Instead,
for every primitive direction orbit it chooses an abstract occupancy 0,1,2
for each C4 line orbit.  Row/column saturation fixes the zeroth and second
moments.  The Gaussian resource formula shows that every fourth moment is a
linear expression in the same two cell moments

    Q = sum X^2 Y^2,
    T = sum X Y (X^2-Y^2).

Infeasibility would therefore be a global rot4 obstruction, independent of a
local basin.  Feasibility measures the strength left after discarding cell
compatibility.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, N
from verify_rot4_multidirection_resource_model import direction_representatives


HERE = Path(__file__).resolve().parent


def direction_resources(normal: tuple[int, int]):
    """Return (centered label, orbit size, line capacity) records."""
    a, b = normal
    absolute_counts = Counter()
    for x in range(N):
        for y in range(N):
            label = abs(2 * (a * x + b * y) - (N - 1) * (a + b))
            absolute_counts[label] += 1
    records = []
    for label, total_point_count in sorted(absolute_counts.items()):
        orbit_size = 2 if label == 0 else 4
        divisor = 1 if label == 0 else 2
        assert total_point_count % divisor == 0
        one_line_point_count = total_point_count // divisor
        records.append(
            {
                "label": label,
                "orbit_size": orbit_size,
                "line_point_count": one_line_point_count,
                "capacity": min(2, one_line_point_count),
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", type=int, default=5)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--enforce-cell-moments",
        action="store_true",
        help="require Q,T to arise from an oriented 2-factor of fundamental cells",
    )
    parser.add_argument(
        "--out", default="rot4_direction_moment_relaxation.json"
    )
    args = parser.parse_args()

    model = cp_model.CpModel()
    max_cell_moment = M * (N - 1) ** 4
    q_quotient = model.NewIntVar(0, max_cell_moment // 8, "Q_quotient")
    Q = model.NewIntVar(0, max_cell_moment, "Q")
    model.Add(Q == 8 * q_quotient + (M % 8))
    t_bound = max_cell_moment
    t_quotient = model.NewIntVar(
        -t_bound // 8, t_bound // 8, "T_quotient"
    )
    T = model.NewIntVar(-t_bound, t_bound, "T")
    model.Add(T == 8 * t_quotient)

    cell_variables = {}
    if args.enforce_cell_moments:
        incident = {u: [] for u in range(M)}
        for u in range(M):
            loop = model.NewBoolVar(f"cell_{u}_{u}")
            cell_variables[(u, u)] = loop
            incident[u].append(2 * loop)
        for u in range(M):
            for v in range(u + 1, M):
                forward = model.NewBoolVar(f"cell_{u}_{v}")
                reverse = model.NewBoolVar(f"cell_{v}_{u}")
                cell_variables[(u, v)] = forward
                cell_variables[(v, u)] = reverse
                model.Add(forward + reverse <= 1)
                incident[u].extend([forward, reverse])
                incident[v].extend([forward, reverse])
        for u in range(M):
            model.Add(sum(incident[u]) == 2)
        model.Add(sum(cell_variables.values()) == M)
        model.Add(
            Q
            == sum(
                (2 * u - (N - 1)) ** 2
                * (2 * v - (N - 1)) ** 2
                * variable
                for (u, v), variable in cell_variables.items()
            )
        )
        model.Add(
            T
            == sum(
                (2 * u - (N - 1))
                * (2 * v - (N - 1))
                * (
                    (2 * u - (N - 1)) ** 2
                    - (2 * v - (N - 1)) ** 2
                )
                * variable
                for (u, v), variable in cell_variables.items()
            )
        )

    centered = [2 * u - (N - 1) for u in range(M)]
    cell_second_constant = 2 * sum(value**2 for value in centered)
    cell_fourth_constant = 2 * sum(value**4 for value in centered)
    direction_records = []
    occupancy_variables = {}
    for normal in direction_representatives(args.q):
        a, b = normal
        resources = direction_resources(normal)
        variables = []
        for resource in resources:
            variable = model.NewIntVar(
                0,
                resource["capacity"],
                f"d_{a}_{b}_{resource['label']}",
            )
            variables.append(variable)
            occupancy_variables[(normal, resource["label"])] = variable

        # An orbit of noncentral lines contains four lines; a central orbit
        # contains the two perpendicular centered lines.
        model.Add(
            sum(
                resource["orbit_size"] * variable
                for resource, variable in zip(resources, variables)
            )
            # A C4 direction orbit contains two perpendicular parallel-line
            # families, so every grid point has two incidences.
            == 8 * M
        )
        model.Add(
            sum(
                resource["orbit_size"]
                * resource["label"] ** 2
                * variable
                for resource, variable in zip(resources, variables)
            )
            == 4 * (a * a + b * b) * cell_second_constant
        )

        # The line-orbit sum contains both perpendicular direction families,
        # twice the moment for one fixed normal over all lifted points.
        fourth_constant = 4 * (a**4 + b**4) * cell_fourth_constant
        q_coefficient = 48 * a * a * b * b
        t_coefficient = 16 * a * b * (a * a - b * b)
        model.Add(
            sum(
                resource["orbit_size"]
                * resource["label"] ** 4
                * variable
                for resource, variable in zip(resources, variables)
            )
            == fourth_constant + q_coefficient * Q + t_coefficient * T
        )
        direction_records.append(
            {
                "normal": list(normal),
                "resource_count": len(resources),
                "capacity_two_resources": sum(
                    item["capacity"] == 2 for item in resources
                ),
                "capacity_one_resources": sum(
                    item["capacity"] == 1 for item in resources
                ),
                "fourth_Q_coefficient": q_coefficient,
                "fourth_T_coefficient": t_coefficient,
            }
        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071912
    status = solver.Solve(model)
    payload = {
        "parameters": vars(args),
        "status": solver.StatusName(status),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "cell_second_constant": cell_second_constant,
        "cell_fourth_constant": cell_fourth_constant,
        "directions": direction_records,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        payload["shared_moments"] = {
            "Q": solver.Value(Q),
            "T": solver.Value(T),
        }
        payload["occupied_resource_counts"] = {
            f"{normal[0]},{normal[1]}": sum(
                solver.Value(variable) > 0
                for (candidate_normal, _), variable in occupancy_variables.items()
                if candidate_normal == normal
            )
            for normal in direction_representatives(args.q)
        }
        if cell_variables:
            payload["moment_factor_cells"] = [
                list(cell)
                for cell, variable in cell_variables.items()
                if solver.Value(variable)
            ]
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "directions": len(direction_records),
                "branches": payload["branches"],
                "conflicts": payload["conflicts"],
                "wall_s": payload["wall_s"],
                "shared_moments": payload.get("shared_moments"),
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()

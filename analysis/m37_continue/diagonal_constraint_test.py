"""Test whether every 56-defect factor needs a slope +/-1 defect orbit."""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

from ortools.sat.python import cp_model

from signed_nae_core import c4_lifts, geometry_bad_count, oriented_edges


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def slope_type(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    g = math.gcd(abs(dx), abs(dy))
    return tuple(sorted((abs(dx // g), abs(dy // g))))


def collinear_feature(p, q, r):
    det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return None if det else slope_type(p, q)


def enumerate_patterns(m, edges):
    lifts = [(c4_lifts(m, e), c4_lifts(m, e[::-1])) for e in edges]
    patterns = []
    for i, j in itertools.combinations(range(len(edges)), 2):
        for bits in range(4):
            points = lifts[i][bits & 1] + lifts[j][(bits >> 1) & 1]
            slopes = []
            for p, q, r in itertools.combinations(points, 3):
                feature = collinear_feature(p, q, r)
                if feature is not None:
                    slopes.append(feature)
            if slopes:
                patterns.append(((i, j), bits, len(slopes), sorted(set(slopes))))
    for a, b, c in itertools.combinations(range(len(edges)), 3):
        for bits in range(8):
            slopes = []
            for p in lifts[a][bits & 1]:
                for q in lifts[b][(bits >> 1) & 1]:
                    for r in lifts[c][(bits >> 2) & 1]:
                        feature = collinear_feature(p, q, r)
                        if feature is not None:
                            slopes.append(feature)
            if slopes:
                patterns.append(((a, b, c), bits, len(slopes), sorted(set(slopes))))
    return patterns


def solve(m, edges, patterns, time_limit):
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(len(edges))]
    model.Add(x[0] == 0)
    terms = []
    diagonal_patterns = 0
    for index, (vertices, pattern, weight, slopes) in enumerate(patterns):
        wanted = [(pattern >> k) & 1 for k in range(len(vertices))]
        lits = [x[v] if bit else x[v].Not() for v, bit in zip(vertices, wanted)]
        bad = model.NewBoolVar(f"bad{index}")
        model.AddBoolAnd(lits).OnlyEnforceIf(bad)
        model.AddBoolOr([lit.Not() for lit in lits]).OnlyEnforceIf(bad.Not())
        terms.append(weight * bad)
        if (1, 1) in slopes:
            model.Add(bad == 0)
            diagonal_patterns += 1
    model.Minimize(sum(terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    result = {
        "status": solver.StatusName(status),
        "optimal": status == cp_model.OPTIMAL,
        "best_bound": solver.BestObjectiveBound(),
        "diagonal_patterns_forbidden": diagonal_patterns,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        bits = [int(solver.Value(v)) for v in x]
        result.update(
            {
                "bits": bits,
                "weighted_objective": int(round(solver.ObjectiveValue())),
                "geometry": geometry_bad_count(m, edges, bits),
            }
        )
        assert result["weighted_objective"] == result["geometry"]["bad_triples"]
    return result


def main():
    weighted = json.loads(
        (OUT / "weighted_geometry_results.json").read_text(encoding="utf-8")
    )
    cases = [
        {
            "name": item["name"],
            "m": 37,
            "edges": item["edges"],
            "unconstrained_optimum": 56,
        }
        for item in weighted
        if item["weighted_exact"]["violations"] == 56
    ]
    baseline_cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]
    for item in baseline_cases:
        edges, bits = oriented_edges(item)
        cases.append(
            {
                "name": f"control_{item['name']}",
                "m": item["m"],
                "edges": [list(e) for e in edges],
                "control_orientation": bits,
                "unconstrained_optimum": item.get("expected_violations"),
            }
        )
    results = []
    for item in cases:
        print(f"{item['name']}: enumerate diagonal patterns", flush=True)
        edges = [tuple(e) for e in item["edges"]]
        patterns = enumerate_patterns(item["m"], edges)
        solved = solve(item["m"], edges, patterns, 120.0)
        result = {
            "name": item["name"],
            "unconstrained_optimum": item["unconstrained_optimum"],
            "pattern_count": len(patterns),
            "no_slope_1_result": solved,
        }
        results.append(result)
        print(
            f"  {solved['status']} no_diag={solved.get('weighted_objective')} "
            f"bound={solved.get('best_bound')}",
            flush=True,
        )
    (OUT / "diagonal_constraint_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

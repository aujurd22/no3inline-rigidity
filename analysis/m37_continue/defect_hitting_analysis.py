"""Exact hitting sets for the 12 C4 defect orbits of the verified 48 state."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

from ortools.sat.python import cp_model

from defect_orbit_analysis import canonical_triple
from signed_nae_core import c4_lifts


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def defect_owner_sets(edges, bits):
    points = []
    owners = []
    for owner, ((u, v), bit) in enumerate(zip(edges, bits)):
        orbit = c4_lifts(37, (u, v) if bit == 0 else (v, u))
        points.extend(orbit)
        owners.extend([owner] * 4)
    orbits = {}
    for i, j, k in itertools.combinations(range(len(points)), 3):
        p, q, r = points[i], points[j], points[k]
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if not det:
            orbits.setdefault(
                canonical_triple((p, q, r)), tuple(sorted({owners[i], owners[j], owners[k]}))
            )
    return list(orbits.values())


def solve_hitting(edges, defects, independent):
    model = cp_model.CpModel()
    selected = [model.NewBoolVar(f"z{i}") for i in range(len(edges))]
    for defect in defects:
        model.Add(sum(selected[index] for index in defect) >= 1)
    if independent:
        for i, j in itertools.combinations(range(len(edges)), 2):
            if set(edges[i]) & set(edges[j]):
                model.Add(selected[i] + selected[j] <= 1)
    model.Minimize(sum(selected))
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    result = {"status": solver.StatusName(status), "independent": independent}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = [i for i, var in enumerate(selected) if solver.Value(var)]
        result.update(
            {
                "size": len(chosen),
                "indices": chosen,
                "edges": [list(edges[i]) for i in chosen],
                "covered_defects": [
                    [index for index in defect if index in chosen] for defect in defects
                ],
            }
        )
    return result


def max_coverage(edges, defects, independent, budget):
    model = cp_model.CpModel()
    selected = [model.NewBoolVar(f"z{i}") for i in range(len(edges))]
    covered = [model.NewBoolVar(f"c{d}") for d in range(len(defects))]
    model.Add(sum(selected) <= budget)
    for flag, defect in zip(covered, defects):
        model.Add(sum(selected[index] for index in defect) >= flag)
        for index in defect:
            model.Add(flag >= selected[index])
    if independent:
        for i, j in itertools.combinations(range(len(edges)), 2):
            if set(edges[i]) & set(edges[j]):
                model.Add(selected[i] + selected[j] <= 1)
    model.Maximize(sum(covered))
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    chosen = [i for i, var in enumerate(selected) if solver.Value(var)]
    return {
        "budget": budget,
        "independent": independent,
        "covered": int(round(solver.ObjectiveValue())),
        "indices": chosen,
        "edges": [list(edges[i]) for i in chosen],
    }


def main():
    records = json.loads(
        (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    best = next(item for item in records if item["name"] == "m37_weighted_48")
    edges = [tuple(edge) for edge in best["edges"]]
    bits = best["weighted_repeat_exact"]["bits"]
    defects = defect_owner_sets(edges, bits)
    hot = Counter(index for defect in defects for index in defect)
    payload = {
        "edges": best["edges"],
        "bits": bits,
        "defect_owner_sets": [list(defect) for defect in defects],
        "hotness_by_defect_orbit": dict(hot),
        "minimum_hitting_set": solve_hitting(edges, defects, False),
        "minimum_independent_hitting_set": solve_hitting(edges, defects, True),
        "coverage_frontier": [
            max_coverage(edges, defects, independent, budget)
            for independent in (False, True)
            for budget in range(1, 7)
        ],
    }
    (OUT / "defect_hitting_results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print("defects", defects)
    print("minimum", payload["minimum_hitting_set"])
    print("independent", payload["minimum_independent_hitting_set"])
    for item in payload["coverage_frontier"]:
        print(item)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Perfect-matching master search with an exact orientation subproblem."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from directed_cell_lns import canonical_solution, directed_cell, line_components
from signed_nae_core import c4_lifts, geometry_bad_count, validate_factor
from weighted_factor_search import is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def matching_key(matching):
    return tuple(sorted(tuple(sorted(edge)) for edge in matching))


def random_matching(vertices, forbidden, rng):
    vertices = list(vertices)
    for _ in range(1000):
        rng.shuffle(vertices)
        candidate = matching_key(
            (vertices[index], vertices[index + 1])
            for index in range(0, len(vertices), 2)
        )
        if not (set(candidate) & forbidden):
            return candidate
    raise RuntimeError("failed to generate an allowed random matching")


def switch_matching(matching, forbidden, rng):
    matching = list(matching)
    for _ in range(100):
        first, second = rng.sample(range(len(matching)), 2)
        a, b = matching[first]
        c, d = matching[second]
        replacements = [((a, c), (b, d)), ((a, d), (b, c))]
        rng.shuffle(replacements)
        for edge1, edge2 in replacements:
            edge1 = tuple(sorted(edge1))
            edge2 = tuple(sorted(edge2))
            if edge1 in forbidden or edge2 in forbidden:
                continue
            candidate = [edge for index, edge in enumerate(matching) if index not in (first, second)]
            candidate.extend((edge1, edge2))
            return matching_key(candidate)
    return None


def two_switch_neighbors(matching, forbidden):
    neighbors = set()
    matching = list(matching)
    for first, second in itertools.combinations(range(len(matching)), 2):
        a, b = matching[first]
        c, d = matching[second]
        for edge1, edge2 in (((a, c), (b, d)), ((a, d), (b, c))):
            edge1 = tuple(sorted(edge1))
            edge2 = tuple(sorted(edge2))
            if edge1 in forbidden or edge2 in forbidden:
                continue
            candidate = [
                edge for index, edge in enumerate(matching) if index not in (first, second)
            ]
            candidate.extend((edge1, edge2))
            neighbors.add(matching_key(candidate))
    return sorted(neighbors)


def perfect_matchings(vertices):
    vertices = tuple(vertices)
    if not vertices:
        yield ()
        return
    first = vertices[0]
    for index in range(1, len(vertices)):
        second = vertices[index]
        rest = vertices[1:index] + vertices[index + 1 :]
        for suffix in perfect_matchings(rest):
            yield (tuple(sorted((first, second))),) + suffix


def k_switch_neighbors(matching, forbidden, k):
    neighbors = set()
    matching = list(matching)
    for chosen_indices in itertools.combinations(range(len(matching)), k):
        old_edges = {matching[index] for index in chosen_indices}
        vertices = sorted(vertex for index in chosen_indices for vertex in matching[index])
        for replacement in perfect_matchings(vertices):
            replacement = matching_key(replacement)
            if set(replacement) & old_edges:
                continue
            if set(replacement) & forbidden:
                continue
            candidate = [
                edge for index, edge in enumerate(matching) if index not in chosen_indices
            ]
            candidate.extend(replacement)
            neighbors.add(matching_key(candidate))
    return sorted(neighbors)


def three_switch_neighbors(matching, forbidden):
    return k_switch_neighbors(matching, forbidden, 3)


def four_switch_neighbors(matching, forbidden):
    return k_switch_neighbors(matching, forbidden, 4)


def solve_orientation(base, removed_indices, matching, time_limit, workers):
    started = time.time()
    edges = [tuple(edge) for edge in base["edges"]]
    bits = list(base["bits"])
    removed = set(removed_indices)
    fixed_indices = [index for index in range(37) if index not in removed]
    fixed_cells = [directed_cell(edges[index], bits[index]) for index in fixed_indices]
    fixed_points = [point for cell in fixed_cells for point in c4_lifts(37, cell)]

    cells = [cell for u, v in matching for cell in ((u, v), (v, u))]
    variable_points = [c4_lifts(37, cell) for cell in cells]
    model = cp_model.CpModel()
    selected = [model.NewBoolVar(f"cell_{u}_{v}") for u, v in cells]
    for edge_no in range(len(matching)):
        model.Add(selected[2 * edge_no] + selected[2 * edge_no + 1] == 1)

    fixed_plus = Counter(x - y for x, y in fixed_points)
    fixed_minus = Counter(x + y for x, y in fixed_points)
    variable_plus = defaultdict(Counter)
    variable_minus = defaultdict(Counter)
    for index, orbit in enumerate(variable_points):
        for x, y in orbit:
            variable_plus[x - y][index] += 1
            variable_minus[x + y][index] += 1
    for fixed, variable in ((fixed_plus, variable_plus), (fixed_minus, variable_minus)):
        for key in set(fixed) | set(variable):
            model.Add(
                fixed.get(key, 0)
                + sum(count * selected[index] for index, count in variable[key].items())
                <= 2
            )

    pre_solver = cp_model.CpSolver()
    pre_solver.parameters.max_time_in_seconds = min(0.1, time_limit)
    pre_solver.parameters.num_search_workers = 1
    pre_started = time.time()
    pre_status = pre_solver.Solve(model)
    precheck_s = time.time() - pre_started
    if pre_status == cp_model.INFEASIBLE:
        return {
            "status": "INFEASIBLE",
            "matching": [list(edge) for edge in matching],
            "build_s": round(time.time() - started, 4),
            "solve_s": round(precheck_s, 4),
            "diagonal_precheck": "INFEASIBLE",
            "diagonal_precheck_s": round(precheck_s, 4),
            "active_line_costs": 0,
            "raw_line_keys": 0,
            "objective": None,
            "best_bound": None,
        }
    if pre_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for var in selected:
            model.AddHint(var, pre_solver.Value(var))

    points = list(fixed_points)
    owners = [-1] * len(fixed_points)
    for owner, orbit in enumerate(variable_points):
        points.extend(orbit)
        owners.extend([owner] * 4)
    assert len(points) == len(set(points))

    line_constant, components, raw_line_count = line_components(points, owners)
    cost_vars = []
    for line_no, (_, fixed, coefficients, maximum, multiplicity) in enumerate(components):
        occupancy = model.NewIntVar(0, maximum, f"occ_{line_no}")
        model.Add(
            occupancy
            == fixed
            + sum(count * selected[index] for index, count in coefficients.items())
        )
        costs = [
            multiplicity * math.comb(value, 3) if value >= 3 else 0
            for value in range(maximum + 1)
        ]
        cost = model.NewIntVar(0, costs[-1], f"cost_{line_no}")
        model.AddElement(occupancy, costs, cost)
        cost_vars.append(cost)
    model.Minimize(sum(cost_vars) + line_constant)

    build_s = time.time() - started
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = 20260717 + sum(sum(edge) for edge in matching)
    solve_started = time.time()
    status = solver.Solve(model)
    solve_s = time.time() - solve_started
    result = {
        "status": solver.StatusName(status),
        "matching": [list(edge) for edge in matching],
        "build_s": round(build_s, 4),
        "solve_s": round(solve_s, 4),
        "diagonal_precheck": pre_solver.StatusName(pre_status),
        "diagonal_precheck_s": round(precheck_s, 4),
        "active_line_costs": len(components),
        "raw_line_keys": raw_line_count,
        "objective": None,
        "best_bound": None,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen_cells = [cells[index] for index, var in enumerate(selected) if solver.Value(var)]
        candidate_edges, candidate_bits = canonical_solution(fixed_cells + chosen_cells)
        validation = validate_factor(37, candidate_edges)
        geometry = geometry_bad_count(37, candidate_edges, candidate_bits)
        assert validation["is_2factor"]
        assert is_diagonal_safe(candidate_edges)
        assert geometry["bad_triples"] == round(solver.ObjectiveValue())
        result.update(
            {
                "objective": geometry["bad_triples"],
                "best_bound": round(solver.BestObjectiveBound()),
                "edges": [list(edge) for edge in candidate_edges],
                "bits": candidate_bits,
                "geometry": geometry,
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="v40_02")
    parser.add_argument(
        "--indices", default="2,5,7,8,11,13,16,18,20,24,26,29,32"
    )
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--time-limit", type=float, default=2.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--random-restart-rate", type=float, default=0.08)
    parser.add_argument("--enumerate-two-switch", action="store_true")
    parser.add_argument("--enumerate-three-switch", action="store_true")
    parser.add_argument("--enumerate-four-switch", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=1000)
    parser.add_argument("--store-infeasible", action="store_true")
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--out", default="matching_orientation_probe.json")
    args = parser.parse_args()

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    removed_indices = tuple(sorted(int(item) for item in args.indices.split(",")))
    edges = [tuple(edge) for edge in base["edges"]]
    removed = set(removed_indices)
    original_matching = matching_key(edges[index] for index in removed_indices)
    affected = sorted(vertex for edge in original_matching for vertex in edge)
    if len(affected) != len(set(affected)):
        raise ValueError("the removed edges must be an independent matching")
    fixed_edges = {tuple(sorted(edges[index])) for index in range(37) if index not in removed}

    rng = random.Random(args.seed)
    cache = {}
    runs = []
    histogram = Counter()
    payload = {
        "parameters": vars(args),
        "removed_indices": list(removed_indices),
        "affected_vertices": affected,
        "runs": runs,
        "objective_histogram": {},
        "best_candidate": None,
    }
    out_path = OUT / args.out

    current_matching = original_matching
    current_value = None
    best_value = None
    proposals = None
    exhaustive_modes = sum(
        (args.enumerate_two_switch, args.enumerate_three_switch, args.enumerate_four_switch)
    )
    if exhaustive_modes > 1:
        parser.error("choose at most one exhaustive switch mode")
    if args.enumerate_two_switch:
        proposals = [original_matching] + two_switch_neighbors(original_matching, fixed_edges)
        print(f"two-switch proposals={len(proposals)}", flush=True)
    elif args.enumerate_three_switch:
        proposals = [original_matching] + three_switch_neighbors(original_matching, fixed_edges)
        print(f"three-switch proposals={len(proposals)}", flush=True)
    elif args.enumerate_four_switch:
        proposals = [original_matching] + four_switch_neighbors(original_matching, fixed_edges)
        print(f"four-switch proposals={len(proposals)}", flush=True)
    total_iterations = len(proposals) if proposals is not None else args.iterations + 1
    for iteration in range(total_iterations):
        if proposals is not None:
            proposal = proposals[iteration]
        elif iteration == 0:
            proposal = original_matching
        elif rng.random() < args.random_restart_rate:
            proposal = random_matching(affected, fixed_edges, rng)
        else:
            proposal = switch_matching(current_matching, fixed_edges, rng)
            if proposal is None:
                continue
        new_result = proposal not in cache
        if not new_result:
            result = cache[proposal]
        else:
            result = solve_orientation(
                base, removed_indices, proposal, args.time_limit, args.workers
            )
            cache[proposal] = result
            if args.store_infeasible or result["objective"] is not None:
                runs.append({"iteration": iteration, **result})
            key = "INFEASIBLE" if result["objective"] is None else str(result["objective"])
            histogram[key] += 1

        value = result["objective"]
        best_improved = False
        if value is not None:
            temperature = max(1.0, 12.0 * (1.0 - iteration / max(1, args.iterations)))
            accept = (
                current_value is None
                or value <= current_value
                or rng.random() < math.exp((current_value - value) / temperature)
            )
            if accept:
                current_matching = proposal
                current_value = value
            if best_value is None or value < best_value:
                best_value = value
                payload["best_candidate"] = {"iteration": iteration, **result}
                best_improved = True
                print(
                    f"best iteration={iteration} objective={value} "
                    f"bound={result['best_bound']} status={result['status']}",
                    flush=True,
                )

        payload["objective_histogram"] = dict(sorted(histogram.items()))
        payload["unique_matchings"] = len(cache)
        payload["stored_runs"] = len(runs)
        if (
            best_improved
            or iteration == total_iterations - 1
            or (args.checkpoint_every > 0 and iteration % args.checkpoint_every == 0)
        ):
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        progress_every = max(10, args.checkpoint_every)
        if iteration and iteration % progress_every == 0:
            print(
                f"iteration={iteration} unique={len(cache)} current={current_value} "
                f"best={best_value}",
                flush=True,
            )
        if best_value is not None and best_value <= 36:
            print("target reached", flush=True)
            break
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()

"""Joint arbitrary-deletion f-factor and iterative line-cut closure.

This removes the independent-edge restriction from
``solve_joint_rot4_line_cuts.py``.  A vertex can now have deficit 0, 1, or 2;
replacement non-loop cells contribute one at each endpoint and replacement
loops contribute two at their endpoint.  Thus the polynomial core is a genuine
f-factor problem rather than a perfect matching.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from collections import Counter, defaultdict

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS, c4_lifts, directed_cell
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_line_cuts import add_line_capacity, extract_solution


HERE = __import__("pathlib").Path(__file__).resolve().parent


def rotate_line_key(
    key: tuple[int, int, int]
) -> tuple[int, int, int]:
    """Rotate a*x+b*y=c by (x,y)->(2m-1-y,x)."""
    a, b, c = key
    rotated = (-b, a, c - (2 * M - 1) * b)
    if rotated[0] < 0 or (rotated[0] == 0 and rotated[1] < 0):
        rotated = tuple(-value for value in rotated)
    return rotated


def canonical_line_orbit(key: tuple[int, int, int]) -> tuple[int, int, int]:
    orbit = []
    current = key
    for _ in range(4):
        orbit.append(current)
        current = rotate_line_key(current)
    assert current == key
    return min(orbit)


def short_direction_lines(q: int) -> list[tuple[int, int, int]]:
    """All grid lines with >=3 points and primitive normal bounded by q.

    Horizontal and vertical lines are omitted because the rot4 degree equations
    already force exactly two selected points in every row and column.
    """
    if q <= 0:
        return []
    lines = []
    for a in range(q + 1):
        for b in range(-q, q + 1):
            if a == 0 and b <= 0:
                continue
            if a == 0 or b == 0:
                continue
            if math.gcd(abs(a), abs(b)) != 1:
                continue
            counts = Counter(
                a * x + b * y for x in range(2 * M) for y in range(2 * M)
            )
            lines.extend((a, b, c) for c, count in counts.items() if count >= 3)
    # A rot4 orbit variable contributes the same coefficient pattern to all
    # four rotated lines, so retain one canonical representative per orbit.
    return sorted({canonical_line_orbit(key) for key in lines})


def build_general_model(
    base: dict,
    defects: list[list[int]],
    blockers: dict[tuple[int, int], tuple[int, ...]],
    size: int,
    adjacency_count: int | None,
    triple_adjacency_count: int | None,
    loop_count: int | None,
    reselected_count: int | None,
    deficit_two_edge_count: int | None,
    quadruple_adjacency_count: int | None = None,
    forbid_exact_reselection: bool = False,
    forbid_antiparallel: bool = False,
):
    edges = [tuple(edge) for edge in base["edges"]]
    incident_base = defaultdict(list)
    edge_index = {}
    loop_edge_index = {}
    for index, (u, v) in enumerate(edges):
        incident_base[u].append(index)
        incident_base[v].append(index)
        if u == v:
            loop_edge_index[u] = index
        else:
            edge_index[(u, v)] = index

    model = cp_model.CpModel()
    removed = [model.NewBoolVar(f"r_{i}") for i in range(M)]
    model.Add(sum(removed) == size)
    for defect in defects:
        model.Add(sum(removed[i] for i in defect) >= 1)
    adjacent_pairs = []
    for vertex in range(M):
        first, second = incident_base[vertex]
        both = model.NewBoolVar(f"adjacent_removed_at_{vertex}")
        model.Add(both <= removed[first])
        model.Add(both <= removed[second])
        model.Add(both >= removed[first] + removed[second] - 1)
        adjacent_pairs.append(both)
    if adjacency_count is not None:
        model.Add(sum(adjacent_pairs) == adjacency_count)
    triple_windows = []
    for index, (u, v) in enumerate(edges):
        if u == v:
            previous = following = index
        else:
            previous = next(i for i in incident_base[u] if i != index)
            following = next(i for i in incident_base[v] if i != index)
        triple = model.NewBoolVar(f"three_consecutive_removed_at_edge_{index}")
        model.Add(triple <= removed[previous])
        model.Add(triple <= removed[index])
        model.Add(triple <= removed[following])
        model.Add(
            triple
            >= removed[previous] + removed[index] + removed[following] - 2
        )
        triple_windows.append(triple)
    if triple_adjacency_count is not None:
        model.Add(sum(triple_windows) == triple_adjacency_count)
    quadruple_windows = []
    if quadruple_adjacency_count is not None:
        for vertex in range(M):
            first, second = incident_base[vertex]
            overlap = model.NewBoolVar(
                f"overlapping_triple_windows_at_{vertex}"
            )
            model.Add(overlap <= triple_windows[first])
            model.Add(overlap <= triple_windows[second])
            model.Add(
                overlap
                >= triple_windows[first] + triple_windows[second] - 1
            )
            quadruple_windows.append(overlap)
        model.Add(sum(quadruple_windows) == quadruple_adjacency_count)

    cells = []
    selected = []
    loop_variables = []
    cell_variable = {}
    incident_terms = defaultdict(list)
    reselected_terms = []
    exact_reselection_terms = []
    flipped_reselection_terms = []
    reverse_parallel_terms = []
    reverse_parallel_by_old_index = [None] * M
    antiparallel_pair_terms = []
    deficit_two_edge_terms = []

    # A loop is one C4 fundamental orbit and contributes degree two.
    for u in range(M):
        cell = (u, u)
        variable = model.NewBoolVar(f"x_{u}_{u}")
        cells.append(cell)
        selected.append(variable)
        loop_variables.append(variable)
        cell_variable[cell] = variable
        incident_terms[u].append(2 * variable)
        for blocker in blockers[cell]:
            model.Add(
                variable
                <= sum(removed[i] for i in range(M) if (blocker >> i) & 1)
            )
        if u in loop_edge_index:
            old_index = loop_edge_index[u]
            model.Add(variable <= removed[old_index])
            exact_reselection_terms.append(variable)
            reselected_terms.append(variable)
            if forbid_exact_reselection:
                model.Add(variable == 0)
    if loop_count is not None:
        model.Add(sum(loop_variables) == loop_count)

    # A non-loop underlying edge has two geometrically distinct orientations.
    # Both may be selected: their C4 lifts are disjoint and form the two
    # parallel edges of a reduced 2-cycle.  ``forbid_antiparallel`` exists
    # only to reproduce the obsolete simple-underlying-graph relaxation.
    for u, v in itertools.combinations(range(M), 2):
        pair = []
        for cell in ((u, v), (v, u)):
            variable = model.NewBoolVar(f"x_{cell[0]}_{cell[1]}")
            cells.append(cell)
            selected.append(variable)
            cell_variable[cell] = variable
            pair.append(variable)
            incident_terms[u].append(variable)
            incident_terms[v].append(variable)
            for blocker in blockers[cell]:
                model.Add(
                    variable
                    <= sum(
                        removed[i] for i in range(M) if (blocker >> i) & 1
                    )
                )
        if forbid_antiparallel:
            model.Add(sum(pair) <= 1)
        both_orientations = model.NewBoolVar(
            f"both_orientations_selected_{u}_{v}"
        )
        model.Add(both_orientations <= pair[0])
        model.Add(both_orientations <= pair[1])
        model.Add(both_orientations >= pair[0] + pair[1] - 1)
        antiparallel_pair_terms.append(both_orientations)
        if deficit_two_edge_count is not None:
            edge_used = model.NewBoolVar(f"underlying_edge_{u}_{v}_used")
            model.Add(edge_used >= pair[0])
            model.Add(edge_used >= pair[1])
            model.Add(edge_used <= sum(pair))
            both_deficit_two = model.NewBoolVar(
                f"edge_{u}_{v}_joins_two_deficit2"
            )
            model.Add(both_deficit_two <= edge_used)
            model.Add(both_deficit_two <= adjacent_pairs[u])
            model.Add(both_deficit_two <= adjacent_pairs[v])
            model.Add(
                both_deficit_two >= (
                    edge_used + adjacent_pairs[u] + adjacent_pairs[v] - 2
                )
            )
            deficit_two_edge_terms.append(both_deficit_two)
        if (u, v) in edge_index:
            old_index = edge_index[(u, v)]
            old_cell = directed_cell((u, v), base["bits"][old_index])
            old_variable = cell_variable[old_cell]
            flipped_variable = cell_variable[(old_cell[1], old_cell[0])]
            # Identically re-adding an old directed cell requires deleting its
            # old copy.  The reversed orbit, however, may legitimately be
            # added while the old orientation is retained, producing the
            # two parallel edges of a 2-cycle.
            model.Add(old_variable <= removed[old_index])
            actual_flip = model.NewBoolVar(
                f"old_edge_{old_index}_actually_flipped"
            )
            model.Add(actual_flip <= flipped_variable)
            model.Add(actual_flip <= removed[old_index])
            model.Add(
                actual_flip >= flipped_variable + removed[old_index] - 1
            )
            exact_reselection_terms.append(old_variable)
            flipped_reselection_terms.append(actual_flip)
            reverse_parallel_terms.append(flipped_variable)
            reverse_parallel_by_old_index[old_index] = flipped_variable
            reselected_terms.extend([old_variable, actual_flip])
            if forbid_exact_reselection:
                model.Add(old_variable == 0)
    if reselected_count is not None:
        model.Add(sum(reselected_terms) == reselected_count)
    if deficit_two_edge_count is not None:
        model.Add(sum(deficit_two_edge_terms) == deficit_two_edge_count)

    for vertex in range(M):
        model.Add(
            sum(incident_terms[vertex])
            == sum(removed[i] for i in incident_base[vertex])
        )
    # Redundant but useful for presolve and for documenting the orbit count.
    model.Add(sum(selected) == size)

    base_cells = [
        directed_cell(edge, bit) for edge, bit in zip(edges, base["bits"])
    ]
    assert all(
        variable is not None or edges[index][0] == edges[index][1]
        for index, variable in enumerate(reverse_parallel_by_old_index)
    )
    return {
        "model": model,
        "edges": edges,
        "removed": removed,
        "cells": cells,
        "selected": selected,
        "cell_variable": cell_variable,
        "base_cells": base_cells,
        "base_orbits": [c4_lifts(cell) for cell in base_cells],
        "candidate_orbits": {cell: c4_lifts(cell) for cell in cells},
        "adjacent_pairs": adjacent_pairs,
        "triple_windows": triple_windows,
        "quadruple_windows": quadruple_windows,
        "loop_variables": loop_variables,
        "reselected_terms": reselected_terms,
        "exact_reselection_terms": exact_reselection_terms,
        "flipped_reselection_terms": flipped_reselection_terms,
        "reverse_parallel_terms": reverse_parallel_terms,
        "reverse_parallel_by_old_index": reverse_parallel_by_old_index,
        "antiparallel_pair_terms": antiparallel_pair_terms,
        "deficit_two_edge_terms": deficit_two_edge_terms,
        "forbid_antiparallel": forbid_antiparallel,
    }


def solve_general_with_cuts(
    base: dict,
    defects: list[list[int]],
    blockers: dict[tuple[int, int], tuple[int, ...]],
    size: int,
    max_rounds: int,
    per_round_time: float,
    total_time: float,
    workers: int,
    short_direction_q: int,
    adjacency_count: int | None,
    triple_adjacency_count: int | None,
    loop_count: int | None,
    reselected_count: int | None,
    deficit_two_edge_count: int | None,
    extra_line_keys: list[tuple[int, int, int]] | None = None,
    quadruple_adjacency_count: int | None = None,
    forbid_exact_reselection: bool = False,
    fixed_removed_indices: list[int] | None = None,
) -> dict:
    started = time.time()
    problem = build_general_model(
        base,
        defects,
        blockers,
        size,
        adjacency_count,
        triple_adjacency_count,
        loop_count,
        reselected_count,
        deficit_two_edge_count,
        quadruple_adjacency_count,
        forbid_exact_reselection,
    )
    if fixed_removed_indices is not None:
        fixed_removed = set(fixed_removed_indices)
        for index, variable in enumerate(problem["removed"]):
            problem["model"].Add(variable == (index in fixed_removed))
    preseeded_lines = sorted(
        set(short_direction_lines(short_direction_q))
        | {
            canonical_line_orbit(tuple(key))
            for key in (extra_line_keys or [])
        }
    )
    known_lines = set(preseeded_lines)
    for key in preseeded_lines:
        add_line_capacity(problem, key)
    rounds = []
    best_bad_lines = None
    best_solution = None
    final_status = "ROUND_LIMIT"
    for round_no in range(1, max_rounds + 1):
        remaining = total_time - (time.time() - started)
        if remaining <= 0:
            final_status = "TOTAL_TIME_LIMIT"
            break
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(per_round_time, remaining)
        solver.parameters.num_search_workers = workers
        solver.parameters.random_seed = 2026071904 + size * 1000 + round_no
        status = solver.Solve(problem["model"])
        record = {
            "round": round_no,
            "status": solver.StatusName(status),
            "wall_s": round(solver.WallTime(), 3),
            "branches": solver.NumBranches(),
            "conflicts": solver.NumConflicts(),
            "known_line_cuts_before": len(known_lines),
        }
        if status == cp_model.INFEASIBLE:
            final_status = "INFEASIBLE"
            rounds.append(record)
            break
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            final_status = solver.StatusName(status)
            rounds.append(record)
            break

        solution = extract_solution(problem, solver)
        record["bad_line_count"] = solution["bad_line_count"]
        if best_bad_lines is None or solution["bad_line_count"] < best_bad_lines:
            best_bad_lines = solution["bad_line_count"]
            best_solution = solution
        if solution["exact"]:
            final_status = "EXACT_SOLUTION"
            rounds.append(record)
            best_solution = solution
            break

        new_lines = [
            canonical_line_orbit(tuple(key))
            for key in solution["bad_lines"]
            if canonical_line_orbit(tuple(key)) not in known_lines
        ]
        new_lines = sorted(set(new_lines))
        for key in new_lines:
            known_lines.add(key)
            add_line_capacity(problem, key)
        record["new_line_cuts"] = len(new_lines)
        record["known_line_cuts_after"] = len(known_lines)
        rounds.append(record)
        if not new_lines:
            final_status = "NO_NEW_CUT_BUG"
            break
        if round_no == 1 or round_no % 10 == 0:
            print(
                f"      round={round_no} bad_lines={solution['bad_line_count']} "
                f"new={len(new_lines)} cuts={len(known_lines)} "
                f"best={best_bad_lines}",
                flush=True,
            )
    return {
        "size": size,
        "status": final_status,
        "round_count": len(rounds),
        "line_cut_count": len(known_lines),
        "preseeded_line_count": len(preseeded_lines),
        "dynamic_line_cut_count": len(known_lines) - len(preseeded_lines),
        "short_direction_q": short_direction_q,
        "adjacency_count": adjacency_count,
        "triple_adjacency_count": triple_adjacency_count,
        "loop_count": loop_count,
        "reselected_count": reselected_count,
        "deficit_two_edge_count": deficit_two_edge_count,
        "quadruple_adjacency_count": quadruple_adjacency_count,
        "forbid_exact_reselection": forbid_exact_reselection,
        "fixed_removed_indices": fixed_removed_indices,
        "line_keys": [list(key) for key in sorted(known_lines)],
        "best_bad_line_count": best_bad_lines,
        "best_solution": best_solution,
        "rounds": rounds,
        "elapsed_s": round(time.time() - started, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bases", default="all")
    parser.add_argument("--min-size", type=int, default=5)
    parser.add_argument("--max-size", type=int, default=13)
    parser.add_argument("--max-rounds", type=int, default=300)
    parser.add_argument("--per-round-time", type=float, default=15.0)
    parser.add_argument("--total-time", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--short-direction-q",
        type=int,
        default=0,
        help="preload every non-axis primitive grid-line family with max(|a|,|b|)<=q",
    )
    parser.add_argument(
        "--adjacency-count",
        type=int,
        default=None,
        help="fix the number of base-factor vertices incident with two removed edges",
    )
    parser.add_argument(
        "--triple-adjacency-count",
        type=int,
        default=None,
        help="fix the number of three-consecutive-removed-edge windows",
    )
    parser.add_argument(
        "--loop-count",
        type=int,
        default=None,
        help="fix the number of replacement loop cells",
    )
    parser.add_argument(
        "--reselected-count",
        type=int,
        default=None,
        help="fix replacement edges whose unordered endpoints equal a removed base edge",
    )
    parser.add_argument(
        "--deficit-two-edge-count",
        type=int,
        default=None,
        help="fix selected non-loop edges joining two deficit-2 vertices",
    )
    parser.add_argument("--quadruple-adjacency-count", type=int, default=None)
    parser.add_argument("--forbid-exact-reselection", action="store_true")
    parser.add_argument("--out", default="joint_rot4_general_factor.json")
    args = parser.parse_args()

    wanted = (
        {f"v40_{i:02d}" for i in range(1, 5)}
        if args.bases == "all"
        else set(args.bases.split(","))
    )
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [item for item in archive["archive"] if item["id"] in wanted]
    payload = {"parameters": vars(args), "bases": []}
    output = HERE / args.out
    for base in sorted(bases, key=lambda item: item["id"]):
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        print(f"{base['id']}: precomputing blockers", flush=True)
        blockers = candidate_blockers(base)
        lower = max(
            args.min_size, hitting["minimum_hitting_set"]["size"]
        )
        base_result = {"base": base["id"], "runs": []}
        for size in range(lower, args.max_size + 1):
            print(f"  general k={size}", flush=True)
            result = solve_general_with_cuts(
                base,
                hitting["defect_owner_sets"],
                blockers,
                size,
                args.max_rounds,
                args.per_round_time,
                args.total_time,
                args.workers,
                args.short_direction_q,
                args.adjacency_count,
                args.triple_adjacency_count,
                args.loop_count,
                args.reselected_count,
                args.deficit_two_edge_count,
                None,
                args.quadruple_adjacency_count,
                args.forbid_exact_reselection,
            )
            base_result["runs"].append(result)
            print(
                f"    status={result['status']} rounds={result['round_count']} "
                f"cuts={result['line_cut_count']} "
                f"best_bad={result['best_bad_line_count']} "
                f"elapsed={result['elapsed_s']}s",
                flush=True,
            )
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if result["status"] == "EXACT_SOLUTION":
                break
            if result["status"] not in ("INFEASIBLE",):
                break
        payload["bases"].append(base_result)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

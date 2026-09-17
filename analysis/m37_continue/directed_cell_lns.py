"""Exact directed-cell LNS around the verified V=40 factors.

Unlike endpoint matching repairs, a neighborhood may contain adjacent factor
edges.  Removing k edges creates residual degrees on their incident vertices;
CP-SAT may select any oriented cells on those vertices that restore degree 2.
FDR diagonal capacities and the exact line-by-line geometric triple count are
encoded directly.
"""

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

from defect_hitting_analysis import defect_owner_sets, max_coverage
from signed_nae_core import c4_lifts, geometry_bad_count, line_key, validate_factor
from weighted_factor_search import is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def directed_cell(edge, bit):
    u, v = edge
    return (u, v) if bit == 0 else (v, u)


def canonical_solution(cells):
    items = []
    for u, v in cells:
        if u < v:
            items.append(((u, v), 0))
        else:
            items.append(((v, u), 1))
    items.sort()
    return [edge for edge, _ in items], [bit for _, bit in items]


def factor_key(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def rotate_line_key(key):
    """Rotate a*x+b*y=c by (x,y)->(73-y,x), preserving canonical sign."""
    a, b, c = key
    rotated = (-b, a, c - 73 * b)
    if rotated[0] < 0 or (rotated[0] == 0 and rotated[1] < 0):
        rotated = tuple(-value for value in rotated)
    return rotated


def line_orbit(key):
    orbit = []
    current = key
    for _ in range(4):
        orbit.append(current)
        current = rotate_line_key(current)
    assert current == key
    return tuple(sorted(set(orbit)))


def line_components(points, owners):
    masks = {}
    for i, j in itertools.combinations(range(len(points)), 2):
        key = line_key(points[i], points[j])
        masks[key] = masks.get(key, 0) | (1 << i) | (1 << j)
    components = []
    constant = 0
    processed = set()

    def signature(mask):
        if mask.bit_count() < 3:
            return None
        fixed = 0
        coefficients = Counter()
        work = mask
        while work:
            low = work & -work
            index = low.bit_length() - 1
            owner = owners[index]
            if owner < 0:
                fixed += 1
            else:
                coefficients[owner] += 1
            work ^= low
        return fixed, dict(coefficients)

    for key, mask in masks.items():
        orbit = line_orbit(key)
        canonical = orbit[0]
        if canonical in processed:
            continue
        processed.add(canonical)
        signatures = [signature(masks.get(rotated, 0)) for rotated in orbit]
        nonempty = [item for item in signatures if item is not None]
        if not nonempty:
            continue
        assert len(nonempty) == len(orbit)
        assert all(item == nonempty[0] for item in nonempty[1:]), (orbit, nonempty)
        fixed, coefficients = nonempty[0]
        maximum = fixed + sum(coefficients.values())
        if maximum < 3:
            continue
        if not coefficients:
            constant += len(orbit) * math.comb(fixed, 3)
        else:
            components.append((canonical, fixed, coefficients, maximum, len(orbit)))
    return constant, components, len(masks)


def solve_neighborhood(
    base,
    removed_indices,
    target,
    time_limit,
    solver_workers=8,
    branch_parts=1,
    branch_index=0,
    target_exact=False,
    branch_path=None,
    max_retained_original=None,
):
    started = time.time()
    edges = [tuple(edge) for edge in base["edges"]]
    bits = list(base["bits"])
    removed = set(removed_indices)
    fixed_indices = [index for index in range(37) if index not in removed]
    fixed_edges = {edges[index] for index in fixed_indices}
    residual = Counter(
        vertex for index in removed_indices for vertex in edges[index]
    )
    affected = sorted(residual)

    cells = []
    edge_to_cells = defaultdict(list)
    for u, v in itertools.combinations(affected, 2):
        edge = (u, v)
        if edge in fixed_edges:
            continue
        for cell in ((u, v), (v, u)):
            index = len(cells)
            cells.append(cell)
            edge_to_cells[edge].append(index)

    model = cp_model.CpModel()
    selected = [model.NewBoolVar(f"cell_{u}_{v}") for u, v in cells]
    for edge, indices in edge_to_cells.items():
        model.Add(sum(selected[index] for index in indices) <= 1)
    for vertex in affected:
        incident = [
            selected[index]
            for index, (u, v) in enumerate(cells)
            if vertex == u or vertex == v
        ]
        model.Add(sum(incident) == residual[vertex])

    if max_retained_original is not None:
        retained_original = [
            selected[cell_index]
            for index in removed_indices
            for cell_index in edge_to_cells[tuple(sorted(edges[index]))]
        ]
        model.Add(sum(retained_original) <= max_retained_original)

    branches = []
    if branch_parts > 1:
        if branch_path is None:
            branch_path = (branch_index,)
        branch_vertices = [vertex for vertex in affected if residual[vertex] == 1]
        if len(branch_path) > len(branch_vertices):
            raise ValueError("branch path is longer than the eligible vertex list")
        for branch_vertex, path_index in zip(branch_vertices, branch_path):
            partner_edges = sorted(edge for edge in edge_to_cells if branch_vertex in edge)
            groups = [partner_edges[index::branch_parts] for index in range(branch_parts)]
            if not (0 <= path_index < branch_parts) or not groups[path_index]:
                raise ValueError("invalid or empty branch group")
            branch_vars = [
                selected[cell_index]
                for edge in groups[path_index]
                for cell_index in edge_to_cells[edge]
            ]
            model.Add(sum(branch_vars) == 1)
            branches.append(
                {
                    "vertex": branch_vertex,
                    "parts": branch_parts,
                    "index": path_index,
                    "partner_edges": [list(edge) for edge in groups[path_index]],
                }
            )

    fixed_cells = [directed_cell(edges[index], bits[index]) for index in fixed_indices]
    fixed_points = [point for cell in fixed_cells for point in c4_lifts(37, cell)]
    variable_points = [c4_lifts(37, cell) for cell in cells]

    # Diagonal/FDR capacity is a hard constraint.
    fixed_plus = Counter(x - y for x, y in fixed_points)
    fixed_minus = Counter(x + y for x, y in fixed_points)
    variable_plus = defaultdict(Counter)
    variable_minus = defaultdict(Counter)
    for index, orbit in enumerate(variable_points):
        for x, y in orbit:
            variable_plus[x - y][index] += 1
            variable_minus[x + y][index] += 1
    diagonal_constraints = 0
    for fixed, variable in ((fixed_plus, variable_plus), (fixed_minus, variable_minus)):
        for key in set(fixed) | set(variable):
            model.Add(
                fixed.get(key, 0)
                + sum(count * selected[index] for index, count in variable[key].items())
                <= 2
            )
            diagonal_constraints += 1

    points = list(fixed_points)
    owners = [-1] * len(fixed_points)
    for owner, orbit in enumerate(variable_points):
        points.extend(orbit)
        owners.extend([owner] * 4)
    assert len(points) == len(set(points)), "directed-cell orbit overlap"

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
    total_cost = sum(cost_vars) + line_constant
    model.Minimize(total_cost)
    if target is not None:
        if target_exact:
            model.Add(total_cost == target)
        else:
            model.Add(total_cost <= target)

    current_cells = {
        directed_cell(edges[index], bits[index]) for index in removed_indices
    }
    for index, cell in enumerate(cells):
        model.AddHint(selected[index], int(cell in current_cells))

    build_elapsed = time.time() - started
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = solver_workers
    solver.parameters.random_seed = 20260717 + sum(removed_indices)
    solve_started = time.time()
    status = solver.Solve(model)
    solve_elapsed = time.time() - solve_started
    result = {
        "status": solver.StatusName(status),
        "removed_indices": list(removed_indices),
        "removed_edges": [list(edges[index]) for index in removed_indices],
        "affected_vertices": affected,
        "residual_degree_histogram": dict(Counter(residual.values())),
        "directed_cell_variables": len(cells),
        "fixed_point_count": len(fixed_points),
        "potential_point_count": len(points),
        "raw_line_keys": raw_line_count,
        "active_line_costs": len(components),
        "fixed_line_constant": line_constant,
        "diagonal_constraints": diagonal_constraints,
        "branch": branches[0] if len(branches) == 1 else None,
        "branches": branches,
        "target": target,
        "target_exact": target_exact,
        "max_retained_original": max_retained_original,
        "build_s": round(build_elapsed, 3),
        "solve_s": round(solve_elapsed, 3),
        "best_bound": None,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen_cells = [cells[index] for index, var in enumerate(selected) if solver.Value(var)]
        all_cells = fixed_cells + chosen_cells
        candidate_edges, candidate_bits = canonical_solution(all_cells)
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
    elif status == cp_model.INFEASIBLE:
        # An exact-target contradiction does not by itself exclude lower values.
        result["best_bound"] = (
            target + 1 if target is not None and not target_exact else None
        )
    return result


def grow_set(edges, defects, hotness, k, rng, mode):
    all_indices = set(range(37))
    if mode == 0:
        chosen = set(max_coverage(edges, defects, False, k)["indices"])
    elif mode == 1:
        defect = rng.choice(defects)
        chosen = set(defect)
    elif mode == 2:
        cold = sorted(range(37), key=lambda index: (hotness[index], rng.random()))
        # Force at least one current defect to be removable, then use the rest
        # of the budget to expose cold edges that defect-only repair ignores.
        defect = rng.choice(defects)
        chosen = {cold[0], rng.choice(defect)}
    elif mode == 4:
        # A wide endpoint neighborhood: cover defects with independent edges
        # and keep adding disjoint edges where possible.
        chosen = set(max_coverage(edges, defects, True, k)["indices"])
    else:
        chosen = {rng.randrange(37)}
    while len(chosen) < k:
        covered_now = sum(bool(chosen & set(defect)) for defect in defects)
        scored = []
        chosen_vertices = {vertex for index in chosen for vertex in edges[index]}
        for index in all_indices - chosen:
            trial = chosen | {index}
            gain = sum(bool(trial & set(defect)) for defect in defects) - covered_now
            adjacent = len(set(edges[index]) & chosen_vertices)
            if mode == 2:
                score = -4 * hotness[index] + 2 * adjacent + rng.random()
            elif mode == 4:
                score = 8 * gain + 20 * (adjacent == 0) + rng.random()
            else:
                score = 8 * gain + 3 * adjacent + hotness[index] + rng.random()
            scored.append((score, index))
        chosen.add(max(scored)[1])
    return tuple(sorted(chosen))


def make_neighborhoods(base, k, iterations, seed, modes):
    edges = [tuple(edge) for edge in base["edges"]]
    defects = [tuple(item) for item in defect_owner_sets(edges, base["bits"])]
    hotness = Counter(index for defect in defects for index in defect)
    rng = random.Random(seed)
    neighborhoods = []
    seen = set()
    attempts = 0
    while len(neighborhoods) < iterations and attempts < iterations * 20:
        removed = grow_set(edges, defects, hotness, k, rng, modes[attempts % len(modes)])
        attempts += 1
        if removed in seen:
            continue
        seen.add(removed)
        selected = set(removed)
        neighborhoods.append(
            {
                "indices": removed,
                "covered_defects": sum(bool(selected & set(defect)) for defect in defects),
                "owner_union": sorted(set().union(*(set(defect) for defect in defects if selected & set(defect)))),
            }
        )
    return defects, neighborhoods


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bases", default="all", help="all or comma-separated archive ids")
    parser.add_argument("--k", type=int, default=7)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument(
        "--indices",
        default="",
        help="explicit comma-separated removed edge indices (bypasses neighborhood generation)",
    )
    parser.add_argument("--target", type=int, default=36)
    parser.add_argument(
        "--target-exact",
        action="store_true",
        help="require objective == target instead of objective <= target",
    )
    parser.add_argument("--time-limit", type=float, default=45.0)
    parser.add_argument("--solver-workers", type=int, default=8)
    parser.add_argument("--branch-parts", type=int, default=1)
    parser.add_argument("--branch-index", type=int, default=0)
    parser.add_argument(
        "--branch-path",
        default="",
        help="comma-separated group indices for successive residual-degree-one vertices",
    )
    parser.add_argument(
        "--max-retained-original",
        type=int,
        default=None,
        help="upper bound on retained edges among the explicitly removed base edges",
    )
    parser.add_argument(
        "--modes",
        default="0,1,2,3,4",
        help="neighborhood modes: 0 max-cover, 1 defect-grown, 2 cold-mix, 3 connected, 4 wide-independent",
    )
    parser.add_argument("--out", default="directed_cell_lns.json")
    args = parser.parse_args()
    target_value = None if args.target < 0 else args.target
    if args.target_exact and target_value is None:
        parser.error("--target-exact requires a non-negative --target")
    branch_path = (
        tuple(int(item) for item in args.branch_path.split(","))
        if args.branch_path
        else None
    )
    if branch_path is not None and args.branch_parts <= 1:
        parser.error("--branch-path requires --branch-parts > 1")
    explicit_indices = (
        tuple(sorted(int(item) for item in args.indices.split(",")))
        if args.indices
        else None
    )
    if explicit_indices is not None:
        if len(set(explicit_indices)) != len(explicit_indices):
            parser.error("--indices contains duplicates")
        if any(index not in range(37) for index in explicit_indices):
            parser.error("--indices must be in 0..36")

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    v40 = [item for item in archive["archive"] if item["value"] == 40]
    if args.bases == "all":
        bases = v40
    else:
        wanted = set(args.bases.split(","))
        bases = [item for item in v40 if item["id"] in wanted]
    if not bases:
        raise ValueError("no matching V=40 bases")

    modes = tuple(int(item) for item in args.modes.split(","))
    if not modes or any(mode not in range(5) for mode in modes):
        raise ValueError("modes must be chosen from 0,1,2,3,4")
    payload = {"parameters": vars(args), "runs": [], "best_candidate": None}
    out_path = OUT / args.out
    for base_no, base in enumerate(bases):
        if explicit_indices is None:
            defects, neighborhoods = make_neighborhoods(
                base, args.k, args.iterations, 202607175000 + base_no, modes
            )
        else:
            edges = [tuple(edge) for edge in base["edges"]]
            defects = [tuple(item) for item in defect_owner_sets(edges, base["bits"])]
            selected_indices = set(explicit_indices)
            neighborhoods = [
                {
                    "indices": explicit_indices,
                    "covered_defects": sum(
                        bool(selected_indices & set(defect)) for defect in defects
                    ),
                    "owner_union": sorted(
                        set().union(
                            *(
                                set(defect)
                                for defect in defects
                                if selected_indices & set(defect)
                            )
                        )
                    ),
                }
            ]
        print(
            f"base={base['id']} defects={len(defects)} neighborhoods={len(neighborhoods)}",
            flush=True,
        )
        for neighborhood_no, neighborhood in enumerate(neighborhoods, 1):
            print(
                f"  run={neighborhood_no}/{len(neighborhoods)} "
                f"k={len(neighborhood['indices'])} "
                f"covered={neighborhood['covered_defects']} "
                f"indices={neighborhood['indices']}",
                flush=True,
            )
            solve = solve_neighborhood(
                base,
                neighborhood["indices"],
                target_value,
                args.time_limit,
                args.solver_workers,
                args.branch_parts,
                args.branch_index,
                args.target_exact,
                branch_path,
                args.max_retained_original,
            )
            record = {
                "base": base["id"],
                "base_sources": base["sources"],
                "covered_defects": neighborhood["covered_defects"],
                "solve": solve,
            }
            payload["runs"].append(record)
            if solve.get("objective") is not None:
                best = payload["best_candidate"]
                if best is None or solve["objective"] < best["solve"]["objective"]:
                    payload["best_candidate"] = record
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(
                f"    status={solve['status']} objective={solve.get('objective')} "
                f"bound={solve.get('best_bound')} vars={solve['directed_cell_variables']} "
                f"active_lines={solve['active_line_costs']} "
                f"build={solve['build_s']}s solve={solve['solve_s']}s",
                flush=True,
            )
            if target_value is not None and solve.get("objective", 10**9) <= target_value:
                print("target reached", flush=True)
                print(out_path)
                return
    print(out_path)


if __name__ == "__main__":
    main()

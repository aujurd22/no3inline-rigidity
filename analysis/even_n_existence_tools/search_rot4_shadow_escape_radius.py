"""Search the independent-deletion radius at which an m=37 shadow factor appears.

This is the buffered continuation of ``analyze_rot4_shadow_factor.py``.  For
each verified V=40 basin, candidate-orbit blockers are precomputed relative to
the 37 base C4 orbits.  A candidate oriented cell is safe after deleting R iff
R hits every one- or two-owner blocker of that cell.  This turns repeated
geometric checks into small bit-mask tests.

The script first scans random independent supersets of minimum defect-hitting
sets.  With ``--exact-through K`` it then enumerates *all* independent
defect-hitting sets of every size through K, so a missing shadow factor at
those sizes is a certificate rather than a sampling observation.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import time
from collections import defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import (
    M,
    SOURCE_OUTPUTS,
    c4_lifts,
    directed_cell,
    enumerate_minimum_independent_hitting_sets,
    line_key,
    perfect_matching,
    safe_add_orbit,
)


HERE = Path(__file__).resolve().parent


def candidate_blockers(base: dict) -> dict[tuple[int, int], tuple[int, ...]]:
    """All minimal base-owner masks that block one directed C4 cell."""
    edges = [tuple(edge) for edge in base["edges"]]
    points = []
    owners = []
    for owner, (edge, bit) in enumerate(zip(edges, base["bits"])):
        orbit = c4_lifts(directed_cell(edge, bit))
        points.extend(orbit)
        owners.extend([owner] * len(orbit))
    point_owners = defaultdict(set)
    for point, owner in zip(points, owners):
        point_owners[point].add(owner)

    result = {}
    for u in range(M):
        for v in range(M):
            orbit = c4_lifts((u, v))
            blockers: set[int] = set()

            # Point overlap is permitted only if the old owner is deleted.
            for q in orbit:
                blockers.update(1 << owner for owner in point_owners.get(q, ()))

            # One new point plus a secant pair of base points.
            for q in orbit:
                groups = defaultdict(list)
                for p, owner in zip(points, owners):
                    key = line_key(q, p)
                    if key is not None:
                        groups[key].append(owner)
                for group in groups.values():
                    for first, second in itertools.combinations(group, 2):
                        blockers.add((1 << first) | (1 << second))

            # Two new points plus one base point.
            for q, r in itertools.combinations(orbit, 2):
                key = line_key(q, r)
                assert key is not None
                a, b, c = key
                for (x, y), owner in zip(points, owners):
                    if a * x + b * y == c:
                        blockers.add(1 << owner)

            # No directed fundamental cell encountered here should contain a
            # pure internal collinear triple.  Keep the assertion explicit.
            for p, q, r in itertools.combinations(orbit, 3):
                assert (q[0] - p[0]) * (r[1] - p[1]) != (
                    q[1] - p[1]
                ) * (r[0] - p[0])

            # If A is already a blocker, a superset B adds no condition.
            minimal = tuple(
                sorted(
                    mask
                    for mask in blockers
                    if not any(
                        other != mask and other & mask == other
                        for other in blockers
                    )
                )
            )
            result[(u, v)] = minimal
    return result


def is_cell_safe(blockers: tuple[int, ...], removed_mask: int) -> bool:
    return all(blocker & removed_mask for blocker in blockers)


def shadow_factor(
    edges: list[tuple[int, int]],
    removed_indices: tuple[int, ...],
    blockers: dict[tuple[int, int], tuple[int, ...]],
) -> tuple[tuple[tuple[int, int], ...] | None, dict]:
    removed = set(removed_indices)
    removed_mask = sum(1 << i for i in removed)
    affected = tuple(sorted(vertex for i in removed_indices for vertex in edges[i]))
    if len(affected) != 2 * len(removed_indices) or len(set(affected)) != len(affected):
        raise ValueError("shadow_factor expects an independent deletion set")
    fixed_edges = {edge for i, edge in enumerate(edges) if i not in removed}
    options = {}
    for u, v in itertools.combinations(affected, 2):
        if (u, v) in fixed_edges:
            continue
        oriented = tuple(
            cell
            for cell in ((u, v), (v, u))
            if is_cell_safe(blockers[cell], removed_mask)
        )
        if oriented:
            options[(u, v)] = oriented
    matching = perfect_matching(affected, options)
    return matching, {
        "affected_vertices": list(affected),
        "allowed_edge_count": len(options),
        "allowed_orientation_count": sum(map(len, options.values())),
        "matching": [list(edge) for edge in matching] if matching else None,
        "matching_cells": (
            [list(options[edge][0]) for edge in matching] if matching else None
        ),
    }


def defect_coverage_masks(defects: list[list[int]]) -> tuple[list[int], int]:
    coverage = [
        sum(1 << d for d, defect in enumerate(defects) if i in defect)
        for i in range(M)
    ]
    return coverage, (1 << len(defects)) - 1


def all_independent_hitting_sets(
    edges: list[tuple[int, int]],
    defects: list[list[int]],
    size: int,
):
    coverage, full = defect_coverage_masks(defects)
    for chosen in itertools.combinations(range(M), size):
        vertices = 0
        covered = 0
        for index in chosen:
            u, v = edges[index]
            endpoints = (1 << u) | (1 << v)
            if vertices & endpoints:
                break
            vertices |= endpoints
            covered |= coverage[index]
        else:
            if covered == full:
                yield chosen


def random_independent_extensions(
    edges: list[tuple[int, int]],
    seeds: list[tuple[int, ...]],
    size: int,
    limit: int,
    rng: random.Random,
) -> list[tuple[int, ...]]:
    results = set()
    attempts = 0
    while len(results) < limit and attempts < 50 * limit:
        attempts += 1
        chosen = set(rng.choice(seeds))
        vertices = {vertex for i in chosen for vertex in edges[i]}
        candidates = [
            i
            for i, edge in enumerate(edges)
            if i not in chosen and not (set(edge) & vertices)
        ]
        rng.shuffle(candidates)
        for index in candidates:
            if len(chosen) == size:
                break
            if set(edges[index]) & vertices:
                continue
            chosen.add(index)
            vertices.update(edges[index])
        if len(chosen) == size:
            results.add(tuple(sorted(chosen)))
    return sorted(results)


def verify_blocker_oracle(
    base: dict,
    blockers: dict[tuple[int, int], tuple[int, ...]],
    deletion_sets: list[tuple[int, ...]],
) -> None:
    edges = [tuple(edge) for edge in base["edges"]]
    bits = base["bits"]
    for removed_indices in deletion_sets[: min(4, len(deletion_sets))]:
        removed = set(removed_indices)
        removed_mask = sum(1 << i for i in removed)
        retained = [
            point
            for i in range(M)
            if i not in removed
            for point in c4_lifts(directed_cell(edges[i], bits[i]))
        ]
        affected = sorted(vertex for i in removed_indices for vertex in edges[i])
        for u, v in itertools.combinations(affected, 2):
            for cell in ((u, v), (v, u)):
                fast = is_cell_safe(blockers[cell], removed_mask)
                direct = safe_add_orbit(retained, c4_lifts(cell))
                assert fast == direct, (base["id"], removed_indices, cell, fast, direct)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-per-size", type=int, default=500)
    parser.add_argument("--max-size", type=int, default=18)
    parser.add_argument(
        "--exact-through",
        type=int,
        default=0,
        help="exhaust all independent hitting sets through this deletion size",
    )
    parser.add_argument("--out", default="rot4_shadow_escape_radius.json")
    args = parser.parse_args()

    started = time.time()
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [
        item
        for item in archive["archive"]
        if item["id"] in {f"v40_{i:02d}" for i in range(1, 5)}
    ]
    rng = random.Random(2026071901)
    payload = {"parameters": vars(args), "bases": []}
    for base in sorted(bases, key=lambda item: item["id"]):
        base_started = time.time()
        base_id = base["id"]
        edges = [tuple(edge) for edge in base["edges"]]
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base_id}.json").read_text(
                encoding="utf-8"
            )
        )
        defects = hitting["defect_owner_sets"]
        minimum = hitting["minimum_independent_hitting_set"]["size"]
        seeds = enumerate_minimum_independent_hitting_sets(edges, defects, minimum)
        print(f"{base_id}: precomputing candidate blockers", flush=True)
        blockers = candidate_blockers(base)
        verify_blocker_oracle(base, blockers, seeds)
        blocker_sizes = [len(value) for value in blockers.values()]
        base_result = {
            "base": base_id,
            "minimum_independent_hitting_size": minimum,
            "minimum_seed_count": len(seeds),
            "candidate_blocker_count": {
                "min": min(blocker_sizes),
                "max": max(blocker_sizes),
                "average": sum(blocker_sizes) / len(blocker_sizes),
            },
            "random_scan": [],
            "exact_scan": [],
        }

        for size in range(minimum, args.max_size + 1):
            samples = random_independent_extensions(
                edges, seeds, size, args.random_per_size, rng
            )
            feasible = []
            allowed_edges = []
            for chosen in samples:
                matching, detail = shadow_factor(edges, chosen, blockers)
                allowed_edges.append(detail["allowed_edge_count"])
                if matching is not None:
                    feasible.append(
                        {
                            "removed_indices": list(chosen),
                            "removed_edges": [list(edges[i]) for i in chosen],
                            **detail,
                        }
                    )
                    if len(feasible) >= 5:
                        break
            record = {
                "size": size,
                "sample_count": len(samples),
                "tested_until_five_feasible": len(allowed_edges),
                "feasible_count_observed": len(feasible),
                "allowed_edge_min": min(allowed_edges) if allowed_edges else None,
                "allowed_edge_max": max(allowed_edges) if allowed_edges else None,
                "examples": feasible,
            }
            base_result["random_scan"].append(record)
            print(
                f"  random k={size}: samples={len(samples)} "
                f"F0_seen={len(feasible)} "
                f"allowed={record['allowed_edge_min']}.."
                f"{record['allowed_edge_max']}",
                flush=True,
            )

        if args.exact_through:
            for size in range(minimum, args.exact_through + 1):
                count = 0
                feasible = []
                allowed_min = None
                allowed_max = None
                scan_started = time.time()
                for chosen in all_independent_hitting_sets(edges, defects, size):
                    count += 1
                    matching, detail = shadow_factor(edges, chosen, blockers)
                    allowed = detail["allowed_edge_count"]
                    allowed_min = allowed if allowed_min is None else min(allowed_min, allowed)
                    allowed_max = allowed if allowed_max is None else max(allowed_max, allowed)
                    if matching is not None and len(feasible) < 5:
                        feasible.append(
                            {
                                "removed_indices": list(chosen),
                                "removed_edges": [list(edges[i]) for i in chosen],
                                **detail,
                            }
                        )
                record = {
                    "size": size,
                    "independent_hitting_set_count": count,
                    "shadow_factor_count_lower_bound": len(feasible),
                    "all_infeasible": not feasible,
                    "allowed_edge_min": allowed_min,
                    "allowed_edge_max": allowed_max,
                    "examples": feasible,
                    "elapsed_s": round(time.time() - scan_started, 3),
                }
                base_result["exact_scan"].append(record)
                print(
                    f"  exact k={size}: sets={count} "
                    f"F0={'NO' if not feasible else 'YES'} "
                    f"allowed={allowed_min}..{allowed_max} "
                    f"time={record['elapsed_s']}s",
                    flush=True,
                )
        base_result["elapsed_s"] = round(time.time() - base_started, 3)
        payload["bases"].append(base_result)
        (HERE / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    payload["elapsed_s"] = round(time.time() - started, 3)
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

"""Exact shadow-factor audit of the four verified m=37, V=40 basins.

The 37 fundamental C4 cells of a rot4 configuration form a 2-factor on
vertices 0,...,36.  If an independent set of k factor edges is deleted, its
2k endpoints each have residual degree one.  Repair is therefore a perfect
matching problem, but every matching edge has up to two geometrically distinct
orientations.

For every minimum independent defect-hitting deletion set this script checks:

  F0  an allowed perfect matching exists after filtering each oriented cell
      against the retained point set ("one-new-orbit shadow");
  F1  an oriented perfect matching exists whose chosen orbit pairs are all
      mutually compatible with the retained point set;
  F2  a full oriented perfect matching exists whose complete C4 lift has no
      collinear triple.

If F0 fails, a brute-force Tutte odd-component witness X is emitted.  The
largest graph has only 12 vertices, so this witness enumeration is exact.
"""

from __future__ import annotations

import itertools
import json
import math
import time
from collections import Counter
from pathlib import Path


M = 37
N = 2 * M
SOURCE_OUTPUTS = Path(
    r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36"
    r"\no3inline-rigidity\analysis\m37_continue\outputs"
)
HERE = Path(__file__).resolve().parent


def c4_lifts(cell: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    x, y = cell
    out = []
    for _ in range(4):
        out.append((x, y))
        x, y = N - 1 - y, x
    return tuple(out)


def line_key(
    p: tuple[int, int], q: tuple[int, int]
) -> tuple[int, int, int] | None:
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        return None
    g = math.gcd(abs(dx), abs(dy))
    a, b = dy // g, -dx // g
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    return a, b, a * p[0] + b * p[1]


def directed_cell(edge: tuple[int, int], bit: int) -> tuple[int, int]:
    u, v = edge
    return (u, v) if bit == 0 else (v, u)


def has_collinear_triple(points: list[tuple[int, int]]) -> bool:
    """Exact O(q^2) line-mask oracle, used only for assertions."""
    members: dict[tuple[int, int, int], int] = {}
    for i, j in itertools.combinations(range(len(points)), 2):
        key = line_key(points[i], points[j])
        if key is None:
            return True
        mask = members.get(key, 0) | (1 << i) | (1 << j)
        if mask.bit_count() >= 3:
            return True
        members[key] = mask
    return False


def safe_add_orbit(
    exact_points: list[tuple[int, int]],
    orbit: tuple[tuple[int, int], ...],
) -> bool:
    """Whether appending one four-point orbit preserves triple-freeness."""
    if len(set(orbit)) != len(orbit):
        return False
    fixed = set(exact_points)
    if fixed.intersection(orbit):
        return False

    # A new point cannot lie on a secant of the exact retained set.
    for q in orbit:
        seen: set[tuple[int, int, int]] = set()
        for p in exact_points:
            key = line_key(q, p)
            if key in seen:
                return False
            assert key is not None
            seen.add(key)

    # A secant of the new orbit cannot contain a retained point.  This also
    # rejects internal triples once earlier new points are part of exact_points.
    for q, r in itertools.combinations(orbit, 2):
        key = line_key(q, r)
        if key is None:
            return False
        a, b, c = key
        if any(a * x + b * y == c for x, y in exact_points):
            return False

    # Purely internal triple of the four-point orbit.
    for p, q, r in itertools.combinations(orbit, 3):
        if (q[0] - p[0]) * (r[1] - p[1]) == (
            q[1] - p[1]
        ) * (r[0] - p[0]):
            return False
    return True


def enumerate_minimum_independent_hitting_sets(
    edges: list[tuple[int, int]],
    defects: list[list[int]],
    size: int,
) -> list[tuple[int, ...]]:
    defect_full = (1 << len(defects)) - 1
    coverage = [
        sum(1 << defect_no for defect_no, defect in enumerate(defects) if i in defect)
        for i in range(len(edges))
    ]
    results = []
    for chosen in itertools.combinations(range(len(edges)), size):
        vertex_mask = 0
        covered = 0
        for index in chosen:
            u, v = edges[index]
            endpoints = (1 << u) | (1 << v)
            if vertex_mask & endpoints:
                break
            vertex_mask |= endpoints
            covered |= coverage[index]
        else:
            if covered == defect_full:
                results.append(chosen)
    return results


def perfect_matching(
    vertices: tuple[int, ...],
    oriented_options: dict[tuple[int, int], tuple[tuple[int, int], ...]],
) -> tuple[tuple[int, int], ...] | None:
    """Small exact DP for an undirected perfect matching."""
    position = {vertex: i for i, vertex in enumerate(vertices)}
    memo: dict[int, tuple[tuple[int, int], ...] | None] = {}

    def visit(mask: int) -> tuple[tuple[int, int], ...] | None:
        if not mask:
            return ()
        if mask in memo:
            return memo[mask]
        low = mask & -mask
        i = low.bit_length() - 1
        u = vertices[i]
        remaining = mask ^ low
        work = remaining
        while work:
            v_low = work & -work
            j = v_low.bit_length() - 1
            v = vertices[j]
            edge = tuple(sorted((u, v)))
            if oriented_options.get(edge):
                suffix = visit(remaining ^ v_low)
                if suffix is not None:
                    memo[mask] = (edge,) + suffix
                    return memo[mask]
            work ^= v_low
        memo[mask] = None
        return None

    return visit((1 << len(vertices)) - 1)


def odd_component_count(
    vertices: tuple[int, ...],
    adjacency: dict[int, set[int]],
    removed: set[int],
) -> tuple[int, list[list[int]]]:
    unseen = set(vertices) - removed
    components = []
    while unseen:
        start = min(unseen)
        stack = [start]
        unseen.remove(start)
        component = []
        while stack:
            u = stack.pop()
            component.append(u)
            new = (adjacency[u] - removed) & unseen
            unseen.difference_update(new)
            stack.extend(new)
        if len(component) % 2:
            components.append(sorted(component))
    return len(components), components


def tutte_witness(
    vertices: tuple[int, ...],
    oriented_options: dict[tuple[int, int], tuple[tuple[int, int], ...]],
) -> dict | None:
    adjacency = {u: set() for u in vertices}
    for (u, v), options in oriented_options.items():
        if options:
            adjacency[u].add(v)
            adjacency[v].add(u)
    best = None
    for mask in range(1 << len(vertices)):
        removed = {
            vertices[i] for i in range(len(vertices)) if (mask >> i) & 1
        }
        odd_count, components = odd_component_count(vertices, adjacency, removed)
        deficiency = odd_count - len(removed)
        if best is None or deficiency > best["deficiency"]:
            best = {
                "X": sorted(removed),
                "odd_components": components,
                "odd_component_count": odd_count,
                "deficiency": deficiency,
            }
    return best if best and best["deficiency"] > 0 else None


def compatible_oriented_matching(
    vertices: tuple[int, ...],
    oriented_options: dict[tuple[int, int], tuple[tuple[int, int], ...]],
    retained_points: list[tuple[int, int]],
    exact: bool,
) -> tuple[tuple[tuple[int, int], ...] | None, int]:
    """Exact F1/F2 search.  F1 checks pairwise compatibility only."""
    orbit = {
        cell: c4_lifts(cell)
        for options in oriented_options.values()
        for cell in options
    }
    pair_compatible: dict[tuple[tuple[int, int], tuple[int, int]], bool] = {}
    cells = sorted(orbit)
    for i, first in enumerate(cells):
        points = retained_points + list(orbit[first])
        for second in cells[i + 1 :]:
            pair_compatible[first, second] = safe_add_orbit(points, orbit[second])

    def pair_ok(first: tuple[int, int], second: tuple[int, int]) -> bool:
        if first > second:
            first, second = second, first
        return pair_compatible[first, second]

    nodes = 0

    def visit(
        remaining: frozenset[int],
        selected: tuple[tuple[int, int], ...],
        exact_points: list[tuple[int, int]],
    ) -> tuple[tuple[int, int], ...] | None:
        nonlocal nodes
        nodes += 1
        if not remaining:
            return selected

        # Fail first on the vertex with the fewest currently feasible choices.
        best_vertex = None
        best_choices = None
        for u in sorted(remaining):
            choices = []
            for v in sorted(remaining - {u}):
                edge = tuple(sorted((u, v)))
                for cell in oriented_options.get(edge, ()):
                    if all(pair_ok(cell, old) for old in selected) and (
                        not exact or safe_add_orbit(exact_points, orbit[cell])
                    ):
                        choices.append((v, cell))
            if best_choices is None or len(choices) < len(best_choices):
                best_vertex = u
                best_choices = choices
            if not best_choices:
                return None

        assert best_vertex is not None and best_choices is not None
        for v, cell in best_choices:
            result = visit(
                remaining - {best_vertex, v},
                selected + (cell,),
                exact_points + list(orbit[cell]) if exact else exact_points,
            )
            if result is not None:
                return result
        return None

    answer = visit(frozenset(vertices), (), list(retained_points))
    return answer, nodes


def analyze_deletion_set(
    base: dict,
    removed_indices: tuple[int, ...],
) -> dict:
    edges = [tuple(edge) for edge in base["edges"]]
    bits = list(base["bits"])
    removed = set(removed_indices)
    fixed_indices = [i for i in range(M) if i not in removed]
    fixed_edges = {edges[i] for i in fixed_indices}
    retained_cells = [directed_cell(edges[i], bits[i]) for i in fixed_indices]
    retained_points = [
        point for cell in retained_cells for point in c4_lifts(cell)
    ]
    assert len(retained_points) == len(set(retained_points))
    assert not has_collinear_triple(retained_points)

    affected = tuple(
        sorted(vertex for i in removed_indices for vertex in edges[i])
    )
    assert len(affected) == 2 * len(removed_indices)
    assert len(affected) == len(set(affected))

    oriented_options: dict[
        tuple[int, int], tuple[tuple[int, int], ...]
    ] = {}
    orientation_histogram = Counter()
    rejected_orientations = 0
    for u, v in itertools.combinations(affected, 2):
        edge = (u, v)
        if edge in fixed_edges:
            continue
        options = tuple(
            cell
            for cell in ((u, v), (v, u))
            if safe_add_orbit(retained_points, c4_lifts(cell))
        )
        orientation_histogram[len(options)] += 1
        rejected_orientations += 2 - len(options)
        if options:
            oriented_options[edge] = options

    f0 = perfect_matching(affected, oriented_options)
    result = {
        "removed_indices": list(removed_indices),
        "removed_edges": [list(edges[i]) for i in removed_indices],
        "affected_vertices": list(affected),
        "retained_point_count": len(retained_points),
        "candidate_edge_count": math.comb(len(affected), 2) - sum(
            edge in fixed_edges for edge in itertools.combinations(affected, 2)
        ),
        "allowed_edge_count": len(oriented_options),
        "allowed_orientation_count": sum(map(len, oriented_options.values())),
        "rejected_orientation_count": rejected_orientations,
        "orientation_count_histogram": dict(sorted(orientation_histogram.items())),
        "F0_shadow_factor": f0 is not None,
        "F0_matching": [list(edge) for edge in f0] if f0 else None,
        "F0_tutte_witness": None,
        "F1_pairwise_oriented_factor": False,
        "F1_cells": None,
        "F1_nodes": 0,
        "F2_exact_completion": False,
        "F2_cells": None,
        "F2_nodes": 0,
    }
    if f0 is None:
        result["F0_tutte_witness"] = tutte_witness(affected, oriented_options)
        return result

    f1, f1_nodes = compatible_oriented_matching(
        affected, oriented_options, retained_points, exact=False
    )
    result["F1_pairwise_oriented_factor"] = f1 is not None
    result["F1_cells"] = [list(cell) for cell in f1] if f1 else None
    result["F1_nodes"] = f1_nodes
    if f1 is None:
        return result

    f2, f2_nodes = compatible_oriented_matching(
        affected, oriented_options, retained_points, exact=True
    )
    result["F2_exact_completion"] = f2 is not None
    result["F2_cells"] = [list(cell) for cell in f2] if f2 else None
    result["F2_nodes"] = f2_nodes
    if f2 is not None:
        final_points = list(retained_points)
        for cell in f2:
            final_points.extend(c4_lifts(cell))
        assert len(final_points) == 4 * M
        assert len(final_points) == len(set(final_points))
        assert not has_collinear_triple(final_points)
    return result


def main() -> None:
    started = time.time()
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = {
        item["id"]: item
        for item in archive["archive"]
        if item["id"] in {f"v40_{i:02d}" for i in range(1, 5)}
    }
    payload = {
        "method": {
            "m": M,
            "deletion_class": "all minimum independent defect-hitting edge sets",
            "F0": "one-new-orbit shadow followed by perfect matching",
            "F1": "F0 plus pairwise compatibility of selected oriented C4 orbits",
            "F2": "complete no-three-collinear C4 repair",
        },
        "bases": [],
    }
    for base_id in sorted(bases):
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base_id}.json").read_text(
                encoding="utf-8"
            )
        )
        base = bases[base_id]
        assert [tuple(edge) for edge in hitting["edges"]] == [
            tuple(edge) for edge in base["edges"]
        ]
        assert hitting["bits"] == base["bits"]
        size = hitting["minimum_independent_hitting_set"]["size"]
        deletion_sets = enumerate_minimum_independent_hitting_sets(
            [tuple(edge) for edge in base["edges"]],
            hitting["defect_owner_sets"],
            size,
        )
        print(
            f"{base_id}: minimum independent hitting size={size}, "
            f"sets={len(deletion_sets)}",
            flush=True,
        )
        records = []
        for number, deletion_set in enumerate(deletion_sets, 1):
            record = analyze_deletion_set(base, deletion_set)
            records.append(record)
            print(
                f"  {number}/{len(deletion_sets)} {deletion_set}: "
                f"F0={record['F0_shadow_factor']} "
                f"F1={record['F1_pairwise_oriented_factor']} "
                f"F2={record['F2_exact_completion']} "
                f"allowed={record['allowed_edge_count']}/"
                f"{record['candidate_edge_count']} "
                f"nodes={record['F1_nodes']}/{record['F2_nodes']}",
                flush=True,
            )
        counts = {
            key: sum(record[key] for record in records)
            for key in (
                "F0_shadow_factor",
                "F1_pairwise_oriented_factor",
                "F2_exact_completion",
            )
        }
        payload["bases"].append(
            {
                "base": base_id,
                "minimum_independent_hitting_size": size,
                "deletion_set_count": len(deletion_sets),
                "stage_feasible_counts": counts,
                "records": records,
            }
        )

    payload["summary"] = {
        "deletion_set_count": sum(
            item["deletion_set_count"] for item in payload["bases"]
        ),
        "stage_feasible_counts": {
            key: sum(item["stage_feasible_counts"][key] for item in payload["bases"])
            for key in (
                "F0_shadow_factor",
                "F1_pairwise_oriented_factor",
                "F2_exact_completion",
            )
        },
        "elapsed_s": round(time.time() - started, 3),
    }
    output = HERE / "rot4_shadow_factor_v40.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2), flush=True)
    print(output)


if __name__ == "__main__":
    main()

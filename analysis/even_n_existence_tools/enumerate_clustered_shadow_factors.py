"""Exact combinatorial enumeration of highly clustered k=11 deletions.

CP-SAT becomes proof-heavy when many removed base edges are adjacent.  For a
fixed adjacency count, however, the deletion sets can be generated directly as
cyclic runs.  Each retained-exact deletion set is then tested by a small exact
deficit-factor dynamic program using the precomputed one-orbit blockers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from functools import lru_cache
from pathlib import Path

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers, is_cell_safe


HERE = Path(__file__).resolve().parent


def compositions(total: int, parts: int):
    if parts == 0:
        if total == 0:
            yield ()
        return
    for cuts in itertools.combinations(range(1, total), parts - 1):
        values = []
        previous = 0
        for cut in cuts + (total,):
            values.append(cut - previous)
            previous = cut
        yield tuple(values)


def cycle_edge_orders(edges: list[tuple[int, int]]) -> list[tuple[int, ...]]:
    incident = {vertex: [] for vertex in range(M)}
    for index, (u, v) in enumerate(edges):
        incident[u].append(index)
        incident[v].append(index)
    unseen = set(range(M))
    orders = []
    while unseen:
        start = min(unseen)
        current = start
        previous_edge = None
        order = []
        while True:
            choices = [edge for edge in incident[current] if edge != previous_edge]
            edge = choices[0]
            if order and edge == order[0]:
                break
            order.append(edge)
            u, v = edges[edge]
            current = v if current == u else u
            unseen.discard(current)
            previous_edge = edge
            if current == start:
                break
        orders.append(tuple(order))
    assert sorted(index for order in orders for index in order) == list(range(M))
    return orders


@lru_cache(maxsize=None)
def local_cycle_subsets(
    length: int, selected_count: int, adjacency_count: int
) -> tuple[tuple[int, ...], ...]:
    if selected_count == 0:
        return ((),) if adjacency_count == 0 else ()
    if selected_count == length:
        return (tuple(range(length)),) if adjacency_count == length else ()
    runs = selected_count - adjacency_count
    if not (1 <= runs <= min(selected_count, length - selected_count)):
        return ()
    results = []
    for run_lengths in compositions(selected_count, runs):
        for gap_lengths in compositions(length - selected_count, runs):
            for start in range(length):
                selected = set()
                position = start
                for run, gap in zip(run_lengths, gap_lengths):
                    for offset in range(run):
                        selected.add((position + offset) % length)
                    position = (position + run + gap) % length
                run_starts = [
                    index
                    for index in selected
                    if (index - 1) % length not in selected
                ]
                if start == min(run_starts):
                    results.append(tuple(sorted(selected)))
    assert len(results) == len(set(results))
    return tuple(results)


def deletion_sets_by_adjacency(
    cycle_orders: list[tuple[int, ...]],
    selected_count: int,
    adjacency_count: int,
):
    def visit(cycle_no: int, k_left: int, a_left: int, chosen: tuple[int, ...]):
        if cycle_no == len(cycle_orders):
            if k_left == 0 and a_left == 0:
                yield tuple(sorted(chosen))
            return
        order = cycle_orders[cycle_no]
        length = len(order)
        for local_k in range(max(0, k_left - sum(map(len, cycle_orders[cycle_no + 1 :]))), min(length, k_left) + 1):
            for local_a in range(a_left + 1):
                subsets = local_cycle_subsets(length, local_k, local_a)
                if not subsets:
                    continue
                for subset in subsets:
                    mapped = tuple(order[index] for index in subset)
                    yield from visit(
                        cycle_no + 1,
                        k_left - local_k,
                        a_left - local_a,
                        chosen + mapped,
                    )

    yield from visit(0, selected_count, adjacency_count, ())


def shadow_factor_dp(
    edges: list[tuple[int, int]],
    removed_indices: tuple[int, ...],
    blockers: dict[tuple[int, int], tuple[int, ...]],
):
    removed = set(removed_indices)
    removed_mask = sum(1 << index for index in removed)
    deficits = [0] * M
    for index in removed_indices:
        u, v = edges[index]
        deficits[u] += 1
        deficits[v] += 1
    affected = tuple(vertex for vertex, degree in enumerate(deficits) if degree)
    position = {vertex: i for i, vertex in enumerate(affected)}
    fixed_edges = {edge for i, edge in enumerate(edges) if i not in removed}

    options = {}
    for i, u in enumerate(affected):
        if deficits[u] == 2 and is_cell_safe(blockers[(u, u)], removed_mask):
            options[(u, u)] = ((u, u),)
        for v in affected[i + 1 :]:
            if (u, v) in fixed_edges:
                continue
            orientations = tuple(
                cell
                for cell in ((u, v), (v, u))
                if is_cell_safe(blockers[cell], removed_mask)
            )
            if orientations:
                options[(u, v)] = orientations

    start_state = tuple(deficits[vertex] for vertex in affected)

    @lru_cache(maxsize=None)
    def visit(state: tuple[int, ...]):
        if not any(state):
            return ()
        # Minimum-domain deficit vertex.
        best = None
        for i, degree in enumerate(state):
            if not degree:
                continue
            u = affected[i]
            neighbors = [
                j
                for j, other_degree in enumerate(state)
                if j != i
                and other_degree
                and tuple(sorted((u, affected[j]))) in options
            ]
            domain = (
                int(degree == 2 and (u, u) in options)
                + (len(neighbors) if degree == 1 else len(neighbors) * (len(neighbors) - 1) // 2)
            )
            if best is None or domain < best[0]:
                best = (domain, i, neighbors)
        assert best is not None
        _, i, neighbors = best
        u = affected[i]
        degree = state[i]
        if degree == 1:
            for j in neighbors:
                new = list(state)
                new[i] = 0
                new[j] -= 1
                suffix = visit(tuple(new))
                if suffix is not None:
                    return (tuple(sorted((u, affected[j]))),) + suffix
        else:
            if (u, u) in options:
                new = list(state)
                new[i] = 0
                suffix = visit(tuple(new))
                if suffix is not None:
                    return ((u, u),) + suffix
            for j, k in itertools.combinations(neighbors, 2):
                new = list(state)
                new[i] = 0
                new[j] -= 1
                new[k] -= 1
                if new[j] < 0 or new[k] < 0:
                    continue
                suffix = visit(tuple(new))
                if suffix is not None:
                    return (
                        tuple(sorted((u, affected[j]))),
                        tuple(sorted((u, affected[k]))),
                    ) + suffix
        return None

    factor = visit(start_state)
    return factor, {
        "affected_vertex_count": len(affected),
        "deficit_two_count": sum(value == 2 for value in deficits),
        "allowed_underlying_edge_count": len(options),
        "dp_states": visit.cache_info().currsize,
        "factor": [list(edge) for edge in factor] if factor else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bases", default="all")
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--adjacencies", default="8,9,10")
    parser.add_argument("--max-examples", type=int, default=10)
    parser.add_argument("--out", default="clustered_shadow_factors.json")
    args = parser.parse_args()

    wanted = (
        {f"v40_{i:02d}" for i in range(1, 5)}
        if args.bases == "all"
        else set(args.bases.split(","))
    )
    adjacency_values = [int(item) for item in args.adjacencies.split(",")]
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [item for item in archive["archive"] if item["id"] in wanted]
    output = HERE / args.out
    payload = {"parameters": vars(args), "bases": []}
    for base in sorted(bases, key=lambda item: item["id"]):
        edges = [tuple(edge) for edge in base["edges"]]
        orders = cycle_edge_orders(edges)
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        defect_masks = [
            sum(1 << index for index in defect)
            for defect in hitting["defect_owner_sets"]
        ]
        print(f"{base['id']}: precomputing blockers", flush=True)
        blockers = candidate_blockers(base)
        base_result = {
            "base": base["id"],
            "cycle_lengths": list(map(len, orders)),
            "runs": [],
        }
        payload["bases"].append(base_result)
        for adjacency in adjacency_values:
            started = time.time()
            generated = hitting_count = f0_count = 0
            examples = []
            allowed_min = allowed_max = None
            for removed_indices in deletion_sets_by_adjacency(
                orders, args.size, adjacency
            ):
                generated += 1
                removed_mask = sum(1 << index for index in removed_indices)
                if not all(mask & removed_mask for mask in defect_masks):
                    continue
                hitting_count += 1
                factor, detail = shadow_factor_dp(
                    edges, removed_indices, blockers
                )
                allowed = detail["allowed_underlying_edge_count"]
                allowed_min = allowed if allowed_min is None else min(allowed_min, allowed)
                allowed_max = allowed if allowed_max is None else max(allowed_max, allowed)
                if factor is not None:
                    f0_count += 1
                    if len(examples) < args.max_examples:
                        examples.append(
                            {
                                "removed_indices": list(removed_indices),
                                "removed_edges": [list(edges[i]) for i in removed_indices],
                                **detail,
                            }
                        )
            record = {
                "size": args.size,
                "adjacency_count": adjacency,
                "deletion_set_count": generated,
                "defect_hitting_set_count": hitting_count,
                "F0_factor_count": f0_count,
                "allowed_edge_min": allowed_min,
                "allowed_edge_max": allowed_max,
                "examples": examples,
                "elapsed_s": round(time.time() - started, 3),
            }
            base_result["runs"].append(record)
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(
                f"  a={adjacency}: sets={generated} hit={hitting_count} "
                f"F0={f0_count} allowed={allowed_min}..{allowed_max} "
                f"time={record['elapsed_s']}s",
                flush=True,
            )
    print(output)


if __name__ == "__main__":
    main()

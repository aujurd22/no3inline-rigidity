"""Search small cubic bipartite graphs for hitting-perfect-matching obstructions.

Let X be a simple 3-regular bipartite graph whose edges represent a point set
with three points in every row and column.  A forbidden collinear triple is a
set of three pairwise row/column-disjoint edges.  We ask whether a collection
of pairwise edge-disjoint triples can block every perfect matching, where a
perfect matching is blocked when it completely misses at least one triple.

If such a collection exists, no perfect matching hits all triples.  This
script enumerates every perfect matching of a sampled graph and solves the
resulting minimum set-cover problem, optionally enforcing edge-disjointness
of the selected triples.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random

from ortools.sat.python import cp_model


Edge = tuple[int, int]


def random_cubic_bipartite(n: int, rng: random.Random) -> list[Edge]:
    """Generate a simple cubic bipartite graph as three disjoint permutations."""
    while True:
        permutations: list[list[int]] = []
        for _ in range(3):
            for _attempt in range(10_000):
                permutation = list(range(n))
                rng.shuffle(permutation)
                if all(
                    permutation[row] != previous[row]
                    for previous in permutations
                    for row in range(n)
                ):
                    permutations.append(permutation)
                    break
            else:
                break
        if len(permutations) == 3:
            return sorted(
                (row, permutation[row])
                for permutation in permutations
                for row in range(n)
            )


def enumerate_perfect_matchings(n: int, edges: list[Edge]) -> list[frozenset[int]]:
    by_row: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for index, (row, column) in enumerate(edges):
        by_row[row].append((column, index))
    result: list[frozenset[int]] = []

    def visit(row: int, used_columns: int, chosen: list[int]) -> None:
        if row == n:
            result.append(frozenset(chosen))
            return
        for column, edge_index in by_row[row]:
            bit = 1 << column
            if used_columns & bit:
                continue
            chosen.append(edge_index)
            visit(row + 1, used_columns | bit, chosen)
            chosen.pop()

    visit(0, 0, [])
    return result


def candidate_triples(
    edges: list[Edge], geometric_only: bool
) -> list[tuple[int, int, int]]:
    candidates = []
    for triple in itertools.combinations(range(len(edges)), 3):
        rows = {edges[index][0] for index in triple}
        columns = {edges[index][1] for index in triple}
        if len(rows) != 3 or len(columns) != 3:
            continue
        if geometric_only:
            a, b, c = (edges[index] for index in triple)
            determinant = (
                (b[0] - a[0]) * (c[1] - a[1])
                - (b[1] - a[1]) * (c[0] - a[0])
            )
            if determinant:
                continue
        candidates.append(triple)
    return candidates


def has_four_collinear(edges: list[Edge]) -> bool:
    for quadruple in itertools.combinations(edges, 4):
        a, b, c, d = quadruple
        if all(
            (point[0] - a[0]) * (b[1] - a[1])
            == (point[1] - a[1]) * (b[0] - a[0])
            for point in (c, d)
        ):
            return True
    return False


def minimum_obstruction(
    edges: list[Edge],
    perfect_matchings: list[frozenset[int]],
    triples: list[tuple[int, int, int]],
    edge_disjoint: bool,
    time_limit: float,
) -> dict:
    miss_sets = [
        [index for index, matching in enumerate(perfect_matchings)
         if matching.isdisjoint(triple)]
        for triple in triples
    ]
    useful = [index for index, missed in enumerate(miss_sets) if missed]
    model = cp_model.CpModel()
    selected = {index: model.new_bool_var(f"t_{index}") for index in useful}

    for matching_index in range(len(perfect_matchings)):
        blockers = [
            selected[index]
            for index in useful
            if matching_index in miss_sets[index]
        ]
        if not blockers:
            return {
                "status": "IMPOSSIBLE_TO_BLOCK",
                "reason": f"matching {matching_index} meets every candidate triple",
            }
        model.add(sum(blockers) >= 1)

    if edge_disjoint:
        for edge_index in range(len(edges)):
            containing = [
                selected[index]
                for index in useful
                if edge_index in triples[index]
            ]
            if containing:
                model.add(sum(containing) <= 1)

    model.minimize(sum(selected.values()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 4
    status = solver.solve(model)
    answer = {
        "status": solver.status_name(status),
        "objective_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = [index for index in useful if solver.value(selected[index])]
        answer.update(
            {
                "minimum_triples": len(chosen),
                "triples": [
                    [edges[edge_index] for edge_index in triples[index]]
                    for index in chosen
                ],
            }
        )
    return answer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, nargs="+", default=[6, 8, 10, 12])
    parser.add_argument("--graphs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--allow-overlap", action="store_true")
    parser.add_argument(
        "--arbitrary-triples",
        action="store_true",
        help="allow any row/column-disjoint edge triple, not just collinear ones",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    records = []
    for n in args.n:
        for graph_index in range(args.graphs):
            edges = random_cubic_bipartite(n, rng)
            if not args.arbitrary_triples and has_four_collinear(edges):
                print(
                    json.dumps(
                        {
                            "n": n,
                            "graph_index": graph_index,
                            "skipped": "four_collinear",
                        }
                    ),
                    flush=True,
                )
                continue
            matchings = enumerate_perfect_matchings(n, edges)
            triples = candidate_triples(edges, not args.arbitrary_triples)
            result = minimum_obstruction(
                edges,
                matchings,
                triples,
                not args.allow_overlap,
                args.time_limit,
            )
            record = {
                "n": n,
                "graph_index": graph_index,
                "edges": edges,
                "perfect_matchings": len(matchings),
                "candidate_triples": len(triples),
                "edge_disjoint": not args.allow_overlap,
                "result": result,
            }
            records.append(record)
            print(json.dumps(record), flush=True)
            if result.get("minimum_triples") is not None:
                print("OBSTRUCTION_FOUND")
                print(json.dumps(records, indent=2))
                return
    print("NO_OBSTRUCTION_IN_SAMPLE")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()

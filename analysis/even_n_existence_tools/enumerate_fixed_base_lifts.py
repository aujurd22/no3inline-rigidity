"""Enumerate distinct point sets lifting one fixed four-permutation base."""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from four_permutation_lift_sat import Edge, collinear, verify


@dataclass
class LiftModel:
    model: cp_model.CpModel
    edges: list[Edge]
    row_bit: dict[tuple[int, int], cp_model.IntVar]
    col_bit: dict[tuple[int, int], cp_model.IntVar]


def build_model(p: int, permutations: list[list[int]]) -> LiftModel:
    if len(permutations) != 4:
        raise ValueError("exactly four base permutations are required")
    if any(sorted(permutation) != list(range(p)) for permutation in permutations):
        raise ValueError("every layer must be a permutation")
    edges = [
        Edge(layer=layer, x=x, y=permutations[layer][x])
        for layer in range(4)
        for x in range(p)
    ]
    model = cp_model.CpModel()
    row_bit = {
        (edge.layer, edge.x): model.new_bool_var(f"r_{edge.layer}_{edge.x}")
        for edge in edges
    }
    col_bit = {
        (edge.layer, edge.x): model.new_bool_var(f"c_{edge.layer}_{edge.x}")
        for edge in edges
    }
    for x in range(p):
        model.add(sum(row_bit[(layer, x)] for layer in range(4)) == 2)
    for y in range(p):
        model.add(
            sum(
                col_bit[(edge.layer, edge.x)]
                for edge in edges
                if edge.y == y
            )
            == 2
        )

    by_base: dict[tuple[int, int], list[Edge]] = {}
    for edge in edges:
        by_base.setdefault((edge.x, edge.y), []).append(edge)
    for parallel in by_base.values():
        for first, second in itertools.combinations(parallel, 2):
            first_key = (first.layer, first.x)
            second_key = (second.layer, second.x)
            for row_value, column_value in itertools.product((0, 1), repeat=2):
                model.add_bool_or(
                    [
                        row_bit[first_key].Not()
                        if row_value
                        else row_bit[first_key],
                        row_bit[second_key].Not()
                        if row_value
                        else row_bit[second_key],
                        col_bit[first_key].Not()
                        if column_value
                        else col_bit[first_key],
                        col_bit[second_key].Not()
                        if column_value
                        else col_bit[second_key],
                    ]
                )

    for triple in itertools.combinations(edges, 3):
        determinant_mod_p = (
            (triple[1].x - triple[0].x) * (triple[2].y - triple[0].y)
            - (triple[1].y - triple[0].y) * (triple[2].x - triple[0].x)
        ) % p
        if determinant_mod_p:
            continue
        keys = sorted({(edge.layer, edge.x) for edge in triple})
        bit_keys = [(kind, key) for key in keys for kind in (0, 1)]
        for values in itertools.product((0, 1), repeat=len(bit_keys)):
            assignment = dict(zip(bit_keys, values))
            points = [
                (
                    edge.x + p * assignment[(0, (edge.layer, edge.x))],
                    edge.y + p * assignment[(1, (edge.layer, edge.x))],
                )
                for edge in triple
            ]
            if not collinear(*points):
                continue
            literals = []
            for (kind, key), value in zip(bit_keys, values):
                variable = row_bit[key] if kind == 0 else col_bit[key]
                literals.append(variable.Not() if value else variable)
            model.add_bool_or(literals)
    return LiftModel(model, edges, row_bit, col_bit)


class Collector(cp_model.CpSolverSolutionCallback):
    def __init__(self, lift_model: LiftModel, p: int, maximum: int):
        super().__init__()
        self.lift_model = lift_model
        self.p = p
        self.maximum = maximum
        self.point_sets: list[list[tuple[int, int]]] = []
        self._seen: set[tuple[tuple[int, int], ...]] = set()

    def on_solution_callback(self) -> None:
        points = [
            (
                edge.x
                + self.p * self.value(
                    self.lift_model.row_bit[(edge.layer, edge.x)]
                ),
                edge.y
                + self.p * self.value(
                    self.lift_model.col_bit[(edge.layer, edge.x)]
                ),
            )
            for edge in self.lift_model.edges
        ]
        key = tuple(sorted(points))
        if key not in self._seen:
            self._seen.add(key)
            self.point_sets.append(points)
        if len(self.point_sets) >= self.maximum:
            self.stop_search()


def enumerate_lifts(
    p: int,
    permutations: list[list[int]],
    maximum: int,
    time_limit: float,
) -> dict:
    lift_model = build_model(p, permutations)
    collector = Collector(lift_model, p, maximum)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.num_search_workers = 1
    started = time.perf_counter()
    status = solver.solve(lift_model.model, collector)
    elapsed = time.perf_counter() - started
    for points in collector.point_sets:
        if not verify(points, 2 * p)["valid"]:
            raise AssertionError("enumerator produced an invalid point set")
    return {
        "status": solver.status_name(status),
        "elapsed_seconds": elapsed,
        "distinct_point_sets": collector.point_sets,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
    }

"""Audit exhaustive coverage of the v40_01 general-deletion k=11 barrier."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def partitions(total: int, parts: int, minimum: int = 1):
    if parts == 0:
        if total == 0:
            yield ()
        return
    for first in range(minimum, total + 1):
        for rest in partitions(total - first, parts - 1, first):
            yield (first,) + rest


def possible_triple_counts(size: int, adjacency: int) -> list[int]:
    segments = size - adjacency
    return sorted(
        {
            sum(max(length - 2, 0) for length in shape)
            for shape in partitions(size, segments)
        }
    )


def direct_run_status(name: str) -> dict:
    payload = load(name)
    run = payload["bases"][0]["runs"][0]
    assert run["status"] == "INFEASIBLE"
    return {
        "classification": "CLOSED",
        "mechanism": "line_capacity",
        "evidence": name,
        "line_cut_count": run["line_cut_count"],
    }


def overflow_status(name: str) -> dict:
    payload = load(name)
    assert payload["status"] == "OPTIMAL"
    assert payload["objective"] > 0
    assert payload["best_bound"] == payload["objective"]
    return {
        "classification": "CLOSED",
        "mechanism": "fixed_short_direction_overflow",
        "q": payload["parameters"]["direction_q"],
        "objective": payload["objective"],
        "evidence": name,
    }


def main() -> None:
    layers = {
        "0": {
            "classification": "CLOSED",
            "mechanism": "q1_line_capacity",
            "evidence": "rot4_adjacency_cut_sweep_v40_01.json",
        },
        "1": overflow_status("rot4_line_overflow_v40_01_a1_q2.json"),
        "2": overflow_status("rot4_line_overflow_v40_01_a2_q2.json"),
        "3": overflow_status("rot4_line_overflow_v40_01_a3_q2.json"),
        "4": direct_run_status("joint_rot4_general_v40_01_k11_a4_q1.json"),
        "7": {
            "classification": "CLOSED",
            "mechanism": "q1_line_capacity",
            "evidence": "rot4_adjacency_cut_sweep_v40_01.json",
        },
        "8": {
            "classification": "CLOSED",
            "mechanism": "q1_line_capacity",
            "evidence": "rot4_adjacency_cut_sweep_v40_01.json",
        },
        "9": {
            "classification": "CLOSED",
            "mechanism": "q1_line_capacity",
            "evidence": "rot4_adjacency_cut_sweep_v40_01.json",
        },
        "10": {
            "classification": "CLOSED",
            "mechanism": "q1_line_capacity",
            "evidence": "rot4_adjacency_cut_sweep_v40_01.json",
        },
    }
    adjacency_sweep = load("rot4_adjacency_cut_sweep_v40_01.json")
    adjacency_status = adjacency_sweep["bases"][0]["final_status"]
    for adjacency in (0, 7, 8, 9, 10):
        assert adjacency_status[str(adjacency)] == "INFEASIBLE"

    shape_sweep = load("rot4_runshape_cut_sweep_v40_01.json")
    shape_status = shape_sweep["bases"][0]["final_status"]
    loop_status = load("rot4_shape_loop_cut_sweep_v40_01.json")["final_status"]
    overflow_files = {
        (5, 1): "rot4_diagonal_overflow_v40_01_a5_t1_l0.json",
        (5, 2): "rot4_diagonal_overflow_v40_01_a5_t2_l0.json",
        (6, 1): "rot4_diagonal_overflow_v40_01_a6_t1_l0.json",
        (6, 2): "rot4_diagonal_overflow_v40_01_a6_t2_l0.json",
        (6, 3): "rot4_diagonal_overflow_v40_01_a6_t3_l0.json",
    }
    for adjacency in (5, 6):
        triple_layers = {}
        possible = possible_triple_counts(11, adjacency)
        for triple_count in possible:
            key = f"{adjacency}:{triple_count}"
            if shape_status[key] == "INFEASIBLE":
                triple_layers[str(triple_count)] = {
                    "classification": "CLOSED",
                    "mechanism": "q1_line_capacity",
                    "evidence": "rot4_runshape_cut_sweep_v40_01.json",
                }
                continue
            assert shape_status[key] == "UNKNOWN"
            for loop_count in range(1, adjacency + 1):
                assert (
                    loop_status[f"{adjacency}:{triple_count}:{loop_count}"]
                    == "INFEASIBLE"
                )
            evidence = overflow_files[(adjacency, triple_count)]
            overflow = load(evidence)
            f0_closed = overflow["status"] == "INFEASIBLE"
            line_closed = (
                overflow["status"] == "OPTIMAL"
                and overflow["objective"] > 0
                and overflow["best_bound"] == overflow["objective"]
            )
            assert f0_closed or line_closed
            triple_layers[str(triple_count)] = {
                "classification": "CLOSED",
                "mechanism": (
                    "all_positive_loops_q1_and_loop0_f0"
                    if f0_closed
                    else "all_positive_loops_q1_and_loop0_q1_overflow"
                ),
                "loop0_objective": overflow["objective"],
                "evidence": [
                    "rot4_shape_loop_cut_sweep_v40_01.json",
                    evidence,
                ],
            }
        layers[str(adjacency)] = {
            "classification": "CLOSED",
            "possible_triple_counts": possible,
            "triple_layers": triple_layers,
        }

    assert set(layers) == {str(value) for value in range(11)}
    assert all(layer["classification"] == "CLOSED" for layer in layers.values())
    payload = {
        "base": "v40_01",
        "size": 11,
        "cycle_type": [37],
        "adjacency_range": [0, 10],
        "coverage_argument": (
            "A proper 11-edge subset of a 37-cycle has s>=1 deletion "
            "segments and adjacency count A=11-s, hence 0<=A<=10."
        ),
        "status": "INFEASIBLE",
        "consequence": "general deletion escape radius is at least 12",
        "layers": layers,
    }
    output = HERE / "rot4_v40_01_k11_barrier_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

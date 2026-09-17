"""Audit complete closure of the A=6, B<=1 normalized k=12 layers."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str):
    record = json.loads((HERE / name).read_text(encoding="utf-8"))
    assert record["status"] == "INFEASIBLE", (name, record["status"])
    parameters = record["parameters"]
    assert parameters["size"] == 12
    assert parameters["adjacency_count"] == 6
    assert not parameters["allow_exact_reselection"]
    return record


def main() -> None:
    b0_names = {
        base: f"rot4_short_{base}_k12_a6_b0_c0_norm_q3hard.json"
        for base in ("v40_01", "v40_02", "v40_03", "v40_04")
    }
    b1_names = {
        "v40_01": {
            0: "rot4_short_v40_01_k12_a6_b1_c0_l0_fmax5_norm_q4hard.json",
            1: "rot4_short_v40_01_k12_a6_b1_c0_l1_norm_q3hard.json",
        },
        "v40_02": {
            0: "rot4_short_v40_02_k12_a6_b1_c0_l0_norm_q4hard.json",
            1: "rot4_short_v40_02_k12_a6_b1_c0_l1_norm_q3hard.json",
        },
        "v40_03": {
            0: "rot4_short_v40_03_k12_a6_b1_c0_l0_fmax6_norm_q4hard.json",
            1: "rot4_short_v40_03_k12_a6_b1_c0_l1_fmax6_norm_q4hard.json",
        },
        "v40_04": {
            0: "rot4_short_v40_04_k12_a6_b1_c0_l0_fmax4_norm_q4hard.json",
            1: "rot4_short_v40_04_k12_a6_b1_c0_l1_norm_q3hard.json",
        },
    }

    bases = {}
    for base in b0_names:
        b0 = load(b0_names[base])
        p0 = b0["parameters"]
        assert p0["base"] == base
        assert p0["triple_count"] == 0
        assert p0["quadruple_count"] == 0
        b1_layers = {}
        for loop_count, name in b1_names[base].items():
            record = load(name)
            parameters = record["parameters"]
            assert parameters["base"] == base
            assert parameters["triple_count"] == 1
            assert parameters["quadruple_count"] == 0
            assert parameters["loop_count"] == loop_count
            assert parameters["direction_q"] >= 3
            b1_layers[str(loop_count)] = {
                "file": name,
                "direction_q": parameters["direction_q"],
                "flip_max": parameters.get("flip_max"),
                "wall_s": record["wall_s"],
            }
        bases[base] = {
            "B0_C0": {
                "file": b0_names[base],
                "direction_q": p0["direction_q"],
                "wall_s": b0["wall_s"],
            },
            "B1_C0_by_loop_count": b1_layers,
        }

    payload = {
        "scope": {
            "distance": 12,
            "adjacency_count_A": 6,
            "normalization": "exact old-cell reselection forbidden",
            "profiles": [
                {
                    "B": 0,
                    "C": 0,
                    "run_multiset": [2, 2, 2, 2, 2, 2],
                },
                {
                    "B": 1,
                    "C": 0,
                    "run_multiset": [3, 2, 2, 2, 2, 1],
                },
            ],
            "loop_partition_complete_because": (
                "q=1 resource d=0 has capacity 2 and every loop has weight 2, "
                "so at most one replacement loop is possible"
            ),
        },
        "bases": bases,
        "claim": (
            "Any exact normalized k=12 repair from any of the four V=40 "
            "basins with A=6 must have B>=2."
        ),
        "audit_passed": True,
    }
    output = HERE / "rot4_k12_a6_lowB_closure_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(output)


if __name__ == "__main__":
    main()

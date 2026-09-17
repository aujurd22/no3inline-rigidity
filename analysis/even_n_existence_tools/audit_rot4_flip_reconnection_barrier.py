"""Audit blocker-only flip bounds over the normalized k=12 corridor."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASES = [f"v40_{index:02d}" for index in range(1, 5)]


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> None:
    corridor = {}
    for base in BASES:
        by_adjacency = {}
        for adjacency in range(3, 7):
            record = load(
                f"rot4_flip_eligibility_{base}_k12_a{adjacency}_allprofiles.json"
            )
            parameters = record["parameters"]
            assert record["status"] == "OPTIMAL"
            assert record["objective"] == record["best_bound"]
            assert parameters["base"] == base
            assert parameters["size"] == 12
            assert parameters["adjacency_count"] == adjacency
            assert parameters["triple_count"] is None
            assert parameters["quadruple_count"] is None
            by_adjacency[str(adjacency)] = record["objective"]
        maximum = max(by_adjacency.values())
        corridor[base] = {
            "maximum_eligible_flips_by_A": by_adjacency,
            "corridor_maximum_eligible_flips": maximum,
            "minimum_genuine_reconnections": 12 - maximum,
        }

    b1c0 = {}
    for base in BASES:
        cp = load(f"rot4_flip_eligibility_{base}_k12_a6_b1_c0.json")
        suffix = (
            "exhaustive_audit.json"
            if base in {"v40_01", "v40_02"}
            else "exhaustive_audit.json"
        )
        exhaustive = load(f"rot4_flip_eligibility_{base}_{suffix}")
        assert cp["status"] == "OPTIMAL"
        assert cp["objective"] == cp["best_bound"]
        assert exhaustive["cp_sat_cross_check"]["agrees"]
        assert exhaustive["maximum_eligible_flips"] == cp["objective"]
        assert sum(exhaustive["eligibility_histogram"].values()) == exhaustive[
            "defect_hitting_masks"
        ]
        b1c0[base] = {
            "distinct_shape_masks": exhaustive["distinct_shape_masks"],
            "defect_hitting_masks": exhaustive["defect_hitting_masks"],
            "maximum_eligible_flips": exhaustive["maximum_eligible_flips"],
            "minimum_genuine_reconnections": (
                12 - exhaustive["maximum_eligible_flips"]
            ),
            "maximizer_count": exhaustive["eligibility_histogram"][
                str(exhaustive["maximum_eligible_flips"])
            ],
        }

    payload = {
        "scope": {
            "distance": 12,
            "normalized_exact_reselection_forbidden": True,
            "corridor_A": [3, 4, 5, 6],
            "uses_only": [
                "deletion size and adjacency shape",
                "all old-defect hitting constraints",
                "single-orbit blockers of reversed old cells",
            ],
            "does_not_use": [
                "replacement f-factor",
                "line capacities",
                "multi-direction resource graphs",
            ],
        },
        "corridor": corridor,
        "A6_B1_C0_exhaustive": b1c0,
        "claims": {
            "all_corridor_repairs_require_genuine_reconnections": {
                base: record["minimum_genuine_reconnections"]
                for base, record in corridor.items()
            },
            "A6_B1_C0_repairs_require_genuine_reconnections": {
                base: record["minimum_genuine_reconnections"]
                for base, record in b1c0.items()
            },
        },
        "audit_passed": True,
    }
    output = HERE / "rot4_flip_reconnection_barrier_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(output)


if __name__ == "__main__":
    main()

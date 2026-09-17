"""Build a machine-readable (base, adjacency) profile for k=12 at q=1."""

from __future__ import annotations

import json
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS
from audit_other_k11_barriers import (
    cycle_lengths,
    load,
    possible_adjacencies,
)


HERE = Path(__file__).resolve().parent
BASES = tuple(f"v40_{index:02d}" for index in range(1, 5))


def classify(payload: dict) -> str:
    if payload["status"] == "INFEASIBLE":
        return "CLOSED_F0"
    if payload["status"] == "OPTIMAL" and payload["objective"] > 0:
        return "CLOSED_Q1"
    if payload["status"] == "OPTIMAL" and payload["objective"] == 0:
        return "SURVIVES_Q1"
    return "UNRESOLVED"


def main() -> None:
    archive = {
        item["id"]: item
        for item in load(SOURCE_OUTPUTS / "exact_factor_archive.json")["archive"]
    }
    result = {"size": 12, "direction_q": 1, "bases": []}
    for base in BASES:
        lengths = cycle_lengths(archive[base]["edges"])
        possible = possible_adjacencies(lengths, 12)
        layers = {}
        for adjacency in possible:
            evidence = (
                HERE
                / f"rot4_line_overflow_{base}_k12_a{adjacency}_q1.json"
            )
            if not evidence.exists():
                layers[str(adjacency)] = {"classification": "PENDING"}
                continue
            payload = load(evidence)
            assert payload["parameters"]["size"] == 12
            assert payload["parameters"]["direction_q"] == 1
            layers[str(adjacency)] = {
                "classification": classify(payload),
                "status": payload["status"],
                "objective": payload["objective"],
                "best_bound": payload["best_bound"],
                "wall_s": payload["wall_s"],
                "evidence": evidence.name,
                "bad_line_count": (
                    payload.get("solution", {}).get("bad_line_count")
                ),
            }
        result["bases"].append(
            {
                "base": base,
                "cycle_type": lengths,
                "possible_adjacencies": possible,
                "layers": layers,
            }
        )
    output = HERE / "rot4_k12_q1_profile_audit.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)
    for base in result["bases"]:
        counts = {}
        for layer in base["layers"].values():
            key = layer["classification"]
            counts[key] = counts.get(key, 0) + 1
        print(base["base"], counts)


if __name__ == "__main__":
    main()

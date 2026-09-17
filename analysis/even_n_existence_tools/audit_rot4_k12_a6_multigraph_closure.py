"""Aggregate the complete corrected-multigraph A=6 deletion partition audit."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent

PROFILES = {
    (2, 2, 2, 2, 2, 2): "b0_c0",
    (3, 2, 2, 2, 2, 1): "b1_c0",
    (3, 3, 2, 2, 1, 1): "b2_c0",
    (4, 2, 2, 2, 1, 1): "b2_c1",
    (3, 3, 3, 1, 1, 1): "b3_c0",
    (4, 3, 2, 1, 1, 1): "b3_c1",
    (5, 2, 2, 1, 1, 1): "b3_c2",
    (5, 3, 1, 1, 1, 1): "b4_c2a",
    (4, 4, 1, 1, 1, 1): "b4_c2b",
    (6, 2, 1, 1, 1, 1): "b4_c3",
    (7, 1, 1, 1, 1, 1): "b5_c4",
}


def partitions(total: int, parts: int, maximum: int | None = None):
    if parts == 0:
        if total == 0:
            yield ()
        return
    maximum = min(total, maximum if maximum is not None else total)
    for first in range(maximum, 0, -1):
        for tail in partitions(total - first, parts - 1, first):
            yield (first,) + tail


def main() -> None:
    expected = set(partitions(12, 6))
    assert expected == set(PROFILES), (expected - set(PROFILES), set(PROFILES) - expected)
    records = []
    exceptional = []
    for base_number in range(1, 5):
        base = f"v40_{base_number:02d}"
        for profile, suffix in PROFILES.items():
            path = (
                HERE
                / f"rot4_multigraph_factor_exhaustive_{base}_"
                f"k12_a6_{suffix}_q0.json"
            )
            item = json.loads(path.read_text(encoding="utf-8"))
            if "run_lengths" in item:
                assert tuple(sorted(item["run_lengths"], reverse=True)) == profile
            elif "deletion_run_lengths" in item.get("method", {}):
                assert tuple(
                    sorted(
                        item["method"]["deletion_run_lengths"],
                        reverse=True,
                    )
                ) == profile
            assert item["method"]["multigraph"].startswith("both")
            record = {
                "base": base,
                "profile": list(profile),
                "suffix": suffix,
                "distinct_shape_masks": item["distinct_shape_masks"],
                "defect_hitting_masks": item["defect_hitting_masks"],
                "q0_factor_feasible_masks": item["factor_feasible_masks"],
                "root_zero_option_by_deficit": item[
                    "root_zero_option_by_deficit"
                ],
                "maximum_factor_search_nodes": item[
                    "maximum_factor_search_nodes"
                ],
                "certificate": path.name,
            }
            records.append(record)
            if item["factor_feasible_masks"]:
                exceptional.append(
                    {
                        **record,
                        "removed_indices": item[
                            "first_feasible_removed_indices"
                        ],
                        "cells": item["first_feasible_cells"],
                    }
                )

    assert len(exceptional) == 1
    exception = exceptional[0]
    assert exception["base"] == "v40_03"
    assert tuple(exception["profile"]) == (5, 2, 2, 1, 1, 1)
    assert exception["q0_factor_feasible_masks"] == 1
    q1_path = (
        HERE
        / "rot4_fixed_v40_03_k12_a6_b3_c2_unique_multigraph_q1.json"
    )
    q1 = json.loads(q1_path.read_text(encoding="utf-8"))
    assert q1["status"] == "INFEASIBLE"

    per_base = []
    for base_number in range(1, 5):
        base = f"v40_{base_number:02d}"
        subset = [item for item in records if item["base"] == base]
        per_base.append(
            {
                "base": base,
                "profile_count": len(subset),
                "distinct_shape_masks": sum(
                    item["distinct_shape_masks"] for item in subset
                ),
                "defect_hitting_masks": sum(
                    item["defect_hitting_masks"] for item in subset
                ),
                "q0_factor_feasible_masks": sum(
                    item["q0_factor_feasible_masks"] for item in subset
                ),
                "root_zero_option_masks": sum(
                    sum(item["root_zero_option_by_deficit"].values())
                    for item in subset
                ),
            }
        )

    payload = {
        "statement": (
            "For each of the four V40 basins, every normalized k=12, A=6 "
            "deletion shape is impossible in the corrected rot4 multigraph "
            "model. All but one defect-hitting mask fail the q=0 shadow "
            "f-factor; the unique q=0 exception fails q=1."
        ),
        "partition_identity": {
            "k": 12,
            "A": 6,
            "run_count": 6,
            "integer_partition_count": len(expected),
            "covered_profiles": [list(value) for value in sorted(expected, reverse=True)],
        },
        "per_base": per_base,
        "totals": {
            "base_profile_cases": len(records),
            "distinct_shape_masks": sum(
                item["distinct_shape_masks"] for item in records
            ),
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in records
            ),
            "q0_factor_feasible_masks": sum(
                item["q0_factor_feasible_masks"] for item in records
            ),
            "root_zero_option_masks": sum(
                sum(item["root_zero_option_by_deficit"].values())
                for item in records
            ),
        },
        "unique_q0_exception": {
            **exception,
            "q1_status": q1["status"],
            "q1_certificate": q1_path.name,
        },
        "all_a6_closed_after_q1": True,
        "records": records,
    }
    output = HERE / "rot4_k12_a6_corrected_multigraph_closure_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "profiles": len(expected),
        "base_profile_cases": len(records),
        "totals": payload["totals"],
        "unique_q0_exception": {
            "base": exception["base"],
            "profile": exception["profile"],
            "q1_status": q1["status"],
        },
        "all_a6_closed_after_q1": True,
    }, indent=2))
    print(output)


if __name__ == "__main__":
    main()

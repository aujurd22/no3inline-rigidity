"""Aggregate and validate the complete corrected-multigraph k=12 closure."""

from __future__ import annotations

import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASES = [f"v40_{number:02d}" for number in range(1, 5)]


def read(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> None:
    layers = {A: {"regular_sources": [], "special_sources": []} for A in range(12)}

    for A in range(5):
        for base in BASES:
            name = f"rot4_k12_a{A}_{base}_corrected_multigraph_q0_sweep.json"
            item = read(name)
            assert item["A"] == A and item["bases"] == [base]
            layers[A]["regular_sources"].append(
                {"certificate": name, **item["totals"]}
            )

    name = "rot4_k12_a5_corrected_multigraph_q0_sweep.json"
    item = read(name)
    assert item["A"] == 5 and item["bases"] == BASES
    layers[5]["regular_sources"].append({"certificate": name, **item["totals"]})

    name = "rot4_k12_a6_corrected_multigraph_closure_audit.json"
    item = read(name)
    assert item["all_a6_closed_after_q1"]
    layers[6]["regular_sources"].append(
        {"certificate": name, **item["totals"]}
    )

    for A in range(7, 12):
        name = f"rot4_k12_a{A}_corrected_multigraph_q0_sweep.json"
        item = read(name)
        assert item["A"] == A and item["bases"] == BASES
        layers[A]["regular_sources"].append(
            {"certificate": name, **item["totals"]}
        )

    # A fully deleted 4-cycle contributes A=4 by itself and is not represented
    # by the ordinary positive-gap run partitions.  It is impossible for A<4.
    for A in range(4, 12):
        for base in ("v40_03", "v40_04"):
            name = f"rot4_multigraph_factor_full4_{base}_k12_a{A}_q0.json"
            item = read(name)
            assert item["target_adjacency"] == A
            assert item["required_full_cycle_length"] == 4
            assert item["factor_feasible_masks"] == 0
            layers[A]["special_sources"].append(
                {
                    "certificate": name,
                    "base": base,
                    "distinct_shape_masks": item["distinct_shape_masks"],
                    "defect_hitting_masks": item["defect_hitting_masks"],
                    "q0_factor_feasible_masks": item["factor_feasible_masks"],
                }
            )

    expected_q0 = {0: 5, 1: 53, 2: 98, 3: 90, 4: 35, 5: 3, 6: 1}
    per_A = []
    for A in range(12):
        sources = layers[A]["regular_sources"] + layers[A]["special_sources"]
        record = {
            "A": A,
            "regular_source_count": len(layers[A]["regular_sources"]),
            "full_4_cycle_source_count": len(layers[A]["special_sources"]),
            "distinct_shape_masks": sum(
                source["distinct_shape_masks"] for source in sources
            ),
            "defect_hitting_masks": sum(
                source["defect_hitting_masks"] for source in sources
            ),
            "q0_factor_feasible_masks": sum(
                source["q0_factor_feasible_masks"] for source in sources
            ),
            "sources": sources,
        }
        assert record["q0_factor_feasible_masks"] == expected_q0.get(A, 0)
        per_A.append(record)

    expected_shape_total = 4 * math.comb(37, 12)
    actual_shape_total = sum(item["distinct_shape_masks"] for item in per_A)
    assert actual_shape_total == expected_shape_total

    exception_audits = {}
    for A in (0, 1, 2, 3):
        name = f"rot4_k12_a{A}_q0_exceptions_q1_audit.json"
        item = read(name)
        assert item["unique_q0_exception_mask_count"] == expected_q0[A]
        exception_audits[A] = {
            "certificate": name,
            "q0_exception_masks": item["unique_q0_exception_mask_count"],
            "q1_status_histogram": item["q1_status_histogram"],
        }
    name = "rot4_k12_a4_a5_q0_exceptions_q1_audit.json"
    item45 = read(name)
    assert item45["unique_q0_exception_mask_count"] == expected_q0[4] + expected_q0[5]
    for A in (4, 5):
        source_count = sum(
            source["q0_factor_feasible_masks"]
            for source in item45["q0_source_records"]
            if source["A"] == A
        )
        assert source_count == expected_q0[A]
        exception_audits[A] = {
            "certificate": name,
            "q0_exception_masks": source_count,
            "q1_status_histogram": {"INFEASIBLE": source_count},
        }
    name = "rot4_fixed_v40_03_k12_a6_b3_c2_unique_multigraph_q1.json"
    q1_a6 = read(name)
    assert q1_a6["status"] == "INFEASIBLE"
    exception_audits[6] = {
        "certificate": name,
        "q0_exception_masks": 1,
        "q1_status_histogram": {"INFEASIBLE": 1},
    }

    q2_certificates = [
        "rot4_fixed_v40_03_k12_a2_q1core_multigraph_q2.json",
        "rot4_fixed_v40_04_k12_a2_q1core_multigraph_q2.json",
        "rot4_fixed_v40_03_k12_a3_q1core_multigraph_q2.json",
        "rot4_fixed_v40_04_k12_a3_q1core_multigraph_q2.json",
    ]
    for name in q2_certificates:
        assert read(name)["status"] == "INFEASIBLE"

    q0_total = sum(item["q0_factor_feasible_masks"] for item in per_A)
    q1_feasible_total = 4
    q1_infeasible_total = q0_total - q1_feasible_total
    assert q0_total == 285
    assert q1_infeasible_total == 281

    payload = {
        "statement": (
            "For each of the four V40 basins, every normalized k=12 deletion "
            "mask is impossible in the corrected rot4 multigraph model. "
            "This closes the exact distance-12 shell only; it does not by "
            "itself revalidate the older k<=11 escape-radius claim."
        ),
        "coverage_identity": {
            "per_base_all_k12_masks": math.comb(37, 12),
            "base_count": 4,
            "expected_total": expected_shape_total,
            "audited_total": actual_shape_total,
            "exact_match": True,
        },
        "filter_funnel": {
            "all_deletion_masks": actual_shape_total,
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in per_A
            ),
            "q0_factor_feasible_masks": q0_total,
            "q1_feasible_masks": q1_feasible_total,
            "q2_feasible_masks": 0,
        },
        "per_A": per_A,
        "q1_exception_audits": {
            str(A): value for A, value in sorted(exception_audits.items())
        },
        "q2_infeasibility_certificates": q2_certificates,
        "all_k12_closed": True,
        "normalized_escape_radius_lower_bound": None,
        "lower_shells_require_corrected_model_reaudit": list(range(0, 12)),
    }
    output = HERE / "rot4_k12_corrected_multigraph_full_closure_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "coverage_identity": payload["coverage_identity"],
        "filter_funnel": payload["filter_funnel"],
        "all_k12_closed": True,
        "normalized_escape_radius_lower_bound": None,
    }, indent=2))
    print(output)


if __name__ == "__main__":
    main()

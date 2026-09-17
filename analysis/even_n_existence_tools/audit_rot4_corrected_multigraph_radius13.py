"""Aggregate the corrected normalized-distance k<=12 closure certificates."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS


HERE = Path(__file__).resolve().parent
BASES = ["v40_01", "v40_02", "v40_03", "v40_04"]


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def sha256(name: str) -> str:
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def main() -> None:
    minimum_hitting_sizes = {}
    for base in BASES:
        item = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base}.json").read_text(
                encoding="utf-8"
            )
        )
        assert item["minimum_hitting_set"]["status"] == "OPTIMAL"
        minimum_hitting_sizes[base] = item["minimum_hitting_set"]["size"]
    assert minimum_hitting_sizes == {
        "v40_01": 6,
        "v40_02": 6,
        "v40_03": 6,
        "v40_04": 5,
    }

    lower_name = "rot4_k5_k10_corrected_multigraph_full_q0_sweep.json"
    k11_name = "rot4_k11_corrected_multigraph_full_q0_sweep.json"
    k11_q1_name = (
        "rot4_k11_corrected_multigraph_q0_exceptions_q1_audit.json"
    )
    k12_name = "rot4_k12_corrected_multigraph_full_closure_audit.json"
    lower_crosscheck_name = (
        "rot4_k5_k11_corrected_multigraph_crosscheck.json"
    )
    k12_crosscheck_name = (
        "rot4_multigraph_factor_exhaustive_crosscheck.json"
    )
    antiparallel_name = "rot4_antiparallel_pair_model_audit.json"

    lower = read(lower_name)
    k11 = read(k11_name)
    k11_q1 = read(k11_q1_name)
    k12 = read(k12_name)
    lower_crosscheck = read(lower_crosscheck_name)
    k12_crosscheck = read(k12_crosscheck_name)
    antiparallel = read(antiparallel_name)

    assert lower["k_range"] == [5, 10]
    assert all(item["coverage_exact"] for item in lower["per_k"])
    assert lower["totals"]["q0_factor_feasible_masks"] == 0
    assert k11["k"] == 11
    assert k11["totals"]["distinct_shape_masks"] == 4 * math.comb(37, 11)
    assert k11["totals"]["q0_factor_feasible_masks"] == 2
    assert k11_q1["unique_q0_exception_mask_count"] == 2
    assert k11_q1["all_q0_exceptions_q1_infeasible"]
    assert k12["coverage_identity"]["exact_match"]
    assert k12["coverage_identity"]["audited_total"] == 4 * math.comb(37, 12)
    assert k12["all_k12_closed"]
    assert k12["filter_funnel"]["q2_feasible_masks"] == 0
    assert lower_crosscheck["passed"]
    assert k12_crosscheck["passed"]
    assert antiparallel["unordered_pair_count"] == math.comb(37, 2)
    assert antiparallel["failure_count"] == 0

    per_k = []
    for size in range(0, 5):
        per_k.append({
            "k": size,
            "all_deletion_masks": 4 * math.comb(37, size),
            "defect_hitting_masks": 0,
            "q0_factor_feasible_masks": 0,
            "q1_feasible_masks": 0,
            "q2_feasible_masks": 0,
            "closure_stage": "minimum defect-hitting-set lower bound",
        })
    for item in lower["per_k"]:
        per_k.append({
            "k": item["k"],
            "all_deletion_masks": item["audited_all_masks"],
            "defect_hitting_masks": item["defect_hitting_masks"],
            "q0_factor_feasible_masks": item[
                "q0_factor_feasible_masks"
            ],
            "q1_feasible_masks": 0,
            "q2_feasible_masks": 0,
            "closure_stage": "corrected q=0 multigraph deficit factor",
        })
    per_k.append({
        "k": 11,
        "all_deletion_masks": k11["totals"]["distinct_shape_masks"],
        "defect_hitting_masks": k11["totals"]["defect_hitting_masks"],
        "q0_factor_feasible_masks": k11["totals"][
            "q0_factor_feasible_masks"
        ],
        "q1_feasible_masks": 0,
        "q2_feasible_masks": 0,
        "closure_stage": "two q=0 exceptions both q=1 infeasible",
    })
    per_k.append({
        "k": 12,
        **k12["filter_funnel"],
        "closure_stage": "four q=1 exceptions all q=2 infeasible",
    })
    assert [item["k"] for item in per_k] == list(range(13))
    assert all(
        item["all_deletion_masks"] == 4 * math.comb(37, item["k"])
        for item in per_k
    )
    assert all(item["q2_feasible_masks"] == 0 for item in per_k)

    payload = {
        "theorem": (
            "In the corrected rot4 multigraph model, for each of the four "
            "V40 bases, no exact NTIL lies at normalized deletion distance "
            "k<=12. Hence any exact NTIL reachable from one of these bases "
            "has normalized distance at least 13."
        ),
        "scope_limit": (
            "This is a local rigidity theorem around four V40 bases, not a "
            "global nonexistence theorem for m=37 and not an exact solution."
        ),
        "normalization": (
            "k is the number of old C4 orbits removed after cancelling "
            "redundant same-orientation delete-and-reselect pairs; exactly "
            "k genuinely new C4 orbits are added."
        ),
        "corrected_multigraph_semantics": (
            "Opposite orientations (u,v) and (v,u) are distinct parallel "
            "edges and may coexist; exact old-orientation reselection is "
            "forbidden only by normalization."
        ),
        "minimum_defect_hitting_sizes": minimum_hitting_sizes,
        "per_k": per_k,
        "global_filter_funnel_k0_k12": {
            "all_deletion_masks": sum(
                item["all_deletion_masks"] for item in per_k
            ),
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in per_k
            ),
            "q0_factor_feasible_masks": sum(
                item["q0_factor_feasible_masks"] for item in per_k
            ),
            "q1_feasible_masks": sum(
                item["q1_feasible_masks"] for item in per_k
            ),
            "q2_feasible_masks": 0,
        },
        "independent_crosschecks": {
            "antiparallel_geometry_pairs": antiparallel[
                "unordered_pair_count"
            ],
            "antiparallel_geometry_failures": antiparallel["failure_count"],
            "k5_k11_cpp_negative_cp_sat_samples": lower_crosscheck[
                "negative_sample_count"
            ],
            "k5_k11_cpp_positive_cp_sat_samples": lower_crosscheck[
                "positive_sample_count"
            ],
            "k12_cpp_negative_cp_sat_samples": sum(
                item["sample_count"]
                for item in k12_crosscheck["records"]
            ),
            "crosschecks_passed": True,
        },
        "certificate_sha256": {
            name: sha256(name)
            for name in [
                lower_name,
                k11_name,
                k11_q1_name,
                k12_name,
                lower_crosscheck_name,
                k12_crosscheck_name,
                antiparallel_name,
            ]
        },
        "all_k0_k12_closed": True,
        "normalized_escape_radius_lower_bound": 13,
    }
    output = HERE / "rot4_corrected_multigraph_radius13_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "theorem": payload["theorem"],
        "global_filter_funnel_k0_k12": payload[
            "global_filter_funnel_k0_k12"
        ],
        "independent_crosschecks": payload["independent_crosschecks"],
        "all_k0_k12_closed": True,
        "normalized_escape_radius_lower_bound": 13,
    }, indent=2))
    print(output)


if __name__ == "__main__":
    main()

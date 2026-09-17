"""Independent CP-SAT spot cross-check of corrected k=5..11 C++ audits."""

from __future__ import annotations

import json
from pathlib import Path

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS
from crosscheck_rot4_multigraph_factor_exhaustive import solve_fixed
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def indices(mask: int) -> list[int]:
    return [index for index in range(M) if (mask >> index) & 1]


def main() -> None:
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = {
        item["id"]: item
        for item in archive["archive"]
        if item["id"].startswith("v40_")
    }
    negative_records = []
    for size in range(5, 12):
        for base_id, base in sorted(bases.items()):
            defects = json.loads(
                (SOURCE_OUTPUTS / f"defect_hitting_{base_id}.json").read_text(
                    encoding="utf-8"
                )
            )["defect_owner_sets"]
            blockers = candidate_blockers(base)
            chosen = []
            for adjacency in range(size):
                path = HERE / (
                    f"rot4_multigraph_factor_direct_{base_id}_"
                    f"k{size}_a{adjacency}_q0.json"
                )
                item = json.loads(path.read_text(encoding="utf-8"))
                if item["factor_feasible_masks"]:
                    continue
                for mask in item["sample_hitting_masks"]:
                    if mask not in chosen:
                        chosen.append(mask)
                    if len(chosen) == 2:
                        break
                if len(chosen) == 2:
                    break
            for mask in chosen:
                status, wall_s = solve_fixed(
                    base, defects, blockers, indices(mask)
                )
                if status != "INFEASIBLE":
                    raise RuntimeError(
                        f"C++/CP-SAT negative mismatch: {base_id} k={size} "
                        f"mask={mask} status={status}"
                    )
                negative_records.append({
                    "base": base_id,
                    "k": size,
                    "mask": mask,
                    "removed_indices": indices(mask),
                    "cp_sat_status": status,
                    "wall_s": wall_s,
                })

    positive_source = json.loads(
        (
            HERE / "rot4_multigraph_factor_direct_v40_02_k11_a1_q0.json"
        ).read_text(encoding="utf-8")
    )
    base = bases["v40_02"]
    defects = json.loads(
        (SOURCE_OUTPUTS / "defect_hitting_v40_02.json").read_text(
            encoding="utf-8"
        )
    )["defect_owner_sets"]
    blockers = candidate_blockers(base)
    positive_records = []
    for mask in positive_source["feasible_masks"]:
        status, wall_s = solve_fixed(base, defects, blockers, indices(mask))
        if status not in ("OPTIMAL", "FEASIBLE"):
            raise RuntimeError(
                f"C++/CP-SAT positive mismatch: mask={mask} status={status}"
            )
        positive_records.append({
            "base": "v40_02",
            "k": 11,
            "A": 1,
            "mask": mask,
            "removed_indices": indices(mask),
            "cp_sat_status": status,
            "wall_s": wall_s,
        })

    payload = {
        "method": (
            "Independently rebuild the corrected q=0 CP-SAT multigraph model "
            "for up to two C++-negative defect-hitting masks per (k,base), "
            "plus both C++-positive k=11 masks."
        ),
        "negative_sample_count": len(negative_records),
        "negative_samples_all_cp_sat_infeasible": all(
            item["cp_sat_status"] == "INFEASIBLE"
            for item in negative_records
        ),
        "positive_sample_count": len(positive_records),
        "positive_samples_all_cp_sat_feasible": all(
            item["cp_sat_status"] in ("OPTIMAL", "FEASIBLE")
            for item in positive_records
        ),
        "negative_records": negative_records,
        "positive_records": positive_records,
        "passed": True,
    }
    output = HERE / "rot4_k5_k11_corrected_multigraph_crosscheck.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "negative_sample_count": payload["negative_sample_count"],
        "positive_sample_count": payload["positive_sample_count"],
        "passed": payload["passed"],
    }, indent=2))
    print(output)


if __name__ == "__main__":
    main()

"""Independent CP-SAT cross-check of exhaustive C++ q=0 factor audits."""

from __future__ import annotations

import json
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import build_general_model


HERE = Path(__file__).resolve().parent


def solve_fixed(base, defects, blockers, removed_indices):
    problem = build_general_model(
        base,
        defects,
        blockers,
        len(removed_indices),
        None,
        None,
        None,
        None,
        None,
        None,
        True,
        False,
    )
    removed_set = set(removed_indices)
    for index, variable in enumerate(problem["removed"]):
        problem["model"].Add(variable == (index in removed_set))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 1
    status = solver.Solve(problem["model"])
    return solver.StatusName(status), round(solver.WallTime(), 4)


def main() -> None:
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = {item["id"]: item for item in archive["archive"]}
    records = []
    for base_number in range(1, 5):
        base_id = f"v40_{base_number:02d}"
        base = bases[base_id]
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base_id}.json").read_text(
                encoding="utf-8"
            )
        )
        blockers = candidate_blockers(base)
        audit_path = (
            HERE
            / f"rot4_multigraph_factor_exhaustive_{base_id}_"
            "k12_a6_b1_c0_q0.json"
        )
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        samples = []
        for mask in audit["sample_hitting_masks"][:5]:
            removed = [i for i in range(M) if (mask >> i) & 1]
            status, wall_s = solve_fixed(
                base, hitting["defect_owner_sets"], blockers, removed
            )
            samples.append(
                {
                    "mask": mask,
                    "removed_indices": removed,
                    "cp_sat_status": status,
                    "wall_s": wall_s,
                }
            )
            assert status == "INFEASIBLE"
        # Positive control: after deleting the entire base, reversing every
        # old directed edge is an allowed normalized q=0 replacement factor.
        positive_status, positive_wall = solve_fixed(
            base,
            hitting["defect_owner_sets"],
            blockers,
            list(range(M)),
        )
        assert positive_status in ("OPTIMAL", "FEASIBLE")
        records.append(
            {
                "base": base_id,
                "cpp_all_factor_infeasible": audit["all_factor_infeasible"],
                "sample_count": len(samples),
                "sample_cp_sat_all_infeasible": all(
                    item["cp_sat_status"] == "INFEASIBLE" for item in samples
                ),
                "samples": samples,
                "all_37_removed_positive_control": {
                    "cp_sat_status": positive_status,
                    "wall_s": positive_wall,
                },
            }
        )
        print(
            f"{base_id}: 5/5 C++-negative masks CP-INFEASIBLE; "
            f"all-removed control={positive_status}",
            flush=True,
        )
    payload = {
        "method": (
            "For each basin, independently rebuild the corrected CP-SAT "
            "multigraph model on five C++-enumerated defect-hitting masks. "
            "Also test the all-37-removed positive control."
        ),
        "records": records,
        "passed": all(
            item["sample_cp_sat_all_infeasible"]
            and item["all_37_removed_positive_control"]["cp_sat_status"]
            in ("OPTIMAL", "FEASIBLE")
            for item in records
        ),
    }
    output = HERE / "rot4_multigraph_factor_exhaustive_crosscheck.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"passed": payload["passed"]}, indent=2))
    print(output)


if __name__ == "__main__":
    main()

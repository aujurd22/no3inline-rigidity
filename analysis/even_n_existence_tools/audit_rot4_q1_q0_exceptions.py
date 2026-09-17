"""Fix every recorded q=0 exception and independently decide it at q=1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    build_general_model,
    short_direction_lines,
)
from solve_joint_rot4_line_cuts import add_line_capacity, extract_solution


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument(
        "--A",
        type=int,
        action="append",
        help="optional adjacency value filter; omit to audit every source mask",
    )
    parser.add_argument(
        "--source-glob",
        default="rot4_multigraph_factor_exhaustive_v40_*_k12_a*_q0.json",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="factor archive JSON (defaults to the historical V40 archive)",
    )
    parser.add_argument(
        "--hitting-dir",
        type=Path,
        default=None,
        help="directory containing the defect-owner files",
    )
    parser.add_argument(
        "--hitting-prefix",
        default="defect_hitting_",
        help="filename prefix before BASE.json",
    )
    parser.add_argument("--short-direction-q", type=int, default=1)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    wanted_A = set(args.A) if args.A else None

    archive_path = args.archive or (SOURCE_OUTPUTS / "exact_factor_archive.json")
    hitting_dir = args.hitting_dir or SOURCE_OUTPUTS
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    bases = {item["id"]: item for item in archive["archive"]}
    source_records = []
    incomplete_sources = []
    masks_by_base: dict[str, set[int]] = {}
    for path in sorted(HERE.glob(args.source_glob)):
        item = json.loads(path.read_text(encoding="utf-8"))
        feasible_count = item.get("factor_feasible_masks", 0)
        if not feasible_count:
            continue
        method = item.get("method", {})
        if not isinstance(method, dict):
            method = {}
        profile = method.get("deletion_run_lengths")
        A = method.get("A")
        if A is None and profile:
            A = args.size - len(profile)
        if A is None and wanted_A is not None:
            continue
        if wanted_A is not None and A not in wanted_A:
            continue
        masks = item.get("feasible_masks", [])
        source = {
            "certificate": path.name,
            "base": item["base"],
            "A": A,
            "profile": profile,
            "q0_factor_feasible_masks": feasible_count,
            "recorded_mask_count": len(masks),
        }
        source_records.append(source)
        if len(masks) != feasible_count:
            incomplete_sources.append(source)
            continue
        masks_by_base.setdefault(item["base"], set()).update(masks)

    if incomplete_sources:
        raise RuntimeError(
            "Rerun q0 sources with the v3 executable: "
            + ", ".join(item["certificate"] for item in incomplete_sources)
        )

    q_lines = short_direction_lines(args.short_direction_q)
    records = []
    for base_id, masks in sorted(masks_by_base.items()):
        base = bases[base_id]
        hitting = json.loads(
            (
                hitting_dir / f"{args.hitting_prefix}{base_id}.json"
            ).read_text(encoding="utf-8")
        )
        blockers = candidate_blockers(base)
        for mask in sorted(masks):
            removed_indices = [i for i in range(M) if (mask >> i) & 1]
            problem = build_general_model(
                base,
                hitting["defect_owner_sets"],
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
            for key in q_lines:
                add_line_capacity(problem, key)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30
            solver.parameters.num_search_workers = 1
            solver.parameters.random_seed = 2026071917
            status = solver.Solve(problem["model"])
            record = {
                "base": base_id,
                "mask": mask,
                "removed_indices": removed_indices,
                "q_status": solver.StatusName(status),
                "wall_s": round(solver.WallTime(), 4),
                "branches": solver.NumBranches(),
                "conflicts": solver.NumConflicts(),
            }
            if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
                record["solution"] = extract_solution(problem, solver)
            records.append(record)
            if not args.quiet:
                print(
                    f"{base_id} mask={mask}: {record['q_status']} "
                    f"{record['wall_s']}s",
                    flush=True,
                )

    payload = {
        "archive": str(archive_path.resolve()),
        "hitting_dir": str(hitting_dir.resolve()),
        "hitting_prefix": args.hitting_prefix,
        "A_values": sorted(wanted_A) if wanted_A is not None else None,
        "k": args.size,
        "short_direction_q": args.short_direction_q,
        "line_orbit_count": len(q_lines),
        "q0_source_records": source_records,
        "unique_q0_exception_mask_count": sum(
            len(masks) for masks in masks_by_base.values()
        ),
        "q_status_histogram": {
            status: sum(item["q_status"] == status for item in records)
            for status in sorted({item["q_status"] for item in records})
        },
        "all_sources_infeasible": all(
            item["q_status"] == "INFEASIBLE" for item in records
        ),
        "records": records,
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "sources": len(source_records),
        "masks": payload["unique_q0_exception_mask_count"],
        "q_status_histogram": payload["q_status_histogram"],
        "all_closed": payload["all_sources_infeasible"],
    }, indent=2))
    print(output)


if __name__ == "__main__":
    main()

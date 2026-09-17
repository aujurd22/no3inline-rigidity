"""Close the q=1-surviving V20 k=11 masks with full dynamic line cuts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import solve_general_with_cuts


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    bases = {item["id"]: item for item in archive["archive"]}
    q1 = json.loads((HERE / args.source).read_text())
    survivors = [item for item in q1["records"] if item["q1_status"] == "OPTIMAL"]
    records = []
    for item in survivors:
        base_id = item["base"]
        base = bases[base_id]
        hitting = json.loads(
            (HERE / f"v20_defect_hitting_{base_id}.json").read_text()
        )
        if not args.quiet:
            print(f"{base_id} mask={item['mask']}: full cuts", flush=True)
        result = solve_general_with_cuts(
            base,
            hitting["defect_owner_sets"],
            candidate_blockers(base),
            args.size,
            100,
            5.0,
            120.0,
            4,
            1,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            item["removed_indices"],
        )
        records.append(
            {
                "base": base_id,
                "mask": item["mask"],
                "removed_indices": item["removed_indices"],
                "result": result,
            }
        )
        if not args.quiet:
            print(
                f"  {result['status']} rounds={result['round_count']} "
                f"cuts={result['line_cut_count']} t={result['elapsed_s']}s",
                flush=True,
            )
    payload = {
        "source": args.source,
        "size": args.size,
        "record_count": len(records),
        "all_closed": all(
            item["result"]["status"] == "INFEASIBLE" for item in records
        ),
        "records": records,
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"all_closed": payload["all_closed"]}, indent=2))
    print(output)


if __name__ == "__main__":
    main()

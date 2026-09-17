"""Feed one verified V20 base to the CUDA fixed-weight mask prefilter."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import directed_cell
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def owner_mask(owners) -> int:
    return sum(1 << int(owner) for owner in owners)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--exe", default="v20_gpu_mask_prefilter.exe")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (HERE / f"v20_defect_hitting_{args.base}.json").read_text()
    )
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]
    incident = defaultdict(list)
    for index, (u, v) in enumerate(base["edges"]):
        incident[u].append(index)
        incident[v].append(index)
    assert all(len(incident[vertex]) == 2 for vertex in range(37))

    tokens = [str(args.size), str(len(defects))]
    tokens.extend(str(value) for value in defects)
    for vertex in range(37):
        tokens.extend(str(value) for value in incident[vertex])
    exact_old = {
        directed_cell(tuple(edge), bit)
        for edge, bit in zip(base["edges"], base["bits"])
    }
    blockers = candidate_blockers(base)
    for u in range(37):
        for v in range(37):
            values = blockers[(u, v)]
            tokens.extend(
                [
                    str(int((u, v) in exact_old)),
                    str(len(values)),
                    *(str(value) for value in values),
                ]
            )
    started = time.time()
    completed = subprocess.run(
        [str((HERE / args.exe).resolve())],
        input=" ".join(tokens),
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    payload.update(
        {
            "base": args.base,
            "defect_count": len(defects),
            "wall_s": round(time.time() - started, 4),
            "method": (
                "CUDA 18+19 split fixed-weight enumeration; exact defect "
                "hitting, base-factor adjacency classification, and exact "
                "q=0 root-option necessary filtering"
            ),
        }
    )
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(output)


if __name__ == "__main__":
    main()

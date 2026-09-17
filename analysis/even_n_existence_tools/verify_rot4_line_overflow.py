"""Reconstruct and verify primal line-overflow witnesses from JSON evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_rot4_shadow_factor import M, N, SOURCE_OUTPUTS, c4_lifts, directed_cell
from solve_joint_rot4_general_factor import short_direction_lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )["archive"]
    bases = {base["id"]: base for base in archive}

    for raw_path in args.files:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["status"] not in ("OPTIMAL", "FEASIBLE"):
            print(f"{path.name}: {payload['status']} (no primal witness)")
            continue
        parameters = payload["parameters"]
        base = bases[parameters["base"]]
        removed = set(payload["solution"]["removed_indices"])
        base_cells = [
            directed_cell(tuple(edge), bit)
            for edge, bit in zip(base["edges"], base["bits"])
        ]
        chosen_cells = [tuple(cell) for cell in payload["solution"]["chosen_cells"]]
        cells = [
            cell for index, cell in enumerate(base_cells) if index not in removed
        ] + chosen_cells
        assert len(cells) == M
        points = [point for cell in cells for point in c4_lifts(cell)]
        assert len(points) == 4 * M
        assert len(set(points)) == len(points)
        row_counts = Counter(x for x, _ in points)
        column_counts = Counter(y for _, y in points)
        assert set(row_counts) == set(range(N))
        assert set(column_counts) == set(range(N))
        assert set(row_counts.values()) == {2}
        assert set(column_counts.values()) == {2}

        q = parameters.get("direction_q", 1)
        hard_q = parameters.get("hard_direction_q", 0)
        hard_keys = set(short_direction_lines(hard_q))
        for key in hard_keys:
            a, b, c = key
            assert sum(a * x + b * y == c for x, y in points) <= 2
        explicit = payload.get("objective_line_keys", [])
        objective_keys = (
            [tuple(key) for key in explicit]
            if explicit
            else [
                key
                for key in short_direction_lines(q)
                if key not in hard_keys
            ]
        )
        active = []
        for key in objective_keys:
            a, b, c = key
            count = sum(a * x + b * y == c for x, y in points)
            if count > 2:
                active.append({"line": list(key), "overflow": count - 2})
        objective = sum(item["overflow"] for item in active)
        assert objective == payload["objective"]
        recorded = payload.get(
            "active_short_line_overflows",
            payload.get("active_diagonal_overflows", []),
        )
        assert active == recorded
        print(
            f"{path.name}: verified base={parameters['base']} "
            f"A={parameters['adjacency_count']} q={q} "
            f"objective={objective} active={len(active)}"
        )


if __name__ == "__main__":
    main()

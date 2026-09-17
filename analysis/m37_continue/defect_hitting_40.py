"""Hitting-set and coverage frontier for the verified 40-defect factor."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from defect_hitting_analysis import defect_owner_sets, max_coverage, solve_hitting


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="40", help="40 or an exact archive id")
    parser.add_argument("--out", default="defect_hitting_40.json")
    args = parser.parse_args()
    if args.base == "40":
        best = json.loads((OUT / "weighted_40_verified.json").read_text(encoding="utf-8"))
        edges = [tuple(edge) for edge in best["edges"]]
        bits = best["weighted_repeat_exact"]["bits"]
        expected = 10
    else:
        archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
        best = next(item for item in archive["archive"] if item["id"] == args.base)
        edges = [tuple(edge) for edge in best["edges"]]
        bits = best["bits"]
        expected = best["value"] // 4
    defects = defect_owner_sets(edges, bits)
    assert len(defects) == expected
    hot = Counter(index for defect in defects for index in defect)
    payload = {
        "base": args.base,
        "edges": [list(edge) for edge in edges],
        "bits": bits,
        "defect_owner_sets": [list(defect) for defect in defects],
        "hotness_by_defect_orbit": dict(hot),
        "minimum_hitting_set": solve_hitting(edges, defects, False),
        "minimum_independent_hitting_set": solve_hitting(edges, defects, True),
        "coverage_frontier": [
            max_coverage(edges, defects, independent, budget)
            for independent in (False, True)
            for budget in range(1, 7)
        ],
    }
    (OUT / args.out).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print("defects", defects)
    print("minimum", payload["minimum_hitting_set"])
    print("independent", payload["minimum_independent_hitting_set"])
    for item in payload["coverage_frontier"]:
        print(item)


if __name__ == "__main__":
    main()

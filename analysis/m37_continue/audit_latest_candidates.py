"""Independently audit several late candidate JSON files from the source tree."""

from __future__ import annotations

import json
from pathlib import Path

from signed_nae_core import (
    count_clause_violations,
    enumerate_clauses,
    geometry_bad_count,
    validate_factor,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
SOURCE = Path(
    r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36"
    r"\no3inline-rigidity\analysis\results"
)


CASES = [
    ("alts_best.json", False),
    ("cc_best.json", False),
    ("violation_improved_edges.json", True),
]


def main():
    results = []
    for filename, directed_cells in CASES:
        raw = json.loads((SOURCE / filename).read_text(encoding="utf-8"))
        claimed = raw.get("clauses", raw.get("best_clauses"))
        bits = None
        if directed_cells:
            edges, bits = [], []
            for x, y in raw["edges"]:
                u, v = sorted((x, y))
                edges.append((u, v))
                bits.append(0 if (x, y) == (u, v) else 1)
        else:
            edges = [tuple(sorted(e)) for e in raw["edges"]]
        factor = validate_factor(37, edges)
        item = {
            "file": filename,
            "claimed_clauses": claimed,
            "factor": factor,
        }
        if factor["is_2factor"]:
            clauses = enumerate_clauses(37, edges)
            item["independent_clauses"] = len(clauses)
            item["claim_matches"] = claimed == len(clauses)
            if bits is not None:
                item["independent_clause_violations"] = count_clause_violations(clauses, bits)
                item["independent_geometry"] = geometry_bad_count(37, edges, bits)
        results.append(item)
        print(item, flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "latest_candidate_audit.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()


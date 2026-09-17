"""Full independent verification of every sub-16 joint-search candidate."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from signed_nae_core import (
    build_ising,
    c4_lifts,
    count_clause_violations,
    enumerate_clauses,
    geometry_bad_count,
    solve_clause_cp_sat,
    validate_factor,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def points_from_state(m, edges, bits):
    points = []
    for (u, v), bit in zip(edges, bits):
        points.extend(c4_lifts(m, (u, v) if bit == 0 else (v, u)))
    return points


def brute_bad_triples(points):
    bad = 0
    for p, q, r in itertools.combinations(points, 3):
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        bad += det == 0
    return bad


def main():
    candidates = []
    seen = set()
    for filename in (
        "joint_plateau_lns.json",
        "joint_plateau_v14_deep.json",
        "joint_plateau_v14_slack.json",
    ):
        source = json.loads((OUT / filename).read_text(encoding="utf-8"))
        for layer in source["layers"]:
            for item in layer["exact"]:
                if item["solve"].get("violations") != 14:
                    continue
                key = tuple(sorted(tuple(sorted(e)) for e in item["candidate"]["edges"]))
                if key not in seen:
                    seen.add(key)
                    item["source_file"] = filename
                    candidates.append(item)

    exhaustive_name = "exhaustive_v14_neighbors.json"
    exhaustive = json.loads((OUT / exhaustive_name).read_text(encoding="utf-8"))
    for base in exhaustive["bases"]:
        for item in base["exact"]:
            if item["solve"].get("violations") != 14:
                continue
            key = tuple(sorted(tuple(sorted(e)) for e in item["candidate"]["edges"]))
            if key not in seen:
                seen.add(key)
                item["source_file"] = exhaustive_name
                candidates.append(item)

    verified = []
    for index, item in enumerate(candidates, 1):
        candidate = item["candidate"]
        edges = [tuple(e) for e in candidate["edges"]]
        bits = item["solve"]["bits"]
        factor = validate_factor(37, edges)
        clauses = enumerate_clauses(37, edges)
        pairs, _, missing = build_ising(37, clauses)
        clause_v = count_clause_violations(clauses, bits)
        geometry = geometry_bad_count(37, edges, bits)
        points = points_from_state(37, edges, bits)
        brute = brute_bad_triples(points)
        exact = solve_clause_cp_sat(clauses, 37, 120.0)
        record = {
            "name": f"joint_v14_{index}",
            "source_file": item["source_file"],
            "parent": candidate.get("parent", item["source_file"]),
            "edges": candidate["edges"],
            "bits": bits,
            "factor": factor,
            "clauses": len(clauses),
            "complement_pairs": len(pairs),
            "missing_complements": len(missing),
            "independent_clause_violations": clause_v,
            "line_key_geometry": geometry,
            "bruteforce_bad_triples": brute,
            "bad_triples_per_clause_violation": brute / clause_v,
            "repeat_exact_solve": exact,
        }
        assert factor["edge_count"] == 37
        assert set(factor["degree_histogram"]) == {2}
        assert len(missing) == 0
        assert clause_v == 14
        assert brute == geometry["bad_triples"]
        assert exact["status"] == "OPTIMAL" and exact["violations"] == 14
        verified.append(record)
        print(
            record["name"],
            f"clauses={len(clauses)} V={clause_v} bad={brute} exact={exact['status']}",
            flush=True,
        )

    (OUT / "joint_breakthrough_verified.json").write_text(
        json.dumps(verified, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

"""Independent verification of the diagonal-safe 40-defect candidate."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from diagonal_factor_search import diagonal_stats
from signed_nae_core import (
    build_ising,
    c4_lifts,
    count_clause_violations,
    enumerate_clauses,
    geometry_bad_count,
    solve_clause_cp_sat,
    solve_cp_sat,
    validate_factor,
)
from weighted_factor_search import build_state


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def points_from_state(edges, bits):
    points = []
    for (u, v), bit in zip(edges, bits):
        points.extend(c4_lifts(37, (u, v) if bit == 0 else (v, u)))
    return points


def brute_bad(points):
    total = 0
    for p, q, r in itertools.combinations(points, 3):
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        total += det == 0
    return total


def main():
    source = json.loads(
        (OUT / "partial_hitting_repair_slack1.json").read_text(encoding="utf-8")
    )
    item = source["exact"][0]
    candidate = item["candidate"]
    edges = [tuple(edge) for edge in candidate["edges"]]
    bits = item["solve"]["bits"]
    factor = validate_factor(37, edges)
    diagonal = diagonal_stats(37, edges)
    geometry = geometry_bad_count(37, edges, bits)
    brute = brute_bad(points_from_state(edges, bits))

    _, _, _, constant, weighted_j = build_state(edges)
    repeated = solve_cp_sat(constant, weighted_j, 240.0, hint=bits)
    if repeated.get("bits") is not None:
        repeated["geometry"] = geometry_bad_count(37, edges, repeated["bits"])

    clauses = enumerate_clauses(37, edges)
    pairs, _, missing = build_ising(37, clauses)
    legacy_at_bits = count_clause_violations(clauses, bits)
    legacy_exact = solve_clause_cp_sat(clauses, 37, 120.0, hint=bits)
    record = {
        "name": "m37_weighted_40",
        "source": "partial_hitting_repair_slack1.json",
        "selected_indices": candidate["selected_indices"],
        "covered_old_defects": candidate["covered_old_defects"],
        "edges": candidate["edges"],
        "bits": bits,
        "factor": factor,
        "diagonal_invariant": diagonal,
        "geometry_line_key": geometry,
        "geometry_bruteforce": brute,
        "weighted_repeat_exact": repeated,
        "legacy_clause_count": len(clauses),
        "legacy_complement_pairs": len(pairs),
        "legacy_missing_complements": len(missing),
        "legacy_violations_at_weighted_bits": legacy_at_bits,
        "legacy_exact": legacy_exact,
    }
    assert factor["is_2factor"]
    assert diagonal["bad_diagonal_triples"] == 0
    assert geometry["distinct_point_count"] == 148
    assert brute == geometry["bad_triples"] == 40
    assert repeated["status"] == "OPTIMAL" and repeated["violations"] == 40
    (OUT / "weighted_40_verified.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    print(
        f"geometry={brute} weighted={repeated['status']} "
        f"legacyV={legacy_at_bits} legacyOpt={legacy_exact.get('violations')}",
        flush=True,
    )


if __name__ == "__main__":
    main()

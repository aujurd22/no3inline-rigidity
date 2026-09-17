"""Independent full verification of the diagonal-safe 48/52 breakthroughs."""

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
        (OUT / "weighted_safe_factor_search_layer2.json").read_text(encoding="utf-8")
    )
    verified = []
    for item in source["exact"]:
        if item["solve"].get("violations", 10**9) > 52:
            continue
        candidate = item["candidate"]
        edges = [tuple(e) for e in candidate["edges"]]
        bits = item["solve"]["bits"]
        factor = validate_factor(37, edges)
        diagonal = diagonal_stats(37, edges)
        geometry = geometry_bad_count(37, edges, bits)
        brute = brute_bad(points_from_state(edges, bits))

        _, _, _, constant, weighted_j = build_state(edges)
        repeated_weighted = solve_cp_sat(constant, weighted_j, 180.0, hint=bits)
        if repeated_weighted.get("bits") is not None:
            repeated_weighted["geometry"] = geometry_bad_count(
                37, edges, repeated_weighted["bits"]
            )

        clauses = enumerate_clauses(37, edges)
        pair_list, _, missing = build_ising(37, clauses)
        unweighted_at_weighted_bits = count_clause_violations(clauses, bits)
        unweighted_exact = solve_clause_cp_sat(clauses, 37, 120.0, hint=bits)
        record = {
            "name": f"m37_weighted_{geometry['bad_triples']}",
            "edges": candidate["edges"],
            "bits": bits,
            "factor": factor,
            "diagonal_invariant": diagonal,
            "geometry_line_key": geometry,
            "geometry_bruteforce": brute,
            "weighted_repeat_exact": repeated_weighted,
            "legacy_clause_count": len(clauses),
            "legacy_complement_pairs": len(pair_list),
            "legacy_missing_complements": len(missing),
            "legacy_violations_at_weighted_bits": unweighted_at_weighted_bits,
            "legacy_exact": unweighted_exact,
        }
        assert factor["is_2factor"]
        assert diagonal["bad_diagonal_triples"] == 0
        assert brute == geometry["bad_triples"] == item["solve"]["violations"]
        assert repeated_weighted["status"] == "OPTIMAL"
        assert repeated_weighted["violations"] == geometry["bad_triples"]
        verified.append(record)
        print(
            record["name"],
            f"geometry={brute} weighted={repeated_weighted['status']} "
            f"legacyV={unweighted_at_weighted_bits} "
            f"legacyOpt={unweighted_exact.get('violations')}",
            flush=True,
        )
    (OUT / "weighted_breakthrough_verified.json").write_text(
        json.dumps(verified, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

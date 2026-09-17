"""Exhaustively audit the two-orientation (parallel-edge) rot4 geometry.

For every unordered fundamental pair {u,v}, u<v, this checks the union of the
two C4 orbits represented by (u,v) and (v,u).  In the reduced multigraph these
are two parallel edges.  The audit is deliberately independent of CP-SAT: it
checks distinctness, row/column degrees, and all collinear triples directly in
the lifted 74 by 74 grid.
"""

from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from analyze_rot4_shadow_factor import M, N, c4_lifts


HERE = Path(__file__).resolve().parent


def line_key(p: tuple[int, int], q: tuple[int, int]) -> tuple[int, int, int]:
    """Return a primitive canonical key a*x+b*y=c through two points."""
    x1, y1 = p
    x2, y2 = q
    a, b = y2 - y1, x1 - x2
    g = __import__("math").gcd(abs(a), abs(b))
    a, b = a // g, b // g
    c = a * x1 + b * y1
    if a < 0 or (a == 0 and b < 0):
        a, b, c = -a, -b, -c
    return a, b, c


def collinear_triples(
    points: tuple[tuple[int, int], ...],
) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]:
    bad = []
    for triple in combinations(points, 3):
        if line_key(triple[0], triple[1]) == line_key(triple[0], triple[2]):
            bad.append(triple)
    return bad


def main() -> None:
    failures = []
    row_patterns = Counter()
    column_patterns = Counter()
    orbit_intersection_sizes = Counter()
    pair_count = 0
    for u, v in combinations(range(M), 2):
        pair_count += 1
        forward = tuple(c4_lifts((u, v)))
        reverse = tuple(c4_lifts((v, u)))
        intersection = set(forward) & set(reverse)
        union = tuple(sorted(set(forward) | set(reverse)))
        rows = Counter(x for x, _ in union)
        columns = Counter(y for _, y in union)
        triples = collinear_triples(union)
        orbit_intersection_sizes[len(intersection)] += 1
        row_patterns[tuple(sorted(rows.values()))] += 1
        column_patterns[tuple(sorted(columns.values()))] += 1
        reasons = []
        if len(forward) != 4 or len(reverse) != 4:
            reasons.append("orbit_not_size_4")
        if intersection:
            reasons.append("orbits_intersect")
        if len(union) != 8:
            reasons.append("union_not_size_8")
        if any(value != 2 for value in rows.values()) or len(rows) != 4:
            reasons.append("row_degree_pattern_not_2x4")
        if any(value != 2 for value in columns.values()) or len(columns) != 4:
            reasons.append("column_degree_pattern_not_2x4")
        if triples:
            reasons.append("internal_collinear_triple")
        if reasons:
            failures.append(
                {
                    "cell_pair": [[u, v], [v, u]],
                    "reasons": reasons,
                    "forward": forward,
                    "reverse": reverse,
                    "intersection": sorted(intersection),
                    "row_counts": dict(rows),
                    "column_counts": dict(columns),
                    "bad_triples": triples,
                }
            )

    payload = {
        "grid_size": N,
        "fundamental_size": M,
        "unordered_pair_count": pair_count,
        "statement": (
            "For every u<v, the C4 orbits (u,v) and (v,u) are disjoint, "
            "their union has eight points, exactly two in each of four rows "
            "and columns, and contains no collinear triple."
        ),
        "orbit_intersection_size_histogram": dict(orbit_intersection_sizes),
        "row_multiplicity_pattern_histogram": {
            str(key): value for key, value in row_patterns.items()
        },
        "column_multiplicity_pattern_histogram": {
            str(key): value for key, value in column_patterns.items()
        },
        "failure_count": len(failures),
        "failures": failures,
    }
    output = HERE / "rot4_antiparallel_pair_model_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "pairs": pair_count,
                "failures": len(failures),
                "intersection_histogram": dict(orbit_intersection_sizes),
                "row_patterns": {
                    str(key): value for key, value in row_patterns.items()
                },
                "column_patterns": {
                    str(key): value for key, value in column_patterns.items()
                },
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()

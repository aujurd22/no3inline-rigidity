"""Exact multiplicity-weighted Ising objective for geometric bad triples.

The existing Boolean clause model records only whether a cell-orientation
pattern is forbidden.  This script records how many collinear point triples the
pattern creates.  Complement symmetry still cancels odd Fourier terms, so the
true geometric defect count remains a quadratic Ising objective whenever no
bad triple is contained in only one or two C4 orbits.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

from signed_nae_core import c4_lifts, geometry_bad_count, solve_cp_sat


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def collinear_count(points):
    total = 0
    for p, q, r in itertools.combinations(points, 3):
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        total += det == 0
    return total


def enumerate_pair_weighted(m, edges):
    patterns = []
    lifts = [(c4_lifts(m, e), c4_lifts(m, e[::-1])) for e in edges]
    for i, j in itertools.combinations(range(len(edges)), 2):
        for bits in range(4):
            points = lifts[i][bits & 1] + lifts[j][(bits >> 1) & 1]
            count = collinear_count(points)
            if count:
                patterns.append((i, j, bits, count))
    return patterns


def enumerate_weighted(m, edges):
    lifts = [(c4_lifts(m, e), c4_lifts(m, e[::-1])) for e in edges]
    patterns = []
    for a, b, c in itertools.combinations(range(len(edges)), 3):
        for bits in range(8):
            group_a = lifts[a][bits & 1]
            group_b = lifts[b][(bits >> 1) & 1]
            group_c = lifts[c][(bits >> 2) & 1]
            # Count only triples that genuinely use all three orbits.  A bad
            # triple contained in two orbits is handled once by pair_patterns;
            # counting it here would repeat it for every arbitrary third cell.
            weight = 0
            for p in group_a:
                for q in group_b:
                    for r in group_c:
                        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
                        weight += det == 0
            if weight:
                patterns.append((a, b, c, bits, weight))
    return patterns


def build_weighted_ising(n, patterns, pair_patterns):
    lookup = {(a, b, c, bits): weight for a, b, c, bits, weight in patterns}
    missing = []
    unequal = []
    constant_weight = 0
    jmat = [[0] * n for _ in range(n)]
    for a, b, c, bits, weight in patterns:
        partner = lookup.get((a, b, c, bits ^ 7))
        if partner is None:
            missing.append((a, b, c, bits))
        elif partner != weight:
            unequal.append(((a, b, c, bits, weight), partner))
        if bits > (bits ^ 7):
            continue
        constant_weight += weight
        signs = [1 if ((bits >> k) & 1) == 0 else -1 for k in range(3)]
        verts = (a, b, c)
        for x, y in ((0, 1), (0, 2), (1, 2)):
            i, j = verts[x], verts[y]
            w = weight * signs[x] * signs[y]
            jmat[i][j] += w
            jmat[j][i] += w

    pair_lookup = {(i, j, bits): weight for i, j, bits, weight in pair_patterns}
    for i, j, bits, weight in pair_patterns:
        partner = pair_lookup.get((i, j, bits ^ 3))
        if partner is None:
            missing.append((i, j, bits))
        elif partner != weight:
            unequal.append(((i, j, bits, weight), partner))
        if bits > (bits ^ 3):
            continue
        signs = [1 if ((bits >> k) & 1) == 0 else -1 for k in range(2)]
        # A complementary pair of 2-variable indicators is
        # w/2 * (1 + a_i*a_j*s_i*s_j).  Keep the common /4
        # normalization by doubling both the constant and coupling.
        constant_weight += 2 * weight
        w = 2 * weight * signs[0] * signs[1]
        jmat[i][j] += w
        jmat[j][i] += w
    return constant_weight, jmat, missing, unequal


def weighted_value(patterns, pair_patterns, bits):
    triple_value = sum(
        weight
        for a, b, c, pat, weight in patterns
        if (bits[a] | (bits[b] << 1) | (bits[c] << 2)) == pat
    )
    pair_value = sum(
        weight
        for i, j, pat, weight in pair_patterns
        if (bits[i] | (bits[j] << 1)) == pat
    )
    return triple_value + pair_value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--random-checks", type=int, default=100)
    args = parser.parse_args()

    bases = json.loads(
        (OUT / "joint_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    results = []
    for base in bases:
        print(f"{base['name']}: weighted enumeration", flush=True)
        edges = [tuple(e) for e in base["edges"]]
        assert all(
            collinear_count(c4_lifts(37, oriented)) == 0
            for u, v in edges
            for oriented in ((u, v), (v, u))
        )
        pair_patterns = enumerate_pair_weighted(37, edges)
        patterns = enumerate_weighted(37, edges)
        constant, jmat, missing, unequal = build_weighted_ising(
            37, patterns, pair_patterns
        )
        assert not missing and not unequal

        rng = random.Random(2026071700 + len(results))
        for _ in range(args.random_checks):
            bits = [rng.getrandbits(1) for _ in range(37)]
            weighted = weighted_value(patterns, pair_patterns, bits)
            geometric = geometry_bad_count(37, edges, bits)["bad_triples"]
            assert weighted == geometric, (weighted, geometric)

        solved = solve_cp_sat(constant, jmat, args.time_limit, hint=base["bits"])
        if solved.get("bits") is not None:
            solved["geometry"] = geometry_bad_count(37, edges, solved["bits"])
        multiplicities = {}
        for *_, weight in patterns:
            multiplicities[weight] = multiplicities.get(weight, 0) + 1
        record = {
            "name": base["name"],
            "edges": base["edges"],
            "unweighted_clauses": base["clauses"],
            "unweighted_optimum": 14,
            "input_orientation_bad_triples": base["bruteforce_bad_triples"],
            "weighted_patterns": len(patterns),
            "weighted_pair_patterns": len(pair_patterns),
            "pattern_multiplicity_histogram": multiplicities,
            "constant_pair_weight": constant,
            "random_geometry_identity_checks": args.random_checks,
            "weighted_exact": solved,
        }
        results.append(record)
        print(
            f"  patterns={len(patterns)} pairs={len(pair_patterns)} mult={multiplicities} "
            f"weighted={solved.get('status')} bad={solved.get('violations')} "
            f"geometry={solved.get('geometry', {}).get('bad_triples')}",
            flush=True,
        )
        (OUT / "weighted_geometry_results.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()

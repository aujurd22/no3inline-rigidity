"""Compare C4 orbits of geometric defects across all 56-defect factors."""

from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from pathlib import Path

from signed_nae_core import c4_lifts


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def rotate(point):
    x, y = point
    return 73 - y, x


def canonical_triple(points):
    images = []
    current = list(points)
    for _ in range(4):
        images.append(tuple(sorted(current)))
        current = [rotate(p) for p in current]
    return min(images)


def slope_type(points):
    p, q, _ = points
    dx, dy = q[0] - p[0], q[1] - p[1]
    g = math.gcd(abs(dx), abs(dy))
    a, b = abs(dx // g), abs(dy // g)
    return tuple(sorted((a, b)))


def analyse(item):
    edges = [tuple(e) for e in item["edges"]]
    solved = item.get("weighted_exact") or item["weighted_repeat_exact"]
    bits = solved["bits"]
    points = []
    owners = []
    for owner, ((u, v), bit) in enumerate(zip(edges, bits)):
        orbit = c4_lifts(37, (u, v) if bit == 0 else (v, u))
        points.extend(orbit)
        owners.extend([owner] * 4)

    defect_orbits = {}
    bad_count = 0
    for i, j, k in itertools.combinations(range(len(points)), 3):
        p, q, r = points[i], points[j], points[k]
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if det:
            continue
        bad_count += 1
        key = canonical_triple((p, q, r))
        defect_orbits.setdefault(
            key,
            {
                "points": [list(x) for x in key],
                "slope_type": list(slope_type(key)),
                "owner_arity": len({owners[i], owners[j], owners[k]}),
            },
        )
    assert bad_count == solved["violations"]
    assert bad_count % 4 == 0
    assert len(defect_orbits) == bad_count // 4
    slope_counts = Counter(tuple(x["slope_type"]) for x in defect_orbits.values())
    arity_counts = Counter(x["owner_arity"] for x in defect_orbits.values())
    return {
        "name": item["name"],
        "bad_triples": bad_count,
        "c4_defect_orbits": len(defect_orbits),
        "slope_type_counts": {f"{a},{b}": count for (a, b), count in slope_counts.items()},
        "owner_arity_counts": dict(arity_counts),
        "orbits": list(defect_orbits.values()),
    }


def main():
    weighted = json.loads(
        (OUT / "weighted_geometry_results.json").read_text(encoding="utf-8")
    )
    cases = [item for item in weighted if item["weighted_exact"]["violations"] == 56]
    breakthroughs = json.loads(
        (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    cases.extend(breakthroughs)
    results = [analyse(item) for item in cases]
    slope_sets = [set(item["slope_type_counts"]) for item in results]
    common = set.intersection(*slope_sets)
    union = set.union(*slope_sets)
    pairwise = []
    for left, right in itertools.combinations(results, 2):
        a, b = set(left["slope_type_counts"]), set(right["slope_type_counts"])
        pairwise.append(
            {
                "left": left["name"],
                "right": right["name"],
                "intersection": len(a & b),
                "jaccard": len(a & b) / len(a | b),
            }
        )
    payload = {
        "case_count": len(results),
        "common_slope_types": sorted(common),
        "union_slope_type_count": len(union),
        "pairwise": pairwise,
        "cases": results,
    }
    (OUT / "defect_orbit_results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(f"cases={len(results)} common_slopes={sorted(common)} union={len(union)}")
    for item in results:
        print(item["name"], item["owner_arity_counts"], item["slope_type_counts"])


if __name__ == "__main__":
    main()

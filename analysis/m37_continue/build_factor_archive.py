"""Collect the independently/exactly solved low-defect factors in one archive."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

from signed_nae_core import geometry_bad_count
from weighted_factor_search import is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def canonical_factor(edges, bits):
    items = []
    for raw, bit in zip(edges, bits):
        u, v = map(int, raw)
        if u <= v:
            items.append(((u, v), int(bit)))
        else:
            items.append(((v, u), 1 - int(bit)))
    items.sort()
    return [edge for edge, _ in items], [bit for _, bit in items]


def factor_key(edges):
    return tuple(sorted(tuple(sorted(map(int, edge))) for edge in edges))


def load_json(name):
    path = OUT / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def candidates():
    verified40 = load_json("weighted_40_verified.json")
    if verified40:
        yield (
            "weighted_40_verified",
            verified40["edges"],
            verified40["weighted_repeat_exact"],
        )

    for filename in (
        "partial_hitting_repair_slack1.json",
        "partial_hitting_40_slack1.json",
        "partial_hitting_40_slack2.json",
        "weighted_40_neighbors.json",
        "weighted_40_family_neighbors.json",
        "buffered_all_weighted.json",
        "buffered_hitting_repair.json",
        "partial_hitting_repair.json",
        "safe_path_relink_d2.json",
        "weighted_beam_escape_d3.json",
        "weighted_beam_escape_low_d4.json",
        "partial_hitting_v40_01_s1.json",
        "partial_hitting_v40_02_s1.json",
        "all_hitting_v40_04.json",
        "partial_hitting_v40_04_s1.json",
        "partial_hitting_v40_04_s2.json",
        "factor_crossover_d8.json",
        "joint_factor_sa_12x6000.json",
    ):
        payload = load_json(filename)
        if not payload:
            continue
        for item in payload.get("exact", []):
            solve = item.get("solve", {})
            candidate = item.get("candidate", {})
            if candidate.get("edges") and solve.get("bits") is not None:
                yield (f"{filename}:exact{item.get('rank')}", candidate["edges"], solve)

    breakthroughs = load_json("weighted_breakthrough_verified.json") or []
    for item in breakthroughs:
        solve = item.get("weighted_repeat_exact", {})
        if solve.get("bits") is not None:
            yield (item.get("name", "weighted_breakthrough"), item["edges"], solve)

    weighted = load_json("weighted_geometry_results.json") or []
    for item in weighted:
        solve = item.get("weighted_exact", {})
        if solve.get("bits") is not None:
            yield (item.get("name", "weighted_geometry"), item["edges"], solve)


def main():
    by_factor = {}
    rejected = []
    for source, raw_edges, solve in candidates():
        if solve.get("status") != "OPTIMAL":
            rejected.append({"source": source, "reason": solve.get("status")})
            continue
        edges, bits = canonical_factor(raw_edges, solve["bits"])
        key = factor_key(edges)
        geometry = geometry_bad_count(37, edges, bits)
        assert geometry["bad_triples"] == solve["violations"], (source, geometry, solve)
        assert len(edges) == 37 and len(key) == 37
        degree = Counter(v for edge in edges for v in edge)
        assert set(degree) == set(range(37)) and set(degree.values()) == {2}
        record = by_factor.setdefault(
            key,
            {
                "id": "",
                "value": solve["violations"],
                "edges": [list(edge) for edge in edges],
                "bits": bits,
                "diagonal_safe": is_diagonal_safe(edges),
                "geometry": geometry,
                "sources": [],
            },
        )
        assert record["value"] == solve["violations"]
        record["sources"].append(source)

    archive = sorted(by_factor.values(), key=lambda x: (x["value"], x["edges"]))
    counters = Counter()
    for index, item in enumerate(archive, 1):
        counters[item["value"]] += 1
        item["id"] = f"v{item['value']}_{counters[item['value']]:02d}"

    distances = []
    for left, right in itertools.combinations(archive, 2):
        lset = {tuple(edge) for edge in left["edges"]}
        rset = {tuple(edge) for edge in right["edges"]}
        distance = 37 - len(lset & rset)
        if left["value"] <= 48 and right["value"] <= 48:
            distances.append(
                {
                    "left": left["id"],
                    "right": right["id"],
                    "edge_distance": distance,
                    "common_edges": 37 - distance,
                }
            )
    distances.sort(key=lambda x: (x["edge_distance"], x["left"], x["right"]))
    payload = {
        "archive_size": len(archive),
        "value_histogram": dict(sorted(Counter(x["value"] for x in archive).items())),
        "safe_histogram": dict(
            sorted(Counter(x["value"] for x in archive if x["diagonal_safe"]).items())
        ),
        "archive": archive,
        "low_value_pair_distances": distances,
        "rejected_nonoptimal": rejected,
    }
    path = OUT / "exact_factor_archive.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"archive={len(archive)} values={payload['value_histogram']}")
    print("nearest low-value pairs:")
    for item in distances[:20]:
        print(
            f"  {item['left']} - {item['right']}: "
            f"distance={item['edge_distance']} common={item['common_edges']}"
        )
    print(path)


if __name__ == "__main__":
    main()

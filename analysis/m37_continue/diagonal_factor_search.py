"""Orientation-free diagonal invariant and exact search of nearby safe factors."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from signed_nae_core import c4_lifts
from spectral_neighbor_search import generate_switches
from weighted_factor_search import exact_weighted


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def canonical(edges):
    return tuple(sorted(tuple(sorted(e)) for e in edges))


def diagonal_signature(m, edges, swapped=False):
    plus = Counter()
    minus = Counter()
    for u, v in edges:
        cell = (v, u) if swapped else (u, v)
        for x, y in c4_lifts(m, cell):
            plus[x - y] += 1
            minus[x + y] += 1
    return plus, minus


def diagonal_stats(m, edges):
    plus, minus = diagonal_signature(m, edges, False)
    swapped_plus, swapped_minus = diagonal_signature(m, edges, True)
    assert plus == swapped_plus and minus == swapped_minus
    bad = sum(math.comb(count, 3) for count in plus.values() if count >= 3)
    bad += sum(math.comb(count, 3) for count in minus.values() if count >= 3)
    return {
        "bad_diagonal_triples": bad,
        "max_diagonal_occupancy": max([*plus.values(), *minus.values()]),
        "overfull_plus_lines": {str(k): v for k, v in plus.items() if v >= 3},
        "overfull_minus_lines": {str(k): v for k, v in minus.items() if v >= 3},
    }


def diverse(candidates, count):
    if not candidates:
        return []
    candidates = candidates[:]
    chosen = [candidates.pop(0)]
    while candidates and len(chosen) < count:
        item = max(
            candidates,
            key=lambda x: min(
                len(set(canonical(x["edges"])) ^ set(canonical(y["edges"])))
                for y in chosen
            ),
        )
        candidates.remove(item)
        chosen.append(item)
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-top", type=int, default=10)
    parser.add_argument("--exact-time", type=float, default=120.0)
    parser.add_argument("--out", default="diagonal_factor_search.json")
    args = parser.parse_args()

    verified = json.loads(
        (OUT / "joint_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    weighted = json.loads(
        (OUT / "weighted_geometry_results.json").read_text(encoding="utf-8")
    )
    weighted_by_name = {item["name"]: item for item in weighted}
    seen = set()
    candidates = []
    base_stats = []
    for base in verified:
        edges = [tuple(e) for e in base["edges"]]
        stats = diagonal_stats(37, edges)
        base_stats.append({"name": base["name"], **stats})
        warm = weighted_by_name[base["name"]]["weighted_exact"]["bits"]
        for left, right, e1, e2 in generate_switches(edges):
            candidate_edges = edges[:]
            candidate_edges[left], candidate_edges[right] = tuple(e1), tuple(e2)
            key = canonical(candidate_edges)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "parent": base["name"],
                    "switch_indices": [left, right],
                    "new_edges": [list(e1), list(e2)],
                    "edges": [list(e) for e in candidate_edges],
                    "bits": warm,
                    **diagonal_stats(37, candidate_edges),
                }
            )
    candidates.sort(
        key=lambda x: (x["bad_diagonal_triples"], x["max_diagonal_occupancy"])
    )
    histogram = Counter(item["bad_diagonal_triples"] for item in candidates)
    safe = [item for item in candidates if item["bad_diagonal_triples"] == 0]
    selected = diverse(safe, args.exact_top)
    payload = {
        "base_stats": base_stats,
        "unique_one_switch_neighbors": len(candidates),
        "diagonal_bad_histogram": dict(histogram),
        "safe_neighbor_count": len(safe),
        "best_diagonal_bad": candidates[0]["bad_diagonal_triples"],
        "top50": candidates[:50],
        "safe_top50": safe[:50],
        "exact_safe": [],
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"neighbors={len(candidates)} best_diag={candidates[0]['bad_diagonal_triples']} "
        f"safe={len(safe)} histogram={dict(sorted(histogram.items()))}",
        flush=True,
    )
    exact = []
    for rank, item in enumerate(selected, 1):
        solved = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solved})
        payload["exact_safe"] = exact
        (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"exact safe {rank}: parent={item['parent']} "
            f"-> {solved.get('status')} geometry={solved.get('violations')}",
            flush=True,
        )
    print(OUT / args.out)


if __name__ == "__main__":
    main()

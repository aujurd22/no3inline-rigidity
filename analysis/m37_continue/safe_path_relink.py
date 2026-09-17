"""Bidirectional path relinking between the two exact V=40 factor basins.

The first phase searches only the diagonal-safe 2-factor graph.  It then
optimises orientations on the factors lying on discovered short paths.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count, solve_cp_sat
from spectral_neighbor_search import generate_switches
from weighted_factor_search import build_state, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def key_of(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def distance(left, right):
    return 37 - len(set(left) & set(right))


def safe_neighbors(key, target=None, max_target_distance=None):
    edges = list(key)
    out = []
    for i, j, e1, e2 in generate_switches(edges):
        candidate = edges[:]
        candidate[i], candidate[j] = e1, e2
        candidate_key = key_of(candidate)
        if target is not None and max_target_distance is not None:
            if distance(candidate_key, target) > max_target_distance:
                continue
        if is_diagonal_safe(candidate_key):
            out.append(candidate_key)
    return out


def expand_layers(start, target, depth, detour):
    parents = {start: None}
    depths = {start: 0}
    frontier = {start}
    stats = []
    for level in range(1, depth + 1):
        new_frontier = set()
        for state in frontier:
            current_distance = distance(state, target)
            for candidate in safe_neighbors(
                state,
                target=target,
                max_target_distance=current_distance + detour,
            ):
                if candidate in depths:
                    continue
                depths[candidate] = level
                parents[candidate] = state
                new_frontier.add(candidate)
        frontier = new_frontier
        stats.append(
            {
                "depth": level,
                "new_states": len(frontier),
                "total_states": len(depths),
                "target_distance_histogram": dict(
                    sorted(Counter(distance(x, target) for x in frontier).items())
                ),
            }
        )
        print(
            f"  depth={level} new={len(frontier)} total={len(depths)} "
            f"distance_hist={stats[-1]['target_distance_histogram']}",
            flush=True,
        )
        if target in depths or not frontier:
            break
    return parents, depths, stats


def path_to_root(parents, state):
    path = []
    while state is not None:
        path.append(state)
        state = parents[state]
    return path


def optimise_factor(edges, hints, restarts, seed):
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(seed)
    best_value = 10**9
    best_bits = None
    for hint in hints:
        value, bits = local_descent(constant, jmat, hint, rng, 5)
        if value < best_value:
            best_value, best_bits = value, bits
    for _ in range(restarts):
        bits = [rng.getrandbits(1) for _ in edges]
        bits[0] = 0
        value, bits = local_descent(constant, jmat, bits, rng, 4)
        if value < best_value:
            best_value, best_bits = value, bits
    geometry = geometry_bad_count(37, edges, best_bits)
    assert best_value == geometry["bad_triples"]
    return {
        "edges": [list(edge) for edge in edges],
        "warm_value": best_value,
        "bits": best_bits,
        "geometry": geometry,
    }


def project_hint(source, target_edges):
    mapping = {tuple(edge): bit for edge, bit in zip(source["edges"], source["bits"])}
    return [mapping.get(tuple(edge), 0) for edge in target_edges]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--detour", type=int, default=1)
    parser.add_argument("--restarts", type=int, default=12)
    parser.add_argument("--exact-top", type=int, default=12)
    parser.add_argument("--exact-time", type=float, default=45.0)
    parser.add_argument("--max-corridor", type=int, default=200)
    parser.add_argument("--out", default="safe_path_relink.json")
    args = parser.parse_args()

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    endpoints = [item for item in archive["archive"] if item["value"] == 40]
    assert len(endpoints) == 2
    left, right = endpoints
    left_key, right_key = key_of(left["edges"]), key_of(right["edges"])
    print(
        f"endpoints={left['id']},{right['id']} edge_distance={distance(left_key, right_key)}",
        flush=True,
    )

    started = time.time()
    print("forward expansion", flush=True)
    lp, ld, lstats = expand_layers(left_key, right_key, args.depth, args.detour)
    print("backward expansion", flush=True)
    rp, rd, rstats = expand_layers(right_key, left_key, args.depth, args.detour)

    meetings = sorted(
        set(ld) & set(rd),
        key=lambda state: (ld[state] + rd[state], distance(state, left_key), state),
    )
    shortest = min((ld[x] + rd[x] for x in meetings), default=None)
    shortest_meetings = [x for x in meetings if ld[x] + rd[x] == shortest]
    print(
        f"meetings={len(meetings)} shortest={shortest} "
        f"shortest_meetings={len(shortest_meetings)}",
        flush=True,
    )

    corridor = set()
    paths = []
    for meeting in shortest_meetings:
        lpath = list(reversed(path_to_root(lp, meeting)))
        rpath = path_to_root(rp, meeting)[1:]
        path = lpath + rpath
        paths.append(path)
        corridor.update(path)
    if len(corridor) > args.max_corridor:
        rng = random.Random(202607170201)
        keep = {left_key, right_key}
        keep.update(rng.sample(sorted(corridor - keep), args.max_corridor - len(keep)))
        corridor = keep
    print(f"corridor factors to score={len(corridor)}", flush=True)

    evaluated = []
    for index, factor in enumerate(sorted(corridor)):
        hints = [project_hint(left, factor), project_hint(right, factor)]
        result = optimise_factor(
            list(factor), hints, args.restarts, 202607170300 + index
        )
        result.update(
            {
                "distance_left": distance(factor, left_key),
                "distance_right": distance(factor, right_key),
            }
        )
        evaluated.append(result)
        print(
            f"  score {index + 1}/{len(corridor)}: {result['warm_value']} "
            f"d=({result['distance_left']},{result['distance_right']})",
            flush=True,
        )
    evaluated.sort(key=lambda x: (x["warm_value"], x["distance_left"] + x["distance_right"]))

    exact = []
    exact_candidates = evaluated[: args.exact_top]
    for rank, candidate in enumerate(exact_candidates, 1):
        edges = [tuple(edge) for edge in candidate["edges"]]
        _, _, _, constant, jmat = build_state(edges)
        solve = solve_cp_sat(constant, jmat, args.exact_time, hint=candidate["bits"])
        if solve.get("bits") is not None:
            solve["geometry"] = geometry_bad_count(37, edges, solve["bits"])
        exact.append({"rank": rank, "candidate": candidate, "solve": solve})
        print(
            f"  exact {rank}: warm={candidate['warm_value']} "
            f"{solve.get('status')} {solve.get('violations')}",
            flush=True,
        )

    serial_paths = [[[list(edge) for edge in factor] for factor in path] for path in paths[:50]]
    payload = {
        "parameters": vars(args),
        "endpoints": [left["id"], right["id"]],
        "endpoint_edge_distance": distance(left_key, right_key),
        "forward_stats": lstats,
        "backward_stats": rstats,
        "meeting_count": len(meetings),
        "shortest_safe_path_length": shortest,
        "shortest_meeting_count": len(shortest_meetings),
        "sample_paths": serial_paths,
        "evaluated_count": len(evaluated),
        "value_histogram": dict(sorted(Counter(x["warm_value"] for x in evaluated).items())),
        "top50": evaluated[:50],
        "exact": exact,
        "elapsed_s": round(time.time() - started, 3),
    }
    path = OUT / args.out
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(path, flush=True)


if __name__ == "__main__":
    main()

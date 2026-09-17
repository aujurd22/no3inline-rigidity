"""Audit k=11 adjacency-layer coverage for v40_02, v40_03, and v40_04."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS


HERE = Path(__file__).resolve().parent
BASES = ("v40_02", "v40_03", "v40_04")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cycle_lengths(edges: list[list[int]]) -> list[int]:
    neighbors = defaultdict(list)
    for u, v in edges:
        neighbors[u].append(v)
        neighbors[v].append(u)
    assert all(len(values) == 2 for values in neighbors.values())
    unseen = set(neighbors)
    lengths = []
    while unseen:
        start = next(iter(unseen))
        previous = None
        current = start
        length = 0
        while True:
            unseen.discard(current)
            length += 1
            options = [vertex for vertex in neighbors[current] if vertex != previous]
            following = options[0]
            previous, current = current, following
            if current == start:
                break
        lengths.append(length)
    return sorted(lengths)


def cycle_states(length: int, max_size: int) -> set[tuple[int, int]]:
    """Possible (selected edges, adjacent selected-edge vertices) on a cycle."""
    outcomes = set()
    for first in (0, 1):
        states = {(first, first, 0)}  # selected, last bit, internal adjacency
        for _ in range(1, length):
            following = set()
            for selected, last, adjacency in states:
                for bit in (0, 1):
                    if selected + bit <= max_size:
                        following.add(
                            (selected + bit, bit, adjacency + last * bit)
                        )
            states = following
        for selected, last, adjacency in states:
            outcomes.add((selected, adjacency + last * first))
    return outcomes


def possible_adjacencies(lengths: list[int], size: int) -> list[int]:
    combined = {(0, 0)}
    for length in lengths:
        following = set()
        for used, adjacency in combined:
            for cycle_used, cycle_adjacency in cycle_states(length, size - used):
                if used + cycle_used <= size:
                    following.add(
                        (used + cycle_used, adjacency + cycle_adjacency)
                    )
        combined = following
    return sorted(adjacency for used, adjacency in combined if used == size)


def closing_evidence(base: str) -> dict[int, dict]:
    candidates = {}
    patterns = (
        f"rot4_diagonal_overflow_{base}_a*.json",
        f"rot4_line_overflow_{base}_a*_q*.json",
    )
    for pattern in patterns:
        for path in HERE.glob(pattern):
            payload = load(path)
            if "status" not in payload or "parameters" not in payload:
                continue
            if payload["parameters"].get("size") != 11:
                continue
            status = payload["status"]
            objective = payload.get("objective")
            if not (
                status == "INFEASIBLE"
                or (status == "OPTIMAL" and objective is not None and objective > 0)
            ):
                continue
            adjacency = payload["parameters"]["adjacency_count"]
            q = payload["parameters"].get("direction_q", 1)
            record = {
                "classification": (
                    "CLOSED_F0" if status == "INFEASIBLE" else "CLOSED_OVERFLOW"
                ),
                "status": status,
                "objective": objective,
                "q": q,
                "evidence": path.name,
            }
            previous = candidates.get(adjacency)
            if previous is None or q < previous["q"]:
                candidates[adjacency] = record
    return candidates


def main() -> None:
    archive = {
        item["id"]: item
        for item in load(SOURCE_OUTPUTS / "exact_factor_archive.json")["archive"]
    }
    old_sweep = load(HERE / "rot4_adjacency_cut_sweep_v40_02_04_q1.json")
    old_by_base = {item["base"]: item for item in old_sweep["bases"]}
    result = {"size": 11, "bases": []}
    for base_id in BASES:
        lengths = cycle_lengths(archive[base_id]["edges"])
        possible = possible_adjacencies(lengths, 11)
        fixed = closing_evidence(base_id)
        layers = {}
        old = old_by_base[base_id]["final_status"]
        for adjacency in possible:
            if old[str(adjacency)] == "INFEASIBLE":
                layers[str(adjacency)] = {
                    "classification": "CLOSED_EXISTING_CUTS",
                    "evidence": "rot4_adjacency_cut_sweep_v40_02_04_q1.json",
                }
            elif adjacency in fixed:
                layers[str(adjacency)] = fixed[adjacency]
            else:
                layers[str(adjacency)] = {"classification": "UNRESOLVED"}
        closed = all(
            layer["classification"].startswith("CLOSED")
            for layer in layers.values()
        )
        result["bases"].append(
            {
                "base": base_id,
                "cycle_type": lengths,
                "possible_adjacencies": possible,
                "status": "INFEASIBLE" if closed else "PARTIAL",
                "consequence": (
                    "general deletion escape radius is at least 12"
                    if closed
                    else None
                ),
                "layers": layers,
            }
        )
    result["status"] = (
        "INFEASIBLE"
        if all(base["status"] == "INFEASIBLE" for base in result["bases"])
        else "PARTIAL"
    )
    output = HERE / "rot4_k11_other_basins_barrier_audit.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)
    for base in result["bases"]:
        unresolved = [
            adjacency
            for adjacency, layer in base["layers"].items()
            if layer["classification"] == "UNRESOLVED"
        ]
        print(base["base"], base["status"], "unresolved", unresolved)


if __name__ == "__main__":
    main()

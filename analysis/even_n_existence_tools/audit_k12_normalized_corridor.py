"""Audit the rigorous k=12 adjacency corridor after normalization."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


LOW_CLOSURES = {
    "v40_01": {0: 2, 1: 4, 2: 3},
    "v40_02": {0: 2, 1: 2, 2: 2},
    "v40_03": {0: 2, 1: 3, 2: 4},
    "v40_04": {0: 1, 1: 2, 2: 2},
}


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def require_closed_overflow(name: str):
    payload = load(name)
    assert payload["status"] == "OPTIMAL", (name, payload["status"])
    assert payload["objective"] > 0, (name, payload["objective"])
    return {
        "classification": "CLOSED_OVERFLOW",
        "objective": payload["objective"],
        "evidence": name,
    }


def require_f0(name: str):
    payload = load(name)
    assert payload["status"] == "INFEASIBLE", (name, payload["status"])
    assert payload["parameters"]["hard_direction_q"] == 0
    return {"classification": "CLOSED_F0", "evidence": name}


def profile_pairs(name: str, adjacency: int):
    payload = load(name)
    return {
        (item["triple"], item["quadruple"])
        for item in payload["profiles"]
        if item["adjacent"] == adjacency
    }


def audit_v40_02_a7():
    expected_b = {b for b, _ in profile_pairs(
        "rot4_segment_profiles_cycles37_k12.json", 7
    )}
    assert expected_b == {2, 3, 4, 5, 6}
    layers = []
    for b in sorted(expected_b):
        name = f"rot4_line_overflow_v40_02_k12_a7_b{b}_q1.json"
        payload = load(name)
        if b == 2:
            assert payload["status"] == "INFEASIBLE"
            classification = "CLOSED_F0"
        else:
            assert payload["status"] == "OPTIMAL"
            assert payload["objective"] == 2
            classification = "CLOSED_Q1"
        layers.append(
            {
                "triple": b,
                "classification": classification,
                "evidence": name,
            }
        )
    return {
        "classification": "CLOSED_BY_COMPLETE_B_PARTITION",
        "expected_triples": sorted(expected_b),
        "layers": layers,
    }


def audit_normalized_a8(base: str, profile_file: str):
    expected = profile_pairs(profile_file, 8)
    assert {b for b, _ in expected} == {4, 5, 6, 7}
    covered = set()
    layers = []
    for b in (5, 6, 7):
        name = (
            f"rot4_line_overflow_{base}_k12_a8_b{b}"
            "_norm_hq0_q1.json"
        )
        payload = load(name)
        assert payload["parameters"]["forbid_exact_reselection"] is True
        assert payload["parameters"]["hard_direction_q"] == 0
        assert payload["status"] == "INFEASIBLE"
        pairs = {(bb, c) for bb, c in expected if bb == b}
        covered.update(pairs)
        layers.append(
            {
                "triple": b,
                "quadruples": sorted(c for _, c in pairs),
                "classification": "CLOSED_F0_NORMALIZED",
                "evidence": name,
            }
        )
    for b, c in sorted(pair for pair in expected if pair[0] == 4):
        name = (
            f"rot4_{base}_k12_a8_b4_c{c}"
            "_norm_q1resource.json"
        )
        payload = load(name)
        assert payload["parameters"]["allow_exact_reselection"] is False
        assert payload["status"] == "INFEASIBLE"
        covered.add((b, c))
        layers.append(
            {
                "triple": b,
                "quadruple": c,
                "classification": "CLOSED_Q1_NORMALIZED",
                "evidence": name,
            }
        )
    assert covered == expected, (base, expected - covered, covered - expected)
    return {
        "classification": "CLOSED_BY_NORMALIZED_COMPLETE_BC_PARTITION",
        "expected_profiles": [list(pair) for pair in sorted(expected)],
        "covered_profiles": [list(pair) for pair in sorted(covered)],
        "layers": layers,
    }


def audit_complete_profile_sweep(name: str):
    payload = load(name)
    expected = {tuple(item) for item in payload["expected_profiles"]}
    closed = {
        (item["triple"], item["quadruple"])
        for item in payload["layers"]
        if item["classification"].startswith("CLOSED")
    }
    assert payload["complete_closure"] is True
    assert closed == expected
    return {
        "classification": "CLOSED_BY_NORMALIZED_COMPLETE_BC_PARTITION",
        "expected_profiles": [list(item) for item in sorted(expected)],
        "evidence": name,
    }


def audit_v40_03_a7():
    profile_name = "rot4_profile_short_sweep_v40_03_k12_a7_norm_q3.json"
    profile = load(profile_name)
    expected = {tuple(item) for item in profile["expected_profiles"]}
    closed = {
        (item["triple"], item["quadruple"])
        for item in profile["layers"]
        if item["classification"].startswith("CLOSED")
    }
    unresolved = expected - closed
    assert unresolved == {(2, 0)}, unresolved
    split_name = (
        "rot4_cycle_split_v40_03_k12_a7_b2_c0_cycle4_norm_q3.json"
    )
    split = load(split_name)
    assert split["expected_cycle_deletion_counts"] == [0, 1, 2, 3, 4]
    assert split["complete_closure"] is True
    assert all(
        item["classification"].startswith("CLOSED")
        for item in split["layers"]
    )
    return {
        "classification": (
            "CLOSED_BY_NORMALIZED_BC_AND_COMPONENT_PARTITION"
        ),
        "expected_profiles": [list(item) for item in sorted(expected)],
        "coarse_profile_evidence": profile_name,
        "component_split_evidence": split_name,
    }


def main() -> None:
    result = {
        "size": 12,
        "normalization": (
            "Exact same-orientation delete/reinsert pairs may be cancelled; "
            "normalized closure is sufficient for exact Hamming distance 12."
        ),
        "bases": [],
    }
    for base in LOW_CLOSURES:
        layers = {}
        for adjacency, q in LOW_CLOSURES[base].items():
            name = (
                f"rot4_line_overflow_{base}_k12_a{adjacency}_q{q}.json"
            )
            layers[str(adjacency)] = require_closed_overflow(name)
            layers[str(adjacency)]["closing_q"] = q
        if base == "v40_01":
            layers["7"] = audit_complete_profile_sweep(
                "rot4_profile_short_sweep_v40_01_k12_a7_norm_q2.json"
            )
            layers["8"] = require_closed_overflow(
                "rot4_line_overflow_v40_01_k12_a8_q1.json"
            )
        elif base == "v40_02":
            layers["7"] = audit_v40_02_a7()
            layers["8"] = require_closed_overflow(
                "rot4_line_overflow_v40_02_k12_a8_q1.json"
            )
        elif base == "v40_03":
            layers["7"] = audit_v40_03_a7()
            layers["8"] = audit_normalized_a8(
                base, "rot4_segment_profiles_cycles33_4_k12.json"
            )
        else:
            layers["7"] = audit_complete_profile_sweep(
                "rot4_profile_short_sweep_v40_04_k12_a7_norm_q2.json"
            )
            layers["8"] = audit_normalized_a8(
                base, "rot4_segment_profiles_cycles17_16_4_k12.json"
            )
        for adjacency in (9, 10, 11):
            layers[str(adjacency)] = require_f0(
                f"rot4_line_overflow_{base}_k12_a{adjacency}_q1.json"
            )
        closed = {int(value) for value in layers}
        possible = set(range(12))
        candidates = sorted(possible - closed)
        expected_candidates = [3, 4, 5, 6]
        assert candidates == expected_candidates, (base, candidates)
        result["bases"].append(
            {
                "base": base,
                "closed_adjacencies": sorted(closed),
                "candidate_adjacencies": candidates,
                "layers": layers,
            }
        )
    result["common_statement"] = (
        "Every exact distance-12 repair from these four basins must have "
        "3 <= A <= 6."
    )
    output = HERE / "rot4_k12_normalized_corridor_audit.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)
    for base in result["bases"]:
        print(base["base"], base["candidate_adjacencies"])


if __name__ == "__main__":
    main()

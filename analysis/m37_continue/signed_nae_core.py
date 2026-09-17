"""Independent geometry -> signed NAE -> Ising reduction for rot4 NTIL.

No project modules are imported.  Clause enumeration uses exact integer line
keys.  OR-Tools is optional and is used only for the exact Ising ground state.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import time
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def oriented_edges(case):
    if "cells" in case:
        edges, bits = [], []
        for x, y in case["cells"]:
            u, v = sorted((x, y))
            edges.append((u, v))
            bits.append(0 if (x, y) == (u, v) else 1)
        return edges, bits
    return [tuple(e) for e in case["edges"]], case.get("orientation")


def validate_factor(m, edges):
    deg = [0] * m
    for u, v in edges:
        if not (0 <= u < m and 0 <= v < m and u <= v):
            raise ValueError(f"invalid edge {(u, v)} for m={m}")
        if u == v:
            deg[u] += 2
        else:
            deg[u] += 1
            deg[v] += 1
    return {
        "edge_count": len(edges),
        "degree_histogram": dict(Counter(deg)),
        "is_2factor": len(edges) == m and all(d == 2 for d in deg),
        "duplicate_unordered_edges": len(edges) - len(set(edges)),
        "loops": sum(u == v for u, v in edges),
    }


def c4_lifts(m, cell):
    n = 2 * m
    x, y = cell
    out = []
    for _ in range(4):
        out.append((x, y))
        x, y = n - 1 - y, x
    return out


def line_key(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        return None
    g = math.gcd(abs(dx), abs(dy))
    a, b = dy // g, -dx // g
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    return a, b, a * p[0] + b * p[1]


def has_collinear_triple(points):
    members = {}
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            key = line_key(points[i], points[j])
            if key is None:
                continue
            mask = members.get(key, 0) | (1 << i) | (1 << j)
            if mask.bit_count() >= 3:
                return True
            members[key] = mask
    return False


def enumerate_clauses(m, edges):
    lifts = []
    for u, v in edges:
        lifts.append((c4_lifts(m, (u, v)), c4_lifts(m, (v, u))))
    clauses = []
    for a, b, c in itertools.combinations(range(len(edges)), 3):
        for bits in range(8):
            pts = (
                lifts[a][(bits >> 0) & 1]
                + lifts[b][(bits >> 1) & 1]
                + lifts[c][(bits >> 2) & 1]
            )
            if has_collinear_triple(pts):
                clauses.append((a, b, c, bits))
    return clauses


def build_ising(n, clauses):
    clause_set = set(clauses)
    missing = []
    for a, b, c, bits in clauses:
        partner = (a, b, c, bits ^ 7)
        if partner not in clause_set:
            missing.append(((a, b, c, bits), partner))

    pairs = []
    jmat = [[0] * n for _ in range(n)]
    for a, b, c, bits in clauses:
        if bits > (bits ^ 7):
            continue
        signs = [1 if ((bits >> k) & 1) == 0 else -1 for k in range(3)]
        verts = (a, b, c)
        for x, y in ((0, 1), (0, 2), (1, 2)):
            i, j = verts[x], verts[y]
            w = signs[x] * signs[y]
            jmat[i][j] += w
            jmat[j][i] += w
        pairs.append((a, b, c, bits))
    return pairs, jmat, missing


def count_clause_violations(clauses, bits):
    total = 0
    for a, b, c, pat in clauses:
        got = bits[a] | (bits[b] << 1) | (bits[c] << 2)
        total += got == pat
    return total


def qubo_value(pairs_count, jmat, bits):
    spins = [1 if b == 0 else -1 for b in bits]
    pair_energy = sum(
        jmat[i][j] * spins[i] * spins[j]
        for i in range(len(bits))
        for j in range(i + 1, len(bits))
    )
    numerator = pairs_count + pair_energy
    if numerator % 4:
        raise AssertionError(f"non-integral QUBO value: ({pairs_count}+{pair_energy})/4")
    return numerator // 4, pair_energy


def geometry_bad_count(m, edges, bits):
    points = []
    for (u, v), bit in zip(edges, bits):
        cell = (u, v) if bit == 0 else (v, u)
        points.extend(c4_lifts(m, cell))
    unique = list(dict.fromkeys(points))
    lines = {}
    for i in range(len(unique)):
        for j in range(i + 1, len(unique)):
            key = line_key(unique[i], unique[j])
            if key is None:
                continue
            lines[key] = lines.get(key, 0) | (1 << i) | (1 << j)
    bad_lines = []
    total = 0
    for key, mask in lines.items():
        k = mask.bit_count()
        if k >= 3:
            contribution = math.comb(k, 3)
            total += contribution
            bad_lines.append((key, k, contribution))
    return {
        "point_count": len(points),
        "distinct_point_count": len(unique),
        "bad_triples": total,
        "bad_line_count": len(bad_lines),
        "max_points_on_line": max((x[1] for x in bad_lines), default=2),
    }


def solve_cp_sat(pairs_count, jmat, time_limit, hint=None):
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        return {"available": False, "error": str(exc)}

    n = len(jmat)
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(n)]
    model.Add(x[0] == 0)  # global-complement symmetry
    objective_terms = []
    const_energy = 0
    for i in range(n):
        for j in range(i + 1, n):
            w = jmat[i][j]
            if not w:
                continue
            const_energy += w
            xor = model.NewBoolVar(f"d_{i}_{j}")
            model.AddBoolXOr([x[i], x[j], xor.Not()])
            objective_terms.append(-2 * w * xor)
    model.Minimize(sum(objective_terms))
    if hint:
        if hint[0] == 1:
            hint = [1 - b for b in hint]
        for var, value in zip(x, hint):
            model.AddHint(var, value)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    started = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - started
    result = {
        "available": True,
        "status": solver.StatusName(status),
        "elapsed_s": round(elapsed, 3),
        "optimal": status == cp_model.OPTIMAL,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        bits = [int(solver.Value(v)) for v in x]
        value, energy = qubo_value(pairs_count, jmat, bits)
        result.update({"bits": bits, "violations": value, "pair_energy": energy})
    return result


def solve_clause_cp_sat(clauses, n, time_limit, hint=None):
    """Exact MaxSAT solve used as an independent check of the QUBO value."""
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        return {"available": False, "error": str(exc)}
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(n)]
    model.Add(x[0] == 0)
    violated = []
    for idx, (a, b, c, pat) in enumerate(clauses):
        wanted = [(pat >> k) & 1 for k in range(3)]
        lits = [
            x[v] if bit else x[v].Not()
            for v, bit in zip((a, b, c), wanted)
        ]
        bad = model.NewBoolVar(f"bad{idx}")
        model.AddBoolAnd(lits).OnlyEnforceIf(bad)
        model.AddBoolOr([lit.Not() for lit in lits]).OnlyEnforceIf(bad.Not())
        violated.append(bad)
    model.Minimize(sum(violated))
    if hint:
        if hint[0] == 1:
            hint = [1 - b for b in hint]
        for var, value in zip(x, hint):
            model.AddHint(var, value)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    started = time.time()
    status = solver.Solve(model)
    result = {
        "available": True,
        "status": solver.StatusName(status),
        "elapsed_s": round(time.time() - started, 3),
        "optimal": status == cp_model.OPTIMAL,
        "best_bound": solver.BestObjectiveBound(),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result["bits"] = [int(solver.Value(v)) for v in x]
        result["violations"] = int(round(solver.ObjectiveValue()))
    return result


def basic_j_stats(jmat):
    weights = [
        jmat[i][j]
        for i in range(len(jmat))
        for j in range(i + 1, len(jmat))
        if jmat[i][j]
    ]
    abs_degrees = [sum(abs(w) for w in row) for row in jmat]
    return {
        "nonzero_couplings": len(weights),
        "positive_couplings": sum(w > 0 for w in weights),
        "negative_couplings": sum(w < 0 for w in weights),
        "zero_couplings": len(jmat) * (len(jmat) - 1) // 2 - len(weights),
        "sum_abs_couplings": sum(abs(w) for w in weights),
        "max_abs_coupling": max(map(abs, weights), default=0),
        "weight_histogram": dict(sorted(Counter(weights).items())),
        "abs_degree_min": min(abs_degrees),
        "abs_degree_max": max(abs_degrees),
        "abs_degree_mean": sum(abs_degrees) / len(abs_degrees),
    }


def run_case(case, solve, time_limit, rng):
    name, m = case["name"], case["m"]
    edges, supplied = oriented_edges(case)
    print(f"\n[{name}] m={m}, edges={len(edges)}", flush=True)
    factor = validate_factor(m, edges)
    if not factor["is_2factor"]:
        raise ValueError(f"{name} is not a 2-factor: {factor}")
    started = time.time()
    clauses = enumerate_clauses(m, edges)
    enum_s = time.time() - started
    pairs, jmat, missing = build_ising(len(edges), clauses)
    print(
        f"  clauses={len(clauses)}, complement_pairs={len(pairs)}, "
        f"missing_complements={len(missing)}, enum={enum_s:.1f}s",
        flush=True,
    )
    expected = case.get("expected_clauses")
    if expected is not None and len(clauses) != expected:
        raise AssertionError(f"{name}: expected {expected} clauses, got {len(clauses)}")
    if missing:
        raise AssertionError(f"{name}: complement closure failed")

    # Exhaustive identity test on random orientations.
    identity_ok = True
    for _ in range(250):
        bits = [rng.randrange(2) for _ in edges]
        direct = count_clause_violations(clauses, bits)
        quadratic, _ = qubo_value(len(pairs), jmat, bits)
        if direct != quadratic:
            identity_ok = False
            break

    result = {
        "name": name,
        "m": m,
        "edges": [list(e) for e in edges],
        "factor": factor,
        "clauses": len(clauses),
        "complement_pairs": len(pairs),
        "complement_closed": not missing,
        "qubo_identity_random250": identity_ok,
        "enumeration_s": round(enum_s, 3),
        "j_stats": basic_j_stats(jmat),
        "j_matrix": jmat,
        "clause_list": [list(c) for c in clauses],
    }

    if supplied is not None:
        direct = count_clause_violations(clauses, supplied)
        quadratic, energy = qubo_value(len(pairs), jmat, supplied)
        geom = geometry_bad_count(m, edges, supplied)
        result["supplied"] = {
            "bits": supplied,
            "direct_violations": direct,
            "qubo_violations": quadratic,
            "pair_energy": energy,
            "geometry": geom,
        }
        expected_v = case.get("expected_violations")
        if direct != quadratic or (expected_v is not None and direct != expected_v):
            raise AssertionError(f"{name}: supplied orientation verification failed")

    if solve:
        exact = solve_clause_cp_sat(clauses, len(edges), time_limit, supplied)
        result["exact"] = exact
        if exact.get("bits") is not None:
            direct = count_clause_violations(clauses, exact["bits"])
            quadratic, energy = qubo_value(len(pairs), jmat, exact["bits"])
            geom = geometry_bad_count(m, edges, exact["bits"])
            exact["direct_violations"] = direct
            exact["qubo_violations"] = quadratic
            exact["pair_energy"] = energy
            exact["geometry"] = geom
            print(
                f"  exact={exact['status']} V={exact['violations']} "
                f"geometry={geom['bad_triples']} time={exact['elapsed_s']}s",
                flush=True,
            )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(HERE / "cases.json"))
    parser.add_argument("--solve", action="store_true")
    parser.add_argument(
        "--solve-only",
        default="",
        help="comma-separated case names; other cases are enumerated but not solved",
    )
    parser.add_argument("--time-limit", type=float, default=300.0)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    rng = random.Random(20260716)
    solve_only = {x for x in args.solve_only.split(",") if x}
    results = [
        run_case(c, args.solve and (not solve_only or c["name"] in solve_only), args.time_limit, rng)
        for c in cases
    ]
    payload = {
        "generated_at_epoch": time.time(),
        "exact_reduction": "V=P/4+(1/4)sum_{i<j} J_ij s_i s_j",
        "cases": results,
    }
    target = OUT / "signed_nae_results.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main()

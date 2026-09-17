"""collision_lb.py — fast combinatorial lower bound on min bad_triples.

Replaces the expensive 2^W orientation brute force (geometry_and_defects
over all 2^{#witness} orientations) with a guaranteed-valid combinatorial
lower bound.

Given a V20 k=14 survivor (a 37-slot 2-factor with a free-orientation
witness mask), define for every triple T = {i,j,k} of *distinct* slots

    cost_T(local assignment to T∩free) =
        number of collinear lift-combos among the three cells' C4 orbits
        (64 = 4^3 rotation combos), counting only triples of 3 DISTINCT
        148-grid points.

The true bad_triples for a global orientation is exactly
    sum_T cost_T(global assignment restricted to T)
(because every collinear 148-triple involves 3 distinct cells, and the
orbits are disjoint in a valid V20 config).  Therefore for ANY global
assignment

    cost(global) = sum_T cost_T(.)  >=  sum_T min_{local on T∩free} cost_T(.)

so the summed per-triple local minimum is a LOWER BOUND on the true
minimum over orientations:  LB <= min_orientation bad_triples.

This LB needs only the 37 cells + orientations, not the full 2^W oracle.
It is computed by pure NumPy vectorization over the 64 lift combos, so it
is cheap (low CPU) and needs no GPU.

At the end we compare LB against the known exact min_bad_triples
(2^14 brute force) from the certification JSONs to (a) confirm LB > 0 for
all 19 survivors (prescreen would have killed them, matching the brute
force) and (b) confirm LB <= min_bad_triples (validity).
"""
from __future__ import annotations

import itertools
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from prepare_v20_basin_archive import geometry_and_defects
from audit_v20_k14_chunked import build_tokens, owner_mask
from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers

HERE = Path(__file__).resolve().parent
V9W = HERE / "rot4_multigraph_factor_multicycle_exhaustive_v9w.exe"
K = 14
Q = 3
N = 74
M = 37

# 64 lift-combo index triples (a in orbit_i, b in orbit_j, c in orbit_k)
_LIFT_IDX = np.array(list(itertools.product(range(4), repeat=3)), dtype=np.int64)


def c4_lifts(cell):
    x, y = int(cell[0]), int(cell[1])
    pts = []
    for _ in range(4):
        pts.append((x, y))
        x, y = N - 1 - y, x
    return np.array(pts, dtype=np.int64)


def get_survivor_masks(base_id: str):
    """Recover the q3 survivor masks for a basin, from disk if possible."""
    mf = HERE / f"{base_id}_k14_q3_masks.txt"
    if mf.exists():
        masks = [int(x) for x in mf.read_text().split() if x.strip()]
        if masks:
            return masks
    cj = HERE / f"{base_id}_k14_certification.json"
    if cj.exists():
        data = json.loads(cj.read_text())
        return [r["mask"] for r in data["survivors"]]
    return []


def collision_lb(edges, fixed_bits, mask, witness_cells):
    """Return (LB, per-triple local minima list)."""
    mb = [i for i in range(M) if (mask >> i) & 1]
    # directed cell + its C4 orbit for each (slot, orientation)
    orbits = {}
    allowed = {}
    for i in range(M):
        u, v = edges[i]
        if (mask >> i) & 1:
            wi = mb.index(i)
            u, v = witness_cells[wi]
            allowed[i] = [0, 1]
        else:
            allowed[i] = [fixed_bits[i]]
        for b in allowed[i]:
            cx, cy = (u, v) if b == 0 else (v, u)
            orbits[(i, b)] = c4_lifts((cx, cy))

    total = 0
    for i, j, k in itertools.combinations(range(M), 3):
        ai, aj, ak = allowed[i], allowed[j], allowed[k]
        best = None
        for bi in ai:
            Pi = orbits[(i, bi)]
            for bj in aj:
                Pj = orbits[(j, bj)]
                for bk in ak:
                    Pk = orbits[(k, bk)]
                    PA = Pi[_LIFT_IDX[:, 0]]
                    PB = Pj[_LIFT_IDX[:, 1]]
                    PC = Pk[_LIFT_IDX[:, 2]]
                    d1 = PB - PA
                    d2 = PC - PA
                    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
                    # only triples of 3 DISTINCT 148-grid points
                    distinct = (
                        np.any(PA != PB, axis=1)
                        & np.any(PB != PC, axis=1)
                        & np.any(PA != PC, axis=1)
                    )
                    cost = int(np.count_nonzero(distinct & (det == 0)))
                    if best is None or cost < best:
                        best = cost
        total += best
    return total


def main() -> None:
    bases = [f"v20_{n:02d}" for n in range(1, 7)]
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    by_base = {x["id"]: x for x in archive["archive"]}

    report = {"k": K, "q": Q, "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
              "bases": []}

    for base_id in bases:
        print(f"[{base_id}] recovering survivor masks ...", flush=True)
        masks = get_survivor_masks(base_id)
        if not masks:
            print(f"[{base_id}] 0 survivors (CLOSED) -> skip", flush=True)
            report["bases"].append({"base": base_id, "survivors": 0,
                                    "results": []})
            continue

        base = by_base[base_id]
        edges = [tuple(e) for e in base["edges"]]
        bits = list(base["bits"])
        components = ordered_components(edges)
        blockers = candidate_blockers(base)
        hitting = json.loads(
            (HERE / f"v20_defect_hitting_{base_id}.json").read_text())
        defects = [owner_mask(v) for v in hitting["defect_owner_sets"]]

        tokens = build_tokens(base, K, masks, Q, defects, blockers, components)
        res = json.loads(subprocess.run(
            [str(V9W)], input=tokens, text=True, capture_output=True,
            check=True).stdout)
        wf = {entry["mask"]: [tuple(c) for c in entry["cells"]]
              for entry in res.get("witness_factors", [])}

        # known exact mins from certification JSON
        cert = json.loads(
            (HERE / f"{base_id}_k14_certification.json").read_text())
        known = {r["mask"]: r.get("min_bad_triples") for r in cert["survivors"]}

        base_results = []
        for mask in masks:
            cells = wf.get(mask)
            if cells is None:
                print(f"  mask {mask}: missing witness_cells -> skip", flush=True)
                continue
            lb = collision_lb(edges, bits, mask, cells)
            true_min = known.get(mask)
            flag = ""
            if true_min is not None and lb > true_min:
                flag = "  <<< LB>O_TRUE (INVALID!)"
            elif lb == 0 and (true_min or 0) > 0:
                flag = "  (LB=0, inconclusive -> brute force needed)"
            print(f"  mask {mask}: LB={lb}  true_min={true_min}{flag}", flush=True)
            base_results.append({"mask": mask, "LB": lb,
                                 "true_min_bad_triples": true_min})
        report["bases"].append({"base": base_id,
                                "survivors": len(masks),
                                "results": base_results})

    out = HERE / "collision_lb_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # summary
    all_lb = [r["LB"] for b in report["bases"] for r in b["results"]]
    all_true = [r["true_min_bad_triples"] for b in report["bases"]
                for r in b["results"] if r["true_min_bad_triples"] is not None]
    invalid = [r for b in report["bases"] for r in b["results"]
               if r["true_min_bad_triples"] is not None
               and r["LB"] > r["true_min_bad_triples"]]
    print("\n" + "=" * 70)
    print(f"Survivors checked : {len(all_lb)}")
    print(f"All LB > 0        : {all(lb > 0 for lb in all_lb)} "
          f"(prescreen kills all = {all(lb > 0 for lb in all_lb)})")
    print(f"LB <= true for all: {len(invalid) == 0} "
          f"(invalid count = {len(invalid)})")
    if all_true:
        print(f"LB range          : {min(all_lb)}..{max(all_lb)}")
        print(f"true range        : {min(all_true)}..{max(all_true)}")
        print(f"median LB/true    : "
              f"{sorted(r['LB']/r['true_min_bad_triples'] for b in report['bases'] for r in b['results'] if r['true_min_bad_triples'])[len(all_true)//2]:.2f}")
    print("=" * 70)
    print(out)


if __name__ == "__main__":
    main()

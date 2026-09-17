"""collision_lb3.py — coupled per-cell / per-pair lower bound.

A stronger, still-guaranteed-valid lower bound than the per-triple
independent minimum (collision_lb).  The key observation:

    min_x ( f(x) + g(x) )  >=  min_x f(x) + min_x g(x)

so jointly minimizing a free cell's whole *star* of triples (resp. a free
*pair*'s triples) over that cell's single orientation variable yields a
bound that dominates the independent per-triple min and captures the
coupling that makes bad triples unavoidable.

Decomposition (every cell-triple has 0/1/2/3 free slots; the sets are
disjoint, so no double counting):

  LB3 = S0
       + sum_{free c}   min_{b_c}                   sum_{fixed j,k} cost_{c,j,k}(b_c)
       + sum_{free c<d} min_{b_c,b_d}               sum_{fixed k}   cost_{c,d,k}(b_c,b_d)

(S3, the 3-free triples, contribute 0 to the bound — their bad triples
are purely emergent and require the full 2^W search to certify.)

For ANY global orientation assignment sigma:
  true(sigma) = S0 + sum_c star_c(b_c^*) + sum_{c<d} pair_{c,d}(b_c^*,b_d^*) + S3(sigma)
             >= S0 + sum_c min star_c + sum_{c<d} min pair_{c,d}   (since each term >= its min)
so LB3 <= min_sigma true(sigma).  VALID and cheap (no 2^W; pure NumPy).

We compare LB3 against the known exact min_bad_triples (2^14 brute force).
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

_LIFT_IDX = np.array(list(itertools.product(range(4), repeat=3)), dtype=np.int64)


def c4_lifts(cell):
    x, y = int(cell[0]), int(cell[1])
    pts = []
    for _ in range(4):
        pts.append((x, y))
        x, y = N - 1 - y, x
    return np.array(pts, dtype=np.int64)


def get_survivor_masks(base_id: str):
    mf = HERE / f"{base_id}_k14_q3_masks.txt"
    if mf.exists():
        masks = [int(x) for x in mf.read_text().split() if x.strip()]
        if masks:
            return masks
    cj = HERE / f"{base_id}_k14_certification.json"
    if cj.exists():
        return [r["mask"] for r in json.loads(cj.read_text())["survivors"]]
    return []


def _cost(orbits, i, bi, j, bj, k, bk):
    PA = orbits[(i, bi)][_LIFT_IDX[:, 0]]
    PB = orbits[(j, bj)][_LIFT_IDX[:, 1]]
    PC = orbits[(k, bk)][_LIFT_IDX[:, 2]]
    d1 = PB - PA
    d2 = PC - PA
    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    distinct = (np.any(PA != PB, axis=1) & np.any(PB != PC, axis=1)
                & np.any(PA != PC, axis=1))
    return int(np.count_nonzero(distinct & (det == 0)))


def collision_lb3(edges, fixed_bits, mask, witness_cells):
    mb = [i for i in range(M) if (mask >> i) & 1]
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

    free = set(mb)
    fixed_idx = [i for i in range(M) if i not in free]

    S0 = 0
    star = {c: [0, 0] for c in free}          # star[c][b_c]
    pair = {(c, d): [[0, 0], [0, 0]] for c, d in itertools.combinations(sorted(free), 2)}

    for i, j, k in itertools.combinations(range(M), 3):
        fi = i in free
        fj = j in free
        fk = k in free
        nf = fi + fj + fk
        if nf == 0:
            S0 += _cost(orbits, i, allowed[i][0], j, allowed[j][0], k, allowed[k][0])
        elif nf == 1:
            c = i if fi else (j if fj else k)
            b = allowed[c][0]
            others = [x for x in (i, j, k) if x != c]
            # cost depends only on b_c (others fixed)
            star[c][b] += _cost(orbits, i, allowed[i][0], j, allowed[j][0],
                                k, allowed[k][0])
        elif nf == 2:
            c, d = sorted(x for x in (i, j, k) if x in free)
            bc, bd = allowed[c][0], allowed[d][0]
            pair[(c, d)][bc][bd] += _cost(
                orbits, i, allowed[i][0], j, allowed[j][0], k, allowed[k][0])
        # nf == 3 -> contributes 0 to this bound
    lb = S0
    for c in free:
        lb += min(star[c])
    for (c, d) in pair:
        lb += min(min(row) for row in pair[(c, d)])
    return lb


def main() -> None:
    bases = [f"v20_{n:02d}" for n in range(1, 7)]
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    by_base = {x["id"]: x for x in archive["archive"]}

    report = {"k": K, "q": Q, "method": "coupled per-cell/per-pair LB3",
              "generated": time.strftime("%Y-%m-%d %H:%M:%S"), "bases": []}

    for base_id in bases:
        masks = get_survivor_masks(base_id)
        if not masks:
            report["bases"].append({"base": base_id, "survivors": 0, "results": []})
            print(f"[{base_id}] 0 survivors (CLOSED) -> skip", flush=True)
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
        res = json.loads(subprocess.run([str(V9W)], input=tokens, text=True,
                                        capture_output=True, check=True).stdout)
        wf = {e["mask"]: [tuple(c) for c in e["cells"]]
              for e in res.get("witness_factors", [])}
        cert = json.loads((HERE / f"{base_id}_k14_certification.json").read_text())
        known = {r["mask"]: r.get("min_bad_triples") for r in cert["survivors"]}

        results = []
        for mask in masks:
            cells = wf.get(mask)
            if cells is None:
                continue
            lb = collision_lb3(edges, bits, mask, cells)
            true_min = known.get(mask)
            flag = ""
            if true_min is not None and lb > true_min:
                flag = "  <<< INVALID"
            elif lb == 0 and (true_min or 0) > 0:
                flag = "  (LB=0 inconclusive)"
            print(f"  mask {mask}: LB3={lb}  true_min={true_min}{flag}", flush=True)
            results.append({"mask": mask, "LB3": lb,
                            "true_min_bad_triples": true_min})
        report["bases"].append({"base": base_id, "survivors": len(masks),
                                "results": results})

    out = HERE / "collision_lb3_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    all_lb = [r["LB3"] for b in report["bases"] for r in b["results"]]
    all_true = [r["true_min_bad_triples"] for b in report["bases"]
                for r in b["results"] if r["true_min_bad_triples"] is not None]
    invalid = [r for b in report["bases"] for r in b["results"]
               if r["true_min_bad_triples"] is not None
               and r["LB3"] > r["true_min_bad_triples"]]
    print("\n" + "=" * 70)
    print(f"Survivors checked : {len(all_lb)}")
    print(f"All LB3 > 0       : {all(lb > 0 for lb in all_lb)}")
    print(f"LB3 <= true all   : {len(invalid) == 0} (invalid={len(invalid)})")
    if all_true:
        print(f"LB3 range         : {min(all_lb)}..{max(all_lb)}")
        print(f"true range        : {min(all_true)}..{max(all_true)}")
        ratios = sorted(r["LB3"] / r["true_min_bad_triples"] for b in report["bases"]
                        for r in b["results"] if r["true_min_bad_triples"])
        if ratios:
            print(f"median LB3/true   : {ratios[len(ratios)//2]:.2f}")
    print("=" * 70)
    print(out)


if __name__ == "__main__":
    main()

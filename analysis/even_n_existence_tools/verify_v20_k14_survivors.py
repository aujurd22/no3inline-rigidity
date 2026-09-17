"""Geometric certification of the k=14 V=20 basin-01 q=3 survivors.

For each survivor mask we:
  1. ask rot4_multigraph_factor_multicycle_exhaustive_v9w.exe (mode 3) for the
     completed 2-factor ("witness_factors" -> current_cells), and
  2. reconstruct the 37 directed cells (surviving base edges keep their base
     bits; the <=14 witness edges get trial orientations), then
  3. run the exact oracle geometry_and_defects over all 2^(#witness) orientation
     assignments.

If ANY assignment yields bad_triples == 0 the mask is a genuine rot4 NTIL
solution for m=37. Otherwise it is only capacity-feasible (necessary condition
passed) but not a solution.
"""

from __future__ import annotations

import itertools
import json
import subprocess
from pathlib import Path

from prepare_v20_basin_archive import geometry_and_defects
from audit_v20_k14_chunked import build_tokens, owner_mask

HERE = Path(__file__).resolve().parent
V9W = HERE / "rot4_multigraph_factor_multicycle_exhaustive_v9w.exe"
BASE_ID = "v20_01"
K = 14
Q = 3

SURVIVOR_MASKS = [8929978983, 99346809573, 133433689350]


def load_base():
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    base = next(x for x in archive["archive"] if x["id"] == BASE_ID)
    edges = [tuple(e) for e in base["edges"]]
    bits = list(base["bits"])
    components = build_tokens.__globals__  # not used; recompute below
    return base, edges, bits


def main() -> None:
    from audit_rot4_flip_eligibility_multicycle import ordered_components
    from search_rot4_shadow_escape_radius import candidate_blockers
    from solve_joint_rot4_general_factor import short_direction_lines

    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    base = next(x for x in archive["archive"] if x["id"] == BASE_ID)
    edges = [tuple(e) for e in base["edges"]]
    bits = list(base["bits"])

    components = ordered_components(edges)
    blockers = candidate_blockers(base)
    hitting = json.loads((HERE / f"v20_defect_hitting_{BASE_ID}.json").read_text())
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]

    # ---- sanity: reconstruct the base basin (mask=0) -> expect bad_triples=20
    geo0, _ = geometry_and_defects(edges, bits)
    print(f"[sanity] base basin {BASE_ID}: {geo0['bad_triples']} bad_triples, "
          f"{geo0['point_count']} points (expect 20 / 148)")

    # ---- ask v9w for the completed factors of the 3 survivors
    tokens = build_tokens(base, K, SURVIVOR_MASKS, Q, defects, blockers, components)
    res = json.loads(subprocess.run(
        [str(V9W)], input=tokens, text=True, capture_output=True, check=True
    ).stdout)
    wf = res.get("witness_factors", [])
    print(f"[v9w] feasible_masks={res['factor_feasible_masks']} "
          f"witness_factors_returned={len(wf)}")

    report = []
    for entry in wf:
        mask = entry["mask"]
        cells = [tuple(c) for c in entry["cells"]]
        mb = [i for i in range(37) if (mask >> i) & 1]
        survivor_base = [(tuple(edges[i]), bits[i]) for i in range(37) if i not in mb]
        print(f"\n[mask {mask}] removed={len(mb)} witness_cells={len(cells)} "
              f"(expect removed==witness_cells)")
        # witness cells are undirected (u,v); orientation is free -> brute force
        best = None
        found_zero = False
        n_wit = len(cells)
        for assign in itertools.product([0, 1], repeat=n_wit):
            eb = []
            bb = []
            wi = 0
            for i in range(37):
                if (mask >> i) & 1:
                    u, v = cells[wi]
                    eb.append((u, v))
                    bb.append(assign[wi])
                    wi += 1
                else:
                    eb.append(tuple(edges[i]))
                    bb.append(bits[i])
            try:
                geo, _ = geometry_and_defects(eb, bb)
            except AssertionError:
                continue  # duplicate points -> invalid orientation
            bt = geo["bad_triples"]
            if best is None or bt < best[0]:
                best = (bt, assign)
            if bt == 0:
                found_zero = True
                report.append({"mask": mask, "bad_triples": 0,
                               "orientation": list(assign),
                               "verdict": "NTIL_SOLUTION"})
                print(f"  >>> mask {mask}: bad_triples==0 with orientation {list(assign)} "
                      f"=> ROT4 NTIL SOLUTION FOR m=37")
                break
        if not found_zero:
            report.append({"mask": mask,
                           "min_bad_triples": best[0] if best else None,
                           "best_orientation": list(best[1]) if best else None,
                           "verdict": "CAPACITY_FEASIBLE_ONLY"})
            print(f"  mask {mask}: min bad_triples over 2^{n_wit} orientations = "
                  f"{best[0] if best else 'n/a'} -> not a solution")

    out = HERE / "v20_01_k14_certification.json"
    out.write_text(json.dumps(
        {"base": BASE_ID, "k": K, "q": Q, "sanity_base_bad_triples": geo0["bad_triples"],
         "survivors": report}, indent=2), encoding="utf-8")
    print(f"\n[done] certification written to {out}")
    n_sol = sum(1 for r in report if r.get("verdict") == "NTIL_SOLUTION")
    print(f"RESULT: {n_sol} of {len(report)} survivors is a genuine m=37 NTIL solution.")


if __name__ == "__main__":
    main()

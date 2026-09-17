"""Extract (q3) + exactly certify the k=14 survivors of ONE V20 basin.

Step 1: re-run the chunked q0..q3 audit with --save-final to recover the exact
        q3 feasible masks (the main audit discarded them).
Step 2: for each q3 survivor, ask v9w.exe for the completed 2-factor cells,
        brute-force the 2^(#witness) orientations through the exact
        geometry_and_defects oracle, and record min bad_triples.

If any orientation yields bad_triples == 0 the mask is a genuine rot4 NTIL
solution for m=37; otherwise it is only capacity-feasible (necessary condition
passed) and not a solution.
"""
from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

from prepare_v20_basin_archive import geometry_and_defects
from audit_v20_k14_chunked import build_tokens, owner_mask
from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers

HERE = Path(__file__).resolve().parent
V9W = HERE / "rot4_multigraph_factor_multicycle_exhaustive_v9w.exe"
K = 14
Q = 3


def main() -> None:
    base_id = sys.argv[1]
    gpu_json = HERE / f"{base_id}_k14_gpu.json"
    masks_file = HERE / f"{base_id}_k14_q3_masks.txt"

    # ---- Step 1: extract q3 survivors (re-run audit with --save-final)
    print(f"[{base_id}] extracting q3 survivors via audit driver ...", flush=True)
    subprocess.run(
        [sys.executable, "audit_v20_k14_chunked.py",
         "--base", base_id, "--size", str(K), "--gpu", gpu_json.name,
         "--exe", "rot4_multigraph_factor_multicycle_exhaustive_v9.exe",
         "--chunk", "4000000", "--max-q", str(Q),
         "--out", f"{base_id}_k14_audit_rescan.json",
         "--save-final", masks_file.name],
        check=True,
    )
    # (audit driver only writes the file when >=1 survivor exists; a missing
    #  file therefore means the basin is closed at the q3 capacity level)
    masks = []
    if masks_file.exists():
        masks = [int(x) for x in masks_file.read_text().split() if x.strip()]
    if not masks:
        print(f"[{base_id}] q3 survivors = 0 -> CLOSED at capacity level")
        (HERE / f"{base_id}_k14_certification.json").write_text(
            json.dumps({"base": base_id, "k": K, "q": Q, "survivors": []}, indent=2),
            encoding="utf-8",
        )
        return

    # ---- Step 2: exact certification of each q3 survivor
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    base = next(x for x in archive["archive"] if x["id"] == base_id)
    edges = [tuple(e) for e in base["edges"]]
    bits = list(base["bits"])
    components = ordered_components(edges)
    blockers = candidate_blockers(base)
    hitting = json.loads((HERE / f"v20_defect_hitting_{base_id}.json").read_text())
    defects = [owner_mask(v) for v in hitting["defect_owner_sets"]]

    geo0, _ = geometry_and_defects(edges, bits)
    print(f"[sanity] {base_id}: {geo0['bad_triples']} bad_triples / "
          f"{geo0['point_count']} pts (expect 20 / 148)", flush=True)

    tokens = build_tokens(base, K, masks, Q, defects, blockers, components)
    res = json.loads(subprocess.run(
        [str(V9W)], input=tokens, text=True, capture_output=True, check=True
    ).stdout)
    wf = res.get("witness_factors", [])
    print(f"[v9w] feasible={res['factor_feasible_masks']} "
          f"witness_factors_returned={len(wf)}", flush=True)

    report = []
    for entry in wf:
        mask = entry["mask"]
        cells = [tuple(c) for c in entry["cells"]]
        mb = [i for i in range(37) if (mask >> i) & 1]
        print(f"[mask {mask}] removed={len(mb)} witness={len(cells)} "
              f"(expect removed==witness)", flush=True)
        best = None
        found = False
        n = len(cells)
        for assign in itertools.product([0, 1], repeat=n):
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
                found = True
                report.append({"mask": mask, "bad_triples": 0,
                               "verdict": "NTIL_SOLUTION"})
                print(f"  >>> mask {mask}: bad_triples==0 => ROT4 NTIL SOLUTION "
                      f"FOR m=37", flush=True)
                break
        if not found:
            report.append({"mask": mask,
                           "min_bad_triples": best[0] if best else None,
                           "verdict": "CAPACITY_FEASIBLE_ONLY"})
            print(f"  mask {mask}: min bad_triples over 2^{n} orientations = "
                  f"{best[0] if best else 'n/a'} -> not a solution", flush=True)

    out = HERE / f"{base_id}_k14_certification.json"
    out.write_text(json.dumps(
        {"base": base_id, "k": K, "q": Q,
         "sanity_base_bad_triples": geo0["bad_triples"],
         "survivors": report}, indent=2), encoding="utf-8")
    n_sol = sum(1 for r in report if r.get("verdict") == "NTIL_SOLUTION")
    print(f"RESULT[{base_id}]: {n_sol} of {len(report)} survivors is a "
          f"genuine m=37 NTIL solution.")


if __name__ == "__main__":
    main()

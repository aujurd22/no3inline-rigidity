#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k=15 结构化探针收集：对每个 k=15 候选 mask 枚举补全因子，做 2-SAT SCC 矛盾核分析。

与 collect_and_kernelize.py 的区别：
- 读取 k=15 chunked 审计产出的 q3 幸存掩码（v20_XX_k15_survivors.txt）
- 用 W 泛化的 scc_prescreen.scc_classify（支持 k=15，不再依赖 reaudit_k14.W=14）
- 直接聚合逻辑类型（canonical_of_cycle / completion_type），检验「统一 2-变量矛盾环引理」
  能否推广到 k=15：若所有 k=15 补全仍塌缩为同一类型 → 引理推广成立（强证据）；
  若出现新类型（尤其含三元耦合的更长环）→ 引理在 k=15 涌现更复杂结构。

产物：all_completions_k15_kernelized.json + 在末尾打印类型统计。
"""
from __future__ import annotations

import glob
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from reaudit_k14 import (V9W_ALL,)
from audit_v20_k14_chunked import build_tokens, owner_mask
from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers
from scc_prescreen import scc_classify, completion_type

HERE = Path(__file__).resolve().parent


def main():
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    by_id = {b["id"]: b for b in archive["archive"]}

    survivor_files = sorted(glob.glob(str(HERE / "v20_*_k15_survivors.txt")))
    completions = []
    basin_meta = {}
    n_masks_total = 0
    n_masks_feasible = 0

    for sf in survivor_files:
        bid = Path(sf).name.split("_k15")[0]
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        bits_old = list(base["bits"])
        masks = [int(line.strip()) for line in Path(sf).read_text().split()
                 if line.strip()]
        n_masks_total += len(masks)
        if not masks:
            continue

        components = ordered_components(edges_old)
        blockers = candidate_blockers(base)
        hitting = json.loads((HERE / f"v20_defect_hitting_{bid}.json").read_text())
        defects = [owner_mask(v) for v in hitting["defect_owner_sets"]]

        tokens = build_tokens(base, 15, masks, 3, defects, blockers, components)
        print(f"[v9w_all] {bid} ({len(masks)} masks) ...", end=" ", flush=True)
        res = json.loads(subprocess.run(
            [str(V9W_ALL)], input=tokens, text=True,
            capture_output=True, check=True,
        ).stdout)
        wf_by_mask = {}
        for entry in res.get("witness_factors", []):
            m = entry["mask"]
            cells = [tuple(c) for c in entry["cells"]]
            wf_by_mask.setdefault(m, []).append(cells)
        print(f"因子数={[len(wf_by_mask.get(m,[])) for m in masks]}", flush=True)

        basin_meta[bid] = {"edges": edges_old, "bits": bits_old}
        for mask in masks:
            comps = wf_by_mask.get(mask, [])
            if comps:
                n_masks_feasible += 1
            for ci, cells in enumerate(comps):
                edges_37 = []
                wi = 0
                for i in range(37):
                    if (mask >> i) & 1:
                        edges_37.append(cells[wi])
                        wi += 1
                    else:
                        edges_37.append(tuple(edges_old[i]))
                free_positions = [i for i in range(37) if (mask >> i) & 1]
                assert len(free_positions) == 15, f"mask 位数异常: {bin(mask).count('1')}"
                kernel = scc_classify(edges_37, bits_old, free_positions)
                t = completion_type(kernel["all_min_cycles"])
                kernel["type_canonical"] = list(t) if t else None
                completions.append({
                    "bid": bid,
                    "mask": mask,
                    "comp_idx": ci,
                    "cells": cells,
                    "edges_37": edges_37,
                    "bits_37": bits_old,
                    "free_positions": free_positions,
                    "kernel": kernel,
                })
                flag = "UNSAT(2-SAT)" if kernel["unsat_2sat"] else "SAT?"
                print(f"    {bid} mask={mask} #comp{ci}: "
                      f"一元={kernel['n_unary']} 二元={kernel['n_binary']} "
                      f"矛盾={flag} 类型={kernel['type_canonical']}")

    out = {
        "k": 15,
        "n_masks_total": n_masks_total,
        "n_masks_feasible": n_masks_feasible,
        "n_completions_total": len(completions),
        "basin_meta": basin_meta,
        "completions": completions,
    }
    out_path = HERE / "all_completions_k15_kernelized.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── 类型聚合 ──
    types = defaultdict(list)
    n_unsat = 0
    for c in completions:
        if c["kernel"]["unsat_2sat"]:
            n_unsat += 1
        types[tuple(c["kernel"]["type_canonical"])].append(
            (c["bid"], c["mask"], c["comp_idx"]))

    print(f"\n写入 {out_path}")
    print(f"k=15 候选掩码(审计输入)={n_masks_total} | q3 可行掩码={n_masks_feasible} | "
          f"补全因子={len(completions)}")
    print(f"2-SAT UNSAT={n_unsat} | 逻辑类型数={len(types)}")
    for t, members in sorted(types.items(), key=lambda kv: -len(kv[1])):
        print(f"  类型 {list(t)}: {len(members)} 个补全")


if __name__ == "__main__":
    main()

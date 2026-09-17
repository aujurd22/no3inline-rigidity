#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内禀性检验：对每盆地随机抽自由格子集，查纯二元图是否 UNSAT。

目的：验证二元过约束是否内禀于盆地 37-cell 几何（与"选哪些格自由"无关），
支撑猜想 G′。W=14/15 用位掩码表示法可行（2^15 远小于 2^37）。
[COMPUTATIONAL CERTIFICATE]。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, lit_id,
)

HERE = Path(__file__).resolve().parent
N_TRIALS = 200


def pure_binary_unsat(edges, bits, free):
    W = len(free)
    fs = build_correct_fs(edges, bits, free)
    unary, uc, binary = extract_unary_binary(fs, set(free))
    adj, _ec, _cu = build_implication_graph([], False, binary, W)
    comp, _ = tarjan_scc(adj, 2 * W)
    return any(comp[lit_id(p, 0)] == comp[lit_id(p, 1)] and comp[lit_id(p, 0)] != -1
               for p in range(W))


def main():
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    rng = random.Random(20260721)
    summary = {}
    for size in (14, 15):
        print(f"\n##### 随机子集大小 W={size} (每盆地 {N_TRIALS} 次) #####")
        basin_res = {}
        for b in arch["archive"]:
            edges = [tuple(e) for e in b["edges"]]
            bits = list(b["bits"])
            all_cells = list(range(37))
            cnt = 0
            for _ in range(N_TRIALS):
                free = sorted(rng.sample(all_cells, size))
                if pure_binary_unsat(edges, bits, free):
                    cnt += 1
            frac = cnt / N_TRIALS
            basin_res[b["id"]] = frac
            print(f"  {b['id']}: 纯二元UNSAT 比例 = {frac:.3f} ({cnt}/{N_TRIALS})")
        summary[f"W{size}"] = basin_res
    # 总览
    print("\n===== 总览 =====")
    for size, br in summary.items():
        overall = sum(br.values()) / len(br)
        print(f"{size}: 6 盆地平均纯二元UNSAT比例 = {overall:.3f}")
    (HERE / "random_subset_binary_test.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("写入 random_subset_binary_test.json")


if __name__ == "__main__":
    main()

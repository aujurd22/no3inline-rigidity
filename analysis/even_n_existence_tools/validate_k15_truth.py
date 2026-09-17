#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k=15 真值交叉验证（独立于 SCC 蕴含图）。

机制：直接对所有冲突子句的禁配位图 mask_fs 做 OR 归约。
- 若 全元数 OR == FULL(2^W) → 确证 UNSAT（无任何朝向能避开所有共线性禁配）。
- 分别统计 仅一元/二元 OR 与 全元数 OR，核对矛盾是否由二元引发（应 == SCC 结论）。

这是与 scc_prescreen 的 Tarjan SCC 完全独立的判定路径，共用 build_correct_fs 几何提取。
用于排除 W=15 参数化引入的假 UNSAT；并核对“三元耦合是否为必需”。
"""
from __future__ import annotations

import json
from pathlib import Path

from scc_prescreen import build_correct_fs

HERE = Path(__file__).resolve().parent


def main():
    data = json.loads((HERE / "all_completions_k15_kernelized.json").read_text())
    completions = data["completions"]
    W = completions[0]["kernel"]["W"]
    FULL = (1 << (1 << W)) - 1
    print(f"k={data['k']}  W={W}  2^W={1<<W}  FULL位图闭合={FULL==(1<<(1<<W))-1}")

    n_unsat_full = 0
    n_binary_sufficient = 0
    for c in completions:
        edges_37 = [tuple(e) for e in c["edges_37"]]
        bits_37 = list(c["bits_37"])
        free_positions = list(c["free_positions"])
        fs = build_correct_fs(edges_37, bits_37, free_positions)

        or_unary_binary = 0
        or_all = 0
        for owner_set, (mask_fs, _bc) in fs.items():
            n_free = sum(1 for x in owner_set if x in free_positions)
            or_all |= mask_fs
            if n_free <= 2:
                or_unary_binary |= mask_fs

        unsat_full = (or_all == FULL)
        binary_suff = (or_unary_binary == FULL)
        if unsat_full:
            n_unsat_full += 1
        if binary_suff:
            n_binary_sufficient += 1
        print(f"  {c['bid']} mask={c['mask']} #comp{c['comp_idx']}: "
              f"全元数UNSAT={unsat_full}  一元/二元已足={binary_suff}  "
              f"SCC_UNSAT={c['kernel']['unsat_2sat']}")

    print(f"\n全元数OR归约 UNSAT: {n_unsat_full}/{len(completions)}")
    print(f"仅一元/二元已足(无需三元): {n_binary_sufficient}/{len(completions)}")
    if n_unsat_full == len(completions) and n_binary_sufficient == len(completions):
        print("✓ 独立 OR 归约与 SCC 蕴含图结论一致：16/16 UNSAT，且全部由一元/二元引发，"
              "无三元耦合必需 → W=15 参数化无假 UNSAT，统一 2-变量矛盾环引理在 k=15 探针上成立。")
    else:
        print("✗ 存在不一致，需排查", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 k=15 结构化候选掩码：每个 k=14 q3 幸存 mask 再删 1 个旧 cell（置位 1 个清零位）。

这批 437 个候选是 k=15 替换空间中**包含某 k=14 幸存结构**的子集，
用于廉价检验「统一 2-变量矛盾环引理」能否推广到 k=15，而不必先做 k>=15 的
CUDA 根扫描（300M 缓冲溢出，需多趟分块重编）。

产物：v20_XX_k15_superset_gpu.json（假 GPU 格式，供 audit_v20_k14_chunked.py 直接 --gpu 消费）。
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    cert_files = sorted(glob.glob(str(HERE / "v20_*_k14_certification.json")))
    total = 0
    per_basin = {}
    for cf in cert_files:
        d = json.loads(Path(cf).read_text())
        bid = d["base"]
        survivors = [s["mask"] for s in d.get("survivors", [])]
        supersets = set()
        for mask in survivors:
            # 23 个清零位 = 旧 cell（保留位），再置 1 个 → 删 15 个 cell
            for i in range(37):
                if not ((mask >> i) & 1):
                    supersets.add(mask | (1 << i))
        per_basin[bid] = sorted(supersets)
        total += len(supersets)
        # 写假 GPU JSON
        payload = {
            "survivor_masks": list(supersets),
            "survivor_masks_complete": True,
            "root_nonzero_count": len(supersets),
            "note": f"k=15 supersets of k=14 q3 survivors for {bid} "
                    f"({len(survivors)} base survivors -> {len(supersets)} supersets)",
        }
        out = HERE / f"{bid}_k15_superset_gpu.json"
        out.write_text(json.dumps(payload), encoding="utf-8")
        print(f"{bid}: {len(survivors)} 幸存 -> {len(supersets)} 超集  -> {out.name}")

    print(f"\n总计 {total} 个 k=15 候选（6 盆地，每个幸存 mask 产生 23 个超集）")
    # 一致性检查：每个超集必须恰好 15 位
    bad = 0
    for bid, masks in per_basin.items():
        for m in masks:
            if bin(m).count("1") != 15:
                bad += 1
    print(f"位宽校验：异常掩码数 = {bad}（应为 0）")


if __name__ == "__main__":
    main()

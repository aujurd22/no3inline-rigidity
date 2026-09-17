#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机 2-因子 UNSAT 核挖掘（2026-07-21，普遍性/局部性证据）。

对 N 个随机 2-因子：
  - fast_build_3cnf 等价构建 3-CNF
  - extract_mus（已修复删除算法）抽最小不可满足子集
  - 统计 MUS 子句数、涉及互异 cell 数
目的：验证 rot4 取向障碍对 m=37 是**普遍且局部**的（非盆地特有、非全局稠密到无可提取小核）。
结果标 [COMPUTATIONAL CERTIFICATE]。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from scan_new_basins import random_2factor  # noqa: E402
from fast_3cnf import fast_build_3cnf  # noqa: E402
from extract_mus_3sat import extract_mus  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--out", default=str(HERE / "core_mining_random.json"))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    print(f"[核挖掘] 样本={args.n} seed={args.seed}")
    t0 = time.time()
    rows = []
    for i in range(args.n):
        edges = random_2factor(rng)
        clauses, nvars = fast_build_3cnf(edges)
        mus = extract_mus(clauses, nvars, node_budget=20_000_000)
        cells = set()
        for cl in mus:
            for lit in cl:
                cells.add(lit // 2)
        rows.append({
            "idx": i, "n_clauses_total": len(clauses),
            "mus_clauses": len(mus), "mus_cells": len(cells),
            "mus_cells_list": sorted(cells),
            "mus_clauses_list": [list(cl) for cl in mus],
            "edges": edges,
        })
        tag = "  ★小核" if len(cells) <= 10 else ""
        print(f"  [{i}] 总子句={len(clauses)}  MUS子句={len(mus)}  "
              f"涉及cell={len(cells)}/{nvars}{tag}")

    out = {"n": args.n, "elapsed_seconds": time.time() - t0, "rows": rows}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    cells_list = [r["mus_cells"] for r in rows]
    print(f"\n写入 {args.out}")
    print(f"MUS 涉及 cell 数：min={min(cells_list)} max={max(cells_list)} "
          f"均值={sum(cells_list)/len(cells_list):.1f} 中位数={sorted(cells_list)[len(cells_list)//2]}")


if __name__ == "__main__":
    main()

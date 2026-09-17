#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从精确 3-CNF 抽取最小不可满足子集(MUS)，给出有限障碍"核"。

对每个盆地：以全部子句(UNSAT)为起点，用删除算法
  F=全子句; while F: 弹出 c; 若 F 去 c 后 SAT ⇒ c 必要(入MUS); 否则 c 冗余(F缩小)
得 MUS（非最小尺寸，但是不可满足核）。

报告：MUS 子句数、涉及的 cell 集合、每子句 (p,q,k,a,b,c)。
这是把"计算 UNSAT"转为人可读的有限障碍结构（朝定理迈进）。
[COMPUTATIONAL CERTIFICATE，MUS 抽取]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from exact_rot4_3sat import build_full_3cnf, dpll_unsat

HERE = Path(__file__).resolve().parent


def clause_cells(cl):
    """子句 (¬x_p=a ∨ ¬x_q=b ∨ ¬x_k=c) 的字面 → (p,q,k,a,b,c)。"""
    out = []
    for lit in cl:
        var = lit >> 1
        bit = lit & 1
        # ¬(x_v=bit) 的字面是 (2*v+bit)^1；若 lit 为 (2*v+bit)^1 则原 bit=bit
        # 这里 cl 已是字面；lit 的变量与取反：原禁止 (x_v=bit) 对应字面 (2v+bit)^1
        # 反向：lit ^ 1 = 2v+bit → v=lit^1>>1, bit=lit^1&1
        v = (lit ^ 1) >> 1
        b = (lit ^ 1) & 1
        out.append((v, b))
    return out


def extract_mus(clauses, nvars, node_budget=20_000_000):
    """删除算法求包含极小不可满足子集(MUS)。

    正确流程：工作集 F 初始为全子句(UNSAT)。对每条子句 c：
      - 测试 F 去掉 c 后是否 SAT；
      - 若 SAT ⇒ c 必要：加入 MUS，**且 c 保留在 F 中**（供后续冗余判定正确）；
      - 若 UNSAT ⇒ c 冗余：从 F 中删除。
    关键修正（2026-07-21）：旧版用 F.pop(0) 无条件移除 c，使必要子句脱离工作集，
    导致后续子句被错误判为必要、MUS 含重复且非极小。本版保留必要子句于 F。
    """
    F = [list(c) for c in clauses]   # 工作集（可变）
    mus = []
    snapshot = [list(c) for c in clauses]
    for c in snapshot:
        # 在 F 中定位 c（首个匹配）
        idx = next((i for i, x in enumerate(F) if x == c), None)
        if idx is None:
            continue
        F_minus = F[:idx] + F[idx + 1:]
        r, _ = dpll_unsat(F_minus, nvars, node_budget=node_budget)
        if r is False:        # F\{c} SAT ⇒ c 必要，保留在 F
            mus.append(c)
        else:                 # F\{c} UNSAT ⇒ c 冗余，从 F 删除
            del F[idx]
    return mus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin", default=None)
    args = ap.parse_args()
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    basins = ([args.basin] if args.basin else [b["id"] for b in arch["archive"]])

    summary = {}
    for bid in basins:
        b = next(x for x in arch["archive"] if x["id"] == bid)
        edges = [tuple(e) for e in b["edges"]]
        nvar = len(edges)
        clauses, _ = build_full_3cnf(edges, b["bits"])
        print(f"[{bid}] 抽取 MUS（{len(clauses)} 子句）...", flush=True)
        mus = extract_mus(clauses, nvar)
        cells = set()
        for cl in mus:
            for (v, _) in clause_cells(cl):
                cells.add(v)
        summary[bid] = {
            "n_clauses_total": len(clauses),
            "mus_size": len(mus),
            "mus_cells": sorted(cells),
            "mus_cell_count": len(cells),
            "mus_clauses": [[list(clause_cells(cl)) for cl in mus]],
        }
        print(f"  MUS 子句={len(mus)}  涉及 cell={len(cells)} "
              f"cell集={sorted(cells)}", flush=True)

    if args.basin is None:
        out = {"summary": summary}
        (HERE / "mus_3sat_all.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

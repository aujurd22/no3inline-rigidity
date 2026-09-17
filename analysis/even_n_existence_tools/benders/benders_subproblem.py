#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benders 子问题：给定一幅无向 2-因子（37 条 cell 边），求解取向 SAT。

严格复用已验证的几何基元（exact_rot4_3sat.build_full_3cnf / dpll_unsat，
prepare_v20_basin_archive.geometry_and_defects），不重造轮子、不改已验证代码。

子问题判定逻辑：
  1. 合法性预筛：该 2-因子须产生 148 个互异提升点（rot4 2-因子必要条件）。
     否则该候选非合法 rot4 2-因子，直接记为 invalid（可割除）。
  2. 三互异-cell 3-CNF 可靠松弛（build_full_3cnf + 迭代 DPLL）：
       - UNSAT ⇒ 该 2-因子**无任何** rot4-NTIL 取向补全（sound 排除）。
       - SAT   ⇒ 存在规避"3 互异 cell 共线"的取向；但 3-CNF 是子公式，
                 须用完整几何 oracle 验证（2+1 型共线未编码）。
  3. 若 3-CNF SAT，导出满足赋值并送几何 oracle 校验 bad_triples==0：
       - 0 ⇒ ★ 发现 rot4-NTIL 解（突破，停止全局搜索）。
       - >0 ⇒ SAT 但非真解（被 2+1 型共线阻断），记为 sat_blocked。

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。m=37 存在性仍 OPEN。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # analysis/even_n_existence_tools
sys.path.insert(0, str(HERE))

from exact_rot4_3sat import build_full_3cnf, dpll_unsat  # noqa: E402
from prepare_v20_basin_archive import geometry_and_defects  # noqa: E402


def is_valid_rot4_factor(edges_37):
    """该 2-因子是否产生 148 个互异提升点（rot4 2-因子必要条件）。"""
    try:
        geo, _ = geometry_and_defects(edges_37, [0] * len(edges_37))
    except AssertionError:
        return False, None
    if geo.get("bad_triples") is None:
        return False, None
    return True, geo


def dpll_model(clauses, nvars, node_budget=20_000_000):
    """迭代 DPLL，返回 (status, model)。
    status: True=UNSAT, False=SAT, None=超预算。model: SAT 时的位赋值 list（长度 nvars）或 None。

    与 exact_rot4_3sat.dpll_unsat 严格同构（已验证正确），仅增加模型提取：
    - unit_prop 中 `assign[lit]==0` 必须 `continue`（跳过已假字面量），
      只有未赋值(-1)字面量才进入 un；`len(un)==0` 才是真正的冲突（空子句）。
    - 递归式快照：每个分支在赋值**前**保存 `saved=assign[:]`，回溯时 `assign[:]=saved`。
      原实现把快照压在赋值之后、且两个分支共用同一"已污染"快照，回溯失效。
    """
    n = 2 * nvars
    assign = [-1] * n
    active = set()
    for cl in clauses:
        for lit in cl:
            active.add(lit)
    freq = [0] * n
    for cl in clauses:
        for lit in cl:
            freq[lit] += 1
    nodes = [0]

    def unit_prop():
        changed = True
        while changed:
            changed = False
            for cl in clauses:
                un = []
                sat = False
                for lit in cl:
                    if assign[lit] == 1:
                        sat = True
                        break
                    if assign[lit] == 0:
                        continue
                    un.append(lit)
                if sat:
                    continue
                if not un:
                    return False  # 空子句/冲突
                if len(un) == 1:
                    l = un[0]
                    assign[l] = 1
                    assign[l ^ 1] = 0
                    changed = True
        return True

    def search():
        nodes[0] += 1
        if nodes[0] > node_budget:
            return None
        if not unit_prop():
            return True  # UNSAT
        best = -1
        best_score = -1
        for lit in active:
            if assign[lit] != -1:
                continue
            score = freq[lit] + freq[lit ^ 1]
            if score > best_score:
                best_score = score
                best = lit
        if best == -1:
            return False  # 全定且一致 ⇒ SAT
        v = best
        for val in (1, 0):
            saved = assign[:]
            assign[v] = val
            assign[v ^ 1] = 1 - val
            r = search()
            if r is None:
                return None
            if not r:
                return False  # SAT
            assign[:] = saved
        return True

    status = search()
    if status is False:
        model = [0] * nvars
        for i in range(nvars):
            model[i] = assign[2 * i]
        return False, model
    return status, None


def solve_subproblem(edges_37, with_oracle=True, node_budget=20_000_000):
    """对一幅 2-因子跑完整 Benders 子问题。

    返回 dict：verdict ∈ {invalid, unsat, sat_blocked, sat_solution, unknown}。
    """
    valid, geo = is_valid_rot4_factor(edges_37)
    if not valid:
        return {"verdict": "invalid", "reason": "非 148 互异提升点（非合法 rot4 2-因子）"}

    clauses, nvars = build_full_3cnf(edges_37)
    status, model = dpll_model(clauses, nvars, node_budget=node_budget)
    if status is True:
        return {"verdict": "unsat", "n_clauses": len(clauses),
                "n_cells": nvars, "n_bad_initial": geo["bad_triples"]}
    if status is None:
        return {"verdict": "unknown", "reason": "DPLL 超预算",
                "n_clauses": len(clauses)}
    # SAT：需几何 oracle 校验
    if not with_oracle:
        return {"verdict": "sat_unverified", "model": model,
                "n_cells": nvars, "n_clauses": len(clauses)}
    try:
        geo2, _ = geometry_and_defects(edges_37, model)
        bt = geo2["bad_triples"]
    except AssertionError:
        return {"verdict": "sat_blocked", "model": model,
                "reason": "oracle 断言失败（点集非 148 互异）",
                "n_cells": nvars}
    if bt == 0:
        return {"verdict": "sat_solution", "model": model,
                "n_cells": nvars}
    return {"verdict": "sat_blocked", "model": model,
            "bad_triples": bt, "n_cells": nvars}


if __name__ == "__main__":
    # 自测：对六 V20 盆地逐一跑子问题，应全 unsat（与既有证书一致）。
    import json
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    for b in arch["archive"]:
        r = solve_subproblem([tuple(e) for e in b["edges"]])
        print(f"{b['id']}: {r['verdict']}  "
              f"(clauses={r.get('n_clauses')}, bad0={r.get('n_bad_initial')})")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确(sound) 编码：整个 37-cell 2-因子是否容许 rot4-NTIL 补全。

模型（来自 reaudit_k14.build_points / combo_bad）：
- 每个 cell i 有 2 条候选有向边（bit b∈{0,1}）；c4_lifts 给 4 个提升点。
- 补全 = 每 cell 选 bit + 全局 rot4 相位。
- combo_bad(P,[(p,a),(q,b),(k,c)]) = True 当且仅当 4×4×4 提升组合中存在共线三元组。
  这是 *sound over-constraint*（比真正共享相位的坏条件更严），故禁止更多；
  编码 UNSAT ⇒ 确实无补全（valid proof of non-existence）。

编码：变量 x_i∈{0,1}（每 cell 选哪条边）；literal = 2*i + a。
对每三元组 (p,q,k) 互异、每 (a,b,c)∈{0,1}^3，若 combo_bad 则加子句
    ¬(x_p=a) ∨ ¬(x_q=b) ∨ ¬(x_k=c)
该 3-CNF UNSAT ⇔ 不存在边选择使所有三元组非共线（sound）⇔ 该 2-因子无 rot4-NTIL 补全。

用迭代 DPLL（单元传播+活动变量剪枝+MOM）判 UNSAT。
产物：exact_rot4_3sat_<basin>.json ；跨 6 basin 汇总。
[COMPUTATIONAL CERTIFICATE，sound]，非定理。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reaudit_k14 import build_points, combo_bad

sys.setrecursionlimit(100000)
HERE = Path(__file__).resolve().parent


def build_full_3cnf(edges_37, bits_37=None):
    """全部 37 cell 自由；返回 3-CNF 子句列表（literal=2*cell+val）。"""
    n = len(edges_37)
    P = build_points(edges_37, bits_37 if bits_37 is not None else [0] * n)
    clauses = []
    for p in range(n):
        for q in range(p + 1, n):
            for k in range(n):
                if k == p or k == q:
                    continue
                for a in (0, 1):
                    for b in (0, 1):
                        for c in (0, 1):
                            if combo_bad(P, [(p, a), (q, b), (k, c)]):
                                clauses.append([(2 * p + a) ^ 1,
                                                (2 * q + b) ^ 1,
                                                (2 * k + c) ^ 1])
    return clauses, n


def dpll_unsat(clauses, nvars, node_budget=20_000_000):
    """迭代式 DPLL。True=UNSAT, False=SAT, None=超预算(未知)。"""
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
                    return False
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
            return True
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
            return False
        v = best
        for val in (1, 0):
            saved = assign[:]
            assign[v] = val
            assign[v ^ 1] = 1 - val
            r = search()
            if r is None:
                return None
            if not r:
                return False
            assign[:] = saved
        return True

    return search(), nodes[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin", default=None, help="仅测单个 basin；缺省测全部 6 个")
    ap.add_argument("--trials", type=int, default=1, help="重复次数(稳定性/计时)")
    args = ap.parse_args()
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    basins = ([args.basin] if args.basin else
              [b["id"] for b in arch["archive"]])

    summary = {}
    for bid in basins:
        b = next(x for x in arch["archive"] if x["id"] == bid)
        edges_37 = [tuple(e) for e in b["edges"]]
        bits_37 = list(b["bits"])
        clauses, nvars = build_full_3cnf(edges_37, bits_37)
        # 预筛：若空子句或单位子句冲突，极快
        result = None
        total_nodes = 0
        for _ in range(args.trials):
            r, nd = dpll_unsat(clauses, nvars)
            result = r
            total_nodes += nd
        verdict = {True: "UNSAT", False: "SAT", None: "UNKNOWN"}[result]
        summary[bid] = {
            "n_cells": nvars,
            "n_clauses": len(clauses),
            "verdict": verdict,
            "nodes_avg": total_nodes // max(1, args.trials),
        }
        print(f"{bid}: cells={nvars} clauses={len(clauses)} → {verdict} "
              f"(节点≈{total_nodes // max(1, args.trials)})", flush=True)

    if args.basin is None:
        out = {"summary": summary}
        (HERE / "exact_rot4_3sat_all.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        unsat = sum(1 for v in summary.values() if v["verdict"] == "UNSAT")
        sat = sum(1 for v in summary.values() if v["verdict"] == "SAT")
        unk = sum(1 for v in summary.values() if v["verdict"] == "UNKNOWN")
        print(f"\n汇总: UNSAT={unsat} SAT={sat} UNKNOWN={unk} / 共 {len(summary)}")
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

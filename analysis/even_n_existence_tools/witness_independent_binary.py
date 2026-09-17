#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""见证无关二元子句分析（攻击 G′ 的核心计算）。

目标：找"无论第三固定格取何朝向都存在的二元边"——即对任意 c∈{0,1}，
combo_bad((p,a),(q,b),(k,c)) 对某个 (a,b) 成立。若存在这样的边织成
对所有符号赋值都矛盾的奇环，则 G′（任意补全纯二元 UNSAT）得证。

先对单盆地 v20_01 跑（参数 --basin），输出：
- 见证无关边集合 (p,q)，及其触发固定格 k 集合；
- 每条见证无关边对所有 k 朝向给出的"禁 (a,b) 模式"；
- 检查是否存在 SMALL（≤5 变量）子图，其见证无关边在所有符号赋值下均 UNSAT。

[COMPUTATIONAL CERTIFICATE]，产物 witness_independent_<basin>.json。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reaudit_k14 import build_points, combo_bad

HERE = Path(__file__).resolve().parent


def analyze_basin(basin_id):
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    b = next(x for x in arch["archive"] if x["id"] == basin_id)
    edges_37 = [tuple(e) for e in b["edges"]]
    bits_37 = list(b["bits"])
    P = build_points(edges_37, bits_37)
    n = 37

    # 对每个 (p,q) 对，找使其见证无关的 k
    # 见证无关：对 c=0 与 c=1，均 ∃ (a,b) s.t. combo_bad((p,a),(q,b),(k,c))
    wi_edges = {}  # (p,q) -> {"ks":[...], "patterns": {k: [(a,b),...]}}
    for p in range(n):
        for q in range(p + 1, n):
            ks = []
            patterns = {}
            for k in range(n):
                if k == p or k == q:
                    continue
                ok_for_c = []
                pat_c = {}
                for c in (0, 1):
                    bad_ab = []
                    for a in (0, 1):
                        for bb in (0, 1):
                            if combo_bad(P, [(p, a), (q, bb), (k, c)]):
                                bad_ab.append((a, bb))
                    if bad_ab:
                        ok_for_c.append(c)
                        pat_c[c] = bad_ab
                if len(ok_for_c) == 2:  # 两朝向都触发
                    ks.append(k)
                    patterns[k] = pat_c
            if ks:
                wi_edges[(p, q)] = {"ks": ks, "patterns": patterns}

    # 找 SMALL 见证无关奇环：取见证无关边集，构造"符号最弱"蕴含图
    # （每条边两种可能符号都加上 → 若仍 UNSAT 则真·见证无关矛盾）
    # 用 2-变量符号：边 (p,q) 带来自各 k 的禁 (a,b) 集合。
    # 构造最强约束图：对所有 k，add 边 lit(p,a)->lit(q,1-b) for each (a,b) in pat_c[c].
    # 若该图 UNSAT，则无论 k 朝向/符号如何都矛盾 → 见证无关奇环存在。
    # 我们检查每个极小见证无关边子图（≤6 变量）是否全符号 UNSAT。
    import itertools
    var_set = sorted({v for e in wi_edges for v in e})
    results = []
    # 限制规模：只在变量数 ≤ 7 的连通分量里查
    # 构建邻接（变量级）
    adj_var = {v: set() for v in var_set}
    for (p, q) in wi_edges:
        adj_var[p].add(q)
        adj_var[q].add(p)

    # 找连通分量
    seen = set()
    comps = []
    for v in var_set:
        if v in seen:
            continue
        stack = [v]
        comp = set()
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            seen.add(x)
            for y in adj_var[x]:
                if y not in comp:
                    stack.append(y)
        comps.append(comp)

    comps = [c for c in comps if len(c) >= 3]
    comps.sort(key=len)

    def unsat_all_signs(comp_vars):
        # 对给定变量集，构造"全符号"蕴含图：每条见证无关边 (p,q) 对所有 k 的所有 (a,b) 加边
        # lit(p,a) -> lit(q, 1-b) 与 lit(q,b) -> lit(p,1-a)
        # 若该图 UNSAT（存在变量两字面量同 SCC），则无论符号/见证如何都矛盾
        lits = 2 * len(comp_vars)
        litid = {v: {0: 2 * i, 1: 2 * i + 1} for i, v in enumerate(comp_vars)}
        adj = [[] for _ in range(lits)]
        for (p, q) in wi_edges:
            if p not in comp_vars or q not in comp_vars:
                continue
            for k, pat_c in wi_edges[(p, q)]["patterns"].items():
                for c in (0, 1):
                    for (a, bb) in pat_c[c]:
                        lp_a = litid[p][a]
                        lq_b = litid[q][bb]
                        adj[lp_a].append(lq_b ^ 1)  # x_p=a -> x_q != b
                        adj[lq_b].append(lp_a ^ 1)  # x_q=b -> x_p != a
        # Tarjan
        index = [-1] * lits
        low = [0] * lits
        onstack = [False] * lits
        stack = []
        comp = [-1] * lits
        idx = 0
        cc = 0

        def sc(v):
            nonlocal idx, cc
            index[v] = low[v] = idx
            idx += 1
            stack.append(v)
            onstack[v] = True
            for w in adj[v]:
                if index[w] == -1:
                    sc(w)
                    low[v] = min(low[v], low[w])
                elif onstack[w]:
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                while True:
                    w = stack.pop()
                    onstack[w] = False
                    comp[w] = cc
                    if w == v:
                        break
                cc += 1

        for v in range(lits):
            if index[v] == -1:
                sc(v)
        for v in range(len(comp_vars)):
            if comp[litid[comp_vars[v]][0]] == comp[litid[comp_vars[v]][1]]:
                return True
        return False

    universal_cycles = []
    for comp in comps:
        cv = sorted(comp)
        if unsat_all_signs(cv):
            universal_cycles.append({"vars": cv, "n_vars": len(cv)})
        if len(universal_cycles) >= 5:
            break

    return {
        "basin": basin_id,
        "n_wi_edges": len(wi_edges),
        "n_vars_in_wi": len(var_set),
        "n_components_ge3": len(comps),
        "smallest_component_sizes": [len(c) for c in comps[:10]],
        "universal_odd_cycles": universal_cycles,
        "sample_wi_edges": [
            {"p": p, "q": q, "ks": d["ks"][:5], "n_ks": len(d["ks"])}
            for (p, q), d in list(wi_edges.items())[:10]
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin", default="v20_01")
    args = ap.parse_args()
    res = analyze_basin(args.basin)
    out_path = HERE / f"witness_independent_{args.basin}.json"
    out_path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

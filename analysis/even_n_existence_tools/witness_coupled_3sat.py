#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q-b 正确 sound 路线：见证耦合 3-CNF 判 G′。

对给定自由集 F、固定集 K=[37]\F，构造 3-CNF（变量 = 37 个 cell 位 x_c∈{0,1}）：
  对每 WI 边 (p,q)、每触发固定格 k∈K、每朝向 c∈{0,1}、每 combo_bad((p,a),(q,b),(k,c)) 的 (a,b)：
    子句 (y_k=c) ∨ ¬(x_p=a) ∨ ¬(x_q=b)
若此 3-CNF UNSAT ⇒ 对所有见证 β_F，Φ_bin(F,β_F) UNSAT（sound）。

理由：3-CNF UNSAT 意味无任何 (x,y) 赋值满足全部子句；子句被违当且仅当
y_k=c 且 x_p=a 且 x_q=b 且 combo_bad —— 即不存在"见证 y 下 x 取 witness-特定禁配"的赋值，
恰为 Φ_bin(y) 对所有 y 均 UNSAT。

用自写 DPLL（单元传播）判 UNSAT。对多随机 F 统计 UNSAT 比例。
[COMPUTATIONAL CERTIFICATE，sound]，产物 witness_coupled_3sat_<basin>.json。
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from reaudit_k14 import build_points, combo_bad

HERE = Path(__file__).resolve().parent


def build_wi(edges_37, bits_37):
    """WI 边 (p,q) -> {k: {c: [(a,b)]}}（两朝向都触发）。"""
    n = 37
    P = build_points(edges_37, bits_37)
    wi = {}
    for p in range(n):
        for q in range(p + 1, n):
            trig = {}
            for k in range(n):
                if k == p or k == q:
                    continue
                pat = {}
                ok = True
                for c in (0, 1):
                    bad = [(a, bb) for a in (0, 1) for bb in (0, 1)
                           if combo_bad(P, [(p, a), (q, bb), (k, c)])]
                    if not bad:
                        ok = False
                        break
                    pat[c] = bad
                if ok:
                    trig[k] = pat
            if trig:
                wi[(p, q)] = trig
    return wi


def build_3cnf(F, wi):
    """返回 3-CNF 子句列表（字面量 = 2*cell + val）。"""
    K = set(range(37)) - set(F)
    clauses = []
    for (p, q), trig in wi.items():
        if p not in F or q not in F:
            continue
        for k in trig:
            if k not in K:
                continue
            for c in (0, 1):
                for (a, bb) in trig[k][c]:
                    # (y_k=c) ∨ ¬(x_p=a) ∨ ¬(x_q=bb)
                    clauses.append([2 * k + c, (2 * p + a) ^ 1, (2 * q + bb) ^ 1])
    return clauses


def dpll_unsat(clauses, nvars=37, node_budget=2_000_000):
    """迭代式 DPLL（单元传播 + 活动变量剪枝 + MOM 分支）。
    返回 True=UNSAT, False=SAT, None=超出节点预算(未知)。
    赋值数组在递归间共享（修复原递归每次重建 assign 导致死循环 bug）。
    lit 编码：var=lit//2, 真值=lit%2；assign[lit]∈{-1,0,1}。
    """
    n = 2 * nvars
    assign = [-1] * n
    # 仅出现在子句中的字面量才需分支（其余无关变量可任意赋值）
    active = set()
    for cl in clauses:
        for lit in cl:
            active.add(lit)
    # 字面量出现频次（用于 MOM 启发式）
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
                    return False  # 冲突
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
            return True  # UNSAT（冲突）
        # 找活动未定变量（MOM：出现频次最高）
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
            return False  # 所有活动变量已赋且无冲突 → SAT
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

    return search()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin", default="v20_01")
    ap.add_argument("--trials", type=int, default=60)
    args = ap.parse_args()
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    b = next(x for x in arch["archive"] if x["id"] == args.basin)
    edges_37 = [tuple(e) for e in b["edges"]]
    bits_37 = list(b["bits"])
    print(f"构建 WI ({args.basin}) ...", flush=True)
    wi = build_wi(edges_37, bits_37)
    print(f"  WI 边数 = {len(wi)}", flush=True)
    rng = random.Random(20260721)
    all_cells = list(range(37))
    summ = {}
    for size in (14, 15):
        cnt = 0
        unk = 0
        for _ in range(args.trials):
            F = sorted(rng.sample(all_cells, size))
            clauses = build_3cnf(F, wi)
            r = dpll_unsat(clauses)
            if r is True:
                cnt += 1
            elif r is None:
                unk += 1
        summ[f"W{size}"] = {"n": args.trials, "unsat": cnt, "unknown": unk,
                             "frac": cnt / args.trials,
                             "unknown_frac": unk / args.trials}
        print(f"  W={size}: 见证耦合3-CNF UNSAT {cnt}/{args.trials} = {cnt/args.trials:.3f}"
              f"  (未知/超预算 {unk})", flush=True)
    out = {"basin": args.basin, "n_wi_edges": len(wi), "summary": summ}
    (HERE / f"witness_coupled_3sat_{args.basin}.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

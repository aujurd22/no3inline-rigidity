#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正版见证无关 G′ 检验（正确处理"触发边需有固定格 k"）。

关键修正：实际补全中二元边 (p,q) 存在 ⟺ 存在固定格 k∈K=[37]\F 触发它。
故对给定自由集 F，实际 WI 边 = {(p,q): p,q∈F, T(p,q)∩K≠∅}，其中 T(p,q) 为触发 k 集合。
检验该诱导子图在 ALL-SIGNS（所有触发 k 的所有禁 (a,b) 均加上）下是否 UNSAT。
若对所有随机 F 均 UNSAT ⇒ G′ 对该盆地得证（见证无关）。

先对 v20_01 跑（--basin），再扩全部 6 盆地。
[COMPUTATIONAL CERTIFICATE]，产物 witness_independent_universal_<basin>.json。
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from reaudit_k14 import build_points, combo_bad

HERE = Path(__file__).resolve().parent


def build_wi_structure(edges_37, bits_37):
    """返回 wi_edges: {(p,q): {k: {c: [(a,b),...]}}}，仅含两朝向都触发的 k。"""
    n = 37
    P = build_points(edges_37, bits_37)
    wi = {}
    for p in range(n):
        for q in range(p + 1, n):
            trig = {}
            for k in range(n):
                if k == p or k == q:
                    continue
                pat_c = {}
                ok = True
                for c in (0, 1):
                    bad = [(a, bb) for a in (0, 1) for bb in (0, 1)
                           if combo_bad(P, [(p, a), (q, bb), (k, c)])]
                    if not bad:
                        ok = False
                        break
                    pat_c[c] = bad
                if ok:
                    trig[k] = pat_c
            if trig:
                wi[(p, q)] = trig
    return wi


def all_signs_unsat(F, wi):
    """F=自由集列表；实际 WI 边需触发 k∈K=[37]\F。检查全符号 UNSAT。"""
    K = set(range(37)) - set(F)
    fvars = sorted(F)
    litid = {v: {0: 2 * i, 1: 2 * i + 1} for i, v in enumerate(fvars)}
    nv = len(fvars)
    adj = [[] for _ in range(2 * nv)]
    for (p, q), trig in wi.items():
        if p not in F or q not in F:
            continue
        usable = [k for k in trig if k in K]
        if not usable:
            continue  # 无固定触发格 → 该边在实际补全中不存在
        for k in usable:
            for c in (0, 1):
                for (a, bb) in trig[k][c]:
                    adj[litid[p][a]].append(litid[q][bb] ^ 1)
                    adj[litid[q][bb]].append(litid[p][a] ^ 1)
    lits = 2 * nv
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
    for v in fvars:
        if comp[litid[v][0]] == comp[litid[v][1]]:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin", default="v20_01")
    ap.add_argument("--trials", type=int, default=300)
    args = ap.parse_args()
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    b = next(x for x in arch["archive"] if x["id"] == args.basin)
    edges_37 = [tuple(e) for e in b["edges"]]
    bits_37 = list(b["bits"])
    print(f"构建 WI 结构 ({args.basin}) ...", flush=True)
    wi = build_wi_structure(edges_37, bits_37)
    print(f"  WI 边数 = {len(wi)}", flush=True)
    rng = random.Random(20260721)
    all_cells = list(range(37))
    summ = {}
    for size in (14, 15):
        cnt = 0
        smallest_unsat_core = None
        for _ in range(args.trials):
            F = sorted(rng.sample(all_cells, size))
            if all_signs_unsat(F, wi):
                cnt += 1
        summ[f"W{size}"] = {"n": args.trials, "unsat": cnt,
                             "frac": cnt / args.trials}
        print(f"  W={size}: 全符号UNSAT {cnt}/{args.trials} = {cnt/args.trials:.3f}", flush=True)
    out = {"basin": args.basin, "n_wi_edges": len(wi), "summary": summ}
    (HERE / f"witness_independent_universal_{args.basin}.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

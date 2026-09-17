#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正确（sound）的见证无关 G′ 检验：强 WI 边 + 固定符号图。

强 WI 边定义：存在 (a,b)∈{0,1}^2 与固定格 k，使 combo_bad((p,a),(q,b),(k,0)) 与
combo_bad((p,a),(q,b),(k,1)) **同时**成立（同一禁配 (a,b) 对两种见证朝向都共线）。
→ 该边对任意见证 β_F 都禁同一 (a,b)，符号固定、见证无关。

对给定自由集 F、固定集 K=[37]\F：实际强 WI 边 = {(p,q): p,q∈F, ∃k∈K 使 common(p,q,k)≠∅}。
构造**固定符号**蕴含图（只用 common (a,b)，对所有见证都成立），检查是否有奇环（UNSAT）。
若对某 F 该固定图 UNSAT ⇒ 对所有见证 Φ_bin(F,β_F) UNSAT（sound）。
若对所有随机 F 均 UNSAT ⇒ G′ 对该盆地得证（见证无关证书）。

[COMPUTATIONAL CERTIFICATE，sound]，产物 witness_independent_strong_<basin>.json。
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from reaudit_k14 import build_points, combo_bad

HERE = Path(__file__).resolve().parent


def build_strong_wi(edges_37, bits_37):
    """返回 strong_wi: {(p,q): {k: [(a,b),...]}}，common = 两朝向都禁的 (a,b)。"""
    n = 37
    P = build_points(edges_37, bits_37)
    sw = {}
    for p in range(n):
        for q in range(p + 1, n):
            trig = {}
            for k in range(n):
                if k == p or k == q:
                    continue
                common = [(a, bb) for a in (0, 1) for bb in (0, 1)
                          if combo_bad(P, [(p, a), (q, bb), (k, 0)])
                          and combo_bad(P, [(p, a), (q, bb), (k, 1)])]
                if common:
                    trig[k] = common
            if trig:
                sw[(p, q)] = trig
    return sw


def fixed_sign_unsat(F, sw):
    K = set(range(37)) - set(F)
    fvars = sorted(F)
    litid = {v: {0: 2 * i, 1: 2 * i + 1} for i, v in enumerate(fvars)}
    nv = len(fvars)
    adj = [[] for _ in range(2 * nv)]
    for (p, q), trig in sw.items():
        if p not in F or q not in F:
            continue
        usable = [k for k in trig if k in K]
        if not usable:
            continue
        for k in usable:
            for (a, bb) in trig[k]:  # 同一 (a,b) 对所有见证都禁 → 固定符号
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
    print(f"构建强 WI 结构 ({args.basin}) ...", flush=True)
    sw = build_strong_wi(edges_37, bits_37)
    print(f"  强 WI 边数 = {len(sw)}", flush=True)
    rng = random.Random(20260721)
    all_cells = list(range(37))
    summ = {}
    for size in (14, 15):
        cnt = 0
        for _ in range(args.trials):
            F = sorted(rng.sample(all_cells, size))
            if fixed_sign_unsat(F, sw):
                cnt += 1
        summ[f"W{size}"] = {"n": args.trials, "unsat": cnt, "frac": cnt / args.trials}
        print(f"  W={size}: 固定符号UNSAT {cnt}/{args.trials} = {cnt/args.trials:.3f}", flush=True)
    out = {"basin": args.basin, "n_strong_wi_edges": len(sw), "summary": summ}
    (HERE / f"witness_independent_strong_{args.basin}.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

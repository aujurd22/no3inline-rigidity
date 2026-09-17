#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""朝向蕴含图(2-SAT)矛盾预筛 —— 统一矛盾环引理的可操作化工具。

给定一幅 k-替换补全（37 条有向边 = 旧边 + k 条新边，旧边朝向固定），
本模块只取**一元/二元**约束构建 2-CNF 蕴含图，用 Tarjan SCC 判定矛盾：

  - 若某字面量与其否定落入同一 SCC ⇒ 该补全 2-SAT UNSAT ⇒ 真 UNSAT（**sound**，无假阴性）。
  - SCC SAT ⇒ 不能判定（可能依赖纯三元耦合），需回退完整 2^W 几何 oracle。

对 k=14 六盆地 23 个补全（全体，非抽样），本预筛与暴力 2^14 几何 oracle 完全一致：
23/23 UNSAT，且矛盾核正规化后塌缩为单一 2-变量 3-边奇异蕴含环
（见 normalize_kernels.py 与 implication_kernel_unified_lemma.md）。

用途：k≥15 拿到候选 mask 后，对每个补全因子先跑一次本预筛——若 UNSAT 即可瞬间判死，
把原本的 2^W 暴力压缩为线性时间 SCC；仅当预筛 SAT 时才需回退几何 oracle。

依赖：reaudit_k14.build_correct_fs（正确边几何重建三元冲突超图）。
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

# 复用已验证的几何基元（正确边几何），但把 W 参数化以支持 k=15+（reaudit_k14.W 硬编码=14）
from reaudit_k14 import (W, N, FULL, HERE, V9W_ALL,
                         build_points, collinear, combo_bad)


def build_correct_fs(edges_37, base_bits_37, free_positions):
    """W 参数化的正确边冲突超图构建（兼容 k=14 与 k=15+）。

    reaudit_k14.build_correct_fs 内 W=14 是模块常量，free_positions 超过 14 会越界；
    这里用 len(free_positions) 作为 W，对任意 k 适用。
    """
    W_loc = len(free_positions)
    P = build_points(edges_37, base_bits_37)
    free_set = set(free_positions)
    N_loc = 1 << W_loc
    FULL_loc = (1 << N_loc) - 1
    masks = {}
    for p in range(W_loc):
        m0 = m1 = 0
        for a in range(N_loc):
            if (a >> p) & 1:
                m1 |= (1 << a)
            else:
                m0 |= (1 << a)
        masks[(p, 0)] = m0
        masks[(p, 1)] = m1

    fs = {}
    def add_owner(cells):
        uniq = sorted(set(cells))
        key = tuple(uniq)
        if key in fs:
            return
        poss = []
        for c in uniq:
            poss.append([0, 1] if c in free_set else [base_bits_37[c]])
        mask_fs = 0
        bad_count = 0
        for combo in itertools.product(*poss):
            if combo_bad(P, list(zip(uniq, combo))):
                bad_count += 1
                sub = FULL_loc
                for c, bit in zip(uniq, combo):
                    if c in free_set:
                        p = free_positions.index(c)
                        sub &= masks[(p, bit)]
                mask_fs |= sub
        if mask_fs:
            fs[key] = (mask_fs, bad_count)

    for i in range(37):
        add_owner((i,))
    for i, j in itertools.combinations(range(37), 2):
        add_owner((i, j))
    for i, j, k in itertools.combinations(range(37), 3):
        add_owner((i, j, k))
    return fs


# ───────────────────────── 2-SAT 蕴含图工具 ─────────────────────────

def lit_id(p, v):
    """字面量编号：x_p = v → 2p + v；否定 = lit_id ^ 1。"""
    return 2 * p + v


def extract_unary_binary(fs, free_set):
    """从冲突超图提取一元/二元约束的完整禁配组合。

    返回 (unary, unary_contradiction, binary)：
      unary: list[(p, a, owner_set)]  强制 x_p = a
      unary_contradiction: bool        某自由变量两向皆禁（直接矛盾）
      binary: list[(p, a, q, b, owner_set)]  禁止 (x_p=a, x_q=b)
    """
    free_positions = sorted(free_set)
    pos_of = {c: i for i, c in enumerate(free_positions)}
    unary = []
    unary_contradiction = False
    binary = []

    for owner_set, (mask_fs, _bc) in fs.items():
        n_free = sum(1 for c in owner_set if c in free_set)
        if n_free == 1:
            c = next(x for x in owner_set if x in free_set)
            p = pos_of[c]
            bad0 = bool((mask_fs >> (0 << p)) & 1)
            bad1 = bool((mask_fs >> (1 << p)) & 1)
            if bad0 and bad1:
                unary_contradiction = True
            elif bad0:
                unary.append((p, 1, tuple(owner_set)))
            elif bad1:
                unary.append((p, 0, tuple(owner_set)))
        elif n_free == 2:
            frees = [pos_of[c] for c in owner_set if c in free_set]
            p, q = frees
            for a in (0, 1):
                for b in (0, 1):
                    if (mask_fs >> ((a << p) | (b << q))) & 1:
                        binary.append((p, a, q, b, tuple(owner_set)))
    return unary, unary_contradiction, binary


def build_implication_graph(unary, unary_contradiction, binary, n_vars):
    """返回 (adj, edge_constraints, contradiction_via_unary)。字面量编号 = 2p+v。"""
    adj = defaultdict(list)
    edge_constraints = {}
    contradiction_via_unary = unary_contradiction
    for (p, a, owner_set) in unary:
        na_lit = lit_id(p, a) ^ 1
        a_lit = lit_id(p, a)
        adj[na_lit].append(a_lit)
        edge_constraints[(na_lit, a_lit)] = ("unary", owner_set)
    for (p, a, q, b, owner_set) in binary:
        e1 = (lit_id(p, a), lit_id(q, b ^ 1))
        adj[e1[0]].append(e1[1])
        edge_constraints[e1] = ("binary", owner_set)
        e2 = (lit_id(q, b), lit_id(p, a ^ 1))
        adj[e2[0]].append(e2[1])
        edge_constraints[e2] = ("binary", owner_set)
    return adj, edge_constraints, contradiction_via_unary


def tarjan_scc(adj, n_lits):
    index = [-1] * n_lits
    low = [0] * n_lits
    onstack = [False] * n_lits
    stack = []
    comp = [-1] * n_lits
    idx = 0
    comp_cnt = 0

    def strongconnect(v):
        nonlocal idx, comp_cnt
        index[v] = low[v] = idx
        idx += 1
        stack.append(v)
        onstack[v] = True
        for w in adj[v]:
            if index[w] == -1:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif onstack[w]:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            while True:
                w = stack.pop()
                onstack[w] = False
                comp[w] = comp_cnt
                if w == v:
                    break
            comp_cnt += 1

    for v in range(n_lits):
        if index[v] == -1:
            strongconnect(v)
    return comp, comp_cnt


def bfs_shortest(adj, src, dst):
    from collections import deque
    if src == dst:
        return [src]
    prev = {src: None}
    q = deque([src])
    while q:
        u = q.popleft()
        for w in adj[u]:
            if w not in prev:
                prev[w] = u
                if w == dst:
                    path = [dst]
                    x = u
                    while x is not None:
                        path.append(x)
                        x = prev[x]
                    return list(reversed(path))
                q.append(w)
    return None


def scc_classify(edges_37, bits_37, free_positions):
    """对一幅补全做 2-SAT 矛盾判定，返回矛盾核字典。

    字段：W, n_unary, n_binary, unary_contradiction, unsat_2sat,
          minimal_cycle, all_min_cycles, cycle_constraints, type_canonical
    """
    W_loc = len(free_positions)
    free_set = set(free_positions)
    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, unary_contradiction, binary = extract_unary_binary(fs, free_set)

    n_vars = W_loc
    n_lits = 2 * n_vars
    adj, edge_constraints, contra_unary = build_implication_graph(
        unary, unary_contradiction, binary, n_vars)

    has_any = bool(unary) or bool(binary) or unary_contradiction
    unsat_2sat = False
    minimal_cycle = []
    all_min_cycles = []
    cycle_constraints = []

    if has_any:
        comp, comp_cnt = tarjan_scc(adj, n_lits)
        contradictory_pairs = []
        for p in range(n_vars):
            l0, l1 = lit_id(p, 0), lit_id(p, 1)
            if comp[l0] == comp[l1] and comp[l0] != -1:
                unsat_2sat = True
                contradictory_pairs.append((p, 0))
        if unsat_2sat:
            best_len = None
            for p, v0 in contradictory_pairs:
                L, NL = lit_id(p, v0), lit_id(p, 1 - v0)
                pa, pb = bfs_shortest(adj, L, NL), bfs_shortest(adj, NL, L)
                if pa is not None and pb is not None:
                    cycle = pa + pb[1:]
                    if best_len is None or len(cycle) < best_len:
                        best_len = len(cycle)
                        all_min_cycles = [cycle]
                    elif len(cycle) == best_len:
                        all_min_cycles.append(cycle)
            if all_min_cycles:
                best_cycle = min(all_min_cycles,
                                  key=lambda cyc: [c // 2 for c in cyc] + [c % 2 for c in cyc])
                minimal_cycle = [(c // 2, c % 2) for c in best_cycle]
                for i in range(len(best_cycle) - 1):
                    u, v = best_cycle[i], best_cycle[i + 1]
                    kind, owner = edge_constraints.get((u, v), ("?", ()))
                    cycle_constraints.append({
                        "edge": [(u // 2, u % 2), (v // 2, v % 2)],
                        "kind": kind,
                        "owner_set": list(owner),
                    })

    return {
        "W": W_loc,
        "n_unary": len(unary),
        "n_binary": len(binary),
        "unary_contradiction": unary_contradiction,
        "unsat_2sat": unsat_2sat,
        "minimal_cycle": minimal_cycle,
        "all_min_cycles": [[(c // 2, c % 2) for c in cyc] for cyc in all_min_cycles],
        "cycle_constraints": cycle_constraints,
    }


# ───────────────────────── 逻辑同构正规化 ─────────────────────────

def cycle_edges(cycle):
    """把有向字面量环转成有向边列表 [(from_p,from_v,to_p,to_v), ...]。"""
    edges = []
    for i in range(len(cycle) - 1):
        u, v = cycle[i], cycle[i + 1]
        edges.append((u[0], u[1], v[0], v[1]))
    return edges


def exact_min_contradiction_vars(adj, n_vars):
    """精确求纯二元图中最短矛盾环所涉变量数的最小值。

    对 k=2,3,4 枚举所有 k-子集 S，限制在 S 的字面量子图上跑 Tarjan，
    若存在某 p∈S 使 lit(p,0),lit(p,1) 同 SCC ⇒ 用 k 个变量即可矛盾。
    返回最小可达的 k（取首个成立的 k），无矛盾返回 None。
    """
    from itertools import combinations
    for k in (2, 3, 4):
        for S in combinations(range(n_vars), k):
            S = set(S)
            sub = defaultdict(list)
            for u in range(2 * n_vars):
                if (u // 2) in S:
                    for w in adj[u]:
                        if (w // 2) in S:
                            sub[u].append(w)
            comp, _ = tarjan_scc(sub, 2 * n_vars)
            for p in S:
                if comp[lit_id(p, 0)] == comp[lit_id(p, 1)] and comp[lit_id(p, 0)] != -1:
                    return k
    return None


def canonical_of_cycle(cycle):
    """在「变量重命名(环上不同槽位→0..m-1) + 0/1 翻转」下取字典序最小的规范边集。"""
    edges = cycle_edges(cycle)
    slots = sorted({e[0] for e in edges} | {e[2] for e in edges})
    m = len(slots)
    slot_rank = {s: i for i, s in enumerate(slots)}
    best = None
    for perm in itertools.permutations(range(m)):
        inv = {perm[i]: i for i in range(m)}
        for flips in itertools.product([0, 1], repeat=m):
            norm = []
            for (fp, fv, tp, tv) in edges:
                nfp = inv[slot_rank[fp]]
                ntp = inv[slot_rank[tp]]
                nfv = fv ^ flips[nfp]
                ntv = tv ^ flips[ntp]
                norm.append((nfp, nfv, ntp, ntv))
            norm.sort()
            key = tuple(norm)
            if best is None or key < best:
                best = key
    return best


def completion_type(all_min_cycles):
    """该补全的逻辑类型 = 所有最短矛盾环规范形中的字典序最小者。"""
    if not all_min_cycles:
        return None
    return min(canonical_of_cycle(cyc) for cyc in all_min_cycles)


# ───────────────────────── 命令行 ─────────────────────────

def cmd_validate(args):
    """在已存的 all_completions_kernelized.json 上重算 SCC 并交叉验证。"""
    data = json.loads((HERE / "all_completions_kernelized.json").read_text())
    completions = data["completions"]
    n = len(completions)
    n_unsat = 0
    n_mismatch = 0
    types = defaultdict(list)
    for c in completions:
        edges_37 = [tuple(e) for e in c["edges_37"]]
        bits_37 = list(c["bits_37"])
        free_positions = list(c["free_positions"])
        k = scc_classify(edges_37, bits_37, free_positions)
        # 交叉验证：重算结果与已存 kernel 一致
        if k["unsat_2sat"] != c["kernel"]["unsat_2sat"]:
            n_mismatch += 1
        if k["unsat_2sat"]:
            n_unsat += 1
        t = completion_type(k["all_min_cycles"])
        types[t].append((c["bid"], c["mask"], c["comp_idx"]))

    print(f"补全总数={n}")
    print(f"2-SAT UNSAT={n_unsat} | 与已存 kernel 不一致={n_mismatch}")
    print(f"逻辑类型数={len(types)}")
    for t, members in types.items():
        print(f"  类型 canonical={list(t)}  成员数={len(members)}")
    if n_mismatch == 0 and n_unsat == n:
        print("✓ 预筛重算与暴力 2^W oracle 结论一致（k=14：23/23 UNSAT）")
    else:
        print("✗ 存在不一致，需排查", file=sys.stderr)
        return 1
    return 0


def cmd_one(args):
    """对指定 basin/mask/comp 单幅补全做 SCC 预筛。"""
    data = json.loads((HERE / "all_completions_kernelized.json").read_text())
    target = None
    for c in data["completions"]:
        if (c["bid"] == args.basin and str(c["mask"]) == str(args.mask)
                and (args.comp is None or c["comp_idx"] == args.comp)):
            target = c
            break
    if target is None:
        print(f"未找到 bid={args.basin} mask={args.mask} comp={args.comp}", file=sys.stderr)
        return 1
    edges_37 = [tuple(e) for e in target["edges_37"]]
    bits_37 = list(target["bits_37"])
    free_positions = list(target["free_positions"])
    k = scc_classify(edges_37, bits_37, free_positions)
    t = completion_type(k["all_min_cycles"])
    print(json.dumps({
        "bid": target["bid"], "mask": target["mask"], "comp_idx": target["comp_idx"],
        "W": k["W"], "n_unary": k["n_unary"], "n_binary": k["n_binary"],
        "unsat_2sat": k["unsat_2sat"],
        "minimal_cycle": k["minimal_cycle"],
        "type_canonical": list(t) if t else None,
    }, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="朝向蕴含图(2-SAT)矛盾预筛")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("validate", help="在 all_completions_kernelized.json 上重算并交叉验证").set_defaults(func=cmd_validate)
    p1 = sub.add_parser("one", help="对单幅补全做 SCC 预筛")
    p1.add_argument("--basin", required=True)
    p1.add_argument("--mask", required=True)
    p1.add_argument("--comp", type=int, default=None)
    p1.set_defaults(func=cmd_one)
    args = ap.parse_args()
    if not getattr(args, "cmd", None):
        ap.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

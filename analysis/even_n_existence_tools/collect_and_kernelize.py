#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收集全部 23 个补全因子，并为每个构建朝向蕴含图(2-SAT)矛盾核。

步骤：
1. 复用 reaudit_k14 的枚举逻辑，对 6 个盆地用 v9w_all.exe 取全部补全因子。
2. 对每个补全：用 C++ 补回的 37 条边重建冲突超图(build_correct_fs，正确边)。
3. 只取一元(n_free=1)、二元(n_free=2)约束，写成完整禁配组合。
4. 转成蕴含图(2-CNF 字面量图)，Tarjan 求 SCC，若某字面与 ¬它同 SCC → 矛盾。
5. 提取最短矛盾环(含某字面及其否定的最短有向环)与矛盾 SCC 子图。
6. 落盘 all_completions_kernelized.json，供后续逻辑同构正规化。

与旧 k14_reaudit.json 的区别：这里存的是 *完整* 禁配组合 + 全部 23 个补全(而非仅 19 个代表)。
"""
from __future__ import annotations

import glob
import itertools
import json
import subprocess
from collections import defaultdict
from pathlib import Path

# 复用已验证的几何与枚举逻辑
from reaudit_k14 import (
    W, N, FULL, HERE, V9W_ALL,
    build_points, collinear, combo_bad, build_correct_fs,
)
from audit_v20_k14_chunked import build_tokens, owner_mask
from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers

# ─── 2-SAT 蕴含图工具 ───

def lit_id(p, v):
    """字面量编号：x_p = v → 2p + v。否定 = lit_id ^ 1。"""
    return 2 * p + v

def extract_unary_binary(fs, free_set):
    """从冲突超图提取一元/二元约束的完整禁配组合。

    返回：
      unary: list[(p, a, owner_set)] 表示强制 x_p = a（来自 owner_set 子句）
      unary_contradiction: bool  (某自由变量两种朝向都被禁)
      binary: list[(p, a, q, b, owner_set)] 表示禁止 (x_p=a, x_q=b)
    """
    free_positions = sorted(free_set)
    pos_of = {c: i for i, c in enumerate(free_positions)}
    unary = []
    unary_contradiction = False
    binary = []

    for owner_set, (mask_fs, _bc) in fs.items():
        n_free = sum(1 for c in owner_set if c in free_set)
        if n_free == 1:
            # 唯一的自由变量
            c = next(x for x in owner_set if x in free_set)
            p = pos_of[c]
            bad0 = bool((mask_fs >> (0 << p)) & 1)
            bad1 = bool((mask_fs >> (1 << p)) & 1)
            if bad0 and bad1:
                unary_contradiction = True
            elif bad0:
                unary.append((p, 1, tuple(owner_set)))   # x_p=0 被禁 → 强制 1
            elif bad1:
                unary.append((p, 0, tuple(owner_set)))   # x_p=1 被禁 → 强制 0
        elif n_free == 2:
            frees = [pos_of[c] for c in owner_set if c in free_set]
            p, q = frees
            for a in (0, 1):
                for b in (0, 1):
                    if (mask_fs >> ((a << p) | (b << q))) & 1:
                        binary.append((p, a, q, b, tuple(owner_set)))
    return unary, unary_contradiction, binary

def build_implication_graph(unary, unary_contradiction, binary, n_vars):
    """返回邻接表(字面量编号 → list) 与边→约束映射。字面量编号 = 2p+v，否定 = ^1。"""
    adj = defaultdict(list)
    edge_constraints = {}  # (u_lit, v_lit) -> (kind, owner_set)
    contradiction_via_unary = unary_contradiction
    # 一元力：x_p=a → 强制。在蕴含图中加 ¬(x_p=a) → (x_p=a)
    for (p, a, owner_set) in unary:
        na_lit = lit_id(p, a) ^ 1
        a_lit = lit_id(p, a)
        adj[na_lit].append(a_lit)
        edge_constraints[(na_lit, a_lit)] = ("unary", owner_set)
    # 二元禁配：禁止 (x_p=a, x_q=b) ≡ (x_p=¬a ∨ x_q=¬b)
    for (p, a, q, b, owner_set) in binary:
        # (x_p=¬a) ∨ (x_q=¬b)
        # ¬(x_p=¬a) → (x_q=¬b)  : (x_p=a) → (x_q=¬b)
        e1 = (lit_id(p, a), lit_id(q, b ^ 1))
        adj[e1[0]].append(e1[1])
        edge_constraints[e1] = ("binary", owner_set)
        # ¬(x_q=¬b) → (x_p=¬a)  : (x_q=b) → (x_p=¬a)
        e2 = (lit_id(q, b), lit_id(p, a ^ 1))
        adj[e2[0]].append(e2[1])
        edge_constraints[e2] = ("binary", owner_set)
    return adj, edge_constraints, contradiction_via_unary

def tarjan_scc(adj, n_lits):
    """标准 Tarjan，返回 comp_id[lit]。"""
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
    """返回从 src 到 dst 的最短路径(list of 字面量编号)或 None。"""
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
                    # 回溯
                    path = [dst]
                    x = u
                    while x is not None:
                        path.append(x)
                        x = prev[x]
                    return list(reversed(path))
                q.append(w)
    return None

def analyze_completion(edges_37, bits_37, free_positions):
    """返回该补全的 2-SAT 矛盾核分析。"""
    W_loc = len(free_positions)
    free_set = set(free_positions)
    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, unary_contradiction, binary = extract_unary_binary(fs, free_set)

    n_vars = W_loc
    n_lits = 2 * n_vars
    adj, edge_constraints, contra_unary = build_implication_graph(
        unary, unary_contradiction, binary, n_vars)

    # 空图化简：没有约束就必然 SAT
    has_any_constraint = bool(unary) or bool(binary) or unary_contradiction
    unsat_2sat = False
    scc_nodes = []
    scc_edges = []
    minimal_cycle = []
    cycle_constraints = []
    contradictory_pairs = []

    if has_any_constraint:
        comp, comp_cnt = tarjan_scc(adj, n_lits)
        # 找矛盾对：字面与否定同 SCC
        for p in range(n_vars):
            l0 = lit_id(p, 0)
            l1 = lit_id(p, 1)
            if comp[l0] == comp[l1] and comp[l0] != -1:
                unsat_2sat = True
                contradictory_pairs.append((p, 0))
        if unsat_2sat:
            # 矛盾 SCC = 含某变量字面与其否定的所有 SCC
            bad_comps = set()
            for p in range(n_vars):
                if comp[lit_id(p,0)] == comp[lit_id(p,1)]:
                    bad_comps.add(comp[lit_id(p,0)])
            # 收集这些 SCC 的节点与边
            node_set = set()
            edge_set = set()
            for v in range(n_lits):
                if comp[v] in bad_comps:
                    node_set.add(v)
            for v in node_set:
                for w in adj[v]:
                    if comp[w] in bad_comps:
                        edge_set.add((v, w))
            scc_nodes = sorted(node_set)
            scc_edges = sorted(edge_set)
            # 最短矛盾环：遍历矛盾对，收集所有达到最短长度的环(保证同构不变)
            best_len = None
            all_min_cycles = []
            for p, v0 in contradictory_pairs:
                L = lit_id(p, v0)
                NL = lit_id(p, 1 - v0)
                pa = bfs_shortest(adj, L, NL)
                pb = bfs_shortest(adj, NL, L)
                if pa is not None and pb is not None:
                    cycle = pa + pb[1:]  # 拼接，去重衔接点
                    if best_len is None or len(cycle) < best_len:
                        best_len = len(cycle)
                        all_min_cycles = [cycle]
                    elif len(cycle) == best_len:
                        all_min_cycles.append(cycle)
            if all_min_cycles:
                # 取字面序列字典序最小的环作为代表(仅供展示)
                best_cycle = min(all_min_cycles,
                                  key=lambda cyc: [c // 2 for c in cyc] + [c % 2 for c in cyc])
                minimal_cycle = [(c // 2, c % 2) for c in best_cycle]
                # 环上每条边对应的约束(几何 owner_set)，用于翻译回几何
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
        "unary_forces": [(p, a) for (p, a, _o) in unary],
        "binary_forbidden": [(p, a, q, b) for (p, a, q, b, _o) in binary],
        # 带 owner_set 的完整约束(供几何翻译)
        "unary_full": [(p, a, list(o)) for (p, a, o) in unary],
        "binary_full": [(p, a, q, b, list(o)) for (p, a, q, b, o) in binary],
        "unsat_2sat": unsat_2sat,
        "scc_nodes": [(c // 2, c % 2) for c in scc_nodes],
        "scc_edges": [[(e[0]//2, e[0]%2), (e[1]//2, e[1]%2)] for e in scc_edges],
        "minimal_cycle": minimal_cycle,
        "all_min_cycles": [[(c // 2, c % 2) for c in cyc] for cyc in all_min_cycles],
        "cycle_constraints": cycle_constraints,
    }

def main():
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    by_id = {b["id"]: b for b in archive["archive"]}

    cert_files = sorted(glob.glob(str(HERE / "v20_*_k14_certification.json")))
    all_masks = []
    for cf in cert_files:
        d = json.load(open(cf))
        bid = d["base"]
        for s in d["survivors"]:
            all_masks.append((bid, s["mask"]))
    print(f"共 {len(all_masks)} 个幸存 mask")

    masks_by_basin = {}
    for bid, mask in all_masks:
        masks_by_basin.setdefault(bid, []).append(mask)

    completions = []  # 每个补全的完整记录
    basin_meta = {}   # bid -> {edges, bits}

    for bid, masks in masks_by_basin.items():
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        bits_old = list(base["bits"])
        components = ordered_components(edges_old)
        blockers = candidate_blockers(base)
        hitting = json.loads((HERE / f"v20_defect_hitting_{bid}.json").read_text())
        defects = [owner_mask_of(v) for v in hitting["defect_owner_sets"]]

        tokens = build_tokens(base, 14, masks, 3, defects, blockers, components)
        print(f"[v9w_all] {bid} ...", end=" ", flush=True)
        res = json.loads(subprocess.run(
            [str(V9W_ALL)], input=tokens, text=True,
            capture_output=True, check=True,
        ).stdout)
        wf_by_mask = {}
        for entry in res.get("witness_factors", []):
            m = entry["mask"]
            cells = [tuple(c) for c in entry["cells"]]
            wf_by_mask.setdefault(m, []).append(cells)
        print(f"OK 因子数={[len(wf_by_mask.get(m,[])) for m in masks]}", flush=True)

        basin_meta[bid] = {"edges": edges_old, "bits": bits_old}

        for mask in masks:
            comps = wf_by_mask.get(mask, [])
            print(f"  {bid} mask={mask}: {len(comps)} 个补全因子")
            for ci, cells in enumerate(comps):
                # 构造 37 条边
                edges_37 = []
                wi = 0
                for i in range(37):
                    if (mask >> i) & 1:
                        edges_37.append(cells[wi])
                        wi += 1
                    else:
                        edges_37.append(tuple(edges_old[i]))
                free_positions = [i for i in range(37) if (mask >> i) & 1]
                assert len(free_positions) == W
                kernel = analyze_completion(edges_37, bits_old, free_positions)
                completions.append({
                    "bid": bid,
                    "mask": mask,
                    "comp_idx": ci,
                    "cells": cells,                 # 14 条新边
                    "edges_37": edges_37,           # 完整 37 边
                    "bits_37": bits_old,            # 37 朝向(旧边固定)
                    "free_positions": free_positions,
                    "kernel": kernel,
                })
                flag = "UNSAT(2-SAT)" if kernel["unsat_2sat"] else "SAT?"
                print(f"    comp#{ci}: 一元={kernel['n_unary']} 二元={kernel['n_binary']} "
                      f"矛盾={flag} 环长={len(kernel['minimal_cycle'])}")

    out = {
        "k": 14,
        "W": W,
        "n_completions_total": len(completions),
        "basin_meta": basin_meta,
        "completions": completions,
    }
    out_path = HERE / "all_completions_kernelized.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n写入 {out_path}")
    n_unsat = sum(1 for c in completions if c["kernel"]["unsat_2sat"])
    n_unary_contra = sum(1 for c in completions if c["kernel"]["unary_contradiction"])
    print(f"补全总数={len(completions)} | 2-SAT 矛盾={n_unsat} | 一元直接矛盾={n_unary_contra}")

def owner_mask_of(v):
    return owner_mask(v)

if __name__ == "__main__":
    main()

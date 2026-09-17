#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 23 个补全的 2-SAT 矛盾核做逻辑同构正规化与类型聚合。

正规化对象 = 每个补全的所有「最短矛盾环」的边集(蕴含图有向边)。
对称商：
  (1) 变量重命名：环上出现的不同自由槽位 → 0..m-1
  (2) 0/1 翻转：每个槽位的字面量值可翻转
取所有(重命名 × 翻转)下的最小规范形。再对补全的所有最短环取最小，得到该补全的逻辑类型。
后续可叠加 C4(坐标旋转)对称，见末尾注释。
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent

def cycle_edges(cycle):
    """环(字面量序列, 首尾相同) → 有向边列表 [(from_lit, to_lit), ...]。"""
    return [(cycle[i], cycle[i + 1]) for i in range(len(cycle) - 1)]

def canonical_of_cycle(cycle):
    """返回该环在(重命名 × 翻转)下的最小规范形字符串，以及达到最小的代表映射。"""
    edges = cycle_edges(cycle)
    slots = sorted({s for (s, _v) in cycle})
    m = len(slots)
    slot_index = {s: i for i, s in enumerate(slots)}
    best = None
    best_repr = None
    for perm in itertools.permutations(range(m)):
        perm_map = {slots[i]: perm[i] for i in range(m)}
        for flip in range(1 << m):
            flip_map = {slots[i]: (flip >> i) & 1 for i in range(m)}
            norm_edges = []
            for (s1, v1), (s2, v2) in edges:
                ns1 = perm_map[s1]; nv1 = v1 ^ flip_map[s1]
                ns2 = perm_map[s2]; nv2 = v2 ^ flip_map[s2]
                norm_edges.append((ns1, nv1, ns2, nv2))
            cand = tuple(sorted(norm_edges))
            if best is None or cand < best:
                best = cand
                best_repr = (perm_map, flip_map)
    return best, best_repr

def completion_type(all_min_cycles):
    best = None
    for cyc in all_min_cycles:
        cf, _repr = canonical_of_cycle(cyc)
        if best is None or cf < best:
            best = cf
    return best

def main():
    data = json.loads((HERE / "all_completions_kernelized.json").read_text())
    completions = data["completions"]

    # 计算每个补全的逻辑类型(规范形)
    for c in completions:
        c["type"] = completion_type(c["kernel"]["all_min_cycles"])

    # 聚类
    groups = defaultdict(list)
    for c in completions:
        groups[c["type"]].append(c)

    print(f"补全总数={len(completions)} | 逻辑类型数={len(groups)}")
    print("=" * 70)
    # 按类型规模降序展示
    for tidx, (ctype, members) in enumerate(
            sorted(groups.items(), key=lambda kv: -len(kv[1]))):
        print(f"\n### 类型 #{tidx}  (规模={len(members)})  规范形={ctype}")
        rep = members[0]
        k = rep["kernel"]
        print(f"  代表: {rep['bid']} mask={rep['mask']} #{rep['comp_idx']}  "
              f"一元={k['n_unary']} 二元={k['n_binary']} 环长={len(k['minimal_cycle'])}")
        print(f"  代表环(字面量): {k['minimal_cycle']}")
        print(f"  代表环约束(几何 owner_set, 单元索引):")
        for cc in k["cycle_constraints"]:
            tag = "一元力" if cc["kind"] == "unary" else "二元禁配"
            print(f"    [{tag}] edge={cc['edge']} owner_set={cc['owner_set']}")
        members_str = ", ".join(
            f"{m['bid']}:{m['mask']}#{m['comp_idx']}" for m in members)
        print(f"  成员({len(members)}): {members_str}")

    # 保存聚类结果
    out = {
        "n_completions": len(completions),
        "n_types": len(groups),
        "types": [
            {
                "type": ctype,
                "size": len(members),
                "members": [
                    {"bid": m["bid"], "mask": m["mask"], "comp_idx": m["comp_idx"]}
                    for m in members
                ],
                "representative": {
                    "bid": members[0]["bid"],
                    "mask": members[0]["mask"],
                    "comp_idx": members[0]["comp_idx"],
                    "minimal_cycle": members[0]["kernel"]["minimal_cycle"],
                    "cycle_constraints": members[0]["kernel"]["cycle_constraints"],
                },
            }
            for ctype, members in sorted(groups.items(), key=lambda kv: -len(kv[1]))
        ],
    }
    out_path = HERE / "kernel_types.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n写入 {out_path}")

if __name__ == "__main__":
    main()

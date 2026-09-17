#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把统一矛盾核翻译回几何：对若干补全，把最短矛盾环的每条边匹配到真正的约束，
输出涉及的新/旧边单元、坐标、朝向。"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def lid(p, v):
    return 2 * p + v

def match_edge(u, v, unary_full, binary_full):
    """u,v 是字面量(slot,value)。返回 ('unary', owner) 或 ('binary', owner) 或 None。"""
    s1, v1 = u
    s2, v2 = v
    # 一元: (p, ¬a) -> (p, a)
    for (p, a, owner) in unary_full:
        if (lid(p, a ^ 1), lid(p, a)) == (lid(s1, v1), lid(s2, v2)):
            return ("unary", owner)
    # 二元: (p,a) -> (q, ¬b) 或 (q,b) -> (p, ¬a)
    for (p, a, q, b, owner) in binary_full:
        if (lid(p, a), lid(q, b ^ 1)) == (lid(s1, v1), lid(s2, v2)):
            return ("binary", owner)
        if (lid(q, b), lid(p, a ^ 1)) == (lid(s1, v1), lid(s2, v2)):
            return ("binary", owner)
    return None

def describe_completion(c):
    bid = c["bid"]; mask = c["mask"]; ci = c["comp_idx"]
    k = c["kernel"]
    free = set(c["free_positions"])
    edges_37 = c["edges_37"]
    bits_37 = c["bits_37"]
    unary_full = k["unary_full"]
    binary_full = k["binary_full"]
    print(f"\n{'='*72}\n{bid} mask={mask} #{ci}")
    print(f"  自由槽位(free_positions)={c['free_positions']}")
    print(f"  最短矛盾环(字面量)={k['minimal_cycle']}")
    cyc = k["minimal_cycle"]
    for i in range(len(cyc) - 1):
        u, v = cyc[i], cyc[i + 1]
        m = match_edge(u, v, unary_full, binary_full)
        if m is None:
            print(f"  edge {u}->{v}: [未匹配]")
            continue
        kind, owner = m
        desc = []
        for cell in owner:
            uu, vv = edges_37[cell]
            is_new = cell in free
            orient = bits_37[cell] if not is_new else "自由"
            tag = "新边" if is_new else "旧边"
            desc.append(f"cell{cell}({tag},{uu}->{vv},朝向={orient})")
        print(f"  edge {u}->{v}: [{kind}] " + " + ".join(desc))

def main():
    data = json.loads((HERE / "all_completions_kernelized.json").read_text())
    cs = data["completions"]
    # 代表 + 跨盆地取样
    picks = [
        ("v20_01", 8929978983, 0),
        ("v20_03", 20074551377, 0),
        ("v20_05", 26914261035, 0),
        ("v20_04", 74499532496, 0),
    ]
    for bid, mask, ci in picks:
        for c in cs:
            if c["bid"] == bid and c["mask"] == mask and c["comp_idx"] == ci:
                describe_completion(c)
                break

if __name__ == "__main__":
    main()

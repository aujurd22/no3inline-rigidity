# -*- coding: utf-8 -*-
"""对齐「另一个 agent」给出的 k=14 每补全陷阱数统计（1–11，均 5.83）。

直接对 all_completions_kernelized.json 的 23 个补全，扫描多种陷阱口径，
找出 mean≈5.83 / max≈11 的那个，即原 5.83 的确切定义。
"""
import json, statistics
from collections import defaultdict
from scc_prescreen import build_correct_fs, extract_unary_binary

HERE = __import__("pathlib").Path(__file__).resolve().parent
data = json.loads((HERE / "all_completions_kernelized.json").read_text())
comps = data["completions"]

def stats(xs):
    return f"min={min(xs)} max={max(xs)} mean={sum(xs)/len(xs):.3f} n={len(xs)}"

rows = defaultdict(list)
for c in comps:
    e = [tuple(x) for x in c["edges_37"]]
    b = list(c["bits_37"])
    fp = list(c["free_positions"])
    fs = build_correct_fs(e, b, fp)
    unary, _uc, binary = extract_unary_binary(fs, set(fp))

    # 去重一元力 (p,a) 及其位置集合
    uforced = {}            # p -> set of forced values
    for (p, a, _o) in unary:
        uforced.setdefault(p, set()).add(a)
    uforced_pos = set(uforced.keys())

    # 二元分组： (p,a) -> list of (q,b)
    bp = defaultdict(list)
    for (p, a, q, bb, _o) in binary:
        bp[(p, a)].append((q, bb))

    # 口径 A：严格 T(a,b;s)：a 强制且 b 两朝向都禁，去重 (a,b)
    strict = set()
    for p, vals in uforced.items():
        for s in vals:
            bq = defaultdict(lambda: {"0": 0, "1": 0})
            for (q, bb) in bp.get((p, s), []):
                bq[q][str(bb)] += 1
            for q, d in bq.items():
                if d["0"] and d["1"]:
                    strict.add((p, q))
    rows["A_strict_T(a强制,b两禁)"].append(len(strict))

    # 口径 B：a 强制，b 至少一朝向被禁，去重 (a,b)
    btouch = set()
    for p, vals in uforced.items():
        for s in vals:
            for (q, bb) in bp.get((p, s), []):
                btouch.add((p, q))
    rows["B_a强制,b至少一禁"].append(len(btouch))

    # 口径 C：所有二元禁止去重 (p,q)（p<q 无序），涉及自由变量
    allpairs = set()
    for (p, a, q, bb, _o) in binary:
        allpairs.add((min(p, q), max(p, q)))
    rows["C_所有二元对(p,q)"].append(len(allpairs))

    # 口径 D：二元禁止去重 (p,q)，p 或 q 被一元力强制
    forcedpairs = set()
    for (p, a, q, bb, _o) in binary:
        if p in uforced_pos or q in uforced_pos:
            forcedpairs.add((min(p, q), max(p, q)))
    rows["D_二元对含强制端"].append(len(forcedpairs))

    # 口径 E：被一元力强制的位置数
    rows["E_强制位置数"].append(len(uforced_pos))

    # 口径 F：二元条款总数（去重 (p,a,q,b)）
    bin_set = set((p, a, q, bb) for (p, a, q, bb, _o) in binary)
    rows["F_二元条款数"].append(len(bin_set))

    # 口径 G：每强制位置 a 的关联 b 数之和（多算视角）
    g = 0
    for p, vals in uforced.items():
        for s in vals:
            g += len({q for (q, _bb) in bp.get((p, s), [])})
    rows["G_强制端关联b数之和"].append(g)

    # 口径 H：反向也算——b 被强制时 (a,b) 也计（对称 T），去重无序 {a,b}
    sym = set()
    for p, vals in uforced.items():
        for s in vals:
            for (q, _bb) in bp.get((p, s), []):
                sym.add(frozenset((p, q)))
    rows["H_对称陷阱(无序{a,b})"].append(len(sym))

print(f"补全总数 = {len(comps)}\n")
for name in sorted(rows, key=lambda k: -statistics.mean(rows[k])):
    print(f"{name:32s} {stats(rows[name])}")

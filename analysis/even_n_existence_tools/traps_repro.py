# -*- coding: utf-8 -*-
"""尝试复现用户口述的 k=14「每补全 1–11 个陷阱、均≈5.83」。

测试多个候选口径，找 mean≈5.83 / max≈11 的那个，作为 5.83 的精确定义。
"""
import json, statistics
from collections import defaultdict
from scc_prescreen import build_correct_fs, extract_unary_binary

HERE = __import__("pathlib").Path(__file__).resolve().parent
data = json.loads((HERE / "all_completions_kernelized.json").read_text())
comps = data["completions"]


def reach_closure(adj, n):
    """Floyd-Warshall 传递闭包，返回可达矩阵。"""
    INF = 10 ** 9
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
    for u in range(n):
        for v in adj[u]:
            dist[u][v] = 1
    for k in range(n):
        dk = dist[k]
        for i in range(n):
            dik = dist[i]
            if dik[k] == INF:
                continue
            for j in range(n):
                nd = dik[k] + dk[j]
                if nd < dik[j]:
                    dik[j] = nd
    return dist


def analyze(c):
    e = [tuple(x) for x in c["edges_37"]]
    b = list(c["bits_37"])
    fp = list(c["free_positions"])
    fs = build_correct_fs(e, b, fp)
    unary, _uc, binary = extract_unary_binary(fs, set(fp))
    W = len(fp)
    rows = {}

    # —— 直接一元力 (p -> set of forced vals) ——
    uforced = defaultdict(set)
    for (p, a, _o) in unary:
        uforced[p].add(a)
    uforced_pos = set(ufordced := uforced.keys())

    # —— 蕴含图（含 unary + binary 边）——
    Nl = 2 * W
    adj = [[] for _ in range(Nl)]
    def L(p, v):
        return 2 * p + v
    for (p, s) in [(p, s) for p, vs in uforced.items() for s in vs]:
        # 强制 a=s： ¬(a=s) -> (a=s)
        adj[L(p, 1 - s)].append(L(p, s))
    for (p, a, q, bb, _o) in binary:
        adj[L(p, a)].append(L(q, 1 - bb))
        adj[L(q, bb)].append(L(p, 1 - a))
    dist = reach_closure(adj, Nl)
    def reach(u, v):
        return dist[u][v] < 10 ** 9

    # 口径 I：完整蕴含图强制（含间接链），(a,b) 去重
    I = set()
    forced_pairs = []
    for p in range(W):
        for s in (0, 1):
            # a=p 被强制为 s: ¬(p,s) 可达 (p,s)
            if reach(L(p, 1 - s), L(p, s)):
                forced_pairs.append((p, s))
                for q in range(W):
                    if q == p:
                        continue
                    if reach(L(p, s), L(q, 0)) and reach(L(p, s), L(q, 1)):
                        I.add((p, q))
    rows["I_全图强制(a,b)"] = len(I)

    # 口径 J：strict (a 直接一元强制 & b 两禁) 的 b 去重
    bp = defaultdict(list)
    for (p, a, q, bb, _o) in binary:
        bp[(p, a)].append((q, bb))
    J = set()
    strict_pairs = set()
    for p, vs in uforced.items():
        for s in vs:
            bq = defaultdict(lambda: {"0": 0, "1": 0})
            for (q, bb) in bp.get((p, s), []):
                bq[q][str(bb)] += 1
            for q, d in bq.items():
                if d["0"] and d["1"]:
                    strict_pairs.add((p, q))
                    J.add(q)
    rows["A_strict(a,b)"] = len(strict_pairs)        # 已知 2.83
    rows["J_strict的b去重"] = len(J)

    # 口径 K：strict 陷阱的二元见证条款数 = 2 × strict_pairs
    rows["K_2xStrict条款数"] = 2 * len(strict_pairs)

    # 口径 N：直接一元强制 a 引发的所有二元禁止条款数（去重 (a,s,b,t)）
    Ncnt = len({(p, a, q, bb) for (p, a, q, bb, _o) in binary if p in uforced_pos})
    rows["N_a强制二元条款数"] = Ncnt

    # 口径 O：每补全不同的「强制变量 a」数（含间接）
    rows["O_强制变量数(含间接)"] = len(forced_pairs)

    return rows


allrows = defaultdict(list)
for c in comps:
    for k, v in analyze(c).items():
        allrows[k].append(v)

print(f"补全总数 = {len(comps)}\n")
order = ["A_strict(a,b)", "I_全图强制(a,b)", "J_strict的b去重",
         "K_2xStrict条款数", "N_a强制二元条款数", "O_强制变量数(含间接)"]
print(f"{'口径':24s} {'min':>4s} {'max':>4s} {'mean':>7s}")
for k in order:
    xs = allrows[k]
    print(f"{k:24s} {min(xs):4d} {max(xs):4d} {sum(xs)/len(xs):7.3f}")
print("\n目标: min=1 max=11 mean≈5.83")

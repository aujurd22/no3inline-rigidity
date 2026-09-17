"""
defect_cluster_m37.py — 缺陷局域化理论测量.

把当前最优 2-因子 (mega_sweep_v2: 408 子句 / 16 违例) 的 16 个违例
精确映射回涉及的 cell (edge 索引), 判断缺陷是局域(少数 cell)还是全局分布.

理论意义:
  - 若 16 违例集中在 <= ~12 个 cell, 则可对该局部簇做穷举修复(固定其余 27 边,
    搜索该簇的所有 2-因子重排) -> 构造解的可行路径.
  - 若缺陷分散在大量 cell, 则说明残差本质是全局耦合, 局部修复无效.

同时输出每 cell 在"全部子句"中的频率(与 448_hotspots 的 5 热边对比) 及
"违例子句"中的频率, 定位真正的缺陷核.
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import solver_2factor_sat_pipeline as P

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37

def main():
    t0 = time.time()
    # 载入最优构型
    with open(os.path.join(HERE, "results", "mega_sweep_v2.json")) as f:
        data = json.load(f)
    edges = [tuple(e) for e in data["best_edges"]]
    print(f"[load] best_clauses={data['best_clauses']} best_viol={data['best_violations']} "
          f"n_edges={len(edges)}", flush=True)

    # 枚举子句
    clauses, cmap = P.enumerate_clauses(M, edges, verbose=True)
    n_clauses = len(clauses)
    print(f"[enum] {n_clauses} clauses", flush=True)

    # SAT / MaxSAT
    res = P.check_sat(M, edges, clauses, time_limit=180, verbose=True)
    orient = res["orientation"]
    min_viol = res.get("maxsat_min_violations", res.get("maxsat_n_violated"))
    print(f"[sat] status={res.get('maxsat_status','?')} min_viol={min_viol} "
          f"proven_opt={res.get('maxsat_proven_optimal')}", flush=True)

    # 判定违例子句: (t[a],t[b],t[c]) == bits 时为违例
    def bits_of(cl):
        return ((cl[3] >> 0) & 1, (cl[3] >> 1) & 1, (cl[3] >> 2) & 1)

    violated = []
    for cl in clauses:
        a, b, c = cl[0], cl[1], cl[2]
        if (orient[a], orient[b], orient[c]) == bits_of(cl):
            violated.append(cl)
    print(f"[viol] {len(violated)} violated clauses (expected {min_viol})", flush=True)

    # 缺陷核: 违例子句涉及的 cell (edge 索引)
    cluster = set()
    for cl in violated:
        cluster.update(cl[:3])
    cluster = sorted(cluster)
    print(f"[cluster] {len(cluster)} distinct cells in violation cluster: {cluster}", flush=True)

    # 每 cell 在"全部子句"中的频率 vs 在"违例子句"中的频率
    from collections import Counter
    all_freq = Counter()
    for cl in clauses:
        all_freq.update(cl[:3])
    viol_freq = Counter()
    for cl in violated:
        viol_freq.update(cl[:3])
    print("\n[cell]  idx  (u,v)     all_clause_freq  viol_freq")
    for idx in cluster:
        u, v = edges[idx]
        print(f"        {idx:2d}  ({u:2d},{v:2d})    {all_freq[idx]:4d}           {viol_freq[idx]:3d}")

    # 簇内 2-因子邻接结构(哪些簇顶点被同一条 2-因子边直接相连)
    adj = {i: [] for i in cluster}
    for idx in cluster:
        u, v = edges[idx]
        # 找与 idx 共享顶点的其他边
        for jdx in cluster:
            if jdx == idx:
                continue
            uu, vv = edges[jdx]
            if u in (uu, vv) or v in (uu, vv):
                adj[idx].append(jdx)
    # 簇的连通分量
    seen = set()
    comps = []
    for idx in cluster:
        if idx in seen:
            continue
        stack = [idx]; comp = []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x); comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    stack.append(y)
        comps.append(sorted(comp))
    print(f"\n[cluster-graph] {len(comps)} connected component(s): {comps}", flush=True)

    out = {
        "m": M,
        "best_clauses": data["best_clauses"],
        "best_violations": data["best_violations"],
        "n_clauses": n_clauses,
        "min_violations_sat": min_viol,
        "proven_optimal": res.get("maxsat_proven_optimal"),
        "cluster_size": len(cluster),
        "cluster_cells": [{"idx": i, "edge": list(edges[i]),
                           "all_freq": all_freq[i], "viol_freq": viol_freq[i]}
                          for i in cluster],
        "cluster_components": comps,
        "elapsed_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(HERE, "results", "defect_cluster_m37.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[done] wrote results/defect_cluster_m37.json in {out['elapsed_s']}s")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
radial_multi.py -- 同一 m 的多个解之间, 径向层(到中心距离环)有何特别?
数据: analysis/c4_2factors.json, key=棋盘边长 n, cells 数=n/2=我们的 m. 这批是 2-因子枚举.
两个分析:
  A. 已验证 rot4 真解(小 m, brute 通过)的径向层守恒性: 不同解是否共用同一套环?
  B. 全部 2-因子里满足「径向 ≤2/环」律的比例 -> 量化该律剪枝强度(是否真约束).
"""
import os, json
from collections import Counter

def c4(p, r, N):
    x, y = p
    return [(x, y), (N-1-y, x), (N-1-x, N-1-y), (y, N-1-x)][r]

def lift(cells, m):
    n = 2*m
    return [c4(c, r, n) for c in cells for r in range(4)]

def brute_collinear(cells, m):
    pts = lift(cells, m); P = len(pts)
    for i in range(P):
        x1,y1 = pts[i]
        for j in range(i+1,P):
            x2,y2 = pts[j]; dx,dy = x2-x1,y2-y1
            for k in range(j+1,P):
                if dx*(pts[k][1]-y1) == dy*(pts[k][0]-x1): return True
    return False

def ring_of(cell, m):
    x, y = cell
    return (m-2*x-1)**2 + (m-2*y-1)**2

def main():
    data = json.load(open("analysis/c4_2factors.json"))
    report = {}
    print("=== A. 已验证 rot4 真解: 径向层守恒性 ===")
    print(f"{'m':>3} {'ver':>4} {'common':>6} {'union':>5} {'cm/m':>5} {'conc':>5} {'ring_freq_dist(k->#rings)':>32}")
    A = {}
    for key in sorted(data.keys(), key=lambda x:int(x)):
        m = int(key)//2
        entries = [[tuple(c) for c in e] for e in data[key]]
        verified = [e for e in entries if not brute_collinear(e, m)]
        if not verified:
            continue
        n = len(verified)
        ring_freq = Counter()
        conc = 0
        for cells in verified:
            rc = Counter(ring_of(c, m) for c in cells)
            if max(rc.values()) <= 1: conc += 1
            for d in rc: ring_freq[d] += 1
        common = [d for d,c in ring_freq.items() if c == n]
        union = len(ring_freq)
        fd = dict(sorted(Counter(ring_freq.values()).items()))
        A[m] = {"n_verified": n, "common_rings": len(common), "union_rings": union,
                "common_frac": len(common)/m, "concentric": conc, "ring_freq_dist": fd}
        fds = " ".join(f"{k}:{v}" for k,v in sorted(fd.items()))
        print(f"{m:>3} {n:>4} {len(common):>6} {union:>5} {len(common)/m:>5.2f} {conc:>5}  {fds}")
    report["A_verified_conservation"] = A

    print("\n=== B. 全部 2-因子: 径向 ≤2/环 律的满足率(剪枝强度) ===")
    print(f"{'m':>3} {'n_2fac':>7} {'<=2/ring':>9} {'rate':>6} {'max/ring':>8}")
    B = {}
    for key in sorted(data.keys(), key=lambda x:int(x)):
        m = int(key)//2
        entries = [[tuple(c) for c in e] for e in data[key]]
        ok = 0; maxpr = 0
        for cells in entries:
            rc = Counter(ring_of(c, m) for c in cells)
            mx = max(rc.values())
            maxpr = max(maxpr, mx)
            if mx <= 2: ok += 1
        rate = ok/len(entries)
        B[m] = {"n_2factors": len(entries), "radial_ok": ok, "rate": rate, "max_per_ring": maxpr}
        print(f"{m:>3} {len(entries):>7} {ok:>9} {rate:>6.2f} {maxpr:>8}")
    report["B_radial_law_compliance"] = B

    print("\n=== C. 2-因子之间环集守恒性(跨解公共径向骨架?) ===")
    print(f"{'m':>3} {'n':>6} {'common(all)':>11} {'common(<=2)':>12} {'union':>5} {'rings_used_dist':>20}")
    C = {}
    for key in sorted(data.keys(), key=lambda x:int(x)):
        m = int(key)//2
        entries = [[tuple(c) for c in e] for e in data[key]]
        occ_all = []
        occ_ok = []
        ndist = Counter()
        for cells in entries:
            rc = Counter(ring_of(c, m) for c in cells)
            occ_all.append(set(rc.keys()))
            ndist[len(rc)] += 1
            if max(rc.values()) <= 2:
                occ_ok.append(set(rc.keys()))
        common_all = set.intersection(*occ_all) if occ_all else set()
        common_ok = set.intersection(*occ_ok) if occ_ok else set()
        union = len(set.union(*occ_all)) if occ_all else 0
        nd = dict(sorted(ndist.items()))
        nds = " ".join(f"{k}c:{v}" for k,v in nd.items())
        C[m] = {"n": len(entries), "common_all": len(common_all),
                "common_radial_ok": len(common_ok), "union": union, "rings_used_dist": nd}
        print(f"{m:>3} {len(entries):>6} {len(common_all):>11} {len(common_ok):>12} {union:>5}  {nds}")
    report["C_ring_set_conservation"] = C

    os.makedirs("results", exist_ok=True)
    with open("results/radial_multi.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n写入 results/radial_multi.json")

if __name__ == "__main__":
    main()

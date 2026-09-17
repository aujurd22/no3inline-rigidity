"""
test_families_m37.py -- 素数 m 的构造族存在性探针 (rot4-NTIL).

思路: m=37 是素数. 用显式置换族 pi 生成基本 cell 集 {(i, pi(i))},
复用 verify_cells (C4 提升+暴力 3-共线真值) 秒级校验. 若某族对 m=37 命中
=> 显式构造性存在证明 (坐标可独立验证).

同时在校准素数 [5,7,11,13,17,19,23,29,31] 上跑同族, 看是否有 ANY 素数被某族
命中 (若有, 研究哪种族; 若全不中, 印证 R9c 引理6 "线性/幂族太共线").

族 (m 为素数 p):
  pow_k   : pi[i] = i^k mod p,  gcd(k,p-1)=1, k>1   (非零元 k 次幂置换)
  dlog_g  : pi[i] = log_g(i) mod (p-1) (i>0), pi[0]=0  (离散对数, g 原根)

用法:
  python test_families_m37.py
"""
import os, sys, math, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solve_m37_r9b import verify_cells
from math import gcd

PRIMES = [5, 7, 11, 13, 17, 19, 23, 29, 31, 37]


def fam_pow(p, k):
    return [pow(i, k, p) for i in range(p)]


def fam_dlog(p, g):
    # g 原根 mod p; 求离散对数 ind_g(i) (i=1..p-1 -> 0..p-2)
    ind = [-1] * p
    cur = 1
    for e in range(p - 1):
        ind[cur] = e
        cur = (cur * g) % p
    # pi[0] 用未占用的 p-1; pi[i]=ind[i] (0..p-2) for i>=1 -> 完整置换
    pi = [p - 1] + [ind[i] for i in range(1, p)]
    return pi


def is_perm(pi):
    return sorted(pi) == list(range(len(pi)))


def check(p, name, pi):
    if not is_perm(pi):
        return f"{name}: NOT perm (skip)"
    cells = [(i, pi[i]) for i in range(p)]
    ok, npts = verify_cells(cells, p)
    if ok:
        return f"{name}: *** VALID rot4 NTIL for m={p} *** npts={npts}"
    return f"{name}: bad (npts={npts})"


def is_primitive_root(g, p):
    if pow(g, p - 1, p) != 1:
        return False
    # prime factors of p-1
    n = p - 1
    qs = set()
    d = 2
    while d * d <= n:
        if n % d == 0:
            qs.add(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        qs.add(n)
    return all(pow(g, (p - 1) // q, p) != 1 for q in qs)


def main():
    log = []
    print("=== prime construction-family probe (rot4 NTIL) ===", flush=True)
    for p in PRIMES:
        print(f"--- m={p} ---", flush=True)
        any_valid = False
        # power maps k with gcd(k,p-1)=1, k>1
        ks = [k for k in range(2, p) if gcd(k, p - 1) == 1]
        for k in ks:
            msg = check(p, f"pow_k(k={k})", fam_pow(p, k))
            print("  " + msg, flush=True)
            log.append((p, f"pow_k({k})", "VALID" if "VALID" in msg else "bad"))
            if "VALID" in msg:
                any_valid = True
        # discrete log with smallest primitive root
        g = next((cand for cand in range(2, p) if is_primitive_root(cand, p)), None)
        if g is not None:
            msg = check(p, f"dlog_g(g={g})", fam_dlog(p, g))
            print("  " + msg, flush=True)
            log.append((p, f"dlog_g({g})", "VALID" if "VALID" in msg else "bad"))
            if "VALID" in msg:
                any_valid = True
        if not any_valid:
            print(f"  [summary] m={p}: no simple family hit", flush=True)
    with open(os.path.join(HERE, "results", "family_probe.json"), "w") as f:
        json.dump(log, f, indent=2)
    print("[done] wrote results/family_probe.json", flush=True)


if __name__ == "__main__":
    main()

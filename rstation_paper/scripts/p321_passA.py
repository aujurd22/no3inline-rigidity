# -*- coding: utf-8 -*-
"""P321 pass-A: full-DB streaming audit of rot2+rct4 solutions.
Per solution: NTIL verify (2/row/col, antipode-closed, no-3-collinear via line
grouping), T'-F2 census (unimodular mixed triangles, vectorized), confined
check (rep-half row parity). Aggregates only -- RAM-safe streaming.
運行解释器: C:/Users/djr82/AppData/Local/Programs/Python/Python313/python.exe
"""
import sys, os, json, time
from math import gcd
from collections import defaultdict, Counter
import numpy as np

DB = sys.argv[1] if len(sys.argv) > 1 else "all_known_solutions.txt"
ALPHABET = ("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.")
SYM = {'.': 'iden', 'o': 'rot4', ':': 'rot2', 'c': 'rct4'}

def verify_and_f2(sym, n, pts):
    """Returns (verified, f2_count, confined, notes)."""
    S = set(pts)
    ok = len(S) == len(pts) == 2 * n
    rc = Counter(y for _, y in pts); cc = Counter(x for x, _ in pts)
    ok = ok and all(v == 2 for v in rc.values()) and len(rc) == n
    ok = ok and all(v == 2 for v in cc.values()) and len(cc) == n
    # antipode-closed
    ok = ok and all((n - 1 - x, n - 1 - y) in S for x, y in pts)
    # no-3-collinear via line grouping on all pairs
    viol = 0
    line_pts = defaultdict(set)
    Pl = sorted(pts)
    for i, p in enumerate(Pl):
        for q in Pl[i+1:]:
            dx, dy = q[0]-p[0], q[1]-p[1]
            g = gcd(abs(dx), abs(dy)); dx, dy = dx//g, dy//g
            if dx < 0 or (dx == 0 and dy < 0): dx, dy = -dx, -dy
            line_pts[(dx, dy, dx*p[1]-dy*p[0])].add(p); line_pts[(dx, dy, dx*p[1]-dy*p[0])].add(q)
    for ps in line_pts.values():
        if len(ps) >= 3: viol += 1
    ok = ok and viol == 0
    # reps (left half) -- same convention as t42e (x < n/2)
    reps = sorted(p for p in pts if p[0] < n / 2)
    L = np.array(reps, dtype=np.int64)
    R = np.array([(n-1-x, n-1-y) for x, y in reps], dtype=np.int64)
    # F2: exists |det(L[j]-L[i], R[k]-L[i])| == 1 over distinct i,j,k
    # tensor: D[i,j,k] = (L[j,0]-L[i,0])*(R[k,1]-L[i,1]) - (L[j,1]-L[i,1])*(R[k,0]-L[i,0])
    nl = len(L)
    d0 = L[None, :, 0] - L[:, None, 0]  # d[i,j] = Lj - Li  (x)
    d1 = L[None, :, 1] - L[:, None, 1]
    r0 = R[None, :, 0] - L[:, None, 0]  # r[i,k] = Rk - Li
    r1 = R[None, :, 1] - L[:, None, 1]
    # D[i,j,k] = d0[i,j]*r1[i,k] - d1[i,j]*r0[i,k]
    D = d0[:, :, None] * r1[:, None, :] - d1[:, :, None] * r0[:, None, :]
    # exclude i==j (zero det anyway) and k == i or k == j (r must differ from p,q -- but
    # R[k] could coincide with L[i]/L[j] only for center-column odd-n cases; the
    # degenerate det=0 case is excluded by |=1| anyway)
    f2_count = int(np.sum(np.abs(D) == 1)) // 2  # ordered (i,j) counted twice
    confined = False
    par = set(y % 2 for _, y in [(p[0], p[1]) for p in reps])
    if len(par) == 1: confined = True
    return ok, f2_count, confined, viol

def main():
    t0 = time.time()
    agg = defaultdict(lambda: {"n_sols": 0, "verified_bad": 0, "f2_free": 0,
                               "confined": 0, "collinear_viol": 0,
                               "f2_min": 10**9, "f2_max": 0, "f2_sum": 0})
    per_n = defaultdict(lambda: {"sols": 0, "f2_free": 0, "confined": 0})
    exceptions = []
    for line in open(DB, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line: continue
        sym = line[0]
        if sym not in SYM: continue
        cls = SYM[sym]
        if cls not in ("rot2", "rct4"): continue
        rest = line[1:]
        n = len(rest) // 2
        CTV = {c: i for i, c in enumerate(
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.")}
        pts = []
        for r in range(n):
            pts.append((r, CTV[rest[2*r]]))
            pts.append((r, CTV[rest[2*r+1]]))
        a = agg[cls]
        pn = per_n[(cls, n)]
        a["n_sols"] += 1; pn["sols"] += 1
        try:
            ok, f2c, confined, viol = verify_and_f2(cls, n, pts)
        except Exception as e:
            exceptions.append((cls, n, str(e))); continue
        if not ok: a["verified_bad"] += 1
        if viol: a["collinear_viol"] += 1
        if f2c == 0:
            a["f2_free"] += 1; pn["f2_free"] += 1
            exceptions.append(("F2-FREE", cls, n, pts))
        if confined:
            a["confined"] += 1; pn["confined"] += 1
        a["f2_min"] = min(a["f2_min"], f2c); a["f2_max"] = max(a["f2_max"], f2c)
        a["f2_sum"] += f2c
        if time.time() - t0 > 3300:
            print("TIME CAP 55min", flush=True); break
    print(f"elapsed {time.time()-t0:.0f}s")
    for cls, a in agg.items():
        if a["n_sols"]:
            print(f"{cls}: {a['n_sols']} sols | verify_bad={a['verified_bad']} collinear_viol={a['collinear_viol']} "
                  f"| F2-free={a['f2_free']} confined={a['confined']} | F2 min/mean/max = "
                  f"{a['f2_min'] if a['f2_min']<10**9 else '-'}/{a['f2_sum']/max(1,a['n_sols']):.1f}/{a['f2_max']}")
    print("exceptions:", exceptions[:5] if exceptions else "NONE")
    json.dump({k: dict(v) for k, v in agg.items()}, open("p321_passA_agg.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()

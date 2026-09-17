"""
test_construction.py -- 构造性攻击 m=37 (prime!).

核心观察: m=37 是素数 => 任何 k in 1..36 给出的乘法置换
    pi(i) = k * i  mod 37
都是 {0..36} 上的单个 37-圈 (因为 37 是素数, k != 0 => 轨道长度=37).

单圈 2-因子 = cell 集合 {(i, pi(i)) : i=0..36}, 自动满足 rowSum+colSum=2
(每个 i 恰好一次作 row, 一次作 col).  所以这是一个合法的 2-因子候选.

若某个 k 使得 C4 提升后的 4m=148 点无三点共线, 则直接给出 m=37 的
rot4-NTIL 显式构造 => 构造性存在证明 (解决该开放问题).

本脚本:
  (1) 方法校验: 在小素数 m=5,7,11 上, 看乘法/Wech 家族能否复现已知解;
  (2) 主攻: m=37, 试 k=1..36 乘法族, 以及 Welch 族 pi(i)=g^i, 逆族 pi(i)=k*i^{-1}.

无三点共线检测用 O(N^2) 斜率哈希 (N=4m=148 点).
"""
import sys, math, json, time

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def lifted(cells, m):
    n = 2 * m
    pts = []
    seen = set()
    for (x, y) in cells:
        for r in range(4):
            p = c4((x, y), r, n)
            if p not in seen:
                seen.add(p)
                pts.append(p)
    return pts

def has_collinear(pts):
    """O(N^2) slope-hash 三点共线检测. 返回 (False, None) 或 (True, triple)."""
    N = len(pts)
    for i in range(N):
        x1, y1 = pts[i]
        slopes = {}
        for j in range(i + 1, N):
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            g = math.gcd(dx, dy) or 1
            dx //= g; dy //= g
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            if (dx, dy) in slopes:
                return True, (pts[i], pts[slopes[(dx, dy)]], pts[j])
            slopes[(dx, dy)] = j
    return False, None

def inv_mod(a, p):
    # p prime, a != 0
    return pow(a, p - 2, p)

def try_family(m, name, pifn):
    cells = [(i, pifn(i)) for i in range(m)]
    # distinct cells?
    if len(set(cells)) != m:
        return None
    pts = lifted(cells, m)
    bad, triple = has_collinear(pts)
    return (not bad, len(pts), triple)

def primitive_roots(p):
    # find generators of F_p^*
    phi = p - 1
    # factorize phi
    n = phi
    fac = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            fac[d] = fac.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        fac[n] = fac.get(n, 0) + 1
    roots = []
    for g in range(2, p):
        ok = True
        for q in fac:
            if pow(g, phi // q, p) == 1:
                ok = False
                break
        if ok:
            roots.append(g)
    return roots

def main():
    results = {}
    # ---- (1) 方法校验: 小素数 ----
    print("=" * 70)
    print("(1) SANITY on small primes -- does multiplier/Welch family hit a solution?")
    print("=" * 70)
    for m in [5, 7, 11]:
        print(f"--- m={m} ---")
        best = None
        for k in range(1, m):
            ok, np, _ = try_family(m, "mult", lambda i, k=k: (k * i) % m)
            if ok:
                print(f"   MULT k={k}: SOLUTION (pts={np})")
                best = ("mult", k)
                break
        if best is None:
            # Welch
            for g in primitive_roots(m):
                ok, np, _ = try_family(m, "welch", lambda i, g=g: pow(g, i, m))
                if ok:
                    print(f"   WELCH g={g}: SOLUTION (pts={np})")
                    best = ("welch", g)
                    break
        if best is None:
            print(f"   (no solution in mult/Welch families for m={m})")
        results[f"m{m}_sanity"] = best

    # ---- (2) 主攻 m=37 ----
    print("=" * 70)
    print("(2) ATTACK m=37 (prime) -- multiplier / inverse / Welch families")
    print("=" * 70)
    m = 37
    found = []
    t0 = time.time()
    # multiplier family k=1..36
    for k in range(1, m):
        ok, np, trip = try_family(m, "mult", lambda i, k=k: (k * i) % m)
        if ok:
            print(f"   [MULT] k={k}: *** SOLUTION FOUND *** (pts={np})")
            found.append(("mult", k))
    print(f"   mult family done in {time.time()-t0:.1f}s, found={len(found)}")
    # inverse family pi(i)=k*i^{-1} mod 37 (0->0)
    t0 = time.time()
    for k in range(1, m):
        def pinv(i, k=k):
            return 0 if i == 0 else (k * inv_mod(i, m)) % m
        ok, np, trip = try_family(m, "inv", pinv)
        if ok:
            print(f"   [INV] k={k}: *** SOLUTION FOUND *** (pts={np})")
            found.append(("inv", k))
    print(f"   inv family done in {time.time()-t0:.1f}s, found={len(found)}")
    # Welch family pi(i)=g^i mod 37
    t0 = time.time()
    for g in primitive_roots(m):
        ok, np, trip = try_family(m, "welch", lambda i, g=g: pow(g, i, m))
        if ok:
            print(f"   [WELCH] g={g}: *** SOLUTION FOUND *** (pts={np})")
            found.append(("welch", g))
    print(f"   welch family done in {time.time()-t0:.1f}s, found={len(found)}")

    results["m37_found"] = found
    print("=" * 70)
    if found:
        print(f"RESULT: m=37 SOLVED constructively via {found}")
    else:
        print("RESULT: none of mult/inv/Welch families worked for m=37")
        print("  -> need richer family (e.g. full single-cycle permutation search via CP-SAT)")
    print("=" * 70)
    with open("results/construction_m37.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()

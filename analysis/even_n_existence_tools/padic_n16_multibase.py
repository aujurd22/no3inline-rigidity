"""n=16: 多基排列 SA + floor 分析"""
import itertools, json, time, random, math
from collections import Counter

def bitrev(n, k): return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]
def gray(n): return [x ^ (x >> 1) for x in range(n)]

def build_tps(perm, n, k):
    tps = set()
    for x in range(n):
        for b in range(k):
            y = x ^ (1 << b)
            if y > x: a, bb = perm[x], perm[y]; tps.add((min(a, bb), max(a, bb)))
    return sorted(tps)

def count_colls(p0, p1, n):
    cnt = 0
    for i, j, k in itertools.combinations(range(n), 3):
        a0i, a0j, a0k = p0[i], p0[j], p0[k]
        a1i, a1j, a1k = p1[i], p1[j], p1[k]
        dxj, dxk = j - i, k - i
        if dxj * (a0k - a0i) == dxk * (a0j - a0i): cnt += 1
        if dxj * (a1k - a0i) == dxk * (a0j - a0i): cnt += 1
        if dxj * (a0k - a0i) == dxk * (a1j - a0i): cnt += 1
        if dxj * (a1k - a0i) == dxk * (a1j - a0i): cnt += 1
        if dxj * (a0k - a1i) == dxk * (a0j - a1i): cnt += 1
        if dxj * (a1k - a1i) == dxk * (a0j - a1i): cnt += 1
        if dxj * (a0k - a1i) == dxk * (a1j - a1i): cnt += 1
        if dxj * (a1k - a1i) == dxk * (a1j - a1i): cnt += 1
    return cnt

def sa_basic(p0, p1, all_tps, n, n_iter=3000):
    cnt = count_colls(p0, p1, n)
    bp0, bp1 = p0[:], p1[:]; bc = cnt
    T = 3.0; alpha = (0.01 / T) ** (1.0 / n_iter)
    for it in range(n_iter):
        if cnt == 0: break
        tp_type, a, b = random.choice(all_tps)
        if tp_type == 'p0':
            p0t = p0[:]; p0t[a], p0t[b] = p0t[b], p0t[a]
            nc = count_colls(p0t, p1, n)
        else:
            p1t = p1[:]; p1t[a], p1t[b] = p1t[b], p1t[a]
            nc = count_colls(p0, p1t, n)
        delta = nc - cnt
        if delta <= 0 or random.random() < math.exp(-delta / T):
            if tp_type == 'p0': p0[a], p0[b] = p0[b], p0[a]
            else: p1[a], p1[b] = p1[b], p1[a]
            cnt = nc
            if cnt < bc: bp0, bp1 = p0[:], p1[:]; bc = cnt
        T *= alpha
    return bp0, bp1, bc

random.seed(42)
n = 16; k = 4

print("="*64)
print("n=16: 多基排列对 + 不同种子 SA 测试")
print("="*64)

# ===== 1. 不同基对 =====
results = []
for seed_offset in range(5):
    random.seed(42 + seed_offset)
    
    for name, p0b, p1b in [
        ("bitrev+cmpl", bitrev(n,k), [n-1-x for x in bitrev(n,k)]),
        ("bitrev+gray", bitrev(n,k), gray(n)),
    ]:
        degen = sum(1 for i in range(n) if p0b[i] == p1b[i])
        if degen > 0:
            print(f"  seed{seed_offset} {name}: SKIP ({degen}degen)")
            continue
        
        base = count_colls(p0b, p1b, n)
        tp0 = build_tps(p0b, n, k); tp1 = build_tps(p1b, n, k)
        at = [('p0',a,b) for a,b in tp0] + [('p1',a,b) for a,b in tp1]
        
        t0 = time.time()
        pf0, pf1, fc = sa_basic(p0b, p1b, at, n, n_iter=5000)
        elapsed = time.time() - t0
        
        pts = [(i, pf0[i]) for i in range(n)] + [(i, pf1[i]) for i in range(n)]
        unique = len(set(pts))
        bad = sum(1 for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3)
                  if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1))
        ok = bad == 0 and unique == 2*n
        st = "★ NTIL" if ok else f"✗ {fc}c/{bad}g"
        print(f"  {name} seed{seed_offset}: base={base} final={fc}c/{bad}g u={unique} {st} ({elapsed:.1f}s)")
        
        if ok:
            json.dump({'n':n,'p0':pf0,'p1':pf1,'base':name},
                     open(f'ntil_n16_{name}.json','w'), indent=2)
            break
        results.append((name, seed_offset, fc, bad, pf0, pf1))
    else:
        continue
    break  # if found, stop

# ===== 2. 最低 floor 的残存共线分析 =====
if results:
    best = min(results, key=lambda x: x[2])  # min fc
    name, seed, fc, bad, p0f, p1f = best
    print(f"\n{'='*64}")
    print(f"最佳: {name} seed{seed}: {fc}c/{bad}g")
    print(f"残存共线结构分析:")
    
    # Extract collisions
    cols = []
    for i, j, k in itertools.combinations(range(n), 3):
        for mask in range(8):
            yi = p0f[i] if (mask&1) else p1f[i]
            yj = p0f[j] if (mask&2) else p1f[j]
            yk = p0f[k] if (mask&4) else p1f[k]
            if (j-i)*(yk-yi) == (k-i)*(yj-yi):
                cols.append((i,j,k,mask))

    # Check: does each transposition affect any of these residuals?
    tp0 = build_tps(p0f, n, k); tp1 = build_tps(p1f, n, k)
    at = [('p0',a,b) for a,b in tp0] + [('p1',a,b) for a,b in tp1]
    
    affected_by_tp = Counter()
    for tp_type, a, b in at:
        p0t, p1t = p0f[:], p1f[:]
        if tp_type == 'p0': p0t[a], p0t[b] = p0t[b], p0t[a]
        else: p1t[a], p1t[b] = p1t[b], p1t[a]
        # Count which residuals remain
        for i,j,k,mask in cols:
            yi = p0t[i] if (mask&1) else p1t[i]
            yj = p0t[j] if (mask&2) else p1t[j]
            yk = p0t[k] if (mask&4) else p1t[k]
            if (j-i)*(yk-yi) != (k-i)*(yj-yi):
                affected_by_tp[(i,j,k,mask)] += 1
    
    print(f"  残存共线: {len(cols)}")
    print(f"  可被≥1 transposition修复: {sum(1 for c in cols if affected_by_tp[c]>0)}")
    print(f"  平均修复transposition数: {sum(affected_by_tp.values())/len(cols):.1f}")
    
    # Slope analysis
    slope = Counter()
    for i,j,k,mask in cols:
        yi = p0f[i] if (mask&1) else p1f[i]
        yj = p0f[j] if (mask&2) else p1f[j]
        dx = j-i; dy = yj-yi
        g = math.gcd(abs(dx),abs(dy)) if (dx or dy) else 1
        slope[(dx//g, dy//g)] += 1
    print(f"  斜率分布: {slope.most_common(5)}")

print("\n完成。")

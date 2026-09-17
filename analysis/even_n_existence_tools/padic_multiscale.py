"""
p-adic 多尺度 (per-bit) transposition 搜索。
对每个 bit b 独立优化其 transposition 子集，从 MSB 到 LSB。
原理：bit b 的 transposition 仅影响该位相关的共线。
"""
import itertools, time, json, random, math

def bitrev(n, k): return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]
def gray(n): return [x ^ (x >> 1) for x in range(n)]

def count_collisions(p0, p1, n):
    pts = [(i, p0[i]) for i in range(n)] + [(i, p1[i]) for i in range(n)]
    cols = 0
    for i1,i2,i3 in itertools.combinations(range(2*n), 3):
        x1,y1=pts[i1]; x2,y2=pts[i2]; x3,y3=pts[i3]
        if (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1): cols+=1
    return cols

def build_bit_transpositions(p, n, k, bit):
    """仅为位 b 构建 transposition。"""
    inv = [0]*n
    for i in range(n): inv[p[i]] = i
    mask = 1 << bit
    tps = set()
    for y in range(n):
        if (y & mask) == 0:
            a, bv = inv[y], inv[y ^ mask]
            tps.add((min(a,bv), max(a,bv)))
    return sorted(tps)

def sa_single_bit(p0, p1, tps0, tps1, n, max_iter=2000, n_restarts=5):
    """SA 优化单个 bit 的 transposition 子集。"""
    all_tps = [('p0',a,b) for a,b in tps0] + [('p1',a,b) for a,b in tps1]
    
    best_overall = float('inf')
    best_p0, best_p1 = p0[:], p1[:]
    
    for restart in range(n_restarts):
        cp0, cp1 = p0[:], p1[:]
        for _ in range(random.randint(0, min(5, len(all_tps)))):
            tp,a,b = random.choice(all_tps)
            if tp=='p0': cp0[a],cp0[b]=cp0[b],cp0[a]
            else: cp1[a],cp1[b]=cp1[b],cp1[a]
        
        cnt = count_collisions(cp0, cp1, n)
        bp0, bp1, bc = cp0[:], cp1[:], cnt
        T = 2.0
        
        for it in range(max_iter):
            if cnt == 0: break
            tp,a,b = random.choice(all_tps)
            if tp=='p0': cp0[a],cp0[b]=cp0[b],cp0[a]
            else: cp1[a],cp1[b]=cp1[b],cp1[a]
            nc = count_collisions(cp0, cp1, n)
            d = nc - cnt
            if d <= 0 or random.random() < math.exp(-d/max(T,0.01)):
                cnt = nc
                if cnt < bc: bp0,bp1,bc = cp0[:],cp1[:],cnt
            else:
                if tp=='p0': cp0[a],cp0[b]=cp0[b],cp0[a]
                else: cp1[a],cp1[b]=cp1[b],cp1[a]
            T *= 0.995
        
        cp0[:],cp1[:],cnt = bp0[:],bp1[:],bc
        if bc < best_overall:
            best_overall = bc
            best_p0, best_p1 = cp0[:], cp1[:]
    
    return best_p0, best_p1, best_overall

def multiscale_optimize(p0_base, p1_base, n, k):
    """多尺度优化：从 MSB 到 LSB 逐位优化。"""
    p0, p1 = p0_base[:], p1_base[:]
    
    for bit in reversed(range(k)):  # MSB first
        tps0 = build_bit_transpositions(p0, n, k, bit)
        tps1 = build_bit_transpositions(p1, n, k, bit)
        
        before = count_collisions(p0, p1, n)
        p0, p1, after = sa_single_bit(p0, p1, tps0, tps1, n, max_iter=2000, n_restarts=5)
        print(f"    bit {bit}: {before} → {after} ({len(tps0)+len(tps1)} tps)")
        
        if after == 0:
            return p0, p1, 0
    
    final = count_collisions(p0, p1, n)
    return p0, p1, final

# 测试
print("="*60)
print("p-adic 多尺度 (per-bit) transposition 搜索")
print("="*60)

for n, k in [(8, 3), (16, 4)]:
    print(f"\n--- n={n} (k={k}) ---")
    p0b = bitrev(n, k)
    p1b = gray(n)
    
    base = count_collisions(p0b, p1b, n)
    print(f"  base collisions: {base}")
    
    t0 = time.time()
    mp0, mp1, mc = multiscale_optimize(p0b, p1b, n, k)
    elapsed = time.time() - t0
    
    # 验证
    vc = count_collisions(mp0, mp1, n)
    status = "✓ NTIL" if vc == 0 else f"✗ {vc} residual"
    print(f"  result: {status} ({elapsed:.1f}s)")
    
    if vc == 0:
        print(f"  p0[:8] = {mp0[:8]}")
        print(f"  p1[:8] = {mp1[:8]}")
        # Save solution
        json.dump({'n':n, 'p0':mp0, 'p1':mp1}, 
                  open(f'padic_multiscale_n{n}.json', 'w'))

# n=32 quick test
print(f"\n--- n=32 (k=5) quick test ---")
n32, k5 = 32, 5
p0_32, p1_32 = bitrev(n32, k5), gray(n32)
base32 = count_collisions(p0_32, p1_32, n32)
print(f"  base collisions: {base32}")
print(f"  估算: n=8 base=40, n=16 base=~196, n=32 base={base32}")
print(f"  增长模式: 40→196→{base32} = {196/40:.1f}x → {base32/196:.1f}x")

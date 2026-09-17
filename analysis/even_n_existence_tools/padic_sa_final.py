"""
p-adic transposition SA — FINAL rigorous version.
Key fixes:
1. REJECT any transposition creating p0[i]==p1[i] (degenerate row)
2. verify_grid uses SET of points (no duplicate counting)
3. count_colls and verify_grid use IDENTICAL determinant formula
"""
import itertools, json, math, random, time

def bitrev(n,k): return [int(format(x,f'0{k}b')[::-1],2) for x in range(n)]
def gray(n): return [x^(x>>1) for x in range(n)]

def build_tps(perm, n, k):
    tps=set()
    for x in range(n):
        for b in range(k):
            y=x^(1<<b)
            if y>x: a,bb=perm[x],perm[y]; tps.add((min(a,bb),max(a,bb)))
    return sorted(tps)

# ============================================================
# Collision counting — 8 types, 3 distinct rows, unified convention
# bit convention: bit0->i, bit1->j, bit2->k  (0=p0, 1=p1)
# ============================================================

def count_collisions(p0, p1, n):
    cnt = 0
    for i,j,k in itertools.combinations(range(n),3):
        a0i,a0j,a0k = p0[i],p0[j],p0[k]
        a1i,a1j,a1k = p1[i],p1[j],p1[k]
        dxj,dxk = j-i, k-i
        if dxj*(a0k-a0i)==dxk*(a0j-a0i): cnt+=1
        if dxj*(a1k-a0i)==dxk*(a0j-a0i): cnt+=1
        if dxj*(a0k-a0i)==dxk*(a1j-a0i): cnt+=1
        if dxj*(a1k-a0i)==dxk*(a1j-a0i): cnt+=1
        if dxj*(a0k-a1i)==dxk*(a0j-a1i): cnt+=1
        if dxj*(a1k-a1i)==dxk*(a0j-a1i): cnt+=1
        if dxj*(a0k-a1i)==dxk*(a1j-a1i): cnt+=1
        if dxj*(a1k-a1i)==dxk*(a1j-a1i): cnt+=1
    return cnt

def verify_grid(p0, p1, n):
    """NTIL verifier: check all distinct triples of 2n grid points."""
    pts = list(set([(x, p0[x]) for x in range(n)] + 
                   [(x, p1[x]) for x in range(n)]))
    if len(pts) < 2*n:
        return False, len(pts)  # degenerate: duplicate points
    for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            return False, 0
    return True, 2*n

# ============================================================
# SA with degeneracy rejection
# ============================================================

def has_degenerate_row(p0, p1, n):
    """Check if any row i has p0[i]==p1[i]"""
    return any(p0[i]==p1[i] for i in range(n))

def sa_final(p0, p1, all_tps, n, n_iter=5000, n_restarts=8):
    cnt = count_collisions(p0, p1, n)
    best_p0, best_p1 = p0[:], p1[:]
    best_cnt = cnt
    
    for rst in range(n_restarts):
        T = 5.0
        alpha = (0.01 / T) ** (1.0 / n_iter)
        
        for it in range(n_iter):
            if cnt == 0:
                break
            
            tp_type, a, b = random.choice(all_tps)
            
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
                if has_degenerate_row(p0, p1, n):
                    p0[a], p0[b] = p0[b], p0[a]  # reject
                    continue
                new_cnt = count_collisions(p0, p1, n)
            else:
                p1[a], p1[b] = p1[b], p1[a]
                if has_degenerate_row(p0, p1, n):
                    p1[a], p1[b] = p1[b], p1[a]  # reject
                    continue
                new_cnt = count_collisions(p0, p1, n)
            
            delta = new_cnt - cnt
            if delta <= 0 or random.random() < math.exp(-delta / T):
                cnt = new_cnt
                if cnt < best_cnt:
                    best_p0 = p0[:]; best_p1 = p1[:]; best_cnt = cnt
            else:
                if tp_type == 'p0':
                    p0[a], p0[b] = p0[b], p0[a]
                else:
                    p1[a], p1[b] = p1[b], p1[a]
            
            # If we rejected (degenerate), p0/p1 already restored
            T *= alpha
        
        if cnt > 0:
            p0[:] = best_p0[:]; p1[:] = best_p1[:]; cnt = best_cnt
        print(f"    r{rst}: cnt={cnt} best={best_cnt}")
    
    return best_p0, best_p1, best_cnt

# ============================================================
# Main
# ============================================================

random.seed(42)
results = []

for n in [8, 16, 32]:
    k = n.bit_length() - 1
    p0o = bitrev(n, k)
    p1o = [(n - 1 - v) % n for v in p0o]  # complement: guaranteed p0[i]≠p1[i]
    
    assert len(set(p0o)) == n and len(set(p1o)) == n
    base_degen = sum(1 for i in range(n) if p0o[i]==p1o[i])
    if base_degen > 0:
        print(f"  (base has {base_degen} degenerate rows — included in SA cost)")
    
    base = count_collisions(p0o, p1o, n)
    tp0 = build_tps(p0o, n, k)
    tp1 = build_tps(p1o, n, k)
    all_tps = [('p0',a,b) for a,b in tp0] + [('p1',a,b) for a,b in tp1]
    
    n_iter = 3000 if n <= 16 else 1000
    n_rst = 8 if n <= 16 else 4
    
    print(f"\nn={n} k={k} base={base} tps={len(all_tps)}")
    t0 = time.time()
    p0f, p1f, fc = sa_final(p0o, p1o, all_tps, n, n_iter, n_rst)
    elapsed = time.time() - t0
    
    # Validation
    c1 = count_collisions(p0f, p1f, n)
    degenerate = has_degenerate_row(p0f, p1f, n)
    ntil_ok, n_unique = verify_grid(p0f, p1f, n)
    
    consistent = (c1 == 0) == ntil_ok
    print(f"  final: base={base}→{fc} c1={c1} degen={degenerate} "
          f"ntil={ntil_ok} unique_pts={n_unique} consistent={consistent}")
    print(f"  time: {elapsed:.1f}s")
    
    results.append({
        'n': n, 'base': base, 'final': fc, 'c1': c1,
        'ntil': ntil_ok, 'degen': degenerate, 'consistent': consistent,
        'unique_pts': n_unique, 'time': elapsed,
    })
    
    if ntil_ok:
        json.dump({'n':n,'p0':p0f,'p1':p1f,'time':elapsed},
                  open(f'ntil_n{n}_sa.json','w'), indent=2)
        print(f"  ★★★ NTIL solution saved!")

print(f"\n{'='*60}")
print("FINAL SUMMARY")
print('='*60)
for r in results:
    status = "★ NTIL" if r['ntil'] else f"✗ {r['final']}c"
    print(f"  n={r['n']}: {status} base={r['base']}→{r['final']} "
          f"degen={r['degen']} uniq={r['unique_pts']} consistent={r['consistent']} "
          f"{r['time']:.1f}s")

json.dump(results, open('padic_sa_final_results.json','w'), indent=2)

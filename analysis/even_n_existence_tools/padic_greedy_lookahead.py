"""
贪心+2-步前瞻逃逸：主循环用贪心，卡住时暴力穷举 transposition 对。
已验证：48-52% 次模性不成立 → 成对效应关键。
"""
import itertools, time, json

def bitrev(n,k): return [int(format(x,f'0{k}b')[::-1],2) for x in range(n)]
def gray(n): return [x^(x>>1) for x in range(n)]

def build_tps(perm, n, k):
    tps = set()
    for x in range(n):
        for b in range(k):
            y = x ^ (1 << b)
            if y > x:
                a,bb = perm[x], perm[y]
                tps.add((min(a,bb), max(a,bb)))
    return [(a,b) for a,b in tps]

def count_colls(p0, p1, n):
    cnt=0
    for i in range(n):
        p0i,p1i=p0[i],p1[i]
        for j in range(i+1,n):
            dxj=j-i; p0j,p1j=p0[j],p1[j]
            for k in range(j+1,n):
                dxk=k-i; p0k,p1k=p0[k],p1[k]
                if dxj*(p0k-p0i)==dxk*(p0j-p0i): cnt+=1
                if dxj*(p0k-p1i)==dxk*(p0j-p1i): cnt+=1
                if dxj*(p1k-p0i)==dxk*(p1j-p0i): cnt+=1
                if dxj*(p1k-p1i)==dxk*(p1j-p1i): cnt+=1
                if dxj*(p0k-p0i)==dxk*(p1j-p0i): cnt+=1
                if dxj*(p0k-p1i)==dxk*(p1j-p1i): cnt+=1
                if dxj*(p1k-p0i)==dxk*(p0j-p0i): cnt+=1
                if dxj*(p1k-p1i)==dxk*(p0j-p1i): cnt+=1
    return cnt

def verify_ntil(p0, p1, n):
    pts=[(i,p0[i]) for i in range(n)]+[(i,p1[i]) for i in range(n)]
    bad=sum(1 for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3)
             if (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1))
    return bad==0, bad

def greedy_with_lookahead(p0, p1, tps0, tps1, n, max_iter=500):
    """贪心 + 卡住时 2-步前瞻"""
    all_single = [('p0',a,b) for a,b in tps0] + [('p1',a,b) for a,b in tps1]
    m = len(all_single)
    
    cnt = count_colls(p0, p1, n)
    p0_best, p1_best = p0[:], p1[:]
    cnt_best = cnt
    
    stuck_count = 0
    
    for it in range(max_iter):
        if cnt == 0: break
        
        # Step 1: try single transposition
        best_d, best_tp = 0, None
        for tp in all_single:
            tp_type,a,b = tp
            p0c,p1c = p0[:],p1[:]
            if tp_type=='p0': p0c[a],p0c[b]=p0c[b],p0c[a]
            else: p1c[a],p1c[b]=p1c[b],p1c[a]
            new_cnt = count_colls(p0c,p1c,n)
            delta = new_cnt - cnt
            if delta < best_d:
                best_d, best_tp = delta, tp
        
        if best_d < 0:
            # 应用贪心最优
            tp_type,a,b = best_tp
            if tp_type=='p0': p0[a],p0[b]=p0[b],p0[a]
            else: p1[a],p1[b]=p1[b],p1[a]
            cnt += best_d
            stuck_count = 0
            if cnt < cnt_best: p0_best,p1_best = p0[:],p1[:]; cnt_best = cnt
            if it < 5 or cnt <= 20: print(f"  [{it}] cnt={cnt} (Δ={best_d})")
            continue
        
        # Step 2: STUCK — 2-step lookahead (try all pairs)
        stuck_count += 1
        if stuck_count > 3: break  # truly stuck
        
        print(f"  [{it}] STUCK at cnt={cnt}, trying {m}×{m} lookahead...")
        best_pair_d, best_pair = 0, None
        
        # Sample pairs (full enumeration too slow for n≥16 with >64 tps)
        n_sample = min(500, m*(m-1)//2)
        import random; random.seed(it)
        indices = random.sample(range(m*(m-1)//2), n_sample) if m>10 else range(m*(m-1)//2)
        
        for idx in indices:
            i1 = int((1 + (1+8*idx)**0.5) // 2) if m>10 else idx//(m-1)
            i2 = idx % (m-1)
            if i2 >= i1: i2 += 1
            if i1 >= m or i2 >= m: continue
            
            tp1, tp2 = all_single[i1], all_single[i2]
            
            p0c,p1c = p0[:],p1[:]
            for tp in [tp1, tp2]:
                tp_type,a,b = tp
                if tp_type=='p0': p0c[a],p0c[b]=p0c[b],p0c[a]
                else: p1c[a],p1c[b]=p1c[b],p1c[a]
            new_cnt = count_colls(p0c,p1c,n)
            delta = new_cnt - cnt
            
            if delta < best_pair_d:
                best_pair_d, best_pair = delta, (tp1, tp2)
        
        if best_pair_d < 0:
            print(f"    → pair Δ={best_pair_d}, applying")
            for tp in best_pair:
                tp_type,a,b = tp
                if tp_type=='p0': p0[a],p0[b]=p0[b],p0[a]
                else: p1[a],p1[b]=p1[b],p1[a]
            cnt += best_pair_d
            stuck_count = 0
            if cnt < cnt_best: p0_best,p1_best = p0[:],p1[:]; cnt_best = cnt
        else:
            print(f"    → no improving pair found")
    
    return p0_best, p1_best, cnt_best

print("="*64)
print("贪心+2-步前瞻: n=8,16")
print("="*64)

results = []
for n in [8, 16]:
    k = n.bit_length()-1
    p0=bitrev(n,k); p1=gray(n)
    base = count_colls(p0,p1,n)
    tps0=build_tps(p0,n,k); tps1=build_tps(p1,n,k)
    n_tps = len(tps0)+len(tps1)
    
    print(f"\n--- n={n} base={base} tps={n_tps} ---")
    t0=time.time()
    p0f,p1f,fc = greedy_with_lookahead(p0,p1,tps0,tps1,n,max_iter=200)
    elapsed = time.time()-t0
    
    ok,nb = verify_ntil(p0f,p1f,n) if fc==0 else (False,fc)
    
    r = {'n':n,'base':base,'final':fc,'time':round(elapsed,1),'ntil':ok}
    results.append(r)
    status = "NTIL ✓" if ok else f"✗ ({fc} residual)"
    print(f"  Result: {status} ({elapsed:.1f}s)")

print(f"\n===== 汇总 =====")
for r in results:
    print(f"  n={r['n']}: {r['base']}→{r['final']} ({r['time']}s, NTIL={r['ntil']})")

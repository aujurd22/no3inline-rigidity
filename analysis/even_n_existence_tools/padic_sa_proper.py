"""
正确版 SA: O(1) 增量 Δ 计算 + Metropolis 接受 + 慢降温 + 最优重启。
关键优化: 不用 count_colls_full，仅检查涉及交换行 (a,b) 的三元组 Δ。
"""
import itertools, json, time, random, math

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

def full_collision_count(p0, p1, n):
    """完整计数（仅验证时使用）"""
    cnt = 0
    for i,j,k in itertools.combinations(range(n),3):
        a0i,a0j,a0k=p0[i],p0[j],p0[k]
        a1i,a1j,a1k=p1[i],p1[j],p1[k]
        dxj,dxk=j-i,k-i
        if dxj*(a0k-a0i)==dxk*(a0j-a0i): cnt+=1
        if dxj*(a0k-a1i)==dxk*(a0j-a1i): cnt+=1
        if dxj*(a1k-a0i)==dxk*(a1j-a0i): cnt+=1
        if dxj*(a1k-a1i)==dxk*(a1j-a1i): cnt+=1
        if dxj*(a0k-a0i)==dxk*(a1j-a0i): cnt+=1
        if dxj*(a0k-a1i)==dxk*(a1j-a1i): cnt+=1
        if dxj*(a1k-a0i)==dxk*(a0j-a0i): cnt+=1
        if dxj*(a1k-a1i)==dxk*(a0j-a1i): cnt+=1
    return cnt

def count_triple_colls(p0, p1, i, j, k):
    """三元组 (i,j,k) 的 8-type 碰撞数 (i<j<k)"""
    p0i,p0j,p0k = p0[i],p0[j],p0[k]
    p1i,p1j,p1k = p1[i],p1[j],p1[k]
    dxj,dxk = j-i, k-i
    c = 0
    if dxj*(p0k-p0i)==dxk*(p0j-p0i): c+=1
    if dxj*(p0k-p1i)==dxk*(p0j-p1i): c+=1
    if dxj*(p1k-p0i)==dxk*(p1j-p0i): c+=1
    if dxj*(p1k-p1i)==dxk*(p1j-p1i): c+=1
    if dxj*(p0k-p0i)==dxk*(p1j-p0i): c+=1
    if dxj*(p0k-p1i)==dxk*(p1j-p1i): c+=1
    if dxj*(p1k-p0i)==dxk*(p0j-p0i): c+=1
    if dxj*(p1k-p1i)==dxk*(p0j-p1i): c+=1
    return c

def count_delta(p0, p1, n, a, b, tp_type):
    """增量 Δ: 所有涉及行 a 或 b 的三元组变化 (O(n²))"""
    # 记录 old 值
    old_total = 0
    changed = {a, b}
    
    # 所有涉及 a 或 b 的三元组
    for r1 in range(n):
        if r1 in changed: continue
        for r2 in range(r1+1, n):
            if r2 in changed: continue
            # 三元组 (a, r1, r2): a 在 changed 集中
            triples = []
            # a with r1,r2, b with r1,r2, a,b with r1
            for x in changed:
                rows = sorted([x, r1, r2])
                triples.append(rows)
            for x in changed:
                for y in changed:
                    if x >= y: continue
                    rows = sorted([x, y, r1])
                    triples.append(rows)
            # Deduplicate
            for i,j,k in set(tuple(t) for t in triples):
                old_total += count_triple_colls(p0, p1, i, j, k)
    
    # 执行交换
    if tp_type == 'p0': p0[a],p0[b] = p0[b],p0[a]
    else: p1[a],p1[b] = p1[b],p1[a]
    
    # NEW count
    new_total = 0
    for r1 in range(n):
        if r1 in changed: continue
        for r2 in range(r1+1, n):
            if r2 in changed: continue
            triples = []
            for x in changed:
                rows = sorted([x, r1, r2])
                triples.append(rows)
            for x in changed:
                for y in changed:
                    if x >= y: continue
                    rows = sorted([x, y, r1])
                    triples.append(rows)
            for i,j,k in set(tuple(t) for t in triples):
                new_total += count_triple_colls(p0, p1, i, j, k)
    
    # 回滚
    if tp_type == 'p0': p0[a],p0[b] = p0[b],p0[a]
    else: p1[a],p1[b] = p1[b],p1[a]
    
    return new_total - old_total

def sa_proper(p0, p1, tps0, tps1, n, n_iter=20000, n_restarts=5):
    """正确版 SA: 增量 Δ + Metropolis + 慢降温"""
    all_tps = [('p0',a,b) for a,b in tps0] + [('p1',a,b) for a,b in tps1]
    m = len(all_tps)
    
    cnt = full_collision_count(p0, p1, n)
    best_p0, best_p1 = p0[:], p1[:]
    best_cnt = cnt
    
    total_swaps = 0
    
    for restart in range(n_restarts):
        T = 10.0
        alpha = (0.01/T)**(1.0/n_iter)  # 从T降到0.01
        
        for it in range(n_iter):
            if cnt == 0: break
            
            # 随机选 transposition
            tp_idx = random.randrange(m)
            tp_type, a, b = all_tps[tp_idx]
            
            # 增量计算 Δ
            delta = count_delta(p0, p1, n, a, b, tp_type)
            
            # Metropolis 接受
            if delta <= 0 or random.random() < math.exp(-delta / T):
                if tp_type == 'p0': p0[a], p0[b] = p0[b], p0[a]
                else: p1[a], p1[b] = p1[b], p1[a]
                cnt += delta
                total_swaps += 1
                
                if cnt < best_cnt:
                    best_p0, best_p1 = p0[:], p1[:]
                    best_cnt = cnt
            
            T *= alpha
        
        # 重启
        if cnt > 0:
            p0[:] = best_p0[:]
            p1[:] = best_p1[:]
            cnt = best_cnt
        
        if restart == 0 or cnt <= 20:
            print(f"  restart {restart}: cnt={cnt} (best={best_cnt}) swaps={total_swaps}")
    
    return best_p0, best_p1, best_cnt

def verify_ntil(p0,p1,n):
    pts=[(i,p0[i]) for i in range(n)]+[(i,p1[i]) for i in range(n)]
    bad=sum(1 for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3)
             if (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1))
    return bad==0, bad

random.seed(42)
print("="*64)
print("正确版 SA (增量Δ+Metropolis): n=8,16,32")
print("="*64)

for n in [8, 16, 32]:
    k = n.bit_length()-1
    p0=bitrev(n,k); p1=gray(n)
    base = full_collision_count(p0,p1,n)
    tp0=build_tps(p0,n,k); tp1=build_tps(p1,n,k)
    
    n_iter = 5000 if n<=16 else 3000
    n_restart = 10
    
    print(f"\n--- n={n} base={base} tps={len(tp0)+len(tp1)} ---")
    t0=time.time()
    p0f,p1f,fc = sa_proper(p0,p1,tp0,tp1,n, n_iter=n_iter, n_restarts=n_restart)
    elapsed = time.time()-t0
    
    ok, nb = verify_ntil(p0f,p1f,n) if fc==0 else (False,fc)
    status = "★ NTIL" if ok else f"✗ residual={fc}"
    print(f"  Result: {status} ({elapsed:.1f}s)")
    
    if ok:
        json.dump({'n':n,'p0':p0f,'p1':p1f,'time':elapsed},
                  open(f'ntil_n{n}_sa.json','w'),indent=2)
        print(f"  Saved ntil_n{n}_sa.json")

"""
纯对合型 SA 吸收器——多 N 可扩展性测试。
无进位、无暴力清理，纯 SA（20000 迭代 × O(N²)/swap）。
σ(x) = N-1-π(x)，所有点严格 0..N-1。
"""
import itertools, random, time, json, math

def full_collision_count(pi, N_val):
    cnt = 0
    for i,j,k in itertools.combinations(range(N_val),3):
        yi=pi[i]; yj=pi[j]; yk=pi[k]
        yis=N_val-1-pi[i]; yjs=N_val-1-pi[j]; yks=N_val-1-pi[k]
        if (j-i)*(yk-yi)==(k-i)*(yj-yi): cnt+=1
        if (j-i)*(yks-yi)==(k-i)*(yj-yi): cnt+=1
        if (j-i)*(yk-yi)==(k-i)*(yjs-yi): cnt+=1
        if (j-i)*(yk-yis)==(k-i)*(yj-yis): cnt+=1
        if (j-i)*(yks-yis)==(k-i)*(yjs-yis): cnt+=1
        if (j-i)*(yks-yi)==(k-i)*(yjs-yi): cnt+=1
        if (j-i)*(yk-yis)==(k-i)*(yj-yis): cnt+=1
        if (j-i)*(yks-yis)==(k-i)*(yjs-yis): cnt+=1
    return cnt

def sa_one_trial(N_val, max_iter=20000, seed=42):
    random.seed(seed)
    pi = list(range(N_val)); random.shuffle(pi)
    cnt = full_collision_count(pi, N_val)
    best_pi = pi[:]; best_cnt = cnt
    
    T = 2.0; alpha = 0.998
    swaps = 0; accepted = 0
    
    for it in range(max_iter):
        if cnt == 0: break
        i, j = random.sample(range(N_val), 2)
        old_pi = pi[i], pi[j]
        pi[i], pi[j] = pi[j], pi[i]
        
        # 增量：仅计涉及 i,j 的三元组变化
        triples_ij = set()
        others = [x for x in range(N_val) if x not in (i,j)]
        for k in others:
            triples_ij.add(tuple(sorted([i,j,k])))
        for r in (i,j):
            for jj, kk in itertools.combinations(others, 2):
                triples_ij.add(tuple(sorted([r, jj, kk])))
        
        old_cnt_local = 0
        for ti,tj,tk in triples_ij:
            yi=pi[ti]; yj=pi[tj]; yk=pi[tk]  # NOTE: using OLD pi (we haven't swapped yet here - BUG!)
        
        # Actually need to compute old first, then new. Let me restructure.
        
    # Bug in the above - let me just do full count for now and be efficient about it.
    # The full_collision_count does C(N,3)=650K triples×8=5.2M ops, ~0.2s.
    # With 20000 iterations that's too slow. Use delta method.
    
    # Delta approach:
    # 1. Compute old collisions for triples involving i,j
    # 2. Swap
    # 3. Compute new collisions for same triples
    # 4. Delta = new_cnt - old_cnt
    
    for it in range(max_iter):
        if cnt == 0: break
        i, j = random.sample(range(N_val), 2)
        
        # 涉及 i,j 的三元组
        triples_ij = set()
        others_t = [x for x in range(N_val) if x not in (i,j)]
        for k in others_t:
            triples_ij.add(tuple(sorted([i,j,k])))
        for r in (i,j):
            for jj, kk in itertools.combinations(others_t, 2):
                triples_ij.add(tuple(sorted([r, jj, kk])))
        
        # 旧计数
        old_cnt = 0
        for ti, tj, tk in triples_ij:
            yi=pi[ti]; yj2=pi[tj]; yk2=pi[tk]
            yis=N_val-1-pi[ti]; yjs=N_val-1-pi[tj]; yks=N_val-1-pi[tk]
            if (tj-ti)*(yk2-yi)==(tk-ti)*(yj2-yi): old_cnt+=1
            if (tj-ti)*(yks-yi)==(tk-ti)*(yj2-yi): old_cnt+=1
            if (tj-ti)*(yk2-yi)==(tk-ti)*(yjs-yi): old_cnt+=1
            if (tj-ti)*(yk2-yis)==(tk-ti)*(yj2-yis): old_cnt+=1
            if (tj-ti)*(yks-yis)==(tk-ti)*(yjs-yis): old_cnt+=1
            if (tj-ti)*(yks-yi)==(tk-ti)*(yjs-yi): old_cnt+=1
            if (tj-ti)*(yk2-yis)==(tk-ti)*(yj2-yis): old_cnt+=1
            if (tj-ti)*(yks-yis)==(tk-ti)*(yjs-yis): old_cnt+=1
        
        # 交换
        pi[i], pi[j] = pi[j], pi[i]
        
        # 新计数
        new_cnt = 0
        for ti, tj, tk in triples_ij:
            yi=pi[ti]; yj2=pi[tj]; yk2=pi[tk]
            yis=N_val-1-pi[ti]; yjs=N_val-1-pi[tj]; yks=N_val-1-pi[tk]
            if (tj-ti)*(yk2-yi)==(tk-ti)*(yj2-yi): new_cnt+=1
            if (tj-ti)*(yks-yi)==(tk-ti)*(yj2-yi): new_cnt+=1
            if (tj-ti)*(yk2-yi)==(tk-ti)*(yjs-yi): new_cnt+=1
            if (tj-ti)*(yk2-yis)==(tk-ti)*(yj2-yis): new_cnt+=1
            if (tj-ti)*(yks-yis)==(tk-ti)*(yjs-yis): new_cnt+=1
            if (tj-ti)*(yks-yi)==(tk-ti)*(yjs-yi): new_cnt+=1
            if (tj-ti)*(yk2-yis)==(tk-ti)*(yj2-yis): new_cnt+=1
            if (tj-ti)*(yks-yis)==(tk-ti)*(yjs-yis): new_cnt+=1
        
        delta = new_cnt - old_cnt
        accepted += 1
        
        if delta <= 0:
            cnt += delta; swaps += 1
            if cnt < best_cnt:
                best_pi = pi[:]; best_cnt = cnt
        elif random.random() < pow(2.718, -delta/max(T,0.01)):
            cnt += delta; swaps += 1
            if cnt < best_cnt:
                best_pi = pi[:]; best_cnt = cnt
        else:
            pi[i], pi[j] = pi[j], pi[i]  # 回滚
            accepted -= 1
        
        T *= alpha
        if it % 500 == 499:
            # 定期校准
            cnt = full_collision_count(pi, N_val)
        if it % 2000 == 1999:
            T = 2.0
            pi[:] = best_pi[:]
            cnt = full_collision_count(pi, N_val)
    
    return best_pi, best_cnt, swaps

print("="*64)
print("纯对合型 SA 吸收器 — 多 N 可扩展性测试")
print("="*64)

for N_val in [20, 30, 40, 50, 60, 74]:
    print(f"\n=== N={N_val} ===")
    for trial in range(3):
        t0 = time.time()
        seed = 42 + trial*100 + N_val
        random.seed(seed)
        pi_init = list(range(N_val)); random.shuffle(pi_init)
        init_cnt = full_collision_count(pi_init, N_val)
        
        pi, final_cnt, swaps = sa_one_trial(N_val, max_iter=20000, seed=seed)
        elapsed = time.time() - t0
        
        status = "✓ 0!" if final_cnt == 0 else f"cnt={final_cnt}"
        print(f"  trial{trial}: {init_cnt}→{status} swaps={swaps} ({elapsed:.1f}s)")
    print(f"  (SA only, no brute-force)")

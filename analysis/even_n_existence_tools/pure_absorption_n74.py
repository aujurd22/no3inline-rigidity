"""
纯对合型吸收器 N=74 直测（简化版）。
σ(x) = N-1-π(x)，所有点严格在 0..N-1 方格内。
每次 swap 仅测涉及变化行的冲突数（O(N²)），定期全量校准。
"""
import itertools, random, time, json

def count_triple_collisions(pi, N_val, triples_subset):
    """对指定三元组子集计数冲突。"""
    cnt = 0
    for i,j,k in triples_subset:
        yi=pi[i]; yj=pi[j]; yk=pi[k]
        yis=N_val-1-pi[i]; yjs=N_val-1-pi[j]; yks=N_val-1-pi[k]
        if (j-i)*(yk-yi)==(k-i)*(yj-yi): cnt+=1  # PPP
        if (j-i)*(yks-yi)==(k-i)*(yj-yi): cnt+=1  # PPS_k
        if (j-i)*(yk-yi)==(k-i)*(yjs-yi): cnt+=1  # PPS_j
        if (j-i)*(yk-yis)==(k-i)*(yj-yis): cnt+=1  # PPS_i
        if (j-i)*(yks-yis)==(k-i)*(yjs-yis): cnt+=1  # PSS_i
        if (j-i)*(yks-yi)==(k-i)*(yjs-yi): cnt+=1  # PSS_j
        if (j-i)*(yk-yis)==(k-i)*(yj-yis): cnt+=1  # PSS_k
        if (j-i)*(yks-yis)==(k-i)*(yjs-yis): cnt+=1  # SSS
    return cnt

def full_collision_count(pi, N_val):
    """全量冲突计数。"""
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

def sa_clean(N_val, max_iter=10000, seed=42):
    """简化 SA：O(N²) per swap，定期校准。"""
    random.seed(seed)
    pi = list(range(N_val)); random.shuffle(pi)
    
    # 初始全量计数
    cnt = full_collision_count(pi, N_val)
    best_pi = pi[:]; best_cnt = cnt
    
    T = 2.0; alpha = 0.995
    swaps = 0; rsts = 0
    
    for it in range(max_iter):
        if cnt == 0: break
        
        i, j = random.sample(range(N_val), 2)
        old_pi_i, old_pi_j = pi[i], pi[j]
        
        # 涉及 i 或 j 的所有三元组
        triples_ij = []
        others = sorted(set(range(N_val)) - {i,j})
        for k in others:
            triples_ij.append(sorted([i,j,k]))
        for r in (i,j):
            for jj, kk in itertools.combinations(others, 2):
                triples_ij.append(sorted([r, jj, kk]))
        # 去重
        triples_ij = list(set(tuple(t) for t in triples_ij))
        
        old_cnt_ij = count_triple_collisions(pi, N_val, triples_ij)
        
        # 执行交换
        pi[i], pi[j] = pi[j], pi[i]
        new_cnt_ij = count_triple_collisions(pi, N_val, triples_ij)
        
        delta = new_cnt_ij - old_cnt_ij
        
        if delta <= 0 or random.random() < pow(2.718, -delta/max(T,0.01)):
            cnt += delta; swaps += 1
            if cnt < best_cnt:
                best_pi = pi[:]; best_cnt = cnt
        else:
            pi[i], pi[j] = old_pi_i, old_pi_j
        
        T *= alpha
        if it % 500 == 499:
            # 定期校准
            true_cnt = full_collision_count(pi, N_val)
            if true_cnt != cnt:
                cnt = true_cnt
            if it % 2000 == 1999:
                T = 2.0; rsts += 1
                pi[:] = best_pi[:]
                cnt = full_collision_count(pi, N_val)
    
    # 最终校准
    pi[:] = best_pi[:]
    cnt = full_collision_count(pi, N_val)
    return pi, cnt, swaps, rsts

def brute_force_cleanup(pi, N_val):
    """暴力消除残存冲突。"""
    cnt = full_collision_count(pi, N_val)
    if cnt == 0: return pi, 0
    
    # 4-环全枚举
    for i, j in itertools.combinations(range(N_val), 2):
        pi[i], pi[j] = pi[j], pi[i]
        new_cnt = full_collision_count(pi, N_val)
        if new_cnt < cnt:
            cnt = new_cnt
            if cnt == 0: return pi, 4
        else:
            pi[i], pi[j] = pi[j], pi[i]
    
    # 6-环
    for i, j, k in itertools.combinations(range(N_val), 3):
        pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
        new_cnt = full_collision_count(pi, N_val)
        if new_cnt < cnt:
            cnt = new_cnt
            if cnt == 0: return pi, 6
        else:
            pi[i], pi[j], pi[k] = pi[k], pi[i], pi[j]
    
    return pi, cnt

def verify_ntil(pi, N_val):
    """完整验证。"""
    pts = [(x, pi[x]) for x in range(N_val)] + [(x, N_val-1-pi[x]) for x in range(N_val)]
    for x,y in pts:
        if not (0 <= x < N_val and 0 <= y < N_val):
            return False, f"OOB: ({x},{y})"
    if len(set(pts)) < 2*N_val:
        return False, "dups"
    for p1,p2,p3 in itertools.combinations(pts, 3):
        x1,y1=p1; x2,y2=p2; x3,y3=p3
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            return False, "collinear"
    return True, "OK"

N=74
print(f"=== N={N} 纯对合型吸收器 (无进位, 简化 SA) ===")
t0 = time.time()

for trial in range(5):
    random.seed(42 + trial*100)
    t1 = time.time()
    pi, cnt, swaps, rsts = sa_clean(N, max_iter=10000, seed=42+trial*100)
    elapsed_sa = time.time() - t1
    print(f"  trial{trial}: SA→cnt={cnt} swaps={swaps} rsts={rsts} ({elapsed_sa:.1f}s)")
    
    if cnt <= 5:
        t2 = time.time()
        pi, remaining = brute_force_cleanup(pi[:], N)
        elapsed_bf = time.time() - t2
        print(f"    brute-force: remaining={remaining} ({elapsed_bf:.1f}s)")
        
        if remaining == 0:
            ok, msg = verify_ntil(pi, N)
            print(f"    ★ verify: {ok} {msg}")
            if ok:
                json.dump({'N':N,'pi':pi}, open('ntil_solution_n74_pure.json','w'), indent=2)
                print(f"    ★★★ N=74 NTIL 解！总耗时 {time.time()-t0:.1f}s")
                break

elapsed = time.time() - t0
print(f"\n总耗时 {elapsed:.0f}s")

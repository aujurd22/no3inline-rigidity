"""
N=74 直接进位+SA 测试。关键改动：更大 patience、8-环、多重启、多 carry 尝试。
"""
import sys, itertools, random, time, math, copy, json
from collections import Counter

def build_collision_map(pi, N_val):
    collisions = {}
    for i, j, k in itertools.combinations(range(N_val), 3):
        x1,y1=i,pi[i]; x2,y2=j,pi[j]; x3,y3=k,pi[k]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PPP')] = True
        y3s = N_val-1-pi[k]
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PPS')] = True
        y2s = N_val-1-pi[j]; y3s = N_val-1-pi[k]
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PSS')] = True
    return collisions

def update_collision_map(pi, N_val, collisions, changed_rows):
    to_remove = [key for key in collisions
                 if any(r in (key[0],key[1],key[2]) for r in changed_rows)]
    for k in to_remove: del collisions[k]
    all_rows = set(range(N_val))
    for r in changed_rows:
        others = all_rows - {r}
        for a, b in itertools.combinations(others, 2):
            i, j, k = sorted([r, a, b])
            x1,y1=i,pi[i]; x2,y2=j,pi[j]; x3,y3=k,pi[k]
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                collisions[(i,j,k,'PPP')] = True
            y3s = N_val-1-pi[k]
            if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
                collisions[(i,j,k,'PPS')] = True
            y2s = N_val-1-pi[j]
            if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
                collisions[(i,j,k,'PSS')] = True

def sa_absorb_large(pi, N_val, max_iter=20000, patience=300):
    collisions = build_collision_map(pi, N_val)
    cnt = len(collisions)
    best_cnt, best_pi = cnt, pi.copy()
    T, T_min, T_decay = 3.0, 0.002, 0.999
    no_imp, swaps, rsts = 0, 0, 0
    
    for it in range(max_iter):
        if cnt == 0: break
        
        # 热点行
        hot = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                     key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])),
                     reverse=True)[:min(15, N_val)]
        
        improved = False
        saved = copy.deepcopy(collisions)
        
        # 4-环
        candidates = [(hot[i], hot[j]) for i in range(len(hot))
                      for j in range(i+1, len(hot))]
        random.shuffle(candidates)
        best_d, best_pair = 0, None
        for i, j in candidates[:50]:  # 限制搜索量
            old_cnt = cnt
            pi[i], pi[j] = pi[j], pi[i]
            update_collision_map(pi, N_val, collisions, {i, j})
            delta = len(collisions) - old_cnt
            pi[i], pi[j] = pi[j], pi[i]
            collisions.clear(); collisions.update(saved)
            
            accept = delta < 0 or (delta <= 3 and random.random() < math.exp(-delta/T))
            if accept and (delta < best_d or best_pair is None):
                best_d, best_pair = delta, (i, j)
        
        if best_pair and best_d <= 0:
            i, j = best_pair
            pi[i], pi[j] = pi[j], pi[i]
            update_collision_map(pi, N_val, collisions, {i, j})
            cnt = len(collisions); improved = True; swaps += 1
        
        # 6-环
        if not improved:
            for _ in range(min(10, len(hot))):
                try: a,b,c = random.sample(hot, 3)
                except: break
                old_cnt = cnt
                pi[a],pi[b],pi[c] = pi[b],pi[c],pi[a]
                update_collision_map(pi, N_val, collisions, {a,b,c})
                delta = len(collisions) - old_cnt
                pi[a],pi[b],pi[c] = pi[c],pi[a],pi[b]
                collisions.clear(); collisions.update(saved)
                if delta < 0:
                    pi[a],pi[b],pi[c] = pi[b],pi[c],pi[a]
                    update_collision_map(pi, N_val, collisions, {a,b,c})
                    cnt = len(collisions); improved = True; swaps += 1
                    break
        
        # 8-环（仅当 cnt≤5 时）
        if not improved and cnt <= 5:
            for _ in range(min(5, len(hot))):
                try: a,b,c,d = random.sample(hot, 4)
                except: break
                old_cnt = cnt
                pi[a],pi[b],pi[c],pi[d] = pi[b],pi[c],pi[d],pi[a]
                update_collision_map(pi, N_val, collisions, {a,b,c,d})
                delta = len(collisions) - old_cnt
                pi[a],pi[b],pi[c],pi[d] = pi[d],pi[a],pi[b],pi[c]
                collisions.clear(); collisions.update(saved)
                if delta < 0:
                    pi[a],pi[b],pi[c],pi[d] = pi[b],pi[c],pi[d],pi[a]
                    update_collision_map(pi, N_val, collisions, {a,b,c,d})
                    cnt = len(collisions); improved = True; swaps += 1
                    break
        
        if improved:
            no_imp = 0
            if cnt < best_cnt: best_cnt, best_pi = cnt, pi.copy()
        else:
            no_imp += 1
            if no_imp >= patience:
                pi[:] = best_pi; cnt = best_cnt
                hot2 = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                              key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])),
                              reverse=True)[:10]
                for _ in range(int(5 + N_val*0.1)):
                    if len(hot2) >= 2: i,j = random.sample(hot2, 2)
                    else: i,j = random.sample(range(N_val), 2)
                    pi[i], pi[j] = pi[j], pi[i]
                collisions = build_collision_map(pi, N_val)
                cnt = len(collisions); no_imp = 0; rsts += 1; T = 3.0
        
        T = max(T * T_decay, T_min)
        if it % 500 == 0:
            print(f"    [{it}] cnt={cnt} best={best_cnt} swaps={swaps} rst={rsts} T={T:.3f}")
    
    pi[:] = best_pi
    return len(collisions), swaps, rsts


# ===== 主实验 =====
random.seed(12345)
print("="*64)
print("N=74 进位+SA 直接测试")
print("="*64)

N_val = 74
n_carry_attempts = 10

for trial in range(3):
    print(f"\n--- trial {trial} ---")
    t0 = time.time()
    
    # 1. 随机排列
    pi = list(range(N_val)); random.shuffle(pi)
    
    # 2. 进位提升（更多尝试）
    best_cnt = float('inf')
    best_pi = None
    for ca in range(n_carry_attempts):
        pi_int = [pi[i] + random.choice([0, N_val, 2*N_val]) for i in range(N_val)]
        z = 0
        # PPS only for speed (dominant type)
        for i,j,k in itertools.combinations(range(N_val), 3):
            x1,y1=i,pi_int[i]; x2,y2=j,pi_int[j]; x3,y3=k,N_val-1-pi_int[k]
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1): z += 1
        if z < best_cnt: best_cnt, best_pi = z, pi.copy()
        if z == 0:
            # Full verify
            pts = [(x, pi[x]) for x in range(N_val)] + [(x, N_val-1-pi[x]) for x in range(N_val)]
            if not any((x2-x1)*(y3-y1) == (x3-x1)*(y2-y1)
                       for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3)):
                best_cnt = 0; break
    
    print(f"  carry: {n_carry_attempts} attempts, best residual = {best_cnt}")
    
    if best_cnt == 0:
        print(f"  ★ carry直接解! ({time.time()-t0:.1f}s)")
        continue
    
    # 3. SA 吸收
    t1 = time.time()
    final, swaps, rsts = sa_absorb_large(best_pi, N_val, max_iter=20000, patience=400)
    elapsed = time.time() - t1
    
    if final == 0:
        print(f"  ★ SA吸收成功! swaps={swaps} rsts={rsts} ({elapsed:.1f}s)")
        # 保存解
        json.dump({'N': N_val, 'pi': best_pi, 'method': 'carry+SA'},
                  open('ntil_solution_n74.json', 'w'), indent=2)
        print(f"  解已保存到 ntil_solution_n74.json")
    else:
        print(f"  ✗ 未收敛, final={final} swaps={swaps} ({elapsed:.1f}s)")

print("\n完成.")

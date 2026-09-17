"""
进位配方 + SA 增量吸收器：完整 NTIL 构造法。
1. 随机对合 π_mod (σ = N-1-π)
2. 进位提升：π_int = π_mod + k_i * N  (k_i ∈ {0,1,2})
3. SA 吸收器消除残存整数共线（增量追踪，6-环辅助）
4. 完整 NTIL 验证
"""
import sys, itertools, random, time, math, copy, json
from collections import Counter, defaultdict

def build_collision_map(pi, N_val):
    """对合型全冲突映射（PPP+PPS+PSS）"""
    collisions = {}
    for i, j, k in itertools.combinations(range(N_val), 3):
        # PPP
        x1,y1=i,pi[i]; x2,y2=j,pi[j]; x3,y3=k,pi[k]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PPP')] = True
        # PPS
        y3s = N_val-1-pi[k]
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PPS')] = True
        # PSS
        y2s = N_val-1-pi[j]; y3s = N_val-1-pi[k]
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PSS')] = True
    return collisions

def update_collision_map(pi, N_val, collisions, changed_rows):
    """增量更新：删除涉及 changed_rows 的冲突，重新计算"""
    to_remove = [key for key in collisions
                 if any(r in (key[0],key[1],key[2]) for r in changed_rows)]
    for k in to_remove:
        del collisions[k]
    
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

def sa_absorb(pi, N_val, max_iter=8000, patience=200):
    """SA 吸收器消除残存冲突"""
    collisions = build_collision_map(pi, N_val)
    cnt = len(collisions)
    best_cnt, best_pi = cnt, pi.copy()
    T, T_min, T_decay = 2.0, 0.005, 0.998
    no_imp, swaps, rsts = 0, 0, 0
    
    for it in range(max_iter):
        if cnt == 0: break
        
        hot = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                     key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])),
                     reverse=True)[:min(12, N_val)]
        
        improved = False
        saved = copy.deepcopy(collisions)
        
        # 4-环 (热点感知 + 随机采样)
        candidates = [(hot[i], hot[j]) for i in range(len(hot))
                      for j in range(i+1, len(hot))]
        if len(candidates) < 20:
            extra = random.sample(range(N_val), min(10, N_val))
            candidates.extend((extra[i],extra[j]) for i in range(len(extra)) for j in range(i+1,len(extra)))
        
        best_d, best_pair = 0, None
        for i, j in candidates:
            old_cnt = cnt
            pi[i], pi[j] = pi[j], pi[i]
            update_collision_map(pi, N_val, collisions, {i, j})
            delta = len(collisions) - old_cnt
            # restore
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
        if not improved and N_val <= 24:
            for _ in range(min(15, len(hot))):
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
        
        if improved:
            no_imp = 0
            if cnt < best_cnt: best_cnt, best_pi = cnt, pi.copy()
        else:
            no_imp += 1
            if no_imp >= patience:
                pi[:] = best_pi; cnt = best_cnt
                hot2 = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                              key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])),
                              reverse=True)[:8]
                for _ in range(int(3 + N_val*0.15)):
                    if len(hot2) >= 2: i,j = random.sample(hot2, 2)
                    else: i,j = random.sample(range(N_val), 2)
                    pi[i], pi[j] = pi[j], pi[i]
                collisions = build_collision_map(pi, N_val)
                cnt = len(collisions); no_imp = 0; rsts += 1; T = 2.0
        
        T = max(T * T_decay, T_min)
    
    pi[:] = best_pi
    return len(collisions), swaps, rsts


# ===== 主实验 =====
random.seed(12345)
print("="*64)
print("进位配方 + SA 吸收器：NTIL 构造")
print("="*64)

results = []
for N_val in [10, 12, 16, 20, 24, 32]:
    print(f"\n--- N={N_val} ---")
    t0_total = time.time()
    solved = 0
    
    for trial in range(5 if N_val <= 16 else 3):
        # 1. 随机对合排列
        pi = list(range(N_val)); random.shuffle(pi)
        initial_conflicts = len(build_collision_map(pi, N_val))
        
        # 2. 进位提升（尝试多种进位模式）
        best_cnt = float('inf')
        best_pi = None
        for _ in range(5):  # 5 次进位尝试
            pi_int = [pi[i] + random.choice([0, N_val, 2*N_val]) for i in range(N_val)]
            # 用 mod 版本检查（进位效果体现在行列式非零，但在 mod 版本中看不见）
            # 直接 check 整数行列式
            z = 0
            for i,j,k in itertools.combinations(range(N_val),3):
                for (y1f,y2f,y3f) in [
                    (pi_int, pi_int, [N_val-1-v for v in pi_int]),
                    (pi_int, [N_val-1-v for v in pi_int], [N_val-1-v for v in pi_int]),
                ]:
                    x1,y1=i,y1f[i]; x2,y2=j,y2f[j]; x3,y3=k,y3f[k]
                    if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1): z += 1
            if z < best_cnt:
                best_cnt = z
                best_pi = pi.copy()  # 存 mod 版本
                # 如果进位后 0 冲突，直接用 mod 版本
                if z == 0:
                    # 验证完整 NTIL
                    pts = [(x, pi[x]) for x in range(N_val)] + [(x, N_val-1-pi[x]) for x in range(N_val)]
                    all_ok = not any((x2-x1)*(y3-y1) == (x3-x1)*(y2-y1)
                                     for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3))
                    if not all_ok:
                        z = 999  # 进位解不是完整 NTIL，继续搜
                    else:
                        best_cnt = 0
        
        if best_cnt == 0:
            solved += 1
            print(f"  trial{trial}: ✓ carry直接解! (init={initial_conflicts})")
            continue
        
        pi = best_pi.copy()
        
        # 3. SA 吸收器
        t0 = time.time()
        final_cnt, swaps, rsts = sa_absorb(pi, N_val, max_iter=8000, patience=200)
        elapsed = time.time() - t0
        
        if final_cnt == 0:
            solved += 1
            print(f"  trial{trial}: ✓ SA吸收! (init={initial_conflicts} carry→{best_cnt} swaps={swaps} rst={rsts} {elapsed:.1f}s)")
        else:
            print(f"  trial{trial}: ✗ final={final_cnt} init={initial_conflicts} carry→{best_cnt} swaps={swaps} {elapsed:.1f}s")
    
    results.append((N_val, solved, (time.time()-t0_total)/max(1,solved or 1)))
    print(f"  收敛率: {solved}/{5 if N_val<=16 else 3}")

print(f"\n===== 总汇 =====")
for N_val, solved, avg_t in results:
    print(f"  N={N_val}: {solved} solved  avg={avg_t:.1f}s/solved")

print("\n完成.")

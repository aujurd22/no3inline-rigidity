"""
v3: SA + brute-force final cleanup for N=74.
cnt ≤ 3 时：穷举所有 4-环 (C(N,2)) + 所有 6-环 (C(N,3)) 直到收敛。
"""
import sys, itertools, random, time, math, copy, json
from collections import Counter

def build_int_collision_map(pi_mod, carry, N_val):
    collisions = {}
    for i, j, k in itertools.combinations(range(N_val), 3):
        yi = pi_mod[i] + carry[i]*N_val
        yj = pi_mod[j] + carry[j]*N_val
        yk = pi_mod[k] + carry[k]*N_val
        if (j-i)*(yk-yi) == (k-i)*(yj-yi):
            collisions[(i,j,k,'PPP')] = True
        yk_s = N_val-1 - (pi_mod[k] + carry[k]*N_val)
        if (j-i)*(yk_s-yi) == (k-i)*(yj-yi):
            collisions[(i,j,k,'PPS')] = True
        yj_s = N_val-1 - (pi_mod[j] + carry[j]*N_val)
        if (j-i)*(yk_s-yi) == (k-i)*(yj_s-yi):
            collisions[(i,j,k,'PSS')] = True
    return collisions

def update_int_collision_map(pi_mod, carry, N_val, collisions, changed_rows):
    to_remove = [key for key in collisions
                 if any(r in (key[0],key[1],key[2]) for r in changed_rows)]
    for k in to_remove: del collisions[k]
    all_rows = set(range(N_val))
    for r in changed_rows:
        others = all_rows - {r}
        for a, b in itertools.combinations(others, 2):
            i, j, k = sorted([r, a, b])
            yi = pi_mod[i] + carry[i]*N_val
            yj = pi_mod[j] + carry[j]*N_val
            yk = pi_mod[k] + carry[k]*N_val
            if (j-i)*(yk-yi) == (k-i)*(yj-yi):
                collisions[(i,j,k,'PPP')] = True
            yk_s = N_val-1 - (pi_mod[k] + carry[k]*N_val)
            if (j-i)*(yk_s-yi) == (k-i)*(yj-yi):
                collisions[(i,j,k,'PPS')] = True
            yj_s = N_val-1 - (pi_mod[j] + carry[j]*N_val)
            if (j-i)*(yk_s-yi) == (k-i)*(yj_s-yi):
                collisions[(i,j,k,'PSS')] = True

def brute_force_cleanup(pi_mod, carry, N_val):
    """暴力穷举清除最后 cnt ≤ 3 个冲突"""
    collisions = build_int_collision_map(pi_mod, carry, N_val)
    cnt = len(collisions)
    if cnt == 0: return True
    
    saved = copy.deepcopy(collisions)
    
    # 阶段1: 穷举所有 4-环
    for i in range(N_val):
        for j in range(i+1, N_val):
            old_cnt = cnt
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            update_int_collision_map(pi_mod, carry, N_val, collisions, {i, j})
            new_cnt = len(collisions)
            if new_cnt < old_cnt:
                # 接受改进，继续
                pi_mod[i], pi_mod[j] = pi_mod[i], pi_mod[j]  # undo
                collisions.clear(); collisions.update(saved)
                # redo
                pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                update_int_collision_map(pi_mod, carry, N_val, collisions, {i, j})
                cnt = new_cnt; saved = copy.deepcopy(collisions)
                if cnt == 0: return True
            else:
                pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                collisions.clear(); collisions.update(saved)
    
    # 阶段2: 穷举所有 6-环
    for i, j, k in itertools.combinations(range(N_val), 3):
        old_cnt = cnt
        pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[j], pi_mod[k], pi_mod[i]
        update_int_collision_map(pi_mod, carry, N_val, collisions, {i, j, k})
        new_cnt = len(collisions)
        if new_cnt < old_cnt:
            pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[k], pi_mod[i], pi_mod[j]
            collisions.clear(); collisions.update(saved)
            pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[j], pi_mod[k], pi_mod[i]
            update_int_collision_map(pi_mod, carry, N_val, collisions, {i, j, k})
            cnt = new_cnt; saved = copy.deepcopy(collisions)
            if cnt == 0: return True
        else:
            pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[k], pi_mod[i], pi_mod[j]
            collisions.clear(); collisions.update(saved)
    
    # 阶段3: 穷举所有 8-环 (最多尝试)
    for a,b,c,d in itertools.combinations(range(N_val), 4):
        old_cnt = cnt
        pi_mod[a],pi_mod[b],pi_mod[c],pi_mod[d] = pi_mod[b],pi_mod[c],pi_mod[d],pi_mod[a]
        update_int_collision_map(pi_mod, carry, N_val, collisions, {a,b,c,d})
        new_cnt = len(collisions)
        if new_cnt < old_cnt:
            pi_mod[a],pi_mod[b],pi_mod[c],pi_mod[d] = pi_mod[d],pi_mod[a],pi_mod[b],pi_mod[c]
            collisions.clear(); collisions.update(saved)
            pi_mod[a],pi_mod[b],pi_mod[c],pi_mod[d] = pi_mod[b],pi_mod[c],pi_mod[d],pi_mod[a]
            update_int_collision_map(pi_mod, carry, N_val, collisions, {a,b,c,d})
            cnt = new_cnt; saved = copy.deepcopy(collisions)
            if cnt == 0: return True
        else:
            pi_mod[a],pi_mod[b],pi_mod[c],pi_mod[d] = pi_mod[d],pi_mod[a],pi_mod[b],pi_mod[c]
            collisions.clear(); collisions.update(saved)
    
    return cnt == 0

def sa_absorb_v3(pi_mod, carry, N_val, max_iter=8000, patience=200):
    collisions = build_int_collision_map(pi_mod, carry, N_val)
    cnt = len(collisions)
    best_cnt, best_pi = cnt, pi_mod.copy()
    T, T_min, T_decay = 3.0, 0.002, 0.999
    no_imp, swaps, rsts = 0, 0, 0
    
    for it in range(max_iter):
        if cnt == 0: break
        
        # 暴力清理（cnt ≤ 3）
        if cnt <= 3:
            print(f"    [{it}] cnt={cnt} → brute force cleanup...")
            t_bf = time.time()
            ok = brute_force_cleanup(pi_mod, carry, N_val)
            collisions = build_int_collision_map(pi_mod, carry, N_val)
            cnt = len(collisions)
            print(f"    brute force: cnt={cnt} ({time.time()-t_bf:.1f}s)")
            if cnt == 0: break
            best_cnt, best_pi = cnt, pi_mod.copy()
        
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
        for i, j in candidates[:50]:
            old_cnt = cnt
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            update_int_collision_map(pi_mod, carry, N_val, collisions, {i, j})
            delta = len(collisions) - old_cnt
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            collisions.clear(); collisions.update(saved)
            accept = delta < 0 or (delta <= 3 and random.random() < math.exp(-delta/T))
            if accept and (delta < best_d or best_pair is None):
                best_d, best_pair = delta, (i, j)
        
        if best_pair and best_d <= 0:
            i, j = best_pair
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            update_int_collision_map(pi_mod, carry, N_val, collisions, {i, j})
            cnt = len(collisions); improved = True; swaps += 1
        
        # 6-环
        if not improved:
            for _ in range(min(10, len(hot))):
                try: a,b,c = random.sample(hot, 3)
                except: break
                old_cnt = cnt
                pi_mod[a],pi_mod[b],pi_mod[c] = pi_mod[b],pi_mod[c],pi_mod[a]
                update_int_collision_map(pi_mod, carry, N_val, collisions, {a,b,c})
                delta = len(collisions) - old_cnt
                pi_mod[a],pi_mod[b],pi_mod[c] = pi_mod[c],pi_mod[a],pi_mod[b]
                collisions.clear(); collisions.update(saved)
                if delta < 0:
                    pi_mod[a],pi_mod[b],pi_mod[c] = pi_mod[b],pi_mod[c],pi_mod[a]
                    update_int_collision_map(pi_mod, carry, N_val, collisions, {a,b,c})
                    cnt = len(collisions); improved = True; swaps += 1
                    break
        
        if improved:
            no_imp = 0
            if cnt < best_cnt: best_cnt, best_pi = cnt, pi_mod.copy()
        else:
            no_imp += 1
            if no_imp >= patience:
                pi_mod[:] = best_pi; cnt = best_cnt
                collisions = build_int_collision_map(pi_mod, carry, N_val)
                hot2 = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                              key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])),
                              reverse=True)[:10]
                for _ in range(int(5 + N_val*0.1)):
                    if len(hot2) >= 2: i,j = random.sample(hot2, 2)
                    else: i,j = random.sample(range(N_val), 2)
                    pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                collisions = build_int_collision_map(pi_mod, carry, N_val)
                cnt = len(collisions); no_imp = 0; rsts += 1; T = 3.0
        
        T = max(T * T_decay, T_min)
        if it % 400 == 0:
            print(f"    [{it}] cnt={cnt} best={best_cnt} swaps={swaps} rst={rsts}")
    
    pi_mod[:] = best_pi
    return len(collisions), swaps, rsts


# ===== 主实验 =====
random.seed(12345)
print("="*64)
print("v3: N=74 进位+SA+暴力清理")
print("="*64)

N_val = 74

for trial in range(3):
    print(f"\n--- trial {trial} ---")
    t0 = time.time()
    
    pi = list(range(N_val)); random.shuffle(pi)
    
    # 进位：50 尝试 + 自适应
    best_cnt = float('inf')
    best_pi, best_carry = None, None
    for _ in range(50):
        carry = [random.choice([0, 1, 2]) for _ in range(N_val)]
        z = 0
        for i, j, k in itertools.combinations(range(N_val), 3):
            yi = pi[i] + carry[i]*N_val
            yj = pi[j] + carry[j]*N_val
            yk = pi[k] + carry[k]*N_val
            if (j-i)*(yk-yi) == (k-i)*(yj-yi): z += 1
            yk_s = N_val-1 - (pi[k] + carry[k]*N_val)
            if (j-i)*(yk_s-yi) == (k-i)*(yj-yi): z += 1
            yj_s = N_val-1 - (pi[j] + carry[j]*N_val)
            if (j-i)*(yk_s-yi) == (k-i)*(yj_s-yi): z += 1
        if z < best_cnt:
            best_cnt, best_pi, best_carry = z, pi.copy(), carry.copy()
        if z == 0: break
    
    print(f"  carry: best residual = {best_cnt} ({time.time()-t0:.1f}s)")
    
    if best_cnt == 0:
        print(f"  ★ carry直接解!")
        json.dump({'N': N_val, 'pi': best_pi, 'carry': best_carry},
                  open('ntil_solution_n74.json', 'w'), indent=2)
        continue
    
    # SA + brute force
    t1 = time.time()
    final, swaps, rsts = sa_absorb_v3(best_pi, best_carry, N_val)
    elapsed = time.time() - t1
    
    if final == 0:
        print(f"  ★★★ N=74 NTIL解! swaps={swaps} rst={rsts} ({elapsed:.1f}s)")
        json.dump({'N': N_val, 'pi': best_pi, 'carry': best_carry, 'method': 'v3',
                   'swaps': swaps, 'time': elapsed},
                  open('ntil_solution_n74.json', 'w'), indent=2)
        print(f"  解已保存!")
        break
    else:
        print(f"  ✗ final={final} swaps={swaps} ({elapsed:.1f}s)")

print("\n完成.")

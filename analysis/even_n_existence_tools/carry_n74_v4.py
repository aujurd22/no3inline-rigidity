"""
v4: 完整碰撞映射 — 检查全部 8 种赋值 (PPP+PPS×3+PSS×3+SSS)。
"""
import sys, itertools, random, time, math, copy, json
from collections import Counter

def build_full_collision_map(pi_mod, carry, N_val):
    """完整 8 种赋值的碰撞映射"""
    collisions = {}
    for i, j, k in itertools.combinations(range(N_val), 3):
        yi = pi_mod[i] + carry[i]*N_val
        yj = pi_mod[j] + carry[j]*N_val
        yk = pi_mod[k] + carry[k]*N_val
        si = N_val-1 - yi  # σ point at i
        sj = N_val-1 - yj  # σ point at j
        sk = N_val-1 - yk  # σ point at k
        
        # PPP (all π)
        if (j-i)*(yk-yi) == (k-i)*(yj-yi):
            collisions[(i,j,k,0)] = True  # 0=PPP
        
        # PPS ×3 (2π + 1σ)
        # σ at k
        if (j-i)*(sk-yi) == (k-i)*(yj-yi): collisions[(i,j,k,1)] = True
        # σ at j
        if (j-i)*(yk-yi) == (k-i)*(sj-yi): collisions[(i,j,k,2)] = True
        # σ at i
        if (j-i)*(yk-si) == (k-i)*(yj-si): collisions[(i,j,k,3)] = True
        
        # PSS ×3 (1π + 2σ)
        # π at i (σ at j,k)
        if (j-i)*(sk-yi) == (k-i)*(sj-yi): collisions[(i,j,k,4)] = True
        # π at j (σ at i,k)
        if (j-i)*(sk-si) == (k-i)*(yj-si): collisions[(i,j,k,5)] = True
        # π at k (σ at i,j)
        if (j-i)*(yk-si) == (k-i)*(sj-si): collisions[(i,j,k,6)] = True
        
        # SSS (all σ) — equivalent to PPP but checked for completeness
        if (j-i)*(sk-si) == (k-i)*(sj-si): collisions[(i,j,k,7)] = True
    return collisions

def update_full_collision_map(pi_mod, carry, N_val, collisions, changed_rows):
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
            si = N_val-1 - yi; sj = N_val-1 - yj; sk = N_val-1 - yk
            
            if (j-i)*(yk-yi) == (k-i)*(yj-yi): collisions[(i,j,k,0)] = True
            if (j-i)*(sk-yi) == (k-i)*(yj-yi): collisions[(i,j,k,1)] = True
            if (j-i)*(yk-yi) == (k-i)*(sj-yi): collisions[(i,j,k,2)] = True
            if (j-i)*(yk-si) == (k-i)*(yj-si): collisions[(i,j,k,3)] = True
            if (j-i)*(sk-yi) == (k-i)*(sj-yi): collisions[(i,j,k,4)] = True
            if (j-i)*(sk-si) == (k-i)*(yj-si): collisions[(i,j,k,5)] = True
            if (j-i)*(yk-si) == (k-i)*(sj-si): collisions[(i,j,k,6)] = True
            if (j-i)*(sk-si) == (k-i)*(sj-si): collisions[(i,j,k,7)] = True

def brute_force_full(pi_mod, carry, N_val):
    collisions = build_full_collision_map(pi_mod, carry, N_val)
    cnt = len(collisions)
    if cnt == 0: return True
    
    saved = copy.deepcopy(collisions)
    
    # 4-环
    for i in range(N_val):
        for j in range(i+1, N_val):
            old_cnt = cnt
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            update_full_collision_map(pi_mod, carry, N_val, collisions, {i, j})
            new_cnt = len(collisions)
            if new_cnt < old_cnt:
                pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                collisions.clear(); collisions.update(saved)
                pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                update_full_collision_map(pi_mod, carry, N_val, collisions, {i, j})
                cnt = new_cnt; saved = copy.deepcopy(collisions)
                if cnt == 0: return True
            else:
                pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                collisions.clear(); collisions.update(saved)
    
    # 6-环
    for i, j, k in itertools.combinations(range(N_val), 3):
        old_cnt = cnt
        pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[j], pi_mod[k], pi_mod[i]
        update_full_collision_map(pi_mod, carry, N_val, collisions, {i, j, k})
        new_cnt = len(collisions)
        if new_cnt < old_cnt:
            pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[k], pi_mod[i], pi_mod[j]
            collisions.clear(); collisions.update(saved)
            pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[j], pi_mod[k], pi_mod[i]
            update_full_collision_map(pi_mod, carry, N_val, collisions, {i, j, k})
            cnt = new_cnt; saved = copy.deepcopy(collisions)
            if cnt == 0: return True
        else:
            pi_mod[i], pi_mod[j], pi_mod[k] = pi_mod[k], pi_mod[i], pi_mod[j]
            collisions.clear(); collisions.update(saved)
    
    return cnt == 0

def sa_absorb_v4(pi_mod, carry, N_val, max_iter=8000, patience=200):
    collisions = build_full_collision_map(pi_mod, carry, N_val)
    cnt = len(collisions)
    best_cnt, best_pi = cnt, pi_mod.copy()
    T, T_min, T_decay = 3.0, 0.002, 0.999
    no_imp, swaps, rsts = 0, 0, 0
    
    for it in range(max_iter):
        if cnt == 0: break
        
        if cnt <= 3:
            print(f"    [{it}] cnt={cnt} → brute force...")
            t_bf = time.time()
            ok = brute_force_full(pi_mod, carry, N_val)
            collisions = build_full_collision_map(pi_mod, carry, N_val)
            cnt = len(collisions)
            print(f"      cnt={cnt} ({time.time()-t_bf:.1f}s)")
            if cnt == 0: break
            best_cnt, best_pi = cnt, pi_mod.copy()
        
        hot = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                     key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])),
                     reverse=True)[:min(15, N_val)]
        
        improved = False
        saved = copy.deepcopy(collisions)
        
        candidates = [(hot[i], hot[j]) for i in range(len(hot)) for j in range(i+1,len(hot))]
        random.shuffle(candidates)
        best_d, best_pair = 0, None
        for i, j in candidates[:50]:
            old_cnt = cnt
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            update_full_collision_map(pi_mod, carry, N_val, collisions, {i, j})
            delta = len(collisions) - old_cnt
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            collisions.clear(); collisions.update(saved)
            accept = delta < 0 or (delta <= 3 and random.random() < math.exp(-delta/T))
            if accept and (delta < best_d or best_pair is None):
                best_d, best_pair = delta, (i, j)
        
        if best_pair and best_d <= 0:
            i, j = best_pair
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            update_full_collision_map(pi_mod, carry, N_val, collisions, {i, j})
            cnt = len(collisions); improved = True; swaps += 1
        
        if not improved:
            for _ in range(min(10, len(hot))):
                try: a,b,c = random.sample(hot, 3)
                except: break
                old_cnt = cnt
                pi_mod[a],pi_mod[b],pi_mod[c] = pi_mod[b],pi_mod[c],pi_mod[a]
                update_full_collision_map(pi_mod, carry, N_val, collisions, {a,b,c})
                delta = len(collisions) - old_cnt
                pi_mod[a],pi_mod[b],pi_mod[c] = pi_mod[c],pi_mod[a],pi_mod[b]
                collisions.clear(); collisions.update(saved)
                if delta < 0:
                    pi_mod[a],pi_mod[b],pi_mod[c] = pi_mod[b],pi_mod[c],pi_mod[a]
                    update_full_collision_map(pi_mod, carry, N_val, collisions, {a,b,c})
                    cnt = len(collisions); improved = True; swaps += 1
                    break
        
        if improved:
            no_imp = 0
            if cnt < best_cnt: best_cnt, best_pi = cnt, pi_mod.copy()
        else:
            no_imp += 1
            if no_imp >= patience:
                pi_mod[:] = best_pi; cnt = best_cnt
                collisions = build_full_collision_map(pi_mod, carry, N_val)
                hot2 = sorted({r for key in collisions for r in (key[0],key[1],key[2])},
                              key=lambda r: sum(1 for k in collisions if r in (k[0],k[1],k[2])), reverse=True)[:10]
                for _ in range(int(5+N_val*0.1)):
                    if len(hot2)>=2: i,j=random.sample(hot2,2)
                    else: i,j=random.sample(range(N_val),2)
                    pi_mod[i],pi_mod[j]=pi_mod[j],pi_mod[i]
                collisions = build_full_collision_map(pi_mod, carry, N_val)
                cnt=len(collisions); no_imp=0; rsts+=1; T=3.0
        
        T = max(T*T_decay, T_min)
        if it%400==0: print(f"    [{it}] cnt={cnt} best={best_cnt} swaps={swaps} rst={rsts}")
    
    if cnt > 0:
        pi_mod[:]=best_pi
    return len(collisions),swaps,rsts


# ===== 主实验 =====
random.seed(12345)
print("="*64)
print("v4: 完整8型碰撞映射 N=74")
print("="*64)
N_val = 74

for trial in range(5):
    print(f"\n--- trial {trial} ---")
    t0 = time.time()
    pi = list(range(N_val)); random.shuffle(pi)
    
    best_cnt = float('inf')
    best_pi, best_carry = None, None
    for _ in range(50):
        carry = [random.choice([0,1,2]) for _ in range(N_val)]
        z = 0
        for i,j,k in itertools.combinations(range(N_val),3):
            yi=pi[i]+carry[i]*N_val; yj=pi[j]+carry[j]*N_val; yk=pi[k]+carry[k]*N_val
            if (j-i)*(yk-yi) == (k-i)*(yj-yi): z+=1
            si=N_val-1-yi; sj=N_val-1-yj; sk=N_val-1-yk
            if (j-i)*(sk-yi) == (k-i)*(yj-yi): z+=1
            if (j-i)*(yk-yi) == (k-i)*(sj-yi): z+=1
            if (j-i)*(yk-si) == (k-i)*(yj-si): z+=1
            if (j-i)*(sk-yi) == (k-i)*(sj-yi): z+=1
            if (j-i)*(sk-si) == (k-i)*(yj-si): z+=1
            if (j-i)*(yk-si) == (k-i)*(sj-si): z+=1
            if (j-i)*(sk-si) == (k-i)*(sj-si): z+=1
        if z<best_cnt: best_cnt,best_pi,best_carry=z,pi.copy(),carry.copy()
        if z==0: break
    
    print(f"  carry: residual={best_cnt} ({time.time()-t0:.1f}s)")
    
    if best_cnt==0:
        # 用完整 NTIL 验证
        pts=[(x,best_pi[x]+best_carry[x]*N_val) for x in range(N_val)]+[(x,N_val-1-(best_pi[x]+best_carry[x]*N_val)) for x in range(N_val)]
        if not any((x2-x1)*(y3-y1)==(x3-x1)*(y2-y1) for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3)):
            print(f"  ★ carry直接解!")
            json.dump({'N':N_val,'pi':best_pi,'carry':best_carry},open('ntil_solution_n74.json','w'),indent=2)
            break
        else:
            best_cnt=999  # false positive
    
    t1=time.time()
    final,swaps,rsts=sa_absorb_v4(best_pi,best_carry,N_val)
    elapsed=time.time()-t1
    
    if final==0:
        # 完整 NTIL 验证
        pts=[(x,best_pi[x]+best_carry[x]*N_val) for x in range(N_val)]+[(x,N_val-1-(best_pi[x]+best_carry[x]*N_val)) for x in range(N_val)]
        ok=not any((x2-x1)*(y3-y1)==(x3-x1)*(y2-y1) for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3))
        if ok:
            print(f"  ★★★ N=74 NTIL 解! swaps={swaps} ({elapsed:.1f}s)")
            json.dump({'N':N_val,'pi':best_pi,'carry':best_carry,'swaps':swaps,'time':elapsed},
                      open('ntil_solution_n74.json','w'),indent=2)
            print(f"  解已保存!")
            break
        else:
            print(f"  ✗ 碰撞0但NTIL失败! 重建映射...")
            # 用完整映射重新进入SA
            collisions = build_full_collision_map(best_pi, best_carry, N_val)
            cnt = len(collisions)
            print(f"    实际冲突数={cnt}，继续SA...")
            final,_,_ = sa_absorb_v4(best_pi, best_carry, N_val, max_iter=16000, patience=400)
            if final == 0:
                pts=[(x,best_pi[x]+best_carry[x]*N_val) for x in range(N_val)]+[(x,N_val-1-(best_pi[x]+best_carry[x]*N_val)) for x in range(N_val)]
                ok=not any((x2-x1)*(y3-y1)==(x3-x1)*(y2-y1) for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3))
                if ok:
                    print(f"  ★★★ N=74 NTIL 解(2nd pass)!")
                    json.dump({'N':N_val,'pi':best_pi,'carry':best_carry},open('ntil_solution_n74.json','w'),indent=2)
                    break
    else:
        print(f"  ✗ final={final} swaps={swaps} ({elapsed:.1f}s)")

print("\n完成.")

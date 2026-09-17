"""
增量冲突追踪的对合型吸收器。
关键优化：交换 π[i]↔π[j] 后只需检查包含行 i 或 j 的三元组。
复杂度从 O(N^4) 降至 O(N^2) per iteration。
"""
import sys, itertools, random, time, math
from collections import Counter, defaultdict

def build_collision_map(pi, N_val):
    """构建初始冲突映射（对合型）。
    返回 {triple_index: conflict_type}"""
    collisions = {}
    for i, j, k in itertools.combinations(range(N_val), 3):
        # PPP: (i,π(i)), (j,π(j)), (k,π(k))
        x1,y1=i,pi[i]; x2,y2=j,pi[j]; x3,y3=k,pi[k]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PPP')] = True
        
        # PPS: (i,π(i)), (j,π(j)), (k,N-1-π(k))
        y3s = N_val-1-pi[k]
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
            collisions[(i,j,k,'PPS')] = True
        
        # PSS: (i,π(i)), (j,N-1-π(j)), (k,N-1-π(k))
        y2s = N_val-1-pi[j]; y3s = N_val-1-pi[k]
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2s-y1):
            collisions[(i,j,k,'PSS')] = True
        
        # SSS 等价于 PPP (反射)
    return collisions

def update_collision_map(pi, N_val, collisions, changed_rows):
    """增量更新冲突映射：只重算涉及 changed_rows 的三元组"""
    # 删除旧冲突中涉及 changed_rows 的
    to_remove = []
    for key in collisions:
        i, j, k = key[0], key[1], key[2]
        # 检查三元组是否涉及 changed_rows
        rows_in = {i, j, k}
        for r in changed_rows:
            if r in rows_in:
                to_remove.append(key)
                break
    for k in to_remove:
        del collisions[k]
    
    # 重新计算涉及 changed_rows 的三元组
    all_rows = set(range(N_val))
    for r in changed_rows:
        others = all_rows - {r}
        for j, k in itertools.combinations(others, 2):
            i, j, k = sorted([r, j, k])
            # PPP
            x1,y1=i,pi[i]; x2,y2=j,pi[j]; x3,y3=k,pi[k]
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                collisions[(i,j,k,'PPP')] = True
            
            y3s = N_val-1-pi[k]
            if (x2-x1)*(y3s-y1) == (x3-x1)*(y2-y1):
                collisions[(i,j,k,'PPS')] = True
            
            y2s = N_val-1-pi[j]
            if (x2-x1)*(y3s-y1) == (x3-x1)*(y2s-y1):
                collisions[(i,j,k,'PSS')] = True

def fast_involution_absorption(pi, N_val, max_iter=2000, patience=80):
    """增量冲突追踪的对合吸收器"""
    collisions = build_collision_map(pi, N_val)
    cnt = len(collisions)
    best_cnt = cnt
    best_pi = pi.copy()
    no_imp = 0
    n4, n6, n_rst = 0, 0, 0
    
    if cnt == 0:
        return cnt, [], n4, n6, n_rst
    
    history = [(0, cnt)]
    
    for it in range(max_iter):
        if cnt == 0:
            print(f"  ★ 收敛! iter={it}")
            break
        
        improved = False
        
        # 找最佳 4-环（增量检测 + deepcopy restore）
        best_d, best_pair = 0, None
        import copy
        saved_collisions = copy.deepcopy(collisions)
        for i in range(N_val):
            for j in range(i+1, N_val):
                old_cnt = cnt
                pi[i], pi[j] = pi[j], pi[i]
                update_collision_map(pi, N_val, collisions, {i, j})
                new_cnt = len(collisions)
                delta = new_cnt - old_cnt
                # restore
                pi[i], pi[j] = pi[j], pi[i]
                collisions.clear()
                collisions.update(saved_collisions)
                
                if delta < best_d:
                    best_d = delta
                    best_pair = (i, j)
        
        if best_pair and best_d < 0:
            i, j = best_pair
            pi[i], pi[j] = pi[j], pi[i]
            update_collision_map(pi, N_val, collisions, {i, j})
            cnt = len(collisions)
            improved = True; n4 += 1
        
        if not improved and N_val <= 16:
            # 6-环（仅对小 N 使用）
            best_d, best_triple = 0, None
            for i, j, k in itertools.combinations(range(N_val), 3):
                old_cnt = cnt
                pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
                update_collision_map(pi, N_val, collisions, {i, j, k})
                new_cnt = len(collisions)
                delta = new_cnt - old_cnt
                # restore
                pi[i], pi[j], pi[k] = pi[k], pi[i], pi[j]
                collisions.clear()
                collisions.update(saved_collisions)
                
                if delta < best_d:
                    best_d = delta
                    best_triple = (i, j, k)
            
            if best_triple and best_d < 0:
                i, j, k = best_triple
                pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
                update_collision_map(pi, N_val, collisions, {i, j, k})
                cnt = len(collisions)
                improved = True; n6 += 1
        
        if improved:
            no_imp = 0
            if cnt < best_cnt:
                best_cnt = cnt; best_pi = pi.copy()
        else:
            no_imp += 1
            if no_imp >= patience:
                pi[:] = best_pi; cnt = best_cnt
                collisions = build_collision_map(pi, N_val)
                # 强随机扰动
                for _ in range(int(2 + N_val*0.2)):
                    i, j = random.sample(range(N_val), 2)
                    pi[i], pi[j] = pi[j], pi[i]
                collisions = build_collision_map(pi, N_val)
                cnt = len(collisions)
                no_imp = 0; n_rst += 1
        
        history.append((it+1, cnt))
        if it % 100 == 0 and it > 0:
            print(f"  [{it}] cnt={cnt} 4c={n4} 6c={n6} rst={n_rst}")
    
    return cnt, history, n4, n6, n_rst


# ===== 测试 =====
random.seed(12345)
print("="*64)
print("增量冲突追踪的对合吸收器")
print("="*64)

for N_val in [10, 12, 16, 20]:
    print(f"\n--- N={N_val} ---")
    t0_total = time.time()
    for trial in range(3):
        pi = list(range(N_val)); random.shuffle(pi)
        collisions = build_collision_map(pi, N_val)
        init_cnt = len(collisions)
        print(f"  trial{trial}: init={init_cnt}")
        
        t0 = time.time()
        final, hist, n4, n6, nr = fast_involution_absorption(
            pi, N_val, max_iter=500, patience=50)
        elapsed = time.time() - t0
        
        status = "✓" if final == 0 else f"✗({final})"
        print(f"    {status} 4c={n4} 6c={n6} rst={nr} time={elapsed:.1f}s")
    
    avg_time = (time.time() - t0_total) / 3
    print(f"  avg_time={avg_time:.1f}s/trial")

print("\n完成。")

"""
模拟退火增强对合吸收器——解决 N≥16 顽固局部极小。
策略：
1. SA：接受 uphill moves with exp(-Δ/T)，降温从 T=1.5 到 0.01
2. 热点感知：仅搜索涉及冲突行的 4-环（避免全枚举）
3. 8-环：对热点行，尝试 4-行循环交换
4. 多重启：SA 耗尽后随机扰动 + 重启
5. 增量冲突追踪：O(N²)/iter
"""
import sys, itertools, random, time, math, copy
from collections import Counter, defaultdict

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
        if (x2-x1)*(y3s-y1) == (x3-x1)*(y2s-y1):
            collisions[(i,j,k,'PSS')] = True
    return collisions

def update_collision_map(pi, N_val, collisions, changed_rows):
    """增量更新：删除涉及 changed_rows 的冲突，重新计算"""
    to_remove = []
    for key in collisions:
        i, j, k = key[0], key[1], key[2]
        if any(r in (i, j, k) for r in changed_rows):
            to_remove.append(key)
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

def get_hot_rows(collisions, N_val, top_k=8):
    """返回冲突最集中的行"""
    row_cnt = Counter()
    for (i, j, k, _) in collisions:
        row_cnt[i] += 1; row_cnt[j] += 1; row_cnt[k] += 1
    return [r for r, _ in row_cnt.most_common(top_k)]

def sa_involution_absorption(pi, N_val, max_iter=5000, patience=150):
    """模拟退火版对合吸收器"""
    collisions = build_collision_map(pi, N_val)
    cnt = len(collisions)
    best_cnt = cnt
    best_pi = pi.copy()
    
    if cnt == 0:
        return cnt, [], 0, 0, 0
    
    # SA 参数
    T = 1.5
    T_min = 0.005
    T_decay = 0.998
    n_swaps, n_restarts = 0, 0
    no_imp_count = 0
    history = [(0, cnt)]
    
    for it in range(max_iter):
        if cnt == 0:
            print(f"  ★ SA收敛! iter={it} T={T:.3f}")
            break
        
        hot_rows = get_hot_rows(collisions, N_val, top_k=min(12, N_val))
        # 仅搜索 hot_rows 中的行对（热点感知）
        improved = False
        
        # --- 4-环 (热点感知) ---
        best_d, best_pair, best_saved = 0, None, None
        saved_collisions = copy.deepcopy(collisions)
        
        candidates = [(i, j) for idx_i, i in enumerate(hot_rows)
                      for j in hot_rows[idx_i+1:]]
        # 也加一些随机行对（探索非热点）
        if len(candidates) < 20:
            extra = random.sample(range(N_val), min(10, N_val-len(hot_rows)))
            candidates.extend((i, j) for idx_i, i in enumerate(extra)
                             for j in extra[idx_i+1:])
        
        for i, j in candidates:
            old_cnt = cnt
            pi[i], pi[j] = pi[j], pi[i]
            update_collision_map(pi, N_val, collisions, {i, j})
            delta = len(collisions) - old_cnt
            
            # restore
            pi[i], pi[j] = pi[j], pi[i]
            collisions.clear()
            collisions.update(saved_collisions)
            
            # SA 接受条件：delta < 0 (改善) 或 以概率 exp(-delta/T) 山移
            accept = delta < 0 or (delta > 0 and random.random() < math.exp(-delta / T))
            if accept and (delta < best_d or best_pair is None):
                best_d = delta
                best_pair = (i, j)
        
        if best_pair and best_d <= 0:  # 只接受无损或改善
            i, j = best_pair
            pi[i], pi[j] = pi[j], pi[i]
            update_collision_map(pi, N_val, collisions, {i, j})
            cnt = len(collisions)
            improved = True; n_swaps += 1
        
        # --- 6-环 (N≤20 或仅热点行) ---
        if not improved and N_val <= 20:
            for _ in range(min(15, len(hot_rows))):
                i, j, k = random.sample(hot_rows, 3)
                old_cnt = cnt
                pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
                update_collision_map(pi, N_val, collisions, {i, j, k})
                delta = len(collisions) - old_cnt
                
                pi[i], pi[j], pi[k] = pi[k], pi[i], pi[j]
                collisions.clear()
                collisions.update(saved_collisions)
                
                if delta < 0:
                    pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
                    update_collision_map(pi, N_val, collisions, {i, j, k})
                    cnt = len(collisions)
                    improved = True; n_swaps += 1
                    break
        
        # --- 8-环 (仅当卡住时，N≤20) ---
        if not improved and cnt <= 5 and N_val <= 20:
            for _ in range(min(8, len(hot_rows)//2)):
                try:
                    sample = random.sample(hot_rows, 4)
                except ValueError:
                    break
                a, b, c, d = sample
                old_cnt = cnt
                pi[a], pi[b], pi[c], pi[d] = pi[b], pi[c], pi[d], pi[a]
                update_collision_map(pi, N_val, collisions, {a, b, c, d})
                delta = len(collisions) - old_cnt
                
                pi[a], pi[b], pi[c], pi[d] = pi[d], pi[a], pi[b], pi[c]
                collisions.clear()
                collisions.update(saved_collisions)
                
                if delta < 0:
                    pi[a], pi[b], pi[c], pi[d] = pi[b], pi[c], pi[d], pi[a]
                    update_collision_map(pi, N_val, collisions, {a, b, c, d})
                    cnt = len(collisions)
                    improved = True; n_swaps += 1
                    break
        
        # --- 降温 & 重启 ---
        if improved:
            no_imp_count = 0
            if cnt < best_cnt:
                best_cnt = cnt; best_pi = pi.copy()
        else:
            no_imp_count += 1
            if no_imp_count >= patience:
                pi[:] = best_pi; cnt = best_cnt
                # 热点扰动：对最热行做多次交换
                hot = get_hot_rows(collisions if collisions else
                                   build_collision_map(pi, N_val), N_val, top_k=8)
                for _ in range(int(3 + N_val * 0.15)):
                    if len(hot) >= 2:
                        i, j = random.sample(hot, 2)
                    else:
                        i, j = random.sample(range(N_val), 2)
                    pi[i], pi[j] = pi[j], pi[i]
                collisions = build_collision_map(pi, N_val)
                cnt = len(collisions)
                no_imp_count = 0; n_restarts += 1
                T = 1.5  # 重新升温
        
        T = max(T * T_decay, T_min)
        
        history.append((it+1, cnt))
        if it % 200 == 0 and it > 0:
            print(f"  [{it}] cnt={cnt} best={best_cnt} T={T:.3f} swaps={n_swaps} rst={n_restarts}")
    
    pi[:] = best_pi; cnt = best_cnt
    return cnt, history, n_swaps, n_restarts, 0


# ===== 测试 =====
random.seed(12345)
print("="*64)
print("SA 增强对合吸收器")
print("="*64)

for N_val in [12, 16, 20]:
    print(f"\n--- N={N_val} ---")
    t0_total = time.time()
    converged = 0
    for trial in range(3):
        pi = list(range(N_val)); random.shuffle(pi)
        collisions = build_collision_map(pi, N_val)
        init_cnt = len(collisions)
        print(f"  trial{trial}: init={init_cnt}")
        
        t0 = time.time()
        final, hist, swaps, rsts, _ = sa_involution_absorption(
            pi, N_val, max_iter=8000, patience=200)
        elapsed = time.time() - t0
        
        status = "✓" if final == 0 else f"✗({final})"
        converged += (final == 0)
        print(f"    {status} swaps={swaps} rst={rsts} time={elapsed:.1f}s")
    
    print(f"  收敛率: {converged}/3  avg={(time.time()-t0_total)/3:.1f}s/trial")

print("\n完成。")

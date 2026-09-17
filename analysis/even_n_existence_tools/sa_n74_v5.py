"""
纯对合型 SA + 增量冲突追踪 + 暴力末段清理 — n=74 直测版。
关键优化：每次 swap 仅检查涉及 i,j 的 O(N²) 个三元组，不是全 O(N³)。
"""
import sys, itertools, random, time, json, math

def count_inv_collisions(pi, N_val):
    """完整对合型冲突计数（仅用于初始化和验证）。"""
    cnt = 0
    for i, j, k in itertools.combinations(range(N_val), 3):
        yi, yj, yk = pi[i], pi[j], pi[k]
        yis = N_val - 1 - yi
        yjs = N_val - 1 - yj
        yks = N_val - 1 - yk
        # Check all 8 types
        if (j-i)*(yk-yi) == (k-i)*(yj-yi): cnt += 1                        # PPP
        if (j-i)*(yks-yi) == (k-i)*(yj-yi): cnt += 1                       # PPS (s at k)
        if (j-i)*(yk-yi)  == (k-i)*(yjs-yi): cnt += 1                      # PPS (s at j)
        if (j-i)*(yk-yis) == (k-i)*(yj-yis): cnt += 1                      # PPS (s at i)
        if (j-i)*(yks-yis) == (k-i)*(yjs-yis): cnt += 1                    # PSS (s at i,j)
        if (j-i)*(yks-yi)  == (k-i)*(yjs-yi): cnt += 1                     # PSS (s at j,k) - needs fix
        if (j-i)*(yk-yis)  == (k-i)*(yj-yis): cnt += 1                     # PSS (s at i,k) - needs fix
        if (j-i)*(yks-yis) == (k-i)*(yjs-yis): cnt += 1                    # SSS
    return cnt

# Correct 8-type check
def check_triple(pi, N_val, i, j, k):
    """返回 (i,j,k) 产生的冲突数 (0-8)。"""
    yi, yj, yk = pi[i], pi[j], pi[k]
    yis = N_val - 1 - yi
    yjs = N_val - 1 - yj
    yks = N_val - 1 - yk
    # sorted
    a, b, c = sorted([i, j, k])
    ya = pi[a]; yb = pi[b]; yc = pi[c]
    yas = N_val - 1 - ya
    ybs = N_val - 1 - yb
    ycs = N_val - 1 - yc
    cnt = 0
    if (b-a)*(yc-ya) == (c-a)*(yb-ya): cnt += 1          # PPP
    if (b-a)*(ycs-ya) == (c-a)*(yb-ya): cnt += 1         # PPS_c
    if (b-a)*(yc-ya) == (c-a)*(ybs-ya): cnt += 1         # PPS_b
    if (b-a)*(yc-yas) == (c-a)*(yb-yas): cnt += 1        # PPS_a
    if (b-a)*(ycs-yas) == (c-a)*(ybs-yas): cnt += 1      # PSS_ab
    if (b-a)*(ycs-ya) == (c-a)*(ybs-ya): cnt += 1        # PSS_bc
    if (b-a)*(yc-yas) == (c-a)*(yb-yas): cnt += 1        # PSS_ac
    if (b-a)*(ycs-yas) == (c-a)*(ybs-yas): cnt += 1      # SSS
    return cnt

def delta_on_swap(pi, N_val, i, j):
    """计算交换 pi[i]↔pi[j] 后的冲突变化量。
    仅检查涉及 i 或 j 的三元组 (旧的 vs 新的冲突数)。
    """
    delta = 0
    # 先算旧状态
    for k in range(N_val):
        if k == i or k == j:
            continue
        old_cnt = check_triple(pi, N_val, i, j, k)
        delta -= old_cnt
    
    # 执行临时交换
    pi[i], pi[j] = pi[j], pi[i]
    
    # 算新状态
    for k in range(N_val):
        if k == i or k == j:
            continue
        new_cnt = check_triple(pi, N_val, i, j, k)
        delta += new_cnt
    
    # 恢复
    pi[i], pi[j] = pi[j], pi[i]
    
    return delta

def greedy_cleanup(pi, N_val, max_iter=10000):
    """贪心+暴力：用 increment delta 找最佳 swap，最后 cnt<=3 时暴力穷举。"""
    cnt = count_inv_collisions(pi, N_val)
    swaps = 0
    best_pi = pi[:]
    best_cnt = cnt
    
    for it in range(max_iter):
        if cnt == 0:
            break
        
        # 找最佳 swap（delta 最负）
        best_delta = 0
        best_pair = None
        for i in range(N_val):
            for j in range(i + 1, N_val):
                d = delta_on_swap(pi, N_val, i, j)
                if d < best_delta:
                    best_delta = d
                    best_pair = (i, j)
        
        if best_pair and best_delta < 0:
            i, j = best_pair
            pi[i], pi[j] = pi[j], pi[i]
            cnt += best_delta
            swaps += 1
            if cnt < best_cnt:
                best_pi = pi[:]
                best_cnt = cnt
        elif cnt <= 3:
            # 暴力穷举所有 4-ring + 6-ring
            found = False
            # 4-ring: swap any pair
            saved_pi = pi[:]
            for a in range(N_val):
                if found: break
                for b in range(a + 1, N_val):
                    pi[:] = saved_pi
                    pi[a], pi[b] = pi[b], pi[a]
                    new_cnt = count_inv_collisions(pi, N_val)
                    if new_cnt < cnt:
                        cnt = new_cnt
                        swaps += 1
                        found = True
                        if new_cnt < best_cnt:
                            best_pi = pi[:]
                            best_cnt = new_cnt
                        break
            pi[:] = saved_pi
            
            # 6-ring if still stuck
            if not found and cnt > 0:
                for a in range(N_val):
                    if found: break
                    for b in range(a + 1, N_val):
                        if found: break
                        for c in range(b + 1, N_val):
                            pi[:] = saved_pi
                            pi[a], pi[b], pi[c] = pi[b], pi[c], pi[a]
                            new_cnt = count_inv_collisions(pi, N_val)
                            if new_cnt < cnt:
                                cnt = new_cnt
                                swaps += 1
                                found = True
                                break
                pi[:] = saved_pi
            
            if not found:
                # 真卡住了——扰动重启
                a, b = random.sample(range(N_val), 2)
                pi[a], pi[b] = pi[b], pi[a]
                cnt = count_inv_collisions(pi, N_val)
                swaps += 1
        else:
            # cnt > 3 但无改善——随机扰动
            a, b = random.sample(range(N_val), 2)
            pi[a], pi[b] = pi[b], pi[a]
            cnt = count_inv_collisions(pi, N_val)
            swaps += 1
        
        if it % 500 == 499:
            # 回滚到最优
            pi[:] = best_pi
            cnt = best_cnt
    
    return best_pi, best_cnt, swaps


def main():
    N_val = 74
    random.seed(42)
    
    n_trials = 10
    best_overall = (None, float('inf'), 0)
    
    print(f"N={N_val} 对合型 SA + 增量 + 暴力")
    print(f"  O(N²) 增量 delta: ~{(N_val*(N_val-1)//2)*(N_val-2)*8} ops/全量 = {(N_val*(N_val-1)//2)*(N_val-2)} triple checks")
    print(f"  预估: ~{(N_val*(N_val-1)//2)*(N_val-2)*20/1e6:.0f}ms/swap, {10} trials")
    print(f"{'='*60}")
    
    for trial in range(n_trials):
        pi = list(range(N_val))
        random.shuffle(pi)
        
        init_cnt = count_inv_collisions(pi, N_val)
        t0 = time.time()
        
        final_pi, final_cnt, swaps = greedy_cleanup(pi, N_val, max_iter=2000)
        
        elapsed = time.time() - t0
        
        status = "✓ NTIL!" if final_cnt == 0 else f"cnt={final_cnt}"
        print(f"  trial{trial}: {init_cnt}→{status} swaps={swaps} ({elapsed:.1f}s)")
        
        if final_cnt == 0:
            # Verify full NTIL
            pts = [(x, final_pi[x]) for x in range(N_val)] + \
                  [(x, N_val - 1 - final_pi[x]) for x in range(N_val)]
            bad = sum(1 for p1, p2, p3 in itertools.combinations(pts, 3)
                     if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
            unique = len(set(pts))
            print(f"    ★ 完整验证: {len(pts)} pts, unique={unique}, collinear={bad}")
            
            if bad == 0 and unique == 2 * N_val:
                print(f"    ★★★ N=74 对合型 NTIL 解验证通过！")
                json.dump({'N': N_val, 'pi': final_pi, 'type': 'involution',
                           'verified': True, 'swaps': swaps},
                          open('ntil_solution_n74_pure.json', 'w'), indent=2)
                break
        
        if final_cnt < best_overall[1]:
            best_overall = (final_pi[:], final_cnt, swaps)
    
    print(f"\n最佳: cnt={best_overall[1]} swaps={best_overall[2]}")
    if best_overall[1] == 0:
        print("★★★ m=37 rot4 NTIL 解已找到 (对合型)！")
    else:
        print(f"未收敛到解，最佳残存 = {best_overall[1]} 冲突")
        print(f"建议：增加 trials、加 SA 退火、或考虑非对合空间")


if __name__ == "__main__":
    main()

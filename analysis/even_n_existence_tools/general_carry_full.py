"""
非对合双排列进位构造：π 和 σ 独立排列，各自进位。
目标：验证去掉 σ=N-1-π 约束后，进位+SA 是否仍有效。
"""
import sys, itertools, random, time, json
from collections import Counter

def full_collision_count_general(pi, sigma, N_val):
    """通用双排列：π 和 σ 独立，检查所有 8 种冲突类型。"""
    cnt = 0
    pts = [(x, pi[x]) for x in range(N_val)] + [(x, sigma[x]) for x in range(N_val)]
    for i1, i2, i3 in itertools.combinations(range(2*N_val), 3):
        x1,y1=pts[i1]; x2,y2=pts[i2]; x3,y3=pts[i3]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            cnt += 1
    return cnt

def carry_phase_general(N_val, attempts=30):
    """通用进位：π 和 σ 独立排列，各自进位。"""
    best = None; best_cnt = float('inf')
    for att in range(attempts):
        pi_mod = list(range(N_val)); random.shuffle(pi_mod)
        sigma_mod = list(range(N_val)); random.shuffle(sigma_mod)
        # 进位
        pi_carry = [random.choice([0,1,2]) for _ in range(N_val)]
        sigma_carry = [random.choice([0,1,2]) for _ in range(N_val)]
        pi_int = [pi_mod[x] + pi_carry[x]*N_val for x in range(N_val)]
        sigma_int = [sigma_mod[x] + sigma_carry[x]*N_val for x in range(N_val)]
        cnt = full_collision_count_general(pi_int, sigma_int, N_val)
        if cnt < best_cnt:
            best_cnt = cnt
            best = (pi_mod, sigma_mod, pi_carry, sigma_carry, pi_int, sigma_int)
    return best, best_cnt

def sa_general(pi_mod, sigma_mod, pi_carry, sigma_carry, N_val, max_iter=5000):
    """通用 SA：交换 π 或 σ 中的两行。"""
    pi_int = [pi_mod[x] + pi_carry[x]*N_val for x in range(N_val)]
    sigma_int = [sigma_mod[x] + sigma_carry[x]*N_val for x in range(N_val)]
    cnt = full_collision_count_general(pi_int, sigma_int, N_val)
    T = 2.0; alpha = 0.995; swaps = 0; rsts = 0
    best_pi = pi_mod[:]; best_sigma = sigma_mod[:]
    best_cnt = cnt
    
    for it in range(max_iter):
        if cnt == 0: break
        # 随机选 π 或 σ 交换
        if random.random() < 0.5:
            i, j = random.sample(range(N_val), 2)
            pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
            pi_int = [pi_mod[x] + pi_carry[x]*N_val for x in range(N_val)]
            new_cnt = full_collision_count_general(pi_int, sigma_int, N_val)
            delta = new_cnt - cnt
            if delta < 0 or random.random() < pow(2.718, -delta/T):
                cnt = new_cnt; swaps += 1
                if cnt < best_cnt:
                    best_pi = pi_mod[:]; best_cnt = cnt
            else:
                pi_mod[i], pi_mod[j] = pi_mod[j], pi_mod[i]
                pi_int = [pi_mod[x] + pi_carry[x]*N_val for x in range(N_val)]
        else:
            i, j = random.sample(range(N_val), 2)
            sigma_mod[i], sigma_mod[j] = sigma_mod[j], sigma_mod[i]
            sigma_int = [sigma_mod[x] + sigma_carry[x]*N_val for x in range(N_val)]
            new_cnt = full_collision_count_general(pi_int, sigma_int, N_val)
            delta = new_cnt - cnt
            if delta < 0 or random.random() < pow(2.718, -delta/T):
                cnt = new_cnt; swaps += 1
                if cnt < best_cnt:
                    best_sigma = sigma_mod[:]; best_cnt = cnt
            else:
                sigma_mod[i], sigma_mod[j] = sigma_mod[j], sigma_mod[i]
                sigma_int = [sigma_mod[x] + sigma_carry[x]*N_val for x in range(N_val)]
        
        T = max(0.05, T*alpha)
        if it % 1000 == 999:
            T = 2.0; rsts += 1
            pi_mod[:] = best_pi[:]; sigma_mod[:] = best_sigma[:]
            pi_int = [pi_mod[x] + pi_carry[x]*N_val for x in range(N_val)]
            sigma_int = [sigma_mod[x] + sigma_carry[x]*N_val for x in range(N_val)]
            cnt = full_collision_count_general(pi_int, sigma_int, N_val)
    
    return best_cnt, swaps, rsts, best_pi, best_sigma

random.seed(42)
print("="*64)
print("非对合双排列进位构造实验")
print("="*64)

results = {}
for N_val in [10, 12, 16, 20, 24]:
    print(f"\n=== N={N_val} ===")
    solved = 0
    for trial in range(5):
        t0 = time.time()
        best, carry_cnt = carry_phase_general(N_val, attempts=30)
        pi_mod, sigma_mod, pi_carry, sigma_carry, pi_int, sigma_int = best
        print(f"  trial{trial}: carry残存={carry_cnt}")
        
        if carry_cnt == 0:
            print(f"    ★ carry直接解!")
            solved += 1
            continue
        
        final_cnt, swaps, rsts, best_pi, best_sigma = sa_general(
            pi_mod[:], sigma_mod[:], pi_carry, sigma_carry, N_val, max_iter=5000)
        elapsed = time.time() - t0
        
        if final_cnt == 0:
            solved += 1
            print(f"    ★ SA解! swaps={swaps} ({elapsed:.1f}s)")
        else:
            print(f"    残存={final_cnt} swaps={swaps} ({elapsed:.1f}s)")
    
    results[N_val] = f"{solved}/5"
    print(f"  收敛率: {solved}/5")

print(f"\n===== 汇总 =====")
for N_val, res in results.items():
    print(f"  N={N_val}: {res}")

"""
自适应进位：先用随机进位，再根据残存冲突的位置分布调整进位值。
核心：冲突热点行的进位值可能是次优的 → 局部重随机化。
"""
import itertools, random, time, math, copy, json
from collections import Counter

def count_int_conflicts(pi, carry, N_val):
    """快速统计整数冲突数"""
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
    return z

def adaptive_carry(pi, N_val, n_global=20, n_adaptive=10):
    """自适应进位：全局随机 + 热点自适应"""
    best_cnt = float('inf')
    best_pi, best_carry = pi.copy(), None
    
    # 阶段1：全局随机
    for _ in range(n_global):
        carry = [random.choice([0, 1, 2]) for _ in range(N_val)]
        cnt = count_int_conflicts(pi, carry, N_val)
        if cnt < best_cnt:
            best_cnt, best_pi, best_carry = cnt, pi.copy(), carry.copy()
    
    if best_cnt <= 5:
        return best_cnt, best_pi, best_carry
    
    # 阶段2：热点自适应
    # 找出残存冲突中涉及的"热点行"
    carry = best_carry.copy()
    hot_rows = Counter()
    for i, j, k in itertools.combinations(range(N_val), 3):
        yi = pi[i] + carry[i]*N_val
        yj = pi[j] + carry[j]*N_val
        yk = pi[k] + carry[k]*N_val
        conflicts = 0
        if (j-i)*(yk-yi) == (k-i)*(yj-yi): conflicts += 1
        yk_s = N_val-1 - (pi[k] + carry[k]*N_val)
        if (j-i)*(yk_s-yi) == (k-i)*(yj-yi): conflicts += 1
        yj_s = N_val-1 - (pi[j] + carry[j]*N_val)
        if (j-i)*(yk_s-yi) == (k-i)*(yj_s-yi): conflicts += 1
        if conflicts > 0:
            hot_rows[i] += conflicts
            hot_rows[j] += conflicts
            hot_rows[k] += conflicts
    
    top_hot = [r for r, _ in hot_rows.most_common(min(20, N_val))]
    
    for _ in range(n_adaptive):
        # 对热点行重新随机化进位
        new_carry = carry.copy()
        for r in top_hot[:10]:  # 重随机化前10个热点
            new_carry[r] = random.choice([0, 1, 2])
        cnt = count_int_conflicts(pi, new_carry, N_val)
        if cnt < best_cnt:
            best_cnt, best_carry = cnt, new_carry.copy()
    
    return best_cnt, pi.copy(), best_carry.copy()


# 测试
random.seed(12345)
print("自适应进位测试 (N=74)")
N_val = 74
pi = list(range(N_val)); random.shuffle(pi)

t0 = time.time()
cnt, pi, carry = adaptive_carry(pi, N_val, n_global=20, n_adaptive=10)
print(f"自适应进位: {cnt} conflicts ({time.time()-t0:.1f}s)")
print(f"进位分布: {Counter(carry).most_common()}")

# 对比纯随机
t0 = time.time()
best = float('inf')
for _ in range(30):
    c = [random.choice([0,1,2]) for _ in range(N_val)]
    z = count_int_conflicts(pi, c, N_val)
    if z < best: best = z
print(f"纯随机30次: {best} conflicts ({time.time()-t0:.1f}s)")
print("完成.")

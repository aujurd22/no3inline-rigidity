"""
非对合双排列进位构造：两独立随机排列 + 进位 + SA 吸收。
σ ≠ N-1-π，完全通用。
"""
import sys, itertools, random, time, math, copy, json
from collections import Counter

def build_double_collision_map(pi, sigma, carry_pi, carry_sigma, N_val):
    """两独立排列的完整 8 型碰撞映射"""
    collisions = {}
    for i, j, k in itertools.combinations(range(N_val), 3):
        pi_i = pi[i] + carry_pi[i]*N_val
        pi_j = pi[j] + carry_pi[j]*N_val
        pi_k = pi[k] + carry_pi[k]*N_val
        si_i = sigma[i] + carry_sigma[i]*N_val
        si_j = sigma[j] + carry_sigma[j]*N_val
        si_k = sigma[k] + carry_sigma[k]*N_val
        
        # PPP: all π
        if (j-i)*(pi_k-pi_i) == (k-i)*(pi_j-pi_i): collisions[(i,j,k,0)]=True
        # SSS: all σ
        if (j-i)*(si_k-si_i) == (k-i)*(si_j-si_i): collisions[(i,j,k,7)]=True
        # PPS×3
        if (j-i)*(si_k-pi_i) == (k-i)*(pi_j-pi_i): collisions[(i,j,k,1)]=True
        if (j-i)*(pi_k-pi_i) == (k-i)*(si_j-pi_i): collisions[(i,j,k,2)]=True
        if (j-i)*(pi_k-si_i) == (k-i)*(pi_j-si_i): collisions[(i,j,k,3)]=True
        # PSS×3
        if (j-i)*(si_k-pi_i) == (k-i)*(si_j-pi_i): collisions[(i,j,k,4)]=True
        if (j-i)*(si_k-si_i) == (k-i)*(pi_j-si_i): collisions[(i,j,k,5)]=True
        if (j-i)*(pi_k-si_i) == (k-i)*(si_j-si_i): collisions[(i,j,k,6)]=True
    return collisions

def update_double_collision_map(pi, sigma, carry_pi, carry_sigma, N_val, collisions, changed_rows):
    to_remove = [key for key in collisions
                 if any(r in (key[0],key[1],key[2]) for r in changed_rows)]
    for k in to_remove: del collisions[k]
    all_rows = set(range(N_val))
    for r in changed_rows:
        others = all_rows - {r}
        for a, b in itertools.combinations(others, 2):
            i, j, k = sorted([r, a, b])
            pi_i = pi[i] + carry_pi[i]*N_val
            pi_j = pi[j] + carry_pi[j]*N_val
            pi_k = pi[k] + carry_pi[k]*N_val
            si_i = sigma[i] + carry_sigma[i]*N_val
            si_j = sigma[j] + carry_sigma[j]*N_val
            si_k = sigma[k] + carry_sigma[k]*N_val
            
            if (j-i)*(pi_k-pi_i) == (k-i)*(pi_j-pi_i): collisions[(i,j,k,0)]=True
            if (j-i)*(si_k-si_i) == (k-i)*(si_j-si_i): collisions[(i,j,k,7)]=True
            if (j-i)*(si_k-pi_i) == (k-i)*(pi_j-pi_i): collisions[(i,j,k,1)]=True
            if (j-i)*(pi_k-pi_i) == (k-i)*(si_j-pi_i): collisions[(i,j,k,2)]=True
            if (j-i)*(pi_k-si_i) == (k-i)*(pi_j-si_i): collisions[(i,j,k,3)]=True
            if (j-i)*(si_k-pi_i) == (k-i)*(si_j-pi_i): collisions[(i,j,k,4)]=True
            if (j-i)*(si_k-si_i) == (k-i)*(pi_j-si_i): collisions[(i,j,k,5)]=True
            if (j-i)*(pi_k-si_i) == (k-i)*(si_j-si_i): collisions[(i,j,k,6)]=True

def count_double_conflicts(pi, sigma, carry_pi, carry_sigma, N_val):
    z = 0
    for i,j,k in itertools.combinations(range(N_val),3):
        pi_i=pi[i]+carry_pi[i]*N_val; pi_j=pi[j]+carry_pi[j]*N_val; pi_k=pi[k]+carry_pi[k]*N_val
        si_i=sigma[i]+carry_sigma[i]*N_val; si_j=sigma[j]+carry_sigma[j]*N_val; si_k=sigma[k]+carry_sigma[k]*N_val
        if (j-i)*(pi_k-pi_i) == (k-i)*(pi_j-pi_i): z+=1
        if (j-i)*(si_k-si_i) == (k-i)*(si_j-si_i): z+=1
        if (j-i)*(si_k-pi_i) == (k-i)*(pi_j-pi_i): z+=1
        if (j-i)*(pi_k-pi_i) == (k-i)*(si_j-pi_i): z+=1
        if (j-i)*(pi_k-si_i) == (k-i)*(pi_j-si_i): z+=1
        if (j-i)*(si_k-pi_i) == (k-i)*(si_j-pi_i): z+=1
        if (j-i)*(si_k-si_i) == (k-i)*(pi_j-si_i): z+=1
        if (j-i)*(pi_k-si_i) == (k-i)*(si_j-si_i): z+=1
    return z

# === 快速测试：N=10 非对合构造 ===
random.seed(42)
N_val = 10
print(f"非对合双排列进位测试 N={N_val}")

pi = list(range(N_val)); sigma = list(range(N_val))
random.shuffle(pi); random.shuffle(sigma)

# 进位搜索
best = float('inf')
best_cp, best_cs = None, None
for _ in range(30):
    cp = [random.choice([0,1,2]) for _ in range(N_val)]
    cs = [random.choice([0,1,2]) for _ in range(N_val)]
    z = count_double_conflicts(pi, sigma, cp, cs, N_val)
    if z < best: best, best_cp, best_cs = z, cp, cs

print(f"初始冲突: {count_double_conflicts(pi, sigma, [0]*N_val, [0]*N_val, N_val)}")
print(f"进位后: {best}")

# 验证是否完整 NTIL
pts = [(x, pi[x]+best_cp[x]*N_val) for x in range(N_val)] + \
      [(x, sigma[x]+best_cs[x]*N_val) for x in range(N_val)]
bad = sum(1 for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts,3)
          if (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1))
print(f"NTIL检查: {bad} 共线 (应为{best})")

print("完成.")

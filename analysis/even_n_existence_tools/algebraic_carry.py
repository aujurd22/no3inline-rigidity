"""
代数进位分析：对合型双排列中"模 N 零行列式→整数非零"的进位机制。
"""
import itertools, random, math, time
from collections import Counter

def integer_carry_check(f_int, N_val):
    """整数公式 f_int(x) 产生 π_int，检查行列式"""
    pi_int = [f_int(x) for x in range(N_val)]
    pi_mod = [v % N_val for v in pi_int]
    if len(set(pi_mod)) < N_val:
        return None, "not_perm"
    
    n_zero = 0
    n_lifted = 0
    for i, j, k in itertools.combinations(range(N_val), 3):
        for (y1f, y2f, y3f) in [
            (lambda x: pi_int[x], lambda x: pi_int[x], lambda x: pi_int[x]),
            (lambda x: pi_int[x], lambda x: pi_int[x], lambda x: N_val-1-pi_int[x]),
            (lambda x: pi_int[x], lambda x: N_val-1-pi_int[x], lambda x: N_val-1-pi_int[x]),
        ]:
            x1,y1=i,y1f(i); x2,y2=j,y2f(j); x3,y3=k,y3f(k)
            det = (x2-x1)*(y3-y1) - (x3-x1)*(y2-y1)
            if det == 0:
                n_zero += 1
            elif det % N_val == 0:
                n_lifted += 1
    return {'n_zero': n_zero, 'n_lifted': n_lifted, 'is_sol': n_zero == 0}, "ok"


print("="*64)
print("实验 1: 线性函数 f(x)=a*x+b (整数)")
print("="*64)
for N_val in [6, 8, 10, 12]:
    print(f"\nN={N_val}:")
    for a in range(1, 10):
        for b in range(0, min(5, N_val)):
            f = lambda x, aa=a, bb=b: aa*x + bb
            res, status = integer_carry_check(f, N_val)
            if status == "ok" and res['n_zero'] <= 3:
                tag = "SOLUTION!" if res['is_sol'] else f"zero={res['n_zero']}"
                print(f"  f(x)={a}x+{b}: {tag} lifted={res['n_lifted']}")

print(f"\n{'='*64}")
print("实验 2: 二次函数 f(x)=ax^2+bx+c (整数)")
print("="*64)
for N_val in [6, 8, 10]:
    print(f"\nN={N_val}:")
    best, bp = float('inf'), None
    for a in range(-3, 4):
        for b in range(-3, 4):
            for c in range(0, min(3, N_val)):
                f = lambda x, aa=a, bb=b, cc=c: aa*x*x + bb*x + cc
                res, st = integer_carry_check(f, N_val)
                if st == "ok":
                    if res['is_sol']:
                        print(f"  SOL: f={a}x^2+{b}x+{c}  lifted={res['n_lifted']}")
                    if res['n_zero'] < best:
                        best, bp = res['n_zero'], (a,b,c)
    if bp:
        print(f"  最佳: f={bp[0]}x^2+{bp[1]}x+{bp[2]}: zero={best}")


print(f"\n{'='*64}")
print("实验 3: 随机整数 π 的进位提升率 vs N")
print("="*64)
random.seed(12345)
for N_val in [8, 10, 12, 16, 20]:
    ratio_sum, n_trials = 0.0, 30
    for _ in range(n_trials):
        pi_mod = list(range(N_val)); random.shuffle(pi_mod)
        pi_int = [pi_mod[i] + random.choice([0,N_val,2*N_val]) for i in range(N_val)]
        nz_mod, nz_lift = 0, 0
        for i,j,k in itertools.combinations(range(N_val),3):
            mx1,my1=i,pi_mod[i]; mx2,my2=j,pi_mod[j]; mx3,my3=k,N_val-1-pi_mod[k]
            md = (mx2-mx1)*(my3-my1) - (mx3-mx1)*(my2-my1)
            if md % N_val == 0:
                nz_mod += 1
                x1,y1=i,pi_int[i]; x2,y2=j,pi_int[j]; x3,y3=k,N_val-1-pi_int[k]
                d = (x2-x1)*(y3-y1) - (x3-x1)*(y2-y1)
                if d != 0: nz_lift += 1
        if nz_mod > 0:
            ratio_sum += nz_lift / nz_mod
    print(f"  N={N_val}: 进位提升率 = {ratio_sum/n_trials:.1%}")


print(f"\n{'='*64}")
print("实验 4: 构造性尝试 — N=10 用模11素数构造 π")
print("="*64)
# 在 mod 11 上构造好排列，然后映射到 N=10 网格
p = 11
N_val = 10
# π(x) = (a*x^2 + b*x) mod p, 然后限制到 [0,9]
for a in range(1, p):
    for b in range(p):
        pi_mod = [(a*x*x + b*x) % p for x in range(N_val)]
        if len(set(pi_mod)) < N_val:
            continue
        # 查冲突
        conflicts = 0
        for i,j,k in itertools.combinations(range(N_val),3):
            for (y1f,y2f,y3f) in [
                (pi_mod, pi_mod, [N_val-1-v for v in pi_mod])
            ]:
                x1,y1=i,y1f[i]; x2,y2=j,y2f[j]; x3,y3=k,y3f[k]
                if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                    conflicts += 1
            break  # only PPS for now
        if conflicts <= 5:
            print(f"  p=11 a={a} b={b}: conflicts={conflicts} pi={pi_mod}")

print("\n完成。")

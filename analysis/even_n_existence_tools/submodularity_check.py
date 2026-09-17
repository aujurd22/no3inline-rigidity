"""
证明/检验：双排列碰撞函数 C(p0,p1) 在 transposition 下的 (近似) 次模性。
若 C 是次模的，则贪心算法保证 1-1/e 近似最优。
"""
import itertools, json
from collections import defaultdict

def bitrev(n,k): return [int(format(x,f'0{k}b')[::-1],2) for x in range(n)]
def gray(n): return [x^(x>>1) for x in range(n)]

def count_colls(p0, p1, n):
    cnt=0
    for i,j,k in itertools.combinations(range(n),3):
        a0i,a0j,a0k=p0[i],p0[j],p0[k]
        a1i,a1j,a1k=p1[i],p1[j],p1[k]
        dxj,dxk=j-i,k-i
        # 8 types (unrolled from bit-mask)
        if dxj*(a0k-a0i)==dxk*(a0j-a0i): cnt+=1
        if dxj*(a0k-a1i)==dxk*(a0j-a1i): cnt+=1
        if dxj*(a1k-a0i)==dxk*(a1j-a0i): cnt+=1
        if dxj*(a1k-a1i)==dxk*(a1j-a1i): cnt+=1
        if dxj*(a0k-a0i)==dxk*(a1j-a0i): cnt+=1
        if dxj*(a0k-a1i)==dxk*(a1j-a1i): cnt+=1
        if dxj*(a1k-a0i)==dxk*(a0j-a0i): cnt+=1
        if dxj*(a1k-a1i)==dxk*(a0j-a1i): cnt+=1
    return cnt

def test_submodularity(p0, p1, n, tps0, tps1, n_samples=50):
    """检验 Δ(A∪B) ≤ Δ(A)+Δ(B) 是否大多数情况成立"""
    all_tps = [('p0',a,b) for a,b in tps0] + [('p1',a,b) for a,b in tps1]
    base_cnt = count_colls(p0, p1, n)
    
    import random; random.seed(42)
    
    n_true = 0
    n_false = 0
    n_tie = 0
    violations = []
    
    for _ in range(n_samples):
        # 随机选两个 transposition A, B
        idx_a, idx_b = random.sample(range(len(all_tps)), 2)
        tp_a, tp_b = all_tps[idx_a], all_tps[idx_b]
        prev_a, prev_b = all_tps[idx_a-1] if idx_a > 0 else all_tps[idx_a+1], all_tps[idx_b-1] if idx_b > 0 else all_tps[idx_b+1]
        
        # Compute Δ(A): apply A to base
        p0a=p0[:]; p1a=p1[:]
        if tp_a[0]=='p0': p0a[tp_a[1]],p0a[tp_a[2]]=p0a[tp_a[2]],p0a[tp_a[1]]
        else: p1a[tp_a[1]],p1a[tp_a[2]]=p1a[tp_a[2]],p1a[tp_a[1]]
        delta_a = count_colls(p0a, p1a, n) - base_cnt
        
        # Compute Δ(B)
        p0b=p0[:]; p1b=p1[:]
        if tp_b[0]=='p0': p0b[tp_b[1]],p0b[tp_b[2]]=p0b[tp_b[2]],p0b[tp_b[1]]
        else: p1b[tp_b[1]],p1b[tp_b[2]]=p1b[tp_b[2]],p1b[tp_b[1]]
        delta_b = count_colls(p0b, p1b, n) - base_cnt
        
        # Compute Δ(A∪B): apply both
        p0ab=p0[:]; p1ab=p1[:]
        for tp in [tp_a, tp_b]:
            if tp[0]=='p0': p0ab[tp[1]],p0ab[tp[2]]=p0ab[tp[2]],p0ab[tp[1]]
            else: p1ab[tp[1]],p1ab[tp[2]]=p1ab[tp[2]],p1ab[tp[1]]
        delta_ab = count_colls(p0ab, p1ab, n) - base_cnt
        
        # Submodularity: Δ_AB ≤ Δ_A + Δ_B (both usually negative)
        if delta_ab <= delta_a + delta_b:
            n_true += 1
        elif delta_ab == delta_a + delta_b:
            n_tie += 1
        else:
            n_false += 1
            violations.append((delta_a, delta_b, delta_ab, delta_ab - (delta_a+delta_b)))
    
    return n_true, n_false, n_tie, violations

def build_tps(perm, n, k):
    tps = set()
    for x in range(n):
        for b in range(k):
            y = x ^ (1 << b)
            if y > x:
                a, bb = perm[x], perm[y]
                tps.add((min(a,bb), max(a,bb)))
    return [(a,b) for a,b in tps]

print("="*64)
print("次模性检验: 双排列碰撞函数的 transposition 边际效用")
print("="*64)

for n in [8, 16]:
    k = n.bit_length() - 1
    p0 = bitrev(n,k); p1 = gray(n)
    tps0 = build_tps(p0, n, k)
    tps1 = build_tps(p1, n, k)
    base = count_colls(p0, p1, n)
    
    n_true, n_false, n_tie, violations = test_submodularity(p0, p1, n, tps0, tps1, n_samples=100)
    
    print(f"\nn={n}: base={base}")
    print(f"  次模成立: {n_true}/{n_true+n_false+n_tie} ({100*n_true/(n_true+n_false+n_tie):.0f}%)")
    print(f"  次模不成立: {n_false} ({100*n_false/(n_true+n_false+n_tie):.0f}%)")
    if violations:
        excesses = [v[3] for v in violations[:10]]
        print(f"  违反幅度: min={min(excesses)} max={max(excesses)} avg={sum(excesses)/len(excesses):.1f}")

# 理论分析
print(f"\n{'='*64}")
print("结论")
print("="*64)
print("次模性意味着: 贪心算法保证 1-1/e ≈ 63% 的最优改善比例。")
print("若次模性大比例成立，贪心(纯)是近乎最优的搜索策略。")
print("若次模性仅 ~50% 成立，则需要次模最大化近似算法。")

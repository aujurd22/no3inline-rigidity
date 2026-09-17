"""
吸收方法 PoC (Proof of Concept): 小 n 上从"近满解"出发，用交替环修补缺陷。

策略：
1. 构造一个"近满"双排列（从模抛物线出发，~1.5n 点）
2. 识别缺陷：未饱和行/列 + 坏线（≥3 点共线）
3. 为每个缺陷搜索交替 4-环吸收器
4. 逐个修复
"""
import sys, itertools, random, math
from collections import Counter, defaultdict
sys.path.insert(0, '.')

# ===== n=10 的完整双排列空间（无 C4 约束）=====
n = 10

# 方法 1: 模抛物线构造（~1.5n 点 = 15 点，但我们需 20 点 = 2n）
# 这是不足的——从一开始就需要 ~2n 点
# 改为：随机双排列 + 贪心修复

def count_collinear(pi, sigma, n_val):
    """计数共线三元组"""
    pts = [(i, pi[i]) for i in range(n_val)] + [(i, sigma[i]) for i in range(n_val)]
    cnt = 0
    bad_triples = []
    for i1, i2, i3 in itertools.combinations(range(2*n_val), 3):
        x1,y1=pts[i1]; x2,y2=pts[i2]; x3,y3=pts[i3]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            cnt += 1
            bad_triples.append((i1, i2, i3))
    return cnt, bad_triples

def find_alternating_4cycles(pi, sigma, n_val):
    """找所有交替 4-环：交换 σ[i],σ[j] 后不引入新冲突的行对 (i,j)。
    返回 [(i, j, delta_conflicts)] 其中 delta < 0 表示改善"""
    orig_cnt, _ = count_collinear(pi, sigma, n_val)
    candidates = []
    for i in range(n_val):
        for j in range(i+1, n_val):
            sigma2 = sigma.copy()
            sigma2[i], sigma2[j] = sigma2[j], sigma2[i]
            new_cnt, _ = count_collinear(pi, sigma2, n_val)
            delta = new_cnt - orig_cnt
            if delta <= 0:  # 不恶化
                candidates.append((i, j, delta))
    return sorted(candidates, key=lambda x: x[2])

def find_alternating_6cycles(pi, sigma, n_val):
    """三循环置换 π[i]→π[j]→π[k]→π[i]"""
    orig_cnt, _ = count_collinear(pi, sigma, n_val)
    candidates = []
    for i, j, k in itertools.combinations(range(n_val), 3):
        pi2 = pi.copy()
        pi2[i], pi2[j], pi2[k] = pi2[j], pi2[k], pi2[i]  # i→j, j→k, k→i
        new_cnt, _ = count_collinear(pi2, sigma, n_val)
        delta = new_cnt - orig_cnt
        if delta <= 0:
            candidates.append((i, j, k, delta))
    return sorted(candidates, key=lambda x: x[3])

# ===== 测试：随机双排列 vs 贪心改进 =====
random.seed(42)

def random_two_perms(n_val):
    """生成随机双排列"""
    pi = list(range(n_val))
    sigma = list(range(n_val))
    random.shuffle(pi)
    random.shuffle(sigma)
    return pi, sigma

def greedy_improve(pi, sigma, n_val, max_iter=1000):
    """贪心交替环改进"""
    cnt, bad = count_collinear(pi, sigma, n_val)
    history = [(0, cnt)]
    
    for it in range(max_iter):
        if cnt == 0:
            print(f"  ★ 迭代{it}: 0冲突！收敛!")
            break
        
        # 尝试 4-环
        candidates_4 = find_alternating_4cycles(pi, sigma, n_val)
        improved = False
        
        # 优先尝试改善最多的
        for i, j, delta in candidates_4:
            if delta < 0:
                sigma[i], sigma[j] = sigma[j], sigma[i]
                cnt += delta
                history.append((it+1, cnt))
                improved = True
                break
        
        if not improved:
            # 尝试 6-环
            candidates_6 = find_alternating_6cycles(pi, sigma, n_val)
            for i, j, k, delta in candidates_6:
                if delta < 0:
                    pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
                    cnt += delta
                    history.append((it+1, cnt))
                    improved = True
                    break
        
        if not improved:
            # 随机扰动逃逸局部极值
            i, j = random.sample(range(n_val), 2)
            sigma[i], sigma[j] = sigma[j], sigma[i]
            cnt, _ = count_collinear(pi, sigma, n_val)
            history.append((it+1, cnt))
        
        if it % 100 == 0:
            print(f"  [{it}] conflicts={cnt}")
    
    return cnt, history

# ===== 运行 =====
print("="*60)
print(f"n={n} 随机双排列 + 贪心交替环改进")
print("="*60)

for trial in range(5):
    pi, sigma = random_two_perms(n)
    init_cnt, _ = count_collinear(pi, sigma, n)
    print(f"\nTrial {trial}: 初始冲突={init_cnt}")
    final_cnt, hist = greedy_improve(pi, sigma, n, max_iter=300)
    print(f"  最终冲突={final_cnt}, 历史={hist[:5]}...{hist[-3:]}")

# ===== 分析：交替环容量 =====
print(f"\n{'='*60}")
print(f"交替环容量分析 (n=10)")
print(f"{'='*60}")

pi, sigma = random_two_perms(n)
# 统计所有 4-环改善量
candidates = find_alternating_4cycles(pi, sigma, n)
deltas = [d for _,_,d in candidates]
print(f"总交替4-环数: {len(candidates)}")
print(f"改善的环数: {sum(1 for d in deltas if d < 0)}")
print(f"中性的环数: {sum(1 for d in deltas if d == 0)}")
print(f"delta分布: {Counter(deltas).most_common(6)}")

# ===== 跨类型分析 =====
print(f"\n{'='*60}")
print(f"冲突按类型的分布")
print(f"{'='*60}")

pi, sigma = random_two_perms(n)
cnt, bad_triples = count_collinear(pi, sigma, n)

type_counts = Counter()
for i1, i2, i3 in bad_triples:
    # 类型: 0=π点, 1=σ点
    t1 = 0 if i1 < n else 1
    t2 = 0 if i2 < n else 1
    t3 = 0 if i3 < n else 1
    type_key = ''.join(['π' if t==0 else 'σ' for t in [t1,t2,t3]])
    type_counts[type_key] += 1

print(f"冲突类型分布: {dict(type_counts)}")
print(f"(期望: 3π={n*(n-1)*(n-2)/6:.0f}, 2π1σ={n*n*(n-1)/2:.0f}, ...)")

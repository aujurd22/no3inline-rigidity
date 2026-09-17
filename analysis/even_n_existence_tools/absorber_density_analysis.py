"""
吸收器密度分析：随 n 增长，交替 4-环中改善冲突的比例如何变化？
这直接决定多尺度吸收策略的可行性。
"""
import sys, itertools, random, time
from collections import Counter, defaultdict
sys.path.insert(0, '.')

def count_collinear_fast(pi, sigma, n_val):
    """快速计数共线三元组（增量版本——只计算涉及特定行的冲突）"""
    pts = [(i, pi[i]) for i in range(n_val)] + [(i, sigma[i]) for i in range(n_val)]
    cnt = 0
    for i1, i2, i3 in itertools.combinations(range(2*n_val), 3):
        x1,y1=pts[i1]; x2,y2=pts[i2]; x3,y3=pts[i3]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            cnt += 1
    return cnt

def absorber_density(n_val, n_samples=5):
    """对给定 n，采样随机双排列，统计交替 4-环的吸收器密度"""
    results = []
    for trial in range(n_samples):
        pi = list(range(n_val)); sigma = list(range(n_val))
        random.shuffle(pi); random.shuffle(sigma)
        
        orig = count_collinear_fast(pi, sigma, n_val)
        
        # 采样 100 个随机行对，检查交替效果
        n_pairs = min(100, n_val*(n_val-1)//2)
        pairs = random.sample(
            [(i,j) for i in range(n_val) for j in range(i+1, n_val)],
            n_pairs
        )
        
        improvements = 0
        neutral = 0
        degradations = 0
        
        for i, j in pairs:
            sigma[i], sigma[j] = sigma[j], sigma[i]
            new_cnt = count_collinear_fast(pi, sigma, n_val)
            sigma[i], sigma[j] = sigma[j], sigma[i]  # restore
            
            delta = new_cnt - orig
            if delta < 0: improvements += 1
            elif delta == 0: neutral += 1
            else: degradations += 1
        
        results.append({
            'n': n_val, 'trial': trial,
            'orig_conflicts': orig,
            'n_pairs': n_pairs,
            'improvements': improvements,
            'neutral': neutral,
            'degradations': degradations,
            'improve_rate': improvements / n_pairs,
        })
        print(f"  n={n_val} trial{trial}: conflicts={orig} improve_rate={improvements/n_pairs:.3f} "
              f"({improvements}/{neutral}/{degradations})")
    
    avg_rate = sum(r['improve_rate'] for r in results) / len(results)
    avg_conf = sum(r['orig_conflicts'] for r in results) / len(results)
    print(f"  => n={n_val}: avg_improve_rate={avg_rate:.3f}, avg_conflicts={avg_conf:.0f}\n")
    return avg_rate, avg_conf

random.seed(12345)

print("="*60)
print("吸收器密度 vs n")
print("="*60)
print()

rates = {}
for n_val in [6, 8, 10, 12, 14]:
    t0 = time.time()
    rate, conf = absorber_density(n_val, n_samples=3)
    rates[n_val] = {'rate': rate, 'conflicts': conf, 'time': time.time()-t0}

print("="*60)
print("汇总")
print("="*60)
for n_val in sorted(rates.keys()):
    r = rates[n_val]
    print(f"  n={n_val}: improve_rate={r['rate']:.3f} conflicts={r['conflicts']:.0f} time={r['time']:.1f}s")

# 拟合：吸收率是否随 n 衰减？
if len(rates) >= 3:
    import math
    xs = sorted(rates.keys())
    ys = [rates[x]['rate'] for x in xs]
    print(f"\n衰减趋势: n={xs}, rates={[f'{y:.3f}' for y in ys]}")
    # 简单线性回归
    n_mean = sum(xs)/len(xs)
    y_mean = sum(ys)/len(ys)
    slope = sum((x-n_mean)*(y-y_mean) for x,y in zip(xs, ys)) / sum((x-n_mean)**2 for x in xs)
    print(f"  线性衰减斜率: {slope:.4f}/n")
    if slope < 0:
        # 预测 n=74 的吸收率
        pred_74 = y_mean + slope * (74 - n_mean)
        print(f"  预测 n=74: improve_rate ≈ {max(0, pred_74):.3f}")
        # 预测 n=74 时的冲突数（假设 ~O(n²) 增长）
        cs = [rates[x]['conflicts'] for x in xs]
        # c ≈ a * n^2
        a_vals = [c/(x*x) for x,c in zip(xs, cs)]
        a_mean = sum(a_vals)/len(a_vals)
        pred_conf_74 = a_mean * 74 * 74
        print(f"  预测 n=74: conflicts ≈ {pred_conf_74:.0f}")
        # 每次交换的平均改善量
        avg_improve = (pred_conf_74 - 0) / (pred_74 * 74*73//2) if pred_74 > 0 else float('inf')
        print(f"  所需吸收器数 ≈ {pred_conf_74 / (-slope * 74):.0f} (粗略)")

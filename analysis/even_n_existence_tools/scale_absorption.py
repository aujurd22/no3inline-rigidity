"""
多尺度吸收器缩放实验：n=12→16→24，4-环+6-环+随机重启。
测量：吸收器需求量增长、冲突类型分布、外推 n=74。
"""
import sys, itertools, random, time, math
from collections import Counter, defaultdict
sys.path.insert(0, '.')

def count_collinear_fast(pi, sigma, n_val):
    pts = [(i, pi[i]) for i in range(n_val)] + [(i, sigma[i]) for i in range(n_val)]
    cnt = 0
    for i1, i2, i3 in itertools.combinations(range(2*n_val), 3):
        x1,y1=pts[i1]; x2,y2=pts[i2]; x3,y3=pts[i3]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            cnt += 1
    return cnt

def find_best_4cycle(pi, sigma, n_val, orig_cnt):
    """找最佳交替 4-环（σ[i]↔σ[j]）"""
    best_delta, best_pair = 0, None
    for i in range(n_val):
        for j in range(i+1, n_val):
            sigma[i], sigma[j] = sigma[j], sigma[i]
            new_cnt = count_collinear_fast(pi, sigma, n_val)
            sigma[i], sigma[j] = sigma[j], sigma[i]
            delta = new_cnt - orig_cnt
            if delta < best_delta:
                best_delta = delta
                best_pair = (i, j)
    return best_pair, best_delta

def find_best_6cycle(pi, sigma, n_val, orig_cnt):
    """找最佳交替 6-环（π 上三循环）"""
    best_delta, best_triple = 0, None
    for i, j, k in itertools.combinations(range(n_val), 3):
        pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
        new_cnt = count_collinear_fast(pi, sigma, n_val)
        pi[i], pi[j], pi[k] = pi[k], pi[i], pi[j]  # restore: k→i, i→j, j→k
        delta = new_cnt - orig_cnt
        if delta < best_delta:
            best_delta = delta
            best_triple = (i, j, k)
    return best_triple, best_delta

def greedy_improve_enhanced(pi, sigma, n_val, max_iter=500, patience=50):
    """增强贪心：4-环 + 6-环 + 智能重启"""
    cnt = count_collinear_fast(pi, sigma, n_val)
    history = [(0, cnt)]
    best_cnt = cnt
    best_state = (pi.copy(), sigma.copy())
    no_improve = 0
    total_4cycles = 0
    total_6cycles = 0
    total_restarts = 0

    for it in range(max_iter):
        if cnt == 0:
            print(f"  ★ 收敛! iter={it}")
            break

        improved = False

        # 4-环（更便宜，先试）
        pair, d4 = find_best_4cycle(pi, sigma, n_val, cnt)
        if d4 < 0:
            i, j = pair
            sigma[i], sigma[j] = sigma[j], sigma[i]
            cnt += d4
            improved = True
            total_4cycles += 1

        if not improved:
            # 6-环
            triple, d6 = find_best_6cycle(pi, sigma, n_val, cnt)
            if d6 < 0:
                i, j, k = triple
                pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
                cnt += d6
                improved = True
                total_6cycles += 1

        if improved:
            no_improve = 0
            if cnt < best_cnt:
                best_cnt = cnt
                best_state = (pi.copy(), sigma.copy())
        else:
            no_improve += 1
            if no_improve >= patience:
                # 智能重启：回最佳状态 + 随机多步扰动
                pi[:], sigma[:] = best_state
                cnt = best_cnt
                # 多步随机交换打破局部极值
                for _ in range(int(2 + n_val * 0.1)):
                    i, j = random.sample(range(n_val), 2)
                    sigma[i], sigma[j] = sigma[j], sigma[i]
                cnt = count_collinear_fast(pi, sigma, n_val)
                no_improve = 0
                total_restarts += 1

        history.append((it+1, cnt))
        if it % 50 == 0 and it > 0:
            print(f"  [{it}] cnt={cnt} 4c={total_4cycles} 6c={total_6cycles} rst={total_restarts}")

    return cnt, history, total_4cycles, total_6cycles, total_restarts

def analyze_conflict_types(pi, sigma, n_val):
    """分析冲突类型分布：πππ, ππσ, πσσ, σσσ, 以及涉及的斜率"""
    pts = [(i, pi[i]) for i in range(n_val)] + [(i, sigma[i]) for i in range(n_val)]
    type_cnt = Counter()
    slope_cnt = Counter()

    for i1, i2, i3 in itertools.combinations(range(2*n_val), 3):
        x1,y1=pts[i1]; x2,y2=pts[i2]; x3,y3=pts[i3]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            t1 = 0 if i1 < n_val else 1
            t2 = 0 if i2 < n_val else 1
            t3 = 0 if i3 < n_val else 1
            type_key = ''.join(['P' if t==0 else 'S' for t in sorted([t1,t2,t3])])
            type_cnt[type_key] += 1
            # 斜率
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0:
                key = "inf"
            else:
                g = math.gcd(abs(dx), abs(dy))
                key = f"{dy//g}/{dx//g}"
            slope_cnt[key] += 1
    return type_cnt, slope_cnt


# ===== 主实验 =====
random.seed(12345)

print("=" * 64)
print("多尺度吸收器缩放实验")
print("=" * 64)

results = {}

for n_val in [8, 10, 12, 16]:
    print(f"\n{'='*64}")
    print(f"n = {n_val}")
    print(f"{'='*64}")

    n_trials = 4 if n_val <= 12 else 3
    trial_results = []

    for trial in range(n_trials):
        pi = list(range(n_val)); sigma = list(range(n_val))
        random.shuffle(pi); random.shuffle(sigma)

        init_cnt = count_collinear_fast(pi, sigma, n_val)
        print(f"\nTrial {trial}: init_conflicts={init_cnt}")

        t0 = time.time()
        final_cnt, hist, n4, n6, nr = greedy_improve_enhanced(
            pi, sigma, n_val,
            max_iter=300 if n_val <= 12 else 200,
            patience=30 if n_val <= 12 else 20
        )
        elapsed = time.time() - t0

        types, slopes = analyze_conflict_types(pi, sigma, n_val)

        r = {
            'n': n_val, 'trial': trial,
            'init_conflicts': init_cnt,
            'final_conflicts': final_cnt,
            'n_4cycles': n4, 'n_6cycles': n6,
            'n_restarts': nr,
            'time': elapsed,
            'conflict_types': dict(types.most_common(5)),
            'top_slopes': dict(slopes.most_common(5)),
        }
        trial_results.append(r)

        improvement = init_cnt - final_cnt
        total_absorbers = n4 + n6
        avg_improve = improvement / max(total_absorbers, 1)
        print(f"  Final: {final_cnt} ({improvement}↓), absorbers={total_absorbers}, "
              f"avg_improve={avg_improve:.1f}/absorber, time={elapsed:.0f}s")

    results[n_val] = trial_results

# ===== 汇总 + 外推 =====
print(f"\n{'='*64}")
print("汇总 + 外推 n=74")
print(f"{'='*64}")

import json
json.dump(results, open("scale_absorption_results.json", "w"), indent=2, default=str)

for n_val in sorted(results.keys()):
    rs = results[n_val]
    avg_init = sum(r['init_conflicts'] for r in rs) / len(rs)
    avg_final = sum(r['final_conflicts'] for r in rs) / len(rs)
    avg_abs = sum(r['n_4cycles']+r['n_6cycles'] for r in rs) / len(rs)
    avg_time = sum(r['time'] for r in rs) / len(rs)
    print(f"n={n_val:2d}: init={avg_init:.0f} final={avg_final:.0f} "
          f"absorbers={avg_abs:.0f} time={avg_time:.0f}s")

# 外推
ns = sorted(results.keys())
init_counts = [sum(r['init_conflicts'] for r in results[n]) / len(results[n]) for n in ns]
absorber_counts = [sum(r['n_4cycles']+r['n_6cycles'] for r in results[n]) / len(results[n]) for n in ns]

# 拟合：absorbers ≈ a * n^2 (冲突数增长 ~ n^2)
log_n = [math.log(n) for n in ns]
log_abs = [math.log(a) for a in absorber_counts]
n_mean = sum(log_n) / len(log_n)
a_mean = sum(log_abs) / len(log_abs)
slope = sum((x-n_mean)*(y-a_mean) for x,y in zip(log_n, log_abs)) / sum((x-n_mean)**2 for x in log_n)

print(f"\n=== 外推 ===")
print(f"absorbers ~ n^{slope:.2f}")
pred_74 = math.exp(a_mean + slope * (math.log(74) - n_mean))
print(f"预测 n=74 所需吸收器: ~{pred_74:.0f}")
print(f"预测 n=74 初始冲突: ~{sum(init_counts)/len(init_counts) / (sum(ns)/len(ns))**2 * 74**2:.0f}")

# 冲突类型聚合
print(f"\n=== 冲突类型分布 (聚合) ===")
all_types = Counter()
for n_val in sorted(results.keys()):
    for r in results[n_val]:
        for t, c in r['conflict_types'].items():
            all_types[t] += c
total_conf = sum(all_types.values())
for t, c in all_types.most_common():
    print(f"  {t}: {c} ({100*c/total_conf:.0f}%)")

print("\n完成。结果保存在 scale_absorption_results.json")

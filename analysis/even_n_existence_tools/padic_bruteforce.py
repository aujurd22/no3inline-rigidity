"""暴力穷举 MSB transposition 子集——决定性实验。n=8: 2^4=16, n=16: 2^8=256。"""
import itertools, math, json, time

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]
def gray(n):
    return [x ^ (x >> 1) for x in range(n)]

def count_collinear(pi0, pi1, n):
    pts = [(i, pi0[i]) for i in range(n)] + [(i, pi1[i]) for i in range(n)]
    return sum(1 for p1,p2,p3 in itertools.combinations(pts, 3)
               if (p2[0]-p1[0])*(p3[1]-p1[1])==(p3[0]-p1[0])*(p2[1]-p1[1]))

def msb_transpositions(n, k):
    """所有 n/2 个 MSB transposition: y ↔ y XOR 2^(k-1)"""
    msb = 1 << (k - 1)
    tps = []
    for y in range(n // 2):
        # x 空间位置: a = bitrev(y), b = bitrev(y XOR msb)
        a = int(format(y, f'0{k}b')[::-1], 2)
        b = int(format(y ^ msb, f'0{k}b')[::-1], 2)
        tps.append((min(a, b), max(a, b)))
    # 去重后应该恰好 n/2 个
    return sorted(set(tps))

def apply_transpositions(p0, transpositions):
    """执行一组 transposition（交换 p[a]↔p[b]）"""
    p = p0[:]
    for a, b in transpositions:
        p[a], p[b] = p[b], p[a]
    return p

def find_optimal_subset(p0_orig, p1, n, k):
    """暴力穷举所有 transposition 子集，找最少零行列式"""
    all_tps = msb_transpositions(n, k)
    best_cnt = float('inf')
    best_subset = None
    best_p0 = None

    for mask in range(1 << len(all_tps)):
        subset = [all_tps[i] for i in range(len(all_tps)) if (mask >> i) & 1]
        p0_mod = apply_transpositions(p0_orig, subset)
        cnt = count_collinear(p0_mod, p1, n)

        if cnt < best_cnt:
            best_cnt = cnt
            best_subset = subset
            best_p0 = p0_mod

    return best_cnt, best_subset, best_p0

print("=" * 64)
print("暴力穷举 MSB transposition 子集")
print("=" * 64)

for n in [8, 16, 32]:
    k = int(math.log2(n))
    p0 = bitrev(n, k)
    p1 = gray(n)

    n_tps = len(msb_transpositions(n, k))
    n_combos = 1 << n_tps

    print(f"\nn={n} (k={k}): transpositions={n_tps}, combinations={n_combos}")

    if n_combos > 500000:
        print(f"  组合太多 ({n_combos})，用贪心退火替代...")
        # 随机爬山
        import random
        random.seed(42)
        best_cnt = count_collinear(p0, p1, n)
        best_p0 = p0[:]
        best_subset = []

        for restart in range(20):
            # 初始随机子集
            cur_p0 = p0[:]
            cur_subset = []
            cur_cnt = best_cnt

            for iteration in range(5000):
                # 随机翻转一个 transposition
                tp_idx = random.randrange(n_tps)
                a, b = msb_transpositions(n, k)[tp_idx]

                # 尝试翻转
                cur_p0[a], cur_p0[b] = cur_p0[b], cur_p0[a]
                new_cnt = count_collinear(cur_p0, p1, n)

                if new_cnt <= cur_cnt or random.random() < 0.01:
                    cur_cnt = new_cnt
                    if (a, b) in cur_subset:
                        cur_subset.remove((a, b))
                    else:
                        cur_subset.append((a, b))

                    if cur_cnt < best_cnt:
                        best_cnt = cur_cnt
                        best_p0 = cur_p0[:]
                        best_subset = cur_subset[:]
                        print(f"    restart{restart} iter{iteration}: cnt={best_cnt}")
                else:
                    cur_p0[a], cur_p0[b] = cur_p0[b], cur_p0[a]

            if best_cnt == 0:
                break

        print(f"  爬山结果: best_cnt={best_cnt}")
    else:
        best_cnt, best_subset, best_p0 = find_optimal_subset(p0, p1, n, k)
        print(f"  最优: {len(best_subset)} transpositions, {best_cnt} collinear triples")

    is_solution = (best_cnt == 0)
    if is_solution:
        print(f"  ★★★ n={n} NTIL 解找到！")
    print(f"  Transpositions used: {best_subset if len(str(best_subset)) < 200 else f'{len(best_subset)} total'}")

    # 保存结果
    if is_solution:
        json.dump({
            'n': n, 'k': k,
            'p0': best_p0, 'p1': p1,
            'transpositions': best_subset,
            'source': 'msb_bruteforce'
        }, open(f'ntil_n{n}_padic_brute.json', 'w'), indent=2)

print("\n" + "=" * 64)
print("[THEOREM] 若任意 n=2^k 存在 transposition 子集消除所有共线→完整无穷族构造")
print("=" * 64)

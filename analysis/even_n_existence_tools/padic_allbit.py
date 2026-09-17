"""
扩展穷举：所有 k 个位的 transposition 组合。
n=8: k=3, 12 transpositions → 2^12=4096 combos (穷举可行)
n=16: k=4, 32 transpositions → 2^32 太大，用爬山

[math-skill-audit] 审计要点：
1. transposition 独立性：不同位的 transposition 可交换（作用于不同输出值的不同位）
2. 但同一个值的不同位翻转会复合 → XOR 组合产生新的 transposition 效应
3. 关键检验：是否存在 ALL-bit transposition 子集使 NTIL=0
"""
import itertools, math, json, time, random
from collections import Counter

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]

def gray(n):
    return [x ^ (x >> 1) for x in range(n)]

def count_collinear(pi0, pi1, n):
    pts = [(i, pi0[i]) for i in range(n)] + [(i, pi1[i]) for i in range(n)]
    return sum(1 for p1,p2,p3 in itertools.combinations(pts, 3)
               if (p2[0]-p1[0])*(p3[1]-p1[1])==(p3[0]-p1[0])*(p2[1]-p1[1]))

def all_transpositions(n, k):
    """所有 k 个位的 transposition 集合。
    对每个位 b (0..k-1) 和每个 y < n/2 且 y 的第 b 位 = 0:
        交换位置 bitrev(y) 和 bitrev(y XOR 2^b) 上的值
    """
    tps_by_bit = {}
    for b in range(k):
        mask = 1 << b
        bit_tps = set()
        for y in range(n):
            if (y & mask) == 0:  # 仅对第 b 位 = 0 的 y
                a = int(format(y, f'0{k}b')[::-1], 2)
                b_val = int(format(y ^ mask, f'0{k}b')[::-1], 2)
                bit_tps.add((min(a, b_val), max(a, b_val)))
        # 去重后应为 n/2 个
        sorted_tps = sorted(bit_tps)
        tps_by_bit[b] = sorted_tps

    # 展平为统一列表
    all_tps = []
    tp_index = []
    for b in range(k):
        for tp in tps_by_bit[b]:
            all_tps.append(tp)
            tp_index.append(b)
    return all_tps, tp_index

def apply_subset(p0_orig, all_tps, subset_mask):
    """应用 transposition 子集。subset_mask 是整数，每一位控制一个 transposition"""
    p = p0_orig[:]
    for i in range(len(all_tps)):
        if (subset_mask >> i) & 1:
            a, b = all_tps[i]
            p[a], p[b] = p[b], p[a]
    return p

print("=" * 64)
print("ALL-bit MSB transposition 穷举 (n=8,16)")
print("=" * 64)

for n in [8, 16]:
    k = int(math.log2(n))
    p0 = bitrev(n, k)
    p1 = gray(n)

    all_tps, tp_index = all_transpositions(n, k)
    n_tps = len(all_tps)
    n_combos = 1 << n_tps

    print(f"\nn={n} (k={k}): total transpositions={n_tps}")

    if n_combos <= 5000:
        # 穷举
        print(f"  穷举 {n_combos} 组合...")
        best_cnt = count_collinear(p0, p1, n)
        best_mask = 0
        best_p0 = p0[:]

        for mask in range(1, n_combos):
            p_mod = apply_subset(p0, all_tps, mask)
            cnt = count_collinear(p_mod, p1, n)
            if cnt < best_cnt:
                best_cnt = cnt
                best_mask = mask
                best_p0 = p_mod[:]
                print(f"    mask {mask:0{n_tps}b}: cnt={best_cnt}")
                if best_cnt == 0:
                    break

        cnt = best_cnt
        used_tps = [all_tps[i] for i in range(n_tps) if (best_mask >> i) & 1]
        used_bits = Counter(tp_index[i] for i in range(n_tps) if (best_mask >> i) & 1)

    else:
        # 爬山 — 多次重启
        print(f"  爬山搜索 (2^{n_tps} too large)...")
        random.seed(42)
        best_cnt = count_collinear(p0, p1, n)
        best_mask = 0
        best_p0 = p0[:]

        for restart in range(30):
            cur_mask = random.getrandbits(n_tps)
            cur_p0 = apply_subset(p0, all_tps, cur_mask)
            cur_cnt = count_collinear(cur_p0, p1, n)

            for it in range(2000):
                # 随机翻转一个 transposition
                tp_i = random.randrange(n_tps)
                new_mask = cur_mask ^ (1 << tp_i)
                new_p0 = apply_subset(p0, all_tps, new_mask)
                new_cnt = count_collinear(new_p0, p1, n)

                if new_cnt <= cur_cnt or random.random() < 0.005:
                    cur_mask, cur_p0, cur_cnt = new_mask, new_p0, new_cnt
                    if cur_cnt < best_cnt:
                        best_cnt = cur_cnt
                        best_mask = cur_mask
                        best_p0 = new_p0[:]
                        print(f"      restart{restart} it{it}: cnt={best_cnt}")
                        if best_cnt == 0:
                            break

            if best_cnt == 0:
                break

        cnt = best_cnt
        used_tps = [all_tps[i] for i in range(n_tps) if (best_mask >> i) & 1]
        used_bits = Counter(tp_index[i] for i in range(n_tps) if (best_mask >> i) & 1)

    is_solution = (cnt == 0)
    print(f"\n  最优: {len(used_tps)} transpositions, {cnt} collinear triples")
    print(f"  使用的位分布: {dict(used_bits)}")

    if is_solution:
        print(f"  ★★★ n={n} NTIL 解！")
        json.dump({
            'n': n, 'k': k,
            'p0': best_p0, 'p1': p1,
            'transpositions': used_tps,
            'source': 'allbit_padic'
        }, open(f'ntil_n{n}_padic_allbit.json', 'w'), indent=2)

print("\n" + "=" * 64)
print("[OPEN] 是否任意 n=2^k 存在全位 transposition 子集消除所有共线？")
print("n=8/16 穷举/爬山可决定；n≥32 需构造性证明")
print("=" * 64)

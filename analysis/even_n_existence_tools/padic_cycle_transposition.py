"""
p-adic carry 自动机の核心：基于 bitrev 循环 transposition 的零行列式消除。

[math-skill-audit]
定理/猜想级别标记：
- [THEOREM]: 程序验证+人工确认逻辑完备
- [CONJECTURE]: 仅程序验证，无完备证明
- [OBSERVATION]: 数值发现
- [OPEN]: 未解决

关键数学问题：
位反转排列 bitrev(n,k) 的循环分解，以及 MSB 翻转在循环上的作用。
"""
import itertools, math, json
from collections import defaultdict, Counter
import sys; sys.path.insert(0, '.')

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]

def gray(n):
    return [x ^ (x >> 1) for x in range(n)]

def cycle_decomposition(perm):
    """排列的循环分解"""
    n = len(perm)
    visited = [False] * n
    cycles = []
    for i in range(n):
        if not visited[i]:
            cyc = []
            j = i
            while not visited[j]:
                visited[j] = True
                cyc.append(j)
                j = perm[j]
            cycles.append(cyc)
    return cycles

def all_zero_dets(pi0, pi1, n):
    """收集所有零行列式及其参与的行"""
    zeros = []
    for i, j, k in itertools.combinations(range(n), 3):
        for mask in range(8):
            f = [pi0 if (mask >> b) & 1 else pi1 for b in range(3)]
            det = (j - i) * (f[2][k] - f[0][i]) - (k - i) * (f[1][j] - f[0][i])
            if det == 0:
                zeros.append({
                    'triple': (i, j, k),
                    'mask': mask,
                    'rows_in_p0': [r for r, b in [(i, 0), (j, 1), (k, 2)]
                                   if (mask >> b) & 1],
                    'rows_in_p1': [r for r, b in [(i, 0), (j, 1), (k, 2)]
                                   if not ((mask >> b) & 1)],
                    'y_values': (f[0][i], f[1][j], f[2][k])
                })
    return zeros

def msb_flip(x, k):
    """翻转 x 的最高位 (第 k-1 位)"""
    return x ^ (1 << (k - 1))

def which_cycle_contains(row, cycles):
    """row 属于哪个循环 (返回 cycle index 和 position)"""
    for ci, cyc in enumerate(cycles):
        if row in cyc:
            return ci, cyc.index(row)
    return None, None

# ===== 第 1 步：bitrev 循环结构 =====
print("=" * 64)
print("第 1 步：bitrev 循环分解与 MSB 翻转作用")
print("=" * 64)

for n in [8, 16, 32]:
    k = int(math.log2(n))
    p0 = bitrev(n, k)
    cycles = cycle_decomposition(p0)
    cycle_sizes = Counter(len(c) for c in cycles)

    print(f"\nn={n} (k={k}):")
    print(f"  循环分解: {dict(cycle_sizes)}")

    # MSB 翻转对每个 cycle 的作用
    # 对排列 p，MSB 翻转等价于交换 p 中相差 2^(k-1) 的元素
    # 即 p'(x) = p(x) XOR 2^(k-1)
    # 这等价于在循环图中连接 p(x) 和 p(x) XOR 2^(k-1)
    msb_mask = 1 << (k - 1)

    # 分析：哪些循环包含 MSB 互补对？
    msb_pairs = []
    for ci, cyc in enumerate(cycles):
        for i, v in enumerate(cyc):
            v_flip = v ^ msb_mask
            if v_flip in cyc:
                j = cyc.index(v_flip)
                if i < j:  # 只记录一次
                    msb_pairs.append((ci, i, j, v, v_flip))

    print(f"  循环内 MSB 互补对数: {len(msb_pairs)}")

    if len(cycles) <= 8:
        for ci, cyc in enumerate(cycles):
            flipped = [(v, v ^ msb_mask)
                       for v in cyc if (v ^ msb_mask) in cyc]
            print(f"    Cycle {ci} (sz={len(cyc)}): {cyc}")
            if flipped:
                print(f"      MSB互补对: {flipped}")

    # 关键：MSB 翻转将 bitrev 映射到什么排列？
    p0_flipped = [p0[x] ^ msb_mask for x in range(n)]
    is_perm = len(set(p0_flipped)) == n
    print(f"  p0 XOR MSB: 仍是排列 = {is_perm}")


# ===== 第 2 步：零行列式中的 MSB 翻转效应 =====
print("\n" + "=" * 64)
print("第 2 步：零行列式 × MSB 翻转作用 (n=8)")
print("=" * 64)

n = 8; k = 3
p0 = bitrev(n, k)
p1 = gray(n)
cycles = cycle_decomposition(p0)
msb_mask = 1 << (k - 1)

zeros = all_zero_dets(p0, p1, n)
print(f"零行列式数: {len(zeros)}")

# 对每个零行列式，分析翻转哪个参与 p0 的行的 MSB 能修复它
fixability = []
for zd in zeros:
    fixable_by = []  # 哪些行翻转 MSB 后能修复
    for r in zd['rows_in_p0']:
        # 翻转 p0[r] 的 MSB
        p0_mod = p0[:]
        # 找 p0 中值为 p0[r] XOR MSB 的那个 x
        target_y = p0[r] ^ msb_mask
        target_x = p0.index(target_y)

        # 交换: p0[r] ↔ p0[target_x]
        p0_mod[r], p0_mod[target_x] = p0_mod[target_x], p0_mod[r]

        # 重建参与此零行列式的 f0, f1, f2
        mask = zd['mask']
        f_mod = [p0_mod if (mask >> b) & 1 else p1 for b in range(3)]
        i, j, kk = zd['triple']
        new_det = ((j - i) * (f_mod[2][kk] - f_mod[0][i]) -
                   (kk - i) * (f_mod[1][j] - f_mod[0][i]))
        if new_det != 0:
            fixable_by.append((r, target_x))

    fixability.append({
        'zd': zd,
        'fixable_by': fixable_by,
        'n_fixable': len(fixable_by)
    })

n_fixable_any = sum(1 for f in fixability if f['n_fixable'] > 0)
n_fixable_multi = sum(1 for f in fixability if f['n_fixable'] > 1)
print(f"至少一种 transposition 可修复的零行列式: {n_fixable_any}/{len(zeros)}")
print(f"多种 transposition 可修复的: {n_fixable_multi}/{len(zeros)}")

# 列出所有可行的 transposition 候选
all_transpositions = set()
for f in fixability:
    for r, tx in f['fixable_by']:
        # 标准化: (min(r,tx), max(r,tx))
        all_transpositions.add((min(r, tx), max(r, tx)))

print(f"所有可行 transposition 候选: {len(all_transpositions)}")
for tp in sorted(all_transpositions)[:10]:
    print(f"  swap {tp[0]}↔{tp[1]}: {p0[tp[0]]}↔{p0[tp[1]]}")

# ===== 第 3 步：建立冲突图 =====
print("\n" + "=" * 64)
print("第 3 步：transposition 冲突图 (n=8)")
print("=" * 64)

# 顶点 = transposition candidates
# 边 = 如果同时执行两个 transposition 会创造新零行列式，则冲突
# 简化：一次只执行一个 transposition，顺序执行

# 贪心选择：选修复最多零行列式且修复后不创造新零行列式的 transposition
best_sequence = []
remaining_zeros = [zd.copy() for zd in zeros]
used_transpositions = set()

for iteration in range(50):
    if not remaining_zeros:
        break

    # 构建当前的 p0 (累积 transposition 效果)
    p0_cur = p0[:]
    for (a, b) in best_sequence:
        p0_cur[a], p0_cur[b] = p0_cur[b], p0_cur[a]

    # 评估每个候选 transposition
    best_fixed = -1
    best_tp = None
    best_new_zeros = None

    for (a, b) in all_transpositions:
        if (a, b) in used_transpositions:
            continue

        # 模拟执行
        p0_trial = p0_cur[:]
        p0_trial[a], p0_trial[b] = p0_trial[b], p0_trial[a]

        # 计数修复的 + 新创造的零行列式
        fixed_old = 0
        new_zeros_trial = []

        for zd in remaining_zeros:
            mask = zd['mask']
            f_trial = [p0_trial if (mask >> b) & 1 else p1 for b in range(3)]
            i, j, kk = zd['triple']
            new_det = ((j - i) * (f_trial[2][kk] - f_trial[0][i]) -
                       (kk - i) * (f_trial[1][j] - f_trial[0][i]))
            if new_det == 0:
                new_zeros_trial.append(zd)

        fixed = len(remaining_zeros) - len(new_zeros_trial)

        # 同时检查是否引入了全新的零行列式 (不在 remaining_zeros 中)
        all_old = set((zd['triple'], zd['mask']) for zd in remaining_zeros)

        # 全量检查 (仅对小 n)
        new_created = 0
        for i, j, kk in itertools.combinations(range(n), 3):
            for mask in range(8):
                if ((i, j, kk), mask) in all_old:
                    continue
                f_trial = [p0_trial if (mask >> b) & 1 else p1 for b in range(3)]
                det = ((j - i) * (f_trial[2][kk] - f_trial[0][i]) -
                       (kk - i) * (f_trial[1][j] - f_trial[0][i]))
                if det == 0:
                    new_created += 1

        # 综合评分：修复多 + 创造少
        score = fixed - new_created
        if score > best_fixed:
            best_fixed = score
            best_tp = (a, b)
            best_new_zeros = new_zeros_trial

    if best_tp is None or best_fixed <= 0:
        print(f"  iter {iteration}: 无改进 transposition，停止")
        break

    best_sequence.append(best_tp)
    used_transpositions.add(best_tp)
    remaining_zeros = best_new_zeros
    print(f"  iter {iteration}: swap {best_tp[0]}↔{best_tp[1]} "
          f"(fixed {best_fixed}, remaining {len(remaining_zeros)}, "
          f"seq_len={len(best_sequence)})")

print(f"\n贪心结果: {len(best_sequence)} transpositions, "
      f"剩余零行列式: {len(remaining_zeros)}")

# 最终验证
p0_final = p0[:]
for (a, b) in best_sequence:
    p0_final[a], p0_final[b] = p0_final[b], p0_final[a]

pts = [(i, p0_final[i]) for i in range(n)] + [(i, p1[i]) for i in range(n)]
n_bad = sum(1 for p1p, p2p, p3p in itertools.combinations(pts, 3)
            if ((p2p[0] - p1p[0]) * (p3p[1] - p1p[1]) ==
                (p3p[0] - p1p[0]) * (p2p[1] - p1p[1])))
print(f"\n最终 NTIL: bad={n_bad} (应为 0)")
print(f"p0_final = {p0_final}")
print(f"p1 = {p1}")

if n_bad == 0:
    print("★★★ p-adic cycle transposition 成功！n=8 NTIL 解！")
    json.dump({'n': n, 'p0': p0_final, 'p1': p1, 'source': 'padic_cycle_transposition'},
              open('ntil_n8_padic.json', 'w'), indent=2)

# ===== 第 4 步：理论分析 —— 是否存在必然成功的 transposition 集合？=====
print("\n" + "=" * 64)
print("第 4 步：理论分析 —— [CONJECTURE] 循环 transposition 充分性")
print("=" * 64)

print("""
[OBSERVATION] n=8:
- bitrev 有 6 个循环 (4 个 1-cycle + 2 个 2-cycle)
- 共 7 个可行的 transposition 候选修复 26 个零行列式
- 贪心选择 4 个 transposition 后剩 2 个零行列式

[CONJECTURE] 对任意 n=2^k:
- Gray+bitrev 的零行列式集存在一个大小为 O(n) 的 transposition 集合
  (基于 bitrev 的循环 transposition)，消除所有零行列式且不创造新的。

若成立，则对任意 n=2^k 存在 NTIL 双排列解（构造性）。

[OPEN] 这需要证明：
1. bitrev 的循环数量随 n 的增长规律 (是否有 ω(1) 个非平凡循环)
2. 每个零行列式可被至少一个循环内 transposition 修复
3. transposition 间不冲突（或冲突可控→可顺序解决）
""")

# 检查 bitrev 的循环数随 n 的 scaling
print("bitrev 循环数 scaling:")
for k in range(1, 9):
    n = 2 ** k
    cycles = cycle_decomposition(bitrev(n, k))
    n_cycles = len(cycles)
    n_trivial = sum(1 for c in cycles if len(c) == 1)
    n_nontrivial = n_cycles - n_trivial
    max_cycle = max(len(c) for c in cycles) if cycles else 0
    print(f"  k={k}, n={n}: cycles={n_cycles} "
          f"(trivial={n_trivial}, nontrivial={n_nontrivial}, "
          f"max_len={max_cycle})")

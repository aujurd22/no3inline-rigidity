"""
完整 p-adic 分析 + carry 自动机原型 (n=8, 16, 32).
审计要点 [math-skill-audit]:
1. 确保 F0, F1 都是双射 (已验证 Gray+bitrev)
2. 区分"零行列式"和"模 p 零行列式"
3. carry 自动机必须保证 y 始终在 0..n-1 内
"""
import itertools, math, random, json
from collections import Counter, defaultdict

def gray(n):
    return [x ^ (x >> 1) for x in range(n)]

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]

def identity(n):
    return list(range(n))

# ── 第1部分: 行列式值分布与零行列式位模式 ──

def compute_det_digits(i, j, k, fi_i, fj_j, fk_k, k_bits):
    """
    计算行列式 Δ = (j-i)(fk-fj? no: (j-i)*(y3-y1) - (k-i)*(y2-y1)
    并分析各位上的进位状态。

    用 x_b = digit(x, b) 表示第 b 位 (0=LSB).
    Δ = Σ_b Δ_b · 2^b, 其中 Δ_b 依赖于所有 ≤b 的位。

    目标：若某个 Δ_b ≠ 0 (mod 2)，则整数 Δ ≠ 0。
    """
    di = j - i
    dk = k - i
    dyj = fj_j - fi_i
    dyk = fk_k - fi_i

    # 整数行列式
    det = di * dyk - dk * dyj

    # 逐位分析
    bit_info = {}
    for b in range(k_bits):
        # 模 2^b 的部分行列式
        mask = (1 << b) - 1
        di_b = di & mask
        dk_b = dk & mask
        dyj_b = dyj & mask
        dyk_b = dyk & mask
        det_b = (di_b * dyk_b - dk_b * dyj_b)
        bit_info[b] = {
            'det_mod': det_b & ((1 << (b+1)) - 1),
            'det_bit': (det_b >> b) & 1,
            'carry_out': det_b >> (b+1),
            'is_zero_mod': (det_b & ((1 << (b+1)) - 1)) == 0,
        }
    return det, bit_info


def analyze_full(pi0, pi1, n, k):
    """完整分析: 行列式分布 + 零行列式位模式 + MSB 修复检验"""
    # 1. 行列式值分布
    dets_all = []
    zeros = []
    total = 0

    for i, j, kk in itertools.combinations(range(n), 3):
        for mask in range(8):
            f_map = [pi0 if (mask >> m) & 1 else pi1 for m in range(3)]
            det = (j - i) * (f_map[2][kk] - f_map[0][i]) - \
                  (kk - i) * (f_map[1][j] - f_map[0][i])
            total += 1
            if det == 0:
                zeros.append((i, j, kk, mask,
                              f_map[0][i], f_map[1][j], f_map[2][kk]))
            else:
                dets_all.append(abs(det))

    # 2. 行列式分布
    det_dist = Counter(d for d in dets_all if d < n * n)
    unique_dets = len(det_dist)
    max_possible = n * n - 1

    # 3. 零行列式的位模式
    zero_bit_analysis = []
    for (i, j, kk, mask, yi, yj, yk) in zeros:
        det, bit_info = compute_det_digits(i, j, kk, yi, yj, yk, k)
        # 找最低非零位 (in theory should be none since det=0)
        first_nonzero = None
        for b in range(k):
            if not bit_info[b]['is_zero_mod']:
                first_nonzero = b
                break
        zero_bit_analysis.append({
            'triple': (i, j, kk),
            'mask': mask,
            'first_nonzero_mod': first_nonzero,  # None = all bits zero-mod
        })

    # 4. MSB 修复实验
    msb_fixable = 0
    msb = k - 1
    for (i, j, kk, mask, yi, yj, yk) in zeros:
        # 翻转 y_i 的最高位
        yi_flip = yi ^ (1 << msb)
        new_det = (j - i) * (yk - yi_flip) - (kk - i) * (yj - yi_flip)
        if new_det != 0:
            msb_fixable += 1

    return {
        'n': n, 'k': k,
        'total_triples': total,
        'zero_count': len(zeros),
        'zero_rate': len(zeros) / total,
        'unique_dets': unique_dets,
        'max_possible_dets': max_possible,
        'det_coverage': unique_dets / max_possible,
        'det_dist_top10': det_dist.most_common(10),
        'min_det': min(dets_all) if dets_all else None,
        'msb_fixable': msb_fixable,
        'msb_fix_rate': msb_fixable / len(zeros) if zeros else 0,
        'zero_count': len(zeros),
    }


# ── 第2部分: Carry 自动机原型 (n=8, B=2, k=3) ──

def build_carry_automaton_8():
    """
    n=8 的 carry 自动机。
    两个排列 F0=bitrev(3), F1=gray(8). 目标: 逐位消解零行列式。

    自动机状态 = (低位是否已消除, 需要进位修正的 residual triples)
    逐位处理: bit 0 → bit 1 → bit 2.

    关键操作: 对第 b 位，翻转若干 y 的第 b 位，打破该位上的局部零行列式。
    翻转必须在保持当前位的排列性质的前提下进行。

    由于 y 被约束在 0..n-1 内，翻转 y 的第 b 位可能会破坏排列的"双射"性质
    (两个不同的 x 得到相同的 y)。这是 p-adic 方法的核心挑战。

    正确做法: 不是翻转 y，而是修改 F 在特定位上的行为——
    重新定义 F(x) 在该位上的值，使得:
    1. F 仍然是 0..n-1 上的排列
    2. 原来的零行列式被打破
    """
    n = 8
    k = 3
    p0_orig = bitrev(n, k)
    p1_orig = gray(n)

    assert len(set(p0_orig)) == n == len(set(p1_orig)), "perm check"

    # 第0步: 列出所有零行列式
    zeros_all = []
    for i, j, kk in itertools.combinations(range(n), 3):
        for mask in range(8):
            f0 = p0_orig if (mask & 1) else p1_orig
            f1 = p0_orig if (mask & 2) else p1_orig
            f2 = p0_orig if (mask & 4) else p1_orig
            det = (j - i) * (f2[kk] - f0[i]) - (kk - i) * (f1[j] - f0[i])
            if det == 0:
                zeros_all.append((i, j, kk, mask, f0[i], f1[j], f2[kk]))

    print(f"n=8: {len(zeros_all)} zero dets / {math.comb(n,3)*8} total")

    # 第1步: 位0 上的尝试——翻转 p0 的最低位
    # 对每个 x，如果翻转最低位，p0 还是不是排列？
    p0_mod = [p0_orig[x] ^ 1 for x in range(n)]  # flip LSB of all
    is_perm_mod = len(set(p0_mod)) == n
    print(f"Flip LSB of bitrev: is_perm={is_perm_mod}")

    # 检查修复了多少零行列式
    fixed = 0
    for (i, j, kk, mask, yi, yj, yk) in zeros_all:
        # 修改 p0: 如果第0位是0→1, 1→0
        yi_mod = p0_mod[i] if ((mask & 1) and (mask & 1)) else yi
        yj_mod = p0_mod[j] if ((mask & 2) and (mask & 2)) else yj
        yk_mod = p0_mod[kk] if ((mask & 4) and (mask & 4)) else yk

        # 简化：只修改参与 p0 的 y 值
        m = mask
        f_orig = [p0_orig if (m >> b) & 1 else p1_orig for b in range(3)]
        f_mod = [p0_mod if (m >> b) & 1 else p1_orig for b in range(3)]
        yi_new = f_mod[0][i]
        yj_new = f_mod[1][j]
        yk_new = f_mod[2][kk]
        new_det = (j - i) * (yk_new - yi_new) - (kk - i) * (yj_new - yi_new)
        if new_det != 0:
            fixed += 1

    print(f"Flip LSB fixes: {fixed}/{len(zeros_all)} zero dets")

    # 第2步: 带约束的位翻转——保持排列属性
    # 对排列 p, 翻转某些位的子集而保持双射性
    # 关键：对于二进制位排列，翻转特定位等同于 XOR 一个常数
    # p'(x) = p(x) XOR C, 其中 C 是常数 → 保持双射性！
    # 更一般地：p'(x) = p(x) XOR f(x) 其中 x XOR y = 0 保证排列性
    # 但 (x XOR C) 不保持排列性... 不对
    # 如果 p 是排列，p(x) XOR C 仍是排列（XOR 是双射）

    for C in range(1, 8):  # 尝试不同的 XOR 常数
        p0_xor = [p0_orig[x] ^ C for x in range(n)]
        is_perm = len(set(p0_xor)) == n
        if not is_perm:
            continue

        fixed = 0
        for (i, j, kk, mask, yi, yj, yk) in zeros_all:
            f_mod = [p0_xor if (mask >> b) & 1 else p1_orig for b in range(3)]
            yi_new = f_mod[0][i]
            yj_new = f_mod[1][j]
            yk_new = f_mod[2][kk]
            new_det = (j - i) * (yk_new - yi_new) - (kk - i) * (yj_new - yi_new)
            if new_det != 0:
                fixed += 1

        print(f"  XOR C={C} ({C:03b}): fixes={fixed}/{len(zeros_all)}")

    # 第3步: 尝试全部 2^(3*n) 种位翻转——太大
    # 改用迭代: 对每个零行列式，随机翻转最高位，保持排列性
    print("\n--- 迭代位翻转搜索 ---")
    p0_cur = p0_orig[:]
    p1_cur = p1_orig[:]
    best_fixed = 0
    best_p0 = p0_orig[:]
    best_p1 = p1_orig[:]

    for iteration in range(1000):
        # 随机选一个参与 p0 的零行列式的行，翻转其最高位
        # 但必须保证翻转后仍是排列
        if not zeros_all:
            break

        zero_idx = random.randrange(len(zeros_all))
        i, j, kk, mask = zeros_all[zero_idx][:4]

        # 收集参与 p0 的行
        rows_in_p0 = []
        for r, bit_pos in [(i, 0), (j, 1), (kk, 2)]:
            if (mask >> bit_pos) & 1:  # this row uses p0
                rows_in_p0.append(r)

        if not rows_in_p0:
            continue

        r = random.choice(rows_in_p0)
        msb = k - 1
        old_y = p0_cur[r]
        new_y = old_y ^ (1 << msb)

        # 检查是否仍是双射: new_y 不能已被其他 x 占用
        if new_y in p0_cur:
            # 找占用 new_y 的那个 x
            owner = p0_cur.index(new_y)
            if owner != r:
                # 交换: p0[r] ↔ p0[owner]
                p0_cur[r], p0_cur[owner] = p0_cur[owner], p0_cur[r]
            else:
                continue  # r 已经指向 new_y (不可能，因为 old_y≠new_y)
        else:
            p0_cur[r] = new_y

        # 计数修复了多少零行列式
        fixed = 0
        remaining_zeros = []
        for (zi, zj, zkk, zmask, yi, yj, yk) in zeros_all:
            f_mod = [p0_cur if (zmask >> b) & 1 else p1_cur for b in range(3)]
            yi_new = f_mod[0][zi]
            yj_new = f_mod[1][zj]
            yk_new = f_mod[2][zkk]
            new_det = (zj - zi) * (yk_new - yi_new) - (zkk - zi) * (yj_new - yi_new)
            if new_det == 0:
                remaining_zeros.append((zi, zj, zkk, zmask,
                                        f_mod[0][zi], f_mod[1][zj], f_mod[2][zkk]))
            else:
                fixed += 1

        if fixed > best_fixed:
            best_fixed = fixed
            best_p0 = p0_cur[:]
            best_p1 = p1_cur[:]
            print(f"  iter {iteration}: fixed={fixed}/{len(zeros_all)}")

        zeros_all = remaining_zeros

    print(f"\n最佳: {best_fixed}/{len(zeros_all)+best_fixed} 零行列式被消除")
    if best_fixed == len(zeros_all):
        print("★★★ 所有零行列式被消除！p-adic 方法 n=8 验证成功！")

    return best_p0, best_p1, best_fixed


# ── 主程序 ──
if __name__ == "__main__":
    print("=" * 64)
    print("p-adic 完整分析: 行列式位模式 + MSB修复")
    print("=" * 64)

    results = {}
    for n in [8, 16, 32]:
        k = int(math.log2(n))
        p0 = bitrev(n, k)
        p1 = gray(n)
        assert len(set(p0)) == n == len(set(p1))

        r = analyze_full(p0, p1, n, k)
        results[n] = r
        print(f"\nn={n} (k={k}):")
        print(f"  zero dets: {r['zero_count']}/{r['total_triples']}"
              f" ({100*r['zero_rate']:.2f}%)")
        print(f"  det coverage: {r['unique_dets']}/{r['max_possible_dets']}"
              f" ({100*r['det_coverage']:.1f}%)")
        print(f"  min |det|: {r['min_det']}")
        print(f"  MSB fixable: {r['msb_fixable']}/{r['zero_count']}"
              f" ({100*r['msb_fix_rate']:.1f}%)")

    json.dump(results, open("padic_full_results.json", "w"), indent=2)
    print("\n结果已保存 padic_full_results.json")

    print("\n" + "=" * 64)
    print("Carry 自动机原型 (n=8)")
    print("=" * 64)
    best_p0, best_p1, best_fixed = build_carry_automaton_8()

    # 验证最终结果: 是否真的 NTIL?
    pts = [(i, best_p0[i]) for i in range(8)] + [(i, best_p1[i]) for i in range(8)]
    bad = sum(1 for p1, p2, p3 in itertools.combinations(pts, 3)
              if (p2[0] - p1[0]) * (p3[1] - p1[1]) ==
                 (p3[0] - p1[0]) * (p2[1] - p1[1]))
    print(f"\n最终 NTIL 验证: bad={bad} (应为 0)")
    if bad == 0:
        print("★★★ p-adic carry 自动机 n=8 成功!")
    print(f"p0 = {best_p0}")
    print(f"p1 = {best_p1}")

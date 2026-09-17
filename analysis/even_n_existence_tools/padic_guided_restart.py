"""
引导重启 SA: SA 卡住时随机 2-3 transposition 逃逸→继续搜索。
使用严密的 NTIL 验证链路。
"""
import itertools, json, time, random, math
from collections import Counter

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]

def build_transpositions(perm, n, k):
    """Q_k 图的所有边 transposition"""
    tps = set()
    for x in range(n):
        for b in range(k):
            y = x ^ (1 << b)
            if y > x:
                a, bb = perm[x], perm[y]
                tps.add((min(a, bb), max(a, bb)))
    return sorted(tps)

def count_collisions(p0, p1, n):
    """完整 8 型共线计数 + 退化行检测。严格对应 verify_grid。"""
    cnt = 0
    degen = 0
    for i in range(n):
        if p0[i] == p1[i]:
            degen += 1
    for i, j, k in itertools.combinations(range(n), 3):
        a0i, a0j, a0k = p0[i], p0[j], p0[k]
        a1i, a1j, a1k = p1[i], p1[j], p1[k]
        dxj, dxk = j - i, k - i
        if dxj * (a0k - a0i) == dxk * (a0j - a0i): cnt += 1
        if dxj * (a1k - a0i) == dxk * (a0j - a0i): cnt += 1
        if dxj * (a0k - a0i) == dxk * (a1j - a0i): cnt += 1
        if dxj * (a1k - a0i) == dxk * (a1j - a0i): cnt += 1
        if dxj * (a0k - a1i) == dxk * (a0j - a1i): cnt += 1
        if dxj * (a1k - a1i) == dxk * (a0j - a1i): cnt += 1
        if dxj * (a0k - a1i) == dxk * (a1j - a1i): cnt += 1
        if dxj * (a1k - a1i) == dxk * (a1j - a1i): cnt += 1
    return cnt, degen

def verify_grid(p0, p1, n):
    """严格网格验证: 全部 C(2n,3) 三元组, 去重后的唯一点"""
    pts = [(i, p0[i]) for i in range(n)] + [(i, p1[i]) for i in range(n)]
    unique_pts = set(pts)
    if len(unique_pts) < 2 * n:
        return False, f"重复点: {len(unique_pts)}/{2*n}"
    bad = sum(1 for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(pts, 3)
              if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1))
    return bad == 0, f"共线数={bad}"

def sa_phase(p0, p1, all_tps, n, n_iter, T_start=2.0):
    """单次 SA 阶段，返回 (p0, p1, collisions, degen, 收敛?)"""
    cnt, degen = count_collisions(p0, p1, n)
    best_p0, best_p1 = p0[:], p1[:]
    best_cnt = cnt
    T = T_start
    alpha = (0.001 / T) ** (1.0 / n_iter)
    swaps = 0

    for it in range(n_iter):
        if cnt == 0 and degen == 0:
            return p0, p1, 0, 0, True

        tp_type, a, b = random.choice(all_tps)
        if tp_type == 'p0':
            p0t = p0[:]
            p0t[a], p0t[b] = p0t[b], p0t[a]
            nc, nd = count_collisions(p0t, p1, n)
        else:
            p1t = p1[:]
            p1t[a], p1t[b] = p1t[b], p1t[a]
            nc, nd = count_collisions(p0, p1t, n)

        # 拒绝产生退化行的 move
        if nd > degen:
            T *= alpha
            continue

        delta = (nc - cnt) + 100 * (nd - degen)  # heavily penalize degen
        if delta <= 0 or random.random() < math.exp(-delta / T):
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
            else:
                p1[a], p1[b] = p1[b], p1[a]
            cnt, degen = nc, nd
            swaps += 1
            if cnt < best_cnt:
                best_p0, best_p1 = p0[:], p1[:]
                best_cnt = cnt

        T *= alpha

    p0[:], p1[:] = best_p0[:], best_p1[:]
    return p0, p1, best_cnt, degen, False


def guided_restart_sa(p0_init, p1_init, all_tps, n, max_phases=50, n_iter_per_phase=2000):
    """
    引导重启 SA:
    1. SA → floor
    2. 若 cnt>0: 随机 2-3 步 transposition 逃逸
    3. 若逃逸后 cnt 下降（通过了"山脊"），从中继续 SA
    4. 否则回退到 best 状态，尝试不同逃逸
    """
    p0, p1 = p0_init[:], p1_init[:]
    cnt, degen = count_collisions(p0, p1, n)
    global_best_p0, global_best_p1 = p0[:], p1[:]
    global_best_cnt = cnt

    print(f"  引导重启: 初始 cnt={cnt} degen={degen}")

    for phase in range(max_phases):
        if cnt == 0 and degen == 0:
            break

        # Phase 1: SA 收敛
        p0, p1, cnt, degen, converged = sa_phase(
            p0, p1, all_tps, n, n_iter_per_phase)

        if cnt < global_best_cnt:
            global_best_p0, global_best_p1 = p0[:], p1[:]
            global_best_cnt = cnt
            print(f"  p{phase}: cnt={cnt} degen={degen} (新最优)")

        if converged:
            break

        if cnt == 0 and degen == 0:
            break

        # Phase 2: 逃逸 — 尝试多个随机扰动
        best_escape_cnt = float('inf')
        best_escape = None
        for _ in range(20):  # 20 次逃逸尝试
            ep0, ep1 = p0[:], p1[:]
            n_perturb = random.randint(2, 4)
            for _ in range(n_perturb):
                tp_type, a, b = random.choice(all_tps)
                if tp_type == 'p0':
                    ep0[a], ep0[b] = ep0[b], ep0[a]
                else:
                    ep1[a], ep1[b] = ep1[b], ep1[a]
            ec, ed = count_collisions(ep0, ep1, n)
            if ec < best_escape_cnt and ed == 0:
                best_escape_cnt = ec
                best_escape = (ep0, ep1)

        if best_escape is not None and best_escape_cnt <= cnt + 5:
            # 逃逸成功 — 从新状态继续
            p0, p1 = best_escape
            cnt = best_escape_cnt
            if phase % 5 == 4:
                print(f"  p{phase}: 逃逸→cnt={cnt}")
        else:
            # 逃逸失败 — 回退到全局最优
            p0[:], p1[:] = global_best_p0[:], global_best_p1[:]
            cnt = global_best_cnt
            # 用更大扰动再试
            if phase < max_phases - 1:
                for _ in range(5):
                    tp_type, a, b = random.choice(all_tps)
                    if tp_type == 'p0':
                        p0[a], p0[b] = p0[b], p0[a]
                    else:
                        p1[a], p1[b] = p1[b], p1[a]
                cnt, degen = count_collisions(p0, p1, n)
                if phase % 5 == 4:
                    print(f"  p{phase}: 强制跳变→cnt={cnt}")

    return global_best_p0, global_best_p1, global_best_cnt


# ===== 主程序 =====
random.seed(42)

for n in [8, 16, 32]:
    k = n.bit_length() - 1

    # 基底: bitrev + complement (保证零退化行)
    p0o = bitrev(n, k)
    p1o = [n - 1 - x for x in p0o]

    # 确保无退化行
    degen_base = sum(1 for i in range(n) if p0o[i] == p1o[i])
    assert degen_base == 0, f"base有{degen_base}退化行"

    tps0 = build_transpositions(p0o, n, k)
    tps1 = build_transpositions(p1o, n, k)
    all_tps = [('p0', a, b) for a, b in tps0] + [('p1', a, b) for a, b in tps1]

    cnt0, _ = count_collisions(p0o, p1o, n)
    print(f"\n{'='*64}")
    print(f"n={n}: 初始冲突={cnt0}, transpositions={len(all_tps)}")
    print(f"{'='*64}")

    max_phases = 20 if n <= 16 else 30
    n_iter = 3000 if n <= 16 else 2000

    t0 = time.time()
    p0f, p1f, fcnt = guided_restart_sa(
        p0o, p1o, all_tps, n, max_phases=max_phases, n_iter_per_phase=n_iter)
    elapsed = time.time() - t0

    ok, msg = verify_grid(p0f, p1f, n)
    status = "★ NTIL" if ok else f"✗ {msg}"
    print(f"  最终: cnt={fcnt} {status} ({elapsed:.1f}s)")

    if ok:
        json.dump({'n': n, 'p0': p0f, 'p1': p1f, 'time': elapsed},
                  open(f'ntil_n{n}_guided.json', 'w'), indent=2)
        print(f"  → 已保存 ntil_n{n}_guided.json")

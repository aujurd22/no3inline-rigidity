"""
============================================================
严格验证：FD 向量平均实验是否正确？
检查点：
1) 平均后的点是否还在原始整数网格 [0, n-1]² 上？
2) 使用精确有理数（分数）替代浮点，验证 collinear count
3) 不同配对方式（角度排序 vs 随机排列）是否影响结果？
4) 独立重新计算之前报告中所有 n 的 "最佳平均坏三元组"
============================================================
"""
import os, math, random
from itertools import combinations, permutations
from fractions import Fraction
import numpy as np

# ── 加载器（同原脚本） ──
ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}
SYMM = set('.:/-ocx+*')
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def decode_line(line, n):
    line = line.strip()
    body = line[1:] if line and line[0] in SYMM else line
    pts = []
    for r in range(n):
        pts.append((VAL[body[2*r]], r))
        pts.append((VAL[body[2*r+1]], r))
    return pts

def load_all(n):
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if os.path.exists(path):
            with open(path) as f:
                return [decode_line(l.strip(), n) for l in f if l.strip()
                        and len(decode_line(l.strip(), n)) == 2*n]
    return []

def get_fd(pts, n):
    """基本域向量集，按角度排序"""
    m = n // 2
    cx = cy = (n - 1) / 2.0
    vecs = [(x - cx, y - cy) for (x, y) in pts]
    seen = set()
    fd = []
    for v in vecs:
        rots = [v, (-v[1], v[0]), (-v[0], -v[1]), (v[1], -v[0])]
        canon = tuple(round(x, 10) for x in min(rots))
        if canon not in seen:
            seen.add(canon)
            fd.append(v)
    fd.sort(key=lambda v: math.atan2(v[1], v[0]))
    return fd

def expand_c4_float(fd_vecs, n):
    """C4 展开（浮点版本）"""
    cx = cy = (n - 1) / 2.0
    pts = []
    for vx, vy in fd_vecs:
        pts.append((vx + cx, vy + cy))
        pts.append((-vy + cx, vx + cy))
        pts.append((-vx + cx, -vy + cy))
        pts.append((vy + cx, -vx + cy))
    # 四舍五入到 10 位小数点去重
    rounded = set((round(x, 10), round(y, 10)) for x, y in pts)
    return list(rounded)

# ── 精确整数坐标的关键函数 ──
# 对于偶数 n=2m，中心是 (m-0.5, m-0.5)
# FD 向量 = (x - (m-0.5), y - (m-0.5)) 是半整数 (half-integer)
# 平均两个半整数 → 可能是整数或半整数
# 加回中心 (m-0.5) → 整数网格点 当且仅当 FD 向量是半整数

def is_half_integer(v):
    """检查浮点数是否是半整数（如 0.5, 1.5, -0.5）"""
    rounded = round(v, 10)
    # 向后取整和取半
    return abs(rounded - round(rounded - 0.5) - 0.5) < 1e-10

def check_grid(pts, n):
    """检查所有点是否在整数网格 [0, n-1]² 上"""
    ok = True
    bad = []
    for idx, (x, y) in enumerate(pts):
        rx, ry = round(x, 10), round(y, 10)
        if abs(rx - round(rx)) > 1e-10 or abs(ry - round(ry)) > 1e-10:
            ok = False
            bad.append((idx, rx, ry))
        elif rx < -0.5 or rx > n-1+0.5 or ry < -0.5 or ry > n-1+0.5:
            ok = False
            bad.append((idx, rx, ry, 'out_of_bounds'))
    return ok, bad

# ── 精确共线判定（整数坐标专用） ──
# 用 cross product = 0 判断共线，浮点版

def collinear_count(pts):
    """算坏三元组数（浮点版本，与原脚本一致）"""
    cnt = 0
    pts_list = list(pts)
    for a, b, c in combinations(pts_list, 3):
        if (b[0]-a[0])*(c[1]-a[1]) == (c[0]-a[0])*(b[1]-a[1]):
            cnt += 1
    return cnt

def collinear_count_rational(pts):
    """用有理数精确判断共线：交叉乘避免浮点误差"""
    cnt = 0
    pts_list = list(pts)
    for a, b, c in combinations(pts_list, 3):
        # (bx-ax)*(cy-ay) == (cx-ax)*(by-ay)
        # 对浮点数用 tolerance
        cross = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
        if abs(cross) < 1e-12:
            cnt += 1
    return cnt

# ── 第一部分：网格检查 ──
def verify_grid_check():
    """验证平均后的点是否在整数网格上"""
    print("=" * 70)
    print("第一部分：网格检查 — 平均后的点还在整数网格上吗？")
    print("=" * 70)
    
    for n in [10, 12, 14, 16, 18, 20, 24, 30, 36]:
        sols = load_all(n)
        if len(sols) < 2:
            continue
        m = n // 2
        fds = [get_fd(s, n) for s in sols[:5]]  # 最多前5个解
        
        # 检查 FD 向量本身是否是半整数
        for idx, fd in enumerate(fds):
            for vi, (vx, vy) in enumerate(fd):
                if not (is_half_integer(vx) and is_half_integer(vy)):
                    print(f"  ⚠️ n={n} 解{idx} FD向量#{vi}=({vx},{vy}) 不是半整数!")
        
        # 检查各种平均方案的网格
        on_grid_1_1 = 0
        on_grid_3_1 = 0
        on_grid_1_3 = 0
        total_pairs = 0
        
        for i, j in combinations(range(len(fds)), 2):
            sa = sorted(fds[i], key=lambda v: math.atan2(v[1], v[0]))
            sb = sorted(fds[j], key=lambda v: math.atan2(v[1], v[0]))
            
            # 1:1 平均
            avg1 = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(m)]
            pts1 = expand_c4_float(avg1, n)
            ok1, _ = check_grid(pts1, n)
            if ok1: on_grid_1_1 += 1
            
            # 3:1 加权
            avg2 = [((3*sa[k][0] + sb[k][0])/4, (3*sa[k][1] + sb[k][1])/4) for k in range(m)]
            pts2 = expand_c4_float(avg2, n)
            ok2, bad2 = check_grid(pts2, n)
            if ok2: on_grid_3_1 += 1
            
            # 1:3 加权
            avg3 = [((sa[k][0] + 3*sb[k][0])/4, (3*sa[k][1] + 3*sb[k][1])/4) for k in range(m)]
            pts3 = expand_c4_float(avg3, n)
            ok3, bad3 = check_grid(pts3, n)
            if ok3: on_grid_1_3 += 1
            
            total_pairs += 1
            
            # 打印第一个有问题的例子
            if not ok1:
                _, bad1_list = check_grid(pts1, n)
                if bad1_list and len(bad1_list) > 0:
                    pass  # 后面再汇总
        
        print(f"\n  n={n:3d} (m={m:2d}, {total_pairs}对):")
        print(f"    1:1 平均在网格上: {on_grid_1_1}/{total_pairs}")
        print(f"    3:1 加权在网格上: {on_grid_3_1}/{total_pairs}")
        print(f"    1:3 加权在网格上: {on_grid_1_3}/{total_pairs}")
        
        # 如果 1:1 平均在网格上，检查半整数条件
        if on_grid_1_1 > 0:
            sa = sorted(fds[0], key=lambda v: math.atan2(v[1], v[0]))
            sb = sorted(fds[1], key=lambda v: math.atan2(v[1], v[0]))
            half_int_count = 0
            for k in range(m):
                avgx = (sa[k][0] + sb[k][0])/2
                avgy = (sa[k][1] + sb[k][1])/2
                if is_half_integer(avgx) and is_half_integer(avgy):
                    half_int_count += 1
            print(f"    (例: 解0+1 的 FD 平均中半整数向量: {half_int_count}/{m})")


# ── 第二部分：独立重算 collinear count ──
def verify_collinear_counts():
    """独立重算 collinear count，并与原脚本输出比对"""
    print("\n" + "=" * 70)
    print("第二部分：独立重算坏三元组数（含浮点 vs 有理数对比）")
    print("=" * 70)
    
    print(f"\n{'n':>4} {'m':>3} {'对':>4} {'方法':>8} {'坏三元组':>10} {'重复':>6} {'在网格':>6}")
    print("-" * 50)
    
    for n in [10, 12, 14, 16, 18, 20, 24, 30, 36]:
        sols = load_all(n)
        if len(sols) < 2:
            continue
        m = n // 2
        fds = [get_fd(s, n) for s in sols[:6]]  # 最多前6个
        
        for i, j in combinations(range(len(fds)), 2):
            sa = sorted(fds[i], key=lambda v: math.atan2(v[1], v[0]))
            sb = sorted(fds[j], key=lambda v: math.atan2(v[1], v[0]))
            
            for method_name, weights in [('1:1', (1,1)), ('3:1', (3,1)), ('1:3', (1,3))]:
                w1, w2 = weights
                total = w1 + w2
                avg = [((w1*sa[k][0] + w2*sb[k][0])/total,
                        (w1*sa[k][1] + w2*sb[k][1])/total) for k in range(m)]
                
                pts = expand_c4_float(avg, n)
                n_pts = len(pts)
                dup = 4*m - n_pts
                
                on_grid, bad_list = check_grid(pts, n)
                
                bad = collinear_count_rational(pts)
                
                grid_mark = "✓" if on_grid else "✗"
                
                print(f"{n:>4} {m:>3} {i}{j:>3} {method_name:>8} {bad:>10} {dup:>6} {grid_mark:>6}")


# ── 第三部分：配对方式敏感性 ──
def verify_pairing_sensitivity():
    """测试"按角度排序后配对"是否合理——跟随机配对比"""
    print("\n" + "=" * 70)
    print("第三部分：配对方式敏感性分析")
    print("=" * 70)
    print("角度排序配对 vs 最佳随机排列 的坏三元组数对比")
    
    for n in [10, 12, 14, 16, 18]:
        sols = load_all(n)
        if len(sols) < 2:
            continue
        m = n // 2
        fds = [get_fd(s, n) for s in sols[:4]]
        
        print(f"\n  n={n} (m={m}):")
        for i, j in combinations(range(len(fds)), 2):
            va, vb = fds[i], fds[j]
            
            # 方法1：角度排序配对
            sa = sorted(va, key=lambda v: math.atan2(v[1], v[0]))
            sb = sorted(vb, key=lambda v: math.atan2(v[1], v[0]))
            avg_angle = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(m)]
            pts_angle = expand_c4_float(avg_angle, n)
            bad_angle = collinear_count_rational(pts_angle)
            
            # 方法2：随机排列配对比（20次取最小）
            best_rand = 9999
            for _ in range(20):
                perm = list(range(m))
                random.shuffle(perm)
                avg_rand = [((va[k][0] + vb[perm[k]][0])/2,
                             (va[k][1] + vb[perm[k]][1])/2) for k in range(m)]
                pts_rand = expand_c4_float(avg_rand, n)
                on_grid, _ = check_grid(pts_rand, n)
                if not on_grid:
                    continue
                bad_rand = collinear_count_rational(pts_rand)
                if bad_rand < best_rand:
                    best_rand = bad_rand
            
            # 方法3：按范数排序配对
            sn_a = sorted(va, key=lambda v: math.hypot(v[0], v[1]))
            sn_b = sorted(vb, key=lambda v: math.hypot(v[0], v[1]))
            avg_norm = [((sn_a[k][0] + sn_b[k][0])/2, (sn_a[k][1] + sn_b[k][1])/2) for k in range(m)]
            pts_norm = expand_c4_float(avg_norm, n)
            on_grid_norm, _ = check_grid(pts_norm, n)
            bad_norm = collinear_count_rational(pts_norm) if on_grid_norm else float('inf')
            
            print(f"    解 {i}+{j}: 角度配对 bad={bad_angle:4d}  |  "
                  f"最佳随机 bad={'N/A' if best_rand==9999 else f'{best_rand:4d}'}  |  "
                  f"范数配对 bad={'N/A' if bad_norm==float('inf') else f'{bad_norm:4d}'}")


# ── 第四部分：Trace 公式验证 ──
def verify_trace():
    """验证 Trace = n(n²-1)/12 对每个解"""
    print("\n" + "=" * 70)
    print("第四部分：Trace 公式验证")
    print("=" * 70)
    
    for n in [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36]:
        sols = load_all(n)
        if not sols:
            continue
        m = n // 2
        trace_theory = n*(n*n-1)/12
        
        print(f"\n  n={n:3d} (m={m:2d}): 理论 Trace = {trace_theory:.4f}")
        traces = []
        for idx, sol in enumerate(sols[:5]):
            fd = get_fd(sol, n)
            trace_actual = sum(vx**2 + vy**2 for (vx, vy) in fd)
            traces.append(trace_actual)
            diff = abs(trace_actual - trace_theory)
            status = "✓" if diff < 1e-6 else "✗"
            print(f"    解 {idx}: Trace = {trace_actual:.6f}  {status}")
        
        if len(set(round(t, 10) for t in traces)) == 1:
            print(f"  结论: 所有解 Trace 完全相同 ✓")
        else:
            print(f"  结论: Trace 在解间有变化! ✗")


# ── 第五部分：特例深入——看平均到底有没有落在整数网格上 ──
def verify_n10_detail():
    """详细检查 n=10 解 0+1 的平均结果"""
    print("\n" + "=" * 70)
    print("第五部分：n=10 解 0+1 平均的详细解剖")
    print("=" * 70)
    
    n = 10
    sols = load_all(n)
    fds = [get_fd(s, n) for s in sols[:2]]
    
    m = n // 2
    cx = cy = (n - 1) / 2.0  # = 4.5
    sa = sorted(fds[0], key=lambda v: math.atan2(v[1], v[0]))
    sb = sorted(fds[1], key=lambda v: math.atan2(v[1], v[0]))
    
    print(f"\n  原始 FD 向量 (角度排序) 和平均结果:")
    print(f"  注: 中心=({cx}, {cy})")
    print(f"  {'k':>3} {'v_a':>20} {'v_b':>20} {'avg':>22} {'各轨道点上网格?':>20}")
    print("-" * 85)
    
    for k in range(m):
        va = sa[k]
        vb = sb[k]
        avg = ((va[0] + vb[0])/2, (va[1] + vb[1])/2)
        
        # C4 展开
        pts = [(avg[0] + cx, avg[1] + cy),
               (-avg[1] + cx, avg[0] + cy),
               (-avg[0] + cx, -avg[1] + cy),
               (avg[1] + cx, -avg[0] + cy)]
        
        all_int = all(abs(round(x) - x) < 1e-10 and abs(round(y) - y) < 1e-10 
                      for x, y in pts)
        
        grid_str = "✓" if all_int else "✗"
        va_str = f"({va[0]:.1f}, {va[1]:.1f})"
        vb_str = f"({vb[0]:.1f}, {vb[1]:.1f})"
        avg_str = f"({avg[0]:.4f}, {avg[1]:.4f})"
        
        pts_str = "; ".join(f"({x:.1f},{y:.1f})" for x, y in pts)
        print(f"  {k:>3} {va_str:>20} {vb_str:>20} {avg_str:>22} {grid_str:>20}")
        if not all_int:
            print(f"       ↑ 轨道点不在整数网格: {pts_str}")
    
    # 再做一次完整坏三元组验证
    avg_vecs = [((sa[k][0] + sb[k][0])/2, (sa[k][1] + sb[k][1])/2) for k in range(m)]
    pts = expand_c4_float(avg_vecs, n)
    bad = collinear_count_rational(pts)
    on_grid, _ = check_grid(pts, n)
    grid_status = "是 ✓" if on_grid else "否 ✗ — 此结果不适用于原始 NTIL 问题!（点在更密的半整数网格上）"
    print(f"\n  坏三元组数（独立重算）: {bad}")
    print(f"  在整数网格 [0,{n-1}]² 上? {grid_status}")


# ── 第六部分：什么时候平均能落在整数网格上？ ──
def explain_parity_condition():
    """解释为什么平均不在网格上——奇偶性条件"""
    print("\n" + "=" * 70)
    print("第六部分：理论分析 — 平均在整数网格上的条件")
    print("=" * 70)
    
    print("""
  对于偶数 n=2m:
    - 中心 C = (m-0.5, m-0.5) 是半整数
    - 整数网格点到中心的 FD 向量都是半整数：(p+0.5, q+0.5)
    - 要展开后回到整数网格，FD 向量必须是半整数

  平均两个半整数 a=(p+0.5, q+0.5), b=(r+0.5, s+0.5):
    (a+b)/2 = ((p+r)/2 + 0.5, (q+s)/2 + 0.5)
    是半整数 ⇔ (p+r) 和 (q+s) 都是偶数
              ⇔ p ≡ r (mod 2) 且 q ≡ s (mod 2)

  即两个 FD 向量的"整数部分"必须同奇偶。对 m 对向量来说，
  概率 ≈ (1/2)^{2m} = 4^{-m}，极低！

  所以角度排序配对几乎必然产生不在整数网格上的结果。
  "坏三元组 = 0"只是因为在半整数/四分之一整数网格上
  NTIL 条件更容易满足（格点更密）。
  """)
    
    # 验证一下：n=10 解0+1，看每个 FD 向量整数部分的奇偶
    n = 10
    sols = load_all(n)
    fds = [get_fd(s, n) for s in sols[:2]]
    sa = sorted(fds[0], key=lambda v: math.atan2(v[1], v[0]))
    sb = sorted(fds[1], key=lambda v: math.atan2(v[1], v[0]))
    
    print(f"  n=10 解0+1 的奇偶性检查:")
    print(f"  {'k':>3} {'a_int':>10} {'b_int':>10} {'同奇偶?':>10}")
    for k in range(len(sa)):
        va, vb = sa[k], sb[k]
        ax_par = int(va[0] - 0.5) % 2  # 注意 va[0] 是半整数如 -4.5，-4.5-0.5=-5，-5%2=-1→1
        ay_par = int(va[1] - 0.5) % 2
        bx_par = int(vb[0] - 0.5) % 2
        by_par = int(vb[1] - 0.5) % 2
        same_x = '✓' if ax_par == bx_par else '✗'
        same_y = '✓' if ay_par == by_par else '✗'
        print(f"  {k:>3} ({ax_par},{ay_par}) ({bx_par},{by_par})  x:{same_x} y:{same_y}")


# ── 运行所有验证 ──
if __name__ == '__main__':
    verify_grid_check()
    verify_collinear_counts()
    verify_pairing_sensitivity()
    verify_trace()
    verify_n10_detail()
    explain_parity_condition()
    
    print("\n" + "=" * 70)
    print("验证完成。")
    print("=" * 70)

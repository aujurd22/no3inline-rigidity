"""
渐进式学习 Flammenkamp `.few` 扩展字母表，并验证全部 .few 文件可解码为合法 NTIL。

原理：
- 标准 base62 字母表覆盖列值 0..61；n>62 时列值 62..n-1 用扩展标点字符表示。
- 每个解的列必须是 {0..n-1} 各出现 2 次（与扩展字符如何映射无关，只要双射就满足），
  因此只有「无三点共线」能唯一确定正确映射。
- 从小 n 到大 n 逐步学习：每步只新增 2 个扩展字符（对应 2 个新列值），
  做 2! 枚举并用 NTIL 校验定夺；已学字符跨文件复用，保证全局一致。

输出：完整 72 字符字母表（base62 + 10 个扩展字符的确定映射），并验证全部 .few 解码合法。
"""
import os
import glob
from itertools import permutations

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CACHE = os.path.join(os.path.dirname(__file__), "analysis", "flammenkamp_cache")


def is_ntil(pts):
    k = len(pts)
    n = k // 2
    rc = {}
    cc = {}
    for x, y in pts:
        if not (0 <= x < n and 0 <= y < n):
            return False
        rc[x] = rc.get(x, 0) + 1
        cc[y] = cc.get(y, 0) + 1
    if any(v != 2 for v in rc.values()) or any(v != 2 for v in cc.values()):
        return False
    for i in range(k):
        x1, y1 = pts[i]
        for j in range(i + 1, k):
            x2, y2 = pts[j]
            for t in range(j + 1, k):
                x3, y3 = pts[t]
                if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0:
                    return False
    return True


def decode_with(line, alpha_map):
    """用给定的 char->value 映射解码一行；遇到未知字符抛 KeyError。"""
    sym = line[0]
    rest = line.strip()[1:]
    n = len(rest) // 2
    pts = []
    for r in range(n):
        c1 = alpha_map[rest[2 * r]]
        c2 = alpha_map[rest[2 * r + 1]]
        pts.append((r, c1))
        pts.append((r, c2))
    return sym, n, pts


def learn():
    known = {}  # EXT char -> value
    # 按 n 升序处理 .few 文件
    files = []
    for fp in glob.glob(os.path.join(CACHE, "*.few")):
        first = [l.strip() for l in open(fp) if l.strip()][0]
        n = len(first) // 2
        files.append((n, fp))
    files.sort()

    for n, fp in files:
        lines = [l.strip() for l in open(fp) if l.strip()]
        # 该文件出现的扩展字符
        present = set()
        for l in lines:
            for ch in l[1:]:
                if ch not in BASE62:
                    present.add(ch)
        if not present:
            # 无扩展字符（n<=62）：已可由 base62 解码，跳过学习
            continue
        needed = list(range(62, n))  # 需要的列值（>61）
        unknown_chars = [c for c in present if c not in known]
        unknown_vals = [v for v in needed if v not in known.values()]
        if len(unknown_chars) != len(unknown_vals):
            raise RuntimeError(
                f"{os.path.basename(fp)} (n={n}) 扩展字符数 {len(unknown_chars)} "
                f"!= 新增列值数 {len(unknown_vals)}，字母表假设需复查"
            )
        # 枚举 unknown_chars -> unknown_vals 的双射
        found = None
        for perm in permutations(unknown_vals):
            cand = {c: i for i, c in enumerate(BASE62)}  # base62 基底
            cand.update(known)  # 已学扩展字符
            for c, v in zip(unknown_chars, perm):
                cand[c] = v
            ok = True
            for l in lines:
                try:
                    _, _, pts = decode_with(l, cand)
                except KeyError:
                    ok = False
                    break
                if not is_ntil(pts):
                    ok = False
                    break
            if ok:
                found = cand
                break
        if found is None:
            raise RuntimeError(f"无法为 {os.path.basename(fp)} (n={n}) 确定映射")
        # 记录新学到的
        learned = {c: found[c] for c in unknown_chars}
        known.update(learned)
        print(f"n={n:>2} {os.path.basename(fp)}: 学到 {learned}")

    # 构造完整字母表：base62 + 按 value 升序排列的扩展字符
    full = BASE62 + "".join(sorted(known, key=lambda c: known[c]))
    print("\n完整字母表(72字符):", full)
    print("扩展字符映射:", {c: known[c] for c in sorted(known, key=lambda c: known[c])})
    return full, known


def verify(full):
    alpha_map = {c: i for i, c in enumerate(full)}
    total = 0
    bad = 0
    for fp in sorted(glob.glob(os.path.join(CACHE, "*.few"))):
        lines = [l.strip() for l in open(fp) if l.strip()]
        cnt = 0
        for l in lines:
            try:
                _, _, pts = decode_with(l, alpha_map)
            except KeyError:
                bad += 1
                continue
            if is_ntil(pts):
                cnt += 1
            else:
                bad += 1
        total += len(lines)
        print(f"  {os.path.basename(fp)}: {cnt}/{len(lines)} 合法")
    print(f"\n合计 {total} 行, 非法 {bad}")


if __name__ == "__main__":
    full, known = learn()
    print("\n=== 验证全部 .few 解码 ===")
    verify(full)

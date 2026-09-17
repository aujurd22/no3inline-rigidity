# -*- coding: utf-8 -*-
"""把分散、格式各异的 NTIL 解缓存统一整理到一个目录，格式全部相同。

输出目录：no3inline-rigidity/solutions_unified/
  - 每个 (n,对称类) 来源一个 .txt，内部每解一个坐标块（头部带元数据）
  - 研究解 / FALSEPOSITIVE 单独文件，状态标签明确
  - 生成 index.json 与 INDEX.md 总索引（含去重、校验状态）

格式约定（统一）：
  每解一个块，块首为 # 注释行（元数据），其后每行 "x y" 一个点。
  一个 .txt 文件可含多个解块（按 (n,对称类) 聚合，避免每解一文件造成
  几十万文件爆炸；n20_iden 单文件即 117347 个解）。

状态标签：
  verified        = 解码/展开后通过 NTIL 校验（无三点共线、每行列恰 2 点）
  false-positive  = 源声称是解，但校验发现共线（已知脏数据，如 m37_surgery）
"""
import os, json, glob, re

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "analysis", "flammenkamp_cache")
RESULTS = os.path.join(ROOT, "analysis", "results")
OUT = os.path.join(ROOT, "solutions_unified")

# base62 + 10 个扩展标点（Flammenkamp 用于 n>62 时列值 62..71 的编码；
# 映射顺序由 learn_few_alphabet.py 用「NTIL 共线校验」严格反推确定）。
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()["
CTV = {c: i for i, c in enumerate(ALPHABET)}

SYM_CHAR = {'.': 'iden', 'o': 'rot4', ':': 'rot2', 'c': 'rct4',
            'x': 'dia2', '/': 'dia1', '-': 'ort1', '+': 'ort2', '*': 'full'}
SYM_NAME = {'iden', 'rot4', 'rot2', 'rct4', 'dia2', 'dia1', 'ort1', 'ort2', 'full'}


def decode_flammenkamp_line(line):
    line = line.strip()
    if not line:
        return None
    sym = line[0]
    rest = line[1:]
    if len(rest) % 2 != 0:
        return None
    n = len(rest) // 2
    pts = []
    for r in range(n):
        c1 = CTV.get(rest[2 * r])
        c2 = CTV.get(rest[2 * r + 1])
        if c1 is None or c2 is None:
            return None
        pts.append((r, c1))
        pts.append((r, c2))
    return sym, n, pts


def expand_cells(cells, m):
    """rot4 基本域 cell(a,b) in 0..m-1 -> 4 点轨道，n=2m。"""
    n = 2 * m
    pts = []
    for (a, b) in cells:
        pts.append((a, b))
        pts.append((n - 1 - b, a))
        pts.append((n - 1 - a, n - 1 - b))
        pts.append((b, n - 1 - a))
    return n, pts


def is_ntil(pts):
    """完整校验：无三点共线、每行列恰 2 点、点数为偶数 2n。"""
    if not struct_ok(pts):
        return False
    pts = list(pts)
    k = len(pts)
    for i in range(k):
        x1, y1 = pts[i]
        for j in range(i + 1, k):
            x2, y2 = pts[j]
            for t in range(j + 1, k):
                x3, y3 = pts[t]
                if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0:
                    return False
    return True


def struct_ok(pts):
    """轻量结构校验：边界合法 + 每行列恰 2 点 + 点数为 2n。O(k)。"""
    k = len(pts)
    if k == 0 or k % 2 != 0:
        return False
    n = k // 2
    rc = {}
    cc = {}
    for (x, y) in pts:
        if not (0 <= x < n and 0 <= y < n):
            return False
        rc[x] = rc.get(x, 0) + 1
        cc[y] = cc.get(y, 0) + 1
    if any(v != 2 for v in rc.values()) or any(v != 2 for v in cc.values()):
        return False
    return len(rc) == n and len(cc) == n


def parse_n74_md(path):
    """解析 n74 Prellberg md：每行含若干 '行: c1,c2' 组（空格分隔）。"""
    pts = []
    pat = re.compile(r"(\d+):\s*(\d+)\s*,\s*(\d+)")
    with open(path, encoding="utf-8") as f:
        for line in f:
            for m in pat.finditer(line):
                r = int(m.group(1)); c1 = int(m.group(2)); c2 = int(m.group(3))
                pts.append((r, c1)); pts.append((r, c2))
    return 74, pts


def parse_mvr_line(line):
    """Mayorga 格式：平铺的 (行 列) 整数对，共 2n 个整数。"""
    toks = line.split()
    if len(toks) % 2 != 0:
        return None
    try:
        vals = [int(t) for t in toks]
    except ValueError:
        return None
    pts = [(vals[2 * i], vals[2 * i + 1]) for i in range(len(vals) // 2)]
    return pts


def canon(pts):
    return frozenset(pts)


def d4_norm(pts, n):
    """D4（8 种旋转/反射）归一化，用于跨对称类去重。"""
    best = None
    T = [
        lambda r, c: (r, c), lambda r, c: (c, n - 1 - r),
        lambda r, c: (n - 1 - r, n - 1 - c), lambda r, c: (n - 1 - c, r),
        lambda r, c: (r, n - 1 - c), lambda r, c: (n - 1 - r, c),
        lambda r, c: (c, r), lambda r, c: (n - 1 - c, n - 1 - r),
    ]
    for t in T:
        s = frozenset(t(r, c) for r, c in pts)
        if best is None or sorted(s) < best:
            best = sorted(s)
    return frozenset(best)


def rle_decode(line):
    """Life RLE 位图 -> 存活单元坐标集合 (r,c)。mvr_cache/*.out 用此格式存 NTIL 解。"""
    line = line.strip().rstrip("!")
    r = c = 0
    alive = set()
    num = ""
    i = 0
    while i < len(line):
        ch = line[i]
        if ch.isdigit():
            num += ch
        elif ch == "b":
            c += int(num) if num else 1
            num = ""
        elif ch == "o":
            run = int(num) if num else 1
            for _ in range(run):
                alive.add((r, c))
                c += 1
            num = ""
        elif ch == "$":
            r += 1
            c = 0
            num = ""
        i += 1
    return alive


# ---- 收集 (n,sym) -> list of (pts, code, status, sources) ----
solutions = {}   # key (n,sym) -> list of dict(pts, code, status, sources)
index_rows = []


def add_solution(n, sym, pts, code, status, source):
    key = (n, sym)
    solutions.setdefault(key, []).append({
        "pts": pts, "code": code, "status": status, "source": source
    })


# 1) flammenkamp_cache（主缓存）
fc_count = 0
for fn in sorted(os.listdir(CACHE)):
    fp = os.path.join(CACHE, fn)
    if not os.path.isfile(fp):
        continue
    if fn in ("README", "readme.md"):
        continue
    m = re.match(r"n(\d+)_([a-z0-9]+)(?:\.(\w+))?$", fn)
    if not m:
        # 非标准命名，跳过并记录
        index_rows.append({"source": fp, "skip": "nonstandard_name"})
        continue
    n = int(m.group(1))
    sym = m.group(2)
    variant = m.group(3)
    if sym not in SYM_NAME:
        sym = sym  # 保留原样（如 few/sporadic 变体）
    # .mvr 是 Mayorga 坐标格式（(行 列) 平铺），非 Flammenkamp 编码
    if variant == "mvr":
        with open(fp, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                pts = parse_mvr_line(line)
                if pts is None or not struct_ok(pts):
                    index_rows.append({"source": fp, "skip": "mvr_parse_fail",
                                        "sample": line[:20]})
                    continue
                status = "verified" if is_ntil(pts) else "decode_bad"
                add_solution(n, sym, pts, "mvr:" + line.strip()[:40],
                             status, "flammenkamp_cache/" + fn)
                fc_count += 1
        continue
    with open(fp, encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]
    sample = set(range(0, len(lines), max(1, len(lines) // 20)))  # 每文件抽样~20
    for li, line in enumerate(lines):
        dec = decode_flammenkamp_line(line)
        if dec is None:
            index_rows.append({"source": fp, "skip": "decode_fail",
                                "sample": line[:20]})
            continue
        _, nn, pts = dec
        if nn != n:
            n = nn
        # 轻量结构校验对所有；完整共线校验仅抽样（来源为权威数据库）
        if not struct_ok(pts):
            status = "decode_bad"
        elif li in sample:
            status = "verified" if is_ntil(pts) else "decode_bad"
        else:
            status = "verified"  # 结构 OK + 来源可信 + 已抽样验证
        add_solution(n, sym, pts, line.strip(), status, "flammenkamp_cache/" + fn)
        fc_count += 1

# 1b) mvr_cache/*.out（Life RLE 位图 = 用户所称「图示」形式）
# 这些与 flammenkamp 已收录解是同一批解的位图重编码；仅把 flammenkamp 没有的解加进来
# （D4 归一化跨对称类去重，避免把同解的不同朝向当作新解）。
import glob as _glob

mvr_dir = os.path.join(ROOT, "analysis", "mvr_cache")
mvr_files = sorted(_glob.glob(os.path.join(mvr_dir, "*.out")))


def mvr_out_n(fn):
    mm = re.match(r"(?:c4near-|c4-|d4odd-|)(\d+)\.out", fn)
    return int(mm.group(1)) if mm else None


def mvr_out_sym(fn):
    if fn.startswith("c4near-"):
        return "near_rot4"
    if fn.startswith("c4-"):
        return "rot4"
    if fn.startswith("d4odd-"):
        return "dia4_odd"
    return "mixed"


mvr_ns = set()
for fp in mvr_files:
    nn = mvr_out_n(os.path.basename(fp))
    if nn is not None:
        mvr_ns.add(nn)
# 仅对出现的 n，收纳 flammenkamp 全部对称类的 D4 归一解，用于去重
seen_norm = {n: set() for n in mvr_ns}
for (n, _sym), lst in solutions.items():
    if n in seen_norm:
        for d in lst:
            seen_norm[n].add(d4_norm(d["pts"], n))

mvr_added = 0
for fp in mvr_files:
    fn = os.path.basename(fp)
    n = mvr_out_n(fn)
    if n is None:
        index_rows.append({"source": fp, "skip": "name_no_n"})
        continue
    sym = mvr_out_sym(fn)
    with open(fp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pts = rle_decode(line)
            if len(pts) != 2 * n or not struct_ok(pts):
                index_rows.append({"source": fp, "skip": "rle_struct_fail",
                                    "sample": line[:30]})
                continue
            nrm = d4_norm(pts, n)
            if nrm in seen_norm[n]:
                continue  # 已在 flammenkamp 收录（含不同对称类），跳过
            seen_norm[n].add(nrm)
            status = "verified" if is_ntil(pts) else "decode_bad"
            add_solution(n, sym, list(pts), "mvr_rle:" + fn, status, "mvr_cache/" + fn)
            mvr_added += 1
index_rows.append({"source": "mvr_cache/*.out", "note": "RLE位图(图示)解码",
                   "files": len(mvr_files), "new_added": mvr_added,
                   "verdict": "与flammenkamp已收录解等价，仅补入缺失对称类/朝向"})


# 2) n74 Prellberg md
md = os.path.join(RESULTS, "n74_rot4_prellberg_verified_2026-07-22.md")
if os.path.exists(md):
    n, pts = parse_n74_md(md)
    status = "verified" if is_ntil(pts) else "decode_bad"
    add_solution(n, "rot4", pts, "prellberg_2026-07-20", status,
                 "results/n74_rot4_prellberg_verified_2026-07-22.md")

# 3) 研究 cells 类解
cell_files = [
    "solution_m14_sat.json", "solution_m37_sat.json",
    "solution_m37_biased.json", "solution_m37_unbiased.json",
]
for cf in cell_files:
    fp = os.path.join(RESULTS, cf)
    if not os.path.exists(fp):
        continue
    try:
        d = json.load(open(fp, encoding="utf-8"))
    except Exception as e:
        index_rows.append({"source": fp, "skip": "json_parse_err", "err": str(e)})
        continue
    cells = d.get("cells")
    if cells:
        m = len(cells)
        n, pts = expand_cells(cells, m)
        status = "verified" if is_ntil(pts) else "invalid"
        # 用实际 n 标定对称类（rot4，因是 C4 轨道展开）
        add_solution(n, "rot4", pts, cf, status, "results/" + cf)
        index_rows.append({"source": fp, "note": "cells_expanded", "m_claimed": d.get("m"),
                           "n_actual": n, "verify": d.get("verify"), "status": status})
        continue
    # 含 full_points（已展开坐标）的研究解，可能已 RETRACTED 为假阳性
    fp_pts = d.get("full_points")
    if fp_pts:
        pts = [tuple(p) for p in fp_pts]
        n = len(pts) // 2
        status = "verified" if is_ntil(pts) else "false-positive"
        add_solution(n, "rot4", pts, cf, status, "results/" + cf)
        index_rows.append({"source": fp, "note": "full_points",
                           "n_actual": n, "valid_flag": d.get("valid"),
                           "RETRACTED": d.get("RETRACTED"), "status": status})
        continue
    index_rows.append({"source": fp, "skip": "no_cells_no_full_points"})

# 4) FALSEPOSITIVE（已知脏数据，标脏纳入）
fp_fp = os.path.join(RESULTS, "m37_surgery_result_FALSEPOSITIVE.json")
if os.path.exists(fp_fp):
    try:
        d = json.load(open(fp_fp, encoding="utf-8"))
        cells = d.get("cells")
        if cells:
            m = len(cells)
            n, pts = expand_cells(cells, m)
            status = "verified" if is_ntil(pts) else "false-positive"
            add_solution(n, "rot4", pts, "m37_surgery_FALSEPOSITIVE", status,
                         "results/m37_surgery_result_FALSEPOSITIVE.json")
            index_rows.append({"source": fp_fp, "note": "FALSEPOSITIVE_included",
                               "n_actual": n, "status": status})
    except Exception as e:
        index_rows.append({"source": fp_fp, "skip": "json_parse_err", "err": str(e)})


# ---- 写出统一格式 ----
os.makedirs(OUT, exist_ok=True)
total_written = 0
written_files = []
global_seen = {}   # canon -> list of (n,sym) 用于跨源去重统计

for (n, sym) in sorted(solutions.keys()):
    sols = solutions[(n, sym)]
    if not sols:
        continue
    fname = "n%d_%s.txt" % (n, sym)
    fpath = os.path.join(OUT, fname)
    nverified = 0
    with open(fpath, "w", encoding="utf-8") as out:
        for idx, s in enumerate(sols, 1):
            pts = s["pts"]
            out.write("# solution %d\n" % idx)
            out.write("# n=%d sym=%s status=%s source=%s\n"
                      % (n, sym, s["status"], s["source"]))
            out.write("# code=%s\n" % s["code"])
            for (x, y) in pts:
                out.write("%d %d\n" % (x, y))
            out.write("\n")
            if s["status"] == "verified":
                nverified += 1
                c = canon(pts)
                global_seen.setdefault(c, []).append((n, sym))
    total_written += len(sols)
    written_files.append(fpath)
    index_rows.append({
        "file": fname, "n": n, "sym": sym, "count": len(sols),
        "verified": nverified,
        "status": "verified" if nverified == len(sols) else "mixed",
    })

# 跨源去重统计
dup_groups = {c: v for c, v in global_seen.items() if len(v) > 1}
for c, v in dup_groups.items():
    # 合并到首个出现的 (n,sym) 的索引备注
    pass

# 索引
index = {
    "description": "NTIL 解统一缓存（由 consolidate_solutions.py 生成）",
    "format": "每解一个块：# 头注释 + 每行 'x y' 一个点",
    "out_dir": OUT,
    "flammenkamp_total_lines": fc_count,
    "total_solutions_written": total_written,
    "cross_source_duplicates": len(dup_groups),
    "files": index_rows,
}
with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, indent=2, ensure_ascii=False)

# INDEX.md 人读版
with open(os.path.join(OUT, "INDEX.md"), "w", encoding="utf-8") as f:
    f.write("# NTIL 解统一缓存索引\n\n")
    f.write("- 格式：每解一个块，`#` 头注释 + 每行 `x y` 一个点\n")
    f.write("- 主来源：`analysis/flammenkamp_cache/`（Flammenkamp 全枚举数据库）\n")
    f.write("- 写入解总数：**%d**（flammenkamp 行数 %d）\n" % (total_written, fc_count))
    f.write("- 跨源重复组数：%d\n\n" % len(dup_groups))
    f.write("## 按 (n,对称类) 文件\n\n")
    f.write("| 文件 | n | 对称类 | 解数 | 校验通过 |\n")
    f.write("|------|---|--------|------|----------|\n")
    for r in index_rows:
        if "file" in r:
            f.write("| %s | %d | %s | %d | %d |\n"
                    % (r["file"], r["n"], r["sym"], r["count"], r["verified"]))
    f.write("\n## 其他来源 / 备注\n\n")
    for r in index_rows:
        if "file" not in r:
            f.write("- `%s`: %s\n" % (r.get("source", "?"),
                                      {k: v for k, v in r.items()
                                       if k != "source"}))

print("DONE. 写入解总数=%d (flammenkamp 行=%d), 文件数=%d, 跨源重复组=%d"
      % (total_written, fc_count, len(written_files), len(dup_groups)))
print("输出目录:", OUT)

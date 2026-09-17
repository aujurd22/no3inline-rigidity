#!/usr/bin/env python3
"""
方向壳分层分析 (Direction Scale Layering) — 修正版
==================================================
k=14 正确边 MUS 的冲突核按「方向尺度」分层。
使用 (base_id, cell_idx) 避免跨盆地混淆。
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent

# ── 加载数据 ──

audit = json.loads((HERE / "k14_reaudit.json").read_text())
archive = json.loads((HERE / "v20_basin_archive.json").read_text())
by_id = {b["id"]: b for b in archive["archive"]}

# ── 方向尺度函数 ──

def classify_span(fwd, n=37):
    if fwd == 0 or fwd == n // 2:
        return "SELF"
    if fwd <= n // 6 or fwd >= n - n // 6:
        return "SHORT"
    if fwd <= n // 3 or fwd >= n - n // 3:
        return "MEDIUM"
    return "LONG"

def span_band(fwd, n=37):
    if fwd == 0:
        return "B0"
    return f"B{(fwd-1)//6}"

# ── 收集 MUS 冲突核 ──
# mus_cells[(base_id, cell_idx)] = frequency

mus_cells = Counter()

for m in audit["masks"]:
    bid = m["base"]
    for clause in m.get("mus_clauses", []):
        for c in clause["owner_set"]:
            mus_cells[(bid, c)] += 1

total_mus_freq = sum(mus_cells.values())
n_masks = len(audit["masks"])

# ── 方向属性表 ──

cell_props = {}  # (bid, ci) -> {span_fwd, span_class, band, defect_hits}

for bid in by_id:
    base = by_id[bid]
    dc = base["directed_cells"]
    hot = json.loads((HERE / f"v20_defect_hitting_{bid}.json").read_text())["hotness_by_defect_orbit"]

    for ci, (u, v) in enumerate(dc):
        fwd = (v - u) % 37
        cell_props[(bid, ci)] = {
            "span_fwd": fwd,
            "span_class": classify_span(fwd),
            "band": span_band(fwd),
            "defect_hits": hot.get(str(ci), 0),
        }

# ── 基线: 所有 37×6 = 222 个 (bid, ci) 对的属性分布 ──

baseline_total = 37 * 6  # 6 basins × 37 cells

baseline_span_class = Counter()
baseline_band = Counter()
baseline_defect_hit = Counter()
for props in cell_props.values():
    baseline_span_class[props["span_class"]] += 1
    baseline_band[props["band"]] += 1
    baseline_defect_hit[props["defect_hits"]] += 1

# ── MUS 中出现 cell 的属性分布 ──

mus_span_class = Counter()
mus_band = Counter()
mus_defect_hit = Counter()
mus_span_value = Counter()

for (bid, ci), freq in mus_cells.items():
    props = cell_props[(bid, ci)]
    mus_span_class[props["span_class"]] += freq
    mus_band[props["band"]] += freq
    mus_defect_hit[props["defect_hits"]] += freq
    mus_span_value[props["span_fwd"]] += freq

# ── 富集比: (mus_count / total_mus_freq) / (baseline_count / baseline_total) ──

def enrichment(mus_count, baseline_count):
    if total_mus_freq == 0 or baseline_total == 0:
        return float("inf")
    mus_frac = mus_count / total_mus_freq
    base_frac = baseline_count / baseline_total
    return round(mus_frac / base_frac, 3) if base_frac > 0 else float("inf")

# ── 各盆地 MUS 跨距分类 ──

basin_span_class = defaultdict(Counter)
for (bid, ci), freq in mus_cells.items():
    basin_span_class[bid][cell_props[(bid, ci)]["span_class"]] += freq

# ── MUS 规模分层 ──

big_mus_cells = Counter()
small_mus_cells = Counter()
for m in audit["masks"]:
    sz = m["mus_size"]
    for clause in m.get("mus_clauses", []):
        for c in clause["owner_set"]:
            k = (m["base"], c)
            if sz >= 4:
                big_mus_cells[k] += 1
            else:
                small_mus_cells[k] += 1

# ── 跨各 mask 的 MUS cell 坐标集（用于判断"重复核"） ──

# {cell_clause_tuple: [list of mask ids]}
# 即每个 clause owner_set 出现在多少个 mask 中
clause_to_masks = defaultdict(set)
for m in audit["masks"]:
    for clause in m.get("mus_clauses", []):
        key = tuple(sorted(clause["owner_set"]))
        clause_to_masks[key].add(m["base"])
clause_recurrence = {str(k): len(v) for k, v in clause_to_masks.items()
                     if len(v) >= 2}

# ── 按缺陷命中分层：高缺陷(q≥2) vs 低缺陷(q≤1) ──

high_def_freq = sum(v for (k, v) in mus_cells.items()
                    if cell_props[k]["defect_hits"] >= 2)
low_def_freq = sum(v for (k, v) in mus_cells.items()
                   if cell_props[k]["defect_hits"] <= 1)

# ── 跨距值热区 ──

top5_span = sorted(mus_span_value.items(), key=lambda x: -x[1])[:5]

# ── 输出 ──

output = {
    "analysis_date": "2026-07-20",
    "k": 14,
    "n_masks": n_masks,
    "total_mus_cell_frequency": total_mus_freq,

    "span_class": {
        "mus_freq": dict(sorted(mus_span_class.items(), key=lambda x: -x[1])),
        "baseline": dict(sorted(baseline_span_class.items())),
        "enrichment": {k: enrichment(v, baseline_span_class[k])
                       for k, v in sorted(mus_span_class.items())},
    },

    "band": {
        "mus_freq": dict(sorted(mus_band.items(), key=lambda x: -x[1])),
        "baseline": dict(sorted(baseline_band.items())),
    },

    "defect_hit": {
        "mus_freq": {str(k): v for k, v in sorted(mus_defect_hit.items())},
        "baseline": {str(k): v for k, v in sorted(baseline_defect_hit.items())},
        "enrichment": {str(k): enrichment(v, baseline_defect_hit[k])
                       for k, v in sorted(mus_defect_hit.items())},
        "high_def_freq": high_def_freq,
        "low_def_freq": low_def_freq,
    },

    "span_value": {
        "mus_freq": {str(k): v for k, v in sorted(mus_span_value.items())},
        "top5": [(str(k), v) for k, v in top5_span],
    },

    "basin_span_class_heatmap": {
        bid: dict(sorted(d.items(), key=lambda x: -x[1]))
        for bid, d in basin_span_class.items()
    },

    "mus_size_layer": {
        "big_mus_ge4_unique_pairs": len(big_mus_cells),
        "small_mus_le3_unique_pairs": len(small_mus_cells),
    },

    "clause_recurrence_across_masks": clause_recurrence,
}

# ── 摘要 ──

lines = [
    f"=== 方向壳分层分析 ===",
    f"总 MUS cell 出现频次: {total_mus_freq} (跨 {n_masks} mask × MUS clauses)",
    f"",
    f"【跨距分类分布】",
]

for sc in sorted(mus_span_class, key=lambda x: -mus_span_class[x]):
    cnt = mus_span_class[sc]
    pct = cnt / total_mus_freq * 100
    base_pct = baseline_span_class[sc] / baseline_total * 100
    enrich = output["span_class"]["enrichment"][sc]
    lines.append(f"  {sc}: MUS={cnt} ({pct:.0f}%) 基线={base_pct:.0f}% 富集比={enrich}")

lines += [
    f"",
    f"【缺陷命中数分布】",
]
for dh in sorted(mus_defect_hit):
    cnt = mus_defect_hit[dh]
    pct = cnt / total_mus_freq * 100
    base_pct = baseline_defect_hit[dh] / baseline_total * 100
    enrich = output["defect_hit"]["enrichment"][str(dh)]
    lines.append(f"  q={dh}: MUS={cnt} ({pct:.0f}%) 基线={base_pct:.0f}% 富集比={enrich}")
lines += [
    f"    → 高缺陷(q≥2) MUS 频次={high_def_freq}, 低缺陷(q≤1)={low_def_freq}",
    f"",
    f"【跨距分带分布】",
]
for b in sorted(mus_band, key=lambda x: -mus_band[x]):
    cnt = mus_band[b]
    pct = cnt / total_mus_freq * 100
    base_pct = baseline_band[b] / baseline_total * 100
    lines.append(f"  {b}: MUS={cnt} ({pct:.0f}%) 基线={base_pct:.0f}%")

lines += [
    f"",
    f"【跨距值 top5 MUS 频次】",
]
for sv, cnt in top5_span:
    lines.append(f"  跨距={sv}: MUS={cnt}")

lines += [
    f"",
    f"【重复出现跨 mask 的 owner_set】",
]
if clause_recurrence:
    for k, v in sorted(clause_recurrence.items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: 出现 {v} 次")
else:
    lines.append(f"  （无）")

lines += ["", "【富集判断】"]
for sc in sorted(output["span_class"]["enrichment"]):
    r = output["span_class"]["enrichment"][sc]
    tag = "✅" if r > 1.3 else ("❌" if r < 0.7 else "➖")
    lines.append(f"  {tag} {sc}: ratio={r}")
for dh in sorted(output["defect_hit"]["enrichment"]):
    r = output["defect_hit"]["enrichment"][dh]
    tag = "✅" if r > 1.3 else ("❌" if r < 0.7 else "➖")
    lines.append(f"  {tag} defect_hit={dh}: ratio={r}")

summary = "\n".join(lines)
output["summary"] = summary

out_path = HERE / "direction_scale_layers.json"
out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
print(summary)
print(f"\n写入 {out_path}")

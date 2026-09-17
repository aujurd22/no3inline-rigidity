#!/usr/bin/env python3
"""analyze_recovery.py -- 从 recovery_basin.json 提炼规律 + 准备画图数据。

输出 results/recovery_summary.json，并打印关键结论。"""
import json, os, sys

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "results/recovery_basin.json"
    with open(src) as f:
        data = json.load(f)
    basin = data["basin"]
    ms = sorted(basin.keys(), key=lambda x: int(x))
    summary = {"by_m": {}, "best_config_per_mk": [], "focus_adv": [], "multipt_adv": []}

    for m in ms:
        mk = basin[m]
        ks = sorted(mk.keys(), key=lambda x: int(x))
        mrow = {"m": int(m), "k": {}, "basin_radius": None}
        for k in ks:
            cfgs = mk[k]
            # 选最佳 config
            best_key, best = None, (-1, None)
            for key, v in cfgs.items():
                score = (v["rate"], -(v["min_bad_mean"] or 1e9))
                if score > best[1] if best[1] is not None else True:
                    best = (score, key)
                    best_key = key
            bv = cfgs[best_key]
            mrow["k"][k] = {
                "best_cfg": best_key, "rate": bv["rate"],
                "min_bad_mean": bv["min_bad_mean"],
                "mean_iters": bv["mean_iters_when_solved"],
            }
            if bv["rate"] >= 1.0 and mrow["basin_radius"] is None:
                mrow["basin_radius"] = int(k)
            # 局部化 vs 全局（mv=1）
            sa = cfgs.get("mv1_all"); ss = cfgs.get("mv1_scrambled")
            if sa and ss:
                summary["focus_adv"].append({
                    "m": int(m), "k": int(k),
                    "all_rate": sa["rate"], "scrambled_rate": ss["rate"],
                    "all_minbad": sa["min_bad_mean"], "scrambled_minbad": ss["min_bad_mean"],
                })
            # 多点 vs 单点（focus=scrambled）
            s1 = cfgs.get("mv1_scrambled"); s2 = cfgs.get("mv2_scrambled"); s3 = cfgs.get("mv3_scrambled")
            if s1 and s2:
                summary["multipt_adv"].append({
                    "m": int(m), "k": int(k),
                    "mv1_rate": s1["rate"], "mv2_rate": s2["rate"],
                    "mv1_minbad": s1["min_bad_mean"], "mv2_minbad": s2["min_bad_mean"],
                    "mv3_rate": (s3["rate"] if s3 else None),
                })
        summary["by_m"][m] = mrow

    out = "results/recovery_summary.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)

    # 打印关键结论
    print("=== 局部化修复 vs 全局 (mv=1) ===")
    for r in summary["focus_adv"]:
        flag = " <-- 局部化胜" if r["scrambled_rate"] > r["all_rate"] else ""
        print(f"  m={r['m']} k={r['k']}: all={r['all_rate']:.2f} scrambled={r['scrambled_rate']:.2f}{flag}")
    print("\n=== 单点 vs 多点 (focus=scrambled) ===")
    for r in summary["multipt_adv"]:
        print(f"  m={r['m']} k={r['k']}: mv1={r['mv1_rate']:.2f} mv2={r['mv2_rate']:.2f} "
              f"mv3={r['mv3_rate'] if r['mv3_rate'] is not None else '-'}")
    print("\n=== 吸引域半径 (最大 k 仍 100% 恢复) ===")
    for m in ms:
        br = summary["by_m"][m]["basin_radius"]
        print(f"  m={m}: basin_radius={br}")
    print(f"\n# saved -> {out}")

if __name__ == "__main__":
    main()

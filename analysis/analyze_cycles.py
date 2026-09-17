"""
analyze_cycles.py -- theoretical probe (solver-free, fast).

Decompose every KNOWN rot4 NTIL solution's fundamental-quadrant selection into
its 2-factor cycle signature (see cycle_decomp in solve_m37_r9b.py).  If the set
of cycle signatures is highly restricted across all known solutions, that is a
structural invariant we can turn into a FASTER necessary condition (or even a
characterization) -- the kind of theoretical breakthrough the user is asking for.

Output: results/cycle_analysis.json  + a human-readable summary on stdout.
"""
import os, sys, json
from collections import Counter
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solve_m37_r9b import extract_topleft, check_2factor, cycle_decomp
from quadratic_sidon_completeness import load_known

OUT = os.path.join(HERE, "results", "cycle_analysis.json")


def main():
    out = {}
    log_lines = []
    for m in range(3, 37):
        try:
            sols = load_known(m, cap=200)
        except Exception as e:
            log_lines.append(f"m={m}: load_known ERROR: {e!r} (skip)")
            continue
        if not sols:
            log_lines.append(f"m={m}: (no known solutions loaded -- skip)")
            continue
        types = []
        n2f = 0
        for pairs in sols:
            cells = extract_topleft(pairs, m)
            ok, _ = check_2factor(cells, m)
            n2f += ok
            types.append(tuple(cycle_decomp(cells, m)))
        c = Counter(types)
        distinct = len(c)
        log_lines.append(
            f"m={m:2d}: n={2*m:2d} nsol={len(sols):3d} 2F_ok={n2f:3d} "
            f"distinct_cycle_types={distinct}")
        for cyc, cnt in c.most_common(6):
            log_lines.append(f"        {list(cyc)}  x{cnt}")
        out[m] = {"n": 2 * m, "nsol": len(sols), "twofactor_ok": n2f,
                  "distinct_types": distinct,
                  "types": [[list(k), v] for k, v in c.most_common()]}

    ts = datetime.now().isoformat(timespec='seconds')
    with open(OUT, "w") as f:
        json.dump({"ts": ts, "data": out}, f, indent=1)

    report = "\n".join(log_lines)
    print(report)
    print(f"\nwritten {OUT}  ({ts})")
    # also append to the persistent theory log
    with open(os.path.join(HERE, "results", "theory_log.txt"), "a") as f:
        f.write(f"\n[{ts}] cycle_analysis (known solutions m=3..36)\n{report}\n")


if __name__ == "__main__":
    main()

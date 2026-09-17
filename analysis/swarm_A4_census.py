"""
swarm_A4_census.py — Census of m values around 37.

For each m in {31, 33, 35, 36, 38, 39, 41, 43}, generate >= 30 random 2-factors,
run clause enumeration + SAT/MaxSAT check, record results.
Key question: do composite m's show systematically fewer violations than primes?

Optimized for ~20 minute total budget:
  - 10s time_limit per MaxSAT check
  - 20 trials per m (small m) / 15 trials per m (large m)
  - Parallel workers across m values

Usage:
  "C:/Users/djr82/.workbuddy/binaries/python/envs/default/Scripts/python.exe" swarm_A4_census.py
"""
import sys, os, json, time, math, random, argparse, traceback, multiprocessing
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from solver_2factor_sat_pipeline import generate_2factor_full, enumerate_clauses, check_sat

RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Config ──
# Small m (31,33,35,36): faster enumeration → more trials
# Large m (38,39,41,43): slower enumeration → fewer trials
SMALL_M_TRIALS = 30
LARGE_M_TRIALS = 20
TIME_LIMIT = 10       # seconds per MaxSAT check
N_WORKERS = 4         # parallel workers
GLOBAL_SEED = 42

INTERIM_PATH = os.path.join(RESULTS_DIR, "swarm_A4_census_interim.json")
FINAL_PATH = os.path.join(RESULTS_DIR, "swarm_A4_census.json")
REPORT_PATH = os.path.join(RESULTS_DIR, "swarm_A4_report.md")

def is_prime(n):
    if n < 2: return False
    if n % 2 == 0: return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0: return False
        i += 2
    return True

SMALL_M = {31, 33, 35, 36}


def run_one_trial(m, trial_idx, seed, time_limit=10):
    """Run a single trial: generate 2-factor → enumerate clauses → SAT/MaxSAT.
    
    Returns a dict with results (JSON-serializable, no lambda/defaultdict).
    """
    start_wall = time.time()
    rng = random.Random(seed)
    
    try:
        edges = generate_2factor_full(m, rng, allow_twocycles=True)
    except Exception as e:
        return {"m": m, "trial": trial_idx, "error": f"gen_2factor: {e}", "time_s": round(time.time()-start_wall, 3)}
    
    # edge stats
    edge_counts = defaultdict(int)
    for u, v in edges:
        edge_counts[(u, v)] += 1
    n_twocycles = sum(1 for c in edge_counts.values() if c >= 2)
    
    # enumerate
    try:
        clauses, _ = enumerate_clauses(m, edges, verbose=False)
    except Exception as e:
        return {"m": m, "trial": trial_idx, "error": f"enumerate: {e}", "time_s": round(time.time()-start_wall, 3)}
    
    n_clauses = len(clauses)
    res = {
        "m": m, "trial": trial_idx, "n_edges": len(edges), "edges": edges,
        "n_clauses": n_clauses, "has_twocycle": n_twocycles > 0, "n_twocycles": n_twocycles,
        "seed_used": seed,
    }
    
    if n_clauses == 0:
        res["sat_status"] = "TRIVIAL_SAT"
        res["sat_found"] = True
        res["min_violations"] = 0
        res["proven_optimal"] = True
        res["breakthrough"] = True
        res["time_s"] = round(time.time() - start_wall, 3)
        return res
    
    # SAT/MaxSAT
    try:
        sat_res = check_sat(m, edges, clauses, time_limit=time_limit, verbose=False)
    except Exception as e:
        res["error"] = f"check_sat: {e}"
        res["time_s"] = round(time.time() - start_wall, 3)
        return res
    
    total_time = time.time() - start_wall
    min_viol = sat_res.get("maxsat_min_violations", sat_res.get("min_violations", -1))
    
    res.update({
        "sat_status": sat_res.get("sat_status", "?"),
        "sat_found": sat_res.get("sat_found", False),
        "maxsat_status": sat_res.get("maxsat_status", "?"),
        "min_violations": min_viol,
        "maxsat_proven_optimal": sat_res.get("maxsat_proven_optimal", False),
        "time_s": round(total_time, 3),
        "breakthrough": (min_viol == 0) and (sat_res.get("sat_found", False) or sat_res.get("maxsat_status") == "OPTIMAL"),
    })
    
    if res["breakthrough"]:
        res["orientation"] = sat_res.get("orientation", [])
        res["cells"] = sat_res.get("cells", [])
    
    return res


def run_m_value(m, trials, seed_base, time_limit=10):
    """Run all trials for a single m value. Returns (m, trial_results, summary_dict)."""
    print(f"\n--- m={m} ({'prime' if is_prime(m) else 'composite'}) starting ---", flush=True)
    t_start = time.time()
    
    results = []
    rng = random.Random(seed_base + m)
    best_clauses = float("inf")
    best_min_viol = float("inf")
    best_trial = None
    
    for ti in range(trials):
        trial_seed = rng.randint(0, 2**31)
        tr = run_one_trial(m, ti, trial_seed, time_limit=time_limit)
        results.append(tr)
        
        nc = tr.get("n_clauses", -1)
        if nc >= 0 and nc < best_clauses:
            best_clauses = nc
        
        mv = tr.get("min_violations", -1)
        if mv >= 0 and mv < best_min_viol:
            best_min_viol = mv
            best_trial = tr
        
        if tr.get("breakthrough"):
            print(f"  *** BREAKTHROUGH m={m} trial {ti}: 0 violations! ***", flush=True)
        elif mv >= 0 and mv == best_min_viol:
            pass  # already printed
        elif tr.get("error"):
            print(f"  Trial {ti} ERROR: {tr['error']}", flush=True)
    
    elapsed = time.time() - t_start
    
    # Compute stats
    nc_list = [r["n_clauses"] for r in results if r.get("n_clauses", -1) >= 0]
    mv_list = [r["min_violations"] for r in results if r.get("min_violations", -1) >= 0]
    tm_list = [r["time_s"] for r in results]
    
    summary = {
        "m": m, "is_prime": is_prime(m), "n_trials": len(results),
        "n_errors": sum(1 for r in results if "error" in r),
        "n_breakthroughs": sum(1 for r in results if r.get("breakthrough")),
        "elapsed_s": round(elapsed, 1),
        "clause_count": {"min": min(nc_list), "mean": round(sum(nc_list)/len(nc_list), 1),
                         "median": sorted(nc_list)[len(nc_list)//2]} if nc_list else None,
        "min_violations": {"min": min(mv_list), "mean": round(sum(mv_list)/len(mv_list), 1),
                           "median": sorted(mv_list)[len(mv_list)//2]} if mv_list else None,
        "time": {"min": round(min(tm_list),3), "max": round(max(tm_list),3),
                 "mean": round(sum(tm_list)/len(tm_list),3)} if tm_list else None,
        "best_clauses": best_clauses,
        "best_min_violations": best_min_viol,
        "best_trial_tidx": best_trial["trial"] if best_trial else None,
    }
    
    print(f"  m={m} done: {trials} trials in {elapsed:.0f}s | "
          f"clauses={summary['clause_count']['min']}/{summary['clause_count']['mean']}/{summary['clause_count']['median']} | "
          f"viol={summary['min_violations']['min']}/{summary['min_violations']['mean']}/{summary['min_violations']['median']}", flush=True)
    
    return {"m": m, "results": results, "summary": summary}


def generate_report(all_results_dict):
    """Generate markdown report from all_results dict."""
    lines = []
    lines.append("# Swarm A4: Census of m values around 37")
    lines.append("")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| m | prime? | n_trials | clauses (min/mean/median) | violations (min/mean/median) | proven_optimal | breakthroughs | time_elapsed |")
    lines.append("|---|--------|----------|---------------------------|------------------------------|----------------|---------------|--------------|")
    
    for m_str in sorted(all_results_dict.keys(), key=lambda x: int(x)):
        s = all_results_dict[m_str]["summary"]
        cc = s["clause_count"]
        mv = s["min_violations"]
        p_opt = sum(1 for r in all_results_dict[m_str]["results"]
                    if r.get("maxsat_proven_optimal", False))
        line = (f"| {s['m']} | {'Y' if s['is_prime'] else 'N'} | {s['n_trials']} | "
                f"{cc['min']}/{cc['mean']}/{cc['median']} | "
                f"{mv['min']}/{mv['mean']}/{mv['median']} | "
                f"{p_opt}/{s['n_trials']} | "
                f"{s['n_breakthroughs']} | {s['elapsed_s']}s |")
        lines.append(line)
    
    lines.append("")
    lines.append("## Key Question: Prime vs Composite")
    lines.append("")
    
    primes = sorted([int(k) for k in all_results_dict if all_results_dict[k]["summary"]["is_prime"]])
    composites = sorted([int(k) for k in all_results_dict if not all_results_dict[k]["summary"]["is_prime"]])
    
    lines.append(f"- Primes tested: {primes}")
    lines.append(f"- Composites tested: {composites}")
    lines.append("")
    
    for group_name, group in [("Primes", primes), ("Composites", composites)]:
        viol_means = [all_results_dict[str(m)]["summary"]["min_violations"]["mean"] for m in group]
        clause_means = [all_results_dict[str(m)]["summary"]["clause_count"]["mean"] for m in group]
        lines.append(f"**{group_name}:**")
        for i, m in enumerate(group):
            lines.append(f"  - m={m}: mean violations={viol_means[i]:.1f}, mean clauses={clause_means[i]:.1f}")
        lines.append(f"  - Overall avg violations: {sum(viol_means)/len(viol_means):.1f}")
        lines.append(f"  - Overall avg clauses: {sum(clause_means)/len(clause_means):.1f}")
        lines.append("")
    
    # Compare
    if primes and composites:
        pv = [all_results_dict[str(m)]["summary"]["min_violations"]["mean"] for m in primes]
        cv = [all_results_dict[str(m)]["summary"]["min_violations"]["mean"] for m in composites]
        pc = [all_results_dict[str(m)]["summary"]["clause_count"]["mean"] for m in primes]
        cc_list = [all_results_dict[str(m)]["summary"]["clause_count"]["mean"] for m in composites]
        avg_pv = sum(pv)/len(pv)
        avg_cv = sum(cv)/len(cv)
        avg_pc = sum(pc)/len(pc)
        avg_cc = sum(cc_list)/len(cc_list)
        
        lines.append(f"**Comparison:**")
        lines.append(f"- Prime mean violations: {avg_pv:.1f} vs Composite mean violations: {avg_cv:.1f}")
        lines.append(f"- Prime mean clauses: {avg_pc:.1f} vs Composite mean clauses: {avg_cc:.1f}")
        ratio_v = avg_pv / avg_cv if avg_cv > 0 else float('inf')
        lines.append(f"- Violation ratio (prime/composite): {ratio_v:.2f}")
        if ratio_v > 1.15:
            lines.append("- **CONCLUSION**: Primes show systematically MORE violations → supports hypothesis")
        elif ratio_v < 0.85:
            lines.append("- **CONCLUSION**: Composites show more violations → contradicts hypothesis")
        else:
            lines.append("- **CONCLUSION**: No significant difference between prime and composite m values")
    
    lines.append("")
    lines.append("## Best 2-Factor Found for Each m")
    lines.append("")
    
    for m_str in sorted(all_results_dict.keys(), key=lambda x: int(x)):
        s = all_results_dict[m_str]["summary"]
        results = all_results_dict[m_str]["results"]
        # Find best (lowest violations)
        best_r = min(results, key=lambda r: r.get("min_violations", 9999) if r.get("min_violations", -1) >= 0 else 9999)
        lines.append(f"### m={s['m']} ({'prime' if s['is_prime'] else 'composite'})")
        lines.append(f"- Best violations: {best_r.get('min_violations', '?')}")
        lines.append(f"- Best clause count: {best_r.get('n_clauses', '?')}")
        lines.append(f"- Trial idx: {best_r.get('trial', '?')}")
        if best_r.get("breakthrough"):
            lines.append(f"- **BREAKTHROUGH: SAT solution found!**")
            lines.append(f"- Orientation: {best_r.get('orientation', [])}")
        lines.append(f"- Has 2-cycle: {best_r.get('has_twocycle', '?')} ({best_r.get('n_twocycles', 0)})")
        lines.append(f"- Proven optimal: {best_r.get('maxsat_proven_optimal', '?')}")
        lines.append(f"- Edges count: {best_r.get('n_edges', 0)}")
        lines.append("")
    
    # Breakthroughs
    n_bt = sum(s["summary"]["n_breakthroughs"] for s in all_results_dict.values())
    if n_bt > 0:
        lines.append("## BREAKTHROUGHS FOUND")
        lines.append("")
        for m_str in sorted(all_results_dict.keys(), key=lambda x: int(x)):
            s = all_results_dict[m_str]["summary"]
            if s["n_breakthroughs"] > 0:
                lines.append(f"### m={s['m']}: {s['n_breakthroughs']} breakthrough(s)")
                for r in all_results_dict[m_str]["results"]:
                    if r.get("breakthrough"):
                        lines.append(f"- Trial {r['trial']}: {r['n_clauses']} clauses")
                        lines.append(f"  - Orientation: {r.get('orientation', [])}")
                        lines.append(f"  - Time: {r.get('time_s', 0)}s")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-values", type=int, nargs="+", default=[31, 33, 35, 36, 38, 39, 41, 43])
    parser.add_argument("--trials", type=int, default=None)
    parser.add_argument("--time-limit", type=int, default=TIME_LIMIT)
    parser.add_argument("--workers", type=int, default=N_WORKERS)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    
    time_limit = args.time_limit
    
    if args.report_only:
        for path in [INTERIM_PATH, FINAL_PATH]:
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                report = generate_report(data)
                with open(REPORT_PATH, "w") as f:
                    f.write(report)
                print(f"Report from {path} → {REPORT_PATH}")
                return
        print("No results files found")
        return
    
    m_values = args.m_values
    trials_map = {}
    for m in m_values:
        if args.trials:
            trials_map[m] = args.trials
        else:
            trials_map[m] = SMALL_M_TRIALS if m in SMALL_M else LARGE_M_TRIALS
    
    print(f"Swarm A4 Census: m_values={m_values}, trials_map={trials_map}")
    print(f"  time_limit={time_limit}s, workers={args.workers}, seed={args.seed}")
    print(f"  Estimated budget: ", sum(trials_map.values()), "total trials")
    t_start = time.time()
    
    # Run each m value sequentially with a global time budget check
    all_results = {}
    for m in m_values:
        elapsed = time.time() - t_start
        if elapsed > 1100:  # ~18 minutes cap
            print(f"\n!!! Global time budget (~20 min) nearly reached. Saving partial results. !!!")
            break
        
        m_data = run_m_value(m, trials_map[m], args.seed, time_limit=time_limit)
        all_results[str(m)] = m_data
        
        # Save interim
        with open(INTERIM_PATH, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
    
    t_total = time.time() - t_start
    print(f"\nTotal elapsed: {t_total:.0f}s")
    
    # Save final
    with open(FINAL_PATH, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Final results → {FINAL_PATH}")
    
    # Report
    report = generate_report(all_results)
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"Report → {REPORT_PATH}")
    
    # Quick summary
    print("\n" + "="*60)
    print("CENSUS SUMMARY")
    print("="*60)
    for m_str in sorted(all_results.keys(), key=lambda x: int(x)):
        s = all_results[m_str]["summary"]
        cc = s["clause_count"]
        mv = s["min_violations"]
        p = "P" if s["is_prime"] else "C"
        print(f"  m={s['m']:2d} [{p}] n={s['n_trials']:2d} "
              f"cls={cc['min']:>4d}/{cc['mean']:>6.1f}/{cc['median']:>4d} "
              f"viol={mv['min']:>3d}/{mv['mean']:>5.1f}/{mv['median']:>3d} "
              f"bt={s['n_breakthroughs']}")


if __name__ == "__main__":
    main()

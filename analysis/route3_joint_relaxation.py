"""
route3_joint_relaxation.py — Joint (2-factor × Ising) relaxation prototype.

Route 3 of the m=37 attack: the outer variable is the 2-factor, the inner is the
signed-Ising orientation. For a FIXED 2-factor the Ising min_viol has a rigorous
SDP lower bound (GW MAX-CUT relaxation, sdp_frustration_cert.sdp_min_viol_lb).
Route 3 = sample MANY 2-factors (diverse, independent) and collect their SDP
lower bounds. If EVERY diverse 2-factor has a strictly positive SDP bound, that
is strong evidence that m=37 has no satisfiable 2-factor (impossibility).

Two phases:
  (A) VALIDATION on small m (5, 6): enumerate ALL 2-factors, compute exact
      min_viol via CP-SAT and the SDP lower bound. Confirm SDP_lb <= true_min
      for every config, and SDP_lb <= 0 whenever the config is SAT. This proves
      the SDP is a valid (non-optimistic) discriminator.
  (B) m=37 broad diverse sample: generate N independent random 2-factors,
      compute SDP lower bound for each; report min / max / distribution and the
      structural features (n_clauses, 2-factor cycle lengths, #frustrated
      triangles in G_J) to look for an analytic universal lower bound.

Outputs incrementally to results/route3_joint_relaxation.json.
"""
import sys, os, json, time, random, itertools
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solver_2factor_sat_pipeline import enumerate_clauses, generate_2factor_full, check_sat
from ising_reduction import build_J
from sdp_frustration_cert import sdp_min_viol_lb

OUT = "results/route3_joint_relaxation.json"
results = {"validation": {}, "m37_sample": [], "meta": {}}


# ── 2-factor enumeration / generation ────────────────────────────────────────
def all_2factors(m):
    """Enumerate all 2-factors on {0..m-1} via permutations (dedup cycle covers)."""
    seen = set()
    out = []
    for perm in itertools.permutations(range(m)):
        visited = [False] * m
        edges = []
        for i in range(m):
            if not visited[i]:
                cyc = []
                j = i
                while not visited[j]:
                    visited[j] = True
                    cyc.append(j)
                    j = perm[j]
                for k in range(len(cyc)):
                    a, b = cyc[k], cyc[(k + 1) % len(cyc)]
                    edges.append((a, b) if a <= b else (b, a))
        key = frozenset(edges)
        if key not in seen:
            seen.add(key)
            out.append(sorted(edges))
    return out


def random_2factor(m, rng):
    return generate_2factor_full(m, rng)


def cycle_lengths(edges, m):
    """DFS the 2-regular graph into cycles; return sorted list of lengths."""
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = [False] * m
    lengths = []
    for s in range(m):
        if not visited[s]:
            cur = s
            prev = -1
            L = 0
            while not visited[cur]:
                visited[cur] = True
                nxt = adj[cur][0] if adj[cur][1] == prev else adj[cur][1]
                prev = cur
                cur = nxt
                L += 1
            lengths.append(L)
    return sorted(lengths)


def n_frustrated_triangles(J):
    """Count signed triangles (3-cycles) in G_J with negative product of signs."""
    sign = {}
    for (i, j), val in J.items():
        sign[(i, j) if i < j else (j, i)] = 1 if val > 0 else -1
    nodes = set()
    for (i, j) in sign:
        nodes.add(i); nodes.add(j)
    adj = defaultdict(set)
    for (i, j) in sign:
        adj[i].add(j); adj[j].add(i)
    cnt = 0
    for i in nodes:
        for j in adj[i]:
            if j <= i:
                continue
            for k in adj[j]:
                if k <= j:
                    continue
                if k in adj[i]:
                    p = sign[(i, j) if i < j else (j, i)] * \
                        sign[(j, k) if j < k else (k, j)] * \
                        sign[(i, k) if i < k else (k, i)]
                    if p < 0:
                        cnt += 1
    return cnt


# ── per-config evaluation ─────────────────────────────────────────────────────
def evaluate(m, edges, compute_exact=False, sdp_time=60):
    rec = {"m": m, "n_edges": len(edges)}
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, missing, n_cl = build_J(clauses)
    rec["n_clauses"] = n_cl
    rec["closure_missing"] = missing
    rec["cycle_lengths"] = cycle_lengths(edges, m)
    rec["n_odd_cycles"] = sum(1 for L in rec["cycle_lengths"] if L % 2 == 1)
    rec["n_frustrated_triangles"] = n_frustrated_triangles(J)
    # SDP lower bound
    try:
        sdp = sdp_min_viol_lb(m, edges, time_limit=sdp_time)
        rec["sdp_lb"] = sdp["min_viol_lb_sdp"]
        rec["sdp_status"] = sdp["sdp_status"]
        rec["sdp_M"] = sdp["M_sdp"]
    except Exception as e:
        rec["sdp_lb"] = None
        rec["sdp_error"] = repr(e)
    # exact min_viol (small m only)
    if compute_exact:
        try:
            res = check_sat(m, edges, clauses, time_limit=120, verbose=False)
            if res.get("sat_found"):
                rec["true_min"] = 0
            else:
                rec["true_min"] = res.get("maxsat_min_violations",
                                          res.get("min_violations"))
            rec["true_proven"] = res.get("maxsat_proven_optimal", False)
        except Exception as e:
            rec["true_error"] = repr(e)
    return rec


def save():
    json.dump(results, open(OUT, "w"), indent=2)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    # ── (A) validation on small m ──
    for m in (5, 6):
        print(f"\n===== VALIDATION m={m}: enumerate all 2-factors =====", flush=True)
        configs = all_2factors(m)
        print(f"  {len(configs)} distinct 2-factors", flush=True)
        recs = []
        ok_lb = 0
        ok_sat = 0
        sat_seen = 0
        for idx, edges in enumerate(configs):
            rec = evaluate(m, edges, compute_exact=True, sdp_time=30)
            # validate
            if rec.get("true_min") is not None and rec.get("sdp_lb") is not None:
                if rec["sdp_lb"] <= rec["true_min"] + 1e-6:
                    ok_lb += 1
                if rec["true_min"] == 0:
                    sat_seen += 1
                    if rec["sdp_lb"] <= 0 + 1e-6:
                        ok_sat += 1
            recs.append(rec)
            if (idx + 1) % 10 == 0 or idx == len(configs) - 1:
                print(f"  [{idx+1}/{len(configs)}] sdp_lb={rec.get('sdp_lb')} "
                      f"true_min={rec.get('true_min')} n_cl={rec['n_clauses']} "
                      f"cyc={rec['cycle_lengths']}", flush=True)
        results["validation"][str(m)] = {
            "n_configs": len(configs),
            "n_sdp_le_true": ok_lb,
            "n_sat_configs": sat_seen,
            "n_sat_with_sdp_le0": ok_sat,
            "records": recs,
        }
        save()
        print(f"  VALIDATION m={m}: SDP<=true for {ok_lb}/{len(configs)}; "
              f"SAT configs={sat_seen}, of which SDP<=0: {ok_sat}", flush=True)

    # ── (B) m=37 broad diverse sample ──
    print(f"\n===== m=37 diverse 2-factor SDP sample =====", flush=True)
    rng = random.Random(12345)
    N = 20
    lbs = []
    for i in range(N):
        edges = random_2factor(37, rng)
        rec = evaluate(37, edges, compute_exact=False, sdp_time=60)
        rec["sample_idx"] = i
        results["m37_sample"].append(rec)
        if rec.get("sdp_lb") is not None:
            lbs.append(rec["sdp_lb"])
        print(f"  [{i+1}/{N}] sdp_lb={rec.get('sdp_lb')} n_cl={rec['n_clauses']} "
              f"cyc_lens={rec['cycle_lengths']} n_odd={rec['n_odd_cycles']} "
              f"fr_tri={rec['n_frustrated_triangles']}", flush=True)
        save()
    if lbs:
        results["meta"]["m37_sample_summary"] = {
            "n": len(lbs), "min_lb": min(lbs), "max_lb": max(lbs),
            "mean_lb": sum(lbs) / len(lbs),
        }
        print(f"\n  m=37 sample: min_sdp_lb={min(lbs):.3f} max={max(lbs):.3f} "
              f"mean={sum(lbs)/len(lbs):.3f}", flush=True)
    results["meta"]["total_time_s"] = round(time.time() - t0, 1)
    save()
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()

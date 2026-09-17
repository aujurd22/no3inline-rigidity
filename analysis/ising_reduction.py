"""
ising_reduction.py — Rewrite the rot4-NTIL direction subproblem as signed NAE / Ising / MaxCut.

For a FIXED 2-factor, each forbidden pattern (a,b,c,bits) pairs with its complement
(a,b,c,bits^7) under 180° C4 (collinearity is rotation invariant). Summing the
indicator over a complementary pair gives a PURE QUADRATIC form:

    1_{s=a}+1_{s=-a} = 1/4 (1 + a_i a_j s_i s_j + a_i a_k s_i s_k + a_j a_k s_j s_k)

so the total violation energy is

    V_E(s) = P_E/4 + 1/4 Σ_{i<j} J^E_{ij} s_i s_j ,  s_i = 2 t_i - 1 ,

with P_E = #clauses/2.  => the direction problem is a 37-vertex signed weighted
MaxCut / Ising ground-state problem, NOT a genuine cubic 3-SAT.

This script:
  1. Verifies the complement-closure + quadratic reduction (V_E == brute-force count).
  2. Builds J^E for the m=37-408 (16-viol) and m=37-448 (17-viol, proven) configs and
     for the m=36 satisfiable solution.
  3. Compares signed-graph invariants: frustration index, balanceability, spectral
     lower bound, frustrated short cycles.
  4. Extracts the frustrated core (edges / cycles involved in the minimal violations).
"""
import sys, os, json, time, random
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solver_2factor_sat_pipeline import enumerate_clauses, check_sat

# ── J builder ────────────────────────────────────────────────────────────────
def build_J(clauses):
    """Return (J, closure_missing, n_clauses). J is dict (i,j)->Σ a_i a_j over clauses."""
    J = defaultdict(int)
    clause_set = set(clauses)
    missing = 0
    for (a, b, c, bits) in clauses:
        comp = bits ^ 7
        if (a, b, c, comp) not in clause_set:
            missing += 1
        sa = 2 * ((bits >> 0) & 1) - 1
        sb = 2 * ((bits >> 1) & 1) - 1
        sc = 2 * ((bits >> 2) & 1) - 1
        for (i, j), prod in [((a, b), sa * sb), ((a, c), sa * sc), ((b, c), sb * sc)]:
            lo, hi = (i, j) if i < j else (j, i)
            J[(lo, hi)] += prod
    return dict(J), missing, len(clauses)


def energy_from_orientation(J, n_clauses, orient):
    # J is summed over ALL clauses; the user's J^E is summed over complementary
    # PAIRS (= clauses/2), so J_code = 2 * J^E_user.  Hence:
    #   V_E = n_clauses/8 + (1/8) * Σ_{clauses} (a_i a_j s_i s_j)
    #      = n_clauses/8 + (1/8) * Σ J_code s_i s_j.
    s = [2 * o - 1 for o in orient]
    E = 0
    for (i, j), val in J.items():
        E += val * s[i] * s[j]
    return n_clauses / 8.0 + E / 8.0


def count_violations_bruteforce(clauses, orient):
    cnt = 0
    for (a, b, c, bits) in clauses:
        ba = (bits >> 0) & 1
        bb = (bits >> 1) & 1
        bc = (bits >> 2) & 1
        if orient[a] == ba and orient[b] == bb and orient[c] == bc:
            cnt += 1
    return cnt


def verify_reduction(clauses, J, orient_opt, n_rand=8, seed=0):
    """Check V_E(s) == brute-force violation count for the optimal + random orientations."""
    rng = random.Random(seed)
    n_clauses = len(clauses)
    checks = []
    # optimal orientation
    vo = count_violations_bruteforce(clauses, orient_opt)
    eo = energy_from_orientation(J, n_clauses, orient_opt)
    checks.append(("optimal", vo, round(eo, 6)))
    for k in range(n_rand):
        o = [rng.randint(0, 1) for _ in range(len(orient_opt))]
        v = count_violations_bruteforce(clauses, o)
        e = energy_from_orientation(J, n_clauses, o)
        ok = abs(v - e) < 1e-9
        checks.append((f"rand{k}", v, round(e, 6)))
    allok = all(abs(v - e) < 1e-9 for _, v, e in checks)
    return allok, checks


# ── signed-graph analysis ─────────────────────────────────────────────────────
def spectral_bound(J, n_clauses, n):
    """Rigorous lower bound on min violations via Rayleigh quotient:
       E(s) = s^T M s, M = J/2 (diag 0)  =>  E(s) >= n * λ_min(M) = (n/2) λ_min(Jmat)."""
    M = np.zeros((n, n))
    for (i, j), val in J.items():
        M[i, j] = val / 2.0
        M[j, i] = val / 2.0
    w = np.linalg.eigvalsh(M)
    lam_min = w[0]
    # E(s) = s^T A s, A = J/2 (diag 0); Rayleigh: E(s) >= n * λ_min(A) = n*lam_min.
    # min_viol = n_cl/8 + E_min/8  =>  viol_lb = n_cl/8 + E_lb/8.
    E_lb = n * lam_min
    viol_lb = n_clauses / 8.0 + E_lb / 8.0
    return float(lam_min), float(viol_lb)


def frustrated_cycles(J, max_len=5):
    """Enumerate short cycles in the signed graph; count frustrated (sign product = -1)."""
    adj = defaultdict(list)
    sign = {}
    for (i, j), val in J.items():
        adj[i].append(j)
        adj[j].append(i)
        sign[(i, j) if i < j else (j, i)] = val
    nodes = list(adj.keys())
    frustrated_by_len = defaultdict(int)
    total_by_len = defaultdict(int)

    def sgn(i, j):
        return sign[(i, j) if i < j else (j, i)]

    # DFS for cycles up to max_len
    def dfs(start, cur, depth, visited, prod):
        if depth >= 3:
            # close cycle if cur connects back to start and start not in visited path
            if start in adj[cur] and depth <= max_len:
                total_by_len[depth] += 1
                if prod * sgn(cur, start) < 0:
                    frustrated_by_len[depth] += 1
        if depth == max_len:
            return
        for nxt in adj[cur]:
            if nxt == start:
                continue
            if nxt in visited:
                continue
            visited.add(nxt)
            dfs(start, nxt, depth + 1, visited, prod * sgn(cur, nxt))
            visited.discard(nxt)

    seen = set()
    for s0 in nodes:
        dfs(s0, s0, 1, {s0}, 1)
    return dict(total_by_len), dict(frustrated_by_len)


def frustrated_core(clauses, orient_opt):
    """Edges + triples involved in the violated clauses at the optimal orientation."""
    violated = [c for c in clauses if count_violations_bruteforce([c], orient_opt) == 1]
    edges_involved = set()
    for (a, b, c, bits) in violated:
        edges_involved.update([a, b, c])
    return violated, sorted(edges_involved)


# ── main analysis ──────────────────────────────────────────────────────────
def analyze(label, m, edges, orient_opt=None, time_limit=60, proven_min=None):
    print(f"\n########## {label} (m={m}, {len(edges)} edges) ##########", flush=True)
    t0 = time.time()
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    n_cl = len(clauses)
    J, missing, _ = build_J(clauses)
    print(f"  clauses={n_cl}, complementary-pair closure missing={missing} "
          f"(0 => pure quadratic Ising)", flush=True)

    if orient_opt is None:
        res = check_sat(m, edges, clauses, time_limit=time_limit, verbose=False)
        orient_opt = res.get("orientation") or res.get("maxsat_solution")
        if res.get("sat_found"):
            min_viol = 0
            proven = True
            print(f"  CP-SAT: SAT (min_violations=0, proven_optimal=True)", flush=True)
        else:
            proven = res.get("maxsat_proven_optimal", False)
            min_viol = res.get("maxsat_min_violations", res.get("min_violations"))
            print(f"  CP-SAT: min_violations={min_viol}, proven_optimal={proven} "
                  f"(status {res.get('maxsat_status', res.get('sat_status'))})", flush=True)
    else:
        min_viol = proven_min
        proven = (proven_min is not None)
        print(f"  using provided optimal orientation: min_violations={min_viol} "
              f"(proven_optimal={proven})", flush=True)

    # verify reduction
    ok, checks = verify_reduction(clauses, J, orient_opt, n_rand=8)
    print(f"  reduction V_E == brute-force: {ok} "
          f"(optimal: brute={checks[0][1]} ising={checks[0][2]})", flush=True)
    if orient_opt is not None and checks[0][1] != min_viol:
        print(f"  *** WARNING: provided orientation yields {checks[0][1]} violations "
              f"but expected {min_viol} -> edges may not match orientation! ***", flush=True)

    # energy / frustration  (min_viol = n_cl/8 + E_min/8  =>  E_min = 8*min_viol - n_cl)
    E_min = 8 * min_viol - n_cl
    sum_abs = sum(abs(v) for v in J.values())
    frustration = (sum_abs - E_min) / 2.0
    lam_min, viol_lb = spectral_bound(J, n_cl, m)
    print(f"  E_min(ising)={E_min:.1f}, Σ|J|={sum_abs}, "
          f"frustration_index={frustration:.1f}", flush=True)
    print(f"  spectral λ_min(Jmat)={lam_min:.3f}, spectral lower bound on min_viol "
          f"≥ {viol_lb:.2f}", flush=True)

    # frustrated core + cycles
    violated, core_edges = frustrated_core(clauses, orient_opt)
    tot_cyc, fr_cyc = frustrated_cycles(J, max_len=5)
    print(f"  frustrated core: {len(violated)} violated clauses over "
          f"{len(core_edges)} edges {core_edges}", flush=True)
    print(f"  frustrated short cycles (len: total/frustrated): "
          + ", ".join(f"{k}:{tot_cyc.get(k,0)}/{fr_cyc.get(k,0)}"
                      for k in sorted(set(tot_cyc)|set(fr_cyc))), flush=True)

    return {
        "label": label, "m": m, "n_edges": len(edges), "n_clauses": n_cl,
        "closure_missing": missing, "reduction_ok": ok,
        "min_violations": min_viol, "proven_optimal": proven,
        "E_min": E_min, "sum_abs_J": sum_abs, "frustration_index": frustration,
        "spectral_lambda_min": lam_min, "spectral_viol_lb": viol_lb,
        "n_violated_clauses": len(violated), "core_edges": core_edges,
        "core_edge_count": len(core_edges),
        "frustrated_cycles_total": tot_cyc, "frustrated_cycles_frustrated": fr_cyc,
        "enum_time_s": round(time.time() - t0, 1),
    }


def main():
    rng = random.Random(1)
    results = {}

    # m=37 408 config (best, 16 violations, NOT yet proven optimal)
    d408 = json.load(open("results/config_408_edges.json"))
    edges408 = [tuple(e) for e in d408["edges"]]
    r408 = analyze("m37-408 (best, 16 viol)", 37, edges408,
                   orient_opt=None, time_limit=180)
    results["m37_408"] = r408

    # m=37 448 config (17 violations, PROVEN optimal)
    s448 = json.load(open("results/mutation_448_satchk.json"))
    edges448 = []
    for x in s448["edges"]:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            u, v = x[0], x[1]
        elif isinstance(x, int):
            u = v = x
        else:
            raise ValueError(f"unexpected edge encoding: {x!r}")
        edges448.append((min(u, v), max(u, v)))
    o448 = json.load(open("results/mutation_448_maxsat_long.json"))["orientation"]
    r448 = analyze("m37-448 (proven 17 viol)", 37, edges448,
                   orient_opt=o448, proven_min=17)
    results["m37_448"] = r448

    # m=36 satisfiable solution
    m36 = json.load(open("results/solutions/m36.json"))
    cells36 = [tuple(c) for c in m36["cells"]]
    edges36 = [tuple(sorted(c)) for c in cells36]
    r36 = analyze("m36-solution (SAT, 670 clauses)", 36, edges36,
                  orient_opt=None, time_limit=60)
    results["m36"] = r36

    json.dump(results, open("results/ising_reduction_report.json", "w"), indent=2)
    print("\n==== SUMMARY ====")
    for k, r in results.items():
        print(f"  {k}: viol={r['min_violations']} proven={r['proven_optimal']} "
              f"closure_missing={r['closure_missing']} reduction_ok={r['reduction_ok']} "
              f"frustration={r['frustration_index']:.1f} "
              f"spec_lb={r['spectral_viol_lb']:.2f} core_edges={r['core_edge_count']}")
    print("saved results/ising_reduction_report.json")


if __name__ == "__main__":
    main()

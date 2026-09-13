#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Four-tightness census (numpy vectorized, resumable).
Definition: minimum non-zero |F| over ordered triples of pairwise distinct representatives.
  rot4: six classes F1..F6; half-turn (rot2/rct4): F1, F2 only.
Cross-validated against an independent pure-Python reference before scaling out."""
import sys, os, json, time, glob
import numpy as np
sys.path.insert(0, r"D:\djr82\Documents\workbuddy\night_research_20260904\outputs\tools")
from audit_batch import load_blocks

DB = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\solutions_unified"
FEW = r"D:\djr82\Documents\workbuddy\night_research_20260904\outputs\T1_configs\few"
OUT = r"D:\djr82\Documents\workbuddy\night_research_20260904\outputs\T18_fourtight"
os.makedirs(OUT, exist_ok=True)
PROG = os.path.join(OUT, "progress.json")
JSONL = os.path.join(OUT, "per_solution.jsonl")
BIG = 10 ** 9


def reps_rot4(pts, n):
    m = n // 2
    S = set(pts)
    out, seen = [], set()
    for p in pts:
        if p in seen:
            continue
        x, y = p
        orb = [(x, y), (n - 1 - y, x), (n - 1 - x, n - 1 - y), (y, n - 1 - x)]
        if not all(q in S for q in orb):
            return None
        seen |= set(orb)
        r = [q for q in orb if q[0] < m and q[1] < m]
        if len(r) != 1:
            return None
        out.append(r[0])
    return out if len(out) == m else None


def reps_half(pts, n):
    mm = n - 1
    rs = set()
    for x, y in pts:
        a, b = (x, y), (mm - x, mm - y)
        rs.add(min(a, b))
    return sorted(rs) if len(rs) == n else None


def minF_vec(reps, kind):
    C = np.array([[2 * a - 1, 2 * b - 1] for a, b in reps], dtype=np.int64)
        # centred coordinates X=2x-(n-1); parity of n-1 varies with n, so pass n explicitly
    raise NotImplementedError  # filled by the wrapper below


def make_minF(kind):
    def fn(reps, n):
        mm = n - 1
        C = np.array([[2 * a - mm, 2 * b - mm] for a, b in reps], dtype=np.int64)
        X, Y = C[:, 0], C[:, 1]
        m = len(C)
        D = X[:, None] * Y[None, :] - Y[:, None] * X[None, :]
        Sx = X[:, None] * X[None, :] + Y[:, None] * Y[None, :]
        idx = np.arange(m)
        mins = [BIG] * (6 if kind == 'rot4' else 2)
        modok = True
        for i in range(m):
            mask = np.ones((m, m), dtype=bool)
            mask[i, :] = False
            mask[:, i] = False
            mask[idx, idx] = False
            A_D = D[i, :]
            A_S = Sx[i, :]
            # d3[j,k] = det(k,i) = -D[i,k]；s3[j,k] = <k,i> = S[i,k]
            if kind == 'rot4':
                Fs = [
                    A_D[:, None] + D - A_D[None, :],          # F1
                    A_S[:, None] + Sx - A_D[None, :],         # F2 = s1+s2+d3
                    A_D[:, None] - D + A_D[None, :],          # F3 = d1-d2-d3
                    A_S[:, None] + Sx + A_D[None, :],         # F4 = s1+s2-d3
                    A_D[:, None] - Sx + A_S[None, :],         # F5 = d1-s2+s3
                    A_D[:, None] + Sx - A_S[None, :],         # F6 = d1+s2-s3
                ]
            else:
                Fs = [
                    A_D[:, None] + D - A_D[None, :],          # F1
                    A_D[:, None] - D + A_D[None, :],          # F2 = d1-d2-d3
                ]
            for t, F in enumerate(Fs):
                modok &= bool(np.all(F[mask] % 4 == 0))
                A = np.abs(F[mask])
                A = A[A != 0]
                if A.size and A.min() < mins[t]:
                    mins[t] = int(A.min())
        return mins, modok
    return fn


def ref_minF_python(reps, n, kind):
    """Independent pure-Python reference: pairwise distinct ordered triples."""
    import itertools
    mm = n - 1
    C = [(2 * a - mm, 2 * b - mm) for a, b in reps]
    m = len(C)
    if kind == 'rot4':
        mins = [BIG] * 6
    else:
        mins = [BIG] * 2
    for i, j, k in itertools.permutations(range(m), 3):
        X1, Y1 = C[i]; X2, Y2 = C[j]; X3, Y3 = C[k]
        d1 = X1 * Y2 - Y1 * X2
        d2 = X2 * Y3 - Y2 * X3
        d3 = X3 * Y1 - Y3 * X1
        s1 = X1 * X2 + Y1 * Y2
        s2 = X2 * X3 + Y2 * Y3
        s3 = X3 * X1 + Y3 * Y1
        if kind == 'rot4':
            F = (d1 + d2 + d3, s1 + s2 + d3, d1 - d2 - d3, s1 + s2 - d3, d1 - s2 + s3, d1 + s2 - s3)
        else:
            F = (d1 + d2 + d3, d1 - d2 - d3)
        for t in range(len(mins)):
            if F[t] != 0 and abs(F[t]) < mins[t]:
                mins[t] = abs(F[t])
    return mins


def cross_validate():
    from audit_rot4 import orbits_and_reps
    fn4 = make_minF('rot4')
    fnh = make_minF('half')
    bad = tot = 0
    for n in range(6, 15, 2):
        fp = os.path.join(DB, f"n{n}_rot4.txt")
        if not os.path.exists(fp):
            continue
        for meta, pts in load_blocks(fp):
            if len(pts) != 2 * n:
                continue
            reps = [r for r, _ in orbits_and_reps(pts, n)]
            mine, _ = fn4(reps, n)
            ref = ref_minF_python(reps, n, 'rot4')
            tot += 1
            if ref != mine:
                bad += 1
                if bad <= 3:
                    print(f"MISMATCH n={n}: ref={ref} mine={mine}")
    # half-turn reference check (rct4 n=17 subset)
    fp = os.path.join(DB, "n17_rct4.txt")
    if os.path.exists(fp):
        for meta, pts in load_blocks(fp)[:3]:
            n = len(pts) // 2
            reps = reps_half(pts, n)
            mine, _ = fnh(reps, n)
            ref = ref_minF_python(reps, n, 'half')
            tot += 1
            if ref != mine:
                bad += 1
                print(f"MISMATCH rct4 n={n}: ref={ref} mine={mine}")
    print(f"cross-validation: {tot} solutions, {bad} mismatches")
    return bad == 0


def main():
    if '--crossval' in sys.argv:
        sys.exit(0 if cross_validate() else 1)
    fn4 = make_minF('rot4')
    fnh = make_minF('half')
    t0 = time.time()
    progress = json.load(open(PROG)) if os.path.exists(PROG) else {"done_files": []}
    done_files = set(progress["done_files"])
    f = open(JSONL, "a", encoding="utf-8")
    stats = {"solutions": 0, "four_tight": 0, "not4": 0, "mod4_violation": 0, "not4_examples": []}

    def process(fp, kind, sample=None):
        base = os.path.basename(fp)
        if base in done_files:
            return
        blocks = load_blocks(fp)
        if sample and len(blocks) > sample:
            import random
            random.seed(0)
            blocks = random.sample(blocks, sample)
        fn = fn4 if kind == 'rot4' else fnh
        for idx, (meta, pts) in enumerate(blocks):
            n = len(pts) // 2
            reps = reps_rot4(pts, n) if kind == 'rot4' else reps_half(pts, n)
            if reps is None:
                continue
            mins, modok = fn(reps, n)
            stats["solutions"] += 1
            if not modok:
                stats["mod4_violation"] += 1
            tight = all(v == 4 for v in mins)
            if tight:
                stats["four_tight"] += 1
            else:
                stats["not4"] += 1
                if len(stats["not4_examples"]) < 20:
                    stats["not4_examples"].append({"file": base, "idx": idx, "n": n, "minF": mins})
            f.write(json.dumps({"file": base, "idx": idx, "n": n, "kind": kind,
                                "minF": mins, "mod4": modok, "tight4": tight}) + "\n")
        done_files.add(base)
        progress["done_files"] = sorted(done_files)
        json.dump(progress, open(PROG, "w"))
        f.flush()
        print(f"[{time.time()-t0:6.0f}s] done {base} | total {stats['solutions']} sols, not4={stats['not4']}, mod4bad={stats['mod4_violation']}", flush=True)

    # rot4: unified corpus, all n <= 56
    for fp in sorted(glob.glob(os.path.join(DB, "n*_rot4.txt"))):
        n = int(os.path.basename(fp).split("_")[0][1:])
        if n > 56:
            continue
        if time.time() - t0 > 480:
            print("[timebox] pausing"); break
        process(fp, 'rot4')
    # record rot4 solutions (incl. n=76)
    if time.time() - t0 < 480:
        for fp in sorted(glob.glob(os.path.join(FEW, "n*_rot4_decoded.txt"))):
            if time.time() - t0 > 480:
                break
            process(fp, 'rot4')
    # all rct4
    for fp in sorted(glob.glob(os.path.join(DB, "n*_rct4.txt"))) + sorted(glob.glob(os.path.join(FEW, "n*_rct4_decoded.txt"))):
        if time.time() - t0 > 480:
            break
        process(fp, 'half')
    # rot2: exhaustive n <= 20, sample 100 for 22..30
    for fp in sorted(glob.glob(os.path.join(DB, "n*_rot2.txt"))):
        n = int(os.path.basename(fp).split("_")[0][1:])
        if n > 30:
            break
        if time.time() - t0 > 480:
            break
        process(fp, 'half', sample=None if n <= 20 else 100)
    f.close()
    print(json.dumps(stats, ensure_ascii=False), flush=True)
    print(f"elapsed {time.time()-t0:.0f}s; files completed {len(done_files)}")


if __name__ == '__main__':
    main()

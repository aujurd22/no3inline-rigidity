#!/usr/bin/env python3
"""
H_ring deepening — beyond the basic "missing-center <=> independent set".

Three new results computed from the Flammenkamp cache:

  (D1) Ring-population lemma for ANY solution:
       a ring may host k solution-points; missing-center <=> max k <= 2.
       Consequence: a 2n-point MISSING-CENTER solution needs >= n distinct
       distance rings.  We measure the slack = (#rings_used - n) and check
       whether the bound is ever sharp.

  (D2) C4 (rot4) ring structure (bridge to Direction 1):
       every used ring has population divisible by 4 (a full 4-orbit, or two
       orbits sharing a ring).  A C4 extremal solution has exactly m=n/2
       orbits; we verify #orbits == m and population % 4 == 0 on real data.

  (D3) Cross-check: the 5-class exclusion theorem re-derived purely in H_ring
       language (each excluded class forces a ring with pop >= 4, hence NOT
       missing-center).

Standard-format files (n <= 44) are decoded; .few files (n >= 54) skipped.
"""
import os, re, glob, math
from collections import Counter, defaultdict
import hypergraph_framework as hf

CACHE = hf.CACHE


def orbit_of(n, x, y):
    """4-orbit of (x,y) under 90-deg rotation about grid centre."""
    return {(x, y),
            (n - 1 - y, x),
            (n - 1 - x, n - 1 - y),
            (y, n - 1 - x)}


def main():
    files = sorted(glob.glob(os.path.join(CACHE, 'n*_*')))
    out = []
    w = out.append

    # (D1) missing-center ring stats
    mc_rows = []          # (n, |S|, ndistinct_rings, maxpop)
    # (D2) C4 ring stats
    c4_rows = []          # (n, m, ndistinct_rings, maxpop, all_pop_mod4_ok)
    # sanity: total solutions scanned
    total = 0

    for f in files:
        base = os.path.basename(f)
        m = re.match(r'n(\d+)_([a-z0-9]+)(\.few)?$', base)
        if not m:
            continue
        n = int(m.group(1))
        cls = m.group(2)
        is_few = m.group(3) is not None
        with open(f) as fh:
            lines = [l for l in fh if l.strip()]
        for line in lines:
            pts = hf.decode_line(line, n)
            if pts is None:
                continue
            if is_few:
                continue        # keep scan to standard-format only
            total += 1
            S = set(pts)
            # ring populations
            pops = Counter(hf.ring_sig(n, x, y) for x, y in pts)
            ndistinct = len(pops)
            maxpop = max(pops.values())
            mc = (maxpop <= 2)

            if mc:
                mc_rows.append((n, len(pts), ndistinct, maxpop))

            if cls == 'rot4':
                # count 4-orbits
                seen = set()
                norbits = 0
                for (x, y) in pts:
                    if (x, y) in seen:
                        continue
                    orb = orbit_of(n, x, y)
                    seen |= orb
                    norbits += 1
                mod4_ok = all(v % 4 == 0 for v in pops.values())
                c4_rows.append((n, n // 2, ndistinct, maxpop, mod4_ok, norbits))

    # ---- (D1) report ----
    w("=" * 78)
    w("H_RING DEEPENING  (D1)  missing-center ring lower bound")
    w("=" * 78)
    w(f"standard-format solutions scanned : {total}")
    w(f"missing-center solutions found    : {len(mc_rows)}")
    w("")
    w("Ring-population lemma: missing-center <=> every ring has <= 2 points.")
    w("For a |S|-point missing-center solution:  #rings_used >= ceil(|S|/2).")
    w("For extremal |S| = 2n:  #rings_used >= n   (n-ring lower bound).")
    w("")
    gaps = []
    sharp = 0
    extremal = 0
    for (n, size, nd, mx) in mc_rows:
        if size == 2 * n:
            extremal += 1
            gap = nd - n
            gaps.append(gap)
            if gap == 0:
                sharp += 1
    w(f"extremal (2n-point) missing-center solutions : {extremal}")
    if gaps:
        w(f"  slack = #rings - n :  min={min(gaps)}  max={max(gaps)}  "
          f"mean={sum(gaps)/len(gaps):.2f}")
        w(f"  sharp (slack == 0, exactly n rings) : {sharp}/{extremal}")
        w(f"  -> the >= n ring bound is {'SHARP for some n' if sharp else 'never sharp in data'}.")
    w("")
    w("Per-class extremal missing-center ring usage (smallest few n):")
    bycls = defaultdict(list)
    for (n, size, nd, mx) in mc_rows:
        if size == 2 * n:
            bycls[n].append((nd, mx))
    for n in sorted(bycls)[:14]:
        vals = bycls[n]
        w(f"  n={n:>3}  #sol={len(vals):<4}  "
          f"rings/2n in [{min(v[0] for v in vals)},{max(v[0] for v in vals)}]  "
          f"(lower bound n={n})")

    # ---- (D2) report ----
    w("")
    w("=" * 78)
    w("H_RING DEEPENING  (D2)  C4 (rot4) ring structure")
    w("=" * 78)
    w(f"C4 solutions analysed : {len(c4_rows)}")
    w("Predictions: #orbits == m=n/2 ; every ring population % 4 == 0.")
    bad_orbit = [r for r in c4_rows if r[5] != r[1]]
    bad_mod4 = [r for r in c4_rows if not r[4]]
    w(f"  #orbits == m violated : {len(bad_orbit)}")
    w(f"  population %4 == 0 violated : {len(bad_mod4)}")
    w("")
    w(f"{'n':>4}{'m':>4}{'rings':>7}{'maxpop':>8}{'orbits':>8}  status")
    for (n, m_, nd, mx, mod4, no) in c4_rows:
        ok = "OK" if (no == m_ and mod4) else "*** CHECK ***"
        w(f"{n:>4}{m_:>4}{nd:>7}{mx:>8}{no:>8}  {ok}")

    # ---- (D3) re-derive exclusion in H_ring language ----
    w("")
    w("=" * 78)
    w("H_RING DEEPENING  (D3)  exclusion theorem in H_ring language")
    w("=" * 78)
    w("Each EXCLUDED class forces a used ring with population >= 4:")
    w("  rot4/rct4/full : 90-deg rotation -> 4-orbit on one ring (pop 4)")
    w("  dia2/ort2      : 2 reflections  -> 4-orbit on one ring (pop 4)")
    w("=> that ring contains a 3-subset => S not H_ring-independent")
    w("=> NOT missing-center.  (Re-derives the 5-class exclusion theorem.)")

    report = '\n'.join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__),
                           'hring_deepening.txt'), 'w') as fo:
        fo.write(report + '\n')


if __name__ == '__main__':
    main()

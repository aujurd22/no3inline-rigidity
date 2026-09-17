#!/usr/bin/env python3
"""
Distance-Ring Hypergraph framework for the No-Three-In-Line problem.

Empirical backbone for:
  * Lemma  : missing-center  <=>  S is an independent set of H_ring
  * Theorem: Symmetry classification of missing-center solutions
             (excluded classes: rot4, rct4, full, dia2, ort2;
              compatible: iden, rot2, dia1, ort1)

Data: analysis/flammenkamp_cache/n{n}_{class}[.few]   (Flammenkamp 2026 cache)
Standard format (n <= 45): one line per solution, a 1-char symmetry MARKER
followed by 2n value-chars (2 per row), each value = x in
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".
(.few files for n>=54 use a different RLE scheme and are skipped here.)
"""
import os, re, glob
from collections import Counter, defaultdict

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

# filename class -> Flammenkamp marker char (see convert_flammenkamp.py)
CLASS_TO_MARKER = {
    'iden': '.', 'rot2': ':', 'dia1': '/', 'ort1': '-',
    'rot4': 'o', 'rct4': 'c', 'dia2': 'x', 'ort2': '+', 'full': '*',
}
MARKER_TO_CLASS = {v: k for k, v in CLASS_TO_MARKER.items()}

# Symmetry-Exclusion Theorem (verified 2026-07-09): FIVE classes can NEVER
# be missing-center; only FOUR classes are compatible (not excluded).
#   EXCLUDED (5): rot4/rct4/full/ -> 90-deg rotation forces 4-orbit on a ring
#                dia2/ort2        -> both reflections force 4-orbit on ring (NEW)
#   COMPAT  (4): iden/rot2/dia1/ort1  (off-axis orbit size 1 or 2, allowed)
EXCLUDED = {'rot4', 'rct4', 'full', 'dia2', 'ort2'}
COMPAT  = {'iden', 'rot2', 'dia1', 'ort1'}


# ---------------------------------------------------------------- decoding
def decode_line(line, n):
    """Return list of (x,y) points for a standard-format line, or None."""
    line = line.strip()
    if len(line) < 2:
        return None
    body = line[1:]                      # drop symmetry marker
    if len(body) != 2 * n:               # standard format: 2 points per row
        return None
    pts = []
    per_row = len(body) // n
    for y in range(n):
        for j in range(per_row):
            ch = body[y * per_row + j]
            if ch not in ALPHABET:
                return None
            x = ALPHABET.index(ch)
            pts.append((x, y))
    return pts


# ----------------------------------------------------- symmetry recompute
def transform(n, x, y, t):
    if t == 0: return (x, y)
    if t == 1: return (n - 1 - y, x)          # rot90
    if t == 2: return (n - 1 - x, n - 1 - y)  # rot180
    if t == 3: return (y, n - 1 - x)          # rot270
    if t == 4: return (n - 1 - x, y)          # reflect vertical
    if t == 5: return (x, n - 1 - y)          # reflect horizontal
    if t == 6: return (y, x)                  # reflect main diag
    if t == 7: return (n - 1 - y, n - 1 - x)  # reflect anti-diag
    raise ValueError(t)


def is_invariant(n, pts, t):
    S = set(pts)
    return all(transform(n, x, y, t) in S for x, y in pts)


def near_rot4(n, pts):
    S = set(pts)
    filtered = {(x, y) for (x, y) in pts if x != y and x + y != n - 1}
    if not filtered:
        return True
    return all(transform(n, x, y, 1) in S for x, y in filtered)


def recompute_class(n, pts):
    rot90 = is_invariant(n, pts, 1)
    rot180 = is_invariant(n, pts, 2)
    refl_v = is_invariant(n, pts, 4)
    refl_h = is_invariant(n, pts, 5)
    refl_d = is_invariant(n, pts, 6)
    refl_a = is_invariant(n, pts, 7)
    full = rot90 and refl_v and refl_h and refl_d and refl_a
    if full: return '*'
    if rot90: return 'o'
    if near_rot4(n, pts): return 'c'
    if refl_d and refl_a: return 'x'
    if refl_v and refl_h: return '+'
    if rot180: return ':'
    if refl_d or refl_a: return '/'
    if refl_v or refl_h: return '-'
    return '.'


# ----------------------------------------------------------- ring / center
def ring_sig(n, x, y):
    """Squared distance from grid centre C=((n-1)/2,(n-1)/2), scaled to int."""
    a = 2 * x - (n - 1)
    b = 2 * y - (n - 1)
    return a * a + b * b


def is_missing_center(n, pts):
    """missing-center <=> every ring has <= 2 solution points
       <=> S is an independent set of H_ring."""
    rings = Counter(ring_sig(n, x, y) for x, y in pts)
    return max(rings.values()) <= 2


def valid_ntil(n, pts):
    """Sanity: exactly 2n points, 2 per row, 2 per col, no 3 collinear."""
    if len(pts) != 2 * n:
        return False
    if any(Counter(x for x, _ in pts).values()) and \
       any(c != 2 for c in Counter(x for x, _ in pts).values()):
        return False
    if any(c != 2 for c in Counter(y for _, y in pts).values()):
        return False
    # no three collinear (cross product)
    P = sorted(pts)
    from itertools import combinations
    for (x1, y1), (x2, y2), (x3, y3) in combinations(P, 3):
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            return False
    return True


# ---------------------------------------------------------------- main scan
def main():
    files = sorted(glob.glob(os.path.join(CACHE, 'n*_*')))
    per_class = defaultdict(lambda: {'total': 0, 'mc': 0, 'first_mc_n': None})
    per_nc = {}                       # (n, class) -> (total, mc)
    mismatches = []                   # filename class != recomputed
    decode_fail = 0
    total_solutions = 0
    witness = {}                      # class -> (n, example points) smallest n

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
            pts = decode_line(line, n)
            if pts is None:
                if not is_few:
                    decode_fail += 1
                continue
            total_solutions += 1
            per_class[cls]['total'] += 1
            per_nc.setdefault((n, cls), [0, 0])
            per_nc[(n, cls)][0] += 1

            mc = is_missing_center(n, pts)
            # cross-validate symmetry label
            recomputed = MARKER_TO_CLASS.get(recompute_class(n, pts), '?')
            if recomputed != cls:
                mismatches.append((base, cls, recomputed))

            if mc:
                per_class[cls]['mc'] += 1
                per_nc[(n, cls)][1] += 1
                if cls not in witness or n < witness[cls][0]:
                    witness[cls] = (n, pts)

    # ---- report
    out = []
    w = out.append
    w("=" * 78)
    w("DISTANCE-RING HYPERGRAPH  —  SYMMETRY CLASSIFICATION VERIFICATION")
    w("=" * 78)
    w(f"total solutions scanned : {total_solutions}")
    w(f"standard-format decoded : {total_solutions - decode_fail}  "
      f"(decode-fail/skip: {decode_fail})")
    w(f"symmetry-label mismatches (file vs recompute): {len(mismatches)}")
    for mm in mismatches[:10]:
        w(f"    {mm}")
    w("")
    w("-" * 78)
    w("PER-CLASS  missing-center (MC) cross-tabulation")
    w("-" * 78)
    w(f"{'class':<8}{'total':>8}{'MC':>8}{'MC%':>8}   status")
    for cls in ['iden', 'rot2', 'dia1', 'dia2', 'ort1', 'ort2',
                'rot4', 'rct4', 'full']:
        d = per_class.get(cls)
        if not d or d['total'] == 0:
            continue
        tot = d['total']
        mc = d['mc']
        status = 'EXCLUDED (0 MC expected)' if cls in EXCLUDED \
            else 'compatible'
        w(f"{cls:<8}{tot:>8}{mc:>8}{100.0*mc/tot:>7.1f}%   {status}")
    w("")
    w("-" * 78)
    w("REALIZATION WITNESSES  (smallest n with a missing-center example)")
    w("-" * 78)
    for cls in ['iden', 'rot2', 'dia1', 'dia2', 'ort1', 'ort2']:
        if cls in witness:
            n0, pts0 = witness[cls]
            # pretty-print as sorted coords
            pp = ','.join(f"({x},{y})" for x, y in sorted(pts0))
            w(f"{cls:<8} n={n0:<3}  pts = {{{pp}}}")
        else:
            w(f"{cls:<8} NO missing-center example found in cache")
    w("")
    w("EXCLUDED classes (rot4/rct4/full/dia2/ort2): MC count must be 0 across ALL n.")
    for cls in ['rot4', 'rct4', 'full', 'dia2', 'ort2']:
        d = per_class.get(cls, {'total': 0, 'mc': 0})
        ok = 'OK (0 MC)' if d['mc'] == 0 else '*** VIOLATION ***'
        w(f"  {cls:<8} total={d['total']:<6} MC={d['mc']:<6} {ok}")
    w("=" * 78)

    report = '\n'.join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__),
                           'hypergraph_verification.txt'), 'w') as fo:
        fo.write(report + '\n')


if __name__ == '__main__':
    main()

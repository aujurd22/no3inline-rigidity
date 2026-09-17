"""Rigorous independent verification of a found m=37 rot4-NTIL solution.

Unlike verify_and_emit.py (which only checks equally-spaced collinear triples via the
doubling formula), this checks the FULL no-three-in-line condition by brute-forcing ALL
collinearity triples (cross product = 0) over the 148 lifted points. This is the condition
that actually defines NTIL, so it is the decisive check.

Checks performed (each is a necessary & sufficient piece of the rot4-NTIL definition):
  1. base quadrant is a PERMUTATION of {0..m-1} (one cell per row, bijective).
  2. lifted point set has exactly 4m = 148 points, all distinct, all on the 74x74 board.
  3. C4 symmetry: the point set is closed under 90-degree rotation about the centre.
  4. NO THREE points collinear (full brute-force over all C(148,3) triples).
  5. Slope+1 / slope-1 (FDR) sanity: no quadrant line holds >=3 cells (implied by 4).

Usage: verify_certificate.py [biased|unbiased]
"""
import os, sys, json, argparse, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37
N = 2 * M
CENTER = (N - 1) / 2.0


def rot90(p):
    # 90-degree CCW rotation about board centre (N-1)/2 on the N x N board
    return (N - 1 - p[1], p[0])


def lifted_points(x, y, m):
    return [(x, y), (2 * m - 1 - y, x), (2 * m - 1 - x, 2 * m - 1 - y), (y, 2 * m - 1 - x)]


def verify(variant):
    fn = os.path.join(HERE, f'solution_m37_{variant}.json')
    d = json.load(open(fn))
    cells = [tuple(c) for c in d['base_quadrant']]
    m = d['m']
    cert = {'variant': variant, 'm': m, 'n': 2 * m, 'board': f'{N}x{N}'}

    # 1. permutation
    cols = [c[1] for c in cells]
    rows = [c[0] for c in cells]
    perm_ok = (sorted(cols) == list(range(m))) and (sorted(rows) == list(range(m)))
    cert['permutation_ok'] = perm_ok

    # 2. lifted points
    pts = []
    for c in cells:
        pts.extend(lifted_points(c[0], c[1], m))
    ptset = set(pts)
    cert['num_points'] = len(pts)
    cert['num_distinct'] = len(ptset)
    cert['expected_points'] = 4 * m
    cert['all_on_board'] = all(0 <= X < N and 0 <= Y < N for (X, Y) in pts)
    distinct_ok = (len(pts) == len(ptset) == 4 * m)

    # 3. C4 symmetry (closure under rot90)
    closed = all(rot90(p) in ptset for p in pts)
    orbits = set()
    for p in pts:
        o = tuple(sorted([p, rot90(p), rot90(rot90(p)), rot90(rot90(rot90(p)))]))
        orbits.add(o)
    orbit_sizes_ok = all(len(o) == 4 for o in orbits)
    cert['c4_closed'] = closed
    cert['c4_orbit_count'] = len(orbits)
    cert['c4_orbit_sizes_ok'] = orbit_sizes_ok

    # 4. full no-three-in-line: brute force all triples
    plist = list(ptset)
    n = len(plist)
    violations = []
    checked = 0
    for (a, b, c) in itertools.combinations(plist, 3):
        checked += 1
        # cross product (b-a) x (c-a)
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if cross == 0:
            violations.append([a, b, c])
    cert['triples_checked'] = checked
    cert['collinear_triples'] = len(violations)
    collinear_ok = (len(violations) == 0)

    # 5. FDR slope+-1 within quadrant (implied by 4, but reported for completeness)
    badp = badm = 0
    for key in ('p', 'm'):
        line = {}
        for (x, y) in cells:
            v = (x - y) if key == 'p' else (x + y)
            line.setdefault(v, 0)
            line[v] += 1
        if key == 'p':
            badp = sum(1 for v in line.values() if v >= 3)
        else:
            badm = sum(1 for v in line.values() if v >= 3)
    cert['fdr_slope+1_overflow'] = badp
    cert['fdr_slope-1_overflow'] = badm
    fdr_ok = (badp == 0 and badm == 0)

    cert['VALID_rot4_NTIL'] = perm_ok and distinct_ok and closed and orbit_sizes_ok and collinear_ok and fdr_ok
    return cert, violations[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('variant', nargs='?', default='biased')
    args = ap.parse_args()
    variants = [args.variant] if args.variant != 'both' else ['biased', 'unbiased']
    out = {}
    for v in variants:
        cert, sample = verify(v)
        out[v] = cert
        print(f"=== {v} ===")
        print(f"  permutation_ok     = {cert['permutation_ok']}")
        print(f"  points             = {cert['num_distinct']}/{cert['expected_points']} distinct")
        print(f"  all_on_board       = {cert['all_on_board']}")
        print(f"  C4 closed / orbits = {cert['c4_closed']} / {cert['c4_orbit_count']} (size-4 ok={cert['c4_orbit_sizes_ok']})")
        print(f"  collinear triples  = {cert['collinear_triples']} over {cert['triples_checked']} triples checked")
        print(f"  FDR slope+-1 over  = +{cert['fdr_slope+1_overflow']} / -{cert['fdr_slope-1_overflow']}")
        print(f"  >>> VALID_rot4_NTIL = {cert['VALID_rot4_NTIL']}")
        if sample:
            print(f"     sample violation: {sample[0]}")
    with open(os.path.join(HERE, 'verify_certificate.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print("\nwrote analysis/results/verify_certificate.json")


if __name__ == '__main__':
    main()

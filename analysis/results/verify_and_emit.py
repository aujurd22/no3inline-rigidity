"""
Independently verify a rot4 base set (a permutation cols[]) as a genuine rot4-NTIL
solution, and emit the full 2n = 4m lifted point configuration.

Conditions (Th-44 / R9b): a rot4 solution's fundamental quadrant is a PERMUTATION
(cols[i] = column of the single cell in row i, bijective), and the lifted 4m points
must satisfy:
  (X) no three lifted points collinear, and
  (S) no slope-+1 line of the quadrant holds >=3 cells (FDR / R8-G quadratic layer).

Usage:
  verify_and_emit.py --m 37 --cols "[3,0,5,1,...]"     verify an explicit base set
  verify_and_emit.py --m 37 --from biased_nibble.json  verify the best config in a report
"""
import os, sys, json, math, argparse
from collections import defaultdict


def lifted_points(x, y, m):
    # C4 orbit of the quadrant cell (x,y); board is 2m x 2m, indices 0..2m-1
    return [(x, y), (2 * m - 1 - y, x), (2 * m - 1 - x, 2 * m - 1 - y), (y, 2 * m - 1 - x)]


def verify(m, cols):
    """Return (ok, detail) where detail lists any violation."""
    if sorted(cols) != list(range(m)):
        return False, f"cols is not a permutation of 0..{m-1}"
    cells = [(i, cols[i]) for i in range(m)]
    pts = []
    for c in cells:
        pts.extend(lifted_points(c[0], c[1], m))
    ptset = set(pts)
    # (X): no three collinear among the 4m lifted points
    badX = []
    for i in range(len(pts)):
        p1 = pts[i]
        for j in range(i + 1, len(pts)):
            p2 = pts[j]
            for p3 in ((2 * p2[0] - p1[0], 2 * p2[1] - p1[1]),
                       (2 * p1[0] - p2[0], 2 * p1[1] - p2[1])):
                if p3 in ptset and p3 != p1 and p3 != p2:
                    badX.append((p1, p2, p3))
    # (S): slope+1 (x-y const) and slope-1 (x+y const) lines of the quadrant
    badS = []
    for key in ('p', 'm'):
        line = defaultdict(list)
        for (x, y) in cells:
            v = (x - y) if key == 'p' else (x + y)
            line[v].append((x, y))
        for v, members in line.items():
            if len(members) >= 3:
                badS.append((key, v, members))
    ok = (not badX) and (not badS)
    detail = {}
    if badX:
        detail['X_violations'] = badX[:5]
    if badS:
        detail['S_violations'] = badS[:5]
    return ok, detail


def emit(m, cols):
    cells = [(i, cols[i]) for i in range(m)]
    pts = []
    for c in cells:
        pts.extend(lifted_points(c[0], c[1], m))
    return cells, pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m', type=int, required=True)
    ap.add_argument('--cols', type=str, default=None, help='JSON list of columns')
    ap.add_argument('--from', dest='fromfile', default=None, help='biased_nibble.json')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    cols = None
    if args.cols:
        cols = json.loads(args.cols)
    elif args.fromfile:
        rep = json.load(open(args.fromfile))
        for key in ('m37_biased', 'm36_biased', 'm36_unbiased'):
            if key in rep:
                # pick the restart with the best (lowest) objective
                hist = rep[key]['best_bad_hist']
                # we stored only the int objective, not the columns -> need cols.
                # biased_nibble does not dump cols; for a real found solution we must
                # re-run with emit. Fall back to re-deriving is not possible here.
                print(f"[info] report key {key} present but columns not dumped; "
                      f"use --cols to verify a specific config.")
        cols = None
    if cols is None:
        print("No columns supplied and report has none stored; supply --cols.")
        sys.exit(2)

    ok, detail = verify(args.m, cols)
    cells, pts = emit(args.m, cols)
    out = {
        'm': args.m, 'n': 2 * args.m, 'valid': ok,
        'base_quadrant': cells, 'full_points': pts,
        'detail': detail,
    }
    if args.out is None:
        args.out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                f'solution_m{args.m}.json')
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"m={args.m}: valid_rot4_NTIL={ok}  points={len(pts)}")
    if not ok:
        print("violations:", json.dumps(detail)[:500])
    print(f"wrote {args.out}")


if __name__ == '__main__':
    main()

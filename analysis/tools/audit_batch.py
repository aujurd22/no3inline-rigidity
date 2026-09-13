#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_batch.py — batch audit of *_decoded.txt files (multi-solution block format); emits JSON + Markdown
Per solution: NTIL check / independent symmetry class / C4 identity / R3R4 (rot2) / Motzkin+fz / Th58 (rot2) / half-turn census (rot2)
Usage: python audit_batch.py <dir-with-decoded-txt> <out-prefix>
"""
import sys, os, json, time
from math import gcd
from collections import Counter, defaultdict

def load_blocks(path):
    blocks, cur, meta = [], [], []
    for line in open(path, encoding='utf-8'):
        s = line.strip()
        if s.lower().startswith('# solution'):
            if cur: blocks.append((meta, cur))
            cur, meta = [], []
        elif s.startswith('#'):
            if not cur: meta.append(s)
        elif s:
            a, b = s.split()[:2]
            cur.append((int(a), int(b)))
    if cur: blocks.append((meta, cur))
    return blocks

def ntil_bad(pts):
    lines = defaultdict(set)
    for i in range(len(pts)):
        x1, y1 = pts[i]
        for j in range(i+1, len(pts)):
            x2, y2 = pts[j]
            dx, dy = x2-x1, y2-y1
            g = gcd(abs(dx), abs(dy)) or 1
            dx, dy = dx//g, dy//g
            if dx < 0 or (dx == 0 and dy < 0): dx, dy = -dx, -dy
            k = (dy, -dx, dy*x1 - dx*y1)
            lines[k].add(i); lines[k].add(j)
    bad = 0
    for v in lines.values():
        if len(v) >= 3:
            bad += len(v)*(len(v)-1)*(len(v)-2)//6
    return bad

def sym_classes(pts, n):
    S = set(pts); mm = n-1
    out = []
    tests = {
        'rot2': lambda p: (mm-p[0], mm-p[1]),
        'rot4': lambda p: (mm-p[1], p[0]),
        'dia1': lambda p: (p[1], p[0]),
        'dia2': lambda p: (mm-p[1], mm-p[0]),
        'ort1': lambda p: (p[0], mm-p[1]),
        'ort2': lambda p: (mm-p[0], p[1]),
    }
    for name, f in tests.items():
        if all(f(p) in S for p in pts): out.append(name)
    return out

def analyze(pts, do_census):
    n = len(pts)//2; mm = n-1
    r = {'n': n, 'ntil_bad': ntil_bad(pts), 'sym': sym_classes(pts, n)}
    rows = defaultdict(list)
    for x, y in pts: rows[x].append(y)
    pi = {}; sg = {}
    for i in sorted(rows):
        a, b = sorted(rows[i]); pi[i] = a; sg[i] = b
    # C4 identity
    r['c4id_bad'] = sum(1 for i in rows if sg[i] != mm - pi[mm-i])
    # Motzkin
    mp = Counter(pi.values()); ms = Counter(sg.values())
    sig = ''.join('L' if mp.get(c,0)==2 else ('R' if ms.get(c,0)==2 else 'B') for c in range(n))
    h = 0; mn = 0; fz = None
    for t, s in enumerate(sig):
        h += 1 if s=='L' else (-1 if s=='R' else 0)
        mn = min(mn, h)
        if h == 0 and t < n-1 and fz is None: fz = t+1
    r['motz_prefix_min'] = mn; r['motz_end'] = h; r['fz'] = fz  # None => fz = n-1 irreducible
    if 'rot2' in r['sym']:
        r['r3_bad'] = sum(1 for i in rows if pi[i]+pi[mm-i] > n-2)
        r['r4_bad'] = sum(1 for i in rows if sg[i]+sg[mm-i] < n)
        reps = sorted({min((x,y),(mm-x,mm-y)) for x,y in pts})
        assert len(reps) == n
        dd = Counter(); ss = Counter()
        for (x,y) in reps:
            X, Y = 2*x-mm, 2*y-mm
            dd[abs(X-Y)] += 1; ss[abs(X+Y)] += 1
        r['th58_max'] = max(list(dd.values())+list(ss.values()))
        if do_census:
            C = [(2*x-mm, 2*y-mm) for (x,y) in reps]
            N1 = N2 = 0
            for i in range(n):
                X1,Y1 = C[i]
                for j in range(n):
                    X2,Y2 = C[j]
                    d1 = X1*Y2 - Y1*X2
                    s2r = X2*Y2  # placeholder
                    for k in range(n):
                        X3,Y3 = C[k]
                        d2 = X2*Y3 - Y2*X3
                        d3 = X3*Y1 - Y3*X1
                        if d1+d2+d3 == 0: N1 += 1
                        if d1-d2-d3 == 0: N2 += 1
            r['census_N1'] = N1; r['census_N2'] = N2
            r['census_lb1'] = 3*n*n-2*n; r['census_lb2'] = n*n
    return r

def main(d, prefix):
    t0 = time.time()
    results = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('_decoded.txt'): continue
        src = fn.replace('_decoded.txt', '')
        claimed = 'rot2' if '_rot2' in fn else ('rot4' if '_rot4' in fn else ('rct4' if '_rct4' in fn else 'iden'))
        for meta, pts in load_blocks(os.path.join(d, fn)):
            n = len(pts)//2
            do_census = (claimed == 'rot2') and n <= 60
            r = analyze(pts, do_census)
            r['src'] = src; r['claimed'] = claimed
            results.append(r)
    # summary
    agg = defaultdict(lambda: Counter())
    for r in results:
        key = (r['n'], r['claimed'])
        a = agg[key]
        a['count'] += 1
        a['ntil_ok'] += (r['ntil_bad'] == 0)
        a['c4id_ok'] += (r['c4id_bad'] == 0)
        a['sym_ok'] += (r['claimed'] in r['sym'] or (r['claimed']=='iden' and r['sym']==[])
                        or (r['claimed']=='rct4' and 'rot2' in r['sym']))
        a['motz_ok'] += (r['motz_prefix_min'] == 0 and r['motz_end'] == 0)
        a['irreducible'] += (r['fz'] is None)
        if 'th58_max' in r: a['th58_ok'] += (r['th58_max'] <= 2)
        if 'census_N1' in r:
            a['census_ok'] += (r['census_N1'] == r['census_lb1'] and r['census_N2'] == r['census_lb2'])
            a['r34_ok'] += (r.get('r3_bad',0)==0 and r.get('r4_bad',0)==0)
    with open(prefix + '_detail.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    lines = ["| n | class | #sols | NTIL | sym class | C4 id | Motzkin | irreducible | Th58 | census | R3R4 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for (n, cl), a in sorted(agg.items()):
        lines.append(f"| {n} | {cl} | {a['count']} | {a['ntil_ok']} | {a['sym_ok']} | {a['c4id_ok']} | {a['motz_ok']} | {a['irreducible']} | {a['th58_ok'] or '-'} | {a['census_ok'] or '-'} | {a['r34_ok'] or '-'} |")
    report = '\n'.join(lines)
    open(prefix + '_summary.md', 'w', encoding='utf-8').write(report)
    print(report)
    print(f"\n{len(results)} solutions audited in {time.time()-t0:.1f}s")
    # key statistic: C4 identity for n >= 33
    big = [r for r in results if r['n'] >= 33]
    okc = sum(1 for r in big if r['c4id_bad'] == 0)
    print(f"\n*** n >= 33: {len(big)} solutions, C4 identity holds for {okc} ***")
    viol = [r for r in results if r['c4id_bad'] > 0]
    print(f"C4 identity violations: {[(r['n'], r['claimed'], r['src']) for r in viol] if viol else 'none'}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

"""Compare BT pruning verdict vs ground-truth brute 3-collinear for random m-subsets.
R8 says they must AGREE.  Any disagreement = bug in pair_x_bad / pair_s_bad."""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_m37_backtrack as BT

def ground_truth(cells, m):
    n = 2*m
    lifted = []
    for idx in cells:
        x, y = idx//m, idx%m
        for r in range(4):
            lifted.append(BT.c4((x,y), r, n))
    pl = lifted
    for i in range(len(pl)):
        x1,y1 = pl[i]
        for j in range(i+1, len(pl)):
            x2,y2 = pl[j]
            dx,dy = x2-x1, y2-y1
            for k in range(j+1, len(pl)):
                x3,y3 = pl[k]
                if dx*(y3-y1) == dy*(x3-x1):
                    return True, (pl[i],pl[j],pl[k])
    return False, None

def my_verdict(cells, m):
    """Does my pruning flag an internal violation among `cells`?"""
    BT.build(m)
    ch = list(cells)
    n = len(ch)
    # S
    for a in range(n):
        for b in range(n):
            if a == b: continue
            if BT.pair_s_bad(ch[a], ch[b]):
                return True, ('S', ch[a], ch[b])
    # X
    for a in range(n):
        for b in range(a+1, n):
            for c in range(b+1, n):
                if ch[c] in BT.pair_x_bad(ch[a], ch[b]) or ch[c] in BT.pair_x_bad(ch[b], ch[a]) \
                   or ch[b] in BT.pair_x_bad(ch[a], ch[c]) or ch[b] in BT.pair_x_bad(ch[c], ch[a]) \
                   or ch[a] in BT.pair_x_bad(ch[b], ch[c]) or ch[a] in BT.pair_x_bad(ch[c], ch[b]):
                    return True, ('X', ch[a], ch[b], ch[c])
    return False, None

def main():
    m = 9
    rng = random.Random(42)
    disagree = 0
    tested = 0
    for _ in range(4000):
        cells = rng.sample(range(m*m), m)
        gt, gtinfo = ground_truth(cells, m)
        mv, mvinfo = my_verdict(cells, m)
        tested += 1
        if gt != mv:
            disagree += 1
            if disagree <= 5:
                print(f"DISAGREE gt={gt} mine={mv}")
                print(f"  cells={sorted(cells)}")
                print(f"  gtinfo={gtinfo} mvinfo={mvinfo}")
    print(f"tested={tested} disagree={disagree}")

if __name__ == '__main__':
    main()

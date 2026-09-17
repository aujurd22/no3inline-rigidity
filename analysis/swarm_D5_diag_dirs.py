import os, sys, json, math
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import solver_theory_m37 as E
def dir_angle(cell,m):
    cx=cell[0]-(2*m-1)/2.0; cy=cell[1]-(2*m-1)/2.0
    return math.atan2(cy,cx)  # in (-pi,pi]
cfg=json.load(open(os.path.join(HERE,"results","solver_theory_m37_long.json")))
cells=[tuple(c) for c in cfg["cells"]]; m=37
ang=[dir_angle(c,m) for c in cells]
angmod=[a%(math.pi) for a in ang]  # mod 180 deg
angmod.sort()
gaps=[]
for i in range(len(angmod)):
    cur=angmod[i]
    nxt=angmod[(i+1)%len(angmod)]
    g=(nxt-cur+math.pi)%math.pi
    gaps.append(g)
# perpendicular gaps: for each theta, distance to theta+pi/2 mod pi
perp_min=1e9
for a in angmod:
    b=(a+math.pi/2)%math.pi
    # closest direction to b
    d=min((abs(((x-b+math.pi/2)%math.pi)-math.pi/2)) for x in angmod)
    perp_min=min(perp_min,d)
print("n directions:",len(angmod))
print("min adjacent angular gap (mod 180): %.4f rad = %.2f deg"%(min(gaps),math.degrees(min(gaps))))
print("mean adjacent gap: %.4f rad = %.2f deg"%(sum(gaps)/len(gaps),math.degrees(sum(gaps)/len(gaps))))
print("min distance from any direction to its +90 partner: %.4f rad = %.2f deg"%(perp_min,math.degrees(perp_min)))
# how many distinct directions
print("distinct dirs:",len(set((round(a,6) for a in angmod))),"/",m)

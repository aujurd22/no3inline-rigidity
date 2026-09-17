"""
第二轮挖掘：单圈解的置换本质 + 升维/时间-空间视角

检验两个最可能藏公式的方向：
  (A) 单圈解定向成置换 pi（m-圈），看步长序列 pi(i)-i (mod m)：
      - 是否"完全映射"(所有步长互异) → orthomorphism / 完整映射
      - 是否存在生成元规律（如 pi(i)=2i, 或 pi 是某个固定置换的幂）
  (B) 种子点（Q3 cell）按 FD 向量角度排序后，角度间隙是否近似等距
      → "对数螺旋上近似均匀采样"假说

纯分析。
"""
import os, json, math
from collections import defaultdict, Counter
ALPH='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL={c:i for i,c in enumerate(ALPH)}
SYMM=set('.:/-ocx+*')
CACHE='analysis/flammenkamp_cache'

def decode(line,n):
    line=line.strip(); body=line[1:] if line and line[0] in SYMM else line
    pts=[]
    for r in range(n):
        pts.append((VAL[body[2*r]],r)); pts.append((VAL[body[2*r+1]],r))
    return pts

def q3_cells(pts,m):
    return [(x,y) for x,y in pts if x<m and y<m]

def undirected_cycles(cells,m):
    adj=defaultdict(list)
    for a,b in cells:
        adj[a].append(b); adj[b].append(a)
    visited=set(); cycles=[]
    for s in range(m):
        if s in visited or s not in adj: continue
        cyc=[]; cur=s; prev=-1
        while cur not in visited:
            visited.add(cur); cyc.append(cur)
            nxt=[x for x in adj[cur] if x!=prev]
            if not nxt: break
            prev,cur=cur,nxt[0]
        cycles.append(cyc)
    return cycles

def orient_single_cycle(cyc):
    """cyc 是顶点环（undirected），定向为 i->next 的置换字典。"""
    return {cyc[i]: cyc[(i+1)%len(cyc)] for i in range(len(cyc))}

def analyze(n, cap=80):
    m=n//2
    lines=[l.strip() for l in open(f'{CACHE}/n{n}_rot4') if l.strip()]
    out={'n':n,'m':m,'single_cycle':0,'multi':0,'ortho_count':0,'step_patterns':Counter(),
         'angle_gap_uniform':0,'angle_gap_total':0,'examples':[]}
    for line in lines[:cap]:
        pts=decode(line,n)
        cells=q3_cells(pts,m)
        if len(cells)!=m: continue
        # 2-factor validity
        combined=[a for a,b in cells]+[b for a,b in cells]
        if any(v!=2 for v in Counter(combined).values()): continue
        cycs=undirected_cycles(cells,m)
        lengths=sorted(len(c) for c in cycs)
        if len(cycs)==1 and len(cycs[0])==m:
            out['single_cycle']+=1
            pi=orient_single_cycle(cycs[0])
            # 步长序列
            steps=[(pi[i]-i)%m for i in range(m)]
            stepc=Counter(steps)
            is_ortho = (len(stepc)==m)  # 所有步长互异 = 完全映射
            if is_ortho: out['ortho_count']+=1
            # 步长模式（排序后作为签名，限制长度）
            sig=tuple(sorted(steps))
            out['step_patterns'][sig[:6]]+=1
            # 角度间隙（FD 向量 = (x-(m-0.5), y-(m-0.5))）
            vecs=[(x-(m-0.5), y-(m-0.5)) for x,y in cells]
            angs=sorted(math.atan2(vy,vx) for vx,vy in vecs)
            gaps=[(angs[(i+1)%m]-angs[i])%(2*math.pi) for i in range(m)]
            # 均匀性：间隙的变异系数
            mean_gap=2*math.pi/m
            var=sum((g-mean_gap)**2 for g in gaps)/m
            cv=math.sqrt(var)/mean_gap
            out['angle_gap_total']+=1
            if cv<0.25: out['angle_gap_uniform']+=1
            if len(out['examples'])<2:
                out['examples'].append({'cells':cells,'steps':steps,'is_ortho':is_ortho,'cv':round(cv,3)})
        else:
            out['multi']+=1
    out['step_patterns']=dict(out['step_patterns'].most_common(5))
    return out

def main():
    results={}
    for n in [8,10,12,14,16,18,20,24,30,36,40,44]:
        r=analyze(n)
        results[n]=r
        print(f"n={n:2d} m={n//2:2d}: single={r['single_cycle']:3d} multi={r['multi']:3d} "
              f"ortho(步长互异)={r['ortho_count']:3d} "
              f"angle_uniform(cv<0.25)={r['angle_gap_uniform']}/{r['angle_gap_total']}")
        if r['examples']:
            e=r['examples'][0]
            print(f"      ex steps={e['steps']} ortho={e['is_ortho']} cv={e['cv']}")
    # 保存
    os.makedirs('analysis/results',exist_ok=True)
    save={}
    for n,r in results.items():
        rr=dict(r)
        rr['step_patterns']={str(k):v for k,v in r['step_patterns'].items()}
        save[n]=rr
    with open('analysis/results/mine_permutation_essence.json','w') as f:
        json.dump(save,f,indent=1)
    print("\nsaved analysis/results/mine_permutation_essence.json")

if __name__=='__main__':
    main()

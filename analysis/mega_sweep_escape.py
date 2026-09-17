"""
Mega Sweep V3 — with ESCAPE mechanisms.
When stuck at a local min, escalate perturbation to escape.
"""
import sys, os, json, time, random, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P

M = 37
CHECKPOINT = 'results/mega_sweep_escape.json'
LOG_FILE = '_mega_escape_out.txt'

def log(msg):
    with open(LOG_FILE, 'a') as lf:
        lf.write(f'{time.strftime("%H:%M:%S")} {msg}\n')

# ── New mutation operators ────────────────────────────────────────────────────

def three_switch(edges, rng):
    """3-edge swap: pick 3 edges with 6 distinct vertices, rewire.
    More disruptive than two_switch — can change cycle structure."""
    E = list(edges)
    for _ in range(50):
        i, j, k = rng.sample(range(M), 3)
        u1, v1 = E[i]; u2, v2 = E[j]; u3, v3 = E[k]
        vs = {u1, v1, u2, v2, u3, v3}
        if len(vs) < 6:
            continue
        # Multiple rewire patterns — try each
        patterns = [
            # Pattern A: cycle the connections
            [(u1,u2),(v1,u3),(v2,v3)],
            [(u1,u2),(v1,v3),(v2,u3)],
            [(u1,v2),(v1,u2),(v3,u3)],
            [(u1,u3),(v1,v2),(u2,v3)],
        ]
        for pat in patterns:
            ne = list(E)
            valid = True
            for idx, (nx, ny) in zip([i, j, k], pat):
                if nx == ny:
                    valid = False; break
                ne[idx] = tuple(sorted((nx, ny)))
            if not valid:
                continue
            dedup = sorted(set(ne))
            if len(dedup) == M and all(
                sum(1 for a,b in dedup if a==v or b==v) == 2 for v in range(M)
            ):
                return sorted(dedup)
    return None

def path_rewire(edges, rng):
    """Break the cycle at 2 random points, reconnect the 2 segments swapped.
    This is a more global mutation than two_switch."""
    # Build adjacency
    adj = {i: [] for i in range(M)}
    for u,v in edges:
        adj[u].append(v); adj[v].append(u)
    
    # Get the cycle ordering
    visited = set()
    cycle = []
    v = 0
    prev = -1
    while v not in visited:
        visited.add(v); cycle.append(v)
        nxt = [x for x in adj[v] if x != prev][0]
        prev, v = v, nxt
    
    # Pick 2 break points
    for _ in range(30):
        p1 = rng.randrange(M); p2 = rng.randrange(M)
        if abs(p1-p2) < 3: continue
        
        # Two segments: A: cycle[p1:p2], B: cycle[p2:] + cycle[:p1]
        a_start, a_end = min(p1, p2), max(p1, p2)
        seg_a = cycle[a_start:a_end]
        seg_b = cycle[a_end:] + cycle[:a_start]
        
        # Reconnect by swapping segment order: A + reversed(B) or reversed(A) + B
        segments = [seg_a, seg_b]
        rng.shuffle(segments)
        
        new_cycle = segments[0] + segments[1]
        new_edges = []
        prev_v = None
        valid = True
        seen = set()
        for v in new_cycle:
            if v in seen: valid = False; break
            seen.add(v)
            if prev_v is not None:
                new_edges.append((prev_v, v) if prev_v <= v else (v, prev_v))
            prev_v = v
        if not valid: continue
        # Close the cycle
        a, b = new_cycle[-1], new_cycle[0]
        new_edges.append((a, b) if a <= b else (b, a))
        new_edges = sorted(set(new_edges))
        if len(new_edges) == M:
            return new_edges
    return None

def aggressive_perturb(edges, rng):
    """Massive perturbation: randomly reassign ~30% of the vertices to 
    different positions while keeping Hamiltonian cycle structure."""
    for _ in range(20):
        # Get cycle order
        adj = {i: [] for i in range(M)}
        for u,v in edges:
            adj[u].append(v); adj[v].append(u)
        cycle = [0]
        prev = -1
        for _ in range(M-1):
            nxt = [x for x in adj[cycle[-1]] if x != prev][0]
            prev, cycle[-1] = cycle[-1], nxt
            cycle.append(nxt)
        
        # Pick a segment to scramble
        seg_len = rng.randint(6, 14)
        start = rng.randrange(M - seg_len)
        segment = cycle[start:start+seg_len]
        rng.shuffle(segment)
        
        new_cycle = cycle[:start] + segment + cycle[start+seg_len:]
        new_edges = []
        for k in range(M):
            a, b = new_cycle[k], new_cycle[(k+1)%M]
            new_edges.append((a,b) if a<=b else (b,a))
        dedup = sorted(set(new_edges))
        if len(dedup) == M:
            return dedup
    return None

# ── Main sweep with escape ────────────────────────────────────────────────────

def main():
    rng = random.Random(20260716)
    
    # Resume from checkpoint or fresh start
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            state = json.load(f)
        print(f'Resumed: trial={state["trial"]}, best_cls={state["best_cls"]}, best_viol={state["best_viol"]}', flush=True)
        best_cls = state['best_cls']
        best_viol = state['best_viol']
        best_edges = [tuple(e) for e in state['best_edges']]
        trial_start = state['trial']
        trials_since_improvement = state.get('stuck_counter', 0)
    else:
        with open('results/mega_sweep_v2.json') as f:
            d = json.load(f)
        best_cls = d['best_clauses']
        best_viol = d['best_violations']
        best_edges = [tuple(e) for e in d['best_edges']]
        trial_start = d['trials']
        trials_since_improvement = 0
        print(f'Fresh: start from v2 best={best_cls} viol={best_viol} trial={trial_start}', flush=True)
    
    # Also load seed
    with open('results/hamiltonian_mutate.json') as f:
        seed_edges = [tuple(e) for e in json.load(f)['best_edges']]
    
    start_time = time.time()
    escape_level = 0  # 0=normal, 1=mild escape, 2=aggressive, 3=desperate
    
    for trial in range(trial_start, 200000):
        # Determine strategy based on escape level
        r = rng.random()
        
        if escape_level == 0:
            # Normal mutation (standard two_switch)
            if r < 0.7:
                if rng.random() < 0.4:
                    edges = list(best_edges)
                    for _ in range(rng.randint(1,3)):
                        ei = rng.randrange(M)
                        ej = rng.randrange(M)
                        if ei == ej: continue
                        u1,v1 = best_edges[ei]; u2,v2 = best_edges[ej]
                        if len({u1,v1,u2,v2}) < 4: break
                        for na, nb in [((u1,u2),(v1,v2)), ((u1,v2),(v1,u2))]:
                            ne = list(best_edges)
                            ne[ei] = tuple(sorted(na)); ne[ej] = tuple(sorted(nb))
                            dedup = sorted(set(ne))
                            if len(dedup)==M and all(sum(1 for a,b in dedup if a==v or b==v)==2 for v in range(M)):
                                edges = dedup; break
                        else: continue
                        break
                    if len(edges) != 37: continue
                else:
                    edges = H.mutate_cycle(best_edges, rng, rng.randint(1,3))
            elif r < 0.85:
                edges = H.mutate_cycle(seed_edges, rng, rng.randint(2,5))
            else:
                edges = H.random_hamiltonian_cycle(M, rng)
        
        elif escape_level == 1:
            # Mild escape: more aggressive two_switch + occasional rewire
            op = rng.choice(['2switch', '2switch', '2switch', '2switch', 'rewire'])
            if op == '2switch':
                edges = H.mutate_cycle(best_edges, rng, rng.randint(3,6))
            else:
                edges = path_rewire(best_edges, rng)
                if edges is None:
                    edges = H.mutate_cycle(best_edges, rng, 4)
        
        elif escape_level == 2:
            # Aggressive escape: 3-switch and path rewire
            op = rng.choice(['3switch', '3switch', 'rewire', 'perturb'])
            if op == '3switch':
                edges = three_switch(best_edges, rng)
                if edges is None: edges = H.mutate_cycle(best_edges, rng, 5)
            elif op == 'rewire':
                edges = path_rewire(best_edges, rng)
                if edges is None: edges = aggressive_perturb(best_edges, rng)
            else:
                edges = aggressive_perturb(best_edges, rng)
        
        else:
            # Desperate escape: anything goes
            op = rng.choice(['aggressive', 'aggressive', 'random', '3switch'])
            if op == 'aggressive':
                edges = aggressive_perturb(best_edges, rng)
            elif op == 'random':
                edges = H.random_hamiltonian_cycle(M, rng)
            else:
                edges = three_switch(best_edges, rng)
            if edges is None:
                edges = H.random_hamiltonian_cycle(M, rng)
        
        if edges is None or len(edges) != 37:
            continue
        
        nc = H.count_clauses_fast(M, edges)
        
        if nc < best_cls:
            best_cls = nc
            best_edges = list(edges)
            trials_since_improvement = 0
            escape_level = 0  # Reset escape when we find improvement
            print(f'trial {trial}: *** NEW BEST nc={nc} (esc_level={escape_level}) ***', flush=True)
            log(f'trial {trial}: NEW BEST nc={nc}')
            
            if nc < 440:
                try:
                    cl, _ = P.enumerate_clauses(M, edges, verbose=False)
                    sr = P.check_sat(M, edges, cl, time_limit=60, verbose=False)
                    mv = sr.get('maxsat_min_violations', -1)
                    log(f'  SAT: mv={mv} -> {4*mv} defects')
                    if mv >= 0 and mv < best_viol:
                        best_viol = mv
                        print(f'  NEW BEST violations: {mv} -> {4*mv} defects!', flush=True)
                        if mv < 16:
                            log('*** SIGNIFICANT! Below 16 violations! ***')
                    if mv == 0:
                        log('*** BREAKTHROUGH! m=37 SOLVED! ***')
                        print('🔥 *** BREAKTHROUGH! m=37 SOLVED! *** 🔥', flush=True)
                        state = {
                            'trial': trial, 'best_cls': best_cls, 'best_viol': best_viol,
                            'best_edges': best_edges, 'breakthrough': True,
                            'elapsed_s': round(time.time()-start_time), 'stuck_counter': 0
                        }
                        with open(CHECKPOINT, 'w') as f: json.dump(state, f, indent=2)
                        return
                except Exception as e:
                    log(f'SAT error: {e}')
        else:
            trials_since_improvement += 1
        
        # Escape level escalation
        if trials_since_improvement > 2000 and escape_level < 3:
            escape_level = min(escape_level + 1, 3)
            print(f'trial {trial}: ESCALATING to escape_level={escape_level} (stuck {trials_since_improvement} trials)', flush=True)
            log(f'ESCAPE escalation to level {escape_level}')
            trials_since_improvement = 0  # Don't immediately re-escalate
        
        # Checkpoint every 100 trials
        if (trial+1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (trial+1-trial_start)/elapsed*3600 if elapsed > 0 else 0
            state = {
                'trial': trial+1, 'best_cls': best_cls, 'best_viol': best_viol,
                'best_edges': best_edges, 'breakthrough': False,
                'elapsed_s': round(elapsed), 'stuck_counter': trials_since_improvement,
                'escape_level': escape_level, 'trials_per_hour': round(rate, 1)
            }
            with open(CHECKPOINT, 'w') as f:
                json.dump(state, f, indent=2)
            
            if (trial+1) % 500 == 0:
                print(f'[{trial+1} trials, {elapsed/3600:.1f}h, rate={rate:.0f}/h, '
                      f'best={best_cls}cls/{best_viol}viol, esc_lvl={escape_level}]', flush=True)
    
    # Finished
    elapsed = time.time() - start_time
    print(f'=== FINISHED: best={best_cls} cls, {best_viol} viol, {elapsed/3600:.1f}h ===', flush=True)
    state = {
        'trial': 200000, 'best_cls': best_cls, 'best_viol': best_viol,
        'best_edges': best_edges, 'breakthrough': False,
        'elapsed_s': round(elapsed), 'stuck_counter': trials_since_improvement,
        'escape_level': escape_level, 'finished': True
    }
    with open(CHECKPOINT, 'w') as f:
        json.dump(state, f, indent=2)
    log(f'FINISHED: best={best_cls}, viol={best_viol}')

if __name__ == '__main__':
    main()

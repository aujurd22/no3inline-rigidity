#!/usr/bin/env python3
"""
Multi-seed parallel DFS: run the orbit_reduced_gpu solver with multiple
random seeds simultaneously. First seed to find a solution wins.

Usage: python multi_seed.py <n> <exclude_dirs> <num_seeds> [base_seed]
"""
import subprocess, os, sys, time, threading

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "orbit_reduced_gpu.exe")
CUDA_DIR = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3"

n = int(sys.argv[1]) if len(sys.argv) > 1 else 14
exclude = int(sys.argv[2]) if len(sys.argv) > 2 else 5
n_seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 4
base_seed = int(sys.argv[4]) if len(sys.argv) > 4 else 42

results = {}
lock = threading.Lock()
found = threading.Event()
t0 = time.time()

def worker(seed):
    env = os.environ.copy()
    env["PATH"] = CUDA_DIR + "\\bin;" + env.get("PATH", "")
    try:
        r = subprocess.run([EXE, str(n), str(seed), str(exclude)],
                          capture_output=True, timeout=3600, env=env,
                          encoding='gbk', errors='replace')
        with lock:
            results[seed] = r
            if "solutions_found=1" in (r.stdout or ""):
                found.set()
    except Exception as e:
        with lock:
            results[seed] = f"ERROR: {e}"

print(f"Launching {n_seeds} workers for n={n} exclude={exclude} ...")
threads = []
for i in range(n_seeds):
    seed = base_seed + i * 7
    t = threading.Thread(target=worker, args=(seed,), daemon=True)
    t.start()
    threads.append(t)
    print(f"  seed={seed} started")

# Wait for first solution or all done
found.wait(timeout=3600) if n_seeds > 0 else None

# Report results
elapsed = time.time() - t0
print(f"\n=== Results after {elapsed:.1f}s ===")
for seed, r in sorted(results.items()):
    if isinstance(r, str):
        print(f"  seed={seed}: {r}")
    else:
        found_sol = "solutions_found=1" in (r.stdout or "")
        nodes = "?"
        for line in (r.stdout or "").splitlines():
            if "nodes=" in line:
                nodes = line.strip()
                break
        mark = "*** SOLUTION ***" if found_sol else "(no solution)"
        print(f"  seed={seed}: {mark}  {nodes}")
        if found_sol:
            for line in (r.stdout or "").splitlines():
                if "solution orbits" in line or "->" in line:
                    print(f"    {line.strip()}")

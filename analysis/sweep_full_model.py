"""
sweep_full_model.py — Sweep max_2cycles from 0..N on m=37 using solver_full_model.
Each k runs independently (separate background calls).
"""
import subprocess, sys, os, time, json

BASE = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis"
PYTHON = r"C:\Users\djr82\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
SCRIPT = os.path.join(BASE, "solver_full_model.py")
TIMELIMIT = 600  # seconds per k
K_MAX = 4
RESULT_DIR = os.path.join(BASE, "results")

def run_k(k):
    outfile = os.path.join(RESULT_DIR, f"full_m37_k{k}.json")
    logfile = os.path.join(BASE, f"_full_m37_k{k}_out.txt")
    cmd = (
        f'cd /d "{BASE}" && "{PYTHON}" -u "{SCRIPT}" '
        f'--m 37 --time {TIMELIMIT} --max-2cycles {k} --out "{outfile}" '
        f'> "{logfile}" 2>&1'
    )
    print(f"Launching k={k}...", flush=True)
    subprocess.Popen(cmd, shell=True)
    print(f"  k={k} launched (PID: to {logfile}, res: {outfile})", flush=True)

if __name__ == "__main__":
    for k in range(1, K_MAX + 1):
        run_k(k)
    print(f"\nAll {K_MAX} runs launched in background.")
    print("Monitor via log files: _full_m37_k{1..4}_out.txt")

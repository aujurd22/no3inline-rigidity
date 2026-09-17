#!/usr/bin/env python3
import subprocess, os, sys

os.chdir(r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\analysis\gpu_smoke")
env = os.environ.copy()

vc = r"D:\vs-20260707\vs\VC\Tools\MSVC\14.44.35207"
sdk = r"C:\Program Files (x86)\Windows Kits\10"
cuda = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3"

env["PATH"] = f"{vc}\\bin\\Hostx64\\x64;{cuda}\\bin;" + env.get("PATH","")
env["INCLUDE"] = f"{vc}\\include;{sdk}\\Include\\10.0.26100.0\\ucrt;{sdk}\\Include\\10.0.26100.0\\um;{sdk}\\Include\\10.0.26100.0\\shared;{cuda}\\include"
env["LIB"] = f"{vc}\\lib\\x64;{sdk}\\Lib\\10.0.26100.0\\ucrt\\x64;{sdk}\\Lib\\10.0.26100.0\\um\\x64;{cuda}\\lib\\x64"

src = sys.argv[1] if len(sys.argv) > 1 else "mc_orbit_validator.cu"
exe = src.replace(".cu", ".exe")

r = subprocess.run([f"{cuda}\\bin\\nvcc.exe", "-O3", "-o", exe, src],
                   capture_output=True, timeout=60, env=env,
                   encoding='gbk', errors='replace')
print("RC:", r.returncode)
if r.returncode != 0:
    lines = ((r.stdout or "") + (r.stderr or "")).splitlines()
    for l in lines:
        if "error" in l.lower():
            print("  ERR:", l.strip())
elif len(sys.argv) > 2:
    # Run the exe with remaining args
    import time; t0=time.time()
    rr = subprocess.run([exe] + sys.argv[2:], capture_output=True, timeout=300, env=env,
                        encoding='gbk', errors='replace')
    print(rr.stdout)
    if rr.stderr: print(rr.stderr, file=sys.stderr)
    print(f"RUNTIME={time.time()-t0:.1f}s")

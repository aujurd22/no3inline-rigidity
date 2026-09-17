"""Quick debug: compile + run n=52 baseline."""
import sys, os, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MVR_DIR = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\mvr_reference"
CUDA_BIN = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin"
MSVC_PATH = r"D:\vs-20260707\vs\VC\Tools\MSVC\14.51.36231"
WKIT_INC = r"D:\Windows Kits\10\Include\10.0.26100.0"
WKIT_LIB = r"D:\Windows Kits\10\Lib\10.0.26100.0"

print("[1] Generating prefilter config (baseline, 0 cells)...", flush=True)
from experiment_prefilter import generate_preconfig_file
generate_preconfig_file(52, 0)
print("[1] Done", flush=True)

print("[2] Compiling n=52 (N=26)...", flush=True)
env = os.environ.copy()
env["PATH"] = CUDA_BIN + ";" + MSVC_PATH + "\\bin\\Hostx64\\x64;" + MSVC_PATH + "\\..\\Common7\\IDE;C:\\Windows\\System32;C:\\Windows;" + env.get("PATH", "")
env["INCLUDE"] = MSVC_PATH + "\\include;" + WKIT_INC + "\\ucrt;" + WKIT_INC + "\\um;" + WKIT_INC + "\\shared"
env["LIB"] = MSVC_PATH + "\\lib\\x64;" + WKIT_LIB + "\\ucrt\\x64;" + WKIT_LIB + "\\um\\x64"

exe = os.path.join(MVR_DIR, "three_c4_bench_n52_debug.exe")
cmd = [
    os.path.join(CUDA_BIN, "nvcc.exe"), "-o", exe,
    "main_c4.cpp", "three_kernel_c4.cu", "-DTHREE_N=26",
    "-O3", "-arch=sm_89", "-std=c++17", "--expt-relaxed-constexpr",
    "-Xcompiler", "/Zc:preprocessor", "-Xcompiler", "/O2",
    "-Wno-deprecated-gpu-targets", "-lcuda", "-lcudadevrt",
]
t0 = time.time()
r = subprocess.run(cmd, cwd=MVR_DIR, env=env, capture_output=True, timeout=300)
print(f"  Compile exit={r.returncode}, took {time.time()-t0:.1f}s", flush=True)
if r.returncode != 0:
    print("STDERR:", r.stderr.decode("utf-8", "replace")[-600:], flush=True)
    sys.exit(1)

print("[3] Running...", flush=True)
t0 = time.time()
try:
    r2 = subprocess.run([exe, "--first-solution", "--time-limit", "120"],
                        cwd=MVR_DIR, capture_output=True, timeout=180)
    elapsed = time.time() - t0
    out = r2.stdout.decode("utf-8", "replace")[:300] if r2.stdout else ""
    print(f"  Exit={r2.returncode}, took {elapsed:.1f}s", flush=True)
    print(f"  Output: {out[:200]}", flush=True)
except subprocess.TimeoutExpired:
    print(f"  TIMEOUT after {time.time()-t0:.1f}s", flush=True)

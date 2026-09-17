import os, subprocess, sys

MVR = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\mvr_reference"
CUDA_BIN = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin"
MSVC_PATH = r"D:\vs-20260707\vs\VC\Tools\MSVC\14.51.36231"
WKIT_INC = r"D:\Windows Kits\10\Include\10.0.26100.0"
WKIT_LIB = r"D:\Windows Kits\10\Lib\10.0.26100.0"

out_name = sys.argv[1] if len(sys.argv) > 1 else "three_c4_n76_moderate.exe"

env = os.environ.copy()
env["PATH"] = f"{CUDA_BIN};{MSVC_PATH}\\bin\\Hostx64\\x64;{MSVC_PATH}\\..\\Common7\\IDE;C:\\Windows\\System32;C:\\Windows;{env.get('PATH','')}"
env["INCLUDE"] = f"{MSVC_PATH}\\include;{WKIT_INC}\\ucrt;{WKIT_INC}\\um;{WKIT_INC}\\shared"
env["LIB"] = f"{MSVC_PATH}\\lib\\x64;{WKIT_LIB}\\ucrt\\x64;{WKIT_LIB}\\um\\x64"

exe_path = os.path.join(MVR, out_name)
cmd = [
    os.path.join(CUDA_BIN, "nvcc.exe"),
    "-o", exe_path,
    os.path.join(MVR, "main_c4.cpp"),
    os.path.join(MVR, "three_kernel_c4.cu"),
    "-DTHREE_N=38", "-O3", "-arch=sm_89", "-std=c++17",
    "--expt-relaxed-constexpr",
    "-Xcompiler", "/Zc:preprocessor",
    "-Xcompiler", "/O2",
    "-Wno-deprecated-gpu-targets",
    "-lcuda", "-lcudadevrt",
]

print(f"Compiling {out_name} ...", flush=True)
result = subprocess.run(cmd, cwd=MVR, env=env, capture_output=True, text=False, timeout=300)

out = result.stdout.decode("utf-8", errors="replace")
if out.strip():
    print(out)

if result.returncode == 0:
    print(f"COMPILE OK -> {exe_path}", flush=True)
else:
    err = result.stderr.decode("utf-8", errors="replace")[-2000:]
    print(f"COMPILE FAILED (code={result.returncode}):", flush=True)
    print(err, flush=True)
    sys.exit(1)

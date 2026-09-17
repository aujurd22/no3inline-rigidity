"""Compile the non-symmetric solver (main.cpp) for n=21 iden search."""
import subprocess, os, sys

MVR = r'D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\mvr_reference'
CUDA_BIN = r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin'
MSVC_PATH = r'D:\vs-20260707\vs\VC\Tools\MSVC\14.51.36231'
WKIT_INC = r'D:\Windows Kits\10\Include\10.0.26100.0'
WKIT_LIB = r'D:\Windows Kits\10\Lib\10.0.26100.0'

target_n = int(sys.argv[1]) if len(sys.argv) > 1 else 21

env = os.environ.copy()
env['PATH'] = f'{CUDA_BIN};{MSVC_PATH}\\bin\\Hostx64\\x64;{MSVC_PATH}\\..\\Common7\\IDE;C:\\Windows\\System32;C:\\Windows;{env.get("PATH","")}'
env['INCLUDE'] = f'{MSVC_PATH}\\include;{WKIT_INC}\\ucrt;{WKIT_INC}\\um;{WKIT_INC}\\shared;{MVR}/vendor'
env['LIB'] = f'{MSVC_PATH}\\lib\\x64;{WKIT_LIB}\\ucrt\\x64;{WKIT_LIB}\\um\\x64'

exe_name = f'three_iden_n{target_n}.exe'
out_path = os.path.join(MVR, exe_name)

cmd = [
    os.path.join(CUDA_BIN, 'nvcc.exe'),
    '-o', out_path,
    os.path.join(MVR, 'main.cpp'),
    os.path.join(MVR, 'three_board.cu'),
    os.path.join(MVR, 'three_kernel.cu'),
    f'-DTHREE_N={target_n}',
    '-O3', '-arch=sm_89', '-std=c++17',
    '--expt-relaxed-constexpr',
    '-Xcompiler', '/Zc:preprocessor',
    '-Xcompiler', '/O2',
    '-Wno-deprecated-gpu-targets',
    '-lcuda', '-lcudadevrt',
    f'-I{MVR}/vendor',
]

print(f"Compiling iden solver for n={target_n}...")
print(f"  Output: {out_path}")
result = subprocess.run(cmd, cwd=MVR, env=env, capture_output=True, text=False, timeout=300)

if result.returncode == 0:
    print(f"✅ COMPILE OK → {exe_name}")
    print(f"   Size: {os.path.getsize(out_path) // 1024} KB")
else:
    err = result.stderr.decode('utf-8', errors='replace')[-2000:]
    print(f"❌ COMPILE FAILED (code={result.returncode})")
    print(err)

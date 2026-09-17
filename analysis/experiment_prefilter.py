"""Pre-filter benchmark: test danger-based cell exclusion at multiple strengths.

For given n, compiles & runs mvr C4 engine with different prefilter levels,
measuring time-to-first-solution. Outputs a comparison table.

Usage: python experiment_prefilter.py <n> [--levels light,medium,aggressive,...]
"""
import sys, os, json, subprocess, time, tempfile

# Force unbuffered output for real-time progress in background jobs
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

DIR = os.path.dirname(os.path.abspath(__file__))
MVR_DIR = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\mvr_reference"
ANALYSIS_DIR = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\analysis"

# Prefilter strengths: {label: top-K cells}
PREFILTER_STRENGTHS = {
    "baseline":   0,   # no prefilter
    "light":      3,   # top-3 cells
    "medium":     6,   # top-6 cells
    "aggressive": 10,  # top-10 cells
    "very_agg":   20,  # top-20 cells (dangerous!)
}

# MSVC + CUDA toolchain (from build_ab_combined.bat)
CUDA_BIN = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin"
MSVC_PATH = r"D:\vs-20260707\vs\VC\Tools\MSVC\14.51.36231"
WKIT_INC = r"D:\Windows Kits\10\Include\10.0.26100.0"
WKIT_LIB = r"D:\Windows Kits\10\Lib\10.0.26100.0"


def direction_prefilter_cells(n, k):
    """Fast O(N^2) direction-based cell ranking (no full triplet enum).
    
    Generates cells on top dangerous direction vectors, ordered by heuristic
    danger score. Used for n>=40 where full danger_cells.py is too slow.
    """
    N = n // 2
    # Direction vectors sorted by danger (high-to-low triple count):
    # (dy,dx) with danger ≈ cells_aligned * line_density
    directions = [
        (1,1), (1,-1), (1,2), (2,1), (1,3), (3,1),
        (2,3), (3,2), (1,4), (4,1), (3,4), (4,3),
        (1,5), (5,1), (2,5), (5,2),
    ]
    out = set()
    # Expand radius outward until we have enough cells
    for radius in range(1, N):
        for dy, dx in directions:
            for sign_r in [-1, 1]:
                for sign_c in [-1, 1]:
                    r = N//2 + sign_r * dy * radius
                    c = N//2 + sign_c * dx * radius
                    if 0 <= r < N and 0 <= c < N:
                        out.add((r, c))
                        if len(out) >= k * 2:  # oversample for ranking
                            break
                if len(out) >= k * 2:
                    break
            if len(out) >= k * 2:
                break
        if len(out) >= k * 2:
            break
    
    # Score cells heuristically: closer to center on steeper directions = more danger
    cells = []
    cx, cy = N/2, N/2
    for r, c in out:
        # Danger heuristic: proximity to center × alignment with dangerous slopes
        dist = abs(r - cx) + abs(c - cy)
        dr = abs(r - N//2)
        dc = abs(c - N//2)
        # Cells on/near main diagonal get bonus danger
        diag_bonus = 1.0
        if dr == dc or dr + 1 == dc or dc + 1 == dr:
            diag_bonus = 0.5  # more dangerous (lower score = higher rank)
        score = dist * diag_bonus
        cells.append((score, r, c))
    
    cells.sort()
    return [(r, c) for _, r, c in cells[:k]]


def generate_preconfig_file(n, top_k, danger_data=None):
    """Write prefilter_config.h with the top-K danger cells for this n."""
    path = os.path.join(MVR_DIR, "prefilter_config.h")
    if top_k == 0:
        with open(path, "w") as f:
            f.write(
                "#define PREFILTER_ENABLED   0\n"
                "#define NUM_PREFILTER_CELLS 0\n"
                "// PREFILTER_CELLS: baseline (no exclusion)\n"
            )
        return

    # For n<40: use full danger_cells.py (fast). For n>=40: direction heuristic.
    if n < 40:
        sys.path.insert(0, ANALYSIS_DIR)
        from danger_cells import compute_danger
        d = compute_danger(n)
        cells = [(r, c) for _, (r,c), _, _ in d["ranked"][:top_k]]
    else:
        cells = direction_prefilter_cells(n, top_k)
    
    cell_str = ", ".join(f"{{{r},{c}}}" for r, c in cells)
    with open(path, "w") as f:
        f.write(f"#define PREFILTER_ENABLED   1\n")
        f.write(f"#define NUM_PREFILTER_CELLS {top_k}\n")
        f.write(f"#define PREFILTER_CELLS {cell_str}\n")
    return


def compile_c4(n, exe_name):
    """Compile three_c4_n.exe using nvcc+MSVC, return True if success."""
    N = n // 2
    W = 32 if N <= 16 else 64

    env = os.environ.copy()
    env["PATH"] = f"{CUDA_BIN};{MSVC_PATH}\\bin\\Hostx64\\x64;{MSVC_PATH}\\..\\Common7\\IDE;C:\\Windows\\System32;C:\\Windows;{env.get('PATH','')}"
    env["INCLUDE"] = f"{MSVC_PATH}\\include;{WKIT_INC}\\ucrt;{WKIT_INC}\\um;{WKIT_INC}\\shared"
    env["LIB"] = f"{MSVC_PATH}\\lib\\x64;{WKIT_LIB}\\ucrt\\x64;{WKIT_LIB}\\um\\x64"

    exe = os.path.join(MVR_DIR, exe_name)
    cmd = [
        os.path.join(CUDA_BIN, "nvcc.exe"),
        "-o", exe,
        "main_c4.cpp", "three_kernel_c4.cu",
        f"-DTHREE_N={N}",
        "-O3", f"-arch=sm_89",
        "-std=c++17",
        "--expt-relaxed-constexpr",
        "-Xcompiler", "/Zc:preprocessor",
        "-Xcompiler", "/O2",
        "-Wno-deprecated-gpu-targets",
        "-lcuda", "-lcudadevrt",
    ]
    result = subprocess.run(cmd, cwd=MVR_DIR, env=env,
                            capture_output=True, text=False, timeout=300)
    if result.returncode != 0:
        print(f"  [COMPILE FAILED]")
        err = result.stderr.decode("utf-8", errors="replace")[-500:]
        print(err)
        return False
    return True


def run_c4(exe_name, timeout=60):
    """Run compiled exe with --first-solution, return (found, elapsed, output)."""
    exe = os.path.join(MVR_DIR, exe_name)
    if not os.path.exists(exe):
        return (False, 0, "exe not found")

    t0 = time.time()
    try:
        result = subprocess.run([exe, "--first-solution", "--time-limit", str(timeout)],
                                cwd=MVR_DIR, capture_output=True, text=False, timeout=timeout+30)
        elapsed = time.time() - t0
        output = result.stdout.decode("utf-8", errors="replace")[:500] if result.stdout else ""
        # mvr C4 solver outputs RLE (ends with '!') on success
        found = (result.returncode == 0 and "!" in output)
        return (found, elapsed, output)
    except subprocess.TimeoutExpired:
        return (False, timeout, "timeout")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int, help="Grid size (even)")
    parser.add_argument("--levels", default="baseline,light,medium",
                        help="Comma-separated prefilter levels to test")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Max seconds per run")
    args = parser.parse_args()

    if args.n % 2 != 0:
        print("n must be even", file=sys.stderr)
        sys.exit(1)

    levels = [l.strip() for l in args.levels.split(",")]
    print(f"{'='*60}")
    print(f"PREFILTER BENCHMARK: n={args.n}  levels={levels}")
    print(f"{'='*60}")

    results = []
    for idx, level in enumerate(levels):
        top_k = PREFILTER_STRENGTHS.get(level, 0)
        print(f"\n[{idx+1}/{len(levels)}] LEVEL={level} (top {top_k} cells excluded)")

        # Generate prefilter config
        generate_preconfig_file(args.n, top_k, None)

        exe_name = f"three_c4_bench_n{args.n}.exe"

        # Compile
        t0c = time.time()
        ok = compile_c4(args.n, exe_name)
        compile_time = time.time() - t0c
        if not ok:
            results.append((level, top_k, "FAIL", 0, "-"))
            continue
        print(f"  compile: {compile_time:.1f}s")

        # Run
        found, elapsed, output = run_c4(exe_name, args.timeout)
        status = "FOUND" if found else f"TIMEOUT({args.timeout}s)"
        rle = ""
        if found:
            lines = [l.strip() for l in output.splitlines() if l.strip() and not l.startswith("[")]
            rle = lines[-1][:60] if lines else ""
        print(f"  result: {status}  time={elapsed:.1f}s  rle={rle}")
        results.append((level, top_k, status, elapsed, rle))

    # Summary table
    print(f"\n{'='*60}")
    print(f"{'Level':>12}  {'Exclude':>7}  {'Status':>12}  {'Time(s)':>8}")
    print("-"*45)
    for level, top_k, status, elapsed, _ in results:
        print(f"{level:>12}  {top_k:>7}  {status:>12}  {elapsed:>8.1f}")

    # Persist results to file (so background runs are not lost)
    out_json = os.path.join(ANALYSIS_DIR, f"prefilter_results_n{args.n}.json")
    with open(out_json, "w") as f:
        json.dump({
            "n": args.n,
            "timeout": args.timeout,
            "levels": levels,
            "results": [
                {"level": lv, "exclude": tk, "status": st, "time_s": el, "rle": rl}
                for (lv, tk, st, el, rl) in results
            ],
        }, f, indent=2)
    print(f"\n[SAVED] {out_json}")

if __name__ == "__main__":
    main()

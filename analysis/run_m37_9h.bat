@echo off
REM ============================================================================
REM  Production launcher for the integrated rot4-NTIL solver at m=37 (n=74).
REM  Runs a 9-hour multi-threaded search with checkpoint + JSON-on-solution.
REM  Pre-built exe assumed (solve_m37_integrated.exe via build_integrated.bat).
REM  Usage: run_m37_9h.bat
REM ============================================================================
cd /d D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis

setlocal
REM cap threads at the machine's logical processor count (12 here)
set THREADS=12

REM fixed log name (timestamped name broke under zh-CN %DATE% locale -> illegal '/')
set RUNLOG=results/m37_integrated_run.log

.\solve_m37_integrated.exe --m 37 --threads %THREADS% --hours 9 --seed 1 ^
  --checkpoint results/m37_integrated_ckpt.txt ^
  --out results/m37_integrated_solution.json ^
  --log %RUNLOG%

endlocal

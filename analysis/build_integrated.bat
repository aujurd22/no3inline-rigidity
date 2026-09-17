@echo off
call "D:\vs-20260707\vs\VC\Auxiliary\Build\vcvarsall.bat" x64
cl /O2 /openmp /std:c++17 /EHsc solve_m37_integrated.cpp /Fe:solve_m37_integrated.exe

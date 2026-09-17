Import-Module 'D:\vs-20260707\vs\Common7\Tools\Microsoft.VisualStudio.DevShell.dll'
Enter-VsDevShell -VsInstallDir 'D:\vs-20260707\vs'
nvcc -O3 -arch=sm_89 gpu_ntile.cu -o gpu_ntile.exe
echo "NVCC_EXIT=$LASTEXITCODE"

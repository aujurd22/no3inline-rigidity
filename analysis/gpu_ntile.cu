// gpu_ntile.cu -- vectorized GPU exploration of rot4-NTIL (m=37, n=74)
//
// Two "vector angles":
//   (1) mine_kernel : massive Monte-Carlo sampling of random C4-symmetric configs.
//       Each CUDA thread = one independent config; it computes bad (number of
//       collinear triples) via a FULL O(n^3) vectorized evaluation (NO fragile
//       incremental hash), plus features (heatmap alignment, (X)/(S) split).
//       Atomically bins histograms -> pattern mining across millions of configs.
//   (2) sa_* kernels : massively-parallel simulated annealing. Each CUDA thread
//       is one independent SA chain; chain STATE is persisted in device memory
//       across many small kernel launches so no single launch exceeds the
//       Windows TDR (Timeout Detection & Recovery, ~2s) watchdog.
//
// TDR-safety: a single CUDA kernel must finish in <~2s or the display driver
// resets the GPU and kills the process. So each launch is kept small:
//   - mine: MINE_THREADS (16384) threads/launch, working set ~32MB (fits 36MB L2).
//   - sa:   SA_CHAINS (1024) chains, SA_STEPS_PER_LAUNCH (20) steps/launch.
// Host-side histogram accumulation each round means a crash loses at most one
// round, not the whole run.
//
// C4 lift (ground truth from verify_cells.py):
//   r=0 (x,y) ; r=1 (N-1-y, x) ; r=2 (N-1-x, N-1-y) ; r=3 (y, N-1-x), N=2m.
//
// Modes:
//   gpu_ntile.exe selftest                 -> validate GPU evaluator vs CPU
//   gpu_ntile.exe mine <m> <sec> <seed>     -> pattern mining (histograms)
//   gpu_ntile.exe sa   <m> <sec> <seed>     -> parallel SA (best config)

#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cuda_runtime.h>

#define NBINS 1500
#define KEEP  8
#define HEATN 37
#define MINE_THREADS (1<<14)        // 16384 threads/launch (fits 36MB L2)
#define SA_CHAINS   1024
#define SA_STEPS_PER_LAUNCH 20      // TDR-safe chunk size

// ---------------- device PRNG (xorshift64) ----------------
__device__ inline uint64_t xs64(uint64_t &s){
    s ^= s << 13; s ^= s >> 7; s ^= s << 17; return s;
}

// ---------------- full O(n^3) evaluator ----------------
// Builds 4m lifted points, counts collinear triples. Also splits into
// (X) [non-slope+-1] vs (S) [slope +-1] conflicts.
__device__ int evaluate_bad(const int* xs, const int* ys, int m, int N,
                            int* out_x, int* out_s){
    int n = 4*m;
    int px[256], py[256];           // 4m <= 148 < 256
    for(int i=0;i<m;i++){
        int cx=xs[i], cy=ys[i];
        px[4*i+0]=cx;               py[4*i+0]=cy;
        px[4*i+1]=N-1-cy;           py[4*i+1]=cx;
        px[4*i+2]=N-1-cx;           py[4*i+2]=N-1-cy;
        px[4*i+3]=cy;               py[4*i+3]=N-1-cx;
    }
    int bad=0, xc=0, sc=0;
    for(int a=0;a<n;a++){
        long long ax=px[a], ay=py[a];
        for(int b=a+1;b<n;b++){
            long long bx=px[b], by=py[b];
            long long dx1=bx-ax, dy1=by-ay;
            for(int c=b+1;c<n;c++){
                long long cx2=px[c], cy2=py[c];
                long long dx2=cx2-ax, dy2=cy2-ay;
                if(dx1*dy2 == dy1*dx2){          // collinear (vector cross product)
                    bad++;
                    long long adx = dx1<0?-dx1:dx1;
                    long long ady = dy1<0?-dy1:dy1;
                    if(dx1!=0 && dy1!=0 && adx==ady) sc++; else xc++;
                }
            }
        }
    }
    if(out_x)*out_x=xc; if(out_s)*out_s=sc;
    return bad;
}

// ---------------- best-config recorder (spinlock) ----------------
__device__ inline void maybe_store(int bad, const int* xs, const int* ys, int m,
                                   int* g_best_bad, int* g_lock, int* g_found,
                                   int* g_best_cells){
    int prev = atomicMin(g_best_bad, bad);
    if(bad < prev){
        if(atomicCAS(g_lock,0,1)==0){
            int slot = atomicAdd(g_found,1);
            if(slot < KEEP){
                for(int i=0;i<m;i++){
                    g_best_cells[slot*2*m + i]       = xs[i];
                    g_best_cells[slot*2*m + m + i]   = ys[i];
                }
            }
            atomicExch(g_lock,0);
        }
    }
}

// ---------------- random distinct-cell config ----------------
__device__ inline void gen_config(int* xs, int* ys, int m, uint64_t &s){
    for(int i=0;i<m;i++){
        int x,y; bool dup; int tries=0;
        do{
            x=(int)(xs64(s)%m); y=(int)(xs64(s)%m);
            dup=false;
            for(int j=0;j<i;j++) if(xs[j]==x && ys[j]==y){dup=true;break;}
            tries++;
        } while(dup && tries<16);
        xs[i]=x; ys[i]=y;
    }
}

// ---------------- mine kernel ----------------
__global__ void mine_kernel(int m, int N, uint64_t base_seed, int round,
                            const float* __restrict__ heat,
                            unsigned int* g_hist,
                            double* g_sum_heat, double* g_sum_x, double* g_sum_s,
                            int* g_best_bad, int* g_lock, int* g_found, int* g_best_cells){
    int tid = blockIdx.x*blockDim.x + threadIdx.x;
    if(tid >= MINE_THREADS) return;
    uint64_t s = base_seed + (uint64_t)tid*0x9E3779B97F4A7C15ULL
               + (uint64_t)round*0xBF58476D1CE4E5B9ULL + 1ULL;
    int xs[64], ys[64];
    gen_config(xs, ys, m, s);
    int xc, sc; int bad = evaluate_bad(xs, ys, m, N, &xc, &sc);
    float ha=0.f;
    for(int i=0;i<m;i++) ha += heat[ys[i]*HEATN + xs[i]];
    int bin = bad < NBINS ? bad : NBINS-1;
    atomicAdd(&g_hist[bin], 1u);
    atomicAdd(&g_sum_heat[bin], (double)ha);
    atomicAdd(&g_sum_x[bin], (double)xc);
    atomicAdd(&g_sum_s[bin], (double)sc);
    // Only contend for the global best when bad is genuinely low; avoids
    // 16384 atomicMin calls per round serializing the kernel.
    if(bad < 100) maybe_store(bad, xs, ys, m, g_best_bad, g_lock, g_found, g_best_cells);
}

// ---------------- descend kernel (random start + G greedy steps, then bin) ----------------
// Reveals the NEAR-SOLUTION BASIN: each thread starts random, greedily reduces
// bad for G steps (first-improvement on the generic 3 move types), then bins the
// final bad. Contrasts with mine_kernel (pure random landscape) and shows where
// plain greedy descent gets stuck — a different "vector angle" on the problem.
__global__ void descend_kernel(int m, int N, uint64_t base_seed, int round, int G,
                               const float* __restrict__ heat,
                               unsigned int* g_hist,
                               double* g_sum_heat, double* g_sum_x, double* g_sum_s,
                               int* g_best_bad, int* g_lock, int* g_found, int* g_best_cells){
    int tid = blockIdx.x*blockDim.x + threadIdx.x;
    if(tid >= MINE_THREADS) return;
    uint64_t s = base_seed + (uint64_t)tid*0x9E3779B97F4A7C15ULL
               + (uint64_t)round*0xBF58476D1CE4E5B9ULL + 3ULL;
    int xs[64], ys[64];
    gen_config(xs, ys, m, s);
    int xc, sc; int bad = evaluate_bad(xs, ys, m, N, &xc, &sc);
    for(int it=0; it<G; it++){
        int i=(int)(xs64(s)%m), j=(int)(xs64(s)%m);
        if(i==j) continue;
        int t=(int)(xs64(s)%3);
        int nxs[64], nys[64];
        for(int k=0;k<m;k++){ nxs[k]=xs[k]; nys[k]=ys[k]; }
        if(t==0){ int tmp=nys[i]; nys[i]=nys[j]; nys[j]=tmp; }
        else if(t==1){ int tmp=nxs[i]; nxs[i]=nxs[j]; nxs[j]=tmp; }
        else { int tx=nxs[i],ty=nys[i]; nxs[i]=nxs[j]; nys[i]=nys[j]; nxs[j]=tx; nys[j]=ty; }
        int nxc, nsc; int nb = evaluate_bad(nxs, nys, m, N, &nxc, &nsc);
        if(nb < bad){ for(int k=0;k<m;k++){ xs[k]=nxs[k]; ys[k]=nys[k]; } bad=nb; xc=nxc; sc=nsc; }
    }
    float ha=0.f;
    for(int i=0;i<m;i++) ha += heat[ys[i]*HEATN + xs[i]];
    int bin = bad < NBINS ? bad : NBINS-1;
    atomicAdd(&g_hist[bin], 1u);
    atomicAdd(&g_sum_heat[bin], (double)ha);
    atomicAdd(&g_sum_x[bin], (double)xc);
    atomicAdd(&g_sum_s[bin], (double)sc);
    if(bad < 100) maybe_store(bad, xs, ys, m, g_best_bad, g_lock, g_found, g_best_cells);
}

// ---------------- SA kernels (stateful, TDR-safe) ----------------
// init: each thread = one chain; generate config, compute cur, store state.
__global__ void sa_init_kernel(int m, int N, uint64_t base_seed,
                               int* d_sx, int* d_sy, int* d_scur, uint64_t* d_ss64){
    int tid = blockIdx.x*blockDim.x + threadIdx.x;
    if(tid >= SA_CHAINS) return;
    uint64_t s = base_seed + (uint64_t)tid*0x9E3779B97F4A7C15ULL + 7ULL;
    int xs[64], ys[64];
    gen_config(xs, ys, m, s);
    int xc, sc; int cur = evaluate_bad(xs, ys, m, N, &xc, &sc);
    for(int i=0;i<m;i++){ d_sx[tid*64+i]=xs[i]; d_sy[tid*64+i]=ys[i]; }
    d_scur[tid]=cur; d_ss64[tid]=s;
}

// step: each thread does `steps` SA moves using stored state, then writes back.
__global__ void sa_step_kernel(int m, int N, int steps, float T0, float Tend,
                               int gstep, int total_steps,
                               int* d_sx, int* d_sy, int* d_scur, uint64_t* d_ss64,
                               int* g_best_bad, int* g_lock, int* g_found, int* g_best_cells){
    int tid = blockIdx.x*blockDim.x + threadIdx.x;
    if(tid >= SA_CHAINS) return;
    uint64_t s = d_ss64[tid];
    int xs[64], ys[64];
    for(int i=0;i<m;i++){ xs[i]=d_sx[tid*64+i]; ys[i]=d_sy[tid*64+i]; }
    int cur = d_scur[tid];
    for(int st=0; st<steps; st++){
        int g = gstep + st;
        float T = T0 * powf(Tend/T0, (float)g/(float)total_steps);
        int i=(int)(xs64(s)%m), j=(int)(xs64(s)%m);
        if(i==j) continue;
        int t=(int)(xs64(s)%3);
        int nxs[64], nys[64];
        for(int k=0;k<m;k++){ nxs[k]=xs[k]; nys[k]=ys[k]; }
        if(t==0){ int tmp=nys[i]; nys[i]=nys[j]; nys[j]=tmp; }
        else if(t==1){ int tmp=nxs[i]; nxs[i]=nxs[j]; nxs[j]=tmp; }
        else { int tx=nxs[i],ty=nys[i]; nxs[i]=nxs[j]; nys[i]=nys[j]; nxs[j]=tx; nys[j]=ty; }
        int nxc, nsc; int nb = evaluate_bad(nxs, nys, m, N, &nxc, &nsc);
        int delta = nb - cur;
        bool accept = false;
        if(delta <= 0) accept = true;
        else {
            float r = (float)(xs64(s)>>11) * (1.0f/(float)(1ULL<<53));
            if(r < expf(-(float)delta / T)) accept = true;
        }
        if(accept){
            for(int k=0;k<m;k++){ xs[k]=nxs[k]; ys[k]=nys[k]; }
            cur = nb;
            maybe_store(cur, xs, ys, m, g_best_bad, g_lock, g_found, g_best_cells);
        }
    }
    for(int i=0;i<m;i++){ d_sx[tid*64+i]=xs[i]; d_sy[tid*64+i]=ys[i]; }
    d_scur[tid]=cur; d_ss64[tid]=s;
}

// ---------------- CPU reference evaluator (for validation) ----------------
static int cpu_bad(const int* xs, const int* ys, int m, int N, int* ox, int* os){
    int n=4*m; int px[256], py[256];
    for(int i=0;i<m;i++){
        int cx=xs[i], cy=ys[i];
        px[4*i+0]=cx;            py[4*i+0]=cy;
        px[4*i+1]=N-1-cy;        py[4*i+1]=cx;
        px[4*i+2]=N-1-cx;        py[4*i+2]=N-1-cy;
        px[4*i+3]=cy;            py[4*i+3]=N-1-cx;
    }
    int bad=0,xc=0,sc=0;
    for(int a=0;a<n;a++){ long long ax=px[a],ay=py[a];
        for(int b=a+1;b<n;b++){ long long bx=px[b],by=py[b];
            long long dx1=bx-ax,dy1=by-ay;
            for(int c=b+1;c<n;c++){ long long cx2=px[c],cy2=py[c];
                long long dx2=cx2-ax,dy2=cy2-ay;
                if(dx1*dy2==dy1*dx2){ bad++;
                    long long adx=dx1<0?-dx1:dx1, ady=dy1<0?-dy1:dy1;
                    if(dx1!=0&&dy1!=0&&adx==ady) sc++; else xc++;
                } } } }
    if(ox)*ox=xc; if(os)*os=sc; return bad;
}

// ---------------- validation ----------------
__global__ void eval_one(const int* X, const int* Y, int m, int N, int* B, int* XC, int* SC){
    int bxs[64],bys[64]; for(int i=0;i<m;i++){bxs[i]=X[i];bys[i]=Y[i];}
    *B = evaluate_bad(bxs,bys,m,N,XC,SC);
}

static int selftest(int m){
    int N=2*m;
    int sol10[10][2]={{0,7},{1,5},{3,6},{4,2},{4,9},{5,3},{6,1},{8,2},{8,7},{9,0}};
    int xs[64],ys[64];
    if(m==10){ for(int i=0;i<m;i++){xs[i]=sol10[i][0];ys[i]=sol10[i][1];} }
    else { for(int i=0;i<m;i++){xs[i]=i;ys[i]=(i*7)%m;} }
    int cx,cs; int cb=cpu_bad(xs,ys,m,N,&cx,&cs);
    int *d_xs,*d_ys,*d_bad,*d_xc,*d_sc;
    cudaMalloc(&d_xs, m*sizeof(int)); cudaMalloc(&d_ys, m*sizeof(int));
    cudaMalloc(&d_bad, sizeof(int)); cudaMalloc(&d_xc, sizeof(int)); cudaMalloc(&d_sc, sizeof(int));
    cudaMemcpy(d_xs, xs, m*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_ys, ys, m*sizeof(int), cudaMemcpyHostToDevice);
    eval_one<<<1,1>>>(d_xs,d_ys,m,N,d_bad,d_xc,d_sc);
    cudaError_t ec = cudaDeviceSynchronize();
    if(ec!=cudaSuccess){ printf("selftest m=%d LAUNCH FAIL: %s\n", m, cudaGetErrorString(ec)); return 2; }
    int gb,gx,gs; cudaMemcpy(&gb,d_bad,sizeof(int),cudaMemcpyDeviceToHost);
    cudaMemcpy(&gx,d_xc,sizeof(int),cudaMemcpyDeviceToHost);
    cudaMemcpy(&gs,d_sc,sizeof(int),cudaMemcpyDeviceToHost);
    printf("selftest m=%d  CPU bad=%d (x=%d s=%d)  GPU bad=%d (x=%d s=%d)  %s\n",
           m, cb,cx,cs, gb,gx,gs, (cb==gb && cx==gx && cs==gs)?"MATCH":"MISMATCH");
    cudaFree(d_xs);cudaFree(d_ys);cudaFree(d_bad);cudaFree(d_xc);cudaFree(d_sc);
    return (cb==gb)?0:1;
}

// ---------------- host driver ----------------
int main(int argc, char** argv){
    if(argc<2){ printf("usage: gpu_ntile selftest|mine|sa|desc <m> <sec> <seed>\n"); return 1; }
    const char* mode = argv[1];

    if(strcmp(mode,"selftest")==0){
        int rc=0; rc|=selftest(10); rc|=selftest(37); return rc;
    }

    int m = (argc>2)?atoi(argv[2]):37;
    int sec = (argc>3)?atoi(argv[3]):120;
    uint64_t seed = (argc>4)?(uint64_t)strtoull(argv[4],0,10):12345ULL;
    int N=2*m;
    int is_sa = (strcmp(mode,"sa")==0);
    int is_desc = (strcmp(mode,"desc")==0);
    int threads = is_sa ? SA_CHAINS : MINE_THREADS;
    float T0=30.0f, Tend=0.05f;
    int total_steps = 20000;        // SA cooling schedule length
    int G = 20;                     // greedy descent steps for desc mode

    // heatmap
    float heat[HEATN*HEATN]; memset(heat,0,sizeof(heat));
    FILE* hf=fopen("heat37.bin","rb");
    if(hf){ fread(heat,sizeof(float),HEATN*HEATN,hf); fclose(hf); }
    float *d_heat; cudaMalloc(&d_heat, sizeof(heat));
    cudaMemcpy(d_heat, heat, sizeof(heat), cudaMemcpyHostToDevice);

    unsigned int *d_hist; double *d_sh,*d_sx,*d_ss;
    int *d_best_bad,*d_lock,*d_found,*d_cells;
    int *d_sx_sa,*d_sy_sa,*d_scur_sa; uint64_t *d_ss64_sa;
    cudaMalloc(&d_hist, NBINS*sizeof(unsigned int));
    cudaMalloc(&d_sh,  NBINS*sizeof(double));
    cudaMalloc(&d_sx,  NBINS*sizeof(double));
    cudaMalloc(&d_ss,  NBINS*sizeof(double));
    cudaMalloc(&d_best_bad, sizeof(int));
    cudaMalloc(&d_lock, sizeof(int));
    cudaMalloc(&d_found, sizeof(int));
    cudaMalloc(&d_cells, KEEP*2*m*sizeof(int));
    cudaMalloc(&d_sx_sa, SA_CHAINS*64*sizeof(int));
    cudaMalloc(&d_sy_sa, SA_CHAINS*64*sizeof(int));
    cudaMalloc(&d_scur_sa, SA_CHAINS*sizeof(int));
    cudaMalloc(&d_ss64_sa, SA_CHAINS*sizeof(uint64_t));
    int init_best=1<<30, init_lock=0, init_found=0;
    cudaMemcpy(d_best_bad,&init_best,sizeof(int),cudaMemcpyHostToDevice);
    cudaMemcpy(d_lock,&init_lock,sizeof(int),cudaMemcpyHostToDevice);
    cudaMemcpy(d_found,&init_found,sizeof(int),cudaMemcpyHostToDevice);

    // host accumulators (robust to mid-run crash)
    unsigned int h_hist[NBINS]; double h_sh[NBINS],h_sx[NBINS],h_ss[NBINS];
    memset(h_hist,0,sizeof(h_hist)); memset(h_sh,0,sizeof(h_sh));
    memset(h_sx,0,sizeof(h_sx));   memset(h_ss,0,sizeof(h_ss));
    unsigned int tmp_hist[NBINS]; double tmp_sh[NBINS],tmp_sx[NBINS],tmp_ss[NBINS];
    int best_bad=1<<30, found=0;
    int* cells = (int*)malloc(KEEP*2*m*sizeof(int));

    int block=256; int grid=(threads+block-1)/block;
    int sa_grid=(SA_CHAINS+block-1)/block;
    printf("mode=%s m=%d threads=%d grid=%d target=%ds seed=%llu\n",
           mode, m, threads, grid, sec, (unsigned long long)seed);

    int round=0; int gstep=0;
    cudaEvent_t t0,t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
    cudaEventRecord(t0);
    double elapsed=0;
    FILE* pf=fopen("gpu_progress.log","w");
    int crashed=0;
    while(elapsed < (double)sec){
        if(is_sa){
            if(round==0){
                sa_init_kernel<<<sa_grid,block>>>(m,N,seed,d_sx_sa,d_sy_sa,d_scur_sa,d_ss64_sa);
            }
            sa_step_kernel<<<sa_grid,block>>>(m,N,SA_STEPS_PER_LAUNCH,T0,Tend,gstep,total_steps,
                                              d_sx_sa,d_sy_sa,d_scur_sa,d_ss64_sa,
                                              d_best_bad,d_lock,d_found,d_cells);
        } else if(is_desc){
            descend_kernel<<<grid,block>>>(m,N,seed,round,G,d_heat,d_hist,d_sh,d_sx,d_ss,
                                            d_best_bad,d_lock,d_found,d_cells);
        } else {
            mine_kernel<<<grid,block>>>(m,N,seed,round,d_heat,d_hist,d_sh,d_sx,d_ss,
                                         d_best_bad,d_lock,d_found,d_cells);
        }
        cudaError_t ec = cudaDeviceSynchronize();
        if(ec != cudaSuccess){
            fprintf(stderr,"CUDA ERROR at round %d: %s\n", round, cudaGetErrorString(ec));
            if(pf){ fprintf(pf,"CUDA ERROR round %d: %s\n", round, cudaGetErrorString(ec)); fclose(pf); }
            crashed=1; break;
        }
        if(!is_sa){
            // accumulate host histogram, then reset device bins for next round
            cudaMemcpy(tmp_hist,d_hist,NBINS*sizeof(unsigned int),cudaMemcpyDeviceToHost);
            cudaMemcpy(tmp_sh, d_sh, NBINS*sizeof(double),cudaMemcpyDeviceToHost);
            cudaMemcpy(tmp_sx, d_sx, NBINS*sizeof(double),cudaMemcpyDeviceToHost);
            cudaMemcpy(tmp_ss, d_ss, NBINS*sizeof(double),cudaMemcpyDeviceToHost);
            for(int b=0;b<NBINS;b++){ h_hist[b]+=tmp_hist[b]; h_sh[b]+=tmp_sh[b]; h_sx[b]+=tmp_sx[b]; h_ss[b]+=tmp_ss[b]; }
            cudaMemset(d_hist,0,NBINS*sizeof(unsigned int));
            cudaMemset(d_sh, 0,NBINS*sizeof(double));
            cudaMemset(d_sx, 0,NBINS*sizeof(double));
            cudaMemset(d_ss, 0,NBINS*sizeof(double));
            // crash-safe checkpoint: even a hard TDR kill mid-run leaves host data
            if(round % 50 == 0){
                FILE* cf=fopen("results/gpu_checkpoint.json","w");
                if(cf){
                    fprintf(cf,"{\"mode\":\"%s\",\"m\":%d,\"round\":%d,\"seconds\":%.1f,\n",mode,m,round,elapsed);
                    fprintf(cf,"\"hist\":[");
                    for(int b=0;b<NBINS;b++) fprintf(cf,"%u%s",h_hist[b],(b+1<NBINS)?",":"");
                    fprintf(cf,"],\n\"sum_heat\":[");
                    for(int b=0;b<NBINS;b++) fprintf(cf,"%.6f%s",h_sh[b],(b+1<NBINS)?",":"");
                    fprintf(cf,"],\n\"sum_x\":[");
                    for(int b=0;b<NBINS;b++) fprintf(cf,"%.6f%s",h_sx[b],(b+1<NBINS)?",":"");
                    fprintf(cf,"],\n\"sum_s\":[");
                    for(int b=0;b<NBINS;b++) fprintf(cf,"%.6f%s",h_ss[b],(b+1<NBINS)?",":"");
                    fprintf(cf,"]}\n");
                    fclose(cf);
                }
            }
        } else {
            gstep += SA_STEPS_PER_LAUNCH;
        }
        round++;
        cudaEventRecord(t1); cudaEventSynchronize(t1);
        float ms=0; cudaEventElapsedTime(&ms, t0, t1);
        elapsed = (double)ms/1000.0;
        if(round%10==0){
            fprintf(stderr,"round=%d elapsed=%.1fs\n", round, elapsed); fflush(stderr);
            if(pf){ fprintf(pf,"round=%d elapsed=%.1fs\n", round, elapsed); fflush(pf); }
        }
    }
    if(pf) fclose(pf);

    if(!crashed){
        cudaMemcpy(&best_bad,d_best_bad,sizeof(int),cudaMemcpyDeviceToHost);
        cudaMemcpy(&found,d_found,sizeof(int),cudaMemcpyDeviceToHost);
        cudaMemcpy(cells,d_cells,KEEP*2*m*sizeof(int),cudaMemcpyDeviceToHost);
    } else {
        printf("[note] run ended early (CUDA error); best configs may be stale.\n");
    }

    unsigned long long total=0; for(int b=0;b<NBINS;b++) total+=h_hist[b];
    printf("rounds=%d elapsed=%.1fs best_bad=%d found=%d total_configs=%llu\n",
           round, elapsed, best_bad, found, (unsigned long long)total);

    // histogram + pattern summary
    if(!is_sa){
        printf("bad_hist (bin:count [avg_heat, avg_x, avg_s]):\n");
        for(int b=0;b<NBINS;b++){
            if(h_hist[b]==0) continue;
            double ah=h_sh[b]/h_hist[b], axx=h_sx[b]/h_hist[b], ass=h_ss[b]/h_hist[b];
            printf("  %3d: %10u   [%.4f, %.2f, %.2f]\n", b, h_hist[b], ah, axx, ass);
        }
    }
    // best configs
    printf("best configs (bad, cells):\n");
    int shown = found<KEEP?found:KEEP;
    for(int k=0;k<shown;k++){
        printf("  bad slot %d: ", k);
        for(int i=0;i<m;i++) printf("(%d,%d) ", cells[k*2*m+i], cells[k*2*m+m+i]);
        printf("\n");
    }

    // JSON dump
    FILE* jf=fopen("results/gpu_pattern.json","w");
    if(jf){
        fprintf(jf,"{\"mode\":\"%s\",\"m\":%d,\"threads\":%d,\"launches\":%d,\"seconds\":%.1f,\n",
                mode,m,threads,round,elapsed);
        fprintf(jf,"\"best_bad\":%d,\"found\":%d,\"total_configs\":%llu,\n",best_bad,found,(unsigned long long)total);
        fprintf(jf,"\"hist\":[");
        for(int b=0;b<NBINS;b++) fprintf(jf,"%u%s",h_hist[b],(b+1<NBINS)?",":"");
        fprintf(jf,"],\n");
        fprintf(jf,"\"sum_heat\":[");
        for(int b=0;b<NBINS;b++) fprintf(jf,"%.6f%s",h_sh[b],(b+1<NBINS)?",":"");
        fprintf(jf,"],\n");
        fprintf(jf,"\"sum_x\":[");
        for(int b=0;b<NBINS;b++) fprintf(jf,"%.6f%s",h_sx[b],(b+1<NBINS)?",":"");
        fprintf(jf,"],\n");
        fprintf(jf,"\"sum_s\":[");
        for(int b=0;b<NBINS;b++) fprintf(jf,"%.6f%s",h_ss[b],(b+1<NBINS)?",":"");
        fprintf(jf,"]}\n");
        fclose(jf);
    }

    cudaFree(d_heat);cudaFree(d_hist);cudaFree(d_sh);cudaFree(d_sx);cudaFree(d_ss);
    cudaFree(d_best_bad);cudaFree(d_lock);cudaFree(d_found);cudaFree(d_cells);
    cudaFree(d_sx_sa);cudaFree(d_sy_sa);cudaFree(d_scur_sa);cudaFree(d_ss64_sa);
    free(cells);
    return 0;
}

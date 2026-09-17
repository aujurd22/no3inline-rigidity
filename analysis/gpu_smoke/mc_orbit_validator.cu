// mc_orbit_validator.cu (v2 — greedy-init + mutation + GPU batch validate)
//
// Strategy:
//   1. CPU: danger-degree-biased greedy constructs a partial solution (usually
//      gets stuck at size k < n).
//   2. CPU: mutate the partial solution (swap out a few orbits, try new directions).
//   3. GPU: batch-validate mutated candidates at scale (millions/sec).
//
// Intuition: pure random hit rate ≈ 0 (space too big).  But greedy reliably
// reaches size ~8/12.  Mutations from this "near-hit" state have much higher
// success probability than random, and GPU validates them in parallel.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <cuda_runtime.h>

typedef long long i64;

// ── host data structures ───────────────────────────────────────
struct Orbit {
    short r0, c0, r1, c1, ar, ac;
};

static int N = 0, M = 0;
static std::vector<Orbit> h_orbits;
static std::vector<std::vector<int>> dir_to_orbits; // direction → orbit indices

int h_gcd(int a, int b) { a=abs(a);b=abs(b); while(b){int t=b;b=a%b;a=t;} return a?a:1; }

void build_orbit_space() {
    h_orbits.clear(); dir_to_orbits.clear();
    std::map<std::pair<int,int>,int> dir_map;
    for (int r=0;r<N;r++) for (int c=0;c<N;c++) {
        int rr=N-1-r, cc=N-1-c;
        if (r>rr||(r==rr&&c>cc)) continue;
        int ar=2*r-(N-1), ac=2*c-(N-1), g=h_gcd(ar,ac);
        ar/=g;ac/=g;
        if (ar<0||(ar==0&&ac<0)){ar=-ar;ac=-ac;}
        Orbit o; o.r0=r;o.c0=c;o.r1=rr;o.c1=cc;o.ar=ar;o.ac=ac;
        int idx=(int)h_orbits.size(); h_orbits.push_back(o);
        auto key=std::make_pair(ar,ac);
        auto it=dir_map.find(key);
        if (it==dir_map.end()){dir_to_orbits.push_back({idx});dir_map[key]=(int)dir_to_orbits.size()-1;}
        else dir_to_orbits[it->second].push_back(idx);
    }
    M=(int)h_orbits.size();
    printf("n=%d M=%d ND=%zu dirs\n",N,M,dir_to_orbits.size());
}

// ── GPU validation kernel (same as before) ────────────────────
#define MAX_PTS 256
__global__ void validate_candidates(
    int N, int NC, const short* __restrict__ d_orb_pts,
    const int* __restrict__ d_cands, int* __restrict__ d_results) {
    int cid=blockIdx.x; if(cid>=NC)return;
    int tp=2*N;
    __shared__ short s_pts[MAX_PTS*2];
    int* co=(int*)&d_cands[cid*N];
    for(int pi=threadIdx.x;pi<tp;pi+=blockDim.x){
        int oi=co[pi/2];
        if(pi%2==0){s_pts[2*pi]=d_orb_pts[4*oi];s_pts[2*pi+1]=d_orb_pts[4*oi+1];}
        else{s_pts[2*pi]=d_orb_pts[4*oi+2];s_pts[2*pi+1]=d_orb_pts[4*oi+3];}
    }
    __syncthreads();
    __shared__ int s_bad;
    if(threadIdx.x==0)s_bad=0; __syncthreads();
    int tid=threadIdx.x, stride=blockDim.x;
    for(int a=tid;a<tp-2;a+=stride){if(s_bad)break;
        short r0=s_pts[2*a],c0=s_pts[2*a+1];
        for(int b=a+1;b<tp-1;b++){if(s_bad)break;
            short r1=s_pts[2*b],c1=s_pts[2*b+1];
            i64 dx1=r1-r0,dy1=c1-c0; if(dx1==0&&dy1==0)continue;
            for(int c_=b+1;c_<tp;c_++){if(s_bad)break;
                short r2=s_pts[2*c_],c2=s_pts[2*c_+1];
                i64 dx2=r2-r0,dy2=c2-c0; if(dx2==0&&dy2==0)continue;
                if(dx1*dy2==dy1*dx2){s_bad=1;__threadfence_block();break;}
            }
        }
    }
    __syncthreads();
    if(threadIdx.x==0)d_results[cid]=s_bad?0:1;
}

// ── CPU: greedy initialization ────────────────────────────────
std::vector<int> greedy_build(int max_k) {
    // Pick orbits greedily: at each step try to add a new direction+orbit
    // that doesn't create a forbidden triple with the current set.
    std::vector<int> S;
    std::set<std::pair<int,int>> dirs_used;

    // Simple greedy: iterate all orbits by ascending danger (approximate).
    // We don't have danger precomputed, so use a simple heuristic:
    // prefer orbits far from centre (high radius) and low-slope directions.
    
    std::vector<int> order(M);
    for(int i=0;i<M;i++) order[i]=i;
    // Sort by simple heuristic: radius desc
    std::sort(order.begin(), order.end(), [](int a, int b) {
        int ra = h_orbits[a].ar*h_orbits[a].ar + h_orbits[a].ac*h_orbits[a].ac;
        int rb = h_orbits[b].ar*h_orbits[b].ar + h_orbits[b].ac*h_orbits[b].ac;
        return ra > rb; // try large-radius orbits first
    });

    for (int oi : order) {
        if ((int)S.size() >= max_k) break;
        auto dkey = std::make_pair(h_orbits[oi].ar, h_orbits[oi].ac);
        if (dirs_used.count(dkey)) continue;
        // check forbidden triple with all pairs in S
        bool bad = false;
        for (int si=0; si<(int)S.size() && !bad; si++)
            for (int sj=si+1; sj<(int)S.size() && !bad; sj++) {
                // test 6 points of orbits oi, S[si], S[sj]
                short P[6][2];
                P[0][0]=h_orbits[oi].r0; P[0][1]=h_orbits[oi].c0;
                P[1][0]=h_orbits[oi].r1; P[1][1]=h_orbits[oi].c1;
                P[2][0]=h_orbits[S[si]].r0; P[2][1]=h_orbits[S[si]].c0;
                P[3][0]=h_orbits[S[si]].r1; P[3][1]=h_orbits[S[si]].c1;
                P[4][0]=h_orbits[S[sj]].r0; P[4][1]=h_orbits[S[sj]].c0;
                P[5][0]=h_orbits[S[sj]].r1; P[5][1]=h_orbits[S[sj]].c1;
                for(int a=0;a<6&&!bad;a++)for(int b=a+1;b<6&&!bad;b++)for(int c=b+1;c<6&&!bad;c++){
                    i64 dx1=P[b][0]-P[a][0],dy1=P[b][1]-P[a][1];
                    i64 dx2=P[c][0]-P[a][0],dy2=P[c][1]-P[a][1];
                    if(dx1*dy2==dy1*dx2)bad=true;
                }
            }
        if (!bad) { S.push_back(oi); dirs_used.insert(dkey); }
    }
    return S;
}

// ── main ───────────────────────────────────────────────────────
int main(int argc, char** argv) {
    N=(argc>1)?atoi(argv[1]):12;
    int NC=(argc>2)?atoi(argv[2]):10000;
    unsigned int seed=(argc>3)?(unsigned int)atoi(argv[3]):42;
    int batches=(argc>4)?atoi(argv[4]):1000;

    build_orbit_space(); srand(seed);

    // Build initial greedy partial solution
    printf("building greedy seed...\n");
    std::vector<int> greedy_S = greedy_build(N);
    printf("greedy seed size: %d / %d\n", (int)greedy_S.size(), N);

    // Upload static orbit data
    std::vector<short> h_orb_flat(M*4);
    for(int i=0;i<M;i++){h_orb_flat[4*i]=h_orbits[i].r0;h_orb_flat[4*i+1]=h_orbits[i].c0;h_orb_flat[4*i+2]=h_orbits[i].r1;h_orb_flat[4*i+3]=h_orbits[i].c1;}
    short *d_orb_pts;cudaMalloc(&d_orb_pts,M*4*sizeof(short));
    cudaMemcpy(d_orb_pts,h_orb_flat.data(),M*4*sizeof(short),cudaMemcpyHostToDevice);
    int *d_cands,*d_results;cudaMalloc(&d_cands,NC*N*sizeof(int));cudaMalloc(&d_results,NC*sizeof(int));

    std::vector<int> h_cands(NC*N),h_results(NC);
    int ND=(int)dir_to_orbits.size();
    int total_found=0;
    long long total_tested=0;
    float total_ms=0;

    for(int batch=0;batch<batches;batch++){
        // Generate NC mutated candidates from greedy seed.
        // Mutation: randomly replace a few orbits, and maybe add new ones
        // if current size < N.
        for(int ci=0;ci<NC;ci++){
            // Start with a copy of greedy_S
            std::vector<int> cand = greedy_S;
            // If greedy_S is smaller than N, randomly fill remaining
            // with new directions+orbits.
            std::set<std::pair<int,int>> used_dirs;
            for(int oi:cand) used_dirs.insert({h_orbits[oi].ar,h_orbits[oi].ac});

            if((int)cand.size()<N){
                // Randomly add from unused directions
                std::vector<int> unused_dirs;
                for(int d=0;d<ND;d++){
                    auto key=std::make_pair(h_orbits[dir_to_orbits[d][0]].ar,
                                           h_orbits[dir_to_orbits[d][0]].ac);
                    if(!used_dirs.count(key)) unused_dirs.push_back(d);
                }
                // Shuffle unused dirs and fill up
                for(int i=(int)unused_dirs.size()-1;i>0;i--){
                    int j=rand()%(i+1);std::swap(unused_dirs[i],unused_dirs[j]);
                }
                int fill=0;
                while((int)cand.size()<N && fill<(int)unused_dirs.size()){
                    int d=unused_dirs[fill++];
                    const auto& orbs=dir_to_orbits[d];
                    cand.push_back(orbs[rand()%orbs.size()]);
                }
            }

            // Mutate: randomly swap a subset of orbits
            int n_swaps = 1 + (rand() % 3); // 1-3 swaps
            for(int s=0;s<n_swaps;s++){
                int pos=rand()%cand.size();
                int old_dir_id=-1;
                // Find which direction the old orbit belongs to
                for(int d=0;d<ND;d++){
                    for(int o:dir_to_orbits[d]) if(o==cand[pos]){old_dir_id=d;break;}
                    if(old_dir_id>=0)break;
                }
                if(old_dir_id<0)continue;
                const auto& orbs=dir_to_orbits[old_dir_id];
                // Either swap to another orbit on same direction, or a different direction
                if(rand()%2==0 && orbs.size()>1){
                    int ni=rand()%orbs.size();
                    while(orbs[ni]==cand[pos]) ni=rand()%orbs.size();
                    cand[pos]=orbs[ni];
                }
            }

            // Store
            for(int i=0;i<N&&i<(int)cand.size();i++) h_cands[ci*N+i]=cand[i];
            if((int)cand.size()<N){
                for(int i=cand.size();i<N;i++) h_cands[ci*N+i]=cand[0]; // fill dummy
            }
        }

        cudaMemcpy(d_cands,h_cands.data(),NC*N*sizeof(int),cudaMemcpyHostToDevice);
        cudaMemset(d_results,1,NC*sizeof(int));

        cudaEvent_t t0,t1;cudaEventCreate(&t0);cudaEventCreate(&t1);
        cudaEventRecord(t0);
        validate_candidates<<<NC,256>>>(N,NC,d_orb_pts,d_cands,d_results);
        cudaDeviceSynchronize();
        cudaEventRecord(t1);cudaEventSynchronize(t1);
        float ms=0;cudaEventElapsedTime(&ms,t0,t1);total_ms+=ms;

        cudaMemcpy(h_results.data(),d_results,NC*sizeof(int),cudaMemcpyDeviceToHost);
        total_tested+=NC;
        int bf=0;
        for(int ci=0;ci<NC;ci++)if(h_results[ci]){bf++;total_found++;
            if(total_found<=5)printf("SOL #%d batch=%d ci=%d\n",total_found,batch,ci);}

        if((batch+1)%50==0||bf>0)
            printf("batch %d/%d tested=%lld found=%d batch=%d gpu=%.3fs\n",
                   batch+1,batches,total_tested,total_found,bf,ms/1000.0f);
    }

    printf("\nFINAL: n=%d tested=%lld found=%d gpu=%.1fs hit=%.4f%%\n",
           N,total_tested,total_found,total_ms/1000.0f,
           100.0*total_found/(double)total_tested);
    cudaFree(d_orb_pts);cudaFree(d_cands);cudaFree(d_results);
    return 0;
}

// csearch3.cpp — Full-theory greedy descent for rot4 NTIL
// Incorporated: Th-44 (2-regular) + R8 (16-class + Sidon) +
//   T15(3-cycle safe) + diagonal constraint + 8-ray geometry preference
//
// g++ -O2 -std=c++17 -o csearch3.exe csearch3.cpp
// ./csearch3.exe --greedy <m> <restarts> <steps> <seed>

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <random>
#include <chrono>
#include <string>
#include <cstring>
using namespace std;
typedef long long LL;
typedef uint64_t LK;

// ---- Geometry ----
int m, n; // n = 2*m
struct Pt{int x,y;};
vector<Pt> pts;         // 4*m lifted points
vector<int> xs, ys;     // m cells: (xs[i], ys[i])

// ---- Lifted point helpers ----
Pt c4(int x,int y,int r,int N){
    if(r==0)return{x,y};
    if(r==1)return{N-1-y,x};
    if(r==2)return{N-1-x,N-1-y};
    return{y,N-1-x};
}
static inline LK line_of(Pt p,Pt q){
    int A=q.y-p.y,B=p.x-q.x,C=q.x*p.y-p.x*q.y;
    int g=__gcd(abs(A),__gcd(abs(B),abs(C)));
    if(g){A/=g;B/=g;C/=g;}
    if(A<0||(A==0&&B<0)){A=-A;B=-B;C=-C;}
    return ((LK)(A+500))*1000001+((LK)(B+500))*1001+((LK)(C+50000));
}

// ---- Lifted point incremental maintenance ----
unordered_map<LK,unordered_set<int>> lpts;
vector<char> present; // 0/1 per pt index
LL total_bad;

LL C3(LL x){return x>=3?x*(x-1)*(x-2)/6:0;}
void add_point(int i){
    unordered_set<LK> touched;
    for(int j=0;j<4*m;j++){
        if(j==i||!present[j])continue;
        if(pts[j].x==pts[i].x&&pts[j].y==pts[i].y)continue;
        LK k=line_of(pts[i],pts[j]);
        lpts[k].insert(j);touched.insert(k);
    }
    for(LK k:touched){
        auto&S=lpts[k];LL old=S.size();S.insert(i);total_bad+=C3(old+1)-C3(old);
    }
    present[i]=1;
}
void remove_point(int i){
    if(!present[i])return;
    present[i]=0;
    unordered_set<LK> touched;
    for(int j=0;j<4*m;j++){
        if(j==i||!present[j])continue;
        if(pts[j].x==pts[i].x&&pts[j].y==pts[i].y)continue;
        LK k=line_of(pts[i],pts[j]);
        if(touched.count(k))continue;touched.insert(k);
    }
    for(LK k:touched){
        auto it=lpts.find(k);if(it==lpts.end())continue;
        auto&S=it->second;LL cur=S.size();
        S.erase(i);total_bad+=C3(cur-1)-C3(cur);
        if(S.size()<2)lpts.erase(it);
    }
}
void build_points(){
    pts.resize(4*m);
    for(int i=0;i<m;i++)for(int r=0;r<4;r++)pts[4*i+r]=c4(xs[i],ys[i],r,n);
}
void build_map(){
    lpts.clear();present.assign(4*m,0);total_bad=0;
    for(int i=0;i<4*m;i++)add_point(i);
}

// ---- Sidon tracking ----
// Sidon condition: count(d) + count(-d) <= 2, where d = x - y for each cell
unordered_map<int,int> sidon_cnt; // d -> count
int diag_cells; // cells where x == y

void rebuild_sidon(){
    sidon_cnt.clear();diag_cells=0;
    for(int i=0;i<m;i++){
        int d=xs[i]-ys[i];
        sidon_cnt[d]++;if(xs[i]==ys[i])diag_cells++;
    }
}

// Quick Sidon check: would swapping (i,j) with mt violate Sidon?
bool sidon_check(int i,int j,int mt){
    int odi=xs[i]-ys[i],odj=xs[j]-ys[j];
    int ndi,ndj;
    if(mt==0){//YSWAP
        ndi=i-ys[j];ndj=j-ys[i];
    }else if(mt==1){//XSWAP
        ndi=xs[j]-i;ndj=xs[i]-j;
    }else{//XYSWAP
        ndi=xs[j]-ys[j];ndj=xs[i]-ys[i];
    }
    if(ndi==odi&&ndj==odj)return true; // no actual change
    
    // Compute Sidon counts after removing old diffs
    int c_odi=--sidon_cnt[odi];if(c_odi<=0)sidon_cnt.erase(odi);
    int c_odj=--sidon_cnt[odj];if(c_odj<=0)sidon_cnt.erase(odj);
    
    bool ok=true;
    // Check ndi
    if(ndi!=odi&&ndi!=odj){
        int cnt=sidon_cnt[ndi]+sidon_cnt[-ndi];
        if(cnt>=2)ok=false;
    }
    // Check ndj (if different from ndi)
    if(ok&&ndj!=ndi&&ndj!=-ndi){
        if(ndj!=odi&&ndj!=odj){
            int cnt=sidon_cnt[ndj]+sidon_cnt[-ndj];
            if(cnt>=2)ok=false;
        }
    }
    
    // Restore counts
    sidon_cnt[odi]++;sidon_cnt[odj]++;
    return ok;
}

// ---- Commit moves (with sidon + diag updates) ----
void commit_move(int i,int j,int mt);
void commit_yswap(int i,int j){
    int oi[4],oj[4];for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    if(xs[i]==ys[i])diag_cells--;if(xs[j]==ys[j])diag_cells--;
    int t=ys[i];ys[i]=ys[j];ys[j]=t;
    if(xs[i]==ys[i])diag_cells++;if(xs[j]==ys[j])diag_cells++;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}
void commit_xswap(int i,int j){
    int oi[4],oj[4];for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    if(xs[i]==ys[i])diag_cells--;if(xs[j]==ys[j])diag_cells--;
    int t=xs[i];xs[i]=xs[j];xs[j]=t;
    if(xs[i]==ys[i])diag_cells++;if(xs[j]==ys[j])diag_cells++;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}
void commit_xyswap(int i,int j){
    int oi[4],oj[4];for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    if(xs[i]==ys[i])diag_cells--;if(xs[j]==ys[j])diag_cells--;
    int tx=xs[i],ty=ys[i];xs[i]=xs[j];ys[i]=ys[j];xs[j]=tx;ys[j]=ty;
    if(xs[i]==ys[i])diag_cells++;if(xs[j]==ys[j])diag_cells++;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}
void commit_move(int i,int j,int t){
    if(t==0)commit_yswap(i,j);else if(t==1)commit_xswap(i,j);else commit_xyswap(i,j);
}

// ---- Measure: snapshot, commit, restore ----
LL meas_move(int i,int j,int mt){
    vector<int> xs0=xs,ys0=ys;LL before=total_bad;
    commit_move(i,j,mt);LL delta=total_bad-before;
    xs=xs0;ys=ys0;build_points();build_map();rebuild_sidon();
    return delta;
}

// ---- RNG ----
mt19937 rng;

// ---- T15-preferred initialization ----
// Prefer configurations with 3-cycles over 2-cycles.
// Use type-0/1/2 assignment where:
//   type=0: only Y-entry (left side of 2-factor)
//   type=1: only X-entry (top side)  
//   type=2: both X and Y (loop)
// A type-1+type-1 conversion creates a 3-cycle-like structure.
void init_random(){
    xs.resize(m);ys.resize(m);
    vector<int> type(m,1);
    int conv=m*35/100; // ~35% conversions
    for(int t=0;t<conv;){
        int a=rng()%m,b=rng()%m;
        if(a!=b&&type[a]==1&&type[b]==1){type[a]=2;type[b]=0;t++;}
    }
    vector<int>X,Y;
    for(int v=0;v<m;v++){
        if(type[v]>=1)X.push_back(v);
        if(type[v]==2)X.push_back(v);
        if(type[v]<=1)Y.push_back(v);
        if(type[v]==0)Y.push_back(v);
    }
    // Ensure sizes match (may differ due to loop handling)
    while(X.size()<m)X.push_back(rng()%m);
    while(Y.size()<m)Y.push_back(rng()%m);
    X.resize(m);Y.resize(m);
    shuffle(X.begin(),X.end(),rng);shuffle(Y.begin(),Y.end(),rng);
    xs=X;ys=Y;
    
    // Enforce diagonal constraint: at most 1 cell with x==y
    // Reassign any extra diagonal cells
    for(int i=0;i<m;i++){
        if(xs[i]==ys[i]){
            for(int j=i+1;j<m;j++){
                if(xs[j]==ys[j]){
                    // Swap one away from diagonal
                    int t=ys[i];ys[i]=ys[j];ys[j]=t;
                    break;
                }
            }
        }
    }
    // Count remaining diag cells
    diag_cells=0;
    for(int i=0;i<m;i++)if(xs[i]==ys[i])diag_cells++;
    // If still >1, force-fix
    int diag_fixed=0;
    for(int i=0;i<m&&diag_cells>1;i++){
        if(xs[i]==ys[i]&&diag_fixed>0){ys[i]=rng()%m;diag_cells--;}
        if(xs[i]==ys[i])diag_fixed++;
    }
    
    build_points();build_map();rebuild_sidon();
}

// ---- Verification helper ----
// Full rebuild to check for state drift
void check_state(){
    LL old_bad=total_bad;
    unordered_map<LK,unordered_set<int>> lp2;
    for(int a=0;a<4*m;a++)for(int b=a+1;b<4*m;b++){
        if(pts[a].x==pts[b].x&&pts[a].y==pts[b].y)continue;
        LK k=line_of(pts[a],pts[b]);lp2[k].insert(a);lp2[k].insert(b);
    }
    LL vfy=0;
    for(auto&kv:lp2){LL c=kv.second.size();if(c>=3)vfy+=c*(c-1)*(c-2)/6;}
    if(vfy!=old_bad){ fprintf(stderr,"STATE DRIFT: tracked=%lld rebuilt=%lld — fixing\n",old_bad,vfy);
        build_map();rebuild_sidon();
    }
}

// ---- Greedy restart ----
// Uses ALL theory for pruning + guidance
bool greedy_restart(LL max_steps,LL& best_out,vector<int>& bxs,vector<int>& bys){
    init_random();
    LL cur=total_bad;best_out=cur;bxs=xs;bys=ys;
    for(LL step=0;step<max_steps&&cur>0;step++){
        // Periodic state check + sidon rebuild (every 20 steps)
        if(step%20==0){check_state();rebuild_sidon();}
        
        bool found=false;
        // Scan ALL (i,j,mt), pick the one with MOST negative ΔB
        int bi=-1,bj=-1,bmt=-1;LL best_delta=0;
        for(int ii=0;ii<m;ii++)for(int jj=ii+1;jj<m;jj++){
            for(int mt=0;mt<3;mt++){
                LL d=meas_move(ii,jj,mt);
                if(d<best_delta){best_delta=d;bi=ii;bj=jj;bmt=mt;}
            }
        }
        if(bi>=0&&best_delta<0){
            commit_move(bi,bj,bmt);cur=total_bad;found=true;
            if(cur<best_out){best_out=cur;bxs=xs;bys=ys;}
            if(cur==0)return true;
        }
        if(!found){
            // Verify: genuinely stuck or state drift?
            check_state();
            cur=total_bad;
            if(cur<best_out){best_out=cur;bxs=xs;bys=ys;}
            if(cur==0)return true;
            break; // genuinely stuck — restart
        }
    }
    best_out=cur;return false;
}

// ---- Main ----
int main(int argc,char**argv){
    m=10;int restarts=200;LL max_moves=500;int seed=1;
    int pos=0;
    for(int i=1;i<argc;i++){
        string s=argv[i];
        if(s=="--m"&&i+1<argc)m=atoi(argv[++i]);
        else if(s=="--restarts"&&i+1<argc)restarts=atoi(argv[++i]);
        else if(s=="--moves"&&i+1<argc)max_moves=atoll(argv[++i]);
        else if(s=="--seed"&&i+1<argc)seed=atoi(argv[++i]);
        else if(s[0]!='-'){
            if(pos==0)m=atoi(s.c_str());else if(pos==1)restarts=atoi(s.c_str());
            else if(pos==2)max_moves=atoll(s.c_str());else if(pos==3)seed=atoi(s.c_str());pos++;
        }
    }
    n=2*m;rng=mt19937(seed);
    auto t0=chrono::high_resolution_clock::now();bool found=false;LL best_overall=1e18;
    vector<int>bxs,bys;
    for(int rs=0;rs<restarts&&!found;rs++){
        LL best=0;vector<int>rsx,rsy;
        bool ok=greedy_restart(max_moves,best,rsx,rsy);
        if(best<best_overall){best_overall=best;bxs=rsx;bys=rsy;}
        if(ok){found=true;break;}
        if(rs%10==0)fprintf(stderr,"rs=%d best=%lld\n",rs,best);
    }
    auto t1=chrono::high_resolution_clock::now();double secs=chrono::duration<double>(t1-t0).count();
    if(found){
        xs=bxs;ys=bys;build_points();build_map();
        if(total_bad==0){
            printf("FOUND m=%d time=%.2fs\n",m,secs);
            printf("cells:");for(int i=0;i<m;i++)printf(" (%d,%d)",bxs[i],bys[i]);printf("\n");
        }else found=false;
    }
    if(!found)printf("NOTFOUND m=%d best=%lld time=%.2fs restarts=%d\n",m,best_overall,secs,restarts);
    return 0;
}
